````markdown
# Data Provenance

## Overview

This repository combines observational station data, gridded climate products, terrain and land-surface information, station metadata, and derived analytical datasets.

The principal data sources used in the BD-AgroClim workflow are:

1. Bangladesh Meteorological Department (BMD) station observations
2. NASA POWER daily climate data
3. ERA5-Land daily climate data
4. Terrain and land-surface datasets
5. Station-level spatial and administrative metadata
6. District-level rice-yield data used as an optional independent validation signal

The repository distinguishes between primary observations, externally sourced datasets, derived datasets, and computational outputs.

---

## 1. Bangladesh Meteorological Department Station Data

### Dataset

```text
bmd_clean_daily.csv
````

### Role

The BMD station observations provide the primary ground-based reference for evaluating NASA POWER and ERA5-Land.

### Variables

```text
station_name
date
tmax
tmin
prcp
record_type
```

### Temporal Coverage

```text
2000-01-01 to 2023-12-31
```

The dataset contains 36 long-record stations together with additional short-record stations. The primary analysis uses the long-record station subset.

### Processing

The station dataset was cleaned through:

* station-name alias reconciliation
* duplicate-row handling
* physical-range quality control
* station-month z-score screening
* calendar completion
* missing-value handling

The principal analysis excludes records where:

```text
record_type == "short"
```

### Redistribution

The redistribution of raw BMD observations is subject to the terms under which the observations were obtained. If redistribution is not permitted, the original station observations should not be redistributed through this repository.

---

## 2. Station Metadata

### Dataset

```text
station_metadata_final.csv
```

### Role

Provides the spatial and administrative metadata required to associate station observations with reanalysis and terrain information.

### Main Fields

```text
station_name
wmo_id
lat
lon
elev_m
division
district
region
coord_source
```

Additional station-level spatial mapping information is provided through:

```text
meta_with_cells.csv
station_cell_map.csv
station_landscape.csv
```

These files support station-to-grid-cell mapping and landscape-based analysis.

---

## 3. NASA POWER

### Dataset

```text
NASA_POWER_Climate_Data_Bangladesh_2000_2026.csv
```

### Role

NASA POWER is used as one of the benchmark gridded climate products in the station-based evaluation.

### Temporal Coverage

```text
2000–2026
```

### Spatial Resolution

Approximately:

```text
0.5°
```

corresponding to roughly 50 km spatial spacing.

### Main Variables

```text
T2M
T2M_MAX
T2M_MIN
PRECTOTCORR
RH2M
WS2M
ALLSKY_SFC_SW_DWN
GWETTOP
GWETROOT
```

`GWETTOP` and `GWETROOT` represent dimensionless wetness fractions and are not treated as volumetric soil-moisture measurements.

Because of its relatively coarse spatial resolution, NASA POWER is primarily treated as a benchmark product rather than a fine-scale spatial representation.

---

## 4. ERA5-Land

### Dataset

```text
era5land_stations_daily_v2.csv
```

### Role

ERA5-Land is the principal reanalysis product used for station-scale validation, terrain-bias analysis, machine-learning correction, and reconstruction.

### Spatial Extraction

ERA5-Land daily values were extracted at the 36 BMD station coordinates.

### Main Variables

```text
point_id
station_name
date
t2m_mean
t2m_max
t2m_min
d2m
prcp
swvl1
swvl2
ssrd
pet_era5
aet_era5
u10
v10
ws10
ws2
sp
ea
es
rh_mean
vpd
era5_source
```

### Temporal Coverage

```text
2000-01-01 to 2026-07-30
```

### Derived Variables

The processing workflow derives:

* `ws2`
* `ea`
* `es`
* `rh_mean`
* `vpd`

The `era5_source` field identifies whether a value is:

```text
native
```

or:

```text
focal_filled
```

---

## 5. Terrain and Land-Surface Data

### Dataset

```text
terrain_full.csv
```

### Role

Terrain and land-surface variables are used to investigate spatial controls on reanalysis bias and skill.

### Source Datasets

The terrain information was derived from:

* Copernicus GLO-30
* SRTM v3
* JRC Global Surface Water

The extraction and spatial processing were performed through Google Earth Engine.

### Main Variables

```text
point_id
station_name
elev_dem
elev_srtm
tpi_1km
tpi_5km
roughness_5km
elev_mean_9km
elev_std_9km
land_frac_9km
dist_water_km
slope_fix
aspect_fix
northness
eastness
slope_mean_9km
```

### Key Terrain Variables

`land_frac_9km` represents the fraction of the ERA5-Land grid cell occupied by land.

`elev_std_9km` represents the standard deviation of elevation within the approximately 9 km grid cell.

These variables are central to the terrain-control analysis.

---

## 6. Terrain–Skill Merged Dataset

### Dataset

```text
terrain_skill_merged.csv
```

### Role

This dataset combines station-level ERA5-Land skill metrics with terrain and land-surface variables.

It is used as an analytical input for the terrain–bias analysis and the corresponding results and figures.

The dataset includes variables such as:

```text
station_name
tmax_r
tmax_bias
tmax_rmse
tmin_r
prcp_r
```

together with the terrain variables.

---

## 7. Paired and Spatially Derived Datasets

The workflow generates several intermediate datasets by combining primary observations, reanalysis products, and spatial metadata.

These include:

```text
paired_era5.parquet
paired_power.parquet
meta_with_cells.csv
station_cell_map.csv
station_landscape.csv
```

These are derived analytical datasets and should not be interpreted as independent observational sources.

Their purpose is to preserve important intermediate stages of the computational workflow.

---

## 8. Statistical Correction and Machine-Learning Outputs

The correction workflow generates several derived datasets, including:

```text
stat_correction_metrics.csv
corrected_stat.parquet
loso_predictions.parquet
island_holdout_metrics.csv
detection_after_ml.csv
reconstruction_summary.csv
```

These files contain model-derived metrics, corrected values, predictions, diagnostics, and reconstruction summaries.

They are computational outputs rather than primary data sources.

---

## 9. SHAP Data

The machine-learning interpretability workflow generates:

```text
shap_features_tmax.parquet
shap_values_tmax.parquet
```

These files contain the feature information and SHAP values used to analyse the contribution of predictors to the Tmax correction model.

The corresponding feature-importance results are provided separately in the results section.

---

## 10. District Rice-Yield Data

### Dataset

```text
yield_panel_final.csv
```

### Role

The district-level rice-yield dataset is an optional independent validation signal for Paper 1 and is also intended as a core data resource for a subsequent paper in the broader research series.

### Main Fields

```text
fiscal_year
year_start
harvest_year
district
season
area_ha
production_mt
yield_kg_ha
qc_pass
confidence
analysis_ready
```

For analyses requiring the quality-controlled subset, the intended filter is:

```text
analysis_ready == True
```

---

## 11. Data Version and File Integrity

The following versions are the intended analysis files:

```text
era5land_stations_daily_v2.csv
terrain_full.csv
yield_panel_final.csv
```

Earlier near-duplicate versions should not be substituted.

In particular:

* the non-v2 ERA5-Land file contains missing values for Kutubdia and Sandwip
* earlier terrain files contained projection-related problems affecting slope and aspect
* the final rice-yield panel contains the required confidence and analysis-readiness information

---

## 12. Temporal Scope and Validation

The principal independently validated study period is:

```text
2000–2023
```

Although some gridded datasets extend to 2026, independent BMD observations are not available for equivalent validation throughout the later period.

Therefore:

```text
2000–2023
= independently validated period

