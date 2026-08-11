# BD-AgroClim

## Land-Fraction and Sub-Grid Relief Controls on Reanalysis Bias and Machine-Learning Reconstruction of Daily Agro-Climatic Data for Bangladesh

BD-AgroClim is the computational research repository accompanying **Paper 1** of a broader research programme on Bangladesh agro-climatic drought, climate-data reconstruction, and downstream climate-impact analysis.

The study evaluates daily **NASA POWER** and **ERA5-Land** data against observations from **36 Bangladesh Meteorological Department (BMD) stations**. It investigates terrain and land-surface controls on reanalysis bias, develops statistical and machine-learning bias-correction methods, evaluates spatial transferability using strict **leave-one-station-out (LOSO) validation**, and generates a corrected daily agro-climatic dataset for Bangladesh.

The independently validated study period is **2000–2023**.

## Research Questions

### RQ1 — Baseline Reanalysis Performance

What is the daily bias structure of NASA POWER and ERA5-Land against the 36 BMD stations, and how does performance vary by season, landscape type, and rainfall intensity?

### RQ2 — Terrain Controls on Bias

Do land fraction and sub-grid elevation variability explain reanalysis bias better than conventional spatial covariates?

### RQ3 — Machine-Learning Bias Correction

Does neighbouring-station-assisted residual learning improve bias correction and rainfall-event detection performance?

### RQ4 — Spatial Transferability

Under strict leave-one-station-out validation, how reliably does the correction framework transfer to spatially withheld stations?

## Key Contributions

- Joint point-scale evaluation of NASA POWER and ERA5-Land against 36 BMD stations in Bangladesh.
- Systematic analysis of spatial, seasonal, landscape, and rainfall-intensity-dependent reanalysis errors.
- Identification of `land_frac_9km` and `elev_std_9km` as important controls on ERA5-Land Tmax bias.
- Statistical and machine-learning approaches for correcting systematic reanalysis errors.
- A residual-learning framework incorporating neighbouring-station information.
- Strict spatial validation through leave-one-station-out cross-validation.
- Independent evaluation of the focal-filled island stations Kutubdia and Sandwip.
- SHAP-based interpretation of the selected LightGBM Tmax correction model.
- A reproducible computational workflow and machine-readable analytical outputs.

## Principal Findings

### Baseline Performance

ERA5-Land shows stronger Tmax correlation with observations than NASA POWER, while exhibiting a larger systematic cold bias. ERA5-Land precipitation remains substantially more difficult to reproduce at daily station scale than temperature.

| Variable | ERA5-Land | NASA POWER |
|---|---:|---:|
| Tmax correlation | 0.896 | 0.781 |
| Tmax bias (°C) | -1.63 | -0.90 |
| Tmax KGE | 0.847 | 0.752 |
| Tmin correlation | 0.951 | 0.943 |
| Tmin bias (°C) | +0.14 | +0.11 |
| Precipitation correlation | 0.448 | 0.515 |

### Terrain Controls

The terrain variables `land_frac_9km` and `elev_std_9km` are particularly important. Together, the selected terrain predictors explain approximately **43% of the spatial variance in Tmax bias** across the 36-station network.

### Extreme Rainfall Detection

Rainfall detection skill decreases substantially as rainfall intensity increases. The Probability of Detection (POD) decreases from approximately **0.91 at 1 mm/day** to **0.13 at 50 mm/day**. This demonstrates that precipitation intensity remains a major limitation even when overall precipitation statistics appear acceptable.

### Machine-Learning Correction

The machine-learning framework uses residual learning with tree-based ensemble models:

- Random Forest
- Extra Trees
- XGBoost
- LightGBM

The selected LightGBM correction framework substantially reduces Tmax error under strict spatial validation:

| Metric | Before correction | After correction |
|---|---:|---:|
| Tmax RMSE | approximately 2.25 °C | approximately 1.36 °C |
| Mean bias | approximately -1.59 °C | approximately -0.03 °C |

### Interpretability

