#!/usr/bin/env python3
"""Normalize sourced inventory and calculate an explicit local budget model."""
import argparse
import calendar
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import json
from pathlib import Path
import re
import sys


COMPONENTS = {"media", "production", "installation", "creative", "fees", "tax", "reserve"}
PER_SURFACE = {"media", "production", "installation"}
DIGITAL_TYPE = re.compile(r"\b(?:led|digital|dooh)\b|цифров|светодиод", re.I)
AMBIGUOUS_TYPE = re.compile(r"media\s*facade|медиафасад", re.I)
BLOCKED = re.compile(r"\b(?:dismantled|inactive|removed)\b|демонтирован\w*|неактив\w*", re.I)
NEGATED = re.compile(r"\b(?:not\s+(?:dismantled|inactive|removed)|не\s+демонтирован\w*)", re.I)
CONTROL_FIELDS = {"chrono", "blockSize", "outputsInBlock", "impressions", "broadcast", "creatives", "broadcastRequest"}


class ModelError(ValueError):
    pass


def check(condition, message):
    if not condition:
        raise ModelError(message)


def text(value, label):
    check(isinstance(value, str) and bool(value.strip()), f"{label}: required text")
    return value.strip()


def decimal(value, label):
    check(type(value) in (str, int, float, Decimal), f"{label}: expected a decimal number")
    result = Decimal(str(value))
    check(result.is_finite() and result >= 0, f"{label}: expected a finite nonnegative number")
    return result


def identifier(value):
    check(type(value) is int or isinstance(value, str) and re.fullmatch(r"[0-9]+", value), "invalid surface ID")
    result = int(value)
    check(result > 0, "surface ID must be positive")
    return result


def flag(value):
    if type(value) is bool:
        return value
    if type(value) is int and value in (0, 1):
        return bool(value)
    if isinstance(value, str) and value.strip().lower() in ("0", "1", "true", "false"):
        return value.strip().lower() in ("1", "true")
    raise ModelError("invalid boolean flag")


def dimensions(value):
    if not isinstance(value, str):
        return None
    match = re.fullmatch(r"\s*(\d+(?:[.,]\d+)?)\s*(?:m|м)?\s*[xх×]\s*(\d+(?:[.,]\d+)?)\s*(?:m|м)?\s*", value, re.I)
    if not match:
        return None
    width, height = (Decimal(v.replace(",", ".")) for v in match.groups())
    if width <= 0 or height <= 0:
        return None
    return width, height


def plain_decimal(value):
    return format(value, "f").rstrip("0").rstrip(".") if "." in format(value, "f") else format(value, "f")


