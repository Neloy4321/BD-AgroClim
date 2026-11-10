# Reproducibility instructions and verification scope

## Software

Python 3.11+ is recommended. The code uses `numpy`, `pandas`, `scipy`, `scikit-learn`, `matplotlib`, `threadpoolctl`, and (where selected) `xgboost` or `lightgbm`. Package version information in historical run evidence should take precedence over a fresh install. Install the audited minimum packages with `pip install -r requirements.txt` in a separate environment.

## Verify the public evidence without private raw observations

1. Inspect `pre_manuscript_run_20261110/validation/recomputed/verification.json` and `validation/splits/split_geometry_verification.json`.
2. Inspect `pre_manuscript_run_20261110/era_source/recovered_gee_audit_summary.json` (original-format export comparisons).
3. Check the source- and method-level observations in `pre_manuscript_run_20261110/PRE_MANUSCRIPT_EXECUTED_RESULTS_20261110.md`.
4. Review `pre_manuscript_run_20261110/new_analysis/*.csv` and `pre_manuscript_run_20261110/new_analysis/*.csv.gz`. Decompress `.gz` files before reading. These are *already computed aggregates*, not synthetic reproductions.
5. The figure PDF/PNG outputs live under `pre_manuscript_run_20261110/figures` and `new_analysis`; no figure was generated from invented proxy values.

## Re-run analyses from the privately held author inputs

The full calculation needs the original relative directories `research_v2/input/dataset/` and `research_rebuild/results/jobs/`. These data and prediction archives are **not committed to this public repository**. Preserve the original relative file layout (see `research_rebuild/code/paper1_pipeline/core.py`). From the project root:

```bash
python research_rebuild/reporting/audit_inputs.py --input research_v2/input/dataset --output pre_manuscript_run_20261110/validation/input_quality.json
python research_rebuild/reporting/audit_splits.py --input research_v2/input/dataset --results research_rebuild/results --output pre_manuscript_run_20261110/validation/splits
python research_rebuild/reporting/build_report.py --results research_rebuild/results --reports pre_manuscript_run_20261110/validation/recomputed --figures pre_manuscript_run_20261110/figures --prior research_rebuild/evidence/author_reference/loso_station_metrics.csv
python pre_manuscript_run_20261110/run_remaining_analytics.py
python pre_manuscript_run_20261110/run_station_index_tradeoffs.py
```

The included one-click notebook is intended for the **complete local project**, with its source inputs and saved jobs. It is **not** executable end-to-end from a GitHub clone alone. A model training rerun is expensive and has **not** been represented as part of this November audit.

## Comparison units

- Native LOSO site support: 34 station sites with native ERA5-Land support; user metadata contain 36 nominal observation stations.
- Duration: processed archive 2000–2023; every result states its own valid-year/day support.
- Daily RMSE: mean of station-specific held-out daily RMSE (not pooled all-station RMSE).
- Annual index RMSE: computed from annual index errors, aggregated by station; distinct from daily RMSE.
- Heavy-rain thresholds: 1, 10, 20, 50 mm/day, evaluated on the **same** supported station-days for a given comparison.
- Station-paired bootstrap intervals are descriptive, not spatially independent coverage guarantees.

## Provenance caveats

Do not promote this archive as proof that the **original** Google Earth Engine script was recovered, that BMD validated the author-processed rain dates, that station coordinates were stable historically, or that evaluation-year exclusion is a full retraining or a leakage-free reconstruction.

