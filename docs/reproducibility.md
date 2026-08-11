````markdown
# Reproducibility Guide

## Overview

This repository is designed to support computational reproducibility of the BD-AgroClim study.

The complete analysis is implemented primarily through four Jupyter notebooks. The notebooks are organised according to the dependency structure of the research workflow, beginning with data preparation and validation and progressing through terrain analysis, statistical and machine-learning correction, spatial validation, interpretability analysis, reconstruction, and figure generation.

---

## 1. Computational Workflow

The recommended notebook execution order is:

```text
01_Validation_and_Data_Preparation.ipynb
                    ↓
02_Terrain_and_Statistical_Analysis.ipynb
                    ↓
03_ML_LOSO_and_SHAP.ipynb
                    ↓
04_Reconstruction_and_Figure_Generation.ipynb
````

Each notebook produces intermediate or final outputs required by subsequent stages.

---

## 2. Notebook 01 — Validation and Data Preparation

```text
01_Validation_and_Data_Preparation.ipynb
```

This notebook performs the initial data preparation and baseline evaluation.

The workflow includes:

* loading the cleaned BMD station observations
* selecting the long-record station network
* loading station metadata
* loading NASA POWER data
* loading ERA5-Land data
* pairing station observations with reanalysis data
* assessing data availability
* calculating baseline validation metrics
* evaluating rainfall detection skill

The primary independently validated period is:

```text
2000–2023
```

The principal observational variables are:

```text
Tmax
Tmin
Precipitation
```

---

## 3. Notebook 02 — Terrain and Statistical Analysis

```text
02_Terrain_and_Statistical_Analysis.ipynb
```

This notebook investigates spatial controls on reanalysis performance and performs statistical bias-correction analysis.

The workflow includes:

* loading terrain covariates
* merging terrain variables with station-level skill metrics
* landscape-stratified analysis
* Spearman rank correlation analysis
* terrain–bias analysis
* nested station-level bias modelling
* statistical bias correction

Important terrain variables include:

```text
land_frac_9km
elev_std_9km
roughness_5km
dist_water_km
elev_dem
slope_mean_9km
northness
eastness
```

The principal parsimonious terrain model uses:

```text
land_frac_9km
+
elev_std_9km
```

---

## 4. Notebook 03 — Machine Learning, LOSO and SHAP

```text
03_ML_LOSO_and_SHAP.ipynb
```

This notebook implements the machine-learning bias-correction and spatial-transferability analysis.

The evaluated machine-learning models include:

* Random Forest
* XGBoost
* LightGBM
* Extra Trees

Statistical correction approaches are retained as comparison baselines.

The machine-learning workflow uses residual learning to model systematic differences between reanalysis estimates and station observations.

Neighbouring-station information is incorporated where specified by the corresponding modelling workflow.

---

## 5. Leave-One-Station-Out Validation

Spatial generalisation is evaluated using leave-one-station-out (LOSO) validation.

For each fold:

```text
One station
     ↓
Completely withheld from training
     ↓
Remaining eligible stations
     ↓
Model training
     ↓
Prediction for withheld station
     ↓
Performance evaluation
```

The process is repeated across the eligible station network.

Random cross-validation should not be substituted for LOSO because spatial dependence can produce overly optimistic estimates of model performance.

The resulting station-level predictions are retained in:

```text
results/predictions/loso_predictions.parquet
```

---

## 6. Island Holdout Evaluation

Kutubdia and Sandwip are treated separately from the main training network because their ERA5-Land records contain focal-filled values.

The two stations are excluded from model training and evaluated as an independent test of correction behaviour at island locations.

The corresponding metrics are stored in:

```text
results/metrics/island_holdout_metrics.csv
```

This separation preserves the distinction between native ERA5-Land values and focal-filled coastal values.

---

## 7. SHAP Analysis

The machine-learning interpretability workflow uses SHAP to analyse the selected Tmax correction model.

The corresponding intermediate outputs are:

```text
results/
└── ...
    ├── shap_features_tmax.parquet
    └── shap_values_tmax.parquet
```

These outputs support the generation of feature-importance rankings and SHAP visualisations.

---

## 8. Notebook 04 — Reconstruction and Figure Generation

```text
04_Reconstruction_and_Figure_Generation.ipynb
```

This notebook performs the final reconstruction and generates the manuscript figures.

The workflow includes:

* assembling corrected outputs
* generating reconstruction summaries
* generating manuscript figures
* preparing final analytical outputs
* producing diagnostic visualisations

The manuscript figures are organised as:

```text
F1  Study area
F2  Data availability
F3  Taylor diagram
F4  Terrain controls
F5  Seasonal error
F6  Rainfall error
F7  Spatial error
F8  LOSO RMSE
F9  SHAP interpretation
F10 Before/after correction
F11 Island diagnostic
```

---

## 9. Required Input Data

The principal input datasets are:

```text
bmd_clean_daily.csv
station_metadata_final.csv
NASA_POWER_Climate_Data_Bangladesh_2000_2026.csv
era5land_stations_daily_v2.csv
terrain_full.csv
terrain_skill_merged.csv
```

Additional intermediate datasets are generated during the workflow and are stored separately from the primary input data.

Large datasets may be distributed through an archival repository rather than committed directly to GitHub.

---

## 10. File Version Control

The intended analysis versions must be used consistently.

In particular:

```text
era5land_stations_daily_v2.csv
terrain_full.csv
yield_panel_final.csv
```

Earlier near-duplicate files should not be substituted.

The repository preserves the final analysis filenames to reduce the possibility of silently using an incorrect dataset version.

---

## 11. Station Selection

The primary analysis uses the 36 long-record BMD stations.

Short-record stations are excluded using:

```python
record_type == "long"
```

Station-specific data-availability limitations are retained in the corresponding station metadata and analysis outputs.

---

## 12. Study-Period Rules

The primary independently validated period is:

```text
2000–2023
```

Although some gridded datasets extend beyond 2023, equivalent independent station observations are not available for the complete later period.

Therefore:

```text
2000–2023
= independently validated period

