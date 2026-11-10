#!/usr/bin/env python3
"""Additional nested, genuinely held-out Tmax gate/TARC revalidation."""
import argparse
import json
import sys
import time
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pandas as pd

CODE = Path(__file__).resolve().parents[1]/"code"
sys.path.insert(0,str(CODE))
from paper1_pipeline.core import Config, TARGETS, load_inputs, sha256
from paper1_pipeline.models import fit_predict_suite
from run_research import scheduled_jobs, station_scores


def run(args):
    out=Path(args.output).resolve();out.mkdir(parents=True,exist_ok=True)
    cfg=Config(seed=42,n_jobs=args.jobs,max_train_rows=50000,include_neighbours=False)
    d=load_inputs(args.input);full=d["full"]
    source={"configuration":asdict(cfg),
            "input_sha256":{k:sha256(p) for k,p in d["paths"].items()},
            "source_module_sha256":{p.name:sha256(p) for p in sorted((CODE/"paper1_pipeline").glob("*.py"))},
            "runner_sha256":sha256(Path(__file__)),
            "design":"Four spatial blocks and four 100-km buffered blocks; Tmax only; nested gate selection within training stations. Neighbour feature optional suite disabled.",
            "prediction_privacy":"Only predictions, no withheld BMD observation arrays."}
    (out/"manifest.json").write_text(json.dumps(source,indent=2))
    scores=[]
    for mode,design,fold,train,test in scheduled_jobs(full,"geometry",False):
        if mode not in ("spatial_block","buffer100"):
            continue
        if args.smoke and scores:
            break
        key=f"{mode}__{fold}"
        base=out/key
        if base.with_suffix(".json").exists():
            print("RESUME",key,flush=True)
            continue
        t=time.time()
        test_valid,preds,info,models=fit_predict_suite(train,test,full,cfg,"Tmax",candidate=True)
        obs,raw=TARGETS["Tmax"]
        assert not set(train.station_name)&set(test.station_name)
        tab=station_scores(test_valid,obs,preds,mode,fold,"Tmax","nested")
        tab.to_csv(base.with_suffix(".csv"),index=False)
        # Do not save the `observed` field from the source suite.
        np.savez_compressed(base.with_suffix(".npz"),row_id=test_valid.row_id.to_numpy(),
                            gate_weight=test_valid.gate_weight.to_numpy(),
                            terrain_distance=test_valid.terrain_distance.to_numpy(),**preds)
        out_info={"experiment":mode,"fold":fold,"target":"Tmax",
                  "train_station_names":sorted(train.station_name.unique().tolist()),
                  "test_station_names":sorted(test_valid.station_name.unique().tolist()),
                  "n_train_available":len(train),"n_test":len(test_valid),
                  "model_methods":sorted(preds),"gate":info["gate"],
                  "constant_gate":info["constant_gate"],
                  "inner_fold_station_separation":info["inner_folds"],
                  "gate_search_grid":info["gate_risk"],
                  "seconds":round(time.time()-t,3),
                  "metrics_sha256":sha256(base.with_suffix(".csv")),
                  "predictions_sha256":sha256(base.with_suffix(".npz"))}
        base.with_suffix(".json").write_text(json.dumps(out_info,indent=2))
        scores.append(tab)
        print(f"DONE candidate {key} {time.time()-t:.1f}s gate={info['gate']['amplitude']}/{info['gate']['bandwidth']} "
              f"scores={tab.groupby('method').rmse.mean().loc[['MONTHLY','HGB_TERRAIN','TARC_SUPPORT','TARC_UNGATED']].round(4).to_dict()}",flush=True)
    all_scores=[pd.read_csv(p) for p in sorted(out.glob("*.csv")) if p.name!="summary.csv"]
    if all_scores:
        combined=pd.concat(all_scores,ignore_index=True)
        combined.groupby(["experiment","method"],as_index=False).agg(
            mean_station_rmse=("rmse","mean"),
            n_stations=("station_name","nunique")
        ).to_csv(out/"summary.csv",index=False)


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input",required=True)
    p.add_argument("--output",required=True)
    p.add_argument("--jobs",type=int,default=4)
    p.add_argument("--smoke",action="store_true")
    run(p.parse_args())