SHAP analysis identifies important contributors to Tmax residual correction, including atmospheric and terrain-related predictors such as soil moisture, sub-grid elevation variability, and vapour pressure deficit.

### Island Transferability

Kutubdia and Sandwip are treated as independent challenging coastal cases because their ERA5-Land values involve focal filling. They are excluded from model training and evaluated separately to test transferability under non-native reanalysis conditions.

## Study Scope and Validation Period

The principal independently validated period is:

```text
2000–2023
```

Although some source datasets extend beyond 2023, equivalent independent BMD observations are not available for complete validation throughout the later period. Therefore, values beyond 2023 should not be interpreted as independently ground-truth-validated observations.

The year **2026 is partial** and should not be treated as a complete annual period.

## Repository Structure

```text
BD-AgroClim/
│
├── README.md
├── LICENSE
├── CITATION.cff
├── requirements.txt
├── .gitignore
│
├── notebooks/
│   ├── 01_Validation_and_Data_Preparation.ipynb
│   ├── 02_Terrain_and_Statistical_Analysis.ipynb
│   ├── 03_ML_LOSO_and_SHAP.ipynb
│   └── 04_Reconstruction_and_Figure_Generation.ipynb
│
├── data/
│   └── metadata/
│
├── results/
│   ├── tables/
│   ├── metrics/
│   └── predictions/
│
├── figures/
│
└── docs/
    ├── methodology.md
    ├── data_provenance.md
    └── reproducibility.md
```

## Computational Workflow

```text
BMD Station Observations
          │
          ▼
Data Cleaning & Quality Control
          │
          ▼
Station–Reanalysis Pairing
          │
     ┌────┴────┐
     ▼         ▼
NASA POWER  ERA5-Land
     │         │
     └────┬────┘
          ▼
Baseline Validation
          │
          ▼
Terrain & Spatial Bias Analysis
          │
          ▼
Statistical Bias Correction
          │
          ▼
Machine-Learning Bias Correction
          │
          ▼
LOSO Spatial Validation
          ├──────────────► Island Holdout
          ▼
SHAP Interpretation
          │
          ▼
Corrected Reconstruction
          │
          ▼
Tables & Figures
```

## Notebook Workflow

The notebooks should be executed in numerical order.

### 01 — Validation and Data Preparation

`notebooks/01_Validation_and_Data_Preparation.ipynb` performs:

- Station-data preparation
- Quality control
- Station selection
- NASA POWER loading
- ERA5-Land loading
- Station–reanalysis pairing
- Data-availability analysis
- Baseline validation
- Rainfall detection analysis

### 02 — Terrain and Statistical Analysis

`notebooks/02_Terrain_and_Statistical_Analysis.ipynb` performs:

- Terrain-data integration
- Landscape-stratified analysis
- Terrain–skill analysis
- Spearman correlation analysis
- Nested bias modelling
- Statistical correction analysis

Key terrain variables include:

```text
land_frac_9km
elev_std_9km
roughness_5km
elev_dem
tpi_5km
dist_water_km
northness
eastness
```

### 03 — Machine Learning, LOSO and SHAP

`notebooks/03_ML_LOSO_and_SHAP.ipynb` performs:

- Machine-learning bias correction
- Residual learning
- Model comparison
- Neighbouring-station feature analysis
- Leave-one-station-out validation
- Island holdout evaluation
- SHAP analysis

Evaluated models include Random Forest, Extra Trees, XGBoost, and LightGBM.

### 04 — Reconstruction and Figure Generation

`notebooks/04_Reconstruction_and_Figure_Generation.ipynb` performs:

- Corrected-series reconstruction
- Reconstruction summaries
- Manuscript figure generation
- Final diagnostics
- Final analytical outputs

## Figures

| Figure | Description |
|---|---|
| F1 | Spatial distribution of the 36 BMD stations |
| F2 | Station–ERA5-Land data availability |
| F3 | Taylor diagrams for Tmax, Tmin, and precipitation |
| F4 | Terrain controls on ERA5-Land bias |
| F5 | Seasonal Tmax error by landscape type |
| F6 | Precipitation error and detection skill |
| F7 | Spatial pattern of ERA5-Land skill |
| F8 | LOSO RMSE across correction methods |
| F9 | SHAP feature contributions for Tmax correction |
| F10 | Before/after Tmax correction at representative stations |
| F11 | Kutubdia and Sandwip island focal-fill diagnostic |

