# BMD / ERA5-Land source-recovery kit — 10 November 2026

**Purpose:** recover missing primary-data provenance for a Bangladesh daily ERA5-Land vs BMD bias-correction manuscript. **Important new finding:** the user's connected Drive contains the original-format GEE-exported CSVs for 2000–2023; all 24 main annual files and all 24 two-island supplemental files have now been independently recovered and validated. A separate raw-data evidence archive preserves those 48 downloads. This kit also creates a **new** GEE extraction for optional service-side revalidation. We have **not** recovered original BMD purchases/downloads, old GEE script/task logs, or historical station relocation records.

## Major recovery: archived ERA5 files were in Google Drive

- [Main original exports](https://drive.google.com/drive/folders/14SW-XM5q2JhNSwNJxtxNJYXGmG4YmVTG): `era5land_stations_2000.csv` through `era5land_stations_2023.csv`, **24 files**, **315,576** station-days.
- [Island supplemental exports](https://drive.google.com/drive/folders/1JcLxmmlzmbvI1PT-lJ7r5F7k_Gjuy8Vk): `era5land_islands_2001.csv` through `era5land_islands_2023.csv`, plus 2000 at a separate Drive folder, **24 files**, **17,532** station-days.
- SHA-256, original Drive IDs, exact file sizes, 16-column source schema and annual/day/station counts were verified and recorded in `original_gee_source_file_manifest.csv` and `raw_export_source_manifest_summary.json`.
- New source-to-processed arithmetic check: **3,876,190 numeric cells**, **0 discrepancies above 1e−7** against the author's v2 source on common keys, once the original transformations are applied. **978** tiny negative source-rain values were clipped to 0, and **732** year-2000 island raw rows are absent from v2 (the previous audit identified the same v1/v2 coverage issue). The script and reports are `audit_recovered_drive_exports.py` and `drive_original_audit_results/`.
- **Scope:** these are original-format extracted numeric files, not original GEE export task logs, service-side code or pixel-grid verification. Main archive currently covers 2000–2023; newer 2024–2026 Drive exports also exist but were not needed for the manuscript audit.

## What is verified, and what is not?

| Evidence | State | Meaning |
| --- | --- | --- |
| Original `dataset(1).zip` | Author-supplied, SHA-256 `0f7fcf642cc53ac6a70eb8f9c66d53e516565a87e7c2f8736b65fd39ac7e0cc0` | Working baseline, **not** evidence of raw BMD acquisition |
| BMD daily processed `bmd_clean_daily.csv` | Present in original author ZIP | Raw daily log, original downloader and QA transformation **missing** |
| Seven wet-day public BMD bulletin examples | Independently rechecked against processed CSV | 1 same-day and 6 previous-day matches; **cannot infer a universal date shift** |
| 36 author extraction points | Present in `station_points_author_draft.csv` | Labels + lat/lon identified, but source is author `draft`; period 2000–2023 unverified |
| BAMIS 2026 station-coordinate snapshot | Present, 53 rows, URL retained | 34 tentative name matches; public **current** position is not a historical location certificate |
| ERA5-Land Earth Engine product | `ECMWF/ERA5_LAND/DAILY_AGGR` officially documented | Product ID, variable meanings, native aggregation verified; original reducer/task/version unverified |
| Original-format ERA5 station exports | **Recovered from user's connected Drive** | 48 raw CSVs, exact source-to-v2 arithmetic verified |
| New independent Earth Engine extraction | Created as `gee_era5land_daily_extract.js` | New runnable code **not executed on Earth Engine yet**, since the cloud Code Editor requires a signed-in Google account |
| New GEE-to-original comparison | `compare_gee_export.py` and synthetic unit tests executed | Needs actual new GEE CSV from user's project/account |

## Optional Step 1 — Do a *small independent* new ERA5 extraction (only if verifying pixel geometry/reducer)

**You do not need to rerun 24 years merely to retrieve the old numerical ERA5 records; all 24 historical main raw CSVs have been recovered.** An independently regenerated GEE sample would still test whether a fresh Code Editor run matches the archived service-side numbers, grid sampling and date labels.

1. Open [Google Earth Engine Code Editor](https://code.earthengine.google.com/). If not already registered, complete access to an eligible Earth Engine project and select it.
2. Copy all content from `gee_era5land_daily_extract.js` into a new Code Editor script. This script includes all **36 provisional** author station positions; there is no shapefile upload requirement.
3. Leave `RUN_MODE = 'sample'` and press **Run**. The console prints three 10-day windows, including BMD public-bulletin example stations in **2019, 2021 and 2023**.
4. Open **Tasks**, start the three table exports to Google Drive. Look for the folder `ERA5_BMD_recovery` and download three CSV files. Preserve original filenames; write down Earth Engine project ID, export task IDs, run date, and any error messages.
5. The script includes `date_utc`, `gee_image_id`, raw bands and explicitly converted units. It never performs an automatic +1-day or −1-day shift.
6. Check `rain_m`, `rain_mm_raw` and `rain_mm_clipped`: raw mm = raw metres ×1000, and clipped mm = max(0, raw mm). Preserve **both** raw and clipped versions; the archived author processing zeroed 978 tiny negative raw rain values.

The sample tests GEE-versus-existing ERA5 file consistency and data geometry. It **does not** establish whether BMD observed rainfall dated `t` refers to the same physical 24-hour window.

### Compare downloaded GEE CSV against the author file

From this kit's folder on your machine (Python 3.10+):

```bash
python compare_gee_export.py \
  --export ERA5_BMD_sample_20190511_UTC.csv ERA5_BMD_sample_20210520_UTC.csv ERA5_BMD_sample_20230906_UTC.csv \
  --reference "/path/to/dataset/era5land_stations_daily/era5land_stations_daily_v2.csv" \
  --out-dir comparison_results
```

Outputs: `comparison_results/gee_comparison_summary.json`, `comparison_by_station.csv`, and `comparison_top_100_discrepancies.csv`. The code requires only the Python standard library, handles samples or annual exports, and compares **native** ERA5 rows without imputing or changing missing source observations. Differences can reflect an older extraction's reducer, pixel geometry, dataset revision, rounding, unit conversion or date mapping; inspect before editing anything.

### Step 1b — Full annual extraction **only after sample review**

Set `RUN_MODE = 'annual'` in the JS and rerun: this queues **24 annual export tasks** (2000–2023, all 36 points) to Drive. They are not started automatically and may be expensive or hit Earth Engine quotas. Validate/correct *source-certified* coordinates **before** full export; if the 2000–2023 station site history changed, extraction must be segmented by valid site/time interval. `gee_era5land_daily_template.js` plus `generate_gee_script.py` can regenerate the JS if approved station coordinates are updated.

```bash
python generate_gee_script.py --points station_points_author_draft.csv
```

**Units (verified from recovered original Drive exports):** Native GEE `total_precipitation_sum` is **metres**, and older author-derived ERA5 `prcp` is **millimetres**, obtained by multiplying source metres ×1000 **and clipping negative values to zero**. Source BMD `prcp` is also **millimetres**. Compare processed `prcp` to `rain_mm_clipped`, **not `rain_m` or `rain_mm_raw` when negative artifacts occur**. Temperatures are K in GEE, °C in author-derived ERA5. Radiation J/m² -> MJ/m²/day, pressure Pa -> kPa. Evaporation source negatives become positive mm using ×−1000 for the author-derived convention.

Official dataset documentation: https://developers.google.com/earth-engine/datasets/catalog/ECMWF_ERA5_LAND_DAILY_AGGR

## Step 2 — Get original or independently licensed BMD data

This is the **non-automatable blocking part** without BMD/BARC access and source terms. We verified **where to request**; we have **not** downloaded historical raw station observations or paid any fees.

1. **Try BARC Climate Information Management System (CIMS).** Government BARC describes its historical database as covering *30 BMD climate stations* plus separate BWDB rainfall stations; **30 is not all 36 author stations**, so verify coverage case by case. Portal: https://barcapps.gov.bd/climate/rainfall ; government agency overview: https://barc.gov.bd/pages/static-pages/6922dfed933eb65569e24b15 . CIMS may require signup/permissions, and it was **not accessible for a successful authenticated download during this review**. Do not equate BWDB rain gauges with BMD sites by name.
2. **Contact the official BMD Climate Data Division/Portal** for research/archival access and a formal fee/permission quote: https://dataportal.bmd.gov.bd/web/ . Its public form indicates short recent date ranges; for 2000–2023, ask BMD for the proper historical request procedure. Suggested request drafted in `BMD_historical_data_request_DRAFT.md`; **not sent**.
3. Ask for both **daily rainfall observations** and **station metadata site history**, including station code, WMO code, dates of site changes, exact observation window for the 06AM report, day-label definition, units, trace/missing codes and correction/QC history. If all 36×24 years is costly, start with an authenticated **stratified wet-day pilot** covering at least 2019, 2021, 2022 and 2023 before buying the full archive.
4. Store an acquisition log containing owner/institution, URL or request ID, exact time, file SHA-256, date range, location, source licence, and whether re-sharing is permitted. Do not redistribute files unless expressly allowed.

The seven public BMD PDF spotchecks in `official_bmd_wetday_examples.csv` and `bmd_public_bulletin_spotcheck_results.csv` are examples, not a valid surrogate for 24 years of raw records. Repeat them against the untouched processed original with:

```bash
python -m pip install pandas
python verify_bmd_wetday_examples.py \
  --bmd "/path/to/dataset/BMD data/bmd_clean_daily.csv" \
  --out bmd_public_bulletin_spotcheck_results.csv
```

## Step 3 — Certify station coordinates historically

`station_historical_source_queue.csv` covers **all 36** sites and their candidate WMO IDs, provisional station coordinates, present BAMIS public coords, gap distances and source-verification priorities. `build_station_source_queue.py` recomputes the queue. The current public table is https://www.bamis.gov.bd/en/bmd/observed/table/ ; WMO station metadata/history can also be investigated via https://oscar.wmo.int/surface/ but an OSCAR match alone may not prove the site's operation throughout 2000–2023. Verify ambiguous *Chittagong* vs *Chittagong Ambagan* identities, coastal stations and relocations with BMD.

## Step 4 — Only then decide on model re-training

- If date semantics, position and variables are verified and consistent: **retain existing model results**, document source evidence and any remaining limits.
- If a source-backed date shift is needed **for specific years/sites**, apply it at the raw/source normalization stage using an explicit correction ledger and redo the affected model training/testing, climate-index and spatial-holdout analyses.
- If point coordinates changed enough to change grid cell, terrain/land-cover predictors or spatial-block membership: redo extraction **for valid historical site dates** and rerun affected evaluation splits.
- Never select the shift that gives the highest correlation as if that proves the observation date; never present hypothetical label-shift metrics as fully retrained corrected results.

## Local verification already run (not equivalent to Earth Engine execution)

```bash
python -m unittest discover -s . -p 'test_*.py' -v
node --check gee_era5land_daily_extract.js  # syntax only if Node.js installed
python build_station_source_queue.py
python generate_gee_script.py
```

Expected: 36 provisional station points, 34 tentative BAMIS current-name matches, seven public-bulletin checks (1 same date, 6 previous), **4** passing Python tests and Node.js syntax check. **No authenticated BMD, WMO history or new Earth Engine server export was performed by these local tests.** The original Drive CSVs were, however, authenticated downloads through the connected Drive account and independently checked against the author-derived dataset.

## Package inventory

- `gee_era5land_daily_extract.js`: self-contained GEE Code Editor script.
- `gee_era5land_daily_template.js`: regenerable template.
- `generate_gee_script.py`: deterministic template builder.
- `compare_gee_export.py`: downloaded GEE CSV comparator.
- `audit_recovered_drive_exports.py`, `drive_original_audit_results/`: full 2000–2023 original-source-to-v2 verification.
- `original_gee_drive_sources.csv`, `original_gee_source_file_manifest.csv`: 48 original Drive IDs and file SHA-256 hashes.
- `build_original_export_manifest.py`, `raw_export_source_manifest_summary.json`: 48-file independent schema, size and full-coverage checks.
- `build_station_source_queue.py`: station metadata ledger generator.
- `station_points_author_draft.csv`, `station_metadata_author_draft.csv`: original author coordinates/metadata, labelled provisional.
- `bamis_station_coordinates_public_2026.csv`: current official public snapshot (not historical).
- `station_historical_source_queue.csv`, `station_queue_summary.json`: 36-station verification requests.
- `verify_bmd_wetday_examples.py`, `official_bmd_wetday_examples.csv`, `bmd_public_bulletin_spotcheck_results.csv`: seven BMD rain date checks.
- `BMD_historical_data_request_DRAFT.md`: email/letter draft to send yourself after review.
- `SOURCE_RECOVERY_STATUS_2026-11-10.md`: assessment and what remains genuinely missing.
- `test_recovery_kit.py`, `integrity_manifest_sha256.txt`: executable local checks and file hashes.

**Integrity policy:** This **small code/report package** does not embed the author's complete proprietary/uncertain-rights raw BMD records, the large recovered daily ERA5 exports (provided in a **separate raw-exports evidence ZIP**), or account credentials. Keep source originals immutable. See `integrity_manifest_sha256.txt` for a kit file manifest and `original_gee_source_file_manifest.csv` for full raw export SHA-256 checksums.
