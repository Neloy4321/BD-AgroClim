#!/usr/bin/env python3
"""Reproducible rainfall-only date-label reconciliation, without touching raw data.

The public Mendeley release is processed BMD-derived data (not an original BMD
gauge export). A one-day label adjustment here is explicitly a hypothesis.
The saved-model experiment is a frozen-prediction score sensitivity, NOT a
leakage-free retraining or an endorsement of the adjusted labels.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import timedelta
from pathlib import Path
import hashlib
import json
import sys

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
OUT = HERE / "BMD_Date_Reconciliation_20261110"
sys.path.insert(0, str(HERE))
from audit_mendeley_bmd_alternative import load_sources, station_key  # noqa: E402
sys.path.insert(0, str(BASE))
from run_integrated_audit import finite_score  # noqa: E402

ORIGINAL = BASE / "input/dataset/BMD data/bmd_clean_daily.csv"
ERA = BASE / "input/dataset/era5land_stations_daily/era5land_stations_daily_v2.csv"
MENDELEY = HERE / "Mendeley_BMD_Derived_35Stations_2023.zip"
BAMIS = HERE / "BAMIS_Immediate_Verification/audit_results.json"
FOLDS = BASE / "evidence_inputs/saved_frozen_predictions"
FOCUS = (2019, 2021, 2023)
# Exclusions based on observed *source* duplication evidence, not on ML scores.
SOURCE_EXCLUSIONS = {
    ("bogra", 2021): "Mendeley Bogra-2021 duplicates Bogra-2020 365/365 days",
    ("teknaf", 2023): "Mendeley Teknaf-2023 repeats Teknaf-2022 on 332/365 days (330/334 outside July)",
}


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def save_csv(rows, name):
    path = OUT / name
    pd.DataFrame(rows).to_csv(path, index=False, float_format="%.8g")
    return path


def compare(source, author, name, year, month, delta):
    total = exact = wet_n = wet_exact = 0
    abs_sum = wet_abs_sum = 0.0
    source_items = (source.get((name, year, month), []) if month else
                    [pair for m in range(1, 13) for pair in source.get((name, year, m), [])])
    for day, src in source_items:
        check = author.get((name, day + timedelta(days=delta)))
        if check is None:
            continue
        d = abs(src - check)
        total += 1
        exact += d <= 1e-6
        abs_sum += d
        if src > 0 or check > 0:
            wet_n += 1
            wet_exact += d <= 1e-6
            wet_abs_sum += d
    return {
        "pairs": total, "exact": exact, "exact_pct": 100 * exact / total if total else np.nan,
        "mae_mm": abs_sum / total if total else np.nan,
        "wet_pairs": wet_n, "wet_exact": wet_exact,
        "wet_exact_pct": 100 * wet_exact / wet_n if wet_n else np.nan,
        "wet_mae_mm": wet_abs_sum / wet_n if wet_n else np.nan,
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    input_hashes = {str(p.relative_to(BASE)): digest(p) for p in [ORIGINAL, ERA, MENDELEY, BAMIS]}
    md, original, spans, names, source_count, source_noninteger, dupes = load_sources()
    grouped_source = defaultdict(list)
    for (station, day), rain in md.items():
        if day.year in FOCUS:
            grouped_source[(station, day.year, day.month)].append((day, rain))
    bmd = pd.read_csv(ORIGINAL, parse_dates=["date"])
    bmd["key"] = bmd.station_name.map(station_key)
    bmd["year"] = bmd.date.dt.year
    assert not bmd.duplicated(["key", "date"]).any(), "Original station/date duplicates"
    source_station_years = {(s, d.year) for s, d in md if d.year in FOCUS}
    apply_years = {(s, y) for s, y in source_station_years if y in (2021, 2023)
                   and (s, y) not in SOURCE_EXCLUSIONS}

    # Detect station-years with no numeric original observations; the source
    # cannot substitute for these missing original gauge data.
    original_numeric_by_year = bmd.groupby(["key", "year"]).prcp.count().to_dict()
    apply_years = {(s, y) for s, y in apply_years
                   if original_numeric_by_year.get((s, y), 0) > 0}
    all_keys = {(r.key, r.date.date()) for r in bmd.itertuples(index=False)}

    # Yearwise and monthly source comparisons; exact 0-mm matches alone can
    # exaggerate agreement, hence the second wet-day-specific denominator.
    annual = []
    monthly = []
    for station in sorted(set(s for s, _ in source_station_years)):
        for year in FOCUS:
            if (station, year) not in source_station_years:
                continue
            per_shift = {d: compare(grouped_source, original, station, year, None, d)
                         for d in (-1, 0, 1)}
            best = max((-1, 0, 1), key=lambda d: (per_shift[d]["wet_exact_pct"]
                       if np.isfinite(per_shift[d]["wet_exact_pct"]) else -1))
            reason = SOURCE_EXCLUSIONS.get((station, year), "")
            if year in (2021, 2023) and (station, year) not in apply_years and not reason:
                reason = "No numeric original rainfall to safely date-align"
            annual.append({"station": station, "year": year,
                           "selected_shift_for_candidate": -1 if (station, year) in apply_years else 0,
                           "diagnostic_best_wet_match_shift": best,
                           "source_status": "excluded_suspected_repetition" if reason.startswith("Mendeley")
                              else "excluded_missing_original" if reason else "comparison_only",
                           "reason": reason,
                           **{f"D{d:+d}_{k}": v for d, scores in per_shift.items()
                              for k, v in scores.items()}})
            for month in range(1, 13):
                details = {d: compare(grouped_source, original, station, year, month, d)
                           for d in (-1, 0, 1)}
                monthly.append({"station": station, "year": year, "month": month,
                                **{f"D{d:+d}_{k}": v for d, scores in details.items()
                                   for k, v in scores.items()}})
    annual_path = save_csv(annual, "station_year_exact_and_wetday_audit.csv")
    monthly_path = save_csv(monthly, "station_month_exact_and_wetday_audit.csv")

    # Cross-year duplicate check, exact days and exact wet-day pairs (including
    # zeros vs wet days); publish all pairs, not just two exclusions.
    year_pairs = []
    for st in sorted(set(s for s, _ in md)):
        for year in range(2001, 2024):
            hits, n, wet_hits, wet_n = 0, 0, 0, 0
            for month in range(1, 13):
                for day in range(1, 32):
                    try:
                        a = pd.Timestamp(year, month, day).date()
                        b = a.replace(year=year - 1)
                    except ValueError:
                        continue
                    x, y = md.get((st, a)), md.get((st, b))
                    if x is None or y is None:
                        continue
                    n += 1
                    hits += abs(x - y) < 1e-6
                    if x > 0 or y > 0:
                        wet_n += 1
                        wet_hits += abs(x - y) < 1e-6
            if n >= 300:
                year_pairs.append({"station": st, "year": year,
                                   "previous_year": year - 1,
                                   "paired_days": n,
                                   "exact_days": hits, "exact_pct": 100 * hits / n,
                                   "wet_pairs": wet_n, "wet_exact": wet_hits,
                                   "wet_exact_pct": 100 * wet_hits / wet_n if wet_n else np.nan,
                                   "risk_flag": bool(n >= 300 and wet_n >= 20
                                      and hits/n >= .90 and wet_hits/wet_n >= .65)})
    dupe_path = save_csv(year_pairs, "mendeley_adjacent_year_repetition_scan.csv")

    # Full rainfall-only author-reference and conservatively aligned scenario.
    # Every row records exactly which original date supplied its candidate.
    # We never copy Mendeley rainfall into the candidate.
    version = bmd[["station_name", "date", "record_type", "prcp", "key", "year"]].copy()
    version = version.rename(columns={"prcp": "prcp_author_original"})
    version["prcp_candidate_date_aligned"] = version.prcp_author_original
    version["candidate_from_original_date"] = version.date
    version["alignment_days"] = 0
    version["original_row_present"] = True
    version["decision"] = "unchanged"
    target_mask = pd.Series([((s, int(y)) in apply_years) for s, y
                             in zip(version.key, version.year)], index=version.index)
    # Align only on dates that actually exist in the independently released
    # station-year source; any other original dates are unmodified and flagged.
    md_dates = set(md)
    eligible = target_mask & pd.Series([((s, d.date()) in md_dates) for s, d
                                           in zip(version.key, version.date)], index=version.index)
    prev = version.loc[eligible, ["key", "date"]].copy()
    prev.date = prev.date - pd.Timedelta(days=1)
    # Author map is the numeric-only immutable source lookup, datetime.date keys.
    prev_values = np.asarray([original.get((s, d.date()), np.nan)
                              for s, d in zip(prev.key, prev.date)], dtype=float)
    version.loc[eligible, "prcp_candidate_date_aligned"] = prev_values
    version.loc[eligible, "candidate_from_original_date"] = prev.date.to_numpy()
    version.loc[eligible, "alignment_days"] = -1
    version.loc[eligible, "decision"] = "candidate_author_previous_day"
    version.loc[target_mask & ~eligible, "decision"] = "source_date_not_available_kept_original"
    for (station, year), _reason in SOURCE_EXCLUSIONS.items():
        version.loc[(version.key == station) & (version.year == year), "decision"] = (
            "unchanged_due_to_suspected_mendeley_source_repetition")
    for station, year in source_station_years - apply_years:
        if (station, year) in SOURCE_EXCLUSIONS or year == 2019:
            continue
        version.loc[(version.key == station) & (version.year == year), "decision"] = (
            "unchanged_no_numeric_author_rainfall")
    # Add source-dated missing author rows; only original preceding-day values.
    new_rows = []
    name_by_key = (bmd.drop_duplicates("key").set_index("key").station_name.to_dict())
    for station, day in sorted(md_dates):
        if (station, day.year) not in apply_years or (station, day) in all_keys:
            continue
        prevday = day - timedelta(days=1)
        new_rows.append({"station_name": name_by_key[station], "date": pd.Timestamp(day),
                         "record_type": "long", "prcp_author_original": np.nan,
                         "key": station, "year": day.year,
                         "prcp_candidate_date_aligned": original.get((station, prevday)),
                         "candidate_from_original_date": pd.Timestamp(prevday),
                         "alignment_days": -1, "original_row_present": False,
                         "decision": "added_missing_target_date_from_previous_author_day"})
    version = pd.concat([version, pd.DataFrame(new_rows)], ignore_index=True)
    version["prcp_candidate_date_aligned"] = pd.to_numeric(
        version["prcp_candidate_date_aligned"], errors="coerce")
    assert not version.duplicated(["key", "date"]).any()
    assert ((version.prcp_candidate_date_aligned.dropna() >= 0).all())
    assert len(version) >= len(bmd)
    version = version.sort_values(["station_name", "date"])
    version["date"] = version.date.dt.strftime("%Y-%m-%d")
    version["candidate_from_original_date"] = version.candidate_from_original_date.dt.strftime("%Y-%m-%d")
    version["mendeley_processed_rain_mm"] = [md.get((s, pd.Timestamp(d).date()), np.nan)
                                               for s, d in zip(version.key, version.date)]
    version["candidate_matches_mendeley"] = np.where(
        version.mendeley_processed_rain_mm.notna() & version.prcp_candidate_date_aligned.notna(),
        np.isclose(version.mendeley_processed_rain_mm.fillna(-999999),
                   version.prcp_candidate_date_aligned.fillna(-888888), atol=1e-6), np.nan)
    version["candidate_warning"] = np.where(version.alignment_days.eq(-1),
        "date-label hypothesis; not authenticated by original BMD archive", "")
    full_path = OUT / "bmd_rainfall_only_date_alignment_CANDIDATE_not_BMD_raw.csv"
    version.drop(columns=["key", "year"]).to_csv(full_path, index=False, float_format="%.8g")

    ledger = []
    for row in version.loc[(version.year.isin(FOCUS)) &
                           (version.decision.ne("unchanged"))].itertuples(index=False):
        if (not row.original_row_present) or pd.isna(row.prcp_candidate_date_aligned):
            ledger.append({"station_name": row.station_name, "date": row.date,
                           "decision": row.decision, "candidate_from_original_date": row.candidate_from_original_date,
                           "author_original_mm": row.prcp_author_original,
                           "candidate_mm": row.prcp_candidate_date_aligned,
                           "mendeley_processed_mm": row.mendeley_processed_rain_mm})
    ledger_path = save_csv(ledger, "candidate_missing_date_and_null_ledger.csv")

    # Frozen predictions: score all three labels over the exact same date rows
    # within each held-out station/year, excluding anomalous source station-years.
    era = pd.read_csv(ERA, parse_dates=["date"])
    era = era.sort_values(["station_name", "date"]).reset_index(drop=True)
    era["row_id"] = np.arange(len(era), dtype=np.int64)
    frame_by_id = era.set_index("row_id")[["station_name", "date", "prcp"]]
    cand_map = {(row.key, pd.Timestamp(row.date).date()): row.prcp_candidate_date_aligned
                for row in version.itertuples(index=False)}
    individual = []
    pooled = defaultdict(lambda: [[], []])
    checked_folds = 0
    for path in sorted(FOLDS.glob("loso*Prcp.npz")):
        with np.load(path) as z:
            ids = z["row_id"]
            frame = frame_by_id.loc[ids]
            if frame.station_name.nunique() != 1:
                raise RuntimeError("Saved fold contains more than one station: " + path.name)
            raw_match = np.isclose(z["RAW"], frame.prcp.to_numpy(dtype=float), rtol=1e-8, atol=1e-8)
            if raw_match.mean() < .9999:
                raise RuntimeError("Saved RAW not aligned with ERA row_id: " + path.name)
            checked_folds += 1
            station = str(frame.station_name.iloc[0]); key = station_key(station)
            days = [d.date() for d in frame.date]
            years = np.array([d.year for d in days]);
            orig = np.array([original.get((key, d), np.nan) for d in days], dtype=float)
            aligned = np.array([cand_map.get((key, d), np.nan) for d in days], dtype=float)
            public = np.array([md.get((key, d), np.nan) for d in days], dtype=float)
            # Suppress source-repetition station-years, even though author data
            # may still exist; the three-way comparison then remains honest.
            for year in FOCUS:
                if (key, year) not in source_station_years or (key, year) in SOURCE_EXCLUSIONS:
                    continue
                year_mask = years == year
                same_mask = year_mask & np.isfinite(orig) & np.isfinite(aligned) & np.isfinite(public)
                if not same_mask.any():
                    continue
                labels = {"author_original": orig[same_mask],
                          "date_aligned_author_candidate": aligned[same_mask],
                          "mendeley_processed_source": public[same_mask]}
                for method in [x for x in z.files if x != "row_id"]:
                    pred = z[method][same_mask]
                    for scenario, obs in labels.items():
                        score = finite_score(pred, obs)
                        individual.append({"station": station, "year": year,
                                           "method": method, "label_scenario": scenario,
                                           "shared_three_way_support": True,
                                           "frozen_predictions_not_retrained": True, **score})
                        pooled[(year, method, scenario)][0].append(pred)
                        pooled[(year, method, scenario)][1].append(obs)
    if checked_folds != 34:
        raise RuntimeError(f"Expected exactly 34 saved folds, found {checked_folds}")
    preds_path = save_csv(individual, "frozen_predictions_station_year_scenarios.csv")
    pooled_rows = []
    for (year, method, scenario), (preds, obs) in sorted(pooled.items()):
        pooled_rows.append({"year": year, "method": method,
                            "label_scenario": scenario,
                            "station_count": len(preds),
                            "shared_three_way_support": True,
                            "frozen_predictions_not_retrained": True,
                            **finite_score(np.concatenate(preds), np.concatenate(obs))})
    pooled_path = save_csv(pooled_rows, "frozen_predictions_pooled_scenarios.csv")

    assert digest(ORIGINAL) == input_hashes[str(ORIGINAL.relative_to(BASE))], "Original BMD was changed"
    assert digest(ERA) == input_hashes[str(ERA.relative_to(BASE))], "Original ERA was changed"
    assert digest(MENDELEY) == input_hashes[str(MENDELEY.relative_to(BASE))]
    summary = {
        "inputs_sha256": input_hashes,
        "output_files_sha256": {p.name: digest(p) for p in [annual_path, monthly_path,
            dupe_path, full_path, ledger_path, preds_path, pooled_path]},
        "mendeley_rows": source_count,
        "mendeley_noninteger_rainfall_rows": source_noninteger,
        "mendeley_duplicate_station_dates": dupes,
        "original_author_rows": len(bmd),
        "candidate_rows": len(version),
        "added_candidate_dates": len(new_rows),
        "date_shifted_rows": int(version.alignment_days.eq(-1).sum()),
        "candidate_nulls_in_shifted_rows": int(version.loc[version.alignment_days.eq(-1),
                                                "prcp_candidate_date_aligned"].isna().sum()),
        "eligible_shift_station_years": len(apply_years),
        "source_excluded": [{"station": s, "year": y, "reason": v} for (s, y), v
                            in SOURCE_EXCLUSIONS.items()],
        "scored_saved_loso_folds": checked_folds,
        "saved_models_retrained": False,
        "frozen_scores_common_support": True,
        "scenario_scope": "2019, 2021, 2023; source anomalies excluded from three-way model sensitivity",
        "date_labels_authentication": "unverified; publisher's processed release is not original BMD metadata",
        "official_bmd_email_status": "request sent by author, reply not yet supplied",
        "bamis_spotcheck": json.loads(BAMIS.read_text(encoding="utf-8"))["annual_shift_tests"],
    }
    (OUT / "reconciliation_manifest.json").write_text(json.dumps(summary,
        ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k not in
          {"inputs_sha256", "output_files_sha256", "bamis_spotcheck"}}, indent=2))


if __name__ == "__main__":
    main()
