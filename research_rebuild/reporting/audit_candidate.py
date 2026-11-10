#!/usr/bin/env python3
"""Audit nested gate selection and summarize TARC candidate without cherry-picking."""
import argparse
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def checksum(p):
    h=hashlib.sha256()
    with p.open("rb") as src:
        for b in iter(lambda:src.read(1<<20),b""):
            h.update(b)
    return h.hexdigest()


def main(args):
    source=Path(args.candidate).resolve();report=Path(args.output).resolve();report.mkdir(parents=True,exist_ok=True)
    figs=Path(args.figures).resolve();figs.mkdir(parents=True,exist_ok=True)
    frames=[];gates=[];errors=[]
    for meta_path in sorted(source.glob("*.json")):
        if meta_path.name=="manifest.json":continue
        d=json.loads(meta_path.read_text());stem=meta_path.stem
        scores_path=source/f"{stem}.csv";pred_path=source/f"{stem}.npz"
        if not scores_path.exists() or not pred_path.exists():
            errors.append(stem+": missing files");continue
        if checksum(scores_path)!=d["metrics_sha256"] or checksum(pred_path)!=d["predictions_sha256"]:
            errors.append(stem+": checksum mismatch")
        outer=set(d["test_station_names"])
        if outer&set(d["train_station_names"]):errors.append(stem+": outer station leakage")
        for fold in d["inner_fold_station_separation"]:
            inner_train=set(fold["train_stations"]);inner_val=set(fold["validation_stations"])
            if inner_train&inner_val or outer&(inner_train|inner_val):
                errors.append(stem+": nested station leakage")
        with np.load(pred_path) as a:
            if any(key.startswith("obs_") or key in {"observed","y_true"} for key in a.files):
                errors.append(stem+": observed target in NPZ")
        frames.append(pd.read_csv(scores_path))
        gates.append({"experiment":d["experiment"],"fold":d["fold"],
                      "amplitude":d["gate"]["amplitude"],
                      "bandwidth":d["gate"]["bandwidth"],
                      "selected_inner_rmse":d["gate"]["mean_station_rmse"],
                      "n_nested_folds":len(d["inner_fold_station_separation"]),
                      "n_test":d["n_test"]})
    if not frames:raise ValueError("No candidate results")
    if errors:raise AssertionError(str(errors))
    z=pd.concat(frames,ignore_index=True)
    wide=z.pivot(index=["experiment","station_name"],columns="method",values="rmse").reset_index()
    comps=[]
    for exp,w in wide.groupby("experiment"):
        for new,old in [("TARC_SUPPORT","HGB_TERRAIN"),("TARC_SUPPORT","TARC_UNGATED"),
                        ("TARC_SUPPORT","TARC_CONSTANT"),("TARC_SUPPORT","MONTHLY")]:
            gain=w[old]-w[new]
            comps.append({"experiment":exp,"candidate":new,"baseline":old,
                          "n_stations":len(gain),"mean_rmse_gain":gain.mean(),
                          "percent_gain":100*gain.mean()/w[old].mean(),
                          "stations_improved":int((gain>0).sum()),
                          "stations_worsened":int((gain<0).sum())})
    c=pd.DataFrame(comps);c.to_csv(report/"gate_paired_comparisons.csv",index=False)
    g=pd.DataFrame(gates);g.to_csv(report/"gate_selected_hyperparameters.csv",index=False)
    state={"status":"PASS","verified_nested_jobs":len(g),"completed_folds":g.groupby("experiment").size().to_dict(),
           "inner_station_leakage_detected":False,"hidden_targets_in_predictions":False,
           "source_sha256":checksum(source/"manifest.json"),
           "note":"Gate selection is inside each outer fold; this is still a 34-station national network, not independent external evidence."}
    (report/"candidate_verification.json").write_text(json.dumps(state,indent=2))
    methods=["MONTHLY","HGB_TERRAIN","TARC_UNGATED","TARC_CONSTANT","TARC_SUPPORT"]
    dat=z[z.method.isin(methods)].groupby(["experiment","method"],as_index=False).rmse.mean()
    dat.to_csv(report/"candidate_methods_summary.csv",index=False)
    fig,axes=plt.subplots(1,2,figsize=(11.2,4.4),sharex=True,sharey=True)
    colors=["#75808D","#CF7936","#537B61","#A15A6B","#7957AE"]
    for ax,exp,title in zip(axes,["spatial_block","buffer100"],["Spatial blocks","100-km donor buffer"]):
        for y,(m,col) in enumerate(zip(methods,colors)):
            value=dat.loc[dat.experiment.eq(exp)&dat.method.eq(m),"rmse"].item()
            ax.scatter(value,y,s=80,color=col,zorder=3)
            ax.text(value+.004,y,f"{value:.4f}",fontsize=8,va="center")
        ax.set_yticks(range(len(methods)),methods)
        ax.invert_yaxis();ax.set_title(title,fontweight="bold")
        ax.set_xlabel("Mean withheld-station Tmax RMSE (°C)")
        ax.grid(axis="x",alpha=.17)
    axes[0].set_xlim(dat.rmse.min()-.05,dat.rmse.max()+.10)
    fig.suptitle("Nested gate candidate: differences are small and design-dependent",fontweight="bold")
    fig.tight_layout()
    fig.savefig(figs/"F04_nested_gate_comparison.png",dpi=200,bbox_inches="tight")
    fig.savefig(figs/"F04_nested_gate_comparison.pdf",bbox_inches="tight")
    plt.close(fig)
    narrative=["# Nested gate/TARC validation", "", "Tmax-only independent CPU rerun of the author's inner GroupKFold gate-search procedure on 4 geographical groups and 4 additional 100-km donor-buffer groups. All gate hyperparameters use **training-station inner validation only**.","", "| Design | HGB terrain | TARC ungated | TARC constant | TARC support |", "|---|---:|---:|---:|---:|"]
    for exp in ["spatial_block","buffer100"]:
        s=dat[dat.experiment.eq(exp)].set_index("method").rmse
        narrative.append(f"| {exp} | "+" | ".join(f"{s[m]:.4f}" for m in ["HGB_TERRAIN","TARC_UNGATED","TARC_CONSTANT","TARC_SUPPORT"])+" |")
    narrative += ["", "A lower RMSE is preferable. The gate may underperform an ungated or HGB model in specific folds; any such finding must not be hidden. Selection is nested, but four geographical blocks and related training folds imply correlated uncertainty.","", "## Hyperparameters selected by outer fold", "", "```text",g.to_string(index=False),"```",""]
    (report/"NESTED_CANDIDATE_FINDINGS.md").write_text("\n".join(narrative))
    print(json.dumps(state,indent=2))


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--candidate",required=True)
    p.add_argument("--output",required=True)
    p.add_argument("--figures",required=True)
    main(p.parse_args())
