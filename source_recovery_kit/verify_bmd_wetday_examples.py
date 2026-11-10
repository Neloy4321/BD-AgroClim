#!/usr/bin/env python3
"""Recompare manually transcribed public BMD 06AM bulletins to uploaded BMD dates.

Official values/URLs are frozen in official_bmd_wetday_examples.csv.
This script cannot automatically authenticate the PDF transcription, observation
window, legal reuse, or the full historical record; inspect PDFs directly.
"""
import argparse
from pathlib import Path
import pandas as pd

BASE=Path(__file__).resolve().parent


def main():
    cli=argparse.ArgumentParser()
    cli.add_argument("--bmd",type=Path,required=True,
                     help="Path to author's original bmd_clean_daily.csv (not redistributed)")
    cli.add_argument("--spotchecks",type=Path,default=BASE/"official_bmd_wetday_examples.csv")
    cli.add_argument("--out",type=Path,default=BASE/"results/official_bmd_wetday_date_comparison.csv")
    args=cli.parse_args()
    source=pd.read_csv(args.bmd,parse_dates=["date"])
    source=source.set_index(["station_name","date"])["prcp"]
    cases=pd.read_csv(args.spotchecks,parse_dates=["bulletin_date"])
    outputs=[]
    for item in cases.itertuples(index=False):
        same_date=source.get((item.station_name,item.bulletin_date),float("nan"))
        previous_date=source.get((item.station_name,item.bulletin_date-pd.Timedelta(days=1)),float("nan"))
        same_match=pd.notna(same_date) and abs(same_date-item.official_rainfall_mm)<1e-9
        previous_match=pd.notna(previous_date) and abs(previous_date-item.official_rainfall_mm)<1e-9
        outputs.append({"bulletin_date":str(item.bulletin_date.date()),"station_name":item.station_name,
                        "official_rainfall_mm":item.official_rainfall_mm,"bmd_date_same_mm":same_date,
                        "bmd_date_previous_mm":previous_date,"matches_bulletin_date":same_match,
                        "matches_previous_date":previous_match,"source_url":item.source_url,
                        "source_note":item.source_note})
    out=pd.DataFrame(outputs)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    out.to_csv(args.out,index=False)
    print(out[["bulletin_date","station_name","official_rainfall_mm","bmd_date_same_mm",
               "bmd_date_previous_mm","matches_bulletin_date","matches_previous_date"]].to_string(index=False))
    print("7 individual wet station-date comparisons across 3 public bulletins; examples only, not yearly source validation.")


if __name__=="__main__":
    main()
