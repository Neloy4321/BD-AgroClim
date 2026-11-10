#!/usr/bin/env python3
"""Auditable ERA5-Land transfer experiments using the authors' embedded model code.

No raw BMD observations or observed prediction labels are written to output.
The input directory must contain the original seven CSVs (at any depth).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import time
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pandas as pd
import scipy
import sklearn
from sklearn.cluster import KMeans

from paper1_pipeline.core import (
    Config,
    ISLANDS,
    LOCAL,
    TARGETS,
    TERRAIN,
    haversine_matrix,
    load_inputs,
    sha256,
)
from paper1_pipeline.experiments import split_definitions
from paper1_pipeline.models import MonthlyCorrection, ResidualModel

os.environ.setdefault("LOKY_MAX_CPU_COUNT", "9")


def station_scores(test: pd.DataFrame, observed: str, predictions: dict[str, np.ndarray],
                   experiment: str, fold: str, target: str, design: str) -> pd.DataFrame:
    rows = []
    y = test[observed].to_numpy(dtype=float)
    stations = test.station_name.to_numpy()
    for station in sorted(set(stations)):
        m = stations == station
        for method, pred in predictions.items():
            e = pred[m] - y[m]
            rows.append({
                "experiment": experiment, "design": design, "fold": fold,
                "target": target, "station_name": station, "method": method,
                "n_days": int(m.sum()), "rmse": float(np.sqrt(np.mean(e**2))),
                "mae": float(np.mean(np.abs(e))), "bias": float(np.mean(e)),
            })
    return pd.DataFrame(rows)


def event_scores(test: pd.DataFrame, observed: str, predictions: dict[str, np.ndarray],
                 experiment: str, fold: str, design: str) -> pd.DataFrame:
    rows = []
    if observed != "obs_prcp":
        return pd.DataFrame()
    truth = test[observed].to_numpy(dtype=float)
    for threshold in (1, 10, 20, 50):
        occurred = truth >= threshold
        for method, pred in predictions.items():
            predicted = pred >= threshold
            hit = int((occurred & predicted).sum())
            miss = int((occurred & ~predicted).sum())
            false = int((~occurred & predicted).sum())
            rows.append({
                "experiment": experiment, "design": design, "fold": fold,
                "method": method, "threshold_mm": threshold,
                "hits": hit, "misses": miss, "false_alarms": false,
                "pod": hit/(hit+miss) if hit+miss else np.nan,
                "far": false/(hit+false) if hit+false else np.nan,
                "csi": hit/(hit+miss+false) if hit+miss+false else np.nan,
            })
    return pd.DataFrame(rows)


def geographic_blocks(full: pd.DataFrame, k: int = 4, seed: int = 42):
    meta = full.loc[~full.station_name.isin(ISLANDS),
                    ["station_name", "lat", "lon"]].drop_duplicates().sort_values("station_name")
    xy = meta[["lat", "lon"]].to_numpy(copy=True)
    xy[:, 1] *= np.cos(np.deg2rad(xy[:, 0].mean()))
    labels = KMeans(n_clusters=k, random_state=seed, n_init=20).fit_predict(xy)
    return [tuple(sorted(meta.station_name.to_numpy()[labels == j])) for j in range(k)]


def scheduled_jobs(full: pd.DataFrame, stage: str, smoke: bool):
    cfg = Config()
    period = full.loc[full.date.between(cfg.study_start, cfg.study_end)]
    native = period.loc[~period.station_name.isin(ISLANDS)]
    if stage == "loso":
        for fold, train, test in split_definitions(full, cfg, "loso"):
            yield "loso", "seed42", fold, train, test
        return
    if stage == "geometry":
        for mode in ("spatial_block", "spatiotemporal", "temporal"):
            for fold, train, test in split_definitions(full, cfg, mode):
                yield mode, "seed42", fold, train, test
        blocks = geographic_blocks(period)
        meta = native[["station_name", "lat", "lon"]].drop_duplicates().set_index("station_name")
        for i, held in enumerate(blocks):
            donor = tuple(sorted(set(meta.index) - set(held)))
            distances = haversine_matrix(meta.loc[list(donor), ["lat", "lon"]],
                                         meta.loc[list(held), ["lat", "lon"]])
            eligible = [name for name, ds in zip(donor, distances) if np.min(ds) >= 100.0]
            assert len(eligible) >= 8
            yield "buffer100", "seed42", f"block_{i}", \
                native.loc[native.station_name.isin(eligible)], \
                period.loc[period.station_name.isin(held)]
        return
    if stage == "partitions":
        # Multiple K-means initializations. Identical assignments are deduplicated.
        seen: set[tuple] = set()
        names = tuple(sorted(native.station_name.unique()))
        for k in (4, 5, 6):
            for seed in (17, 73):
                blocks = geographic_blocks(period, k, seed)
                signature = tuple(tuple(sorted(set(names) - set(block))) for block in blocks)
                signature = tuple(sorted(signature))
                if signature in seen:
                    continue
                seen.add(signature)
                for i, held in enumerate(blocks):
                    yield "partition", f"k{k}_s{seed}", f"block_{i}", \
                        native.loc[~native.station_name.isin(held)], \
                        period.loc[period.station_name.isin(held)]
        return
    raise ValueError(stage)


def source_manifest(data: dict, code_dir: Path, cfg: Config) -> dict:
    return {
        "created_utc": pd.Timestamp.now(tz="UTC").isoformat(),
        "purpose": "Independent reproduction and cross-target withheld validation",
        "data_files": {key: {"name": path.name, "sha256": sha256(path), "bytes": path.stat().st_size}
                       for key, path in data["paths"].items()},
        "code_sha256": {str(p.relative_to(code_dir)): sha256(p)
                        for p in sorted(code_dir.rglob("*.py"))},
        "versions": {"python": platform.python_version(), "pandas": pd.__version__,
                     "numpy": np.__version__, "scipy": scipy.__version__,
                     "scikit_learn": sklearn.__version__},
        "configuration": asdict(cfg),
        "privacy": "No BMD observed y values in generated outputs; full recomputation requires user-supplied BMD inputs.",
    }


def run(args):
    start = time.time()
    out = Path(args.output).resolve()
    out.mkdir(parents=True, exist_ok=True)
    cfg = Config(seed=42, n_jobs=args.jobs, max_train_rows=50000)
    data = load_inputs(args.input)
    full = data["full"]
    if not (out/"run_manifest.json").exists():
        (out/"run_manifest.json").write_text(
            json.dumps(source_manifest(data, Path(__file__).parent, cfg), indent=2))
    else:
        existing = json.loads((out/"run_manifest.json").read_text())
        actual = source_manifest(data, Path(__file__).parent, cfg)
        assert existing["data_files"] == actual["data_files"], "Source file hash changed"
        assert existing["code_sha256"] == actual["code_sha256"], "Code changed: use a fresh output directory"
        # JSON serializes dataclass tuples as lists; normalize both sides first.
        assert existing["configuration"] == json.loads(json.dumps(actual["configuration"])), "Configuration changed"
    stages = ["geometry", "loso", "partitions"] if args.stage == "all" else [args.stage]
    completed = 0
    for stage in stages:
        for mode, design, fold, train_all, test_all in scheduled_jobs(full, stage, args.smoke):
            for target in ("Tmax", "Tmin", "Prcp"):
                if args.smoke and (completed > 0 or target != "Tmax"):
                    continue
                if stage == "partitions" and target == "Tmax":
                    # The published manuscript already reports this extensive experiment.
                    continue
                key = f"{mode}__{design}__{fold}__{target}"
                base = out/"jobs"/key
                if base.with_suffix(".csv").exists() and base.with_suffix(".json").exists():
                    print("RESUME", key, flush=True)
                    completed += 1
                    continue
                obs, raw = TARGETS[target]
                train = train_all.dropna(subset=[obs, raw]).copy()
                test = test_all.dropna(subset=[obs, raw]).copy()
                assert len(train) > 0 and len(test) > 0
                assert not set(train.row_id).intersection(test.row_id)
                assert not set(train.station_name).intersection(ISLANDS)
                # Geometric tests hold out complete station groups; temporal holds out later dates.
                if mode != "temporal":
                    assert not set(train.station_name).intersection(test.station_name)
                elif mode == "temporal":
                    assert train.date.max() < test.date.min()
                methods = ["ET_LOCAL", "ET_TERRAIN"]
                if stage == "geometry":
                    methods += ["HGB_LOCAL", "HGB_TERRAIN"]
                predictions: dict[str, np.ndarray] = {"RAW": test[raw].to_numpy(dtype=float)}
                monthly = MonthlyCorrection(precip=(target == "Prcp")).fit(train, obs, raw)
                predictions["MONTHLY"] = monthly.predict(test)
                job_start = time.time()
                for method in methods:
                    kind, feature_set = method.split("_")
                    feats = LOCAL + (TERRAIN if feature_set == "TERRAIN" else [])
                    fit = ResidualModel().fit(train, obs, raw, feats, cfg, kind)
                    predictions[method] = fit.predict(test)
                if target == "Prcp":
                    predictions = {name: np.maximum(p, 0) for name, p in predictions.items()}
                scores = station_scores(test, obs, predictions, mode, fold, target, design)
                event = event_scores(test, obs, predictions, mode, fold, design)
                base.parent.mkdir(parents=True, exist_ok=True)
                scores.to_csv(base.with_suffix(".csv"), index=False)
                if len(event):
                    event.to_csv(base.with_name(base.name+"__events.csv"), index=False)
                # Prediction-only evidence. The withheld observations are intentionally excluded.
                np.savez_compressed(base.with_suffix(".npz"), row_id=test.row_id.to_numpy(), **predictions)
                report = {
                    "experiment": mode, "design": design, "fold": fold, "target": target,
                    "train_station_names": sorted(train.station_name.unique().tolist()),
                    "test_station_names": sorted(test.station_name.unique().tolist()),
                    "n_train_available": len(train), "n_train_sample_limit": cfg.max_train_rows,
                    "n_test": len(test), "train_first": str(train.date.min().date()),
                    "train_last": str(train.date.max().date()),
                    "test_first": str(test.date.min().date()), "test_last": str(test.date.max().date()),
                    "methods": methods + ["RAW", "MONTHLY"],
                    "duration_seconds": round(time.time()-job_start, 3),
                    "result_sha256": sha256(base.with_suffix(".csv")),
                    "predictions_sha256": sha256(base.with_suffix(".npz")),
                }
                base.with_suffix(".json").write_text(json.dumps(report, indent=2))
                completed += 1
                result = scores.groupby("method").rmse.mean().round(4).to_dict()
                print(f"DONE {key} n={len(test)} {time.time()-job_start:.1f}s {result}", flush=True)
            if args.smoke and completed:
                break
        if args.smoke and completed:
            break
    aggregate(out)
    print(f"FINISHED {completed} jobs in {time.time()-start:.1f}s", flush=True)


def aggregate(out: Path):
    frames = [pd.read_csv(p) for p in sorted((out/"jobs").glob("*.csv")) if not p.name.endswith("__events.csv")]
    if not frames:
        return
    rows = pd.concat(frames, ignore_index=True)
    rows.to_csv(out/"station_metrics.csv", index=False)
    # A unique station contributes equally to its experiment/design score.
    summary = rows.groupby(["experiment", "design", "target", "method"], as_index=False).agg(
        mean_station_rmse=("rmse", "mean"),
        mean_station_mae=("mae", "mean"),
        station_count=("station_name", "nunique"),
        tested_station_days=("n_days", "sum"),
    )
    summary.to_csv(out/"summary.csv", index=False)
    event_frames = [pd.read_csv(p) for p in sorted((out/"jobs").glob("*__events.csv"))]
    if event_frames:
        events = pd.concat(event_frames, ignore_index=True)
        events.to_csv(out/"rainfall_event_fold_metrics.csv", index=False)
        group = events.groupby(["experiment", "design", "method", "threshold_mm"],as_index=False)[
            ["hits", "misses", "false_alarms"]].sum()
        group["pod"] = group.hits/(group.hits+group.misses)
        group["far"] = group.false_alarms/(group.hits+group.false_alarms)
        group["csi"] = group.hits/(group.hits+group.misses+group.false_alarms)
        group.to_csv(out/"rainfall_event_summary.csv", index=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Directory containing the original seven CSV inputs")
    parser.add_argument("--output", required=True, help="Directory for results, no raw observations saved")
    parser.add_argument("--stage", choices=["geometry", "loso", "partitions", "all"], default="all")
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--smoke", action="store_true", help="One cheap end-to-end fold")
    run(parser.parse_args())
