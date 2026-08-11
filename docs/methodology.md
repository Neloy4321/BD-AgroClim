````markdown
# Methodology

## Overview

BD-AgroClim is a research workflow for evaluating, analysing, bias-correcting, and reconstructing daily agro-climatic information for Bangladesh using station observations and gridded reanalysis products.

Paper 1 evaluates NASA POWER and ERA5-Land against 36 long-record Bangladesh Meteorological Department (BMD) stations, investigates terrain-related controls on reanalysis bias, applies statistical and machine-learning bias correction, evaluates spatial transferability using leave-one-station-out (LOSO) validation, and produces a reconstructed daily agro-climatic dataset.

The complete computational workflow is implemented through four Jupyter notebooks.

---

## 1. Study Design

The analysis uses 36 long-record BMD stations as the primary observational reference.

The principal validated study period is:

**1 January 2000 – 31 December 2023**

This period is defined by the temporal overlap between the station observations and the analysis requirements. Although ERA5-Land extends beyond 2023, independent station observations are not available for the later period for equivalent validation.

The study addresses four main research questions:

1. What is the daily bias structure of NASA POWER and ERA5-Land against the BMD station network, and how does it vary by season, landscape type, and rainfall intensity?

2. Do land fraction and sub-grid elevation variability explain reanalysis bias better than conventional spatial covariates?

3. Does neighbouring-station-assisted residual learning improve bias correction and rainfall detection performance?

4. How reliably does the correction transfer to spatially withheld stations under leave-one-station-out validation?

---

## 2. Data Preparation

### 2.1 BMD Station Observations

Daily observations of maximum temperature (Tmax), minimum temperature (Tmin), and precipitation (Prcp) are obtained from the cleaned BMD station dataset.

The cleaned station data contain both long-record and short-record stations. The primary analysis excludes records with:

