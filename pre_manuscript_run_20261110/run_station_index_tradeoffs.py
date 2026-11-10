#!/usr/bin/env python3
"""Paired, station-unit climate-index trade-offs on saved frozen LOSO results.

The station-year common support was already enforced in run_remaining_analytics.py.
Descriptive CIs do not assert independent neighboring stations or external validity.
"""

from pathlib import Path
import json

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'new_analysis'
SELECTIONS = {
    'all_processed_years': (),
    'excluding_2021_2023': (2021, 2023),
    'excluding_2019_2021_2023': (2019, 2021, 2023),
}
RNG = np.random.default_rng(20261110)


def descriptive_interval(diff):
    values = diff.to_numpy(dtype=float)
    boot = RNG.choice(values, size=(4000, len(values)), replace=True).mean(axis=1)
    return float(np.quantile(boot, .025)), float(np.quantile(boot, .975))


def main():
    indices = pd.read_csv(OUT/'annual_climate_index_station_year.csv')
    rows = []
    yearwise = []
    station_detail = []
    for selection, excluded in SELECTIONS.items():
        view = indices[~indices.year.isin(excluded)]
        for (target, index), subset in view.groupby(['target', 'index']):
            pv = subset.pivot(index=['station_name', 'year'], columns='method', values='error')
            if pv.isna().any().any():
                raise ValueError(f'Inconsistent annual index supports: {selection}, {index}')
            for method in ['MONTHLY','ET_LOCAL','ET_TERRAIN']:
                x = pv[[method,'RAW']]
                station_rmse = x.groupby(level='station_name').apply(lambda p: pd.Series({
                    'raw_station_annual_rmse': np.sqrt(np.mean(p.RAW**2)),
                    'corrected_station_annual_rmse': np.sqrt(np.mean(p[method]**2)),
                    'station_years': len(p),
                }))
                station_rmse['rmse_gain'] = (station_rmse.raw_station_annual_rmse
                                            - station_rmse.corrected_station_annual_rmse)
                lo,hi=descriptive_interval(station_rmse.rmse_gain)
                rows.append(dict(year_selection=selection, target=target, index=index,
                    candidate=method, baseline='RAW', stations=len(station_rmse),
                    station_years=len(x), stations_better=int((station_rmse.rmse_gain>0).sum()),
                    stations_worse=int((station_rmse.rmse_gain<0).sum()),
                    mean_station_rmse_gain=float(station_rmse.rmse_gain.mean()),
                    relative_mean_station_rmse_gain_pct=float(
                        100*station_rmse.rmse_gain.mean()/station_rmse.raw_station_annual_rmse.mean()),
                    descriptive_bootstrap_low=lo, descriptive_bootstrap_high=hi))
                for station,z in station_rmse.iterrows():
                    station_detail.append(dict(year_selection=selection,target=target,index=index,
                        candidate=method,station_name=station,**z.to_dict()))
                for year,g in x.groupby(level='year'):
                    gain = np.sqrt(np.mean(g.RAW**2))-np.sqrt(np.mean(g[method]**2))
                    yearwise.append(dict(year_selection=selection,target=target,index=index,
                        candidate=method,year=int(year),stations=len(g),
                        pooled_station_year_annual_rmse_gain=float(gain)))
    out = pd.DataFrame(rows)
    details = pd.DataFrame(station_detail)
    trends = pd.DataFrame(yearwise)
    out.to_csv(OUT/'annual_index_paired_station_tradeoffs.csv',index=False)
    details.to_csv(OUT/'annual_index_station_tradeoffs.csv',index=False)
    trends.to_csv(OUT/'annual_index_yearly_tradeoff.csv',index=False)

    # A 95% completeness cutoff allows a few missing observation days.
    # Repeat focal indices on entirely complete station-years to check that
    # the extreme-rainfall ranking is not a completeness-filter artefact.
    complete_rows=[]
    for cutoff in (95.0, 100.0):
        dat=indices[indices.completeness_pct >= cutoff-1e-7]
        for idx in ('TXx_C','TNn_C','Rx1day_mm','Rx5day_mm','R10mm_days','PRCPTOT_mm'):
            g=dat[dat['index'].eq(idx)]
            p=g.pivot(index=['station_name','year'],columns='method',values='error')
            if not len(p):
                continue
            for method in ('RAW','ET_LOCAL'):
                st=p[method].groupby(level='station_name').apply(
                    lambda e: float(np.sqrt(np.mean(e**2))))
                complete_rows.append(dict(index=idx,minimum_completeness_pct=cutoff,
                    method=method, stations=len(st),station_years=len(p),
                    mean_station_annual_index_rmse=st.mean()))
    pd.DataFrame(complete_rows).to_csv(OUT/'annual_indices_completeness_sensitivity.csv',index=False)

    focus = out[(out.year_selection=='all_processed_years') &
                (out.candidate=='ET_LOCAL') &
                out['index'].isin(['TXx_C','TNn_C','Rx1day_mm','Rx5day_mm',
                                   'PRCPTOT_mm','R10mm_days','R20mm_days'])]
    focus=focus.set_index('index').reindex(['TXx_C','TNn_C','PRCPTOT_mm',
        'R10mm_days','R20mm_days','Rx1day_mm','Rx5day_mm'])
    fig,ax=plt.subplots(figsize=(10,5.2))
    y=np.arange(len(focus))
    values=focus.relative_mean_station_rmse_gain_pct
    barcolors=np.where(values>=0,'#18745B','#C25D42')
    ax.barh(y,values,color=barcolors,height=.64)
    ax.axvline(0,color='#3D484F',lw=1.1)
    ax.set_yticks(y,focus.index)
    ax.invert_yaxis()
    ax.set_xlim(min(-70,float(values.min())*1.2),max(70,float(values.max())*1.2))
    ax.set_xlabel('Relative mean station annual-index RMSE reduction vs raw (%)')
    ax.set_title('Daily correction does not guarantee better climate indices')
    for yp,val in zip(y,values):
        ax.text(val+(1.2 if val>=0 else -1.2),yp,f'{val:+.1f}%',
                ha='left' if val>=0 else 'right',va='center',fontsize=9.5)
    ax.spines[['top','right']].set_visible(False)
    fig.tight_layout(); fig.savefig(OUT/'F04_climate_index_paired_tradeoff.png',dpi=240,
                                   bbox_inches='tight');plt.close(fig)
    note = {
        'source':'annual_climate_index_station_year.csv; frozen LOSO predictions, no retraining',
        'shared_station_year_support':True,
        'unit_of_descriptive_resampling':'station; 4000 resamples',
        'caveat':'Station bootstrap not formal external or spatially independent inference.',
        'annual_completeness_sensitivity':'95% versus 100% in annual_indices_completeness_sensitivity.csv',
        'focus_et_local':focus[['stations','station_years','stations_better','stations_worse',
            'relative_mean_station_rmse_gain_pct']].reset_index().to_dict('records'),
    }
    (OUT/'annual_index_tradeoff_manifest.json').write_text(json.dumps(note,indent=2)+'\n')
    print(json.dumps(note,indent=2))


if __name__=='__main__':
    main()
