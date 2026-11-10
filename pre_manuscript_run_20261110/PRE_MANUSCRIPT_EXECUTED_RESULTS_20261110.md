# Pre-Manuscript Executed Scientific Results and Decision Register

**Project:** Spatial Transfer and Metric Dependence of Daily ERA5-Land Bias Correction: A Bangladesh Station-Network Evaluation  
**Author team:** Neloy Pramanik Supto, Sajib Biswas and Sazal Das  
**Audit completed:** 10 November 2026 (Asia/Dhaka)  
**Status:** All analyses that can be defensibly run with the available processed observations, preserved training outputs and recovered exports have been executed. **Original BMD observation-date authentication, historical coordinates and the original GEE script remain unavailable.**

## 1. What was actually run

| Independent operation | Verified result | Output |
|---|---|---|
| Input validation | **7/7 checks PASS**, 326,861 processed BMD rows, 348,756 processed ERA rows; original files unchanged | `validation/input_quality.json` |
| Source-code provenance | **7/7** author notebook-code modules match recovered files | `validation/source_provenance.json` |
| Frozen model file, mask and geometry audit | **191/191 saved jobs PASS**, 34 trainable ERA-native stations, 25 design/target groups, zero split errors | `validation/splits/` |
| Model score recomputation | **191/191 saved jobs verified**; 4,216 station-method metric records, 124 summary rows | `validation/recomputed/` |
| Previous author RMSE replication | **408/408 native LOSO station-level RMSE** reproduced; maximum absolute difference **3.55 × 10⁻¹⁵** | `validation/recomputed/verification.json` |
| Recovered original-format reanalysis CSV audit | **24 calendar-year GEE export CSVs**, 315,576 source rows, **3,876,190 numeric-field comparisons**, zero differences above 10⁻⁷ | `era_source/recovered_gee_audit_summary.json` |
| Independent date/coordinate/feature sensitivity | Executed, including 34 precipitation frozen prediction folds and station geometry | `integrated/` |
| New frozen-LOSO year-wise metrics | **102 LOSO prediction arrays** rejoined by held-out row ID, **9,708 station-year-method records** | `new_analysis/daily_station_year_metrics.csv` |
| New heavy-rain event analysis | **12,960 station-year-method-threshold records**, thresholds 1, 10, 20 and 50 mm/day | `new_analysis/rainfall_event_station_year.csv` |
| New climate-index analysis | **22,420 station-year-method-index records**, station-year coverage ≥95% | `new_analysis/annual_climate_index_station_year.csv` |
| Station-paired climate index trade-offs | 34-station descriptive paired comparison; separate analysis of all years, exclusions and **100%-complete years** | `new_analysis/annual_index_paired_station_tradeoffs.csv` and `annual_indices_completeness_sensitivity.csv` |
| NASA POWER versus uncorrected ERA5-Land | Recomputed raw-product comparisons on common valid rows; **not comparable with 34-site LOSO because the raw product baseline covers 36 sites** | `new_analysis/product_benchmarks/baseline_metrics.csv` |

The underlying 191 model jobs were not wastefully retrained: their train/test signatures and stored predictions were independently revalidated. The **new** analyses above are genuine new computations on frozen held-out predictions, not claims of model refitting or revised rain-date training.

## 2. Main reproducible station-held-out model results

**Unit:** mean of station-specific RMSE over **34 native ERA5-Land stations**, 2000–2023 processed dataset, no held-out station used in that model's training.

| Target | ERA5 raw | Monthly | ET local | ET + terrain | ET-local improvement vs raw | ET local improves stations |
|---|---:|---:|---:|---:|---:|---:|
| Tmax (°C) | 2.2293 | 1.5085 | **1.3169** | 1.3775 | **40.93%** | **34/34** |
| Tmin (°C) | 1.6040 | 1.5127 | **1.3702** | 1.4240 | **14.58%** | **31/34** |
| Rainfall (mm/day) | 16.7208 | 16.8362 | **15.2924** | 15.3098 | **8.54%** | **34/34** |

These values come from `new_analysis/daily_model_subset_summary.csv`; the paired effects are in `new_analysis/daily_paired_station_effects_by_year_subset.csv`. The rainfall estimates are **conditional on the processed date labels**, which independent external checks dispute for some years.

The 100-km buffered spatial donor-exclusion evaluation reduced Tmax RMSE from **2.2293°C to 1.4635°C**, a **34.35%** station-mean improvement. It is within-network evaluation under provisional site coordinates, not independent geographic-network validation. Additional spatial-block, future-year, space-time and alternative geographic partition results are preserved in `validation/recomputed/SCIENTIFIC_RESULTS.md`.

**Negative terrain result:** Adding static terrain to ET local worsened Tmax LOSO RMSE from 1.3169 to 1.3775°C and helped only **6/34** stations. This counters claims of universally beneficial terrain correction.

