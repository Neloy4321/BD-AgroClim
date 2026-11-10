#!/usr/bin/env python3
"""Embed the author's original *draft* station positions into an executable GEE JS.

This creates new, independently written code; it does not recover the author's
missing historical Earth Engine script, task IDs, extraction reducer or pixel IDs.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent


def build_points(point_file: Path) -> list[dict]:
    with point_file.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError("No stations in the points file")
    points = []
    seen = set()
    for row in rows:
        pid = row["point_id"].strip()
        name = row["station_name"].strip()
        lat, lon = float(row["lat"]), float(row["lon"])
        if not pid or not name or pid in seen:
            raise ValueError(f"Missing or duplicate station identification: {pid}")
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            raise ValueError(f"Invalid station coordinates for {pid}")
        seen.add(pid)
        points.append({"point_id": pid, "station_name": name, "lat": lat, "lon": lon})
    return points


def render(points_file: Path, template_file: Path, destination_file: Path) -> dict:
    points = build_points(points_file)
    template = template_file.read_text(encoding="utf-8")
    needle = "__POINTS_JS__"
    if template.count(needle) != 1:
        raise ValueError("GEE template must contain exactly one station placeholder")
    result = template.replace(needle, json.dumps(points, ensure_ascii=False, indent=2))
    destination_file.write_text(result, encoding="utf-8")
    return {
        "station_count": len(points),
        "coordinate_verification": "NOT VERIFIED - author draft station positions",
        "source_csv_sha256": hashlib.sha256(points_file.read_bytes()).hexdigest(),
        "generated_js_sha256": hashlib.sha256(result.encode()).hexdigest(),
        "generated_js": destination_file.name,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--points", type=Path, default=HERE / "station_points_author_draft.csv")
    parser.add_argument("--template", type=Path, default=HERE / "gee_era5land_daily_template.js")
    parser.add_argument("--out", type=Path, default=HERE / "gee_era5land_daily_extract.js")
    args = parser.parse_args()
    print(json.dumps(render(args.points, args.template, args.out), indent=2))


if __name__ == "__main__":
    main()
