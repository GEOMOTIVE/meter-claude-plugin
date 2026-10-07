#!/usr/bin/env python3
"""Classify local METER observations without calling, retrying or changing a service."""
import argparse
from datetime import datetime
import json
from pathlib import Path
import re
import sys

PACKAGES = {"meter@meter-public", "meter@meter-plugins"}
TOOLS = {"meter_status", "meter_query_surfaces", "meter_collect_surfaces", "meter_universe", "meter_calc_2media",
         "meter_mock_campaign", "meter_ots_reach", "meter_ots_reach_by_surface", "meter_ots_reach_with_broadcast",
         "meter_ots_report", "meter_statistic_profile_rate", "meter_new_ots", "meter_new_ots_reach",
         "meter_new_ots_reach_by_surface", "meter_new_ots_reach_with_broadcast", "meter_new_ots_profile_rate"}
NEW_OTS = {name for name in TOOLS if name.startswith("meter_new_ots")}
KNOWN_STATUS = {"connection_error", "timeout", "cancelled", "response_too_large", "inventory_scan_limit", "invalid_country_scope", "upstream_error"}


class DiagnosticError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise DiagnosticError(message)


def provenance(value):
    require(isinstance(value, dict), "observation must be an object")
    require(isinstance(value.get("source_reference"), str) and value["source_reference"].strip(), "source_reference required")
    try:
        timestamp = datetime.fromisoformat(value["observed_at"].replace("Z", "+00:00"))
        require(timestamp.utcoffset() is not None, "observed_at requires a timezone")
    except (KeyError, AttributeError, ValueError):
        raise DiagnosticError("observed_at must be an ISO timestamp with timezone") from None


def version(value):
    if value is None:
        return None
    provenance(value)
    raw = value.get("value")
    require(isinstance(raw, str) and len(raw) <= 80 and re.fullmatch(r"v?\d+\.\d+\.\d+(?:-[A-Za-z0-9.-]+)?(?:\+[A-Za-z0-9.-]+)?", raw), "invalid version observation")
    return raw


def unwrap(response):
    """Structured content is authoritative; conflicting JSON text is not ignored."""
    if not isinstance(response, dict):
        return None
    candidates = []
    if isinstance(response.get("structuredContent"), dict):
        candidates.append(response["structuredContent"])
    if "content" in response:
        for item in response["content"] if isinstance(response["content"], list) else []:
            if isinstance(item, dict) and item.get("type") == "text":
                try:
                    parsed = json.loads(item.get("text", ""))
                    if isinstance(parsed, dict):
                        candidates.append(parsed)
                except (ValueError, TypeError):
                    pass
    if candidates:
        if any(candidate != candidates[0] for candidate in candidates[1:]):
            return None
        return candidates[0]
    return response if "content" not in response else None


