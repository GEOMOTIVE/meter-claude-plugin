"""Inventory quality, explicit billing models and campaign-cost binding."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load(name, file):
    spec = importlib.util.spec_from_file_location(name, ROOT / "skills/meter/scripts" / file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


budget = load("inventory_budget", "inventory-budget.py")
ledger = load("campaign_ledger", "campaign-ledger.py")


def fixture():
    return {
        "schema_version": 1, "inventory_source_reference": "inventory.json", "model_source_reference": "budget-model.json", "dimension_unit": "m",
        "campaign": {"currency": "UZS", "parameters": {
            "city": "Ташкент", "periodFrom": "2026-08-01", "periodTo": "2026-08-31",
            "audience": {"age_from": 18, "age_to": 55, "gender": "all", "income": "bc"},
            "blockSize": 0, "chrono": 10, "outputsInBlock": 1, "byDays": False,
            "impressions": [-1], "normalizeCoeff": 0.3, "reachModel": "nbd-dirichlet",
        }},
        "records": [
            {"id": 1, "isDigital": 0, "type": "Billboard", "dimension": "3x6", "lat": 41.3, "lng": 69.2, "description": "not dismantled"},
            {"id": 2, "is_digital": "false", "type": "Billboard", "dimension": "3х6", "lat": None, "lng": None},
        ],
        "selected_ids": [1, 2], "required_components": ["media"],
        "price_rules": [{
            "match": {"media_class": "static", "type": "Billboard", "dimension": "3x6"},
            "component": "media", "unit": "surface_month", "proration": "calendar_days",
            "amounts": {"low": "100", "base": "120", "high": "150"}, "status": "estimate", "currency": "UZS",
            "valid_from": "2026-08-01", "valid_to": "2026-08-31", "as_of": "2026-07-01",
            "source_reference": "synthetic-model.json", "basis": "Illustrative test assumptions, not a tariff",
        }], "extras": [],
    }


class InventoryBudgetTests(unittest.TestCase):
    def test_preselection_keeps_fraction_model_and_never_binds_an_empty_total(self):
        model = fixture()
        model["selected_ids"] = []
        model["extras"] = [{"component": "reserve", "unit": "fraction", "applies_to": ["media"],
                            "amounts": dict.fromkeys(("low", "base", "high"), "0.15"), "currency": "UZS", "status": "estimate",
                            "basis": "Illustrative reserve", "source_reference": "test-assumptions.json"}]
        before = deepcopy(model)
        output = budget.calculate(model)
        self.assertEqual(output["eligible_ids"], [1, 2])
        self.assertFalse(output["budget_complete"])
        self.assertIsNone(output["total"])
        self.assertIsNone(output["ledger_cost"])
        self.assertIn({"id": None, "component": "reserve", "reason": "missing_fraction_base_rates"}, output["missing_costs"])
        self.assertEqual(model, before)
        for dependency in ("creative", "reserve", "unknown"):
            model["extras"][0]["applies_to"] = [dependency]
            with self.subTest(dependency=dependency), self.assertRaisesRegex(ValueError, "fraction base"):
                budget.calculate(model)

    def test_conflicting_or_malformed_country_codes_block_selection(self):
        for code in ("KZ", "Uzbekistan"):
            model = fixture()
            model["records"][0]["cntry"] = "UZ"
            model["records"].append({"id": 1, "cntry": code})
            with self.subTest(code=code), self.assertRaises(budget.ModelError):
                budget.calculate(model)

    def test_camel_snake_flags_and_missing_map_data_preserve_two_eligible_ids(self):
        output = budget.calculate(fixture())
        self.assertEqual(output["eligible_ids"], [1, 2])
        self.assertEqual(output["rows"][1]["media_class"], "static")
        self.assertIsNone(output["rows"][1]["coordinates"])
        self.assertEqual(output["rows"][0]["availability"], "unconfirmed")
        self.assertEqual(output["total"], {"low": "200.00", "base": "240.00", "high": "300.00"})

    def test_distinct_sides_at_same_coordinates_are_not_deduplicated(self):
        model = fixture()
        model["records"][1].update(lat=41.3, lng=69.2, side="B")
        self.assertEqual(len(budget.calculate(model)["rows"]), 2)

    def test_duplicate_ids_retain_all_sources_and_complementary_metadata(self):
        model = fixture()
        model["records"].append({"id": "001", "is_digital": False, "address": "Sourced address"})
        output = budget.calculate(model)
        self.assertEqual(output["eligible_ids"], [1, 2])
        self.assertEqual(len(output["rows"][0]["source_records"]), 2)
        self.assertEqual(output["rows"][0]["metadata"]["address"], "Sourced address")

    def test_dismantled_inactive_and_invalid_flags_cannot_enter_selection(self):
        for changes in ({"description": "Демонтирован"}, {"status": "inactive"}, {"isActive": "0"}, {"isDigital": "unknown"}):
            with self.subTest(changes=changes):
                model = fixture()
                model["records"][0].update(changes)
                with self.assertRaises(budget.ModelError):
                    budget.calculate(model)

    def test_mediafacade_false_flag_requires_source_backed_classification(self):
        model = fixture()
        model["records"][0]["type"] = "Mediafacade"
        model["selected_ids"] = []
        output = budget.calculate(model)
        row = output["rows"][0]
        self.assertEqual(row["status"], "requires_review")
        self.assertIn("ambiguous_mediafacade_classification", row["review_reasons"])
        model["classification_overrides"] = [{"id": 1, "media_class": "static", "source_reference": "surface-card.json", "reason": "Sourced confirmation of printed static face"}]
        output = budget.calculate(model)
        self.assertTrue(output["rows"][0]["planning_eligible"])
        self.assertEqual(output["rows"][0]["source_records"][0]["isDigital"], 0)
        self.assertIn("classification_resolved", " ".join(output["rows"][0]["warnings"]))

    def test_classification_override_does_not_erase_dismantled_or_format_conflicts(self):
        model = fixture()
        model["records"].append({"id": 1, "isDigital": 1, "dimension": "6x3", "description": "демонтирована"})
        model["selected_ids"] = []
        model["classification_overrides"] = [{"id": 1, "media_class": "static", "source_reference": "classification.json", "reason": "Test resolution"}]
        row = budget.calculate(model)["rows"][0]
        self.assertFalse(row["planning_eligible"])
        self.assertIn("conflicting_metadata:dimension", row["review_reasons"])
        self.assertIn("демонтирована", row["warnings"])

    def test_invalid_or_conflicting_coordinates_make_map_partial_without_dropping_id(self):
        for coordinate in ("unknown", 1000):
            model = fixture()
            model["records"][0]["lat"] = coordinate
            output = budget.calculate(model)
            self.assertIn(1, output["eligible_ids"])
            self.assertIsNone(output["rows"][0]["coordinates"])
        model = fixture()
        model["records"].append({"id": 1, "lat": 41.5, "lng": 69.2})
        output = budget.calculate(model)
        self.assertIn(1, output["eligible_ids"])
        self.assertIsNone(output["rows"][0]["coordinates"])

    def test_inclusive_days_and_leap_year_calendar_proration(self):
        from datetime import date
        from decimal import Decimal
        self.assertEqual(budget.month_quantity(date(2024, 2, 1), date(2024, 2, 29)), Decimal(1))
        model = fixture()
        model["campaign"]["parameters"].update(periodFrom="2026-08-15", periodTo="2026-08-31")
        rule = model["price_rules"][0]
        rule["amounts"] = dict.fromkeys(("low", "base", "high"), "310")
        self.assertEqual(budget.calculate(model)["total"]["base"], "340.00")
        rule["unit"] = "surface_day"
        rule["amounts"] = dict.fromkeys(("low", "base", "high"), "10")
        self.assertEqual(budget.calculate(model)["total"]["base"], "340.00")

    def test_decimal_area_costs_components_and_explicit_reserve_base(self):
        model = fixture()
        model["required_components"].append("production")
        rule = deepcopy(model["price_rules"][0])
        rule.update(component="production", unit="m2", amounts=dict.fromkeys(("low", "base", "high"), "0.10"))
        model["price_rules"].append(rule)
        model["extras"] = [{"component": "reserve", "unit": "fraction", "applies_to": ["media", "production"],
                            "amounts": dict.fromkeys(("low", "base", "high"), "0.15"), "currency": "UZS", "status": "estimate",
                            "basis": "Illustrative reserve, not tax", "source_reference": "test-assumptions.json"}]
        output = budget.calculate(model)
        self.assertEqual(output["components"]["production"]["base"], "3.60")
        self.assertEqual(output["components"]["reserve"]["base"], "36.54")
        self.assertEqual(output["total"]["base"], "280.14")
        self.assertIn("tax", output["not_included_components"])
        self.assertEqual(output["budget_status"], "estimate")

    def test_missing_rates_and_required_components_return_partial_not_zero_total(self):
        model = fixture()
        model["records"][1]["dimension"] = "4x8"
        model["required_components"].append("installation")
        output = budget.calculate(model)
        self.assertFalse(output["budget_complete"])
        self.assertIsNone(output["total"])
        self.assertIsNone(output["ledger_cost"])
        self.assertEqual(output["known_subtotal"]["base"], "120.00")
        self.assertIn({"id": 2, "component": "media", "reason": "no_matching_rate"}, output["missing_costs"])
        self.assertIn({"id": 1, "component": "installation", "reason": "no_matching_rate"}, output["missing_costs"])

    def test_price_currency_period_and_exact_campaign_package_are_checked(self):
        for changes in ({"currency": "USD"}, {"valid_to": "2026-08-30"}, {"unit": "campaign", "valid_from": "2026-07-01"}, {"proration": None}):
            model = fixture()
            model["price_rules"][0].update(changes)
            with self.assertRaises(budget.ModelError):
                budget.calculate(model)

    def test_confirmed_quotes_require_exact_id_type_format_and_fixed_amount(self):
        model = fixture()
        rule = model["price_rules"][0]
        rule["status"] = "confirmed"
        with self.assertRaises(budget.ModelError):
            budget.calculate(model)
        rule["match"]["id"] = 1
        rule["amounts"] = dict.fromkeys(("low", "base", "high"), "100")
        model["selected_ids"] = [1]
        self.assertEqual(budget.calculate(model)["budget_status"], "confirmed")
        rule["match"]["dimension"] = "*"
        with self.assertRaises(budget.ModelError):
            budget.calculate(model)

    def test_digital_prices_require_matching_paid_schedule_and_never_use_static_rate(self):
        model = fixture()
        model["records"][0].update(isDigital=1, type="LED")
        model["selected_ids"] = [1]
        self.assertFalse(budget.calculate(model)["budget_complete"])
        rule = model["price_rules"][0]
        rule["match"].update(media_class="digital", type="LED")
        with self.assertRaises(budget.ModelError):
            budget.calculate(model)
        p = model["campaign"]["parameters"]
        p.update(blockSize=120, broadcastRequest=1)
        rule["priced_controls"] = {k: p[k] for k in budget.CONTROL_FIELDS & p.keys()}
        self.assertTrue(budget.calculate(model)["budget_complete"])
        p["broadcastRequest"] = 0
        rule["priced_controls"]["broadcastRequest"] = 0
        with self.assertRaises(budget.ModelError):
            budget.calculate(model)
        p["broadcastRequest"] = 1
        rule["priced_controls"]["broadcastRequest"] = 1
        rule["priced_controls"]["outputsInBlock"] = 2
        with self.assertRaises(budget.ModelError):
            budget.calculate(model)

    def test_exact_quote_overrides_model_but_ambiguous_rates_are_rejected(self):
        model = fixture()
        quote = deepcopy(model["price_rules"][0])
        quote["match"]["id"] = 1
        quote.update(status="confirmed", amounts=dict.fromkeys(("low", "base", "high"), "90"))
        model["price_rules"].append(quote)
        output = budget.calculate(model)
        self.assertEqual(output["total"]["base"], "210.00")
        self.assertEqual(output["budget_status"], "estimate")
        model["price_rules"].append(deepcopy(quote))
        with self.assertRaises(budget.ModelError):
            budget.calculate(model)

    def test_conflicting_exact_id_price_is_not_hidden_by_estimated_fallback(self):
        model = fixture()
        quote = deepcopy(model["price_rules"][0])
        quote["match"].update(id=1, media_class="digital")
        model["price_rules"].append(quote)
        with self.assertRaises(budget.ModelError):
            budget.calculate(model)

    def test_unknown_dimensions_units_never_become_square_metres(self):
        model = fixture()
        model["dimension_unit"] = "unknown"
        production = deepcopy(model["price_rules"][0])
        production.update(component="production", unit="m2")
        model["price_rules"].append(production)
        model["required_components"].append("production")
        output = budget.calculate(model)
        self.assertIsNone(output["rows"][0]["area_m2"])
        self.assertFalse(output["budget_complete"])
        model = fixture()
        model["records"][0]["dimension_unit"] = "px"
        output = budget.calculate(model)
        self.assertIsNone(output["rows"][0]["area_m2"])
        self.assertFalse(output["budget_complete"])

    def test_budget_is_bound_to_exact_campaign_roster_and_parameters(self):
        model = fixture()
        cost = budget.calculate(model)["ledger_cost"]
        parameters = model["campaign"]["parameters"]
        campaign = {"schema_version": 1, "brief": {
            "country": "Uzbekistan", "tool": "meter_ots_reach", "parameters": parameters,
            "objective": {"metric": "campaign_reach_n_plus", "frequency": 5}, "budget_mode": "estimate",
            "constraints": {"max_surfaces": 80, "budget_limit": None, "currency": "UZS", "required_ids": [], "excluded_ids": []}},
            "inventory": {"eligible_ids": [1, 2], "coverage": "screened", "source_reference": "inventory.json"},
            "search": {"evaluation_limit": 40, "stop_reason": None}, "scenarios": [{
                "name": "program", "tool": "meter_ots_reach", "request": {**parameters, "surfaces": [1, 2]},
                "purpose": "search", "status": "ok", "cost": cost,
                "result": {"scope": "campaign", "frequency": 5, "reach_fraction": 0.4, "universe": 1000,
                           "calculated_at": "2026-10-07T10:00:00+05:00", "source_reference": "synthetic-result.json"}}]}
        self.assertEqual(ledger.summarize(campaign)["best"]["cost"]["amount"], 240)
        cost["surface_ids"] = [1]
        with self.assertRaises(ledger.LedgerError):
            ledger.summarize(campaign)
        cost["surface_ids"] = [1, 2]
        cost["campaign_parameters"] = deepcopy(parameters)
        cost["campaign_parameters"]["chrono"] = 20
        with self.assertRaises(ledger.LedgerError):
            ledger.summarize(campaign)

    def test_cli_is_readonly_and_does_not_create_a_tariff_when_prices_are_missing(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "budget.json"
            model = fixture()
            model["price_rules"] = []
            path.write_text(json.dumps(model), encoding="utf-8")
            original = path.read_bytes()
            result = subprocess.run([sys.executable, str(ROOT / "skills/meter/scripts/inventory-budget.py"), str(path)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIsNone(json.loads(result.stdout)["total"])
            self.assertEqual(path.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
