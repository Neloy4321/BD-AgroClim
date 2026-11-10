# BMD / ERA5-Land source recovery — executed status

**Date:** 10 November 2026, Bangladesh time  
**Purpose:** remove major provenance uncertainties affecting the author's daily Bangladesh ERA5-Land spatial-transfer manuscript.  
**Updated conclusion following connected Drive recovery:** The user's **original-format source-level ERA5-Land CSV exports for 2000–2023 were found and downloaded**: all 24 annual station files and all 24 supplemental island files, 48 in total. The 24 main annual source files can reproduce **3,876,190** numeric cells of the pre-existing ERA5 v2 table within absolute 1e−7 after reconstructing the unit conversions and negative-rain clipping. This materially resolves the missing-ERA5-source-file issue, but **does not** recover the original GEE code/task IDs, missing untouched BMD observation downloads or historical station-location certificates. The proposed new independent GEE extraction has not run because the browser requires Google sign-in. Source-corrected retraining remains unsupported until BMD day semantics are established.

## Completed, with measured results

| Work item | Result | Evidence |
| --- | --- | --- |
| Public BMD rainfall-date checks | Seven spotchecks from 3 official bulletin dates. Same-calendar-day match: **1/7**. Previous-day match: **6/7**. | `bmd_public_bulletin_spotcheck_results.csv`, `official_bmd_wetday_examples.csv` |
| Station source verification queue | **36** original station entries; **34** current BAMIS name/alias candidate matches, **2** not matched unambiguously; **7** sites exceed 1 km coordinate difference, including **1** exceeding 5 km | `station_historical_source_queue.csv`, `station_queue_summary.json` |
| ERA5 extraction method | New self-contained Earth Engine JS with UTC date field, raw variables and labelled conversions; author metadata embedded | `gee_era5land_daily_extract.js` |
| Independently repeatable GEE spot-check design | Three 10-day windows targeting 2019-05-11, 2021-05-20 and 2023-09-06 BMD bulletin examples | `gee_era5land_daily_extract.js` in `sample` mode |
| GEE-export vs old-ERA5 comparator | Native author record keys and 13 measured source/derived fields; discrepancy examples, per-station and per-feature statistics | `compare_gee_export.py` |
| Recovered original ERA5 annual CSV files | **48 files recovered**, including 24 main years 2000–2023 (**315,576** rows) and 24 island years (**17,532** rows) | Separate raw-exports ZIP, `original_gee_source_file_manifest.csv` |
| Original-source-to-processed numerical audit | **3,876,190 numeric comparisons**, **zero errors greater than 1e−7**; **978** negative-precipitation artifacts clipped to zero; **732** year-2000 raw rows absent from v2 | `audit_recovered_drive_exports.py`, `drive_original_audit_results/recovered_gee_audit_summary.json` |
| Machine tests | Python unittest cases for 36-station generation, 36-station source ledger, synthetic comparison and negative-rain clipping: **4 passed**. JS: `node --check` passed (syntax only) | `test_recovery_kit.py` |

## Outstanding evidential blockers

### 1. Original BMD source, day semantics and cleaning trail — **BLOCKING**

The supplied dataset includes a processed `bmd_clean_daily.csv` but not its untouched source retrieval or a complete station-by-station day-label mapping. Three official BMD bulletin spotchecks show **contradictory date mapping**. The 2019 example matches same day, while the May 2021 and September 2023 samples match preceding calendar day. This is evidence of a *possible year-specific source/QC/date handling issue*, **not** proof of any causal explanation, data corruption, or whole-dataset shift.

The previous independent scientific audit also found 33/34 stations preferred `ERA(t-1)` for aggregate rainfall correlation, whereas 2021 and 2023 subperiods mostly preferred zero shift. This statistical lag result is not enough to modify the rainfall dates. Recover authenticated BMD records and their observation-window definitions before altering labels.

**Source route:** Government BARC CIMS (`https://barcapps.gov.bd/climate/rainfall`) advertises a mixed BMD/BWDB archive but actual station coverage, access rights and successful CSV download remain unverified; the BMD official Climate Data Portal (`https://dataportal.bmd.gov.bd/web/`) provides an archival inquiry route but may have restrictions/charges. A request draft is included; none was sent or purchased.

### 2. Historical station identity and coordinates — **BLOCKING**