## 3. Annual climate indices: most important new trade-off

This analysis computes annual statistics from the **same frozen held-out daily predictions** for each index and method, with **at least 95% valid days in each calendar year**. Annual index RMSE is first computed per station and then averaged across the 34 stations. This is *not* the RMSE of daily predictions.

| Annual index | Station-year pairs | ERA5 raw index RMSE | ET local index RMSE | Station wins for ET local | Interpretation |
|---|---:|---:|---:|---:|---|
| TXx: annual hottest daily Tmax (°C) | 797 | 1.815 | **1.219** | **32/34** | Better |
| TNn: annual coldest daily Tmin (°C) | 793 | 2.459 | **1.591** | **31/34** | Better |
| PRCPTOT: annual wet-day precipitation sum (mm) | 803 | 559.265 | **455.599** | **24/34** | Better |
| R10mm: number of days ≥10 mm | 803 | **16.733** | 25.183 | **7/34** | **Worse**, frequent false wet-day intensity |
| R20mm: number of days ≥20 mm | 803 | 11.399 | **11.187** | 18/34 | Small, mixed difference |
| Rx1day: largest single daily rain (mm) | 803 | **92.819** | 108.429 | **1/34** | **Worse in 33/34 stations** |
| Rx5day: largest consecutive five-day rain (mm) | 803 | **152.350** | 152.462 | 19/34 | Essentially no advantage |

Station paired bootstrap intervals are **descriptive only**, since neighboring stations and common fitted models do not provide independent sampling units. The ±95% interval reported in these outputs is **not a formal spatially independent confidence statement**.

### Extreme-result robustness to data completeness

With **100%-complete station-years** instead of ≥95%, there are **731 rainfall station-years** (versus 803). Rx1day mean station index RMSE remains **91.483 mm RAW versus 107.164 mm ET local**; R10mm days remains **17.134 versus 25.752**. The qualitative trade-off therefore survives a strict missing-data filter. All derived values remain provisional with respect to source date mapping.

### Source-date sensitivity (do not mix up with corrected retraining)

When only **2021 and 2023 evaluation rows** are excluded, annual Rx1day error remains **91.620 mm RAW versus 107.006 mm ET local** (740 station-years). At the station level, ET local still loses Rx1day in **33/34** sites. Excluding **2019 as well** is computed separately in the CSV files.

**Important:** evaluation-year exclusions do **not** remove these years from the original saved models' training folds. This is a test-population sensitivity analysis, **not** source-provenance-corrected retraining.

## 4. Rainfall event skill, same days and stations

Pooled held-out station-day rain-event contingency matrix, 34 native sites, 295,141 valid station-days. Here CSI=hits/(hits+misses+false alarms), POD=hits/(hits+misses), and FAR=false alarms/(hits+false alarms).

| Threshold | ERA5 raw CSI | ET local CSI | Interpretation |
|---|---:|---:|---|
| ≥1 mm/day | **0.565** | 0.536 | ET local worse for ordinary wet-day detection |
| ≥10 mm/day | 0.344 | **0.397** | ET local better |
| ≥20 mm/day | 0.236 | **0.279** | ET local better |
| ≥50 mm/day | 0.102 | **0.122** | Relative gain but **low absolute skill** |

At ≥50 mm/day ET local has **1,392 hits**, **8,400 misses**, **1,649 false alarms**; **POD=0.142** and **FAR=0.542**. A 0.122 CSI is not good extreme-event forecasting skill despite the improvement over 0.102 raw CSI. All four thresholds were pre-specified in the analysis script rather than selected post hoc.

## 5. Interannual source-date sensitivity, including the specific disputed years

Year-wise mean station rainfall RMSE reduction of ET local versus raw, evaluated on the *author processed labels* (original fixed trained models):

| Year | Eligible stations | Relative daily RMSE reduction | Source-date status |
|---|---:|---:|---|
| 2019 | 34 | **9.17%** | One official May 2019 BMD bulletin example matched same calendar date |
| 2020 | 34 | 8.67% | No exhaustive day-label certification |
| 2021 | 33 | **1.68%** | Official wet-day examples align to preceding CSV date |
| 2022 | 34 | 9.62% | Annual ERA-vs-BMD lag audit resembles earlier years |
| 2023 | 33 | **0.71%** | Official wet-day examples align to preceding CSV date |

The **2021 and 2023 deterioration** is a descriptive symptom, not proof that every value in those years has the same shift. The independent Mendeley BMD-derived records also contain detected duplicated station-years (Bogra 2021 matching 2020; Teknaf 2023 matching 2022), so **do not present that archive as certified ground truth**.

On the frozen held-out arrays, evaluating only the **other 22 years** yields rainfall mean station RMSE **16.903 mm RAW → 15.372 mm ET local**, or **9.06%** reduction (34 stations). This is not an independently retrained dataset.

