#!/usr/bin/env python3
"""Turn completed, privacy-safe model runs into auditable tables and figures."""
import argparse
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

DESIGNS = ["loso", "spatial_block", "spatiotemporal", "temporal", "buffer100"]
LABELS = {"loso":"LOSO", "spatial_block":"Spatial blocks", "spatiotemporal":"Space + time", "temporal":"Future years", "buffer100":"100-km buffer"}
TARGETS = ["Tmax", "Tmin", "Prcp"]


def digest(path):
    hash_obj = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            hash_obj.update(block)
    return hash_obj.hexdigest()


def effects(station, out, rng):
    groups = station[station.experiment.isin(DESIGNS)]
    rows=[]
    for (experiment, design, target), frame in groups.groupby(["experiment", "design", "target"]):
        wide = frame.pivot(index="station_name", columns="method", values="rmse")
        for candidate, baseline in (("ET_LOCAL", "RAW"), ("ET_TERRAIN", "ET_LOCAL"),
                                    ("HGB_LOCAL", "ET_LOCAL"), ("MONTHLY", "RAW")):
            if candidate not in wide or baseline not in wide:
                continue
            delta = (wide[baseline] - wide[candidate]).dropna()
            if len(delta) == 0:
                continue
            # Paired station bootstrap describes uncertainty only; training splits overlap.
            samples = rng.choice(delta.to_numpy(), size=(3000, len(delta)), replace=True).mean(axis=1)
            rows.append({"experiment":experiment, "design":design, "target":target,
                         "candidate":candidate, "baseline":baseline,
                         "n_stations":len(delta), "mean_station_rmse_gain":delta.mean(),
                         "gain_percent_of_baseline":100*delta.mean()/wide.loc[delta.index,baseline].mean(),
                         "median_station_gain":delta.median(),
                         "stations_improved":int((delta>0).sum()),
                         "stations_worsened":int((delta<0).sum()),
                         "station_bootstrap_low_exploratory":np.quantile(samples,.025),
                         "station_bootstrap_high_exploratory":np.quantile(samples,.975)})
    effects_frame = pd.DataFrame(rows)
    effects_frame.to_csv(out/"paired_effects.csv", index=False)
    return effects_frame


def historical_comparison(station, historical, out):
    if not historical.is_file():
        return {"status":"prior author export not available"}
    past = pd.read_csv(historical)
    past = past.loc[past.method.isin(["RAW", "MONTHLY", "ET_LOCAL", "ET_TERRAIN"]) & past.target.isin(TARGETS)]
    now = station.loc[station.experiment.eq("loso")]
    joined = past[["target","method","station_name","rmse"]].merge(
        now[["target","method","station_name","rmse"]],
        on=["target","method","station_name"], suffixes=("_prior","_recomputed"), validate="one_to_one")
    joined["absolute_difference"] = (joined.rmse_prior-joined.rmse_recomputed).abs()
    joined.to_csv(out/"prior_vs_recomputed_loso.csv", index=False)
    return {"status":"compared", "matched_station_method_target_rows":len(joined),
            "max_absolute_rmse_difference":float(joined.absolute_difference.max()),
            "median_absolute_rmse_difference":float(joined.absolute_difference.median()),
            "within_1e_minus_8":int((joined.absolute_difference<1e-8).sum()),
            "within_1e_minus_4":int((joined.absolute_difference<1e-4).sum()),
            "note":"Earlier file is an author-provided result export, not an independent raw-data benchmark."}


