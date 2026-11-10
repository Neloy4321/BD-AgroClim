# Original-format ERA5-Land annual CSV exports: recovered evidence

**Recovered from the author's own connected Google Drive, 10 November 2026.**

## Contents and provenance

- `drive_exports_original/era5land_stations_2000.csv` through `era5land_stations_2023.csv`: all **24** raw-format annual files, **315,576** rows (= 36 author stations × all 8,766 days).
- `drive_exports_original/era5land_islands_2000.csv` through `era5land_islands_2023.csv`: all **24** supplemental files, **17,532** rows (= 2 island sites × all 8,766 days). The separate 2000 island file was found in the second `ERA5L_BD_ISLANDS` Drive folder; it fills the 732-row historical exception.
- `original_gee_drive_sources.csv`: original Drive file IDs, folder URLs, file sizes, years and classification.
- `original_gee_source_file_manifest.csv`: per-file SHA-256 and schema/completeness checks.
- `raw_export_source_manifest_summary.json`: aggregate counts and 48/48 file verification.
- `drive_original_audit_results/recovered_gee_audit_summary.json`: independent original-format-to-author-v2 arithmetic comparison, all 24 years.
- `drive_original_audit_results/recovered_gee_per_year.csv`: per-year raw vs derived counts, file-level SHA checks and small artifact clipping counts.
- `drive_original_audit_results/recovered_gee_discrepancy_first_200.csv`: rows outside tolerance, **none after reconstructing clipping**.

## Numerical audit result

The 24 main exports contain **315,576** point-date keys. Their overlap with the processed author v2 table is **314,844** keys; **732** raw main-island-year-2000 rows were not in that version. Among the 314,844 matched keys, the processed provenance labels are 298,044 `native` and 16,800 `focal_filled`.

The 13 directly comparable native variables have **3,876,190 numeric comparisons**, with **zero** absolute differences over **1e−7** after the transformations described below. Some raw measurements are missing/blank, so cell count is slightly less than 13×matched rows.

Unit/feature transformations: K → °C (−273.15), precipitation m → mm (×1000), tiny negative rainfall artifacts clipped to zero (**978** overlapping source rows), shortwave radiation J/m² → MJ/m² (÷1,000,000), evap accumulations m → positive mm (×−1000), pressure Pa → kPa (÷1000), other source bands retained directly.

This verifies **source data values and arithmetic transform lineage** strongly. It does **not** independently certify the original Earth Engine `reduceRegions` method, exact pixel centers, task IDs, historical station coordinates, UTC vs BMD daily observation time conventions or untouched BMD source observations. Thus it does not resolve rainfall temporal alignment or guarantee publication acceptance.

## How to reproduce

Extract this ZIP next to the small source-recovery kit, preserving the `drive_exports_original/` folder. Then from the small kit run:

```bash
python build_original_export_manifest.py
python audit_recovered_drive_exports.py \
  --raw-dir drive_exports_original \
  --processed "/path/to/dataset/era5land_stations_daily/era5land_stations_daily_v2.csv" \
  --out-dir drive_original_audit_results
```

These commands use Python 3.10+ standard library only and never modify the original files.

Primary product and credit information: https://developers.google.com/earth-engine/datasets/catalog/ECMWF_ERA5_LAND_DAILY_AGGR

**Privacy and reuse:** This archive contains original-format ERA5 numerical exports obtained from the author's connected Drive, not BMD observation values, Google credentials, paid BMD files or original GEE scripts. Follow ECMWF/Copernicus citation and distribution requirements if publishing the raw export archive elsewhere.
