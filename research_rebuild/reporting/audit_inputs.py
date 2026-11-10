#!/usr/bin/env python3
"""Check dataset provenance/joins, missingness, QC flags and station exclusions."""
import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"code"))
from paper1_pipeline.core import TARGETS, ISLANDS, load_inputs, sha256


def main(args):
    root=Path(args.input).resolve();out=Path(args.output).resolve()
    data=load_inputs(root);bmd=data["bmd"];era=data["era"];full=data["full"]
    flags=list(root.rglob("bmd_flags.csv"))
    assert len(flags)==1
    rejected=pd.read_csv(flags[0]);clean=bmd.set_index(["station_name","date"])
    rejects_missing=[]
    for r in rejected.itertuples(index=False):
        value=clean.loc[(r.station_name,r.date),r.variable]
        rejects_missing.append(bool(pd.isna(value)))
    native=era.loc[~era.station_name.isin(ISLANDS)]
    paired_count={lab:int(full[[obs,raw]].notna().all(axis=1).sum()) for lab,(obs,raw) in TARGETS.items()}
    report={
        "status":"PASS", "source_manifest":{k:{"bytes":p.stat().st_size,"sha256":sha256(p)} for k,p in data["paths"].items()},
        "bmd":{"rows":len(bmd),"station_count":bmd.station_name.nunique(),
                "long_station_count":bmd.loc[bmd.record_type.eq("long"),"station_name"].nunique(),
                "short_station_count":bmd.loc[bmd.record_type.eq("short"),"station_name"].nunique(),
                "missing_fraction":{c:float(bmd[c].isna().mean()) for c in ["tmax","tmin","prcp"]},
                "flagged_values_count":len(rejected),"flagged_values_set_missing_in_clean":sum(rejects_missing),
                "duplicate_station_date_rows":int(bmd.duplicated(["station_name","date"]).sum()),
                "tmax_lt_tmin":int((bmd.tmax<bmd.tmin).sum()),
                "negative_rain":int((bmd.prcp<0).sum())},
        "era":{"rows":len(era),"station_count":era.station_name.nunique(),
               "source_counts":era.era5_source.value_counts().to_dict(),
               "native_station_count":native.station_name.nunique(),
               "native_missing_targets":{c:int(native[c].isna().sum()) for c in ["t2m_max","t2m_min","prcp"]},
               "duplicate_station_date_rows":int(era.duplicated(["station_name","date"]).sum())},
        "power":{"rows":len(data["power"]),"grid_cells":int(data["power"][["LAT","LON"]].drop_duplicates().shape[0]),
                 "minus999_raw_sentinel_counts":{c:int(v) for c,v in data["power_sentinels"].items() if v>0}},
        "merged":{"rows":len(full),"valid_paired_observation_era_rows":paired_count,
                  "trainable_native_stations":int(full.loc[~full.station_name.isin(ISLANDS),"station_name"].nunique())},
        "metadata":{"coordinate_source_counts":data["meta"].coord_source.value_counts().to_dict(),
                    "coordinate_validation":"Unverified draft user metadata; do not infer authoritative coordinates."},
        "known_limits":["Daily BMD pre-QC records and complete station observing-hour conventions were not supplied.",
                        "ERA5/NASA sampling offset and field extraction provenance need independent source documentation.",
                        "This is not an independent external national station network.",
                        "BMD/public reuse licensing must be checked before publishing station observations."],
    }
    checks=[report["bmd"]["flagged_values_count"]==report["bmd"]["flagged_values_set_missing_in_clean"],
            report["bmd"]["tmax_lt_tmin"]==0,report["bmd"]["negative_rain"]==0,
            report["bmd"]["duplicate_station_date_rows"]==0,
            report["era"]["duplicate_station_date_rows"]==0,
            report["era"]["native_station_count"]==34,
            not any(report["era"]["native_missing_targets"].values())]
    report["checks_passed"]=sum(checks);report["checks_total"]=len(checks)
    if not all(checks):report["status"]="FAIL"
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,indent=2,ensure_ascii=False))
    print(f"DATA AUDIT {report['status']} {sum(checks)}/{len(checks)} checks, {len(bmd)} BMD rows")
    if not all(checks):raise AssertionError("Input audit failed")


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input",required=True)
    p.add_argument("--output",required=True)
    main(p.parse_args())
