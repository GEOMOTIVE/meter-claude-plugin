#!/usr/bin/env python3
"""Validate a local METER comparison ledger; no network or credential access."""
import argparse
from datetime import date, datetime
import hashlib
import json
import math
from pathlib import Path
import re
import sys


TOOLS = {
    "meter_ots_reach": "legacy",
    "meter_ots_reach_with_broadcast": "legacy",
    "meter_new_ots_reach": "new_ots",
    "meter_new_ots_reach_with_broadcast": "new_ots",
}


class LedgerError(ValueError):
    """The input cannot substantiate a comparable campaign recommendation."""


def require(condition, message):
    if not condition:
        raise LedgerError(message)


def number(value, label, minimum=0):
    require(type(value) in (int, float) and math.isfinite(value) and value >= minimum,
            f"{label}: expected a finite number >= {minimum}")
    return value


def integer(value, label, minimum=1):
    require(type(value) is int and value >= minimum, f"{label}: expected integer >= {minimum}")
    return value


def nonblank(value, label):
    require(isinstance(value, str) and bool(value.strip()), f"{label}: required text")
    return value


def object_value(value, label):
    require(isinstance(value, dict), f"{label}: expected an object")
    return value


def timestamp(value, label):
    parsed = datetime.fromisoformat(nonblank(value, label).replace("Z", "+00:00"))
    require(parsed.utcoffset() is not None, f"{label}: timezone required")


def ids(values, label, allow_empty=True):
    require(isinstance(values, list), f"{label}: expected an ID list")
    for value in values:
        integer(value, label)
    require(len(values) == len(set(values)), f"{label}: duplicate IDs")
    require(allow_empty or bool(values), f"{label}: empty program")
    return set(values)


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def validate_parameters(parameters, tool):
    require(isinstance(parameters, dict), "brief.parameters: expected an object")
    require("surfaces" not in parameters, "brief.parameters: surfaces belong in each scenario request")
    require(not {"userKey", "user_key", "fallbackMode"} & parameters.keys(),
            "brief.parameters: private account/routing selectors are not accepted")
    nonblank(parameters.get("city"), "city")
    start = date.fromisoformat(nonblank(parameters.get("periodFrom"), "periodFrom"))
    end = date.fromisoformat(nonblank(parameters.get("periodTo"), "periodTo"))
    require(start <= end, "periodFrom exceeds periodTo")
    legacy = TOOLS[tool] == "legacy"
    audience = parameters.get("audience") if legacy else parameters
    require(isinstance(audience, dict), "explicit audience required")
    low_key, high_key = ("age_from", "age_to") if legacy else ("ageFrom", "ageTo")
    low = integer(audience.get(low_key), low_key, 0)
    high = integer(audience.get(high_key), high_key, 0)
    require(low <= high, "audience age range is reversed")
    nonblank(audience.get("gender"), "gender")
    nonblank(audience.get("income"), "income")
    integer(parameters.get("chrono"), "chrono")
    integer(parameters.get("blockSize"), "blockSize", 0)
    integer(parameters.get("outputsInBlock"), "outputsInBlock")
    require(type(parameters.get("byDays")) is bool, "explicit byDays boolean required")
    impressions = parameters.get("impressions")
    require(isinstance(impressions, list) and bool(impressions), "explicit impressions required")
    for value in impressions:
        integer(value, "impressions", -1)
    norm = "normalizeCoeff" if legacy else "normalize_coeff"
    number(parameters.get(norm), norm)
    if tool == "meter_new_ots_reach_with_broadcast":
        require(type(parameters.get("broadcastRequest")) is int and parameters["broadcastRequest"] == 1,
                "New OTS broadcast campaign requires broadcastRequest=1")
    if tool == "meter_ots_reach":
        nonblank(parameters.get("reachModel"), "reachModel")


