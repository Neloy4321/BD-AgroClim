"""Frozen-held-out reanalysis correction diagnostics, without model refitting.

All observations are used ONLY for evaluating already-saved test predictions.
No results from a held-out station are used to select a policy/threshold.
Public outputs deliberately omit station names, coordinates, dates, and row IDs.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import spearmanr, wilcoxon

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "research_v2/input/dataset"
JOBS = ROOT / "research_rebuild/results/jobs"
OUT = Path(__file__).resolve().parent / "outputs"
OUT.mkdir(exist_ok=True)

TARGET = {"Tmax": ("tmax", "t2m_max"), "Tmin": ("tmin", "t2m_min"),
          "Prcp": ("prcp_obs", "prcp")}
SEASON = {12: "DJF", 1: "DJF", 2: "DJF", 3: "MAM", 4: "MAM", 5: "MAM",
          6: "JJAS", 7: "JJAS", 8: "JJAS", 9: "JJAS", 10: "ON", 11: "ON"}
SEASONS = ["DJF", "MAM", "JJAS", "ON"]
RNG = np.random.default_rng(20261111)


def haversine(a, b):
    a, b = np.deg2rad(np.asarray(a)), np.deg2rad(np.asarray(b))
    dlat = a[0] - b[:, 0]
    dlon = a[1] - b[:, 1]
    x = np.sin(dlat / 2) ** 2 + np.cos(a[0]) * np.cos(b[:, 0]) * np.sin(dlon / 2) ** 2
    return float((6371 * 2 * np.arcsin(np.sqrt(np.clip(x, 0, 1)))).min())


def rmse(a, b):
    a, b = np.asarray(a), np.asarray(b)
    keep = np.isfinite(a) & np.isfinite(b)
    return float(np.sqrt(np.mean((a[keep] - b[keep]) ** 2))) if keep.sum() >= 3 else np.nan


def bias(a, b):
    a, b = np.asarray(a), np.asarray(b)
    keep = np.isfinite(a) & np.isfinite(b)
    return float(np.mean(a[keep] - b[keep])) if keep.sum() >= 3 else np.nan


def bootstrap_ci(values, n=3000):
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values)]
    if len(values) < 4:
        return (np.nan, np.nan)
    sample = RNG.integers(0, len(values), size=(n, len(values)))
    means = values[sample].mean(axis=1)
    return tuple(map(float, np.percentile(means, [2.5, 97.5])))


def main():
    print("Loading original processed observations and reanalysis index ...", flush=True)
    era = pd.read_csv(INPUT / "era5land_stations_daily/era5land_stations_daily_v2.csv",
                      usecols=["station_name", "date", "t2m_max", "t2m_min", "prcp"])
    era = era.sort_values(["station_name", "date"]).reset_index(drop=True)
    era["date"] = pd.to_datetime(era.date)
    era["year"] = era.date.dt.year
    era["season"] = era.date.dt.month.map(SEASON)
    era["row_id"] = np.arange(len(era))
    bmd = pd.read_csv(INPUT / "BMD data/bmd_clean_daily.csv")
    bmd = bmd.query("record_type == 'long'").drop(columns="record_type")
    bmd = bmd.rename(columns={"prcp": "prcp_obs"})
    bmd["date"] = pd.to_datetime(bmd.date)
    base = era.merge(bmd, on=["station_name", "date"], how="left", validate="one_to_one")
    assert len(base) == len(era) and base.row_id.is_unique
    meta = pd.read_csv(INPUT / "BMD data/station_metadata_final.csv")
    coords = {r.station_name: (float(r.lat), float(r.lon)) for r in meta.itertuples()}
    station_folds = {"loso": set(), "spatial_block": set(), "spatiotemporal": set()}
    season_rows, all_rows, annual_rows = [], [], []
    seen = {}
    methods = ["RAW", "MONTHLY", "ET_LOCAL", "ET_TERRAIN", "HGB_LOCAL", "HGB_TERRAIN"]
    for exp in station_folds:
        for target in TARGET:
            files = sorted(JOBS.glob(f"{exp}__seed42__*__{target}.npz"))
            for file in files:
                tag = file.stem
                rec = json.loads(file.with_suffix(".json").read_text())
                pred = np.load(file)
                rid = pred["row_id"].astype(int)
                assert len(rid) == len(set(rid))
                subset = base.iloc[rid].copy()
                assert np.allclose(subset[TARGET[target][1]], pred["RAW"], atol=1e-8, rtol=0)
                assert set(subset.station_name).issubset(set(rec["test_station_names"]))
                assert not set(rec["train_station_names"]).intersection(rec["test_station_names"])
                obscol = TARGET[target][0]
                if not np.isfinite(subset[obscol]).all():
                    raise ValueError(f"Frozen rows included non-finite observed target: {file.name}")
                for method in pred.files:
                    if method != "row_id":
                        subset["pred_" + method] = pred[method]
                # A predefined exploratory rainfall gate, not trained/tuned on test outcomes.
                if target == "Prcp":
                    raw = subset.pred_RAW.to_numpy()
                    et = subset.pred_ET_LOCAL.to_numpy()
                    subset["pred_FALLBACK20"] = np.where(raw >= 20.0, raw, et)
                    # Event-preserving correction (EPC10): a pre-specified
                    # constraint at the published R10mm climate-index boundary.
                    # No observation-conditional gating; never change a raw
                    # >=10-mm event, and never create one on a raw <10-mm day.
                    # Four predeclared thresholds (wet day, moderate, heavy,
                    # very heavy). Each EPC_T preserves ALL event masks >=T.
                    for threshold in (1, 10, 20, 50):
                        below = np.nextafter(float(threshold), 0.0)
                        name = f"pred_EPC{threshold}"
                        subset[name] = np.where(raw >= threshold, raw,
                                               np.minimum(np.maximum(et, 0.0), below))
                        for h in (threshold, 50.0 if threshold < 50 else threshold):
                            assert np.array_equal(raw >= h, subset[name].to_numpy() >= h)
                seen[(exp, target, tag)] = (len(subset), len(rec["test_station_names"]))
                for station, grp in subset.groupby("station_name"):
                    dist = haversine(coords[station], [coords[s] for s in rec["train_station_names"]])
                    station_folds[exp].add(station)
                    eligible = [m for m in methods + ["FALLBACK20", "EPC1", "EPC10", "EPC20", "EPC50"] if "pred_" + m in grp]
                    for s, gs in grp.groupby("season"):
                        if len(gs) < 20:
                            continue
                        for method in eligible:
                            season_rows.append({"protocol": exp, "variable": target, "fold": rec["fold"],
                                                "station": station, "season": s, "method": method,
                                                "n": len(gs), "distance_km": dist,
                                                "rmse": rmse(gs["pred_" + method], gs[obscol]),
                                                "bias": bias(gs["pred_" + method], gs[obscol])})
                    for method in eligible:
                        all_rows.append({"protocol": exp, "variable": target, "fold": rec["fold"],
                                         "station": station, "method": method, "n": len(grp),
                                         "distance_km": dist,
                                         "rmse": rmse(grp["pred_" + method], grp[obscol])})
                    if exp not in ("loso", "spatial_block"):
                        continue
                    # Annual extremes: year with >=90% paired finite days only.
                    for year, yy in grp.groupby("year"):
                        days = 366 if pd.Timestamp(f"{year}-12-31").is_leap_year else 365
                        if len(yy) < np.ceil(days * .95):
                            continue
                        obs = yy[obscol].to_numpy()
                        if target == "Tmax":
                            fn = lambda z: float(np.max(z)); index = "TXx"
                        elif target == "Tmin":
                            fn = lambda z: float(np.min(z)); index = "TNn"
                        else:
                            fn = lambda z: float(np.max(z)); index = "Rx1day"
                        observed = fn(obs)
                        for method in eligible:
                            p = yy["pred_" + method].to_numpy()
                            v = fn(p)
                            annual_rows.append({"protocol": exp, "variable": target, "fold": rec["fold"],
                                                "station": station, "year": year, "index": index,
                                                "method": method, "n": len(yy), "error_abs": abs(v - observed),
                                                "error_signed": v - observed})
                        if target == "Prcp":
                            observed = float(np.sum(obs >= 10))
                            for method in eligible:
                                v = float(np.sum(yy["pred_" + method].to_numpy() >= 10))
                                annual_rows.append({"protocol": exp, "variable": target, "fold": rec["fold"],
                                                    "station": station, "year": year, "index": "R10mm",
                                                    "method": method, "n": len(yy), "error_abs": abs(v - observed),
                                                    "error_signed": v - observed})
            print(exp, target, "folds", len(files), "stations", len(station_folds[exp]), flush=True)

    sea = pd.DataFrame(season_rows)
    daily = pd.DataFrame(all_rows)
    annual = pd.DataFrame(annual_rows)
    # Freeze independent station-period observations, not daily pseudo-replicates.
    p = sea.pivot_table(index=["protocol", "variable", "station", "season", "distance_km"],
                        columns="method", values="rmse", aggfunc="mean").reset_index()
    for method in ["MONTHLY", "ET_LOCAL", "ET_TERRAIN", "FALLBACK20", "EPC1", "EPC10", "EPC20", "EPC50"]:
        if method in p:
            p["benefit_" + method] = p["RAW"] - p[method]
    stats = []
    for (protocol, variable, season), g in p.groupby(["protocol", "variable", "season"]):
        for method in ["MONTHLY", "ET_LOCAL", "ET_TERRAIN", "FALLBACK20", "EPC1", "EPC10", "EPC20", "EPC50"]:
            if method not in g:
                continue
            t = g.dropna(subset=["RAW", method])
            if len(t) < 5:
                continue
            d = (t.RAW - t[method]).to_numpy()
            ci = bootstrap_ci(d)
            try: pval = float(wilcoxon(d).pvalue) if np.any(d) else 1.0
            except ValueError: pval = np.nan
            stats.append({"protocol": protocol, "variable": variable, "season": season,
                          "method": method, "stations": len(t), "mean_raw_rmse": t.RAW.mean(),
                          "mean_model_rmse": t[method].mean(), "mean_benefit": d.mean(),
                          "benefit_percent": 100 * d.mean() / t.RAW.mean(),
                          "stations_improved": int((d > 0).sum()),
                          "station_bootstrap_lo": ci[0], "station_bootstrap_hi": ci[1],
                          "paired_wilcoxon_p_exploratory": pval})
    ss = pd.DataFrame(stats)
    ss.to_csv(OUT / "seasonal_station_benefits.csv", index=False)
    # Use FDR for the family of seasonal comparisons within each protocol and variable.
    def bh_qvals(arr):
        arr = np.asarray(arr)
        order = np.argsort(arr)
        ranked = arr[order] * len(arr) / np.arange(1, len(arr) + 1)
        ranked = np.minimum.accumulate(ranked[::-1])[::-1]
        out = np.empty_like(ranked)
        out[order] = np.minimum(ranked, 1)
        return out
    ss["wilcoxon_q_by_protocol_target"] = np.nan
    for (_, _), ids in ss.groupby(["protocol", "variable"]).groups.items():
        q = ss.loc[ids, "paired_wilcoxon_p_exploratory"]
        valid = q.notna()
        if valid.any():
            ss.loc[q[valid].index, "wilcoxon_q_by_protocol_target"] = bh_qvals(q[valid].to_numpy())
    ss.to_csv(OUT / "seasonal_station_benefits.csv", index=False)

    # Distance association, one station per protocol (not daily rows).
    dlong = daily.pivot_table(index=["protocol", "variable", "station", "distance_km"],
                              columns="method", values="rmse").reset_index()
    dlong["et_benefit"] = dlong.RAW - dlong.ET_LOCAL
    daily_agg=[]
    for (prot, var), group in dlong.groupby(["protocol", "variable"]):
        for method in group.columns:
            if method in ("protocol", "variable", "station", "distance_km", "et_benefit", "RAW"):
                continue
            zz = group.dropna(subset=["RAW", method])
            if len(zz) == 0:
                continue
            improvements = (zz.RAW-zz[method]).to_numpy()
            lo, hi = bootstrap_ci(improvements)
            daily_agg.append(dict(protocol=prot, variable=var, method=method,
                                  stations=len(zz), mean_station_daily_raw_rmse=zz.RAW.mean(),
                                  mean_station_daily_corrected_rmse=zz[method].mean(),
                                  mean_daily_rmse_gain=improvements.mean(),
                                  stations_better=int((improvements>0).sum()),
                                  station_bootstrap_gain_lo=lo, station_bootstrap_gain_hi=hi))
    pd.DataFrame(daily_agg).to_csv(OUT / "mean_station_daily_rmse.csv",index=False)
    distance_rows = []
    for (protocol, target), z in dlong.groupby(["protocol", "variable"]):
        rho, pv = spearmanr(z.distance_km, z.et_benefit)
        distance_rows.append(dict(protocol=protocol, variable=target, stations=len(z),
                                  min_distance_km=z.distance_km.min(),
                                  median_distance_km=z.distance_km.median(),
                                  max_distance_km=z.distance_km.max(),
                                  spearman_distance_vs_benefit=rho,
                                  spearman_p_exploratory=pv))
    pd.DataFrame(distance_rows).to_csv(OUT / "distance_transfer_associations.csv", index=False)
    distance_bin = []
    for (protocol, variable), z in dlong.groupby(["protocol", "variable"]):
        z = z.copy()
        z["bin"] = pd.qcut(z.distance_km, q=4, labels=["Q1_near", "Q2", "Q3", "Q4_far"], duplicates="drop")
        for label, g in z.groupby("bin", observed=True):
            distance_bin.append(dict(protocol=protocol, variable=variable, donor_distance_quantile=str(label),
                                     stations=len(g), distance_median_km=g.distance_km.median(),
                                     raw_rmse=g.RAW.mean(), et_local_rmse=g.ET_LOCAL.mean(),
                                     mean_benefit=g.et_benefit.mean()))
    pd.DataFrame(distance_bin).to_csv(OUT / "distance_quartile_risk.csv", index=False)

    # Annual extreme ranks: station-level mean annual absolute error, not pooled daily.
    per_station = annual.groupby(["protocol", "variable", "index", "station", "method"]).error_abs.mean().reset_index()
    extreme_table = per_station.groupby(["protocol", "variable", "index", "method"]).agg(
        stations=("station", "nunique"), mean_station_annual_mae=("error_abs", "mean")
    ).reset_index()
    extreme_table.to_csv(OUT / "annual_extreme_station_mae.csv", index=False)
    annual_rmse_station = annual.groupby(["protocol", "variable", "index", "station", "method"]).error_signed.apply(
        lambda v: float(np.sqrt(np.mean(v.to_numpy() ** 2)))).reset_index(name="annual_rmse")
    annual_rmse_summary = annual_rmse_station.groupby(["protocol", "variable", "index", "method"]).agg(
        stations=("station", "nunique"), mean_station_annual_rmse=("annual_rmse", "mean")
    ).reset_index()
    annual_rmse_summary.to_csv(OUT / "annual_extreme_station_rmse.csv", index=False)
    joint = per_station.pivot_table(index=["protocol", "variable", "index", "station"],
                                   columns="method", values="error_abs").reset_index()
    daily_station = daily.pivot_table(index=["protocol", "variable", "station"],
                                     columns="method", values="rmse").reset_index()
    decisions = []
    for _, x in joint.iterrows():
        dr = daily_station[(daily_station.protocol == x["protocol"]) &
                           (daily_station.variable == x["variable"]) &
                           (daily_station.station == x["station"])]
        if len(dr) != 1:
            continue
        d = dr.iloc[0]
        for method in ["ET_LOCAL", "ET_TERRAIN", "FALLBACK20", "EPC1", "EPC10", "EPC20", "EPC50"]:
            if method not in x or pd.isna(x[method]):
                continue
            decisions.append({"protocol": x["protocol"], "variable": x["variable"],
                              "index": x["index"], "station": x["station"], "method": method,
                              "daily_improved": bool(d[method] < d.RAW),
                              "extreme_worsened": bool(x[method] > x.RAW),
                              "extreme_improved": bool(x[method] < x.RAW),
                              "daily_gain": d.RAW - d[method],
                              "extreme_gain": x.RAW - x[method]})
    contrasts = pd.DataFrame(decisions)
    contrast_summary = contrasts.groupby(["protocol", "variable", "index", "method"]).agg(
        stations=("station", "nunique"), daily_better_extreme_worse=("daily_improved", lambda col: 0),
        mean_daily_gain=("daily_gain", "mean"), mean_extreme_gain=("extreme_gain", "mean")
    ).reset_index()
    discordance = contrasts.groupby(["protocol", "variable", "index", "method"]).apply(
        lambda z: int((z.daily_improved & z.extreme_worsened).sum()), include_groups=False)
    contrast_summary["daily_better_extreme_worse"] = contrast_summary.set_index(
        ["protocol", "variable", "index", "method"]).index.map(discordance)
    contrast_summary.to_csv(OUT / "daily_extreme_rank_discordance.csv", index=False)

    # One cross-outcome comparison figure uses the same station-weighted RMSE
    # definition for daily and annual quantities.
    fig, ax = plt.subplots(1, 2, figsize=(10.8, 4.1))
    for k, protocol in enumerate(["loso", "spatial_block"]):
        dd = daily[(daily.protocol == protocol) & (daily.variable == "Prcp")].groupby("method").rmse.mean()
        ex = annual_rmse_summary[(annual_rmse_summary.protocol == protocol) &
                                 (annual_rmse_summary.variable == "Prcp") &
                                 (annual_rmse_summary["index"] == "Rx1day")].set_index("method")
        for method, color in [("RAW", "#666666"), ("ET_LOCAL", "#146d80"),
                              ("FALLBACK20", "#b76d44"), ("EPC10", "#43855b")]:
            xx, yy = dd.get(method), ex.mean_station_annual_rmse.get(method)
            ax[k].scatter(xx, yy, s=65, color=color, label=method.replace("_", " "))
            ax[k].annotate(method.replace("_", " "), (xx, yy), xytext=(5, 6),
                           textcoords="offset points", fontsize=8)
        ax[k].set_title("Station withholding" if k == 0 else "Regional-block withholding")
        ax[k].set_xlabel("Daily precipitation RMSE (mm/day)")
        if k == 0: ax[k].set_ylabel("Mean station annual Rx1day RMSE (mm)")
        ax[k].spines[["top", "right"]].set_visible(False)
        ax[k].grid(alpha=.15)
    fig.suptitle("A constrained choice of daily skill versus annual-extreme fidelity")
    fig.tight_layout()
    fig.savefig(OUT / "Fig14_constraint_pareto.png", dpi=260, bbox_inches="tight")
    fig.savefig(OUT / "Fig14_constraint_pareto.pdf", bbox_inches="tight")
    plt.close(fig)

    # A-priori rain extreme protection: preserve ERA5-Land whenever raw daily rain >=20mm.
    # 20mm is the recognized R20mm threshold; this is an exploratory, untuned stress test.
    # Study endpoints are NOT a prospective recalibration or causal safety guarantee.
    safe = ss[(ss.variable == "Prcp") & (ss.method.isin(["ET_LOCAL", "EPC10"]))]
    print("Seasonal:", ss.shape, "Annual:", extreme_table.shape, "Discordance:", contrast_summary.shape)
    print("Rain fallback seasons:\n", safe.to_string(index=False, float_format=lambda x: f"{x:.3f}"))

    # Figure 1: robust annual-season interaction under independent spatial geometries.
    fig, axes = plt.subplots(3, 2, figsize=(10.8, 10.5), sharex=True)
    for i, target in enumerate(TARGET):
        for j, protocol in enumerate(["loso", "spatial_block"]):
            ax = axes[i, j]
            z = ss[(ss.variable == target) & (ss.protocol == protocol) &
                   (ss.method == "ET_LOCAL")].set_index("season").reindex(SEASONS)
            x = np.arange(4)
            ax.axhline(0, color="#777777", linewidth=.9)
            ax.bar(x, z.mean_benefit, color=["#15616d" if v >= 0 else "#c04e34" for v in z.mean_benefit])
            ax.errorbar(x, z.mean_benefit, yerr=np.vstack([
                z.mean_benefit - z.station_bootstrap_lo,
                z.station_bootstrap_hi - z.mean_benefit]), fmt="none", color="#222222", capsize=3)
            ax.set_xticks(x, SEASONS)
            ax.set_title(f"{target} — {'LOSO' if j == 0 else 'Spatial blocks'}")
            ax.set_ylabel("RMSE reduction vs raw\n(°C)" if target != "Prcp" else "RMSE reduction vs raw\n(mm day⁻¹)")
            ax.spines[["top", "right"]].set_visible(False)
    fig.suptitle("Season-dependent transfer gains: equally weighted stations", fontsize=14)
    fig.text(.5, .018, "Bars: mean raw minus ET-local RMSE; whiskers: station-resampling 95% intervals", ha="center", fontsize=9)
    fig.tight_layout(rect=[0, .032, 1, .965])
    fig.savefig(OUT / "Fig11_seasonal_transfer.png", dpi=260, bbox_inches="tight")
    fig.savefig(OUT / "Fig11_seasonal_transfer.pdf", bbox_inches="tight")
    plt.close(fig)

    # Figure 2: independent spatial-distance association; avoid drawing an unearned regression trend.
    fig, ax = plt.subplots(1, 3, figsize=(11.0, 3.5))
    for k, target in enumerate(TARGET):
        z = dlong[(dlong.protocol == "loso") & (dlong.variable == target)]
        ax[k].scatter(z.distance_km, z.et_benefit, s=33, c="#176e8b", alpha=.85)
        ax[k].axhline(0, color="#8a5454", linestyle="--", linewidth=1)
        rho, _ = spearmanr(z.distance_km, z.et_benefit)
        ax[k].text(.05, .94, f"Spearman ρ = {rho:.2f}", transform=ax[k].transAxes, va="top", fontsize=9)
        ax[k].set_title(target)
        ax[k].set_xlabel("Nearest donor station (km)")
        if k == 0: ax[k].set_ylabel("RMSE reduction vs raw")
        ax[k].spines[["top", "right"]].set_visible(False)
    fig.suptitle("Donor distance alone does not certify transferable correction", fontsize=12)
    fig.tight_layout()
    fig.savefig(OUT / "Fig12_distance_risk.png", dpi=260, bbox_inches="tight")
    fig.savefig(OUT / "Fig12_distance_risk.pdf", bbox_inches="tight")
    plt.close(fig)

    # Figure 3: quantitative decision trade-off for station-wise rain indices.
    z = contrast_summary[(contrast_summary.protocol == "loso") &
                         (contrast_summary.variable == "Prcp") &
                         (contrast_summary.method.isin(["ET_LOCAL", "FALLBACK20", "EPC10"]))]
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    xx = np.arange(2)
    for k, method in enumerate(["ET_LOCAL", "FALLBACK20", "EPC10"]):
        zz = z[z.method == method].set_index("index").reindex(["Rx1day", "R10mm"])
        xbars=xx + (k - 1) * .28
        ax.bar(xbars, zz.daily_better_extreme_worse, width=.26,
               label=["Extra Trees", "Raw ≥20 mm fallback", "Event-preserving EPC10"][k],
               color=["#186d79", "#ba693f", "#59815d"][k])
        if method == "EPC10":
            for pos in xbars: ax.text(pos, .55, "0", ha="center", fontsize=9, color="#38613d")
    ax.set_xticks(xx, ["Rx1day", "R10mm"])
    ax.set_ylim(0, 34)
    ax.set_ylabel("Stations: daily RMSE better,\nannual index MAE worse")
    ax.set_title("Daily-accuracy / extreme-utility reversals (34 LOSO stations)")
    ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(.5, -.16), ncol=3, fontsize=8)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout(rect=[0, .05, 1, 1])
    fig.savefig(OUT / "Fig13_utility_discordance.png", dpi=260, bbox_inches="tight")
    fig.savefig(OUT / "Fig13_utility_discordance.pdf", bbox_inches="tight")
    plt.close(fig)

    # Figure 5: predeclared family of threshold constraints and event accuracy.
    fig, ax = plt.subplots(1, 2, figsize=(10.5, 4.0))
    for k, protocol in enumerate(["loso", "spatial_block"]):
        dd = daily[(daily.protocol == protocol) & (daily.variable == "Prcp")].groupby("method").rmse.mean()
        ar = annual_rmse_summary[(annual_rmse_summary.protocol == protocol) &
                                 (annual_rmse_summary.variable == "Prcp") &
                                 (annual_rmse_summary["index"] == "R10mm")].set_index("method")
        for method, color in [("RAW", "#444444"), ("ET_LOCAL", "#146d80"),
                              ("EPC1", "#7b9a75"), ("EPC10", "#387f51"),
                              ("EPC20", "#b67537"), ("EPC50", "#b24736")]:
            xx = dd.get(method)
            yy = ar.mean_station_annual_rmse.get(method)
            ax[k].scatter(xx, yy, s=62, color=color)
            offset = (5, 15) if method == "RAW" else ((5, -15) if method == "EPC1" else (4, 5))
            ax[k].annotate(method.replace("_", " "), (xx, yy), xytext=offset,
                           textcoords="offset points", fontsize=8)
        ax[k].set_xlabel("Daily rainfall RMSE (mm/day)")
        if k == 0: ax[k].set_ylabel("Annual R10mm RMSE (days)")
        ax[k].set_title("LOSO" if k == 0 else "Regional blocks")
        ax[k].spines[["top", "right"]].set_visible(False)
        ax[k].grid(alpha=.15)
    fig.suptitle("Predefined event-preserving thresholds select different utility frontiers")
    fig.tight_layout()
    fig.savefig(OUT / "Fig15_threshold_frontier.png", dpi=260, bbox_inches="tight")
    fig.savefig(OUT / "Fig15_threshold_frontier.pdf", bbox_inches="tight")
    plt.close(fig)

    public = {"source_predictions": "research_rebuild/results/jobs (private row-linked arrays)",
              "source_observations": "Private processed BMD-derived observations; not redistributed",
              "frozen_methods": sorted(set(sea.method)),
              "validation": "Each outer-test station disjoint from its fitting donors; no refitting or selection on held-out targets",
              "station_count": {k: len(v) for k, v in station_folds.items()},
              "saved_job_count": len(seen),
              "years": "2000–2023 (space–time test 2016–2023)",
              "station_weighting": "equal per station; station bootstrap (3000 samples)",
              "annual_validity": ">=95% of calendar days with valid paired predictions per station-year",
              "season_calendar": {"DJF": "Dec-Feb", "MAM": "Mar-May", "JJAS": "Jun-Sep", "ON": "Oct-Nov"},
              "experimental_fallback": "A-priori threshold 20 mm ERA5-Land daily precipitation; untrained, descriptive, no safety guarantee",
              "event_preserving_rule": "EPC_T: use RAW for RAW>=T, else min(max(ET_LOCAL,0), nextafter(T,0)); exactly preserves RAW occurrence for every threshold>=T, not observed-event accuracy",
              "a_priori_thresholds_mm": [1, 10, 20, 50],
              "privacy": "Exports aggregate station-level statistics without row IDs, station identifiers, original observations, coordinates, or predictions"}
    (OUT / "run_provenance.json").write_text(json.dumps(public, indent=2, ensure_ascii=False))
    # Internal consistency audit: sample validation against original raw arrays is mandatory.
    assert len(seen) == 102 + 12 * 2, len(seen)
    assert len(station_folds["loso"]) == 34
    print("PASS: frozen RAW match, disjoint train/test, unique IDs, expected saved jobs", flush=True)


if __name__ == "__main__":
    main()
