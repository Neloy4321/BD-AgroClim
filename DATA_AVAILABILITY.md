# Data availability, traceability and redistribution limits

## What is public in this repository

- Reproducibility-oriented source code, audit scripts, notebook and source-file SHA-256 inventories.
- Derived aggregate evaluation tables (method/station-year, precipitation event and annual climate indices), plus selected `.csv.gz` compressed tables where the uncompressed CSV is large. Run `gzip -dk filename.csv.gz` to restore a CSV.
- Summary verification JSON, public source metadata, figure PNG/PDF and LaTeX tables.
- Comparison metrics that were computed from the already-preserved frozen held-out predictions; the full observation-level prediction archives remain private.

## What is deliberately not redistributable here

1. **BMD-derived daily observation table** (2000–2023) and its 326,861 cleaned station-day rows. Provenance indicates BMD ownership, but an official license explicitly permitting public redistribution has not been established. The manuscript must state its actual access terms; this GitHub repository cannot grant rights owned by BMD.
2. Any joined daily *observation/prediction* datasets, including `product_benchmarks/paired.pkl`, and BMD rain-date candidate correction tables containing source observation values.
3. Frozen model `.npz` artifacts that may contain observation-level `y_true` arrays. Audit summaries and SHA/metrics are shared instead.
4. The 124 MB processed ERA5-Land station-day CSV and 48 original-format Google Drive exports. The source comparisons and retrieval/generation procedures are documented; this release does not claim to host the full raw reanalysis archive.
5. The authors' **unrecovered original Earth Engine extraction script**, task logs and verified historical grid IDs. Reconstructed `.js` scripts in `source_recovery_kit/` are **independent replacements**, not original execution evidence.

## Original data source and access

- **BMD daily temperature/rainfall**: Bangladesh Meteorological Department, original access to be arranged through the agency. Formal archive-date/observation-window and 2000–2023 station-history clarification is outstanding as of 10 November 2026; a request was sent by the authors. No BMD primary observation records are implied to be public domain by the authors' access.
- **ERA5-Land**: Copernicus Climate Change Service / ECMWF ERA5-Land reanalysis; publicly obtainable under its current provider data terms and attribution requirements. Source years 2000–2023 and source-feature audits are documented in `pre_manuscript_run_20261110/era_source/`.
- **NASA POWER**: NASA Prediction Of Worldwide Energy Resources service; the comparative analysis specifies the exact common-row support.
- **BMD-derived Mendeley secondary archive**: derivative observations cannot by themselves authenticate historical station-day reporting rules. Independent QC found duplicated station-year sequences for some sites/years. It is not asserted to be the original BMD archival record.

## Processing and evidence semantics

- `ERA5 raw` denotes the original reanalysis input at the author-defined station site (not observed truth).
- `ET local` denotes the saved Extra Trees locally trained correction evaluated at held-out stations.
- A station held out of model fitting within the 34-site network is **not** a completely independent national network validation.
- Year-specific rainfall anomalies are identified as **sensitivity findings**; no code in this public release claims to have authenticated or uniformly corrected every BMD historical observation date.
- The published metrics are computed from the *author-processed* inputs as they were available in the source runs, unless a table clearly states a filtered evaluation-only subset.

## Reviewer access

For a reproducibility request requiring daily BMD values, the corresponding author should obtain appropriate BMD permissions or arrange a controlled inspection compliant with its data policy. There is no legitimate route to a fully public reproduction of private BMD observations solely from this repository.

