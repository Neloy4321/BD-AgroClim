# BD-AgroClim: Bangladesh ERA5-Land bias-correction transfer evidence

**Research subject:** Spatial transfer and metric dependence of daily ERA5-Land bias correction across a Bangladesh meteorological-station network (2000–2023).

**Authors/research team:** Neloy Pramanik Supto, Sajib Biswas, and Sazal Das.

**Evidence snapshot:** 10 November 2026. This is a computational evidence release for a manuscript in preparation, **not** a publication of authenticated original Bangladesh Meteorological Department (BMD) observations.

## Research questions and key findings

1. Can daily ERA5-Land temperature and precipitation errors be reduced at *held-out stations* using correction models trained on other stations?
2. Does adding terrain information or separating donor and test stations geographically reliably improve transfer?
3. Do daily precipitation scores agree with wet-day detection, heavy-rain events and annual climate-index scores?

For 34 ERA5-Land-native, station-held-out sites, station-mean daily RMSE (raw ERA5-Land → locally trained Extra Trees correction) is **2.2293 → 1.3169 °C** for Tmax, **1.6040 → 1.3702 °C** for Tmin, and **16.7208 → 15.2924 mm/day** for precipitation. These comparisons reflect the author-processed dates and the original saved model folds.

**Important negative results:** For precipitation, annual Rx1day index RMSE worsens from **92.819 to 108.429 mm** after correction (33 of 34 stations worse); annual R10mm count RMSE worsens from **16.733 to 25.183 days**. Ordinary wet-day (≥1 mm/day) CSI decreases from **0.565 to 0.536**. Additional static terrain information also worsens native LOSO Tmax RMSE from 1.3169 to 1.3775 °C. Full denominators, sensitivity results and limits are in [the executed results report](pre_manuscript_run_20261110/PRE_MANUSCRIPT_EXECUTED_RESULTS_20261110.md).

## Find the evidence

| Evidence | Location |
|---|---|
| Full executed results and limitations | [`pre_manuscript_run_20261110/PRE_MANUSCRIPT_EXECUTED_RESULTS_20261110.md`](pre_manuscript_run_20261110/PRE_MANUSCRIPT_EXECUTED_RESULTS_20261110.md) |
| Reproduction walkthrough (.ipynb) | [`pre_manuscript_run_20261110/Pre_Manuscript_Reproduce_One_Click.ipynb`](pre_manuscript_run_20261110/Pre_Manuscript_Reproduce_One_Click.ipynb) |
| Original verified author method modules | [`research_rebuild/code/paper1_pipeline/`](research_rebuild/code/paper1_pipeline/) |
| Run orchestration and model/partition code | [`research_rebuild/code/run_research.py`](research_rebuild/code/run_research.py) |
| Verification scripts | [`research_rebuild/reporting/`](research_rebuild/reporting/) |
| New annual/event/physical-consistency analysis scripts | [`pre_manuscript_run_20261110/run_remaining_analytics.py`](pre_manuscript_run_20261110/run_remaining_analytics.py), [`run_station_index_tradeoffs.py`](pre_manuscript_run_20261110/run_station_index_tradeoffs.py) |
| Reanalysis-source audit scripts and publicly documented station metadata caveats | [`source_recovery_kit/`](source_recovery_kit/) |
| Full same-day / preceding-day / following-day rainfall source comparison by station and year | [`rainfall_date_audit/`](rainfall_date_audit/) |
| Summary tables (CSV) | [`pre_manuscript_run_20261110/new_analysis/`](pre_manuscript_run_20261110/new_analysis/) |
| Annual/event large **derived** station-year tables | [`pre_manuscript_run_20261110/new_analysis/`](pre_manuscript_run_20261110/new_analysis/) (`.csv.gz`: decompress before use) |
| Reviewer-ready figures (PNG and PDF) | [`pre_manuscript_run_20261110/figures/`](pre_manuscript_run_20261110/figures/), [`new_analysis/`](pre_manuscript_run_20261110/new_analysis/) |
| LaTeX-draft numerical tables | [`pre_manuscript_run_20261110/MANUSCRIPT_TABLES_DRAFT.tex`](pre_manuscript_run_20261110/MANUSCRIPT_TABLES_DRAFT.tex) |
| SHA-256 validation manifest and independent checks | [`pre_manuscript_run_20261110/PACKAGE_MANIFEST_SHA256.json`](pre_manuscript_run_20261110/PACKAGE_MANIFEST_SHA256.json), [`validation/`](pre_manuscript_run_20261110/validation/) |
| Dataset access, rights and outstanding evidence | [`DATA_AVAILABILITY.md`](DATA_AVAILABILITY.md) |
| Exact reproduction conditions | [`REPRODUCIBILITY.md`](REPRODUCIBILITY.md) |

## Verification at a glance

- 7/7 input-quality checks passed; source input counts: 326,861 **private BMD-derived processed observation rows** and 348,756 **reanalysis rows**.
- 7/7 recovered author-code modules matched reference code fingerprints.
- 191/191 original saved experimental jobs passed frozen-prediction, train/test-mask and geometry audits. **This release does not claim they were retrained in November 2026.**
- 408/408 LOSO RMSE values were recomputed from saved predictions (largest absolute discrepancy 3.55 × 10⁻¹⁵).
- 24 recovered original-format yearly Earth Engine CSVs were audited: 3,876,190 numeric comparisons, none differing by more than 10⁻⁷ at the specified comparison tolerance.

## Critical qualifications

**Rainfall dates:** Some 2021/2023 independent bulletin comparisons suggest a preceding-calendar-day mapping. That does **not** establish a universal yearly shift. Neither the original BMD historical date convention nor authenticated original BMD daily observations have been delivered by BMD. Rainfall and annual extreme indices therefore remain conditional on *author-processed* observation dates.

The independent date-label comparison uses the open secondary dataset [*High Volume Real-World Weather Data* (Mendeley Data, DOI 10.17632/tbrhznpwg9.1)](https://data.mendeley.com/datasets/tbrhznpwg9/1). Its CC BY 4.0 publishing licence does not certify that all of its interpolated/processed daily values are original BMD readings. The audit reports 2019 same-date agreement of **90.22%**, while 2021 and 2023 previous-date agreement is **95.76%** and **95.07%**, respectively, before QC exclusions. Zero-rain values may inflate exact-match percentages; examine wet-day-only tables. These comparisons are **not** BMD confirmation.

**Locations:** The historical positions and relocation dates of the 36 nominal BMD stations have not been certified; the author-point coordinates are draft metadata. The evaluated 34-site network does not establish generalization to a different national observing network.

**Reproducibility levels:** The included code, aggregate tables, exported audit reports and figures are openly inspectable. End-to-end retraining or recomputing every daily score requires privately held BMD-derived input observations and saved frozen predictions, which are **not public**; see [`DATA_AVAILABILITY.md`](DATA_AVAILABILITY.md). The original Earth Engine script was not recovered, although a clearly labelled reconstruction and source audit are supplied.

## Ethical use

Please cite the eventual paper and this repository commit when reusing derived figures, code or aggregate tables. Do not describe these files as an official release or validation of BMD's primary archive. Do not infer, redistribute or reverse-engineer unlicensed station-day observations from the derived outputs.