def classify(observation, legacy_allowed):
    layer = observation.get("layer")
    require(layer in ("mcp_transport", "mcp_rpc", "tool_result"), "observation layer must be explicit")
    tool = observation.get("tool")
    require(tool is None or (isinstance(tool, str) and tool in TOOLS), "use a canonical supported tool name")
    if layer == "tool_result":
        require(tool in TOOLS, "tool_result needs a canonical tool name")
    result = {"kind": "unknown", "layer": layer, "tool": tool, "api_probe": "not_established",
              "calculation": "not_established", "next_action": "inspect_retained_observation",
              "repeat_identical": False, "legacy_fallback_allowed": False, "safe_evidence": {}}

    def set_kind(kind, action, calculation="not_established"):
        result.update(kind=kind, next_action=action, calculation=calculation)
        return result

    if layer == "mcp_transport":
        status = observation.get("http_status")
        require(type(status) is int and 0 <= status <= 599, "transport http_status required")
        result["safe_evidence"]["http_status"] = status
        target = observation.get("target")
        require(target in ("mcp_endpoint", "site_root", "unknown"), "transport target must be explicit")
        if target != "mcp_endpoint":
            return set_kind("site_root_response" if target == "site_root" else "unknown_transport_target", "check_requested_connection")
        if status == 401:
            return set_kind("authentication_required", "reconnect_requested_connection")
        if status == 403:
            return set_kind("access_denied", "check_account_and_country_access")
        if status == 404:
            return set_kind("mcp_route_not_found", "verify_configured_mcp_endpoint")
        if status in (429, 502, 503, 504) or status >= 500:
            return set_kind("mcp_transport_unavailable", "check_transport_then_retry_later")
        if status == 0:
            return set_kind("mcp_connection_failed", "check_client_transport")
        return set_kind("mcp_transport_response", "inspect_rpc_or_tool_result")
    response = unwrap(observation.get("response"))
    if response is None:
        return result
    if layer == "mcp_rpc":
        error = response.get("error")
        if not isinstance(error, dict):
            return result
        code, message = error.get("code"), error.get("message")
        if type(code) is not int:
            return set_kind("mcp_rpc_error", "inspect_retained_observation")
        result["safe_evidence"]["rpc_code"] = code
        if code == -32602:
            return set_kind("invalid_arguments", "correct_same_tool_request")
        if code == -32600 and message == "Tool access denied.":
            return set_kind("access_denied", "check_account_and_country_access")
        if code == -32600 and message == "Wallet subscription verification is unavailable. Retry shortly.":
            return set_kind("subscription_verification_unavailable", "retry_subscription_check_later")
        if code == -32600 and isinstance(message, str) and re.fullmatch(
                r"An active METER Plugin subscription is required for this user and country \(\$[0-9]+/month\)\. Manage subscriptions: https://window\.wallet\.meter\.ad/plugin", message):
            return set_kind("subscription_required", "check_subscription_for_signed_in_user_and_country")
        return set_kind("mcp_rpc_error", "inspect_retained_observation")
    status, ok = response.get("status"), response.get("ok")
    if type(status) is not int or not 0 <= status <= 599 or type(ok) is not bool:
        return result
    result["safe_evidence"]["http_status"] = status
    label = response.get("statusText")
    if isinstance(label, str) and label in KNOWN_STATUS:
        result["safe_evidence"]["status_code"] = label
    data = response.get("data")
    successful = ok and 200 <= status < 300
    if isinstance(observation.get("response"), dict) and observation["response"].get("isError") is True and successful:
        return set_kind("inconsistent_envelope", "inspect_retained_observation")
    if tool == "meter_status" and successful and response.get("path") == "/subscription" and isinstance(data, dict) and data.get("subscription") == "required":
        return set_kind("subscription_required", "check_subscription_for_signed_in_user_and_country")
    if isinstance(data, dict) and data.get("status") == "no_data" and (successful or
            (not ok and status == 400 and tool in NEW_OTS and data.get("reason") == "new_ots_coverage_unavailable")):
        result["legacy_fallback_allowed"] = tool in NEW_OTS and legacy_allowed
        return set_kind("no_data", "calculate_equivalent_legacy_once" if result["legacy_fallback_allowed"] else "retain_unavailable_method_result", "unavailable")
    if ok != (200 <= status < 300):
        return set_kind("inconsistent_envelope", "inspect_retained_observation")
    if not ok:
        if status == 0:
            if label == "timeout":
                return set_kind("timeout", "retain_request_and_check_service", "failed")
            if label == "cancelled":
                return set_kind("cancelled", "retain_request_without_retry", "cancelled")
            if label == "connection_error":
                return set_kind("api_connection_failed", "check_service_availability", "failed")
            return result
        if status == 502 and isinstance(label, str) and label in ("response_too_large", "inventory_scan_limit", "invalid_country_scope"):
            if label == "response_too_large" and tool == "meter_query_surfaces":
                return set_kind("response_too_large", "reduce_limit_preserve_skip", "failed")
            if label == "inventory_scan_limit" and tool == "meter_query_surfaces":
                return set_kind("inventory_scan_limit", "narrow_filters_restart_skip_zero", "failed")
            return set_kind(label, "inspect_scope_or_response_contract", "failed")
        return set_kind("upstream_http_error", "inspect_retained_observation", "failed")
    if tool == "meter_status":
        if response.get("path") == "/api/v4/docs/doc.json":
            result["api_probe"] = "documentation_reachable"
            return set_kind("api_docs_reachable", "validate_requested_operation")
        if response.get("path") == "/api/v4":
            result["api_probe"] = "status_route_reachable"
            return set_kind("api_status_reachable", "validate_requested_operation")
        return set_kind("unrecognized_status_response", "inspect_retained_observation")
    if data is None or data == "" or data == [] or data == {}:
        return set_kind("empty_result", "retain_request_and_validate_result", "unavailable")
    if isinstance(data, dict) and data.get("status") in ("error", "failed"):
        return set_kind("inconsistent_envelope", "inspect_retained_observation")
    return set_kind("tool_response_received", "validate_result_before_reporting", "response_received")


