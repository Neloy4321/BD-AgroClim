# Independently recomputed validation evidence

The source observations are withheld from this archive; all results below were generated locally from the supplied seven-input dataset bundle. Numbers are mean station RMSE (same-station averaging, not pooled daily RMSE).

| Design | Variable | Raw | Monthly | ET local | ET terrain | HGB local | HGB terrain |
|---|---|---:|---:|---:|---:|---:|---:|
| LOSO | Tmax | 2.229 | 1.509 | 1.317 | 1.378 | — | — |
| LOSO | Tmin | 1.604 | 1.513 | 1.370 | 1.424 | — | — |
| LOSO | Prcp | 16.721 | 16.836 | 15.292 | 15.310 | — | — |
| Spatial blocks | Tmax | 2.229 | 1.526 | 1.401 | 1.391 | 1.415 | 1.407 |
| Spatial blocks | Tmin | 1.604 | 1.535 | 1.386 | 1.439 | 1.395 | 1.404 |
| Spatial blocks | Prcp | 16.721 | 16.889 | 15.500 | 15.489 | 15.708 | 15.678 |
| Space + time | Tmax | 2.277 | 1.428 | 1.394 | 1.356 | 1.383 | 1.367 |
| Space + time | Tmin | 1.565 | 1.528 | 1.402 | 1.435 | 1.394 | 1.394 |
| Space + time | Prcp | 16.263 | 16.384 | 15.302 | 15.269 | 15.416 | 15.410 |
| Future years | Tmax | 2.277 | 1.403 | 1.280 | 1.246 | 1.280 | 1.248 |
| Future years | Tmin | 1.565 | 1.497 | 1.333 | 1.201 | 1.332 | 1.207 |
| Future years | Prcp | 16.263 | 16.353 | 15.152 | 15.109 | 15.292 | 15.228 |
| 100-km buffer | Tmax | 2.229 | 1.544 | 1.463 | 1.445 | 1.463 | 1.486 |
| 100-km buffer | Tmin | 1.604 | 1.553 | 1.423 | 1.547 | 1.429 | 1.538 |
| 100-km buffer | Prcp | 16.721 | 16.936 | 15.667 | 15.571 | 16.015 | 15.849 |

## Alternative geographic partition sensitivity

The partition designs below are sensitivity checks of the same network, not independent external datasets.

| Partition | Target | Raw RMSE | ET local RMSE | ET terrain RMSE |
|---|---|---:|---:|---:|
| k4_s17 | Prcp | 16.721 | 15.507 | 15.493 |
| k4_s17 | Tmin | 1.604 | 1.389 | 1.466 |
| k4_s73 | Prcp | 16.721 | 15.500 | 15.489 |
| k4_s73 | Tmin | 1.604 | 1.386 | 1.439 |
| k5_s17 | Prcp | 16.721 | 15.445 | 15.451 |
| k5_s17 | Tmin | 1.604 | 1.397 | 1.456 |
| k6_s17 | Prcp | 16.721 | 15.446 | 15.443 |
| k6_s17 | Tmin | 1.604 | 1.397 | 1.453 |
| k6_s73 | Prcp | 16.721 | 15.455 | 15.448 |
| k6_s73 | Tmin | 1.604 | 1.399 | 1.452 |

## Verification

- Completed, checksum-verified model/target/fold jobs: **191**.
- Prior author-export LOSO comparison: **compared**; maximal absolute station RMSE delta **0.00000000**.
- Spatial holdouts disjoint at station level; temporal folds disjoint in time; native-only training excludes two ERA island locations with filled reanalysis.
- Predicted values are saved without observed BMD target values. Recompute scores by running with authorized original BMD data.

## Crucial scientific caveats

1. Dataset coordinates are labelled draft and have not been independently verified against station records or extraction grid points.
2. Historical comparison tests computational reproducibility against the author export, not independent field-data provenance.
3. All corrected models use the same station network and correlated samples; naive station-bootstrap intervals are exploratory and not formal spatial-inference guarantees.
4. A held-out station is out of sample for training but this is not a wholly new independent country or observing network.
5. Report validation-design effects with unmodified raw baselines, including failed terrain gains and rainfall-event trade-offs.
6. Physical observational data redistribution rights need separate confirmation. The prediction-only archive avoids including BMD daily observations.
