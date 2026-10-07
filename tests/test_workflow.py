"""Cross-helper task regressions with synthetic inventory, prices and media results.

METER_WORKFLOW_SKILL_DIRECTORY selects an extracted/installed skill explicitly.
No live calculation, source-response authentication or XLSX authoring is claimed.
"""
from copy import deepcopy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SKILL = Path(os.environ.get("METER_WORKFLOW_SKILL_DIRECTORY", ROOT / "skills/meter"))


def helper(name):
    spec = importlib.util.spec_from_file_location("workflow_" + name, SKILL / "scripts" / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


campaign = helper("campaign-ledger")
budget = helper("inventory-budget")
export = helper("prepare-export")
diagnostics = helper("diagnose")
STAMP = "2026-10-07T15:00:00+05:00"


def fixture():
    """Price three complete programs, retain a failed attempt and validate the winner."""
    parameters = {
        "city": "Ташкент", "periodFrom": "2026-08-01", "periodTo": "2026-08-31",
        "audience": {"age_from": 18, "age_to": 55, "gender": "all", "income": "bc"},
        "blockSize": 0, "chrono": 10, "outputsInBlock": 1, "byDays": False,
        "impressions": [-1], "normalizeCoeff": 0.3, "reachModel": "nbd-dirichlet",
    }
    records = [{"id": i, "city": "Ташкент", "country": "Uzbekistan",
                "address": f"Тестовый адрес {i}", "type": "LED" if i == 80 else "Billboard",
                "isDigital": i == 80, "dimension": "3x6", "side": "A",
                "lat": 41.25 + (i % 8) * 0.01, "lng": 69.20 + (i // 8) * 0.01}
               for i in range(1, 81)]
    records[2].update(lat=records[1]["lat"], lng=records[1]["lng"], side="B")
    records += [{"id": 2, "description": "Видимость ограничена деревьями"},
                {**records[0], "id": 81, "active": False, "description": "демонтирован"},
                {**records[0], "id": 82, "type": "Mediafacade", "isDigital": False}]
    rules = []
    for media_class, kind in (("static", "Billboard"), ("digital", "LED")):
        for component, rate in (("media", 1000000 if media_class == "static" else 2000000),
                                ("production", 360000 if media_class == "static" else 0),
                                ("installation", 100000 if media_class == "static" else 0)):
            rule = {"component": component, "currency": "UZS", "unit": "surface_month" if component == "media" else "surface",
                    "match": {"media_class": media_class, "type": kind, "dimension": "3x6"},
                    "amounts": {"low": str(rate), "base": str(rate), "high": str(rate)}, "status": "estimate",
                    "basis": "Synthetic regression assumption; not an operator quote",
                    "source_reference": "synthetic-prices.json", "as_of": "2026-07-01",
                    "valid_from": "2026-08-01", "valid_to": "2026-08-31", "proration": "calendar_days"}
            if media_class == "digital" and component == "media":
                rule["priced_controls"] = {k: deepcopy(parameters[k]) for k in ("chrono", "blockSize", "outputsInBlock", "impressions")}
            rules.append(rule)
    model = {"schema_version": 1, "inventory_source_reference": "synthetic-inventory.json",
             "model_source_reference": "synthetic-prices.json", "dimension_unit": "m", "records": records,
             "campaign": {"parameters": deepcopy(parameters), "currency": "UZS", "money_decimals": 2},
             "selected_ids": [], "required_components": ["media", "production", "installation"],
             "price_rules": rules, "extras": [{"component": "reserve", "currency": "UZS", "unit": "fraction",
                 "applies_to": ["media", "production", "installation"], "amounts": {"low": "0.1", "base": "0.1", "high": "0.1"},
                 "status": "estimate", "source_reference": "synthetic-prices.json", "basis": "Synthetic regression reserve"}]}
    # Discover the pool before a roster exists; a reserve has no priced base yet.
    normalized = budget.calculate({**model, "extras": []})
    ledger = {"schema_version": 1,
              "brief": {"country": "Uzbekistan", "tool": "meter_ots_reach", "parameters": parameters,
                        "objective": {"metric": "campaign_reach_n_plus", "frequency": 5},
                        "constraints": {"max_surfaces": 80, "budget_limit": None, "currency": "UZS", "required_ids": [], "excluded_ids": [81, 82]},
                        "budget_mode": "estimate"},
              "inventory": {"eligible_ids": normalized["eligible_ids"], "coverage": "screened", "source_reference": "synthetic-inventory.json"},
              "search": {"evaluation_limit": 4, "stop_reason": "evaluation_budget"}, "scenarios": [], "final_scenario": None}
    for name, ids, reach in (("filled80", list(range(1, 81)), 0.41),
                             ("smaller79", list(range(2, 81)), 0.42),
                             ("economy60", list(range(1, 61)), 0.39)):
        priced = budget.calculate({**model, "selected_ids": ids})
        ledger["scenarios"].append({"name": name, "tool": "meter_ots_reach", "purpose": "search", "status": "ok",
            "request": {**deepcopy(parameters), "surfaces": ids}, "cost": priced["ledger_cost"],
            "result": {"scope": "campaign", "frequency": 5, "reach_fraction": reach, "universe": 1267819,
                       "calculated_at": STAMP, "source_reference": name + "-synthetic-response.json"}})
    ledger["scenarios"].append({"name": "failed78", "tool": "meter_ots_reach", "purpose": "search", "status": "error",
        "request": {**deepcopy(parameters), "surfaces": list(range(1, 79))},
        "failure": {"recorded_at": STAMP, "source_reference": "synthetic-timeout.json"}})
    winner = campaign.summarize(ledger)["best"]
    final = deepcopy(next(s for s in ledger["scenarios"] if s["name"] == winner["name"]))
    final.update(name="final79", purpose="final_validation")
    final["result"].update(universe=1300000, source_reference="final79-synthetic-response.json")
    ledger["scenarios"].append(final)
    ledger["final_scenario"] = "final79"
    model["selected_ids"] = list(final["request"]["surfaces"])
    return ledger, model


class WorkflowTests(unittest.TestCase):
    def test_selection_budget_and_export_share_final_program_and_own_universe(self):
        ledger, model = fixture()
        summary = campaign.summarize(ledger)
        bundle = export.prepare(ledger, model)
        self.assertEqual(summary["best"]["surface_ids"], list(range(2, 81)))
        self.assertTrue(summary["final_confirmed"])
        self.assertEqual(summary["search_calls"], 4)
        self.assertEqual(summary["final_validation_calls"], 1)
        self.assertEqual(summary["failed_attempts"], 1)
        self.assertEqual(summary["best"]["projected_people"], 546000)
        self.assertEqual(bundle["result"]["universe"], 1300000)
        self.assertEqual(bundle["budget"]["total"]["base"], "127468000.00")
        self.assertEqual(bundle["budget"]["ledger_cost"], ledger["scenarios"][-1]["cost"])
        self.assertEqual([r["id"] for r in bundle["rows"]], model["selected_ids"])
        self.assertEqual([r["seq"] for r in bundle["rows"]], list(range(1, 80)))
        self.assertIn("Видимость ограничена деревьями", bundle["rows"][0]["warnings"])
        self.assertEqual(bundle["rows"][-1]["media_class"], "digital")
        normalized = budget.calculate(model)
        self.assertEqual(normalized["excluded_ids"], [81, 82])
        self.assertEqual(len(normalized["eligible_ids"]), 80)

    def test_new_process_followups_reuse_state_without_adding_calculation_attempts(self):
        ledger, model = fixture()
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            ledger_file, model_file = base / "ledger.json", base / "model.json"
            ledger_file.write_text(json.dumps(ledger, ensure_ascii=False))
            model_file.write_text(json.dumps(model, ensure_ascii=False))
            original = {p: p.read_bytes() for p in (ledger_file, model_file)}
            summaries = []
            for turn in range(2):
                result = subprocess.run([sys.executable, str(SKILL / "scripts/campaign-ledger.py"), str(ledger_file)], capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                summaries.append(json.loads(result.stdout))
                output = base / f"followup-{turn}"
                result = subprocess.run([sys.executable, str(SKILL / "scripts/prepare-export.py"), str(ledger_file), str(model_file), str(output)], capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                bundle = json.loads((output / "export.json").read_text())
                self.assertEqual(bundle["brief"]["parameters"], ledger["brief"]["parameters"])
                self.assertEqual(bundle["result"], ledger["scenarios"][-1]["result"])
                self.assertEqual(bundle["map"]["unmapped_ids"], model["selected_ids"])
            self.assertEqual(summaries[0], summaries[1])
            self.assertEqual(summaries[1]["calculation_attempts"], 5)
            for path, content in original.items():
                self.assertEqual(path.read_bytes(), content)

    def test_repricing_requires_new_bound_cost_but_keeps_exact_media_result(self):
        ledger, model = fixture()
        before = campaign.summarize(ledger)
        media_result = deepcopy(ledger["scenarios"][-1]["result"])
        model["price_rules"][0]["amounts"] = {k: "1500000" for k in ("low", "base", "high")}
        model["model_source_reference"] = "repriced-synthetic-prices.json"
        model["price_rules"][0]["source_reference"] = model["model_source_reference"]
        with self.assertRaisesRegex(ValueError, "budget differs"):
            export.prepare(ledger, model)
        ledger["scenarios"][-1]["cost"] = budget.calculate(model)["ledger_cost"]
        bundle = export.prepare(ledger, model)
        after = campaign.summarize(ledger)
        self.assertEqual(bundle["result"], media_result)
        for key in ("comparison_id", "request_keys", "calculation_attempts", "final_validation_calls"):
            self.assertEqual(after[key], before[key])
        self.assertGreater(after["best"]["cost"]["amount"], before["best"]["cost"]["amount"])
        self.assertEqual(bundle["budget"]["ledger_cost"]["source_reference"], "repriced-synthetic-prices.json")

    def test_completed_budget_must_be_bound_in_retained_final_state(self):
        ledger, model = fixture()
        media_result = deepcopy(ledger["scenarios"][-1]["result"])
        ledger["scenarios"][-1].pop("cost")
        with self.assertRaisesRegex(ValueError, "bind the complete budget"):
            export.prepare(ledger, model)
        ledger["scenarios"][-1]["cost"] = budget.calculate(model)["ledger_cost"]
        bundle = export.prepare(ledger, model)
        self.assertEqual(bundle["result"], media_result)
        self.assertEqual(bundle["summary"]["best"]["cost"], bundle["budget"]["ledger_cost"])
        self.assertNotIn("Requested budget is not yet available.", bundle["limitations"])

    def test_changed_frequency_or_spending_cap_cannot_relabel_old_selection(self):
        ledger, model = fixture()
        ledger["brief"]["objective"]["frequency"] = 1
        with self.assertRaisesRegex(ValueError, "wrong Reach frequency"):
            export.prepare(ledger, model)
        ledger, model = fixture()
        ledger["brief"]["constraints"]["budget_limit"] = 100000000
        with self.assertRaisesRegex(ValueError, "spending cap exceeded"):
            export.prepare(ledger, model)

    def test_changed_inputs_cannot_relabel_retained_results(self):
        changes = [lambda p: p["audience"].update(income="abc"), lambda p: p.update(periodTo="2026-08-30"),
                   lambda p: p.update(chrono=20), lambda p: p.update(impressions=[10]), lambda p: p.update(normalizeCoeff=0.5)]
        for change in changes:
            ledger, model = fixture()
            change(ledger["brief"]["parameters"])
            with self.subTest(change=change), self.assertRaisesRegex(ValueError, "submitted parameters differ"):
                export.prepare(ledger, model)
        ledger, model = fixture()
        ledger["brief"]["tool"] = "meter_new_ots_reach"
        ledger["brief"]["parameters"].update(ageFrom=18, ageTo=55, gender="all", income="bc", normalize_coeff=0.3)
        with self.assertRaisesRegex(ValueError, "mixed calculation tools"):
            campaign.summarize(ledger)

    def test_failed_latest_final_blocks_export_and_retains_earlier_checkpoint(self):
        ledger, model = fixture()
        checkpoint = deepcopy(ledger["scenarios"][-1])
        failed = deepcopy(checkpoint)
        failed.update(name="final-timeout", status="error")
        failed.pop("result")
        failed["failure"] = {"recorded_at": STAMP, "source_reference": "synthetic-final-timeout.json"}
        ledger["scenarios"].append(failed)
        with self.assertRaises(ValueError):
            export.prepare(ledger, model)
        self.assertEqual(ledger["scenarios"][-2], checkpoint)
        snapshot = {"schema_version": 1, "observed_at": STAMP, "source_reference": "synthetic-client-observation",
            "connection": {"requested": "meter@meter-public", "observed": "meter@meter-public", "state": "ready"},
            "observation": {"observed_at": STAMP, "source_reference": failed["failure"]["source_reference"],
                "layer": "tool_result", "tool": "meter_ots_reach",
                "response": {"ok": False, "status": 0, "statusText": "timeout", "data": None}}}
        diagnosis = diagnostics.diagnose(snapshot)["diagnosis"]
        self.assertEqual(diagnosis["kind"], "timeout")
        self.assertFalse(diagnosis["repeat_identical"])

    def test_missing_coordinates_and_prices_preserve_media_roster_and_result(self):
        ledger, model = fixture()
        model["records"][1].pop("lat")
        model["price_rules"] = [r for r in model["price_rules"] if r["component"] != "installation"]
        ledger["scenarios"][-1].pop("cost")
        bundle = export.prepare(ledger, model)
        self.assertEqual(len(bundle["rows"]), 79)
        self.assertIsNone(bundle["rows"][0]["coordinates"])
        self.assertEqual(bundle["result"]["reach_fraction"], 0.42)
        self.assertFalse(bundle["budget"]["budget_complete"])
        self.assertIsNone(bundle["budget"]["total"])
        self.assertIsNone(bundle["budget"]["ledger_cost"])
        self.assertEqual(len(bundle["budget"]["missing_costs"]), 79)
        self.assertEqual(bundle["budget"]["components"]["reserve"]["base"], "10808000.00")
        for dependency in ("creative", "reserve"):
            model["extras"][0]["applies_to"] = [dependency]
            with self.subTest(dependency=dependency), self.assertRaisesRegex(ValueError, "fraction base"):
                export.prepare(ledger, model)

    def test_per_surface_result_or_reordered_pricing_cannot_substantiate_export(self):
        ledger, model = fixture()
        ledger["scenarios"][-1]["result"]["scope"] = "surface"
        with self.assertRaisesRegex(ValueError, "not campaign Reach"):
            export.prepare(ledger, model)
        ledger, model = fixture()
        model["selected_ids"].reverse()
        with self.assertRaisesRegex(ValueError, "roster/order differs"):
            export.prepare(ledger, model)

    def test_no_known_prices_keeps_fraction_unavailable_and_never_a_zero_total(self):
        ledger, model = fixture()
        model["price_rules"] = []
        ledger["scenarios"][-1].pop("cost")
        bundle = export.prepare(ledger, model)
        self.assertIsNone(bundle["budget"]["total"])
        self.assertIsNone(bundle["budget"]["ledger_cost"])
        self.assertEqual(bundle["budget"]["line_items"], [])
        self.assertEqual(bundle["budget"]["known_subtotal"]["base"], "0.00")
        self.assertIn({"id": None, "component": "reserve", "reason": "missing_fraction_base_rates"}, bundle["budget"]["missing_costs"])

    def test_rekeying_json_objects_keeps_request_identity_but_id_order_does_not(self):
        ledger, model = fixture()
        before = campaign.summarize(ledger)
        ledger = json.loads(json.dumps(ledger, sort_keys=True))
        self.assertEqual(campaign.summarize(ledger)["request_keys"], before["request_keys"])
        ledger["scenarios"][-1]["request"]["surfaces"].reverse()
        ledger["scenarios"][-1]["cost"]["surface_ids"].reverse()
        after = campaign.summarize(ledger)
        self.assertNotEqual(after["request_keys"]["final79"], before["request_keys"]["final79"])
        self.assertEqual(after["unique_rosters_attempted"], before["unique_rosters_attempted"])


if __name__ == "__main__":
    unittest.main()
