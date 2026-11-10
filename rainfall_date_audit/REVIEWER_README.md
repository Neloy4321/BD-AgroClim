# Bangladesh rainfall date-label forensic reconciliation — 10 November 2026

**Status: sensitivity analysis and explicitly hypothetical labels; not a certified replacement for original BMD data.**

Project: *When does daily reanalysis bias correction transfer?* (Bangladesh, 2000–2023).

## Executive result

The author's processed `bmd_clean_daily.csv` was compared with a separately published, **processed** BMD-derived Mendeley rainfall compilation covering 35 named stations, and with limited publicly archived BAMIS daily reports. Same-day agreement is largest in 2019; the preceding author calendar date agrees best with the public source date in 2021 and 2023. Matching two differently processed datasets does **not** authenticate an original BMD observation window, station relocation history, or a universally correct temporal shift.

| Source year | Author same-date exact | Author previous-date exact | Evaluation denominator |
|---|---:|---:|---:|
| 2019 | 90.22% (11,525/12,775) | 57.46% (7,341/12,775) | All 35 matched stations |
| 2021 | 59.88% (7,355/12,282) | 95.76% (11,761/12,282) | All 35 incl. suspect Bogra, empty-original Ambagan |
| 2023 | 61.27% (7,624/12,444) | 95.07% (11,831/12,444) | All 35 incl. suspect Teknaf |
| 2021, exception removed | 60.00% | **96.99%** | 33 comparable station-years after excluding Bogra and entirely missing Ambagan |
| 2023, exception removed | 61.24% | **95.83%** | 34 comparable station-years after excluding Teknaf |

Exact agreement means values differ by no more than 0.000001 mm. Percentages describe a **cross-source comparison of available numeric pairs**, not proportion of verified raw observations. Zero-rain agreement can be misleading; `station_year_exact_and_wetday_audit.csv` and `station_month_exact_and_wetday_audit.csv` also report rainy-day-only matches and MAE.

## Public-source anomalies (do not silently fix or use as original truth)

1. **Mendeley Bogra, 2021:** all 365 daily rainfall values repeat Mendeley Bogra 2020 exactly, including 122 wet-in-either daily pairs. Excluded from the proposed shift and three-way frozen-prediction comparison.
2. **Mendeley Teknaf, 2023:** 332/365 dates repeat Teknaf 2022, with 330/334 outside July and 90/123 identical wet-in-either-day pairs. Excluded likewise.
3. **Other source repetition:** all comparable 365 daily values repeat across several Mendeley Chittagong early-2000s year pairs, and Sandwip 2002→2003; see `mendeley_adjacent_year_repetition_scan.csv`. The source must not be characterized as untouched, independent raw BMD gauge measurements.
4. **2019 residual mismatch:** same-day is the best yearwide source match but some stations and months remain substantially different (for example, Mymensingh). No values from Mendeley are copied to the author's file.
5. **Missing/imputed data:** the Mendeley release is described by its authors as processed with linear interpolation. There are 771 noninteger rainfall values in the combined source. This count is **not** an estimate of all imputed values: an interpolated result may be integer. The author's own missing/filled flags and source cleaning trail remain unverified.

## Candidate file: interpretation and exact generation rules

`bmd_rainfall_only_date_alignment_CANDIDATE_not_BMD_raw.csv` contains **326,861 rows** corresponding to the author's processed BMD rows. Its columns retain the original value separately and show a candidate value, source date, status, and independent processed public-source comparison.

- **2019:** candidate = original author date D; none of the 2019 mismatch values is overridden.
- **2021 and 2023:** for **67 eligible station-years** and source date D, candidate(D) = author original(D−1); this affects **24,455** date-labelled rows. It is a separate hypothesis, **not** a BMD-certified correction or an observed rainfall re-extraction.
- **Bogra 2021 and Teknaf 2023:** no date shift, because the public source is suspiciously repeated year-to-year.
- **Ambagan 2021:** no date shift because author rainfall has no numeric values for that year; no third-party values are silently imported.
- If author(D−1) is missing, the candidate remains blank. **418** shifted target rows have missing candidate rainfall; no fabricated interpolation occurs.
- Every original station/date row already exists (including missing rainfall dates); **zero new rows** were inserted. Station/date uniqueness and nonnegative candidate rainfall are checked.
- **Temperature variables are not shifted.** This is a **rainfall-only** scenario; joining it to other climate variables and retraining without physical observation-window evidence would be premature.
- All dates are kept in ISO form, and `candidate_from_original_date` records exactly which original date supplied the hypothetical rainfall value.

## Saved predictions: sensitivity, not retrained performance

The code used the author's **34 saved seed-42 leave-one-station-out precipitation prediction folds**, checking each fold's `RAW` vector against the processed ERA5-Land row IDs. Every scenario for each station-year uses exactly the same finite observation/prediction support; 2019 has 33 comparable folds, 2021 has 31, and 2023 has 32. Bogra 2021 and Teknaf 2023 are excluded from the public-source three-way comparison. The three compared labels are original author, shifted-author candidate, and public processed Mendeley.

