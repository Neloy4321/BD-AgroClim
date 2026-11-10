#!/usr/bin/env python3
"""Verify raw ERA5 annual CSVs retrieved from the user's own connected Drive."""
from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from datetime import date
from pathlib import Path


HERE = Path(__file__).resolve().parent


def check_sources(root: Path = HERE) -> dict:
    with (root / "original_gee_drive_sources.csv").open(encoding="utf-8", newline="") as f:
        source_rows = list(csv.DictReader(f))
    output = []
    status = Counter()
    raw_folder = root / "drive_exports_original"
    expected_columns = [
        "point_id", "station_name", "date", "temperature_2m", "temperature_2m_max",
        "temperature_2m_min", "dewpoint_temperature_2m", "total_precipitation_sum",
        "volumetric_soil_water_layer_1", "volumetric_soil_water_layer_2",
        "surface_solar_radiation_downwards_sum", "potential_evaporation_sum",
        "total_evaporation_sum", "u_component_of_wind_10m", "v_component_of_wind_10m",
        "surface_pressure",
    ]
    for item in source_rows:
        path = raw_folder / item["original_filename"]
        if not path.is_file():
            raise FileNotFoundError(f"Drive export missing: {path}")
        size = path.stat().st_size
        if size != int(item["reported_bytes"]):
            raise ValueError(f"File size mismatches Drive listing: {path}")
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        year = int(item["year"])
        day_count = (date(year + 1, 1, 1) - date(year, 1, 1)).days
        expected = day_count * (36 if item["source_group"] == "main" else 2)
        seen = set()
        with path.open(encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames != expected_columns:
                raise ValueError(f"Unexpected source-band columns: {path}")
            for row in reader:
                key = (row["point_id"], row["date"])
                if not row["date"].startswith(str(year)) or key in seen:
                    raise ValueError(f"Bad date or duplicate point/day: {path} {key}")
                seen.add(key)
        if len(seen) != expected:
            raise ValueError(f"Row count unexpected for {path}: {len(seen)} instead of {expected}")
        status[item["source_group"]] += 1
        output.append({**item, "verified_bytes": size, "rows": len(seen),
                       "sha256": h.hexdigest(), "schema_valid": "YES"})
    with (root / "original_gee_source_file_manifest.csv").open(
            "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(output[0]))
        writer.writeheader(); writer.writerows(output)
    summary = {
        "raw_export_files": len(output),
        "files_by_group": dict(status),
        "rows_by_group": {group: sum(int(x["rows"]) for x in output if x["source_group"] == group)
                          for group in status},
        "all_48_source_file_sizes_match_google_drive": True,
        "all_48_annual_coverage_and_schema_checks_pass": True,
        "provenance_limit": "Source-level exported CSVs recovered, but original GEE scripts/tasks/parameters and historical station metadata NOT recovered.",
    }
    (root / "raw_export_source_manifest_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8")
    return summary


if __name__ == "__main__":
    print(json.dumps(check_sources(), indent=2))