## Results and Analytical Outputs

### Tables

The `results/tables/` directory contains manuscript result tables, including:

- Station inventory
- Data sources
- Pooled validation
- Rainfall detection
- Terrain correlations
- Nested bias models
- Machine-learning comparison
- SHAP importance
- Station-level before/after correction

### Metrics

The `results/metrics/` directory contains derived performance and evaluation metrics, including:

- Homogeneity results
- Landscape-stratified skill
- Statistical correction metrics
- Island holdout metrics
- Rainfall detection results
- Reconstruction summaries

### Predictions

The `results/predictions/` directory contains model-level prediction outputs, including:

```text
loso_predictions.parquet
corrected_stat.parquet
```

## Data

Primary and derived datasets are documented in [`docs/data_provenance.md`](docs/data_provenance.md).

Important data resources include:

```text
bmd_clean_daily.csv
station_metadata_final.csv
NASA_POWER_Climate_Data_Bangladesh_2000_2026.csv
era5land_stations_daily_v2.csv
terrain_full.csv
terrain_skill_merged.csv
```

Large datasets and source data subject to redistribution restrictions may be distributed through an archival repository rather than directly through GitHub.

## Reproducibility

Detailed methodological and computational documentation is provided in:

- [`docs/methodology.md`](docs/methodology.md)
- [`docs/data_provenance.md`](docs/data_provenance.md)
- [`docs/reproducibility.md`](docs/reproducibility.md)

### Recommended Reproduction Procedure

1. Clone the repository.
2. Create a compatible Python environment.
3. Install the dependencies from `requirements.txt`.
4. Obtain the required external datasets.
5. Place the datasets in the documented locations.
6. Execute the notebooks in numerical order.
7. Verify the intermediate outputs.
8. Compare the generated metrics, tables, and figures with the versioned outputs.

## Software Environment

The analysis is implemented in Python. Core scientific and machine-learning dependencies include:

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

CPU execution is sufficient for the Paper 1 workflow. The exact package versions used for reproduction are specified in [`requirements.txt`](requirements.txt).

## Data Availability

The repository distinguishes between:

- Primary observational data
- Externally sourced gridded data
- Derived datasets
- Intermediate analytical outputs
- Model predictions
- Final research outputs

The redistribution of original BMD observations is subject to the relevant data-access conditions.

Large datasets and reconstructed outputs may be archived through **Zenodo** or another appropriate research-data repository to provide persistent access and DOI-based citation. The corresponding archival DOI will be added to this repository when the data release is finalised.

## Citation

If you use the code, methodology, figures, or derived datasets from this repository, please cite the associated research paper and the archived dataset. Citation metadata are provided in [`CITATION.cff`](CITATION.cff).

## Authors

**Neloy Pramanik Supto**  
Department of Computer Science and Engineering  
Daffodil International University, Dhaka, Bangladesh

**Sajib Biswas**  
Department of Computer Science and Engineering  
Daffodil International University, Dhaka, Bangladesh

**Sazal Das**  
Department of Computer Science and Engineering  
Daffodil International University, Dhaka, Bangladesh

## Research Project

**BD-AgroClim** is the foundation study of a broader research programme on Bangladesh agro-climatic drought, climate-data reconstruction, and downstream climate-impact analysis. This repository corresponds specifically to **Paper 1**. Subsequent papers use the reconstructed agro-climatic resource as a foundation for downstream analyses.

## License

See [`LICENSE`](LICENSE) for the applicable repository license.

## Reproducibility and Transparency

This repository is intended to provide a transparent computational record of the analyses reported in the associated study. It separates source data, derived data, analytical outputs, model predictions, figures, and documentation so that the relationship between the underlying datasets and reported scientific results can be inspected systematically.