def normalize(records, overrides, dimension_unit):
    check(isinstance(records, list), "records must be a list")
    check(dimension_unit in ("m", "unknown"), "dimension_unit must be m or unknown")
    check(isinstance(overrides, list), "classification_overrides must be a list")
    grouped = defaultdict(list)
    for record in records:
        check(isinstance(record, dict), "inventory record must be an object")
        grouped[identifier(record["id"])].append(record)
    resolutions = {}
    for override in overrides:
        check(isinstance(override, dict), "classification override must be an object")
        key = identifier(override["id"])
        check(key in grouped and key not in resolutions, "unknown or duplicate classification override")
        check(override["media_class"] in ("static", "digital"), "invalid resolved media_class")
        text(override.get("source_reference"), "override.source_reference")
        text(override.get("reason"), "override.reason")
        resolutions[key] = override
    rows = []
    for key, sources in sorted(grouped.items()):
        warnings, review = [], []
        flags, type_classes, values = set(), set(), defaultdict(set)
        blocked = False
        for source in sources:
            for name in ("isDigital", "is_digital"):
                if source.get(name) is not None:
                    try:
                        flags.add(flag(source[name]))
                    except ModelError:
                        review.append("invalid_digital_flag")
            for name in ("active", "isActive", "is_active"):
                if source.get(name) is not None:
                    try:
                        blocked |= not flag(source[name])
                    except ModelError:
                        review.append("invalid_active_flag")
            surface_type = str(source.get("type") or "").strip()
            if DIGITAL_TYPE.search(surface_type):
                type_classes.add(True)
            if AMBIGUOUS_TYPE.search(surface_type) and False in flags:
                review.append("ambiguous_mediafacade_classification")
            for field in ("description", "status"):
                message = str(source.get(field) or "")
                remainder = NEGATED.sub("", message)
                blocked |= bool(BLOCKED.search(remainder))
                if message.strip():
                    warnings.append(message.strip())
            for field in ("city", "address", "type", "supplierId", "side", "dimension", "lat", "lng"):
                value = source.get(field)
                if value is not None and value != "":
                    if field == "dimension":
                        value = dimensions(value) or str(value).strip().casefold()
                    elif field in ("lat", "lng"):
                        try:
                            value = Decimal(str(value))
                            check(value.is_finite(), "nonfinite coordinate")
                        except (ModelError, InvalidOperation):
                            warnings.append("invalid_coordinate")
                            continue
                    else:
                        value = str(value).strip().casefold()
                    values[field].add(value)
        # A missing field in one response is complementary data, not a conflict.
        coordinate_conflict = any(len(values[f]) > 1 for f in ("lat", "lng"))
        if coordinate_conflict:
            warnings.append("conflicting_map_coordinates")
        conflicting = [field for field, entries in values.items() if len(entries) > 1 and field not in ("lat", "lng")]
        if conflicting:
            review.append("conflicting_metadata:" + ",".join(sorted(conflicting)))
        evidence = flags | type_classes
        if len(evidence) > 1:
            review.append("conflicting_media_classification")
        if any(AMBIGUOUS_TYPE.search(str(s.get("type") or "")) for s in sources) and False in flags:
            review.append("ambiguous_mediafacade_classification")
        media_class = ("digital" if True in evidence else "static") if len(evidence) == 1 else "unknown"
        if key in resolutions:
            media_class = resolutions[key]["media_class"]
            review = [w for w in review if w not in ("invalid_digital_flag", "conflicting_media_classification", "ambiguous_mediafacade_classification")]
            warnings.append("classification_resolved: " + resolutions[key]["reason"])
        if media_class == "unknown":
            review.append("unknown_media_classification")
        metadata = {field: next((s[field] for s in sources if s.get(field) is not None and s.get(field) != ""), None)
                    for field in ("city", "country", "address", "type", "supplierId", "side", "dimension", "lat", "lng")}
        size = dimensions(metadata["dimension"])
        source_units = {str(s["dimension_unit"]).strip().lower() for s in sources if s.get("dimension_unit")}
        row_unit = dimension_unit if not source_units else "m" if source_units == {"m"} else "unknown"
        if size is None:
            warnings.append("missing_or_unparsed_dimensions")
        if row_unit == "unknown":
            warnings.append("dimension_units_unknown")
        coordinates = None
        try:
            lat, lng = (next(iter(values[f])) if len(values[f]) == 1 else Decimal(str(metadata[f])) for f in ("lat", "lng"))
            if lat.is_finite() and lng.is_finite() and -90 <= lat <= 90 and -180 <= lng <= 180 and (lat, lng) != (0, 0):
                coordinates = {"lat": float(lat), "lng": float(lng)}
        except InvalidOperation:
            pass
        if coordinate_conflict:
            coordinates = None
        if coordinates is None:
            warnings.append("missing_or_invalid_map_coordinates")
        review = sorted(set(review))
        rows.append({
            "id": key, "metadata": metadata, "media_class": media_class,
            "status": "inactive_or_dismantled" if blocked else "requires_review" if review else "not_known_inactive",
            "planning_eligible": not blocked and not review, "availability": "unconfirmed",
            "dimension_key": "x".join(plain_decimal(v) for v in size) if size else None,
            "dimension_unit": row_unit,
            "area_m2": plain_decimal(size[0] * size[1]) if size and row_unit == "m" else None,
            "coordinates": coordinates, "review_reasons": review, "warnings": sorted(set(warnings)),
            "classification_resolution": resolutions.get(key), "source_records": sources,
        })
    return rows


