#!/usr/bin/env python3
"""Verify executed climate audit outputs, package aggregates without raw BMD data."""

import hashlib
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import pandas as pd

HERE=Path(__file__).resolve().parent
BASE=HERE.parent
ARCHIVE=BASE/'Pre_Manuscript_ERA5_BMD_Executed_Analysis_20261110.zip'


def load(rel):
    return json.loads((HERE/rel).read_text())


def main():
    inp=load('validation/input_quality.json')
    geometry=load('validation/splits/split_geometry_verification.json')
    training=load('validation/recomputed/verification.json')
    geo_exports=load('era_source/recovered_gee_audit_summary.json')
    new=load('new_analysis/new_analysis_manifest.json')
    trades=load('new_analysis/annual_index_tradeoff_manifest.json')
    assert inp['status']=='PASS' and inp['checks_passed']==7
    assert geometry['status']=='PASS' and geometry['checked_jobs']==191
    assert training['status']=='PASS' and training['n_executed_jobs']==191
    assert not training['verification_errors']
    assert training['comparison_with_prior_export']['within_1e_minus_8']==408
    assert len(new['source_sha256'])==7
    assert new['saved_loso_files_verified']==102
    assert geo_exports['total_field_discrepancies_above_1e_7']==0
    assert sum(v['paired'] for v in geo_exports['field_comparison'].values())==3876190
    assert len(trades['focus_et_local'])==7
    annual=pd.read_csv(HERE/'new_analysis/annual_index_paired_station_tradeoffs.csv')
    for regime in ['all_processed_years','excluding_2021_2023']:
        rx=annual[(annual.year_selection==regime) & (annual['index']=='Rx1day_mm') &
                   (annual.candidate=='ET_LOCAL')]
        assert len(rx)==1 and int(rx.stations_worse.iloc[0])==33

    manifest={'title':'Pre-manuscript scientific evidence from frozen LOSO outputs',
        'date_BDT':'2026-11-10',
        'result':'PASS',
        'same_processed_dataset_preserved':True,
        'retrained_models':False,
        'prior_saved_training_jobs_checked':191,
        'original_author_loso_rmse_matches':408,
        'new_saved_loso_arrays_used':102,
        'recovered_ERA_numeric_value_comparisons':3876190,
        'verified_BMD_original_source':False,
        'authenticated_station_coordinates':False,
        'recovered_original_GEE_script':False,
        'explicitly_excluded':['original processed BMD station daily values',
             'precomputed `paired.pkl` with observation-level values',
             'model checkpoints and full prediction arrays',
             'raw NASA POWER and raw ERA station source files'],
        'files':{}}
    items=[]
    for path in sorted(HERE.rglob('*')):
        if not path.is_file():
            continue
        if path.name=='PACKAGE_MANIFEST_SHA256.json':
            continue
        if path.suffix in ('.pyc','.pkl') or '__pycache__' in path.parts:
            continue
        if '.libhelpers_' in str(path):
            continue
        rel=path.relative_to(BASE).as_posix()
        # This safety filter must never be loosened for an export intended for sharing.
        if 'bmd_clean_daily.csv' in rel or 'raw_daily' in rel:
            raise RuntimeError('Refusing to package an observation-level input: '+rel)
        items.append((path,rel))
        manifest['files'][rel]={
            'size_bytes':path.stat().st_size,
            'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    mpath=HERE/'PACKAGE_MANIFEST_SHA256.json'
    mpath.write_text(json.dumps(manifest,indent=2)+'\n')
    with ZipFile(ARCHIVE,'w',ZIP_DEFLATED,compresslevel=8) as z:
        for src,name in items:
            z.write(src,name)
        z.write(mpath,mpath.relative_to(BASE).as_posix())
    with ZipFile(ARCHIVE) as z:
        assert z.testzip() is None
        assert not any(s.endswith('paired.pkl') or 'bmd_clean_daily.csv' in s for s in z.namelist())
    print(json.dumps({'archive':str(ARCHIVE),'size_bytes':ARCHIVE.stat().st_size,
                      'packaged_files':len(items)+1,'all_checks':'PASS',
                      'private_raw_bmd_in_archive':False},indent=2))


if __name__=='__main__':
    main()
