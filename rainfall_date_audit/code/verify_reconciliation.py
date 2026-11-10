#!/usr/bin/env python3
"""Fail-fast checks for the non-destructive candidate and frozen-score audit."""
from pathlib import Path
import hashlib
import json
import zipfile
import xml.etree.ElementTree as ET

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parent.parent
OUT = BASE / "outputs/BMD_Date_Reconciliation_20261110"


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for c in iter(lambda: f.read(1024 * 1024), b''):
            h.update(c)
    return h.hexdigest()


def check():
    manifest = json.loads((OUT / 'reconciliation_manifest.json').read_text())
    for rel, expected in manifest['inputs_sha256'].items():
        path = BASE / rel
        assert path.exists() and sha(path) == expected, 'Original input altered or unavailable: ' + rel
    for name, expected in manifest['output_files_sha256'].items():
        assert sha(OUT / name) == expected, 'Output changed without manifest update: ' + name
    original = pd.read_csv(BASE/'input/dataset/BMD data/bmd_clean_daily.csv', parse_dates=['date'])
    candidate = pd.read_csv(OUT/'bmd_rainfall_only_date_alignment_CANDIDATE_not_BMD_raw.csv', parse_dates=['date', 'candidate_from_original_date'])
    assert len(candidate) == len(original) == 326861
    assert not candidate.duplicated(['station_name','date']).any()
    assert np.all(candidate.prcp_candidate_date_aligned.dropna() >= 0)
    align = candidate.loc[candidate.alignment_days.eq(-1)]
    assert len(align) == manifest['date_shifted_rows'] == 24455
    assert align.prcp_candidate_date_aligned.isna().sum() == 418
    assert (align.date - align.candidate_from_original_date).eq(pd.Timedelta(days=1)).all()
    # The original rainfall input remains present as a separate column.
    m = original[['station_name','date','prcp']].merge(candidate[['station_name','date',
        'prcp_author_original']],on=['station_name','date'],validate='one_to_one')
    assert np.allclose(m.prcp.fillna(-12345), m.prcp_author_original.fillna(-12345))
    # Every proposed shift pulls from the author's original previous day.
    prev=align[['station_name','candidate_from_original_date','prcp_candidate_date_aligned']].merge(
        original[['station_name','date','prcp']],
        left_on=['station_name','candidate_from_original_date'],right_on=['station_name','date'],
        how='left',validate='many_to_one')
    assert np.allclose(prev.prcp.fillna(-12345),prev.prcp_candidate_date_aligned.fillna(-12345))
    for station, year in [('Bogra',2021),('Teknaf',2023)]:
        q=candidate[(candidate.station_name==station)&(candidate.date.dt.year==year)]
        assert len(q)>300 and q.alignment_days.eq(0).all()
    q=candidate[candidate.date.dt.year==2019]
    assert q.alignment_days.eq(0).all()
    assert np.allclose(q.prcp_author_original.fillna(-12345),q.prcp_candidate_date_aligned.fillna(-12345))
    scores=pd.read_csv(OUT/'frozen_predictions_pooled_scenarios.csv')
    nscore=scores.groupby(['year','method']).agg(scenarios=('label_scenario','nunique'),
                                                    counts=('n','nunique'))
    assert nscore.scenarios.eq(3).all() and nscore.counts.eq(1).all()
    assert scores.frozen_predictions_not_retrained.all()
    source=pd.read_csv(OUT/'mendeley_adjacent_year_repetition_scan.csv')
    assert source.loc[(source.station=='bogra')&(source.year==2021),'exact_days'].iloc[0]==365
    assert source.loc[(source.station=='teknaf')&(source.year==2023),'exact_days'].iloc[0]==332
    with zipfile.ZipFile(OUT/'Rainfall_Date_Reviewer_Audit.xlsx') as book:
        root=ET.fromstring(book.read('xl/workbook.xml'))
        names=[e.attrib['name'] for e in root.findall('.//{*}sheet')]
        assert names==['Overview','Station years','Frozen LOSO','Source repetition'], names
    notebook=json.loads((OUT/'run_reconciliation.ipynb').read_text())
    assert notebook['nbformat']==4 and len(notebook['cells'])>=3
    print(json.dumps({"status":"PASS","original_rows":len(original),"candidate_rows":len(candidate),
                      "shifted_rows":len(align),"shifted_missing_rows":int(align.prcp_candidate_date_aligned.isna().sum()),
                      "score_groups":len(scores),"workbook_sheets":names,"input_sha_verified":True},indent=2))


if __name__=='__main__':
    check()