def diagnose(snapshot):
    require(isinstance(snapshot, dict) and type(snapshot.get("schema_version")) is int and snapshot["schema_version"] == 1, "unsupported diagnostic schema")
    provenance(snapshot)
    connection = snapshot.get("connection")
    require(isinstance(connection, dict) and isinstance(connection.get("requested"), str) and connection["requested"] in PACKAGES,
            "requested connection must identify the public Codex or Claude package")
    requested = connection["requested"]
    state = connection.get("state")
    require(state in ("ready", "loading", "missing", "auth_required", "unknown"), "invalid connection state")
    observed = connection.get("observed")
    require(observed is None or isinstance(observed, str), "observed connection must be a client-reported identity or null")
    policy = snapshot.get("policy", {})
    require(isinstance(policy, dict) and type(policy.get("legacy_allowed", False)) is bool, "legacy_allowed must be a boolean")
    facts = snapshot.get("versions", {})
    require(isinstance(facts, dict), "versions must be an object")
    helper_version = json.loads(Path(__file__).parent.parent.joinpath("references/package-version.json").read_text())["version"]
    versions = {"helper_package": helper_version, "installed_package": version(facts.get("installed_package")),
                "loaded_skill": version(facts.get("loaded_skill")), "mcp_server": version(facts.get("mcp_server")),
                "installed_matches_helper": None}
    if observed == requested and versions["installed_package"] is not None:
        versions["installed_matches_helper"] = versions["installed_package"] == helper_version
    diagnosis = {"kind": "connection_unknown", "layer": "client", "tool": None, "api_probe": "not_established",
                 "calculation": "not_established", "next_action": "discover_requested_connection",
                 "repeat_identical": False, "legacy_fallback_allowed": False, "safe_evidence": {}}
    if observed is not None and observed != requested:
        diagnosis.update(kind="connection_mismatch", next_action="select_requested_connection")
    elif state in ("loading", "missing", "auth_required"):
        diagnosis.update(kind={"loading": "connection_loading", "missing": "connection_missing", "auth_required": "authentication_required"}[state],
                         next_action={"loading": "finish_discovery_then_check_once", "missing": "check_requested_plugin_installation", "auth_required": "reconnect_requested_connection"}[state])
    elif state == "ready" and observed == requested:
        observation = snapshot.get("observation")
        if observation is not None:
            provenance(observation)
            diagnosis = classify(observation, policy.get("legacy_allowed", False))
        else:
            diagnosis.update(kind="connection_ready_no_observation", next_action="check_status_once")
    return {"schema_version": 1, "versions": versions, "diagnosis": diagnosis,
            "limits": ["Observations are client-reported, not independently authenticated.",
                       "Helper/package, loaded skill and MCP server versions describe different components; no deployment version or incompatibility is inferred.",
                       "A status response does not validate campaign calculations; no retry or external action was executed."]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path)
    args = parser.parse_args()
    try:
        require(args.snapshot.stat().st_size <= 2 * 1024 * 1024, "diagnostic input exceeds 2 MiB; retain full results separately")
        result = diagnose(json.loads(args.snapshot.read_text()))
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    except (DiagnosticError, ValueError, KeyError, TypeError, OSError, RecursionError, OverflowError):
        # Do not echo malformed input, file paths, backend messages or credentials.
        print("Invalid diagnostic observation; check schema, timestamp, provenance and supported fields.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
