#!/usr/bin/env python3
"""New, independent pre-manuscript evaluations on frozen out-of-fold predictions.

No refitting, date editing, or source-data mutations. All metrics are explicitly
conditional on the author's processed BMD labels and draft station coordinates.
"""

from __future__ import annotations

from collections import defaultdict
from hashlib import sha256
from pathlib import Path
import json
import math
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
WORKSPACE = HERE.parent
sys.path.insert(0, str(WORKSPACE / "research_rebuild/code"))
from paper1_pipeline.core import load_inputs, foundation  # noqa: E402

OUT = HERE / "new_analysis"
JOBS = WORKSPACE / "research_rebuild/results/jobs"
METHODS = ("RAW", "MONTHLY", "ET_LOCAL", "ET_TERRAIN")
TARGETS = {"Tmax": "obs_tmax", "Tmin": "obs_tmin", "Prcp": "obs_prcp"}
YEAR_SELECTIONS = {
    "all_processed_years": lambda y: True,
    "excluding_2021_2023": lambda y: y not in (2021, 2023),
    "excluding_2019_2021_2023": lambda y: y not in (2019, 2021, 2023),
}


def save(frame, name):
    out = OUT / name
    frame.to_csv(out, index=False, float_format="%.8g")
    return out


def finite_metrics(pred, obs):
    pred = np.asarray(pred, dtype=float)
    obs = np.asarray(obs, dtype=float)
    mask = np.isfinite(pred) & np.isfinite(obs)
    pred, obs = pred[mask], obs[mask]
    if not len(pred):
        return dict(n=0, rmse=np.nan, mae=np.nan, bias=np.nan, r=np.nan)
    err = pred - obs
    r = (np.corrcoef(pred, obs)[0, 1]
         if len(pred) > 2 and np.std(pred) > 0 and np.std(obs) > 0 else np.nan)
    return dict(n=len(pred), rmse=float(np.sqrt(np.mean(err**2))),
                mae=float(np.mean(np.abs(err))), bias=float(err.mean()), r=float(r))


def contingency(pred, obs, threshold):
    pred = np.asarray(pred, dtype=float)
    obs = np.asarray(obs, dtype=float)
    mask = np.isfinite(pred) & np.isfinite(obs)
    a = pred[mask] >= threshold
    b = obs[mask] >= threshold
    h = int((a & b).sum())
    m = int((~a & b).sum())
    f = int((a & ~b).sum())
    return dict(n=int(mask.sum()), hits=h, misses=m, false_alarms=f,
                csi=h/(h+m+f) if h+m+f else np.nan,
                pod=h/(h+m) if h+m else np.nan,
                far=f/(h+f) if h+f else np.nan)


def indices(series, variable):
    """One station-year with an explicit full calendar and missing-day NaNs."""
    x = series.astype(float)
    if variable == 'Tmax':
        return {'TXx_C': float(x.max())}
    if variable == 'Tmin':
        return {'TNn_C': float(x.min())}
    assert variable == 'Prcp'
    r5 = x.rolling(5, min_periods=5).sum()
    return {
        'Rx1day_mm': float(x.max()),
        'Rx5day_mm': float(r5.max()),
        'R10mm_days': int((x >= 10.).sum()),
        'R20mm_days': int((x >= 20.).sum()),
        'PRCPTOT_mm': float(x.sum(min_count=1)),
    }


