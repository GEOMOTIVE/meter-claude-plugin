#!/usr/bin/env python3
"""Check the actual saved XLSX against its prepared METER export bundle."""
import argparse
from collections import Counter
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import posixpath
import sys
import xml.etree.ElementTree as ET
import zipfile

NS = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
      "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
      "p": "http://schemas.openxmlformats.org/package/2006/relationships",
      "a": "http://schemas.openxmlformats.org/drawingml/2006/main"}


class VerificationError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise VerificationError(message)


def close(actual, expected, message):
    require(actual is not None and abs(Decimal(str(actual)) - Decimal(str(expected))) <= Decimal("0.00001"), message)


def verify(bundle, filename):
    with zipfile.ZipFile(filename) as archive:
        require(archive.testzip() is None, "XLSX ZIP is corrupt")
        names = set(archive.namelist())

        def xml(name):
            return ET.fromstring(archive.read(name))

        def relationships(part):
            parent, name = posixpath.split(part)
            relfile = posixpath.join(parent, "_rels", name + ".rels")
            require(relfile in names, "missing relationships for " + part)
            return {r.attrib["Id"]: posixpath.normpath(r.attrib["Target"].lstrip("/")) if r.attrib["Target"].startswith("/")
                    else posixpath.normpath(posixpath.join(parent, r.attrib["Target"])) for r in xml(relfile)}

        for name in names:
            if name.endswith(".rels"):
                for rel in xml(name):
                    require(rel.attrib.get("TargetMode") != "External", "external relationship in workbook")
        strings = []
        if "xl/sharedStrings.xml" in names:
            strings = ["".join(node.itertext()) for node in xml("xl/sharedStrings.xml")]

        def cells(part):
            result = {}
            for cell in xml(part).findall(".//s:sheetData/s:row/s:c", NS):
                require(cell.attrib.get("t") != "e", "Excel error in " + part + ":" + cell.attrib["r"])
                value = cell.findtext("s:v", default=None, namespaces=NS)
                if cell.attrib.get("t") == "s":
                    value = strings[int(value)]
                elif cell.attrib.get("t") == "inlineStr":
                    value = "".join(cell.find("s:is", NS).itertext())
                formula = cell.findtext("s:f", default=None, namespaces=NS)
                if formula:
                    require("[" not in formula and "]" not in formula, "external or unsupported structured formula")
                result[cell.attrib["r"]] = {"value": value, "formula": formula, "type": cell.attrib.get("t", "n")}
            return result

        book_rels = relationships("xl/workbook.xml")
        sheets = {s.attrib["name"]: book_rels[s.attrib["{%s}id" % NS["r"]]] for s in xml("xl/workbook.xml").findall("s:sheets/s:sheet", NS)}
        expected = ["Карта и итог", "Адресная программа"] + (["Бюджет"] if bundle["budget"] else [])
        require(list(sheets) == expected, "unexpected or missing worksheets")
        rows = bundle["rows"]
        ids = [r["id"] for r in rows]
        require(ids == bundle["summary"]["best"]["surface_ids"], "bundle roster mismatch")
        address = cells(sheets["Адресная программа"])
        stored = []
        for i, row in enumerate(rows, 6):
            id_cell = address.get(f"B{i}", {})
            require(id_cell.get("type") in ("s", "inlineStr", "str") and id_cell.get("formula") is None, "ID is not literal text")
            stored.append(int(id_cell["value"]))
            close(address[f"A{i}"]["value"], row["seq"], "address number mismatch")
            for col in "BCDEFGHIJ":
                require(not address.get(f"{col}{i}", {}).get("formula"), "source text interpreted as formula")
            expected_text = {"C": row["metadata"].get("address") or "нет адреса в источнике",
                             "D": row["metadata"].get("supplierId"), "E": row["metadata"].get("type"),
                             "F": row["metadata"].get("dimension"), "G": "DOOH" if row["media_class"] == "digital" else "OOH",
                             "H": row["metadata"].get("side"), "I": "; ".join(row["warnings"]), "J": "не подтверждено"}
            for col, value in expected_text.items():
                value = "" if value is None else str(value)
                actual = address.get(f"{col}{i}", {}).get("value") or ""
                require(actual in (value, "'" + value), f"source text/warning changed at {col}{i}")
            coords = row["coordinates"]
            for col, key in (("K", "lat"), ("L", "lng")):
                actual = address.get(f"{col}{i}", {}).get("value")
                if coords:
                    close(actual, coords[key], "coordinate mismatch")
                else:
                    require(actual in (None, ""), "missing coordinate replaced with a number")
        require(stored == ids, "saved address roster/order differs from campaign")
        extra_ids = [cell["value"] for ref, cell in address.items() if ref.startswith("B") and ref[1:].isdigit() and int(ref[1:]) >= len(rows) + 6 and cell["value"] not in (None, "")]
        require(not extra_ids, "unexpected additional address records")
        require(xml(sheets["Адресная программа"]).find("s:sheetViews/s:sheetView/s:pane", NS) is not None, "address header panes missing")
        require(xml(sheets["Адресная программа"]).find("s:tableParts/s:tablePart", NS) is not None, "address filter table missing")
        summary = cells(sheets["Карта и итог"])
        close(summary["B7"]["value"], len(ids), "summary surface count mismatch")
        close(summary["B8"]["value"], bundle["result"]["reach_fraction"], "campaign Reach mismatch")
        close(summary["B9"]["value"], bundle["result"]["universe"], "campaign Universe mismatch")
        close(summary["B10"]["value"], bundle["result"]["reach_fraction"] * bundle["result"]["universe"], "derived people mismatch")
        require(summary["B10"]["formula"] == "B8*B9", "people formula is not derived from campaign Universe")
        require(summary["B13"]["value"] == f"{len(bundle['map']['mapped_ids'])} / {len(ids)}", "map coverage disclosure mismatch")
        expected_hashes = Counter(panel["sha256"] for panel in bundle["map"]["panels"])
        embedded_hashes = Counter()
        drawing = xml(sheets["Карта и итог"]).find("s:drawing", NS)
        if expected_hashes:
            require(drawing is not None, "map image is not attached to summary sheet")
            drawing_part = relationships(sheets["Карта и итог"])[drawing.attrib["{%s}id" % NS["r"]]]
            image_rels = relationships(drawing_part)
            for image in xml(drawing_part).findall(".//a:blip", NS):
                part = image_rels[image.attrib["{%s}embed" % NS["r"]]]
                require(part in names, "drawing points to a missing embedded image")
                embedded_hashes[hashlib.sha256(archive.read(part)).hexdigest()] += 1
        require(embedded_hashes == expected_hashes, "embedded maps differ from prepared map panels")
        budget = bundle["budget"]
        if budget:
            saved = cells(sheets["Бюджет"])
            for i, line in enumerate(budget["line_items"], 7):
                for col, key in zip("JKL", ("low", "base", "high")):
                    require(saved[f"{col}{i}"]["formula"], "budget amount is not editable through a formula")
                    close(saved[f"{col}{i}"]["value"], line["amounts"][key], "line budget mismatch")
            total_row = len(budget["line_items"]) + 8
            for col, key in zip("JKL", ("low", "base", "high")):
                close(saved[f"{col}{total_row}"]["value"], budget["known_subtotal"][key], "known subtotal mismatch")
                if budget["budget_complete"]:
                    close(saved[f"{col}{total_row + 1}"]["value"], budget["total"][key], "complete total mismatch")
                else:
                    require(saved[f"{col}{total_row + 1}"]["value"] == "n.a.", "partial budget presented as a complete total")
            require(summary["B19"]["formula"] == f"'Бюджет'!K{total_row + 1}" and summary["B20"]["formula"] == f"'Бюджет'!K{total_row}", "budget headline is not linked to schedule")
        # Check errors on all sheets, including cells outside headline ranges.
        for part in sheets.values():
            cells(part)
        return {"surfaces": len(ids), "embedded_map_panels": sum(embedded_hashes.values()),
                "map_complete": bundle["map"]["complete"], "budget_status": budget["budget_status"] if budget else "not_requested"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("workbook", type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(verify(json.loads(args.bundle.read_text()), args.workbook)))
    except (VerificationError, ValueError, KeyError, TypeError, OSError, zipfile.BadZipFile, ET.ParseError) as exc:
        print("Invalid XLSX export: " + str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
