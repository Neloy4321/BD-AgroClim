#!/usr/bin/env python3
"""Compare a *new, independently exported* ERA5-Land GEE CSV with author ERA5 v2.

Read-only on inputs. This is a provenance consistency audit, NOT a recovery of
the original Earth Engine task. Matches do not certify the historical BMD dates
or station coordinates. No BMD target observations are needed or exported.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


HERE = Path(__file__).resolve().parent
# existing author file -> new extraction column, numerical absolute tolerance
PAIRINGS = {
    "t2m_mean": ("t2m_C", 0.05),
    "t2m_max": ("tmax_C", 0.05),
    "t2m_min": ("tmin_C", 0.05),
    "d2m": ("d2m_C", 0.05),
    "prcp": ("rain_mm_clipped", 0.05),  # Confirmed: old prcp is mm with negative raw ERA5 rain clipped.
    "swvl1": ("swvl1_m3m3", 0.002),
    "swvl2": ("swvl2_m3m3", 0.002),
    "ssrd": ("ssrd_MJ_m2_day", 0.2),
    "pet_era5": ("pet_evap_positive_mm", 0.5),  # GEE evaporation downward-signed
    "aet_era5": ("aet_evap_positive_mm", 0.5),
    "u10": ("u10_ms", 0.1),
    "v10": ("v10_ms", 0.1),
    "sp": ("sp_kPa", 0.1),
}


def load_new_exports(paths: list[Path]) -> tuple[dict, dict]:
    data = {}
    stats = Counter()
    for path in paths:
        with path.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            for needed in ("point_id", "date_utc", "rain_m", "rain_mm_raw", "rain_mm_clipped"):
                if needed not in (reader.fieldnames or []):
                    raise ValueError(f"{path}: missing expected new-export column {needed}")
            for row in reader:
                key = (row["point_id"], row["date_utc"])
                if key in data:
                    raise ValueError(f"Duplicate station/UTC date in GEE exports: {key}")
                data[key] = row
                stats["exported_rows"] += 1
                try:
                    if float(row["rain_m"]) < 0:
                        stats["negative_native_precipitation_rows"] += 1
                except (ValueError, TypeError):
                    stats["precipitation_unreadable_rows"] += 1
                try:
                    metres = float(row["rain_m"])
                    mm = float(row["rain_mm_raw"])
                    if not math.isclose(mm, 1000 * metres, abs_tol=1e-7, rel_tol=1e-8):
                        stats["unit_conversion_inconsistent_rows"] += 1
                except (ValueError, TypeError):
                    stats["unit_conversion_unreadable_rows"] += 1
    return data, dict(stats)


def compare_exports(reference: Path, exports: list[Path], output_dir: Path) -> dict:
    newer, export_stats = load_new_exports(exports)
    if not newer:
        raise ValueError("New GEE exports contain zero data rows")
    reference_keys = set()
    per_var = defaultdict(lambda: {"paired": 0, "within_tolerance": 0, "abs_error_sum": 0., "max_abs_error": 0.})
    per_station = defaultdict(lambda: {"matched_days": 0, "field_failures": 0})
    largest = []
    skipped_filled = 0
    missing_reference = 0
    with reference.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            key = (row["point_id"], row["date"])
            if key not in newer:
                continue
            reference_keys.add(key)
            if row.get("era5_source") != "native":
                skipped_filled += 1
                continue
            fresh = newer[key]
            per_station[key[0]]["matched_days"] += 1
            for source_col, (fresh_col, tol) in PAIRINGS.items():
                if source_col not in row or fresh_col not in fresh:
                    continue
                try:
                    old = float(row[source_col]); new = float(fresh[fresh_col])
                    if not (math.isfinite(old) and math.isfinite(new)):
                        continue
                except (ValueError, TypeError):
                    continue
                error = abs(old - new)
                info = per_var[source_col]
                info["paired"] += 1
                info["within_tolerance"] += int(error <= tol)
                info["abs_error_sum"] += error
                info["max_abs_error"] = max(info["max_abs_error"], error)
                if error > tol:
                    per_station[key[0]]["field_failures"] += 1
                    largest.append({
                        "point_id": key[0], "date_utc": key[1], "field": source_col,
                        "original_derived": old, "new_gee": new,
                        "absolute_error": error, "tolerance": tol,
                    })
    for info in per_var.values():
        n = info["paired"]
        info["mean_abs_error"] = info.pop("abs_error_sum") / n if n else None
        info["within_tolerance_fraction"] = info["within_tolerance"] / n if n else None
    largest.sort(key=lambda x: x["absolute_error"] / max(x["tolerance"], 1e-15), reverse=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "comparison_top_100_discrepancies.csv").open("w", newline="", encoding="utf-8") as handle:
        names = ["point_id", "date_utc", "field", "original_derived", "new_gee", "absolute_error", "tolerance"]
        writer = csv.DictWriter(handle, fieldnames=names)
        writer.writeheader()
        writer.writerows(largest[:100])
    with (output_dir / "comparison_by_station.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["point_id", "matched_days", "field_failures"])
        writer.writeheader()
        for key in sorted(per_station):
            writer.writerow({"point_id": key, **per_station[key]})
    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "provenance": "new GEE export compared to old author-derived ERA5 CSV; NOT original GEE task reconstruction",
        "date_basis": "date_utc from GEE compared literally to old date (no shift)",
        "coordinate_basis": "author draft coordinates; site relocation not verified",
        "reference_file": str(reference), "gee_export_files": [str(p) for p in exports],
        "new_export_stats": export_stats,
        "new_export_keys_absent_from_old_reference": len(set(newer) - reference_keys),
        "new_export_keys_skipped_non_native_reference": skipped_filled,
        "native_days_compared": sum(v["matched_days"] for v in per_station.values()),
        "total_field_discrepancies": len(largest),
        "pairings": {k: {"new_gee_column": v[0], "tolerance": v[1]} for k, v in PAIRINGS.items()},
        "per_field": dict(per_var),
        "per_station": dict(per_station),
        "interpretation": "If discrepancy is large, investigate sampling reducer, grid, run dates and units; do not overwrite source data automatically.",
    }
    (output_dir / "gee_comparison_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--export", type=Path, nargs="+", required=True,
                        help="Downloaded GEE CSV(s) from Drive, e.g. sample CSV or annual CSVs")
    parser.add_argument("--reference", type=Path, required=True,
                        help="dataset/era5land_stations_daily/era5land_stations_daily_v2.csv")
    parser.add_argument("--out-dir", type=Path, default=HERE / "comparison_results")
    args = parser.parse_args()
    result = compare_exports(args.reference, args.export, args.out_dir)
    print(json.dumps({
        "native_days_compared": result["native_days_compared"],
        "new_export_keys_absent_from_old_reference": result["new_export_keys_absent_from_old_reference"],
        "total_field_discrepancies": result["total_field_discrepancies"],
        "result_directory": str(args.out_dir),
    }, indent=2))


if __name__ == "__main__":
    main()