def paired_station_bootstrap(station_series, rng, n_boot=3000):
    """Descriptive station bootstrap; adjacent stations are NOT independent."""
    a = station_series.to_numpy(dtype=float)
    if not len(a):
        return (np.nan, np.nan)
    boot = rng.choice(a, size=(n_boot, len(a)), replace=True).mean(axis=1)
    return float(np.quantile(boot, 0.025)), float(np.quantile(boot, 0.975))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    print('Loading original author input tables (read only)...', flush=True)
    data = load_inputs(WORKSPACE / 'research_v2/input/dataset')
    full = data['full'].set_index('row_id')
    source_hash = {key: sha256(path.read_bytes()).hexdigest() for key, path in data['paths'].items()}
    print('Computing new independently generated NASA POWER baseline tables...', flush=True)
    foundation(data, OUT / 'product_benchmarks')

    # Pred file is one LOSO station and one target; every prediction has a
    # known row_id in original ERA and is already held out from training.
    station_year = []
    climate_index = []
    rain_event = []
    raw_negative = []
    temperature_methods_by_station = defaultdict(dict)
    jobs = sorted(JOBS.glob('loso__seed42__*.npz'))
    if len(jobs) != 102:
        raise RuntimeError(f'Expected 34*3=102 native LOSO arrays, found {len(jobs)}')
    seen = set()
    for ji, job in enumerate(jobs, 1):
        target = job.stem.rsplit('__', 1)[-1]
        if target not in TARGETS:
            raise ValueError('Unexpected target in ' + job.name)
        with np.load(job) as arrays:
            ids = arrays['row_id']
            frame = full.loc[ids, ['station_name','date', TARGETS[target],
                                   {'Prcp':'era5_prcp','Tmax':'t2m_max','Tmin':'t2m_min'}[target]]].copy()
            if frame.station_name.nunique() != 1:
                raise AssertionError('LOSO fold has multiple stations: ' + job.name)
            station = frame.station_name.iloc[0]
            k = (station, target)
            if k in seen:
                raise AssertionError('Duplicate station target LOSO file: ' + str(k))
            seen.add(k)
            raw_field = {'Prcp':'era5_prcp','Tmax':'t2m_max','Tmin':'t2m_min'}[target]
            if not np.allclose(arrays['RAW'], frame[raw_field].to_numpy(float), rtol=1e-8, atol=1e-8):
                raise AssertionError('Saved RAW does not match author ERA row_id: ' + job.name)
            if not set(METHODS).issubset(arrays.files):
                raise AssertionError('Prediction methods not complete: '+job.name)
            obs = frame[TARGETS[target]].to_numpy(float)
            when = pd.DatetimeIndex(frame.date)
            years = when.year.to_numpy()
            preds = {method: arrays[method].copy() for method in METHODS}
            if target != 'Prcp':
                temperature_methods_by_station[station][target] = (ids.copy(), preds)
            else:
                for method in METHODS:
                    raw_negative.append({'station_name': station,'method':method,
                                         'negative_prediction_count':int((preds[method]<-1e-9).sum()),
                                         'nonfinite_prediction_count':int((~np.isfinite(preds[method])).sum())})
            for year in range(2000, 2024):
                include = years == year
                if not include.any():
                    continue
                # Common finite support across obs and all predictors.
                common = include & np.isfinite(obs)
                for method in METHODS:
                    common &= np.isfinite(preds[method])
                if not common.any():
                    continue
                target_dates = when[common]
                reference = obs[common]
                expected = 366 if pd.Timestamp(f'{year}-01-01').is_leap_year else 365
                completeness = len(reference) / expected
                annual_grid = pd.date_range(f'{year}-01-01', f'{year}-12-31', freq='D')
                indexed_obs = pd.Series(reference, index=target_dates).reindex(annual_grid)
                metric_by_method = {}
                for method in METHODS:
                    method_pred = preds[method][common]
                    metric_by_method[method] = finite_metrics(method_pred, reference)
                    station_year.append(dict(station_name=station, target=target, year=year,
                        method=method, expected_days=expected, valid_days=len(reference),
                        completeness_pct=100*completeness,
                        date_issue_year=year in (2019, 2021, 2023),
                        **metric_by_method[method]))
                    if target=='Prcp':
                        for t in (1,10,20,50):
                            rain_event.append(dict(station_name=station, year=year,
                                method=method, threshold_mm=t, date_issue_year=year in (2019,2021,2023),
                                **contingency(method_pred, reference, t)))
                    if completeness >= .95:
                        pi = indices(pd.Series(method_pred, index=target_dates).reindex(annual_grid), target)
                        oi = indices(indexed_obs, target)
                        for index_name, predvalue in pi.items():
                            climate_index.append(dict(station_name=station,target=target,year=year,
                                method=method,index=index_name,observed=oi[index_name],
                                predicted=predvalue,error=predvalue-oi[index_name],
                                abs_error=abs(predvalue-oi[index_name]),
                                completeness_pct=100*completeness,
                                date_issue_year=year in (2019, 2021, 2023)))
        if ji%34==0:
            print(f'  Loaded {ji}/{len(jobs)} frozen LOSO files', flush=True)
    assert len(seen)==102
    by_year = pd.DataFrame(station_year)
    events = pd.DataFrame(rain_event)
    cidx = pd.DataFrame(climate_index)
    negatives = pd.DataFrame(raw_negative)
    save(by_year,'daily_station_year_metrics.csv')
    save(events,'rainfall_event_station_year.csv')
    save(cidx,'annual_climate_index_station_year.csv')
    save(negatives,'rainfall_prediction_physical_check.csv')

    # Separate year-specific deterioration from the 34-station mean summary;
    # station, not station-year, is the unit for descriptive paired bootstrap.
    by_regime = []
    rng=np.random.default_rng(20261110)
    for selection, include in YEAR_SELECTIONS.items():
        mask=by_year.year.map(include)
        group=by_year[mask]
        for (target,method), g in group.groupby(['target','method']):
            # One station's pooled RMSE across all selected years, not the
            # average of that station's annual RMSE values.
            station_agg=g.groupby('station_name').apply(
                lambda z: pd.Series({'n':z.n.sum(),
                    'rmse':np.sqrt(np.average(z.rmse**2,weights=z.n)),
                    'mae':np.average(z.mae,weights=z.n),
                    'bias':np.average(z.bias,weights=z.n)}),
                include_groups=False).reset_index()
            by_regime.append(dict(year_selection=selection,target=target,method=method,
                stations=station_agg.station_name.nunique(),valid_days=int(station_agg.n.sum()),
                mean_station_rmse=station_agg.rmse.mean(),
                mean_station_mae=station_agg.mae.mean(),
                mean_station_bias=station_agg.bias.mean()))
    summary=pd.DataFrame(by_regime)
    save(summary,'daily_model_subset_summary.csv')

    paired=[]
    for (regime,target),g in summary.groupby(['year_selection','target']):
        subset=by_year[by_year.year.map(YEAR_SELECTIONS[regime]) & by_year.target.eq(target)]
        for candidate,baseline in [('ET_LOCAL','RAW'),('ET_TERRAIN','ET_LOCAL'),('MONTHLY','RAW')]:
            scores={}
            for method in (candidate,baseline):
                v=subset[subset.method.eq(method)]
                s=v.groupby('station_name').apply(lambda z:
                    np.sqrt(np.average(z.rmse**2,weights=z.n)),include_groups=False)
                scores[method]=s
            common=scores[candidate].to_frame('new').join(scores[baseline].to_frame('old'),how='inner')
            delta=common.old-common.new
            low,high=paired_station_bootstrap(delta,rng)
            paired.append(dict(year_selection=regime,target=target,candidate=candidate,
                baseline=baseline,n_stations=len(delta),mean_station_rmse_gain=delta.mean(),
                relative_gain_percent=100*delta.mean()/common.old.mean(),
                median_station_gain=delta.median(),stations_improved=int((delta>0).sum()),
                descriptive_station_bootstrap_low=low,descriptive_station_bootstrap_high=high))
    paired_df=pd.DataFrame(paired)
    save(paired_df,'daily_paired_station_effects_by_year_subset.csv')

    out_event=[]
    for selection, include in YEAR_SELECTIONS.items():
        subset=events[events.year.map(include)]
        for (method,threshold),g in subset.groupby(['method','threshold_mm']):
            h,m,f=map(int,[g.hits.sum(),g.misses.sum(),g.false_alarms.sum()])
            out_event.append(dict(year_selection=selection,method=method,threshold_mm=threshold,
                stations=g.station_name.nunique(),station_years=len(g),days=int(g.n.sum()),
                hits=h,misses=m,false_alarms=f,
                csi=h/(h+m+f) if h+m+f else np.nan,
                pod=h/(h+m) if h+m else np.nan,
                far=f/(h+f) if h+f else np.nan))
    event_summary=pd.DataFrame(out_event)
    save(event_summary,'rainfall_event_summary_by_year_subset.csv')

    out_index=[]
    for selection, include in YEAR_SELECTIONS.items():
        subset=cidx[cidx.year.map(include)]
        for (target,index_name,method),g in subset.groupby(['target','index','method']):
            st=g.groupby('station_name').apply(lambda z:
                np.sqrt(np.mean(z.error**2)),include_groups=False)
            out_index.append(dict(year_selection=selection,target=target,index=index_name,
                method=method,stations=st.size,station_years=len(g),
                annual_index_rmse_pooled=np.sqrt(np.mean(g.error**2)),
                mean_station_index_rmse=st.mean(),
                mean_station_index_bias=g.error.mean()))
    index_summary=pd.DataFrame(out_index)
    save(index_summary,'annual_climate_index_summary_by_year_subset.csv')

    # Physical consistency for saved Tmax/Tmin predictions on identical ERA
    # station-date IDs (target-specific missingness masks may differ).
    consistency=[]
    for station,sub in temperature_methods_by_station.items():
        if not {'Tmax','Tmin'}<=set(sub):
            raise AssertionError('Missing temperature LOSO prediction for '+station)
        a_ids, a_pred=sub['Tmax']; b_ids, b_pred=sub['Tmin']
        ai=pd.Series(np.arange(len(a_ids)),index=a_ids)
        bi=pd.Series(np.arange(len(b_ids)),index=b_ids)
        common=ai.index.intersection(bi.index)
        i=ai.loc[common].to_numpy(int)
        j=bi.loc[common].to_numpy(int)
        for method in METHODS:
            d=a_pred[method][i]-b_pred[method][j]
            consistency.append(dict(station_name=station,method=method,n_common_days=len(d),
                tmax_below_tmin_days=int((d < -1e-9).sum()),
                minimum_tmax_minus_tmin_C=float(np.min(d))))
    consistency=pd.DataFrame(consistency)
    save(consistency,'temperature_physical_consistency.csv')

    # Independent, year-by-year paired station summaries; excludes accidental
    # pooling of unlike held-out station-day populations.
    annual_rows=[]
    for (target,year),frame in by_year.groupby(['target','year']):
        w=frame.pivot(index='station_name',columns='method',values='rmse')
        if {'RAW','ET_LOCAL','ET_TERRAIN'}<=set(w):
            annual_rows.append(dict(target=target,year=year,stations=len(w),
                 raw_mean_station_rmse=w.RAW.mean(),
                 et_local_mean_station_rmse=w.ET_LOCAL.mean(),
                 terrain_mean_station_rmse=w.ET_TERRAIN.mean(),
                 et_local_improve_stations=int((w.ET_LOCAL<w.RAW).sum()),
                 terrain_improve_over_local_stations=int((w.ET_TERRAIN<w.ET_LOCAL).sum()),
                 et_local_relative_gain_percent=100*(w.RAW.mean()-w.ET_LOCAL.mean())/w.RAW.mean(),
                 date_issue_year=year in (2019,2021,2023)))
    temporal_summary=pd.DataFrame(annual_rows)
    save(temporal_summary,'yearly_loso_model_ranking.csv')

    # Simple publication-ready figures, no annual status hidden by pooling.
    plt.rcParams.update({'font.size':10.5,'axes.spines.top':False,
                         'axes.spines.right':False,'savefig.dpi':250})
    fig,axes=plt.subplots(1,3,figsize=(14,4.6))
    for ax,t in zip(axes,['Tmax','Tmin','Prcp']):
        a=temporal_summary[temporal_summary.target.eq(t)]
        ax.axhline(0,color='#8A919A',lw=1)
        ax.plot(a.year,a.et_local_relative_gain_percent,lw=1.8,color='#115C83',marker='o',ms=3)
        for issue in (2019,2021,2023):
            ax.axvspan(issue-.4,issue+.4,color='#DDA15E',alpha=.20)
        ax.set(title=f'{t}: ET-local vs raw ERA5',xlabel='Year',ylabel='RMSE reduction (%)')
        ax.grid(alpha=.13,axis='y')
    fig.suptitle('Annual station-held-out skill (processed labels; flagged date years shaded)',fontsize=12)
    fig.tight_layout();fig.savefig(OUT/'F01_yearly_transfer_skill.png',bbox_inches='tight');plt.close(fig)

    data_plot=index_summary[(index_summary.year_selection=='all_processed_years') &
        (index_summary['index'].isin(['TXx_C','TNn_C','Rx1day_mm','Rx5day_mm'])) &
        index_summary.method.isin(['RAW','ET_LOCAL','ET_TERRAIN'])]
    fig,axs=plt.subplots(2,2,figsize=(11.2,7.4))
    for ax,(idx,g) in zip(axs.flat,data_plot.groupby('index',sort=True)):
        g=g.set_index('method').reindex(['RAW','ET_LOCAL','ET_TERRAIN'])
        bars=ax.bar(['Raw','ET local','ET + terrain'],g.mean_station_index_rmse,
                    color=['#7A8797','#1D6B8D','#D48A39'])
        ax.set(title=idx,ylabel='Mean station annual-index RMSE')
        for bar,x in zip(bars,g.mean_station_index_rmse):
            ax.text(bar.get_x()+bar.get_width()/2,bar.get_height(),f'{x:.1f}',
                    va='bottom',ha='center',fontsize=9)
        ax.set_ylim(top=max(g.mean_station_index_rmse)*1.18)
    fig.suptitle('Annual climate-index error from frozen LOSO predictions',fontsize=13)
    fig.tight_layout();fig.savefig(OUT/'F02_annual_climate_indices.png',bbox_inches='tight');plt.close(fig)

    fig,axes=plt.subplots(1,2,figsize=(12,4.2))
    for ax,selection in zip(axes,['all_processed_years','excluding_2021_2023']):
        dd=event_summary[(event_summary.year_selection==selection) &
                         event_summary.method.isin(['RAW','ET_LOCAL','ET_TERRAIN'])]
        for method,color in [('RAW','#7A8797'),('ET_LOCAL','#115C83'),('ET_TERRAIN','#D48A39')]:
            qq=dd[dd.method==method].sort_values('threshold_mm')
            ax.plot(qq.threshold_mm,qq.csi,marker='o',lw=2,color=color,label=method)
        ax.set(xlabel='Rainfall threshold (mm/day)',ylabel='CSI',title=selection.replace('_',' '))
        ax.set_xticks([1,10,20,50]);ax.grid(alpha=.12);ax.legend(frameon=False)
    fig.suptitle('Heavy-rain occurrence skill under source-date sensitivity exclusions',fontsize=12)
    fig.tight_layout();fig.savefig(OUT/'F03_event_skill_excluding_uncertain_years.png',bbox_inches='tight');plt.close(fig)

    # Stable summary written after all source files and derived products exist.
    def metric_for(sel,t,m):
        z=summary[(summary.year_selection==sel)&(summary.target==t)&(summary.method==m)]
        return float(z.mean_station_rmse.iloc[0])
    def index_for(sel,idx,method):
        z=index_summary[(index_summary.year_selection==sel)&
            (index_summary['index']==idx)&(index_summary.method==method)]
        return float(z.mean_station_index_rmse.iloc[0]) if len(z) else None
    def csi_for(sel,threshold,method):
        z=event_summary[(event_summary.year_selection==sel)&
            (event_summary.threshold_mm==threshold)&(event_summary.method==method)]
        return float(z.csi.iloc[0]) if len(z) else None
    result={
        'date_BDT':'2026-11-10','nature':'frozen out-of-fold analytics; NO new model fitting',
        'source_sha256':source_hash,'saved_loso_files_verified':len(jobs),
        'output_series':{'station_year_daily_metrics':len(by_year),'index_station_year_rows':len(cidx),
            'event_station_year_rows':len(events),'all_rainfall_predictions_negative':int(negatives.negative_prediction_count.sum()),
            'temperature_physical_violations':int(consistency.loc[consistency.method.eq('ET_LOCAL'),
                                                   'tmax_below_tmin_days'].sum())},
        'tmax_loso_original':{'raw':metric_for('all_processed_years','Tmax','RAW'),
                              'et_local':metric_for('all_processed_years','Tmax','ET_LOCAL'),
                              'et_terrain':metric_for('all_processed_years','Tmax','ET_TERRAIN')},
        'rainfall_loso_non_suspect_years':{'raw':metric_for('excluding_2021_2023','Prcp','RAW'),
             'et_local':metric_for('excluding_2021_2023','Prcp','ET_LOCAL')},
        'rainfall_50mm_CSI':{
            s:{m:csi_for(s,50,m) for m in ['RAW','ET_LOCAL','ET_TERRAIN']}
            for s in YEAR_SELECTIONS},
        'annual_indices_mean_station_rmse':{
            s:{idx:{m:index_for(s,idx,m) for m in ['RAW','ET_LOCAL','ET_TERRAIN']}
               for idx in ['TXx_C','TNn_C','Rx1day_mm','Rx5day_mm']}
            for s in YEAR_SELECTIONS},
        'cautions':['No new refitting; all observations are existing processed author labels.',
          'Year exclusions are predeclared source-provenance sensitivity, not proof other years are authenticated.',
          'The 2021/2023 candidate date shifts require official source provenance before adopting in a paper.',
          '95% calendar completeness for annual indices; method comparisons use identical observation dates.',
          'Station bootstrap exploratory only due shared calibration folds and geographic dependence.',
          'Historical station coordinates and source time windows have not been independently certified.']
    }
    (OUT/'new_analysis_manifest.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('source_sha256','annual_indices_mean_station_rmse')},
                     indent=2),flush=True)


if __name__=='__main__':
    main()