def summarize(ledger):
    require(isinstance(ledger, dict) and type(ledger.get("schema_version")) is int
            and ledger["schema_version"] == 1, "schema_version must be 1")
    brief = object_value(ledger["brief"], "brief")
    tool = brief["tool"]
    require(tool in TOOLS, "tool must calculate whole-campaign Reach")
    nonblank(brief.get("country"), "country")
    parameters = brief["parameters"]
    validate_parameters(parameters, tool)
    objective = object_value(brief["objective"], "objective")
    require(objective["metric"] == "campaign_reach_n_plus", "objective must be campaign Reach N+")
    frequency = integer(objective["frequency"], "frequency")
    constraints = object_value(brief["constraints"], "constraints")
    maximum = constraints["max_surfaces"]
    cap = constraints["budget_limit"]
    if maximum is not None:
        integer(maximum, "max_surfaces")
    if cap is not None:
        require(number(cap, "budget_limit") > 0, "budget_limit must be positive")
    require(maximum is not None or cap is not None, "a surface limit or spending cap is required")
    currency = constraints["currency"]
    require(isinstance(currency, str) and re.fullmatch(r"[A-Z]{3}", currency), "currency: expected three uppercase letters")
    require(brief["budget_mode"] in ("none", "estimate", "confirmed"), "invalid budget_mode")
    require(cap is None or brief["budget_mode"] != "none", "a spending cap requires costs")
    required = ids(constraints["required_ids"], "required_ids")
    excluded = ids(constraints["excluded_ids"], "excluded_ids")
    inventory = object_value(ledger["inventory"], "inventory")
    eligible = ids(inventory["eligible_ids"], "eligible_ids", False)
    require(not eligible & excluded, "excluded IDs remain in the eligible pool")
    require(required <= eligible, "required IDs are outside the eligible pool")
    require(inventory["coverage"] in ("complete", "screened", "partial"), "invalid inventory coverage")
    nonblank(inventory.get("source_reference"), "inventory.source_reference")
    search = object_value(ledger["search"], "search")
    limit = integer(search["evaluation_limit"], "evaluation_limit")
    stop = search.get("stop_reason")
    require(stop is None or isinstance(stop, str) and bool(stop.strip()), "invalid stop_reason")
    require(isinstance(ledger["scenarios"], list), "scenarios: expected a list")
    names, latest, request_keys = {}, {}, {}
    attempts = failed = search_calls = final_calls = 0
    comparison_id = digest({"brief": brief, "inventory": inventory})
    for scenario in ledger["scenarios"]:
        object_value(scenario, "scenario")
        name = nonblank(scenario.get("name"), "scenario.name")
        require(name not in names, f"duplicate scenario name: {name}")
        names[name] = scenario
        require(scenario["tool"] == tool, f"{name}: mixed calculation tools/methodologies")
        request = scenario["request"]
        require(isinstance(request, dict), f"{name}: request must be an object")
        request_parameters = {k: v for k, v in request.items() if k != "surfaces"}
        require(canonical(request_parameters) == canonical(parameters), f"{name}: submitted parameters differ from brief")
        selected = ids(request["surfaces"], f"{name}.surfaces", False)
        require(selected <= eligible, f"{name}: IDs outside the eligible pool")
        require(required <= selected, f"{name}: required IDs missing")
        require(maximum is None or len(selected) <= maximum, f"{name}: maximum surface count exceeded")
        key = digest({"comparison_id": comparison_id, "tool": tool, "request": request})
        request_keys[name] = key
        status = scenario["status"]
        require(status in ("planned", "ok", "no_data", "error"), f"{name}: invalid status")
        purpose = scenario["purpose"]
        require(purpose in ("search", "final_validation"), f"{name}: invalid purpose")
        cost = scenario.get("cost")
        require(cap is None or status not in ("planned", "ok") or cost is not None,
                f"{name}: spending cap requires a cost")
        if cost is not None:
            object_value(cost, f"{name}.cost")
            amount = number(cost["amount"], f"{name}.cost")
            require(cost["currency"] == currency, f"{name}: cost currency mismatch")
            require(cost["status"] in ("estimate", "confirmed"), f"{name}: invalid cost status")
            require(brief["budget_mode"] != "confirmed" or cost["status"] == "confirmed", f"{name}: estimated cost under confirmed-price policy")
            require(cap is None or amount <= cap, f"{name}: spending cap exceeded")
        if status == "planned":
            require(scenario.get("result") is None, f"{name}: planned scenario has a result")
            continue
        attempts += 1
        search_calls += purpose == "search"
        final_calls += purpose == "final_validation"
        latest[key] = scenario
        if status != "ok":
            require(scenario.get("result") is None, f"{name}: failed/no_data attempt must not carry media metrics")
            failure = object_value(scenario["failure"], f"{name}.failure")
            timestamp(failure.get("recorded_at"), f"{name}.failure.recorded_at")
            nonblank(failure.get("source_reference"), f"{name}.failure.source_reference")
            failed += 1
            continue
        result = object_value(scenario["result"], f"{name}.result")
        require(result["scope"] == "campaign", f"{name}: per-surface Reach is not campaign Reach")
        require(type(result["frequency"]) is int and result["frequency"] == frequency,
                f"{name}: wrong Reach frequency")
        require(number(result["reach_fraction"], f"{name}.reach_fraction") <= 1, f"{name}: Reach must be a fraction <= 1")
        require(number(result["universe"], f"{name}.universe") > 0, f"{name}: Universe must be positive")
        timestamp(result.get("calculated_at"), f"{name}.calculated_at")
        nonblank(result.get("source_reference"), f"{name}.source_reference")
    require(search_calls <= limit, "search evaluation limit exceeded")
    successful = [s for s in latest.values() if s["status"] == "ok"]
    successful.sort(key=lambda s: (-s["result"]["reach_fraction"], len(s["request"]["surfaces"]), s["name"]))
    best = successful[0] if successful else None
    final_name = ledger.get("final_scenario")
    confirmed = False
    if final_name is not None:
        require(final_name in names, "final_scenario does not identify a recorded attempt")
        final = names[final_name]
        require(final["status"] == "ok" and final["purpose"] == "final_validation", "final_scenario must be a successful final validation")
        require(best is not None and request_keys[final_name] == request_keys[best["name"]], "final validation does not match the best current program")
        require(latest[request_keys[final_name]]["name"] == final_name, "final validation was superseded by another attempt")
        require(stop is not None, "completed selection requires a stopping reason")
        confirmed = True
    limitations = ["Best tested program only; global optimality and booking availability are unverified."]
    if inventory["coverage"] != "complete":
        limitations.append("Inventory pool is " + inventory["coverage"] + ".")
    if not confirmed:
        limitations.append("Final campaign validation is not confirmed.")
    recommendation = None
    if best:
        result = best["result"]
        cost = best.get("cost")
        if cost and cost["status"] == "estimate":
            limitations.append("Budget and any cost-based feasibility use estimates.")
        elif not cost and brief["budget_mode"] != "none":
            limitations.append("Requested budget is not yet available.")
        recommendation = {
            "name": best["name"], "surface_ids": best["request"]["surfaces"],
            "reach_percent": result["reach_fraction"] * 100,
            "projected_people": result["reach_fraction"] * result["universe"],
            "universe": result["universe"], "cost": cost,
        }
    return {
        "brief_id": digest(brief), "comparison_id": comparison_id, "methodology": TOOLS[tool],
        "frequency": frequency, "eligible_count": len(eligible), "inventory_coverage": inventory["coverage"],
        "calculation_attempts": attempts, "unique_requests_attempted": len(latest), "failed_attempts": failed,
        "unique_rosters_attempted": len({tuple(sorted(s["request"]["surfaces"])) for s in latest.values()}),
        "search_calls": search_calls, "final_validation_calls": final_calls,
        "successful_current_programs": len(successful), "request_keys": request_keys,
        "best": recommendation, "final_confirmed": confirmed, "stop_reason": stop, "limitations": limitations,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ledger", type=Path, help="Local JSON campaign ledger")
    args = parser.parse_args()
    try:
        output = summarize(json.loads(args.ledger.read_text(encoding="utf-8")))
        print(json.dumps(output, ensure_ascii=False, indent=2, allow_nan=False))
    except (LedgerError, KeyError, TypeError, ValueError, OSError) as exc:
        print(f"Invalid campaign ledger: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
