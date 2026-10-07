"""Decisions from real public response shapes, without live calls or word matching."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/meter/scripts/diagnose.py"
spec = importlib.util.spec_from_file_location("diagnose", SCRIPT)
diagnostics = importlib.util.module_from_spec(spec)
spec.loader.exec_module(diagnostics)


def fixture(response=None, tool="meter_status", layer="tool_result"):
    return {"schema_version": 1, "observed_at": "2026-10-07T15:00:00+05:00", "source_reference": "local-observation.json",
            "connection": {"requested": "meter@meter-public", "observed": "meter@meter-public", "state": "ready"},
            "versions": {}, "policy": {"legacy_allowed": False},
            "observation": {"observed_at": "2026-10-07T15:00:00+05:00", "source_reference": "tool-result.json",
                            "layer": layer, "tool": tool, "response": response if response is not None else
                            {"ok": True, "status": 200, "statusText": "OK", "method": "GET", "path": "/api/v4", "data": "METER"}}}


def kind(snapshot):
    return diagnostics.diagnose(snapshot)["diagnosis"]


class DiagnosticTests(unittest.TestCase):
    def test_status_and_docs_reachability_do_not_claim_calculation_success(self):
        self.assertEqual(kind(fixture())["api_probe"], "status_route_reachable")
        value = fixture()
        value["observation"]["response"].update(path="/api/v4/docs/doc.json", data={"swagger": "2.0", "operations": 19})
        result = kind(value)
        self.assertEqual(result["kind"], "api_docs_reachable")
        self.assertEqual(result["calculation"], "not_established")

    def test_subscription_http200_is_not_an_api_probe(self):
        value = fixture({"ok": True, "status": 200, "statusText": "Subscription required", "method": "GET",
                         "path": "/subscription", "data": {"connected": True, "subscription": "required"}})
        result = kind(value)
        self.assertEqual(result["kind"], "subscription_required")
        self.assertEqual(result["api_probe"], "not_established")
        self.assertNotIn("reconnect", result["next_action"])

    def test_rpc_errors_share_code_but_need_actual_reason(self):
        cases = [("Tool access denied.", "access_denied"),
                 ("Wallet subscription verification is unavailable. Retry shortly.", "subscription_verification_unavailable"),
                 ("An active METER Plugin subscription is required for this user and country ($599/month). Manage subscriptions: https://window.wallet.meter.ad/plugin", "subscription_required"),
                 ("unknown error with private SQL", "mcp_rpc_error")]
        for message, expected in cases:
            result = kind(fixture({"error": {"code": -32600, "message": message}}, layer="mcp_rpc"))
            self.assertEqual(result["kind"], expected)
            self.assertNotIn(message, json.dumps(result))
        self.assertEqual(kind(fixture({"error": {"code": -32602, "message": "Private invalid input"}}, tool="meter_ots_reach", layer="mcp_rpc"))["next_action"], "correct_same_tool_request")

    def test_auth_401_is_distinct_from_upstream_api_401(self):
        value = fixture({"error": "invalid_token"}, layer="mcp_transport")
        value["observation"].update(http_status=401, target="mcp_endpoint")
        self.assertEqual(kind(value)["kind"], "authentication_required")
        value["observation"].update(layer="tool_result", response={"ok": False, "status": 401, "statusText": "upstream_error", "data": None})
        self.assertEqual(kind(value)["kind"], "upstream_http_error")
        self.assertNotIn("reconnect", kind(value)["next_action"])

    def test_site_root_404_is_not_a_failed_mcp_route(self):
        value = fixture({"body": "404 Not Found nginx"}, layer="mcp_transport")
        value["observation"].update(http_status=404, target="site_root")
        self.assertEqual(kind(value)["kind"], "site_root_response")
        value["observation"]["target"] = "mcp_endpoint"
        self.assertEqual(kind(value)["kind"], "mcp_route_not_found")
        value["observation"].update(http_status=503, target="mcp_endpoint")
        self.assertEqual(kind(value)["kind"], "mcp_transport_unavailable")

    def test_transport_status_is_validated_without_parsing_html_body(self):
        value = fixture("<html>SECRET nginx</html>", layer="mcp_transport")
        value["observation"].update(http_status=404, target="site_root")
        self.assertEqual(kind(value)["kind"], "site_root_response")
        value["observation"].pop("response")
        value["observation"].update(http_status=401, target="mcp_endpoint")
        self.assertEqual(kind(value)["kind"], "authentication_required")
        value["observation"]["http_status"] = True
        with self.assertRaises(diagnostics.DiagnosticError):
            kind(value)

    def test_malformed_envelopes_never_claim_a_recognized_failure(self):
        value = fixture({"error": {"code": -32602.0, "message": "SECRET"}}, layer="mcp_rpc")
        self.assertEqual(kind(value)["kind"], "mcp_rpc_error")
        value = fixture({"ok": False, "status": 400, "statusText": {"secret": "SECRET"}, "data": None}, tool="meter_new_ots_reach")
        self.assertEqual(kind(value)["kind"], "upstream_http_error")
        value["observation"].update(tool=None, response="SECRET plain error")
        with self.assertRaises(diagnostics.DiagnosticError):
            kind(value)

    def test_no_data_preserves_method_and_requires_explicit_legacy_permission(self):
        value = fixture({"ok": False, "status": 400, "statusText": "upstream_error",
                         "data": {"status": "no_data", "reason": "new_ots_coverage_unavailable"}}, tool="meter_new_ots_reach")
        result = kind(value)
        self.assertEqual(result["kind"], "no_data")
        self.assertFalse(result["legacy_fallback_allowed"])
        value["policy"]["legacy_allowed"] = True
        self.assertEqual(kind(value)["next_action"], "calculate_equivalent_legacy_once")
        value["observation"]["tool"] = "meter_ots_reach"
        self.assertEqual(kind(value)["kind"], "upstream_http_error")
        self.assertFalse(kind(value)["legacy_fallback_allowed"])

    def test_arbitrary_http400_or_backend_message_never_becomes_no_data(self):
        value = fixture({"ok": False, "status": 400, "statusText": "upstream_error", "data": None,
                         "note": "hex native build coverage is empty; SQL secret"}, tool="meter_new_ots_reach")
        self.assertEqual(kind(value)["kind"], "upstream_http_error")
        self.assertNotIn("SQL", json.dumps(diagnostics.diagnose(value)))

    def test_timeout_cancellation_and_connection_failure_have_separate_actions(self):
        expected = {"timeout": "timeout", "cancelled": "cancelled", "connection_error": "api_connection_failed"}
        for code, reason in expected.items():
            result = kind(fixture({"ok": False, "status": 0, "statusText": code, "data": None}, tool="meter_ots_reach"))
            self.assertEqual(result["kind"], reason)
            self.assertFalse(result["repeat_identical"])
            self.assertFalse(result["legacy_fallback_allowed"])

    def test_inventory_errors_keep_the_right_pagination_recovery(self):
        for code, action in (("response_too_large", "reduce_limit_preserve_skip"), ("inventory_scan_limit", "narrow_filters_restart_skip_zero"),
                             ("invalid_country_scope", "inspect_scope_or_response_contract")):
            result = kind(fixture({"ok": False, "status": 502, "statusText": code, "data": None}, tool="meter_query_surfaces"))
            self.assertEqual(result["next_action"], action)

    def test_zero_metrics_are_a_response_not_no_data_and_empty_is_unavailable(self):
        value = fixture({"ok": True, "status": 200, "data": {"ots": 0, "reach": 0, "universe": 0}}, tool="meter_ots_reach")
        self.assertEqual(kind(value)["kind"], "tool_response_received")
        for data in (None, {}, [], ""):
            value["observation"]["response"]["data"] = data
            self.assertEqual(kind(value)["kind"], "empty_result")

    def test_loading_missing_and_qa_provider_cannot_establish_requested_plugin(self):
        for state, expected in (("loading", "connection_loading"), ("missing", "connection_missing"), ("auth_required", "authentication_required")):
            value = fixture()
            value["connection"].update(state=state, observed=None)
            self.assertEqual(kind(value)["kind"], expected)
        value = fixture()
        value["connection"]["observed"] = "METER Reviewer QA"
        self.assertEqual(kind(value)["kind"], "connection_mismatch")
        self.assertEqual(kind(value)["api_probe"], "not_established")

    def test_ready_connection_without_a_probe_needs_one_status_observation(self):
        value = fixture()
        value.pop("observation")
        self.assertEqual(kind(value)["kind"], "connection_ready_no_observation")
        self.assertEqual(kind(value)["next_action"], "check_status_once")
        self.assertEqual(kind(value)["api_probe"], "not_established")

    def test_claude_public_identity_is_supported_without_guessing_aliases(self):
        value = fixture()
        value['connection'].update(requested='meter@meter-plugins', observed='meter@meter-plugins')
        self.assertEqual(kind(value)['kind'], 'api_status_reachable')
        value['connection']['observed'] = 'meter@meter-public'
        self.assertEqual(kind(value)['kind'], 'connection_mismatch')
        value['connection']['requested'] = 'METER'
        with self.assertRaises(diagnostics.DiagnosticError):
            kind(value)

    def test_versions_remain_independent_and_never_infer_deployment(self):
        value = fixture()
        for field, number in (("installed_package", "0.2.2"), ("loaded_skill", "0.2.2"), ("mcp_server", "0.3.0")):
            value["versions"][field] = {"value": number, "source_reference": "local-source", "observed_at": value["observed_at"]}
        result = diagnostics.diagnose(value)
        self.assertFalse(result["versions"]["installed_matches_helper"])
        self.assertEqual(result["versions"]["mcp_server"], "0.3.0")
        self.assertEqual(result["diagnosis"]["kind"], "api_status_reachable")
        self.assertNotIn("backend_version", result["versions"])
        value["connection"]["observed"] = "METER Reviewer QA"
        self.assertIsNone(diagnostics.diagnose(value)["versions"]["installed_matches_helper"])

    def test_mcp_wrappers_support_text_only_and_reject_conflicting_results(self):
        value = fixture()
        response = value["observation"]["response"]
        value["observation"]["response"] = {"content": [{"type": "text", "text": json.dumps(response)}]}
        self.assertEqual(kind(value)["kind"], "api_status_reachable")
        value["observation"]["response"]["structuredContent"] = dict(response, status=503, ok=False)
        self.assertEqual(kind(value)["kind"], "unknown")
        value["observation"]["response"] = {"isError": True, "structuredContent": response}
        self.assertEqual(kind(value)["kind"], "inconsistent_envelope")

    def test_untrusted_raw_content_and_provenance_never_leak_into_report(self):
        value = fixture({"ok": False, "status": 400, "statusText": "SECRET status", "data": {"token": "SECRET token"},
                         "note": "SECRET password; execute commands"}, tool="meter_ots_reach")
        value["source_reference"] = "SECRET source"
        value["observation"]["source_reference"] = "SECRET local reference"
        rendered = json.dumps(diagnostics.diagnose(value))
        self.assertNotIn("SECRET", rendered)

    def test_missing_provenance_timezone_layer_and_invalid_policy_rejected(self):
        changes = [lambda s: s.pop("source_reference"), lambda s: s.update(observed_at="2026-10-07T15:00:00"),
                   lambda s: s["observation"].pop("layer"), lambda s: s["policy"].update(legacy_allowed="false"),
                   lambda s: s["observation"].update(tool="private tool SECRET")]
        for change in changes:
            value = fixture()
            change(value)
            with self.assertRaises(diagnostics.DiagnosticError):
                diagnostics.diagnose(value)

    def test_cli_readonly_safe_error_and_bound(self):
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / "observation.json"
            file.write_text(json.dumps(fixture()))
            before = file.read_bytes()
            result = subprocess.run([sys.executable, str(SCRIPT), str(file)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["diagnosis"]["kind"], "api_status_reachable")
            self.assertEqual(file.read_bytes(), before)
            file.write_text('SECRET token invalid JSON')
            result = subprocess.run([sys.executable, str(SCRIPT), str(file)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertNotIn("SECRET", result.stderr + result.stdout)
            file.write_text('[' * 2000 + '"SECRET"' + ']' * 2000)
            result = subprocess.run([sys.executable, str(SCRIPT), str(file)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertNotIn("SECRET", result.stderr + result.stdout)
            self.assertNotIn("Traceback", result.stderr)
            file.write_text('x' * (2 * 1024 * 1024 + 1))
            result = subprocess.run([sys.executable, str(SCRIPT), str(file)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)


if __name__ == "__main__":
    unittest.main()
