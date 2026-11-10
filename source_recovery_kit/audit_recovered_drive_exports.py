#!/usr/bin/env python3
"""Compare recovered original per-year GEE raw CSVs with author's derived ERA5 v2.

The Drive exports are the original-ish SOURCE-LEVEL files found in the author's
connected Drive. They are not proof of source code, Earth Engine run parameters
or historical station location. Uses standard library; no BMD targets.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path


HERE = Path(__file__).resolve().parent
INPUT_DIR = HERE / "drive_exports_original"


def source_values(row: dict) -> dict[str, float]:
    def c(key: str) -> float:
        try:
            return float(row[key])
        except (ValueError, TypeError, KeyError):
            return float("nan")
    rain_m = c("total_precipitation_sum")
    # The original author's ERA5 v2 processing non-negativity-clipped the
    # occasionally negative GRIB-artifact precipitation *after* m->mm.
    rainfall_mm = max(0.0, rain_m * 1000) if math.isfinite(rain_m) else float("nan")
    return {
        "t2m_mean": c("temperature_2m") - 273.15,
        "t2m_max": c("temperature_2m_max") - 273.15,
        "t2m_min": c("temperature_2m_min") - 273.15,
        "d2m": c("dewpoint_temperature_2m") - 273.15,
        "prcp": rainfall_mm,
        "swvl1": c("volumetric_soil_water_layer_1"),
        "swvl2": c("volumetric_soil_water_layer_2"),
        "ssrd": c("surface_solar_radiation_downwards_sum") / 1_000_000.0,
        "pet_era5": c("potential_evaporation_sum") * -1000.0,
        "aet_era5": c("total_evaporation_sum") * -1000.0,
        "u10": c("u_component_of_wind_10m"),
        "v10": c("v_component_of_wind_10m"),
        "sp": c("surface_pressure") / 1000.0,
    }


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def process(raw_dir: Path, processed_csv: Path, result_dir: Path) -> dict:
    years = list(range(2000, 2024))
    exports = [raw_dir / f"era5land_stations_{year}.csv" for year in years]
    missing = [p.name for p in exports if not p.is_file()]
    if missing:
        raise FileNotFoundError(f"Missing recovered raw GEE source CSV files: {missing}")
    index = {}
    with processed_csv.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            if row["date"][:4] in {str(x) for x in years}:
                key = (row["point_id"], row["date"])
                if key in index:
                    raise ValueError(f"Duplicate processed key: {key}")
                index[key] = row
    field_totals = defaultdict(lambda: {"paired": 0, "close_1e_7": 0, "max_abs_error": 0.0})
    year_rows = []
    discrepancies = []
    unique_source = set()
    source_types = Counter()
    all_raw_rows = 0
    for year, path in zip(years, exports):
        matched, missing_processed, differences, clipped_negatives = 0, 0, 0, 0
        year_keys = set()
        with path.open(encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                key = (row["point_id"], row["date"])
                if key in year_keys or key in unique_source:
                    raise ValueError(f"Duplicate raw source point/day: {key}")
                year_keys.add(key); unique_source.add(key)
                all_raw_rows += 1
                existing = index.get(key)
                if not existing:
                    missing_processed += 1
                    continue
                matched += 1
                typ = existing.get("era5_source", "")
                source_types[typ] += 1
                try:
                    clipped_negatives += int(float(row["total_precipitation_sum"]) < 0)
                except (ValueError, TypeError):
                    pass
                for field, predicted in source_values(row).items():
                    try:
                        actual = float(existing[field])
                    except (ValueError, KeyError, TypeError):
                        continue
                    if not math.isfinite(actual) or not math.isfinite(predicted):
                        continue
                    delta = abs(actual - predicted)
                    stat = field_totals[(typ, field)]
                    stat["paired"] += 1
                    stat["close_1e_7"] += int(delta <= 1e-7)
                    stat["max_abs_error"] = max(stat["max_abs_error"], delta)
                    if delta > 1e-7:
                        differences += 1
                        if len(discrepancies) < 200:
                            discrepancies.append({
                                "year": year, "point_id": key[0], "date": key[1],
                                "source_type": typ, "field": field,
                                "raw_export_derived_value": predicted,
                                "old_processed_value": actual, "abs_error": delta,
                            })
        year_rows.append({
            "year": year, "raw_source_rows": len(year_keys),
            "matching_processed_keys": matched,
            "raw_keys_missing_from_processed": missing_processed,
            "negative_precipitation_sources_clipped_to_zero": clipped_negatives,
            "source_to_processed_field_discrepancies": differences,
            "original_drive_csv_sha256": sha(path),
        })
    missing_raw = len(set(index) - unique_source)
    result_dir.mkdir(parents=True, exist_ok=True)
    with (result_dir / "recovered_gee_per_year.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(year_rows[0]))
        writer.writeheader(); writer.writerows(year_rows)
    with (result_dir / "recovered_gee_discrepancy_first_200.csv").open("w", encoding="utf-8", newline="") as f:
        cols = ["year", "point_id", "date", "source_type", "field", "raw_export_derived_value", "old_processed_value", "abs_error"]
        writer = csv.DictWriter(f, fieldnames=cols)
        writer.writeheader(); writer.writerows(discrepancies)
    summary = {
        "source": "Original-format station CSVs recovered from connected user's Google Drive ERA5L_BD directory",
        "original_gee_script_and_task_ids_recovered": False,
        "historical_station_site_geometry_proved": False,
        "year_start": min(years), "year_end": max(years),
        "raw_csvs": len(exports), "raw_source_rows": all_raw_rows,
        "raw_keys_missing_from_processed": sum(r["raw_keys_missing_from_processed"] for r in year_rows),
        "processed_keys_absent_from_raw": missing_raw,
        "processed_matched_rows_by_source_type": dict(source_types),
        "negative_precipitation_sources_clipped_to_zero": sum(
            r["negative_precipitation_sources_clipped_to_zero"] for r in year_rows),
        "compared_numeric_field_units": "t C; rain mm (raw m x 1000); radiation MJ/m2; evaporation positive mm; pressure kPa; other raw units",
        "total_field_discrepancies_above_1e_7": sum(r["source_to_processed_field_discrepancies"] for r in year_rows),
        "field_comparison": {
            f"{kind}::{field}": values for (kind, field), values in sorted(field_totals.items())
        },
        "per_year": year_rows,
        "important_limitation": "This checks arithmetic and source CSV continuity, NOT BMD date observation semantics or GEE pixel geometry provenance.",
    }
    (result_dir / "recovered_gee_audit_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8")
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, default=INPUT_DIR)
    parser.add_argument("--processed", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, default=HERE / "drive_original_audit_results")
    args = parser.parse_args()
    result = process(args.raw_dir, args.processed, args.out_dir)
    print(json.dumps({x: result[x] for x in (
        "raw_csvs", "raw_source_rows", "raw_keys_missing_from_processed",
        "processed_keys_absent_from_raw", "processed_matched_rows_by_source_type",
        "total_field_discrepancies_above_1e_7")}, indent=2))