```python
record_type == "short"
````

and retains the 36 long-record stations.

The cleaning procedure includes:

* station-name alias reconciliation
* duplicate-row handling
* physical-range quality control
* station-month z-score screening
* calendar completion
* explicit missing-value handling

The cleaned dataset covers 2000–2023.

---

## 3. Reanalysis Data

### 3.1 NASA POWER

NASA POWER daily data are used as one of the benchmark gridded products.

The dataset provides approximately 0.5° spatial resolution data over Bangladesh for 2000–2026.

The principal variables include:

* `T2M`
* `T2M_MAX`
* `T2M_MIN`
* `PRECTOTCORR`
* `RH2M`
* `WS2M`
* `ALLSKY_SFC_SW_DWN`
* `GWETTOP`
* `GWETROOT`

`GWETTOP` and `GWETROOT` are treated as dimensionless wetness fractions rather than volumetric soil-moisture measurements.

Because of its approximately 50 km grid spacing, NASA POWER is treated primarily as a benchmark product rather than a fine-scale spatial representation.

### 3.2 ERA5-Land

ERA5-Land daily data are extracted at the 36 station coordinates.

The dataset contains:

* mean, maximum, and minimum temperature
* dew-point temperature
* precipitation
* soil-water variables
* radiation
* evapotranspiration variables
* wind components
* surface pressure
* derived humidity and vapour-pressure variables

Several variables are derived during preprocessing, including:

* `ws2`
* `ea`
* `es`
* `rh_mean`
* `vpd`

The `era5_source` field distinguishes native ERA5-Land values from focal-filled values.

---

## 4. Station–Reanalysis Pairing

Station observations are paired with reanalysis estimates using:

```text
station_name + date
```

Station metadata are merged with observational records to provide spatial and administrative information including latitude, longitude, elevation, division, district, and region.

The resulting paired datasets form the basis for product-level validation and subsequent bias analysis.

---

## 5. Baseline Validation

NASA POWER and ERA5-Land are evaluated against BMD observations using multiple performance metrics.

The primary metrics include:

* Pearson correlation (`r`)
* mean bias
* mean absolute error (MAE)
* root mean square error (RMSE)
* Kling–Gupta Efficiency (KGE)
* Nash–Sutcliffe Efficiency (NSE)

Metrics are evaluated at pooled and station levels where appropriate.

Seasonal error patterns are also examined across landscape categories.

---

## 6. Rainfall Detection Analysis

Precipitation detection skill is evaluated using threshold-based contingency tables.

The rainfall thresholds are:

* 1 mm day⁻¹
* 10 mm day⁻¹
* 20 mm day⁻¹
* 50 mm day⁻¹

The reported categorical metrics include:

* Probability of Detection (POD)
* False Alarm Ratio (FAR)
* Critical Success Index (CSI)
* Heidke Skill Score (HSS)

The analysis evaluates whether bias correction changes rainfall-event detection performance, including at higher rainfall intensities.

---

## 7. Terrain and Spatial Bias Analysis

Terrain and land-surface characteristics are evaluated as potential controls on reanalysis performance.

The principal terrain variables include:

* DEM elevation
* SRTM elevation
* topographic position index
* terrain roughness
* sub-grid elevation mean
* sub-grid elevation standard deviation
* land fraction
* distance to water
* slope
* aspect
* northness
* eastness

Two variables are central to the analysis:

### `land_frac_9km`

The fraction of the ERA5-Land grid cell occupied by land.

### `elev_std_9km`

The standard deviation of elevation within the approximately 9 km ERA5-Land grid cell.

These variables are evaluated against station-level reanalysis skill using Spearman rank correlations.

---

## 8. Nested Bias Modelling

Station-level Tmax bias is modelled using nested predictor sets.

The analysis begins with land fraction and progressively adds terrain variables.

The selected parsimonious model uses:

```text
land_frac_9km
+
elev_std_9km
```

This model explains approximately 42.8% of the spatial variance in station-level Tmax bias.

Additional predictors are evaluated, but model complexity is constrained because the effective spatial sample consists of only 36 stations.

---

## 9. Statistical Bias Correction

Statistical correction methods are evaluated as baseline correction approaches.

The methodological framework includes:

* linear scaling
* empirical quantile mapping (EQM)
* trend-preserving quantile mapping (TQM)

These methods provide non-machine-learning baselines against which machine-learning correction methods can be compared.

---

## 10. Machine-Learning Bias Correction

Machine-learning correction is formulated as residual learning.

The evaluated model families include:

* Random Forest
* XGBoost
* LightGBM
* Extra Trees

The feature space can include:

* raw reanalysis variables
* derived atmospheric variables
* terrain variables
* neighbouring-station information

The objective is to learn systematic differences between reanalysis estimates and station observations while preserving the underlying temporal signal.

---

## 11. Leave-One-Station-Out Validation

Spatial generalisation is evaluated using leave-one-station-out (LOSO) cross-validation.

For each validation fold:

1. One station is completely withheld from model training.
2. The remaining eligible stations are used for training.
3. The trained model predicts the withheld station.
4. Prediction errors are calculated for the withheld station.
5. The process is repeated across the station network.

Random cross-validation is not used because spatial dependence can produce overly optimistic performance estimates.

The LOSO predictions are retained as machine-readable outputs in the repository.

---

## 12. Island Holdout Evaluation

Kutubdia and Sandwip receive special treatment because their ERA5-Land values required focal filling due to their location within masked ocean cells.

These stations are excluded from model training and used as an independent transferability test.

Their results are reported separately from the main station-level LOSO evaluation.

This distinction is important because focal-filled values are not equivalent to native ERA5-Land station extractions.

---

## 13. SHAP Interpretability

SHAP (SHapley Additive exPlanations) is applied to the LightGBM Tmax correction model.

The analysis produces:

* feature-level SHAP values
* feature-importance rankings
* SHAP visualisations

The purpose is to identify which environmental and reanalysis predictors contribute most strongly to the model's residual correction.

---

## 14. Reconstruction

Following model evaluation, the selected correction framework is used to generate corrected daily agro-climatic outputs.

The reconstructed dataset is intended to provide an analysis-ready resource for downstream applications such as:

* drought monitoring
* crop–climate analysis
* compound-event analysis
* climate-services research

The independently validated observational period remains 2000–2023. Any extension beyond the independently validated period must be interpreted as model-driven rather than independently ground-truth validated.

---

## 15. Computational Workflow

The complete workflow is organised into four notebooks:

```text
01_Validation_and_Data_Preparation.ipynb
        ↓
02_Terrain_and_Statistical_Analysis.ipynb
        ↓
03_ML_LOSO_and_SHAP.ipynb
        ↓
04_Reconstruction_and_Figure_Generation.ipynb
```

The notebooks generate the intermediate datasets, evaluation metrics, prediction outputs, tables, and figures included in the repository.

```
```
