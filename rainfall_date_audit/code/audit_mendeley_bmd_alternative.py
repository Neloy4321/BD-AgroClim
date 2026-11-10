#!/usr/bin/env python3
"""Audit publicly released BMD-derived Mendeley station records against author CSV.

Read-only with respect to both inputs; emits JSON and a short Markdown summary.
Alignment comparisons are diagnostics, NOT authorization to change dates.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import csv
from datetime import date, timedelta
from io import TextIOWrapper
import json
from pathlib import Path
import zipfile


HERE = Path(__file__).resolve().parent
MENDELEY_ZIP = HERE / "Mendeley_BMD_Derived_35Stations_2023.zip"
CLEANED_CSV = HERE.parent / "input" / "dataset" / "BMD data" / "bmd_clean_daily.csv"
DATA_IN_ZIP = "High Volume Real-World Weather Data/Weather Datasets/Combined Data/BD_weather.csv"
ALIASES = {
    "ambaganctg": "ambagan (ctg)",
    "coxsbazar": "cox's bazar",
    "jessore": "jashore",
    "mcourt": "maijdee court",
    "sydpur": "saidpur",
}


def station_key(name):
    s = name.lower().strip()
    return ALIASES.get(s, s)


def numeric(value):
    if not value or value.strip().lower() in {"trace", "tr", "xx", "nan", "na", "-"}:
        return None
    try:
        n = float(value)
        return n if n >= 0 else None
    except ValueError:
        return None


def load_sources():
    md = {}
    spans = defaultdict(list)
    source_n = 0
    source_noninteger = 0
    duplicate_keys = 0
    with zipfile.ZipFile(MENDELEY_ZIP) as z:
        with TextIOWrapper(z.open(DATA_IN_ZIP), encoding="utf-8-sig", newline="") as stream:
            for row in csv.DictReader(stream):
                day = date(int(row["Year"]), int(row["Month"]), int(row["Day"]))
                name = station_key(row["Station"])
                rain = numeric(row["Rainfall"])
                source_n += 1
                spans[name].append(day)
                if rain is None:
                    continue
                if abs(rain - round(rain)) > 1e-7:
                    source_noninteger += 1
                key = (name, day)
                if key in md:
                    duplicate_keys += 1
                md[key] = rain
    author = {}
    author_station_names = set()
    with CLEANED_CSV.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            station = station_key(row["station_name"])
            author_station_names.add(station)
            value = numeric(row["prcp"])
            if value is not None:
                author[(station, date.fromisoformat(row["date"]))] = value
    return md, author, spans, author_station_names, source_n, source_noninteger, duplicate_keys


def evaluate(source, author, shift, year, month=None):
    total, exact, abs_error = 0, 0, 0.0
    wet_total, wet_exact, wet_error = 0, 0, 0.0
    for (name, day), rain in source.items():
        if day.year != year or (month is not None and day.month != month):
            continue
        target = author.get((name, day + timedelta(days=shift)))
        if target is None:
            continue
        total += 1
        difference = abs(rain - target)
        abs_error += difference
        exact += difference < 1e-6
        if rain > 0 or target > 0:
            wet_total += 1
            wet_error += difference
            wet_exact += difference < 1e-6
    return {
        "numeric_pairs": total,
        "exact_pairs": exact,
        "exact_fraction": round(exact / total, 5) if total else None,
        "mae_mm": round(abs_error / total, 5) if total else None,
        "wet_pairs": wet_total,
        "wet_exact": wet_exact,
        "wet_exact_fraction": round(wet_exact / wet_total, 5) if wet_total else None,
        "wet_mae_mm": round(wet_error / wet_total, 5) if wet_total else None,
    }


def main():
    source, author, spans, author_stations, n, noninteger, dupe = load_sources()
    years = {str(year): {str(shift): evaluate(source, author, shift, year) for shift in [-2, -1, 0, 1, 2]} for year in range(2000, 2024)}
    coverage = {station: {"from": min(days).isoformat(), "to": max(days).isoformat(), "row_count": len(days)} for station, days in sorted(spans.items())}
    best_by_year = {}
    for year, tests in years.items():
        viable = {shift: scores for shift, scores in tests.items() if scores["wet_pairs"] >= 50}
        best_by_year[year] = min(viable, key=lambda shift: viable[shift]["wet_mae_mm"]) if viable else None
    monthly_tests = {
        str(year): {
            f"{month:02d}": {
                str(shift): evaluate(source, author, shift, year, month)
                for shift in [-1, 0, 1]
            }
            for month in range(1, 13)
        }
        for year in [2019, 2020, 2021, 2022, 2023]
    }
    best_by_month = {}
    for year, data in monthly_tests.items():
        best_by_month[year] = {}
        for month, tests in data.items():
            # Reject very sparse months where high zero-rain agreement is misleading.
            # Keep March 2022: the same-day comparison has 18 / 18 exact wet pairs.
            viable = {shift: metrics for shift, metrics in tests.items() if metrics["wet_pairs"] >= 15}
            best_by_month[year][month] = min(viable, key=lambda shift: viable[shift]["wet_mae_mm"]) if viable else None
    anchors = {}
    for station, when in [("sylhet", date(2021, 5, 20)), ("chandpur", date(2021, 5, 20)), ("hatiya", date(2021, 5, 20)), ("rajshahi", date(2023, 9, 6)), ("kutubdia", date(2023, 9, 6)), ("faridpur", date(2023, 9, 6))]:
        anchors[f"{station}:{when}"] = {"Mendeley_mm": source.get((station, when)), "author_same_day_mm": author.get((station, when)), "author_previous_day_mm": author.get((station, when - timedelta(days=1)))}
    result = {
        "source": "Zubair et al. (2024), High Volume Real-World Weather Data, Mendeley Data V1, DOI 10.17632/tbrhznpwg9.1",
        "dataset_type": "Third-party processed compilation attributed to BMD; not a certified BMD raw export",
        "year_coverage": "Station-specific spans; see per_station_coverage",
        "source_total_rows": n,
        "source_numeric_rainfall_rows": len(source),
        "source_numeric_noninteger_rows": noninteger,
        "source_duplicate_station_dates": dupe,
        "stations_mendeley": len(spans),
        "stations_matching_author_by_alias": sorted(set(spans) & author_stations),
        "stations_not_matching_author_by_alias": sorted(set(spans) - author_stations),
        "per_station_coverage": coverage,
        "rainfall_2000_2023_offset_checks": years,
        "lowest_wet_mae_offset_by_year_diagnostic_only": best_by_year,
        "monthly_alignment_diagnostics_2019_2023": monthly_tests,
        "lowest_wet_mae_offset_by_month_diagnostic_only": best_by_month,
        "event_anchors": anchors,
        "cautions": [
            "No evidence the original BMD observation time convention can be inferred from a third-party processed dataset alone.",
            "Unknown interpolation/imputation of early records may affect validity; avoid replacing source records with this compilation without QC.",
            "Matching daily values and calendar labels does not prove this copy is the author's original raw BMD export.",
            "Do not select date shifts using model test performance; these comparisons are solely external-data diagnostics.",
        ],
    }
    (HERE / "Mendeley_BMD_Comparison_Audit.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = ["# Independent public BMD-derived dataset comparison", "", result["source"], "", f"Records: {n:,}; stations: {len(spans)}; noninteger daily rainfall values: {noninteger:,}; duplicate station-dates: {dupe}.", "", "## Yearwise minimum wet-day MAE diagnostic", "", "| Year | Lowest-error label offset | Exact wet days / pairs | Wet MAE mm |", "|---|---:|---:|---:|"]
    for year, shift in best_by_year.items():
        if shift is None:
            lines.append(f"| {year} | no comparable wet days | — | — |")
        else:
            item = years[year][shift]
            lines.append(f"| {year} | {shift} | {item['wet_exact']:,} / {item['wet_pairs']:,} | {item['wet_mae_mm']} |")
    lines.extend(["", "**Important:** This is a comparison of two processed representations, not confirmation of raw BMD date semantics. See the JSON for all offsets and station ranges."])
    (HERE / "Mendeley_BMD_Comparison_Audit.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"source_total_rows": n, "station_count": len(spans), "numeric_noninteger": noninteger, "missing_station_aliases": result["stations_not_matching_author_by_alias"], "best_shifts_2000_2023": best_by_year, "anchors": anchors}, indent=2))


if __name__ == "__main__":
    main()