def run_verification(results, station, summary, comparison):
    jobs = sorted((results/"jobs").glob("*.json"))
    errors=[]; counts={}; protected_keys=("observed", "obs_tmax", "obs_tmin", "obs_prcp", "y_true")
    for path in jobs:
        record=json.loads(path.read_text())
        key=(record["experiment"], record["target"])
        counts[str(key)]=counts.get(str(key),0)+1
        datafile=path.with_suffix(".csv")
        npzfile=path.with_suffix(".npz")
        if not datafile.exists() or not npzfile.exists():
            errors.append(str(path)+": missing result")
            continue
        if digest(datafile)!=record["result_sha256"] or digest(npzfile)!=record["predictions_sha256"]:
            errors.append(str(path)+": hash mismatch")
        with np.load(npzfile) as arrays:
            if any(k in protected_keys for k in arrays.files):
                errors.append(str(path)+": observed values found in prediction archive")
            if len(arrays["row_id"])!=record["n_test"]:
                errors.append(str(path)+": test-count mismatch")
        if record["experiment"]!="temporal" and set(record["train_station_names"]) & set(record["test_station_names"]):
            errors.append(str(path)+": station split leakage")
        if {"Kutubdia", "Sandwip"} & set(record["train_station_names"]):
            errors.append(str(path)+": filled-island training leakage")
    if comparison.get("status")=="compared":
        if comparison.get("matched_station_method_target_rows")!=408:
            errors.append("Incomplete prior author-export LOSO comparison; expected 408 matched records")
        if comparison.get("max_absolute_rmse_difference",float("inf"))>1e-8:
            errors.append("Recomputed LOSO model scores differ from previously reported author results")
    all_data = {
        "status":"PASS" if not errors else "FAIL", "n_executed_jobs":len(jobs),
        "n_station_method_metrics":len(station), "summary_rows":len(summary),
        "jobs_by_experiment_target":counts, "verification_errors":errors,
        "comparison_with_prior_export":comparison,
        "interpretation_limit":"Hash and split checks validate integrity, not independence of raw data or scientific truth.",
    }
    return all_data


def plot_designs(summary, out):
    ss=summary.loc[summary.experiment.isin(DESIGNS)]
    fig, axes=plt.subplots(1,3,figsize=(14.2,4.8),sharey=True)
    for ax,target in zip(axes,TARGETS):
        part=ss[ss.target.eq(target)].pivot_table(index="experiment",columns="method",values="mean_station_rmse",aggfunc="mean")
        part=part.reindex(DESIGNS)
        for method,marker,col in (("ET_LOCAL","o","#126782"),("ET_TERRAIN","s","#E18635"),("HGB_LOCAL","^","#65966B")):
            gain=(part["RAW"]-part[method])/part["RAW"]*100
            ax.plot(gain.to_numpy(),np.arange(len(gain)),marker=marker,linestyle="None",color=col,label=method,markersize=7)
        ax.axvline(0,color="0.45",linewidth=.8)
        ax.set_title(target,fontsize=12,fontweight="bold")
        ax.set_yticks(np.arange(len(DESIGNS)),[LABELS[d] for d in DESIGNS])
        ax.grid(axis="x",alpha=.2)
        ax.set_xlabel("RMSE reduction against raw ERA5-Land (%)")
    handles,labels=axes[0].get_legend_handles_labels()
    fig.legend(handles,labels,loc="lower center",bbox_to_anchor=(.5,-.018),ncol=3,fontsize=9)
    fig.suptitle("Transfer performance changes with validation design",fontsize=14,fontweight="bold")
    fig.tight_layout(rect=[0,.05,1,.96])
    fig.savefig(out/"F01_validation_skill.png",dpi=200,bbox_inches="tight")
    fig.savefig(out/"F01_validation_skill.pdf",bbox_inches="tight")
    plt.close(fig)


def plot_terrain(effects_table, out):
    part = effects_table[(effects_table.candidate=="ET_TERRAIN") & (effects_table.baseline=="ET_LOCAL")]
    fig,axes=plt.subplots(1,3,figsize=(14.2,4.5),sharey=True)
    for ax,target in zip(axes,TARGETS):
        z=part.loc[part.target.eq(target)].set_index("experiment").reindex(DESIGNS)
        y=np.arange(len(z))
        x=z.gain_percent_of_baseline.to_numpy()
        ax.barh(y,x,color=["#167D86" if a>=0 else "#C85B45" for a in x],height=.56)
        ax.axvline(0,color="0.3",linewidth=.8)
        ax.set_title(target,fontweight="bold")
        ax.set_yticks(y,[LABELS[d] for d in DESIGNS]);ax.invert_yaxis()
        ax.set_xlabel("Benefit from terrain over local ET (%)")
        ax.grid(axis="x",alpha=.16)
    fig.suptitle("Terrain feature additions are design- and target-dependent",fontweight="bold")
    fig.tight_layout()
    fig.savefig(out/"F02_terrain_increment.png",dpi=200,bbox_inches="tight")
    fig.savefig(out/"F02_terrain_increment.pdf",bbox_inches="tight")
    plt.close(fig)


