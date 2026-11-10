#!/usr/bin/env python3
"""Independently inspect every saved outer split and 100-km geographic buffer."""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


def haversine(a,b):
    a=np.radians(a);b=np.radians(b)
    t=np.sin((a[:,None,0]-b[None,:,0])/2)**2+np.cos(a[:,None,0])*np.cos(b[None,:,0])*np.sin((a[:,None,1]-b[None,:,1])/2)**2
    return 6371*2*np.arcsin(np.sqrt(np.clip(t,0,1)))


def audit(args):
    results=Path(args.results);root=Path(args.input)
    matches=list(root.rglob("station_metadata_final.csv"));assert len(matches)==1
    meta=pd.read_csv(matches[0]).set_index("station_name")
    names=set(meta.index)-{"Kutubdia","Sandwip"}
    rows=[];leaks=[]
    for p in sorted((results/"jobs").glob("*.json")):
        d=json.loads(p.read_text());train=set(d["train_station_names"]);test=set(d["test_station_names"])
        if not test or not train or train&{"Kutubdia","Sandwip"}:
            leaks.append(p.stem+": empty group or filled-island training")
        if d["experiment"]!="temporal" and train&test:
            leaks.append(p.stem+": overlapping station group")
        if d["experiment"]=="temporal" and d["train_last"]>=d["test_first"]:
            leaks.append(p.stem+": temporal overlap")
        if not train.issubset(names) or not test.issubset(names):
            leaks.append(p.stem+": missing/extra station name")
        min_distance=float(haversine(meta.loc[sorted(train),["lat","lon"]].to_numpy(),
                                    meta.loc[sorted(test),["lat","lon"]].to_numpy()).min())
        if d["experiment"]=="buffer100" and min_distance<99.999999:
            leaks.append(p.stem+": training station less than 100 km from held-out station")
        rows.append({"experiment":d["experiment"],"design":d["design"],"fold":d["fold"],
                     "target":d["target"],"n_train_stations":len(train),"n_test_stations":len(test),
                     "min_train_to_test_distance_km":min_distance,
                     "train_dates_max":d["train_last"],"test_dates_min":d["test_first"],
                     "test_station_names":",".join(sorted(test))})
    z=pd.DataFrame(rows)
    for (exp,design,target),g in z.groupby(["experiment","design","target"]):
        observed=[]
        for group in g.test_station_names:
            observed.extend(group.split(","))
        if len(observed)!=len(names) or set(observed)!=names or len(observed)!=len(set(observed)):
            leaks.append(f"{exp}/{design}/{target}: test stations not covered once each")
    out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
    z.to_csv(out/"split_geometry_coverage.csv",index=False)
    state={"status":"PASS" if not leaks else "FAIL","checked_jobs":len(z),
           "native_station_count":len(names),"unique_design_target_groups":z.groupby(["experiment","design","target"]).ngroups,
           "min_100km_buffer_distance_km":float(z.loc[z.experiment.eq("buffer100"),"min_train_to_test_distance_km"].min()),
           "errors":leaks,"limitations":"Coordinates are taken from user-supplied draft metadata and need authority/source validation."}
    (out/"split_geometry_verification.json").write_text(json.dumps(state,indent=2))
    print(json.dumps(state,indent=2))
    if leaks:raise AssertionError("Split verification failed")


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input",required=True)
    p.add_argument("--results",required=True)
    p.add_argument("--output",required=True)
    audit(p.parse_args())
