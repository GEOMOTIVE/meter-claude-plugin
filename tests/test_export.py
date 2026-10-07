"""Export identity, partial-data handling, local-map coverage and saved-file checks."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

from PIL import Image
from test_campaign_ledger import fixture as ledger_fixture, scenario
from test_inventory_budget import fixture as inventory_fixture, load, budget

export = load("prepare_export", "prepare-export.py")
verify = load("verify_export", "verify-export.py")


def fixture():
    model = inventory_fixture()
    ledger = ledger_fixture()
    ledger["search"]["stop_reason"] = "Test evaluation limit"
    final = scenario(ledger, "final", [1, 2], 0.4, purpose="final_validation")
    final["cost"] = budget.calculate(model)["ledger_cost"]
    ledger["final_scenario"] = "final"
    return ledger, model


def tile_spec(directory):
    return {"projection": "web_mercator_tiles", "zoom": 12, "tile_directory": str(directory),
            "attribution": "Synthetic test grid, not a city basemap", "source_reference": "test-only tiles"}


def write_tiles(directory, groups, zoom=12):
    x0, y0, x1, y1 = export.panel_bounds(groups, 1100 / 720)
    import math
    for x in range(math.floor(x0 / 256), math.floor(x1 / 256) + 1):
        for y in range(math.floor(y0 / 256), math.floor(y1 / 256) + 1):
            Image.new("RGB", (256, 256), "#DDDDDD").save(directory / f"{zoom}_{x}_{y}.png")


class ExportPreparationTests(unittest.TestCase):
    def test_localized_country_names_use_retained_iso_identity(self):
        ledger, model = fixture()
        ledger["brief"]["parameters"]["countryCode"] = "UZ"
        model["campaign"]["parameters"]["countryCode"] = "UZ"
        for s in ledger["scenarios"]:
            s["request"]["countryCode"] = "UZ"
        for record in model["records"]:
            record.update(country="Узбекистан", cntry="UZ")
        ledger["scenarios"][0]["cost"] = budget.calculate(model)["ledger_cost"]
        bundle = export.prepare(ledger, model)
        self.assertEqual(bundle["rows"][0]["metadata"]["country"], "Узбекистан")
        self.assertEqual(bundle["rows"][0]["metadata"]["cntry"], "UZ")
        model["records"][0].update(country="Uzbekistan", cntry="KZ")
        with self.assertRaisesRegex(ValueError, "country code differs"):
            export.prepare(ledger, model)

    def test_wrong_country_names_without_iso_evidence_are_rejected(self):
        ledger, model = fixture()
        model["records"][0]["country"] = "Kazakhstan"
        with self.assertRaisesRegex(ValueError, "country differs"):
            export.prepare(ledger, model)

    def test_single_source_order_and_final_campaign_result(self):
        ledger, model = fixture()
        bundle = export.prepare(ledger, model)
        self.assertEqual([r["id"] for r in bundle["rows"]], [1, 2])
        self.assertEqual([r["seq"] for r in bundle["rows"]], [1, 2])
        self.assertEqual(bundle["result"]["reach_fraction"], 0.4)
        self.assertIsNone(bundle["rows"][1]["coordinates"])
        self.assertEqual(bundle["budget"]["total"]["base"], "240.00")
        self.assertNotIn("rows", bundle["budget"], "do not duplicate the raw inventory pool into exports")

    def test_unvalidated_final_wrong_roster_order_parameters_currency_or_city_rejected(self):
        changes = [
            lambda l, m: l.update(final_scenario=None),
            lambda l, m: m.update(selected_ids=[2, 1]),
            lambda l, m: m["campaign"]["parameters"].update(chrono=20),
            lambda l, m: m["campaign"].update(currency="USD"),
            lambda l, m: m["records"][0].update(city="Самарканд"),
            lambda l, m: l["scenarios"][0]["cost"].update(amount=999),
        ]
        for change in changes:
            ledger, model = fixture()
            change(ledger, model)
            with self.subTest(change=change), self.assertRaises(ValueError):
                export.prepare(ledger, model)

    def test_partial_budget_is_retained_and_unrequested_budget_is_absent(self):
        ledger, model = fixture()
        ledger["scenarios"][0].pop("cost")
        model["records"][1]["dimension"] = "4x8"
        bundle = export.prepare(ledger, model)
        self.assertIsNone(bundle["budget"]["total"])
        self.assertEqual(bundle["budget"]["known_subtotal"]["base"], "120.00")
        ledger["brief"]["budget_mode"] = "none"
        self.assertIsNone(export.prepare(ledger, model)["budget"])

    def test_requested_budget_cannot_be_media_free_or_estimated_when_confirmed_requested(self):
        for change in (lambda l, m: m.update(required_components=[]), lambda l, m: l["brief"].update(budget_mode="confirmed")):
            ledger, model = fixture()
            change(ledger, model)
            with self.assertRaises(ValueError):
                export.prepare(ledger, model)

    def test_source_warning_and_formula_like_address_remain_data(self):
        ledger, model = fixture()
        model["records"][0]["address"] = '=HYPERLINK("https://example.invalid","address")'
        model["records"][0]["description"] = "source warning retained"
        bundle = export.prepare(ledger, model)
        self.assertEqual(bundle["rows"][0]["metadata"]["address"], model["records"][0]["address"])
        self.assertIn("source warning retained", bundle["rows"][0]["warnings"])

    def test_missing_map_is_explicit_and_keeps_all_rows(self):
        bundle = export.prepare(*fixture())
        with tempfile.TemporaryDirectory() as directory:
            result = export.render_maps(bundle, None, Path(directory))
        self.assertFalse(result["complete"])
        self.assertEqual(result["unmapped_ids"], [1, 2])
        self.assertEqual(len(bundle["rows"]), 2)

    def test_missing_coordinate_only_reduces_map_count_not_campaign(self):
        bundle = export.prepare(*fixture())
        bundle["brief"]["parameters"]["city"] = "Test city"
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            write_tiles(base, export.map_groups(bundle["rows"], 12))
            result = export.render_maps(bundle, tile_spec(base), base)
            self.assertEqual(result["mapped_ids"], [1])
            self.assertEqual(result["unmapped_ids"], [2])
            self.assertEqual(result["network_requests"], 0)
            self.assertTrue((base / result["panels"][0]["file"]).is_file())

    def test_dense_and_shared_points_have_readable_number_for_every_distinct_id(self):
        bundle = export.prepare(*fixture())
        bundle["brief"]["parameters"]["city"] = "Test city"
        template = bundle["rows"][0]
        bundle["rows"] = [dict(deepcopy(template), id=i, seq=i,
                               coordinates={"lat": 41.3 + (i % 3) * 0.00001, "lng": 69.2}) for i in range(1, 81)]
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            write_tiles(base, export.map_groups(bundle["rows"], 12))
            result = export.render_maps(bundle, tile_spec(base), base)
            self.assertTrue(result["complete"])
            self.assertEqual(result["mapped_ids"], list(range(1, 81)))
            readable = {key for panel in result["panels"] for key in panel["readable_ids"]}
            self.assertEqual(readable, set(range(1, 81)))
            self.assertGreater(len(result["panels"]), 1)
            self.assertTrue(all(p["max_leader_px"] == 48 for p in result["panels"]))

    def test_missing_tiles_or_unicode_font_are_explicit_partial_maps(self):
        bundle = export.prepare(*fixture())
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            spec = tile_spec(base)
            result = export.render_maps(bundle, spec, base)
            self.assertIn("font", result["reason"])
            bundle["brief"]["parameters"]["city"] = "Test city"
            result = export.render_maps(bundle, spec, base)
            self.assertEqual(result["mapped_ids"], [])
            self.assertIn("tiles missing", result["reason"])
            spec["font_path"] = str(base / "missing.ttf")
            self.assertIn("font", export.render_maps(bundle, spec, base)["reason"])

    def test_large_high_zoom_extent_splits_before_overview_allocation(self):
        bundle = export.prepare(*fixture())
        bundle["brief"]["parameters"]["city"] = "Test city"
        bundle["rows"][1]["coordinates"] = {"lat": 41.4, "lng": 69.3}
        groups = export.map_groups(bundle["rows"], 16)
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            for group in groups:
                write_tiles(base, [group], 16)
            spec = dict(tile_spec(base), zoom=16)
            from unittest.mock import patch
            original_new = Image.new
            sizes = []
            def bounded_new(mode, size, *args, **kwargs):
                sizes.append(size)
                self.assertLessEqual(size[0] * size[1], 256 * 256 * 256)
                return original_new(mode, size, *args, **kwargs)
            with patch.object(Image, "new", side_effect=bounded_new):
                result = export.render_maps(bundle, spec, base)
            self.assertTrue(result["complete"])
            self.assertEqual(result["mapped_ids"], [1, 2])
            self.assertEqual(len(result["panels"]), 2)
            self.assertTrue(sizes)
            for tile in base.glob("16_*.png"):
                tile.unlink()
            write_tiles(base, [groups[0]], 16)
            result = export.render_maps(bundle, spec, base)
            self.assertFalse(result["complete"])
            self.assertEqual(result["mapped_ids"], [1])
            self.assertEqual(result["unmapped_ids"], [2])
            self.assertEqual([row["id"] for row in bundle["rows"]], [1, 2])

    def test_coordinates_outside_projection_remain_unmapped_without_losing_rows(self):
        bundle = export.prepare(*fixture())
        bundle["brief"]["parameters"]["city"] = "Test city"
        bundle["rows"][0]["coordinates"]["lat"] = 89
        with tempfile.TemporaryDirectory() as directory:
            result = export.render_maps(bundle, tile_spec(Path(directory)), Path(directory))
        self.assertEqual(result["unmapped_ids"], [1, 2])
        self.assertEqual(len(bundle["rows"]), 2)

    def test_cli_does_not_overwrite_existing_directory(self):
        ledger, model = fixture()
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            for name, value in (("ledger", ledger), ("model", model)):
                (base / (name + ".json")).write_text(json.dumps(value))
            output = base / "output"
            output.mkdir()
            (output / "preserve.txt").write_text("keep")
            result = subprocess.run([sys.executable, str(Path(export.__file__)), str(base / "ledger.json"), str(base / "model.json"), str(output)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertIn("already exists", result.stderr)
            self.assertEqual((output / "preserve.txt").read_text(), "keep")


def saved_fixture(filename, bundle, mutation=None):
    """Minimal OOXML fixture for verifier negative checks, not an authoring engine."""
    from xml.sax.saxutils import escape
    ns = verify.NS["s"]
    def cell(ref, value, formula=None):
        if formula:
            return f'<c r="{ref}"><f>{escape(formula)}</f><v>{value}</v></c>'
        if isinstance(value, str):
            return f'<c r="{ref}" t="inlineStr"><is><t>{escape(value)}</t></is></c>'
        return f'<c r="{ref}"><v>{value}</v></c>'
    values = {"B3": "Ташкент", "B4": 46235, "B5": 46265,
              "B6": "all, 18–55, bc", "A8": "Reach 5+ программы",
              "B11": bundle["summary"]["methodology"],
              "B12": json.dumps({k: v for k, v in bundle["brief"]["parameters"].items()
                                 if k not in ("city", "periodFrom", "periodTo", "audience")}),
              "B7": 2, "B8": 0.4, "B9": 1267819, "B10": 507127.6, "B13": "0 / 2",
              "B14": "1, 2", "B15": "частичная: Missing basemap", "B16": "Наличие не подтверждено",
              "B18": "не запрошен"}
    s = '<worksheet xmlns="' + ns + '"><sheetData><row r="1">' + ''.join(cell(k, v, "B8*B9" if k == "B10" else None) for k, v in values.items()) + '</row></sheetData></worksheet>'
    a = '<worksheet xmlns="' + ns + '"><sheetViews><sheetView><pane state="frozen"/></sheetView></sheetViews><sheetData>'
    for i, row in enumerate(bundle["rows"], 6):
        a += f'<row r="{i}">' + cell(f"A{i}", row["seq"]) + cell(f"B{i}", str(row["id"]))
        for col, value in {"C": row["metadata"].get("address") or "нет адреса в источнике", "D": row["metadata"].get("supplierId"),
                           "E": row["metadata"].get("type"), "F": row["metadata"].get("dimension"), "G": "OOH", "H": row["metadata"].get("side"),
                           "I": "; ".join(row["warnings"]), "J": "не подтверждено"}.items():
            a += cell(f"{col}{i}", "" if value is None else str(value))
        if row["coordinates"]:
            a += cell(f"K{i}", row["coordinates"]["lat"]) + cell(f"L{i}", row["coordinates"]["lng"])
        a += '</row>'
    a += '</sheetData><tableParts><tablePart/></tableParts></worksheet>'
    files = {
        "xl/workbook.xml": '<workbook xmlns="' + ns + '" xmlns:r="' + verify.NS["r"] + '"><sheets><sheet name="Карта и итог" r:id="one"/><sheet name="Адресная программа" r:id="two"/></sheets></workbook>',
        "xl/_rels/workbook.xml.rels": '<Relationships xmlns="' + verify.NS["p"] + '"><Relationship Id="one" Target="worksheets/sheet1.xml"/><Relationship Id="two" Target="worksheets/sheet2.xml"/></Relationships>',
        "xl/worksheets/sheet1.xml": s, "xl/worksheets/sheet2.xml": a,
    }
    if mutation:
        mutation(files)
    with zipfile.ZipFile(filename, "w") as z:
        for name, contents in files.items():
            z.writestr(name, contents)


class SavedExportTests(unittest.TestCase):
    def fixture(self):
        ledger, model = fixture()
        ledger["brief"]["budget_mode"] = "none"
        bundle = export.prepare(ledger, model)
        bundle["map"] = {"mapped_ids": [], "unmapped_ids": [1, 2], "panels": [], "complete": False, "reason": "Missing basemap"}
        return bundle

    def test_reads_exact_text_ids_and_partial_map_from_saved_workbook(self):
        bundle = self.fixture()
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / "fixture.xlsx"
            saved_fixture(file, bundle)
            self.assertEqual(verify.verify(bundle, file)["surfaces"], 2)

    def test_changed_campaign_metadata_and_frequency_are_rejected(self):
        import xml.etree.ElementTree as ET
        changes = {"B3": "Самарканд", "B4": "46236", "B5": "46266", "B6": "female, 25–35, a",
                   "A8": "Reach 1+ программы", "B11": "other method", "B12": "{}",
                   "B14": "нет", "B15": "полная", "B16": "Подтверждено", "B18": "confirmed"}
        for ref, value in changes.items():
            with self.subTest(ref=ref), tempfile.TemporaryDirectory() as directory:
                bundle = self.fixture()
                file = Path(directory) / "changed.xlsx"
                def mutate(files):
                    part = "xl/worksheets/sheet1.xml"
                    root = ET.fromstring(files[part])
                    cell = root.find(f".//s:c[@r='{ref}']", verify.NS)
                    target = cell.find("s:is/s:t", verify.NS) if cell.attrib.get("t") == "inlineStr" else cell.find("s:v", verify.NS)
                    target.text = value
                    files[part] = ET.tostring(root, encoding="unicode")
                saved_fixture(file, bundle, mutate)
                with self.assertRaises(ValueError):
                    verify.verify(bundle, file)

    def test_campaign_metadata_formula_is_rejected_even_with_unchanged_cached_text(self):
        bundle = self.fixture()
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / "changed.xlsx"
            def mutate(files):
                files["xl/worksheets/sheet1.xml"] = files["xl/worksheets/sheet1.xml"].replace(
                    '<c r="B6" t="inlineStr">', '<c r="B6" t="inlineStr"><f>"all, 18–55, bc"</f>')
            saved_fixture(file, bundle, mutate)
            with self.assertRaises(verify.VerificationError):
                verify.verify(bundle, file)

    def test_1904_epoch_preserves_visible_campaign_dates(self):
        bundle = self.fixture()
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / "dates.xlsx"
            def mutate(files):
                files["xl/workbook.xml"] = files["xl/workbook.xml"].replace('<sheets>', '<workbookPr date1904="1"/><sheets>')
                files["xl/worksheets/sheet1.xml"] = files["xl/worksheets/sheet1.xml"].replace('<v>46235</v>', '<v>44773</v>').replace('<v>46265</v>', '<v>44803</v>')
            saved_fixture(file, bundle, mutate)
            self.assertEqual(verify.verify(bundle, file)["surfaces"], 2)

    def test_saved_id_formula_error_and_missing_image_relationship_are_rejected(self):
        for replacement in ('<c r="B6" t="inlineStr"><is><t>99</t></is></c>', '<c r="B6"><f>1</f><v>1</v></c>', '<c r="B6" t="e"><v>#REF!</v></c>'):
            bundle = self.fixture()
            with tempfile.TemporaryDirectory() as directory:
                file = Path(directory) / "fixture.xlsx"
                def mutate(files):
                    files["xl/worksheets/sheet2.xml"] = files["xl/worksheets/sheet2.xml"].replace('<c r="B6" t="inlineStr"><is><t>1</t></is></c>', replacement)
                saved_fixture(file, bundle, mutate)
                with self.assertRaises(verify.VerificationError):
                    verify.verify(bundle, file)
        bundle = self.fixture()
        bundle["map"]["panels"] = [{"sha256": "missing"}]
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / "fixture.xlsx"
            saved_fixture(file, bundle)
            with self.assertRaisesRegex(verify.VerificationError, "not attached"):
                verify.verify(bundle, file)


if __name__ == "__main__":
    unittest.main()
