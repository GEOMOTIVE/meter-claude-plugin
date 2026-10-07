"""Behavioral checks for whole-program selection and retained request integrity."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/meter/scripts/campaign-ledger.py"
spec = importlib.util.spec_from_file_location("campaign_ledger", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def fixture():
    return {
        "schema_version": 1,
        "brief": {
            "country": "Uzbekistan", "tool": "meter_ots_reach",
            "parameters": {
                "city": "Ташкент", "periodFrom": "2026-08-01", "periodTo": "2026-08-31",
                "audience": {"age_from": 18, "age_to": 55, "gender": "all", "income": "bc"},
                "blockSize": 0, "chrono": 10, "outputsInBlock": 1, "byDays": False,
                "impressions": [-1], "normalizeCoeff": 0.3, "reachModel": "nbd-dirichlet",
            },
            "objective": {"metric": "campaign_reach_n_plus", "frequency": 5},
            "constraints": {"max_surfaces": 80, "budget_limit": None, "currency": "UZS", "required_ids": [], "excluded_ids": []},
            "budget_mode": "estimate",
        },
        "inventory": {"eligible_ids": list(range(1, 101)), "coverage": "screened", "source_reference": "inventory.json"},
        "search": {"evaluation_limit": 40, "stop_reason": None},
        "scenarios": [], "final_scenario": None,
    }


def scenario(ledger, name, surface_ids, reach, cost=None, status="ok", purpose="search"):
    value = {
        "name": name, "tool": ledger["brief"]["tool"],
        "request": {**deepcopy(ledger["brief"]["parameters"]), "surfaces": surface_ids},
        "purpose": purpose, "status": status,
    }
    if status == "ok":
        value["result"] = {
            "scope": "campaign", "frequency": 5, "reach_fraction": reach, "universe": 1267819,
            "calculated_at": "2026-10-07T10:00:00+05:00", "source_reference": name + ".json",
        }
    elif status != "planned":
        value["failure"] = {"recorded_at": "2026-10-07T10:00:00+05:00", "source_reference": name + ".json"}
    if cost is not None:
        value["cost"] = {"amount": cost, "currency": "UZS", "status": "estimate"}
    ledger["scenarios"].append(value)
    return value


class CampaignLedgerTests(unittest.TestCase):
    def test_best_campaign_can_have_fewer_than_maximum_surfaces(self):
        ledger = fixture()
        scenario(ledger, "filled", list(range(1, 81)), 0.40, 100)
        scenario(ledger, "smaller", list(range(1, 73)), 0.41, 200)
        result = module.summarize(ledger)
        self.assertEqual(result["best"]["name"], "smaller")
        self.assertEqual(len(result["best"]["surface_ids"]), 72)
        self.assertAlmostEqual(result["best"]["reach_percent"], 41)
        self.assertAlmostEqual(result["best"]["projected_people"], 0.41 * 1267819)
        self.assertFalse(result["final_confirmed"])

    def test_all_submitted_optional_parameters_are_compared(self):
        mutations = [
            lambda s: s["request"]["audience"].update(income="abc"),
            lambda s: s["request"].update(periodTo="2026-08-30"),
            lambda s: s["request"].update(chrono=20),
            lambda s: s["request"].update(normalizeCoeff=0.8),
            lambda s: s["request"].update(extraFilter="new"),
            lambda s: s.update(tool="meter_new_ots_reach"),
        ]
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                ledger = fixture()
                mutate(scenario(ledger, "changed", [1, 2], 0.4))
                with self.assertRaises(module.LedgerError):
                    module.summarize(ledger)

    def test_rejects_per_surface_wrong_frequency_and_percent_as_fraction(self):
        for changes in ({"scope": "surface"}, {"frequency": 1}, {"reach_fraction": 40.7}, {"universe": 0}, {"reach_fraction": float("nan")}):
            with self.subTest(changes=changes):
                ledger = fixture()
                scenario(ledger, "invalid", [1, 2], 0.4)["result"].update(changes)
                with self.assertRaises(module.LedgerError):
                    module.summarize(ledger)

    def test_zero_reach_is_valid_but_no_data_is_not_zero(self):
        ledger = fixture()
        scenario(ledger, "zero", [1], 0)
        scenario(ledger, "unavailable", [2], None, status="no_data")
        scenario(ledger, "failed", [3], None, status="error")
        result = module.summarize(ledger)
        self.assertEqual(result["best"]["name"], "zero")
        self.assertEqual(result["failed_attempts"], 2)
        self.assertEqual(result["calculation_attempts"], 3)
        ledger["scenarios"][1]["result"] = {"reach_fraction": 0}
        with self.assertRaises(module.LedgerError):
            module.summarize(ledger)

    def test_constraints_reject_duplicate_unknown_missing_required_and_over_limit_ids(self):
        for values in ([1, 1], [101], list(range(1, 82)), []):
            with self.subTest(values=values):
                ledger = fixture()
                scenario(ledger, "invalid", values, 0.4)
                with self.assertRaises(module.LedgerError):
                    module.summarize(ledger)
        ledger = fixture()
        ledger["brief"]["constraints"]["required_ids"] = [3]
        scenario(ledger, "missing", [1, 2], 0.4)
        with self.assertRaises(module.LedgerError):
            module.summarize(ledger)
        ledger = fixture()
        ledger["brief"]["constraints"]["excluded_ids"] = [1]
        with self.assertRaises(module.LedgerError):
            module.summarize(ledger)

    def test_budget_cap_requires_matching_feasible_cost_and_preserves_estimate(self):
        for cost in (None, 101):
            ledger = fixture()
            ledger["brief"]["constraints"]["budget_limit"] = 100
            scenario(ledger, "over", [1], 0.4, cost)
            with self.assertRaises(module.LedgerError):
                module.summarize(ledger)
        ledger = fixture()
        ledger["brief"]["constraints"].update(max_surfaces=None, budget_limit=100)
        row = scenario(ledger, "feasible", [1], 0.4, 100)
        self.assertEqual(module.summarize(ledger)["best"]["cost"]["status"], "estimate")
        row["cost"]["currency"] = "USD"
        with self.assertRaises(module.LedgerError):
            module.summarize(ledger)

    def test_stable_identity_includes_audience_frequency_and_ordered_schedule(self):
        ledger = fixture()
        row = scenario(ledger, "base", [1, 2], 0.4)
        first = module.summarize(ledger)
        row["request"] = dict(reversed(list(row["request"].items())))
        self.assertEqual(first["request_keys"], module.summarize(ledger)["request_keys"])
        row["request"]["surfaces"].reverse()
        self.assertNotEqual(first["request_keys"], module.summarize(ledger)["request_keys"])
        row["request"]["surfaces"].reverse()
        ledger["brief"]["parameters"]["audience"]["income"] = "abc"
        row["request"]["audience"]["income"] = "abc"
        self.assertNotEqual(first["brief_id"], module.summarize(ledger)["brief_id"])
        ledger["brief"]["objective"]["frequency"] = 3
        row["result"]["frequency"] = 3
        self.assertNotEqual(first["brief_id"], module.summarize(ledger)["brief_id"])

    def test_latest_failed_attempt_is_not_recommended_and_planned_does_not_erase_result(self):
        ledger = fixture()
        scenario(ledger, "winner", [1, 2], 0.5)
        scenario(ledger, "other", [3], 0.4)
        scenario(ledger, "planned", [1, 2], None, status="planned")
        self.assertEqual(module.summarize(ledger)["best"]["name"], "winner")
        scenario(ledger, "retry", [1, 2], None, status="error")
        result = module.summarize(ledger)
        self.assertEqual(result["best"]["name"], "other")
        self.assertEqual(result["unique_rosters_attempted"], 2)
        self.assertEqual(result["unique_requests_attempted"], 2)
        self.assertEqual(result["calculation_attempts"], 3)

    def test_final_confirmation_uses_latest_exact_roster_and_result(self):
        ledger = fixture()
        scenario(ledger, "start", [1, 2], 0.5)
        scenario(ledger, "other", [3], 0.4)
        scenario(ledger, "final", [1, 2], 0.49, purpose="final_validation")
        ledger["search"]["stop_reason"] = "evaluation_budget"
        ledger["final_scenario"] = "final"
        result = module.summarize(ledger)
        self.assertTrue(result["final_confirmed"])
        self.assertEqual(result["best"]["name"], "final")
        self.assertEqual(result["search_calls"], 2)
        self.assertEqual(result["final_validation_calls"], 1)
        ledger["scenarios"][-1]["result"]["reach_fraction"] = 0.3
        with self.assertRaises(module.LedgerError):
            module.summarize(ledger)

    def test_failed_calls_count_towards_search_limit_but_final_is_separate(self):
        ledger = fixture()
        ledger["search"]["evaluation_limit"] = 1
        scenario(ledger, "valid", [1], 0.4)
        scenario(ledger, "final", [1], 0.4, purpose="final_validation")
        self.assertEqual(module.summarize(ledger)["calculation_attempts"], 2)
        scenario(ledger, "failure", [2], None, status="error")
        with self.assertRaises(module.LedgerError):
            module.summarize(ledger)

    def test_new_ots_broadcast_capacity_cannot_be_used_for_paid_campaign(self):
        ledger = fixture()
        brief = ledger["brief"]
        brief["tool"] = "meter_new_ots_reach_with_broadcast"
        p = brief["parameters"]
        audience = p.pop("audience")
        p.update(ageFrom=audience["age_from"], ageTo=audience["age_to"], gender="all", income="bc",
                 normalize_coeff=p.pop("normalizeCoeff"), broadcastRequest=0)
        p.pop("reachModel")
        with self.assertRaises(module.LedgerError):
            module.summarize(ledger)
        p["broadcastRequest"] = 1
        scenario(ledger, "campaign", [1, 2], 0.4)
        self.assertEqual(module.summarize(ledger)["methodology"], "new_ots")

    def test_preserves_targeted_gender_and_user_by_days_control(self):
        ledger = fixture()
        ledger["brief"]["parameters"]["audience"]["gender"] = "female"
        ledger["brief"]["parameters"]["byDays"] = True
        scenario(ledger, "targeted", [1], 0.4)
        self.assertIsNotNone(module.summarize(ledger)["best"])

    def test_cli_reads_artifact_without_modifying_it_and_reports_invalid_json(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "campaign.json"
            ledger = fixture()
            scenario(ledger, "valid", [1], 0.4077552229)
            path.write_text(json.dumps(ledger, ensure_ascii=False), encoding="utf-8")
            before = path.read_bytes()
            result = subprocess.run([sys.executable, str(SCRIPT), str(path)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertAlmostEqual(json.loads(result.stdout)["best"]["reach_percent"], 40.77552229)
            self.assertEqual(path.read_bytes(), before)
            path.write_text("{}")
            invalid = subprocess.run([sys.executable, str(SCRIPT), str(path)], capture_output=True, text=True)
            self.assertEqual(invalid.returncode, 2)
            self.assertNotIn("Traceback", invalid.stderr)


if __name__ == "__main__":
    unittest.main()