def plot_rainfall(events, out):
    fig,axes=plt.subplots(1,2,figsize=(10.6,4.2),sharey=True)
    for ax, experiment in zip(axes,["loso","buffer100"]):
        for meth,marker,c in (("RAW","o","#777777"),("MONTHLY","s","#AC8026"),("ET_LOCAL","^","#126782"),
                              ("ET_TERRAIN","D","#E18635")):
            tmp=events.loc[events.experiment.eq(experiment)&events.method.eq(meth)].sort_values("threshold_mm")
            if tmp.empty:continue
            ax.plot(tmp.threshold_mm,tmp.csi,color=c,marker=marker,label=meth,linewidth=1.6)
        ax.set_title(LABELS[experiment],fontweight="bold")
        ax.set_xlabel("Observed event threshold (mm/day)")
        ax.grid(alpha=.15)
    axes[0].set_ylabel("Critical Success Index (CSI)")
    axes[1].legend(fontsize=8)
    fig.suptitle("Rainfall-event detection: correcting RMSE does not guarantee event skill",fontweight="bold")
    fig.tight_layout()
    fig.savefig(out/"F03_precipitation_events.png",dpi=200,bbox_inches="tight")
    fig.savefig(out/"F03_precipitation_events.pdf",bbox_inches="tight")
    plt.close(fig)


def latex_validation_table(summary, out):
    """Compact supplementary table with fully defined aggregation and units."""
    lines = [r"\begin{table*}[t]",r"\centering",r"\small",
             r"\caption{Independent held-out reruns of ERA5-Land daily bias correction across transfer designs. Entries are arithmetic means of station-specific RMSE, not pooled sample errors; temperature in $^\circ$C and precipitation in mm day$^{-1}$. All methods are trained using disjoint held-out groups or years, as appropriate. A dash means the method was not rerun in that design.}",
             r"\label{tab:independent_transfer_reruns}",r"\begin{tabular}{llrrrrrr}",r"\hline",
             r"Design & Variable & Raw & Monthly & ET local & ET terrain & HGB local & HGB terrain \\",r"\hline"]
    for exp in DESIGNS:
        for target in TARGETS:
            frame=summary[(summary.experiment==exp)&(summary.target==target)]
            if frame.empty:continue
            by=frame.set_index("method").mean_station_rmse
            formatted=[f"{by[m]:.3f}" if m in by else "--" for m in ["RAW","MONTHLY","ET_LOCAL","ET_TERRAIN","HGB_LOCAL","HGB_TERRAIN"]]
            lines.append(LABELS[exp]+" & "+target+" & "+" & ".join(formatted)+r" \\")
    lines.extend([r"\hline",r"\end{tabular}",r"\end{table*}"])
    (out/"supplementary_validation_table.tex").write_text("\n".join(lines)+"\n")


def plot_partition_sensitivity(summary, out, reports):
    part=summary[summary.experiment.eq("partition")]
    if part.empty:return
    wide=part.pivot(index=["design","target"],columns="method",values="mean_station_rmse").reset_index()
    wide["et_local_gain_pct"]=100*(wide.RAW-wide.ET_LOCAL)/wide.RAW
    wide["terrain_increment_pct"]=100*(wide.ET_LOCAL-wide.ET_TERRAIN)/wide.ET_LOCAL
    wide.to_csv(reports/"alternative_partition_sensitivity.csv",index=False)
    designs=sorted(wide.design.unique())
    fig,axes=plt.subplots(1,2,figsize=(11.6,4.9),sharey=True)
    for ax,target,color in zip(axes,["Tmin","Prcp"],["#127A82","#DA7A38"]):
        s=wide[wide.target.eq(target)].set_index("design").reindex(designs)
        vals=s.terrain_increment_pct.to_numpy()
        ax.barh(np.arange(len(designs)),vals,color=[color if v>=0 else "#BA4E4E" for v in vals])
        ax.axvline(0,color="0.4",linewidth=.8)
        ax.set_title(target,fontweight="bold");ax.set_xlabel("Terrain increment relative to ET local (%)")
        ax.set_yticks(np.arange(len(designs)),designs)
        ax.grid(axis="x",alpha=.15)
    axes[0].invert_yaxis()
    fig.suptitle("Sensitivity to alternate geographically grouped partitions",fontweight="bold")
    fig.tight_layout()
    fig.savefig(out/"F05_alternative_partitions.png",dpi=200,bbox_inches="tight")
    fig.savefig(out/"F05_alternative_partitions.pdf",bbox_inches="tight")
    plt.close(fig)


