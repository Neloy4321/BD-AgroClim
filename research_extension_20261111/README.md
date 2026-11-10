# BD-AgroClim — seasonal transfer and event-preserving rainfall extension

**Analysis date:** 11 November 2026. **Study:** Bangladesh station-located ERA5-Land correction, 2000–2023. **Status:** executed analysis of **frozen held-out predictions**, not new outer-fold training.

## Main novel analysis

1. **Season-resolved transfer:** Separate station-weighted RMSE comparisons for DJF (Dec–Feb), MAM (Mar–May), JJAS (Jun–Sep), and ON (Oct–Nov) under station, regional and space–time withholding.
2. **Nearest-donor distance × transfer benefit:** Great-circle training-donor separation versus station-level improvement, quartile aggregation and exploratory Spearman associations. No distance-only safety threshold is claimed.
3. **Daily versus annual climate-index selection:** Frozen model scores are compared with separately calculated 95%-complete-year Rx1day and R10mm errors. A lower daily RMSE can correspond to worse annual-index RMSE.
4. **Event-preserving correction (EPC):** A deterministic, untuned precipitation post-processor evaluated under frozen LOSO and regional-block predictions. The chosen event threshold is an **application requirement**, never tuned on outer held-out observed outcomes.

### EPC definition and guarantee

For raw ERA5-Land daily rainfall `r`, previously fitted ET-local rainfall `c`, and a prespecified threshold `T > 0`:

```python
EPC_T(r, c) = r                                 if r >= T
            = min(max(c, 0), nextafter(T, 0))  otherwise
```

For **every** event threshold `q >= T`, `EPC_T(r,c) >= q` if and only if `r >= q`. The event mask, raw-based contingency scores, and annual exceedance counts at such thresholds are therefore unchanged exactly. Annual maximum rainfall is also unchanged when the original annual maximum is at least `T`. This is **not** a guarantee of correct rain events, nor is it validated flood-risk safety. EPC cannot recover an observed event that raw ERA5-Land missed. `epc_public.py` independently checks the algebraic invariant on synthetic data.

## Numerical evidence — 34 withheld stations

| Protocol | Method | Daily rain RMSE (mm/day) | Annual R10mm RMSE (days) | Annual Rx1day RMSE (mm) |
|---|---|---:|---:|---:|
| LOSO | Raw | 16.721 | 16.733 | 92.819 |
| LOSO | ET local | 15.292 | 25.183 | 108.429 |
| LOSO | EPC10 | 16.522 | 16.733 | 92.819 |
| Four-region blocks | Raw | 16.721 | 16.733 | 92.819 |
| Four-region blocks | ET local | 15.500 | 26.990 | 112.840 |
| Four-region blocks | EPC10 | 16.536 | 16.733 | 92.819 |

Daily and annual entries are equally weighted means of **station-specific RMSE**, not a pooled RMSE across millions of daily cases. For EPC10, the station-level raw-minus-corrected daily RMSE improvement is 0.199 mm/day (95% station-bootstrap interval 0.176–0.221) under LOSO and 0.185 (0.161–0.209) under spatial blocks; 33 of 34 stations improve in each. These are *relative-to-raw* improvements and do not show better rainfall event truth.

### Other predeclared event thresholds

`T` values of 1, 10, 20 and 50 mm were inspected without outcome-based threshold choice. The trade-off is real: preserving all raw R10mm events with EPC10 yields less daily benefit than allowing R10mm counts to change with EPC20 or EPC50. Plot `Fig15_threshold_frontier` illustrates this choice. The experimental `FALLBACK20` comparison does **not** cap subthreshold ET predictions, and thus does **not** preserve lower event thresholds.

## File guide

| File | Contents |
|---|---|
| `epc_public.py` | Public pure NumPy EPC implementation and self-test |
| `analyze_transfer_novelty.py` | Full matched-row audit and analysis; **requires restricted source files** |
| `outputs/seasonal_station_benefits.csv` | Aggregate station-mean seasonal benefits, paired tests and station bootstrap intervals |
| `outputs/distance_transfer_associations.csv` | Aggregate distance association by variable/protocol |
| `outputs/distance_quartile_risk.csv` | Aggregate distance bins, no station IDs |
| `outputs/mean_station_daily_rmse.csv` | Aggregate daily scores for ET and EPC thresholds |
| `outputs/annual_extreme_station_rmse.csv` | Aggregate station-weighted annual index RMSE |
| `outputs/annual_extreme_station_mae.csv` | Annual index absolute-error sensitivity, separately defined |
| `outputs/daily_extreme_rank_discordance.csv` | Number of station-wise ranking reversals |
| `outputs/run_provenance.json` | Analysis settings and evidence boundaries |
| `outputs/Fig11*` to `outputs/Fig15*` | Generated plots in PDF/PNG |

`run_log.txt` records the actual analysis completion and validity assertions. Figures and aggregate tables are computed outputs, not illustrated or generated example values.

## Reproduce

```bash
python -m pip install numpy pandas scipy matplotlib
python epc_public.py
python analyze_transfer_novelty.py
```

The second command expects the original repository-rebuild layout with `/research_rebuild/results/jobs/` and `/research_v2/input/dataset/` relative to the parent directory. These paths include **private row-linked `.npz` predictions and author-processed station observations**. They cannot be fully reconstructed from the public release alone; access requires documented permission. The script compares every saved `RAW` prediction with the paired ERA5-Land CSV and checks that each outer fold's training and test stations are disjoint. It runs 3,000 station-level bootstrap resamples, uses calendar-year 95% observation availability for climate indices, and exports only aggregate, non-row-linked evidence.

## Important limitations

- The BMD-derived processed source is subject to provenance/licensing constraints and the physical historical rainfall observation-day boundary has not been authenticated. Separate 2021/2023 date-label discrepancies are not resolved here. No date was shifted and no ET model refitted to alternate labels.
- The identical 34 physical stations recur under LOSO and four-region withholding; these are separate **validation designs**, not independent external networks.
- Coordinates are supplied draft metadata, not verified station relocation histories. Distance association does not imply causal effects or establish an operational threshold.
- The algebraic EPC guarantee preserves raw **event masks**, not skill relative to truth. It does not extend to Rx5day, event timing, wet-day totals, crop yield or flood decisions.
- Public files do **not** redistribute original BMD station data, row-linked frozen predictions, row-linked SHAP values, or third-party data contrary to their source conditions.

This extension is documented in the updated main manuscript Methods/Results and Supplementary Sections S9–S10. Retain the pre-extension source/figure files as previous versions; do not silently replace raw archived evidence.