2024–2026
= extended/model-driven period where applicable
```

The year 2026 is also a partial year and must not be treated as a complete annual period.

---

## 13. Focal-Filled Island Stations

Kutubdia and Sandwip require special treatment because they fall within masked ocean cells in the ERA5-Land extraction.

Their records are identified using:

```text
era5_source == "focal_filled"
```

These values are distinguished from native ERA5-Land extractions.

The two island stations are held out from model training and used as an independent test of correction behaviour at island locations.

The distinction between native and focal-filled values is retained throughout the workflow for transparency.

---

## 14. Data Flow

The overall data-provenance chain is:

```text
BMD station observations
          │
          ├──────────────┐
          ↓              ↓
   Station metadata   Quality control
          │              │
          └──────┬───────┘
                 ↓
        Station–reanalysis pairing
                 │
       ┌─────────┴─────────┐
       ↓                   ↓
 NASA POWER            ERA5-Land
       │                   │
       └─────────┬─────────┘
                 ↓
       Baseline validation
                 ↓
       Terrain/land analysis
                 ↓
      Statistical correction
                 ↓
      Machine-learning correction
                 ↓
        LOSO / island holdout
                 ↓
          SHAP interpretation
                 ↓
        Corrected reconstruction
                 ↓
        Final research outputs
```

---

## 15. Data Access and Archiving

The GitHub repository functions primarily as the computational and documentation layer of the project.

Large datasets, reconstructed datasets, and other files that are unsuitable for direct GitHub distribution may be archived through Zenodo or another appropriate research-data repository.

The final archival release should include persistent metadata, version information, and a DOI where applicable.

Users should consult the repository README and the corresponding archival data record for the current data-access instructions.

```
```
