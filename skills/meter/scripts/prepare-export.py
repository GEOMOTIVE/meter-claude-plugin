#!/usr/bin/env python3
"""Validate a final campaign and prepare an XLSX bundle using local map tiles only."""
import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys


class ExportError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise ExportError(message)


def load_helper(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def prepare(ledger, model):
    campaign = load_helper("campaign-ledger")
    inventory = load_helper("inventory-budget")
    summary = campaign.summarize(ledger)
    require(summary["final_confirmed"], "a successful fresh final_validation is required")
    normalized = inventory.calculate(model)
    final = next(s for s in ledger["scenarios"] if s["name"] == ledger["final_scenario"])
    ids = final["request"]["surfaces"]
    require(normalized["selected_ids"] == ids, "export roster/order differs from final calculation")
    require(campaign.canonical(normalized["campaign"]["parameters"]) == campaign.canonical(ledger["brief"]["parameters"]),
            "budget/export parameters differ from final calculation")
    require(normalized["campaign"]["currency"] == ledger["brief"]["constraints"]["currency"], "export currency mismatch")
    requested_budget = ledger["brief"]["budget_mode"] != "none"
    if requested_budget:
        require("media" in model["required_components"], "requested budget must include media")
        cost = final.get("cost")
        require(not normalized["budget_complete"] or cost is not None,
                "bind the complete budget ledger_cost to the retained final scenario before exporting")
        if cost is not None:
            bound = normalized["ledger_cost"]
            require(bound is not None, "final ledger has a total but export budget is incomplete")
            require(cost.get("surface_ids") == ids and cost.get("campaign_parameters") == ledger["brief"]["parameters"],
                    "final cost must be bound to the exact request")
            for key in ("amount", "currency", "status"):
                require(cost.get(key) == bound[key], "export budget differs from final ledger: " + key)
            for key in ("amount_decimal", "low", "high"):
                if key in cost:
                    require(cost[key] == bound[key], "export budget differs from final ledger: " + key)
        require(ledger["brief"]["budget_mode"] != "confirmed" or normalized["budget_status"] == "confirmed",
                "confirmed budget requested but prices are estimated or incomplete")
    rows_by_id = {row["id"]: row for row in normalized["rows"]}
    rows = []
    for seq, key in enumerate(ids, 1):
        source = rows_by_id[key]
        metadata = source["metadata"]
        for field, expected in (("city", ledger["brief"]["parameters"]["city"]), ("country", ledger["brief"]["country"])):
            require(not metadata.get(field) or metadata[field] == expected, f"ID {key}: inventory {field} differs from campaign")
        rows.append({"seq": seq, "id": key, "metadata": metadata, "coordinates": source["coordinates"],
                     "media_class": source["media_class"], "availability": source["availability"],
                     "warnings": source["warnings"], "source_reference": normalized["inventory_source_reference"]})
    return {"schema_version": 1, "brief": ledger["brief"], "summary": summary,
            "result": final["result"], "rows": rows,
            "budget": {k: v for k, v in normalized.items() if k not in ("rows", "eligible_ids", "excluded_ids")} if requested_budget else None,
            "limitations": summary["limitations"] + ["Availability is unconfirmed."]}


def world_pixel(lat, lng, zoom):
    require(abs(lat) < 85.05112878, "coordinate outside Web Mercator coverage")
    size = 256 * 2 ** zoom
    return (lng + 180) / 360 * size, (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * size


def map_groups(rows, zoom):
    groups = {}
    for row in rows:
        coordinate = row["coordinates"]
        if coordinate is not None and abs(coordinate["lat"]) < 85.05112878:
            point = world_pixel(coordinate["lat"], coordinate["lng"], zoom)
            groups.setdefault(point, []).append(row)
    # Multiple sides at one coordinate keep their own numbers. Long shared labels
    # are split into explicitly identified detail panels rather than aggregated.
    return [{"point": p, "rows": values[i:i + 6]} for p, values in groups.items() for i in range(0, len(values), 6)]


def panel_bounds(groups, aspect):
    xs, ys = zip(*(g["point"] for g in groups))
    # Never enlarge a tiny crop into a blurred pseudo-map. Detail panels can
    # separate labels while retaining enough road context from the cached zoom.
    width, height = max(550, max(xs) - min(xs)), max(360, max(ys) - min(ys))
    width, height = max(width, height * aspect), max(height, width / aspect)
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    return cx - width * 0.7, cy - height * 0.7, cx + width * 0.7, cy + height * 0.7


def layout(groups, bounds, width, height, font, draw):
    x0, y0, x1, y1 = bounds
    placements, occupied = [], []
    for group in groups:
        x, y = group["point"]
        x, y = (x - x0) / (x1 - x0) * width, (y - y0) / (y1 - y0) * height
        text = ",".join(str(r["seq"]) for r in group["rows"])
        box = draw.textbbox((0, 0), text, font=font)
        halfw, halfh = (box[2] - box[0]) / 2 + 8, 17
        candidates = [(x, y)] + [(x + radius * math.cos(a * math.pi / 4), y + radius * math.sin(a * math.pi / 4))
                                   for radius in (28, 48) for a in range(8)]
        chosen = None
        for cx, cy in candidates:
            rect = (cx - halfw, cy - halfh, cx + halfw, cy + halfh)
            if rect[0] < 3 or rect[1] < 3 or rect[2] > width - 3 or rect[3] > height - 3:
                continue
            if any(not (rect[2] + 5 < b[0] or b[2] + 5 < rect[0] or rect[3] + 5 < b[1] or b[3] + 5 < rect[1]) for b in occupied):
                continue
            # A moved label must not hide a different exact point.
            if any(rect[0] - 6 < (g["point"][0] - x0) / (x1 - x0) * width < rect[2] + 6 and
                   rect[1] - 6 < (g["point"][1] - y0) / (y1 - y0) * height < rect[3] + 6
                   for g in groups if g["point"] != group["point"]):
                continue
            chosen = (cx, cy, rect)
            break
        placements.append({"group": group, "point": (x, y), "label": chosen, "text": text})
        if chosen:
            occupied.append(chosen[2])
    return placements


def render_maps(bundle, spec, output):
    """Returns complete/partial map metadata; dependencies and tiles are never fetched."""
    ids = [r["id"] for r in bundle["rows"]]
    metadata = {"mapped_ids": [], "unmapped_ids": ids, "panels": [], "complete": False,
                "network_requests": 0, "reason": "No local basemap supplied."}
    if spec is None:
        return metadata
    require(spec.get("projection") == "web_mercator_tiles", "basemap must use web_mercator_tiles")
    zoom = spec.get("zoom")
    require(isinstance(zoom, int) and not isinstance(zoom, bool) and 0 <= zoom <= 20, "invalid tile zoom")
    require(isinstance(spec.get("attribution"), str) and bool(spec["attribution"].strip()), "basemap attribution required")
    require(isinstance(spec.get("source_reference"), str) and bool(spec["source_reference"].strip()), "basemap source required")
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        metadata["reason"] = "Pillow is unavailable; no map rendered."
        return metadata
    font_path = spec.get("font_path")
    if not font_path and not (bundle["brief"]["parameters"]["city"] + spec["attribution"]).isascii():
        metadata["reason"] = "A local Unicode font is required for map labels."
        return metadata
    try:
        font = ImageFont.truetype(font_path, 20) if font_path else ImageFont.load_default(size=20)
        small = ImageFont.truetype(font_path, 16) if font_path else ImageFont.load_default(size=16)
    except OSError:
        metadata["reason"] = "The configured local font is unavailable."
        return metadata
    groups = map_groups(bundle["rows"], zoom)
    if not groups:
        metadata["reason"] = "No selected coordinates can be mapped with this projection."
        return metadata
    width, height, top, bottom = 1100, 720, 54, 58
    probe = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    tile_directory = Path(spec["tile_directory"])
    metadata.update(attribution=spec["attribution"], source_reference=spec["source_reference"])
    covered = set()
    failures = []

    def panel(current, title):
        bounds = panel_bounds(current, width / height)
        x0, y0, x1, y1 = bounds
        tx0, ty0, tx1, ty1 = math.floor(x0 / 256), math.floor(y0 / 256), math.floor(x1 / 256), math.floor(y1 / 256)
        require((tx1 - tx0 + 1) * (ty1 - ty0 + 1) <= 256, "map area exceeds 256 cached tiles; narrow the basemap extent")
        tiles = [(x, y, tile_directory / f"{zoom}_{x}_{y}.png") for x in range(tx0, tx1 + 1) for y in range(ty0, ty1 + 1)]
        placements = layout(current, bounds, width, height, font, probe)
        readable = all(p["label"] is not None for p in placements)
        if any(not path.is_file() for _, _, path in tiles):
            failures.append(title + ": required cached tiles missing")
            return readable, False
        raster = Image.new("RGB", ((tx1 - tx0 + 1) * 256, (ty1 - ty0 + 1) * 256))
        for x, y, path in tiles:
            with Image.open(path) as tile:
                require(tile.size == (256, 256), "cached tile must be 256x256")
                raster.paste(tile.convert("RGB"), ((x - tx0) * 256, (y - ty0) * 256))
        raster = raster.crop((round(x0 - tx0 * 256), round(y0 - ty0 * 256), round(x1 - tx0 * 256), round(y1 - ty0 * 256)))
        raster = raster.resize((width, height), Image.Resampling.LANCZOS)
        canvas = Image.new("RGB", (width, height + top + bottom), "#FBFAFC")
        canvas.paste(raster, (0, top))
        draw = ImageDraw.Draw(canvas)
        draw.text((18, 15), title, font=font, fill="#390050")
        for placement in placements:
            x, y = placement["point"]
            draw.ellipse((x - 5, y + top - 5, x + 5, y + top + 5), fill="#390050", outline="white", width=2)
            chosen = placement["label"]
            if chosen:
                cx, cy, rect = chosen
                if math.hypot(cx - x, cy - y) > 1:
                    draw.line((x, y + top, cx, cy + top), fill="#390050", width=2)
                draw.rounded_rectangle((rect[0], rect[1] + top, rect[2], rect[3] + top), radius=12, fill="#780DA3", outline="white", width=2)
                draw.text((cx, cy + top), placement["text"], font=font, fill="white", anchor="mm")
                covered.update(r["id"] for r in placement["group"]["rows"])
        draw.text((18, height + top + 6), "Numbers match the table; unnumbered overview points are labelled in details.", font=small, fill="#390050")
        draw.text((18, height + top + 30), "Short lines locate labels, not routes. " + spec["attribution"], font=small, fill="#685C6C")
        name = f"map-{len(metadata['panels']) + 1}.png"
        canvas.save(output / name)
        metadata["panels"].append({"file": name, "sha256": hashlib.sha256((output / name).read_bytes()).hexdigest(),
                                   "width": width, "height": canvas.height, "title": title,
                                   "point_ids": [r["id"] for g in current for r in g["rows"]],
                                   "readable_ids": [r["id"] for p in placements if p["label"] for r in p["group"]["rows"]],
                                   "bounds_world_pixels": bounds, "zoom": zoom, "max_leader_px": 48})
        return readable, True

    readable, present = panel(groups, "METER - " + bundle["brief"]["parameters"]["city"] + " - overview")
    if not readable or not present:
        def details(current, depth=0):
            current = [dict(g, rows=[r for r in g["rows"] if r["id"] not in covered]) for g in current]
            current = [g for g in current if g["rows"]]
            if not current:
                return
            good, exists = panel(current, "Detail " + str(len(metadata["panels"]) + 1)) if len(current) <= 12 else (False, False)
            if good and exists or len(current) == 1:
                return
            require(depth < 10, "dense map cannot be split into readable panels")
            axis = max(range(2), key=lambda i: max(g["point"][i] for g in current) - min(g["point"][i] for g in current))
            ordered = sorted(current, key=lambda g: g["point"][axis])
            middle = len(ordered) // 2
            details(ordered[:middle], depth + 1)
            details(ordered[middle:], depth + 1)
        details(groups)
    metadata["mapped_ids"] = [key for key in ids if key in covered]
    metadata["unmapped_ids"] = [key for key in ids if key not in covered]
    metadata["complete"] = not metadata["unmapped_ids"]
    metadata["reason"] = "; ".join(dict.fromkeys(failures)) or ("Missing, conflicting or unsupported map coordinates." if metadata["unmapped_ids"] else None)
    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ledger", type=Path)
    parser.add_argument("inventory_model", type=Path)
    parser.add_argument("output_directory", type=Path, help="New directory; never overwrites existing outputs")
    parser.add_argument("--basemap", type=Path, help="Local tile configuration JSON")
    args = parser.parse_args()
    try:
        bundle = prepare(json.loads(args.ledger.read_text()), json.loads(args.inventory_model.read_text()))
        spec = json.loads(args.basemap.read_text()) if args.basemap else None
        if spec:
            spec["tile_directory"] = str((args.basemap.parent / spec["tile_directory"]).resolve())
            if spec.get("font_path"):
                spec["font_path"] = str((args.basemap.parent / spec["font_path"]).resolve())
        require(not args.output_directory.exists(), "output directory already exists; choose a new directory")
        args.output_directory.mkdir(parents=True)
        bundle["map"] = render_maps(bundle, spec, args.output_directory)
        (args.output_directory / "export.json").write_text(json.dumps(bundle, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
        print(json.dumps({"bundle": str(args.output_directory / "export.json"), "map_complete": bundle["map"]["complete"]}))
    except (ExportError, ValueError, KeyError, TypeError, OSError) as exc:
        print("Cannot prepare export: " + str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
