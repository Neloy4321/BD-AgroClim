# Rainfall date-label audit: public subset

The code, reviewer instructions, and aggregate date-shift comparisons in this folder are available without releasing the author's confidential station-day BMD data.

## Included

- `REVIEWER_README.md` — read the results table and interpret limitations first.
- `station_year_exact_and_wetday_audit.csv` — each station/year, D−1, D+0 and D+1 comparison with exact numeric and wet-day-only percentages.
- `station_month_exact_and_wetday_audit.csv` — monthly comparison for suspected 2019, 2021 and 2023 patterns.
- `mendeley_adjacent_year_repetition_scan.csv` — detected suspicious duplicate source-year patterns.
- `frozen_predictions_pooled_scenarios.csv` and `frozen_predictions_station_year_scenarios.csv` — common-support frozen-model evaluation **without retraining**.
- `Rainfall_Date_Reviewer_Audit.xlsx` — four summary/aggregate worksheet views, **not** original daily observations.
- `SUPPLEMENTARY_TIMING_SENSITIVITY_DRAFT.tex` — draft supplementary table text.
- `reconciliation_manifest.json` — provenance and SHA-256 listings of source inputs that **remain private**.
- `code/reconcile_bmd_date_candidates.py`, `code/verify_reconciliation.py` and `code/audit_mendeley_bmd_alternative.py` — re-run procedures when the original private inputs are available.

## Excluded deliberately

The reviewer README mentions `bmd_rainfall_only_date_alignment_CANDIDATE_not_BMD_raw.csv` and `candidate_missing_date_and_null_ledger.csv`; these are **not** published because they carry observation-level author records and partly copied secondary-source values. They are internal *hypothetical* sensitivity artifacts, not certified BMD corrections.

The independently distributed secondary archive is available directly at [Mendeley Data DOI 10.17632/tbrhznpwg9.1](https://doi.org/10.17632/tbrhznpwg9.1). Its original uploader labels the release CC BY 4.0. The earlier research and this audit do **not** claim that the 2021/2023 preceding-date alignment is a BMD-certified historical convention. No observed data were secretly replaced in the main model inputs.