## 6. Physical plausibility and source provenance

- **Zero** negative rainfall predictions across all four saved prediction method/LOSO folds combined.
- **Four** ET-local held-out station-days have predicted Tmax below predicted Tmin; the model was fitted per target, so cross-target consistency is not mathematically guaranteed. Identify affected sites/days only if observed-date labels are available and data publication rules permit.
- There are **204** out-of-range observations flagged and represented as missing in the user-cleaned dataset; no source values were secretly invented in this audit.
- At the **whole processed BMD table** level, Tmax, Tmin and rainfall missing fractions are **2.724%, 3.141% and 1.976%** respectively; missingness is nonuniform by station. For instance, Chittagong rainfall completeness is **83.2%** during the long record. Thus we should not describe every station-year as 98–99% complete.
- **Recovered ERA source:** 24 original-format year CSVs match processed/native target features at 3,876,190 numeric comparisons to tolerance 1e−7. However, no original *Google Earth Engine source script, task receipts, geometry, aggregation code or historical grid-cell IDs* have been recovered. An independently reconstructed script does not prove what the authors originally ran.
- **Historical coordinates:** all 36 author station metadata latitude/longitude entries are labelled **draft**; a present-day public coordinate snapshot is not an original 2000–2023 historical site ledger. Under a hypothetical replacement, 1/561 native station pairs cross the nominal 100-km distance line; **zero of the original fixed buffer-fold donor memberships** change, but 18/561 same-block pairs change under re-generated K-means geography. Do **not** falsely state that historic station relocation is known or that the original extraction points were certified.
- **BMD convention:** public daily reports specify 24-hour rain up to **06:00 Bangladesh Standard Time** on report date, but they do not resolve the historical year-by-year labels in the processed private CSV. Await the already-sent BMD clarification while documenting alternative alignments explicitly.

## 7. Manuscript safety rules and ready-to-write decisions

1. **Primary scientific claim:** held-out-station Tmax correction transfers within a 34-station Bangladesh network, loses some skill as donor separation increases, and terrain features can undermine transfer.
2. **Second claim:** the rainfall correction's daily RMSE improvements do not imply improvement in extremes, ordinary wet-day detection or annual R10mm/Rx1day indices. Show **both positive and negative results**.
3. **Study design:** station-held-out, spatial-blocked, buffer-based, future-time and spatiotemporal evaluations are distinct. Report their exact train/test supports and don't treat correlated folds as independent experimental replications.
4. **Data status:** refer to supplied daily BMD values as *author-processed BMD-derived observations*; label Mendeley as *independently sourced BMD-derived secondary archive*. Do not claim complete original-data certification or release original observations without authorisation.
5. **Rainfall limitation:** source-date anomaly 2021/23 and limited independent 2019 reference remain unresolved; explicitly mark any rainfall/extreme result as **provisional with respect to source dating**, or defer this component if the journal requires source-perfect observations.
6. **What is not an empirical result:** unverified rainfall+1-day candidate CSV, hypothetical modern station-coordinate substitution, reconstructed Earth Engine code, and any non-existent *retrained corrected dataset*.
7. **One more material manuscript choice:** If the final paper retains rainfall as a major claim, a reviewer may legitimately demand official 2000–2023 rainfall date mapping. A deadline does not make missing agency evidence available; disclose unresolved provenance instead of presenting reconstructed data as original.

## 8. Supporting file map and exact reproduction commands

From the **project root**, with `research_v2/input/dataset/` and `research_rebuild/results/jobs/` available:

```bash
python research_rebuild/reporting/audit_inputs.py --input research_v2/input/dataset --output pre_manuscript_run_20261110/validation/input_quality.json
python research_rebuild/reporting/audit_splits.py --input research_v2/input/dataset --results research_rebuild/results --output pre_manuscript_run_20261110/validation/splits
python research_rebuild/reporting/build_report.py --results research_rebuild/results --reports pre_manuscript_run_20261110/validation/recomputed --figures pre_manuscript_run_20261110/figures --prior research_rebuild/evidence/author_reference/loso_station_metrics.csv
python pre_manuscript_run_20261110/run_remaining_analytics.py
python pre_manuscript_run_20261110/run_station_index_tradeoffs.py
```

**Privacy:** The deliverable ZIP contains aggregated science, code, verification and figures, **not** the actual BMD daily observation table, full ERA/NASA raw files, source credentials or `product_benchmarks/paired.pkl`. The original private files remain in the local project environment.

**Bottom line for manuscript drafting:** The computational evidence and new derivative analyses are reproducible, but full historical input provenance is **not**. Write a candid, focused paper using explicit limitations and avoid saying that official rainfall date convention or 2000–2023 station locations have been authenticated.