def amounts(value, status):
    check(isinstance(value, dict), "amounts must contain low/base/high")
    result = {k: decimal(value[k], k) for k in ("low", "base", "high")}
    check(result["low"] <= result["base"] <= result["high"], "amount range must satisfy low <= base <= high")
    check(status in ("estimate", "confirmed"), "invalid price status")
    check(status != "confirmed" or len(set(result.values())) == 1, "confirmed price cannot have an uncertain range")
    return result


def month_quantity(start, end):
    result, cursor = Decimal(0), start
    while cursor <= end:
        last = date(cursor.year, cursor.month, calendar.monthrange(cursor.year, cursor.month)[1])
        covered_end = min(last, end)
        result += Decimal((covered_end - cursor).days + 1) / Decimal(last.day)
        if covered_end == end:
            break
        cursor = last + timedelta(days=1)
    return result


def calculate(model):
    check(model["schema_version"] == 1 and type(model["schema_version"]) is int, "schema_version must be 1")
    source_reference = text(model.get("inventory_source_reference"), "inventory_source_reference")
    model_reference = text(model.get("model_source_reference"), "model_source_reference")
    rows = normalize(model["records"], model.get("classification_overrides", []), model["dimension_unit"])
    campaign = model["campaign"]
    parameters = campaign["parameters"]
    check(isinstance(parameters, dict) and "surfaces" not in parameters, "campaign.parameters must exclude surfaces")
    text(parameters.get("city"), "campaign city")
    start, end = (date.fromisoformat(text(parameters.get(k), k)) for k in ("periodFrom", "periodTo"))
    check(start <= end, "campaign date range is reversed")
    currency = campaign["currency"]
    check(isinstance(currency, str) and re.fullmatch(r"[A-Z]{3}", currency), "invalid currency")
    precision = campaign.get("money_decimals", 2)
    check(type(precision) is int and 0 <= precision <= 4, "money_decimals must be 0..4")
    quantum = Decimal(1).scaleb(-precision)
    def money(value):
        return format(value.quantize(quantum, rounding=ROUND_HALF_UP), "f")
    check(isinstance(model["selected_ids"], list), "selected_ids must be an ID list")
    selected = [identifier(v) for v in model["selected_ids"]]
    check(len(selected) == len(set(selected)), "duplicate selected IDs")
    by_id = {r["id"]: r for r in rows}
    check(all(v in by_id for v in selected), "selected IDs outside inventory")
    invalid = [v for v in selected if not by_id[v]["planning_eligible"]]
    check(not invalid, "selected IDs require review or are inactive: " + str(invalid))
    check(isinstance(model["required_components"], list), "required_components must be a list")
    required = set(model["required_components"])
    check("media" in required and required <= COMPONENTS, "required_components must include media and known component names")
    controls = {k: parameters[k] for k in sorted(CONTROL_FIELDS & parameters.keys())}
    rules = []
    for rule in model.get("price_rules", []):
        check(isinstance(rule, dict), "price rule must be an object")
        check(rule["component"] in PER_SURFACE, "price rule component must be media/production/installation")
        check(rule["currency"] == currency, "price rule currency mismatch")
        text(rule.get("source_reference"), "price source_reference")
        text(rule.get("basis"), "price basis")
        date.fromisoformat(text(rule.get("as_of"), "price as_of"))
        valid_from, valid_to = (date.fromisoformat(text(rule.get(k), k)) for k in ("valid_from", "valid_to"))
        check(valid_from <= start <= end <= valid_to, "price validity does not cover campaign")
        match = rule["match"]
        check(isinstance(match, dict), "price match must be an object")
        check(match["media_class"] in ("static", "digital"), "price requires a known media_class")
        text(match.get("type"), "price matched type")
        check(match["type"] != "*" or rule["component"] != "media", "media rates require an explicit surface type")
        check(match["dimension"] == "*" or dimensions(match["dimension"]) is not None, "invalid matched dimensions")
        check(rule["status"] != "confirmed" or "id" in match and match["type"] != "*" and match["dimension"] != "*",
              "confirmed quote requires exact ID/type/format match")
        if "id" in match:
            matched_id = identifier(match["id"])
            if matched_id in selected:
                row = by_id[matched_id]
                check(match["dimension"] == "*" or row["dimension_unit"] == "m", "exact-ID physical price requires known metre dimensions")
                check(match["media_class"] == row["media_class"], "exact-ID price conflicts with inventory media class")
                check(match["type"] == "*" or match["type"].strip().casefold() == str(row["metadata"]["type"] or "").strip().casefold(), "exact-ID price conflicts with inventory type")
                check(match["dimension"] == "*" or dimensions(match["dimension"]) == dimensions(row["metadata"]["dimension"]), "exact-ID price conflicts with inventory dimensions")
        check(rule["unit"] in ("campaign", "surface_month", "surface_day", "surface", "m2", "m2_month"), "invalid price unit")
        check(rule["component"] != "media" or rule["unit"] in ("campaign", "surface_month", "surface_day", "m2_month"),
              "media price unit must specify a campaign, day or month")
        if rule["component"] == "media" and rule["unit"] == "campaign":
            check((valid_from, valid_to) == (start, end), "campaign package price must match the exact period")
        if match["media_class"] == "digital" and rule["component"] == "media":
            check({"chrono", "blockSize", "outputsInBlock"} <= parameters.keys(), "digital pricing requires explicit campaign schedule")
            check(json.dumps(rule.get("priced_controls"), sort_keys=True, allow_nan=False) == json.dumps(controls, sort_keys=True, allow_nan=False),
                  "digital quote/model schedule differs from campaign")
            check("broadcastRequest" not in parameters or type(parameters["broadcastRequest"]) is int and parameters["broadcastRequest"] == 1,
                  "capacity mode cannot price a purchased digital campaign")
        if rule["unit"] in ("surface_month", "m2_month"):
            check(rule.get("proration") == "calendar_days", "monthly pricing requires explicit calendar_days proration")
        rules.append((rule, amounts(rule["amounts"], rule["status"])))
    totals = {c: {k: Decimal(0) for k in ("low", "base", "high")} for c in sorted(COMPONENTS)}
    line_items, statuses, missing, included = [], [], [], set()
    for key in selected:
        row = by_id[key]
        for component in sorted(PER_SURFACE):
            candidates = []
            for rule, rate in rules:
                match = rule["match"]
                if rule["component"] != component or match["media_class"] != row["media_class"]:
                    continue
                if "id" in match and identifier(match["id"]) != key:
                    continue
                if match["type"] != "*" and match["type"].strip().casefold() != str(row["metadata"]["type"] or "").strip().casefold():
                    continue
                if match["dimension"] != "*" and (row["dimension_unit"] != "m" or dimensions(match["dimension"]) != dimensions(row["metadata"]["dimension"])):
                    continue
                candidates.append((rule, rate))
            specific = [c for c in candidates if "id" in c[0]["match"]]
            candidates = specific or candidates
            check(len(candidates) <= 1, f"ambiguous {component} rates for ID {key}")
            if not candidates:
                if component in required:
                    missing.append({"id": key, "component": component, "reason": "no_matching_rate"})
                continue
            rule, rate = candidates[0]
            unit = rule["unit"]
            quantity = Decimal(1)
            if unit == "surface_day":
                quantity = Decimal((end - start).days + 1)
            if unit in ("surface_month", "m2_month"):
                quantity = month_quantity(start, end)
            if unit in ("m2", "m2_month"):
                if row["area_m2"] is None:
                    missing.append({"id": key, "component": component, "reason": "missing_dimensions"})
                    continue
                quantity *= Decimal(row["area_m2"])
            cost = {k: rate[k] * quantity for k in rate}
            # Totals sum the displayed line amounts, avoiding rounding drift in exports.
            cost = {k: v.quantize(quantum, rounding=ROUND_HALF_UP) for k, v in cost.items()}
            for k in cost:
                totals[component][k] += cost[k]
            included.add(component)
            statuses.append(rule["status"])
            line_items.append({"id": key, "component": component, "quantity": plain_decimal(quantity), "unit": unit,
                               "rate_amounts": {k: plain_decimal(v) for k, v in rate.items()},
                               "amounts": {k: money(v) for k, v in cost.items()}, "status": rule["status"],
                               "source_reference": rule["source_reference"], "basis": rule["basis"],
                               "as_of": rule["as_of"], "valid_from": rule["valid_from"], "valid_to": rule["valid_to"],
                               "match": rule["match"], "priced_controls": rule.get("priced_controls")})
    for extra in model.get("extras", []):
        check(isinstance(extra, dict), "extra must be an object")
        component = extra["component"]
        check(component in COMPONENTS - PER_SURFACE, "extra must be creative/fees/tax/reserve")
        check(extra["currency"] == currency, "extra currency mismatch")
        text(extra.get("source_reference"), "extra source_reference")
        text(extra.get("basis"), "extra basis")
        rate = amounts(extra["amounts"], extra["status"])
        check(extra["unit"] in ("campaign", "fraction"), "invalid extra unit")
        base = {k: Decimal(1) for k in rate}
        if extra["unit"] == "fraction":
            applies = extra["applies_to"]
            check(isinstance(applies, list) and bool(applies) and len(applies) == len(set(applies)), "fraction requires unique applies_to components")
            processed = included | {item["component"] for item in missing}
            check(set(applies) <= processed and component not in applies, "fraction base must name previously processed components")
            if not set(applies) & included:
                missing.append({"id": None, "component": component, "reason": "missing_fraction_base_rates"})
                continue
            # With missing rates this is the fraction of known amounts only;
            # missing_costs still prevents a complete total or bound ledger_cost.
            base = {k: sum((totals[c][k] for c in applies), Decimal(0)) for k in rate}
        cost = {k: (rate[k] * base[k]).quantize(quantum, rounding=ROUND_HALF_UP) for k in rate}
        for k in cost:
            totals[component][k] += cost[k]
        included.add(component)
        statuses.append(extra["status"])
        line_items.append({"id": None, "component": component, "unit": extra["unit"],
                           "rate_amounts": {k: plain_decimal(v) for k, v in rate.items()},
                           "base_amounts": {k: money(v) for k, v in base.items()}, "applies_to": extra.get("applies_to"),
                           "amounts": {k: money(v) for k, v in cost.items()}, "status": extra["status"],
                           "source_reference": extra["source_reference"], "basis": extra["basis"]})
    missing.extend({"id": None, "component": c, "reason": "missing_component"}
                   for c in sorted(required - included - PER_SURFACE - {item["component"] for item in missing}))
    subtotal = {k: sum((totals[c][k] for c in COMPONENTS), Decimal(0)) for k in ("low", "base", "high")}
    complete = bool(selected) and not missing
    status = "estimate" if "estimate" in statuses else "confirmed"
    ledger_cost = None
    if complete:
        ledger_cost = {"amount": float(subtotal["base"]), "currency": currency, "status": status,
                       "surface_ids": selected, "campaign_parameters": parameters,
                       "amount_decimal": money(subtotal["base"]), "source_reference": model_reference,
                       "low": money(subtotal["low"]), "high": money(subtotal["high"])}
    return {
        "schema_version": 1, "inventory_source_reference": source_reference, "rows": rows,
        "eligible_ids": [r["id"] for r in rows if r["planning_eligible"]],
        "excluded_ids": [r["id"] for r in rows if not r["planning_eligible"]],
        "selected_ids": selected, "campaign": campaign, "line_items": line_items,
        "components": {c: {k: money(v) for k, v in totals[c].items()} for c in sorted(included)},
        "not_included_components": sorted(COMPONENTS - included), "missing_costs": missing,
        "budget_complete": complete, "budget_status": status if complete else "partial",
        "known_subtotal": {k: money(v) for k, v in subtotal.items()},
        "total": {k: money(v) for k, v in subtotal.items()} if complete else None,
        "ledger_cost": ledger_cost,
        "limitations": ["Availability is unconfirmed; price provenance is client-reported.",
                         "Totals cover only the listed components; ranges are model scenarios, not statistical confidence intervals."],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model", type=Path)
    args = parser.parse_args()
    try:
        output = calculate(json.loads(args.model.read_text(encoding="utf-8")))
        print(json.dumps(output, ensure_ascii=False, indent=2, allow_nan=False))
    except (ModelError, KeyError, TypeError, ValueError, InvalidOperation, OSError) as exc:
        print(f"Invalid inventory/budget model: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