All 36 author records have `coord_source=draft`. Matching present public 2026 BAMIS names and positions cannot certify the coordinates for 2000–2023. Our station queue marks **3 priority-P0** current name/position concerns (two unmatched current names; one distance greater than 5 km); additionally six other station aliases/coordinates differ by greater than 1 km. Station opening/closure/relocation history, station ID and site instrument consistency need official records. Do not automatically replace coordinates with 2026 coordinates.

### 3. Earth Engine extraction provenance — **PARTIAL**

The `ECMWF/ERA5_LAND/DAILY_AGGR` product family and source variable units are verified against public official documentation. **The original-format numeric station export CSVs are now available in the user's own Drive**. Original Code Editor script, task IDs, dates, export scale/projection/reducer and service-side version are **still unknown**; the recovered CSV headers do not encode original pixel coordinates or reducer. The new script reconstructs an independently documented default pixel `first` reducer using the published 11,132-metre nominal scale; that may differ from the original one. An independent new GEE run is *optional for further source-method verification*, not needed for recovering historical numeric station exports.

**Correction demonstrated by recovered original Drive exports:** The author v2 ERA5 `prcp` is in **millimetres**, derived from raw GEE `total_precipitation_sum` in metres ×1000 with negative artifacts clipped to zero. For example, the recovered 2021-01-01 S01 source is `0.0000027120113372802734 m`, and the processed ERA5 `prcp` is `0.0027120113372802 mm`. BMD `prcp` is also mm. The earlier assertion that processed ERA5 `prcp` was in metres was **incorrect and superseded**. All other directly comparable raw variables agree after the verified conversion chain. **No source data were overwritten.**

## Scientific publication decision now

1. **Do not claim** rainfall temporal alignment resolved, historical geometry certified or source-corrected results independently rerun.
2. A manuscript can honestly report the existing *methodologically reconstructed* original results **only if** limitations and source provenance uncertainty are prominent. The prior audit showed methods are computationally reproducible conditional on author input files, which is **distinct** from primary source integrity.
3. Source-corrected model reruns become necessary **if and only if** the new authenticated records prove substantive date/geometry/source changes. Re-evaluate blocked/LOSO splits, climate-index tradeoffs, and leakage checks for affected years/sites after correction.
4. Prefer a scientific contribution around **when calibration transfers under spatial separation, donor support and climate-index trade-offs**, with explicit date/coordinate stress tests and transparent provenance, rather than inventing a claim of higher model accuracy.

## Shortest legitimate next actions

1. **Immediate scientific priority:** recover official untouched BMD observations with verified day-label and station-site history. The public BARC climate site timed out during this session. The authenticated BMD portal has terms, fees and short recent date settings. A request draft is ready but **not sent**.
2. **Optional independent method check:** if you want to certify whether a brand-new service-side GEE extraction reproduces old pixels, sign in to Earth Engine and run the three `sample` Code Editor exports, then upload the exported CSVs. It is **no longer necessary to re-export 2000–2023** to recover missing historical raw ERA5 numeric tables.
3. **Assistant, once authenticated BMD raw/metadata arrive:** reconcile year/site-specific BMD day labels, verify historic coordinates and rerun affected LOSO/spatial-block/climate-index experiments **only if** source-backed correction is necessary.

No further author action is needed to repeat the completed **raw ERA5 source-to-processed audit**. External authenticated BMD historical access is still the principal blocker. All recovered Drive ERA5 files are listed with original Drive IDs and SHA-256 checksums in the separate archival evidence package.

## Official reference URLs

- ECMWF/Google Earth Engine `DAILY_AGGR` catalog: https://developers.google.com/earth-engine/datasets/catalog/ECMWF_ERA5_LAND_DAILY_AGGR
- BARC CIMS rainfall: https://barcapps.gov.bd/climate/rainfall
- BARC government CIMS description: https://barc.gov.bd/pages/static-pages/6922dfed933eb65569e24b15
- BMD official climate portal: https://dataportal.bmd.gov.bd/web/
- Current BAMIS observation table: https://www.bamis.gov.bd/en/bmd/observed/table/
- WMO OSCAR/Surface metadata: https://oscar.wmo.int/surface/
- Historical BMD bulletin source files and measured values: `official_bmd_wetday_examples.csv`

This report describes **local actions performed** and clearly separates verified evidence, author-provided files, code reconstruction, unavailable originals and future external service operations.