def make_report(args):
    results=Path(args.results).resolve()
    reports=Path(args.reports).resolve();reports.mkdir(parents=True,exist_ok=True)
    figures=Path(args.figures).resolve();figures.mkdir(parents=True,exist_ok=True)
    station=pd.read_csv(results/"station_metrics.csv")
    summary=pd.read_csv(results/"summary.csv")
    effects_table=effects(station,reports,np.random.default_rng(42))
    latex_validation_table(summary,reports)
    comp=historical_comparison(station,Path(args.prior),reports)
    verify=run_verification(results,station,summary,comp)
    (reports/"verification.json").write_text(json.dumps(verify,indent=2))
    if verify["status"]!="PASS":raise AssertionError("Verification failed: "+str(verify["verification_errors"][:3]))
    present=set(summary.experiment)
    if set(DESIGNS).issubset(present):
        plot_designs(summary,figures)
        plot_terrain(effects_table,figures)
    if "partition" in present:
        plot_partition_sensitivity(summary,figures,reports)
    event=results/"rainfall_event_summary.csv"
    if event.exists():
        events=pd.read_csv(event)
        if {"loso","buffer100"}.issubset(set(events.experiment)):
            plot_rainfall(events,figures)
    lines=["# Independently recomputed validation evidence", "", "The source observations are withheld from this archive; all results below were generated locally from the supplied seven-input dataset bundle. Numbers are mean station RMSE (same-station averaging, not pooled daily RMSE).", "", "| Design | Variable | Raw | Monthly | ET local | ET terrain | HGB local | HGB terrain |", "|---|---|---:|---:|---:|---:|---:|---:|"]
    for design in DESIGNS:
        for target in TARGETS:
            d=summary.loc[summary.experiment.eq(design)&summary.target.eq(target)]
            if d.empty:continue
            methods=d.set_index("method").mean_station_rmse
            x=[f"{methods.get(m,np.nan):.3f}" if pd.notna(methods.get(m,np.nan)) else "—" for m in ["RAW","MONTHLY","ET_LOCAL","ET_TERRAIN","HGB_LOCAL","HGB_TERRAIN"]]
            lines.append(f"| {LABELS[design]} | {target} | "+" | ".join(x)+" |")
    if "partition" in present:
        lines.extend(["", "## Alternative geographic partition sensitivity", "",
                      "The partition designs below are sensitivity checks of the same network, not independent external datasets.", "",
                      "| Partition | Target | Raw RMSE | ET local RMSE | ET terrain RMSE |", "|---|---|---:|---:|---:|"])
        for (design,target),grp in summary.loc[summary.experiment.eq("partition")].groupby(["design","target"]):
            values=grp.set_index("method").mean_station_rmse
            lines.append(f"| {design} | {target} | {values['RAW']:.3f} | {values['ET_LOCAL']:.3f} | {values['ET_TERRAIN']:.3f} |")
    lines.extend(["", "## Verification", "", f"- Completed, checksum-verified model/target/fold jobs: **{verify['n_executed_jobs']}**.", f"- Prior author-export LOSO comparison: **{comp.get('status')}**; maximal absolute station RMSE delta **{comp.get('max_absolute_rmse_difference',float('nan')):.8f}**.", "- Spatial holdouts disjoint at station level; temporal folds disjoint in time; native-only training excludes two ERA island locations with filled reanalysis.", "- Predicted values are saved without observed BMD target values. Recompute scores by running with authorized original BMD data.", "", "## Crucial scientific caveats", "", "1. Dataset coordinates are labelled draft and have not been independently verified against station records or extraction grid points.", "2. Historical comparison tests computational reproducibility against the author export, not independent field-data provenance.", "3. All corrected models use the same station network and correlated samples; naive station-bootstrap intervals are exploratory and not formal spatial-inference guarantees.", "4. A held-out station is out of sample for training but this is not a wholly new independent country or observing network.", "5. Report validation-design effects with unmodified raw baselines, including failed terrain gains and rainfall-event trade-offs.", "6. Physical observational data redistribution rights need separate confirmation. The prediction-only archive avoids including BMD daily observations."])
    (reports/"SCIENTIFIC_RESULTS.md").write_text("\n".join(lines)+"\n")
    print(json.dumps(verify,indent=2))


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results",required=True)
    parser.add_argument("--reports",required=True)
    parser.add_argument("--figures",required=True)
    parser.add_argument("--prior",default="/nonexistent/author_loso_station_metrics.csv")
    make_report(parser.parse_args())