2024–2026
= extended/model-driven period where applicable
```

The year 2026 is a partial year and should not be treated as a complete annual period.

---

## 13. Reproduction of Results

The repository contains machine-readable outputs corresponding to the principal manuscript analyses.

### Tables

```text
T1  Station inventory
T2  Data sources
T3  Pooled validation
T4  Rainfall detection
T5  Terrain correlation
T6  Nested bias model
T7  ML model comparison
T8  SHAP importance
T9  Per-station before/after correction
```

### Figures

```text
F1–F11
```

### Model and analytical outputs

```text
LOSO predictions
Statistical correction metrics
Island holdout metrics
Rainfall detection results
SHAP values
Reconstruction summaries
```

The intended relationship is:

```text
Input data
    ↓
Notebook analysis
    ↓
Intermediate datasets
    ↓
Metrics / predictions
    ↓
Tables
    ↓
Figures
```

---

## 14. Environment and Dependencies

The computational workflow uses Python-based scientific computing libraries.

The principal analysis environment requires packages associated with:

```text
pandas
numpy
scipy
statsmodels
scikit-learn
xgboost
lightgbm
shap
```

The repository provides:

```text
requirements.txt
```

for recording the required Python dependencies.

Exact numerical reproduction may vary slightly with differences in Python versions, package versions, operating systems, or model-library implementations.

---

## 15. External Data Dependencies

Complete reproduction may require access to externally sourced datasets and services.

These include:

* BMD station observations
* NASA POWER
* ERA5-Land
* Copernicus GLO-30
* SRTM v3
* JRC Global Surface Water
* Google Earth Engine-derived data products

The original source data should be obtained according to the relevant provider's access and redistribution conditions.

The provenance and role of each dataset are documented in:

```text
docs/data_provenance.md
```

---

## 16. Data Redistribution Considerations

Not all source datasets should necessarily be redistributed through GitHub.

In particular, the redistribution status of the original BMD observations depends on the terms under which the data were obtained.

Where large or restricted datasets cannot be directly included in the repository, the repository provides:

* dataset descriptions
* expected filenames
* variable information
* processing documentation
* required data provenance
* instructions for obtaining or accessing the corresponding data

---

## 17. Intermediate Outputs

The workflow preserves important intermediate outputs to improve traceability between raw inputs and final manuscript results.

Examples include:

```text
paired_era5.parquet
paired_power.parquet
terrain_skill_merged.csv
landscape_stratified_skill.csv
stat_correction_metrics.csv
loso_predictions.parquet
shap_features_tmax.parquet
shap_values_tmax.parquet
```

These files allow researchers to inspect intermediate analytical stages without relying exclusively on the final manuscript tables and figures.

---

## 18. Reproduction Procedure

A researcher attempting to reproduce the computational workflow should:

1. Clone or download the repository.
2. Create a compatible Python environment.
3. Install the dependencies listed in `requirements.txt`.
4. Obtain any required external datasets according to `docs/data_provenance.md`.
5. Place the required input datasets in the documented data locations.
6. Execute the notebooks in numerical order.
7. Verify intermediate outputs after each notebook.
8. Compare generated metrics with the versioned results.
9. Compare generated tables with the manuscript tables.
10. Compare generated figures with the manuscript figures.
11. Inspect LOSO predictions and island-holdout outputs independently.
12. Interpret reconstructed values according to the documented validation period.

---

## 19. Expected Outputs

A successful execution should reproduce or closely reproduce the principal analytical outputs, including:

* pooled validation metrics
* station-level validation metrics
* rainfall detection metrics
* terrain–bias correlations
* nested bias-model results
* statistical correction results
* machine-learning model comparisons
* LOSO predictions
* island holdout metrics
* SHAP feature-importance results
* manuscript tables
* manuscript figures
* reconstruction summaries

Small numerical differences may occur because of differences in computational environments or software versions.

---

## 20. Reproducibility Scope

This repository is the computational companion to Paper 1 of the BD-AgroClim research programme.

It documents and supports reproduction of the analyses, results, figures, and reconstruction workflow associated with the study.

The repository does not represent the complete computational workflows of the subsequent papers in the broader research programme.

```
```