| Year | Held-out days | Raw ERA5 vs original RMSE (mm) | vs shifted-author RMSE | vs Mendeley RMSE | ET_LOCAL vs original RMSE | vs shifted-author RMSE |
|---|---:|---:|---:|---:|---:|---:|
| 2019 | 12,045 | 15.494 | 15.494 | 16.026 | 14.113 | 14.113 |
| 2021 | 11,095 | 13.949 | **15.786** | 15.724 | 13.758 | **14.661** |
| 2023 | 11,325 | 15.233 | **17.663** | 18.001 | 15.194 | **16.304** |

**Critical interpretation:** A label sequence can agree better with another processed source while performing *worse* against a frozen prediction model trained/evaluated with the original label sequence. Neither score determines the correct physical observation window; selecting the better score as the "true" date would be invalid. These RMSEs are not re-trained or leakage-free corrected model results and **must not replace published baseline model scores**. See `frozen_predictions_pooled_scenarios.csv` for RAW/MONTHLY/ET_LOCAL/ET_TERRAIN, plus CSI and correlation, and `frozen_predictions_station_year_scenarios.csv` for station-level scores.

## External sample corroboration and remaining uncertainties

The previously downloaded BAMIS daily-report CSV spotchecks showed 98/98 exact pairs in May 2021 using the author previous calendar day, 103/106 in September 2023 using previous day, and 75/76 in July 2022 using the same day. These support a **year-specific report-label disagreement**, not a certified measurement start/end time. The 2019 BMD bulletin sample matches the author's same-calendar date. Repetition, interpolation, draft station metadata and coordinate ambiguity are distinct outstanding limitations.

The original-format **48 ERA5-Land annual Drive CSV exports were recovered separately** in `source_recovery_kit/drive_exports_original/` (24 main + 24 island annual exports). Existing raw-to-processed audit found **3,876,190 numeric matches within 1e−7** after unit conversions and clipping, but the historical Code Editor script, task IDs, reducer metadata and original station-location certificates were not recovered. The new `gee_era5land_daily_extract.js` is a documented *reconstruction*, not the original script.

## Submission decision with 2–3 days remaining

1. **Do not replace the manuscript's core measured results** with the hypothetical shifted-label scores. Do not call this candidate "corrected BMD ground truth".
2. Add the source comparison as a **robustness/provenance sensitivity** finding in a supplement, if the journal permits this pre-submission, with this explicit uncertainty and the frozen-prediction caveat.
3. State that the raw BMD observation-date protocol, historical station moves and some source cleaning/interpolation are **not yet authenticated**. The BMD request has been sent, but lack of a reply is not itself proof of a shift.
4. If evidence supports material label/date or coordinate changes later, rerun the actual training, spatial cross-validation and LO(S)O evaluation consistently. Do not treat unchanged trained predictions as newly validated models.
5. Keep BMD files private unless redistribution authorization is documented. The publicly released Mendeley source carries separate publication attribution and conditions.

## File guide

| File | Purpose |
|---|---|
| `bmd_rainfall_only_date_alignment_CANDIDATE_not_BMD_raw.csv` | Original rainfall next to hypothetical aligned rainfall, row-level source date/flags |
| `station_year_exact_and_wetday_audit.csv` | Per-station/year same/previous/next comparison, numeric and wet-day metrics |
| `station_month_exact_and_wetday_audit.csv` | Monthly diagnostic for all three years |
| `mendeley_adjacent_year_repetition_scan.csv` | All 300+-day adjacent-year checks; flag repeated source values |
| `candidate_missing_date_and_null_ledger.csv` | All missing candidate outcomes and target-date issues |
| `frozen_predictions_pooled_scenarios.csv` | Common-support pooled metrics across saved folds |
| `frozen_predictions_station_year_scenarios.csv` | Common-support station/year metrics |
| `reconciliation_manifest.json` | Input/output SHA-256, counts, independent BAMIS spotcheck summaries |
| `reconcile_bmd_date_candidates.py` | Re-run engine, reads local original inputs but does not edit them |
| `run_reconciliation.ipynb` | Run-all wrapper for the same source-level checks; requires the author's local project inputs |
| `Rainfall_Date_Reviewer_Audit.xlsx` | Brief reader-facing station/year, anomaly and model-score audit |

### Reproducibility

The script assumes the user's `research_v2/` directory layout, the Mendeley ZIP stored under `research_v2/outputs/`, and the 34 `.npz` folds under `research_v2/evidence_inputs/saved_frozen_predictions/`. With `numpy`, `pandas`, `scipy`, `scikit-learn`, `matplotlib` installed, run from the project root:

```bash
python research_v2/outputs/reconcile_bmd_date_candidates.py
```

Input byte hashes and output hashes are recorded by `reconciliation_manifest.json`; the script asserts the main original input bytes are unchanged. These outputs represent a **new candidate version**, not replacement files for the author's existing dataset.

### Suggested cautious manuscript wording (if adding a supplement)

> As a provenance sensitivity analysis, we compared author-processed BMD rainfall records against a separately published BMD-derived, subsequently processed station dataset and available archived daily bulletins. Same-day matching dominated in 2019, whereas author-date-minus-one-day matching dominated in 2021 and 2023. Exceptions including suspected repeated station-year source records prevented us from treating the secondary compilation as authoritative observation metadata. We therefore retain the original training/evaluation labels, make date-alignment hypotheses explicit, and report frozen-prediction re-scoring only as a sensitivity diagnostic rather than a corrected model performance estimate. Original BMD observation-window and historical station-site metadata remain subject to confirmation.
