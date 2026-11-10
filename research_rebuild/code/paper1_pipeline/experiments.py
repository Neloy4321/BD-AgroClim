from dataclasses import asdict
from pathlib import Path
import hashlib,json,time
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.cluster import KMeans
from threadpoolctl import threadpool_limits
from .core import Config,ISLANDS,TARGETS,metrics,detection,save_table,write_json,sha256,bh_adjust
from .models import fit_predict_suite

def split_definitions(full,cfg,mode):
    overlap=full[full.date.between(cfg.study_start,cfg.study_end)]
    names=sorted(set(overlap.station_name)-set(ISLANDS))
    native=overlap.station_name.isin(names)
    if mode=='loso':
        for s in names:yield s,overlap[native&overlap.station_name.ne(s)],overlap[overlap.station_name.eq(s)]
    elif mode=='islands':
        yield 'islands',overlap[native],overlap[overlap.station_name.isin(ISLANDS)]
    elif mode=='temporal':
        yield '2016_2023',overlap[native&overlap.date.le(cfg.temporal_cutoff)],overlap[native&overlap.date.gt(cfg.temporal_cutoff)]
    elif mode in ['spatial_block','spatiotemporal']:
        meta=overlap[native][['station_name','lat','lon']].drop_duplicates().sort_values('station_name')
        xy=meta[['lat','lon']].to_numpy();xy[:,1]*=np.cos(np.radians(xy[:,0].mean()))
        labels=KMeans(n_clusters=4,random_state=42,n_init=20).fit_predict(xy)
        for k in sorted(set(labels)):
            held=meta.station_name.to_numpy()[labels==k];tr=overlap[native&~overlap.station_name.isin(held)]
            te=overlap[overlap.station_name.isin(held)]
            if mode=='spatiotemporal':tr=tr[tr.date.le(cfg.temporal_cutoff)];te=te[te.date.gt(cfg.temporal_cutoff)]
            yield f'block_{k}',tr,te
    else:raise ValueError(mode)

def run_experiments(data,out,cfg=Config(),mode='loso',targets=('Tmax',),fold_limit=None):
    out=Path(out);root=out/'experiments'/mode;root.mkdir(parents=True,exist_ok=True)
    # Experiment fingerprint prevents mixing old code/config/input predictions on resume.
    code_hash=hashlib.sha256(''.join(sha256(Path(__file__).parent/p) for p in ['core.py','models.py','experiments.py']).encode()).hexdigest()
    inp=json.loads((out/'input_manifest.json').read_text())['files']
    manifest={'config':asdict(cfg),'code_sha256':code_hash,'input_files':inp,'mode':mode,'targets':list(targets)}
    ident=hashlib.sha256(json.dumps(manifest,sort_keys=True).encode()).hexdigest()
    mp=root/'manifest.json'
    if mp.exists() and json.loads(mp.read_text())['fingerprint']!=ident:
        raise ValueError(f'{root}: existing results have different inputs/code/config. Use a new output directory.')
    write_json(mp,dict(fingerprint=ident,**manifest))
    full=data['full'];start=time.time();done=0
    with threadpool_limits(limits=cfg.n_jobs):
        for i,(fold,train,test) in enumerate(split_definitions(full,cfg,mode)):
            if fold_limit is not None and i>=fold_limit:break
            safe=''.join(c if c.isalnum() else '_' for c in fold)
            for target in targets:
                path=root/f'{safe}__{target}.npz';jpath=path.with_suffix('.json')
                if path.exists() and jpath.exists():print(f'RESUME {mode} {fold} {target}',flush=True);continue
                t=time.time();te,preds,info,_=fit_predict_suite(train,test,full,cfg,target)
                obs,raw=TARGETS[target]
                arrays={'row_id':te.row_id.to_numpy(),'observed':te[obs].to_numpy(),**preds}
                if 'gate_weight' in te:arrays.update(gate_weight=te.gate_weight.to_numpy(),terrain_distance=te.terrain_distance.to_numpy())
                np.savez_compressed(path,**arrays)
                info.update(fold=fold,target=target,mode=mode,seconds=time.time()-t,
                    test_stations=sorted(te.station_name.unique()),train_date_min=str(train.date.min()),
                    train_date_max=str(train.date.max()),test_date_min=str(te.date.min()),test_date_max=str(te.date.max()))
                write_json(jpath,info);done+=1
                score={k:round(metrics(v,te[obs],target!='Prcp')['rmse'],4) for k,v in preds.items()}
                print(f'{mode} {i+1} {fold} {target} {time.time()-t:.1f}s {score}',flush=True)
    print(f'Finished {done} new fits in {time.time()-start:.1f}s; output={root}',flush=True)
    return summarize_experiments(data,out,mode)

def load_predictions(data,out,mode):
    full=data['full'].set_index('row_id');frames=[]
    for path in sorted((Path(out)/'experiments'/mode).glob('*.npz')):
        a=np.load(path);info=json.loads(path.with_suffix('.json').read_text());ids=a['row_id']
        x=full.loc[ids,['station_name','date','landscape','year','era5_source']].reset_index()
        for key in a.files:
            if key!='row_id':x[key]=a[key]
        x['target']=info['target'];x['fold']=info['fold'];frames.append(x)
    if not frames:raise ValueError(f'No predictions for {mode}')
    z=pd.concat(frames,ignore_index=True)
    if z.duplicated(['row_id','target']).any():raise AssertionError('Repeated evaluation row')
    return z

def summarize_experiments(data,out,mode):
    root=Path(out)/'experiments'/mode;z=load_predictions(data,out,mode)
    methods=[c for c in z if c.isupper() or c.startswith('TARC_')]
    pooled=[];station=[];det=[];extremes=[];annual=[];seasons=[]
    for target,part in z.groupby('target'):
        ms=[m for m in methods if part[m].notna().any()]
        part=part.dropna(subset=ms+['observed']) # exact common support across all included models
        for m in ms:
            pooled.append(dict(mode=mode,target=target,method=m,**metrics(part[m],part.observed,target!='Prcp')))
            for s,g in part.groupby('station_name'):
                station.append(dict(mode=mode,target=target,method=m,station_name=s,landscape=g.landscape.iloc[0],fold=g.fold.iloc[0],
                                    **metrics(g[m],g.observed,target!='Prcp')))
                for year,yr in g.groupby('year'):
                    expected=366 if pd.Timestamp(f'{year}-12-31').is_leap_year else 365
                    if len(yr)<.9*expected:continue
                    annual.append(dict(target=target,method=m,station_name=s,year=year,n=len(yr),
                        mean_obs=yr.observed.mean(),mean_pred=yr[m].mean(),sum_obs=yr.observed.sum(),sum_pred=yr[m].sum(),
                        annual_max_obs=yr.observed.max(),annual_max_pred=yr[m].max(),
                        wet_days_obs=int(yr.observed.ge(1).sum()) if target=='Prcp' else np.nan,
                        wet_days_pred=int(yr[m].ge(1).sum()) if target=='Prcp' else np.nan))
            for season,g in part.assign(month=part.date.dt.month).groupby('month'):
                seasons.append(dict(target=target,method=m,month=season,**metrics(g[m],g.observed,target!='Prcp')))
            if target=='Prcp':
                for t in [1,10,20,50]:det.append(dict(target=target,method=m,**detection(part[m],part.observed,t)))
            else:
                # Fixed, physically readable thresholds; no thresholds estimated from outer test observations.
                for t in ([35,38,40] if target=='Tmax' else [20,25,28]):
                    extremes.append(dict(target=target,method=m,**detection(part[m],part.observed,t)))
    pooled=pd.DataFrame(pooled);station=pd.DataFrame(station);summary=[];paired=[]
    rng=np.random.default_rng(42)
    for (target,m),g in station.groupby(['target','method']):
        v=g.rmse.to_numpy();n=len(v);ci=stats.t.interval(.95,n-1,loc=v.mean(),scale=stats.sem(v)) if n>1 else [np.nan,np.nan]
        summary.append(dict(target=target,method=m,n_stations=n,mean_station_rmse=v.mean(),median_station_rmse=np.median(v),
            sd_station_rmse=v.std(ddof=1) if n>1 else np.nan,worst_station_rmse=v.max(),ci_low_naive=ci[0],ci_high_naive=ci[1]))
    comparisons=[('HGB_TERRAIN','HGB_LOCAL'),('ET_TERRAIN','ET_LOCAL'),('ET_NEIGH','ET_TERRAIN'),
      ('TARC_SUPPORT','HGB_TERRAIN'),('TARC_SUPPORT','TARC_UNGATED'),('TARC_SUPPORT','TARC_CONSTANT'),
      ('ET_TERRAIN','MONTHLY'),('HGB_TERRAIN','MONTHLY')]
    for target,g in station.groupby('target'):
        wide=g.pivot(index='station_name',columns='method',values='rmse')
        # Geographic blocks for paired resampling, separate from individual station tests.
        coords=data['meta'].set_index('station_name').loc[wide.index,['lat','lon']].to_numpy()
        coords[:,1]*=np.cos(np.radians(coords[:,0].mean()))
        blocks=KMeans(n_clusters=min(6,len(wide)),n_init=20,random_state=42).fit_predict(coords)
        for new,ref in comparisons:
            if new not in wide or ref not in wide:continue
            delta=wide[ref]-wide[new];delta=delta.dropna();v=delta.to_numpy()
            if not len(v):continue
            p=stats.wilcoxon(v).pvalue if np.any(np.abs(v)>1e-12) else 1.
            # Resample whole geographic groups, keeping within-block dependence.
            boot=[];unique=np.unique(blocks)
            for _ in range(2000):
                choice=rng.choice(unique,len(unique),replace=True)
                ix=np.concatenate([np.flatnonzero(blocks==b) for b in choice]);boot.append(np.nanmean((wide[ref]-wide[new]).to_numpy()[ix]))
            paired.append(dict(target=target,new=new,reference=ref,n_stations=len(v),mean_rmse_gain=v.mean(),
              median_rmse_gain=np.median(v),stations_improved=int((v>0).sum()),stations_worse=int((v<0).sum()),
              wilcoxon_p_naive=p,spatial_block_ci_low=np.quantile(boot,.025),spatial_block_ci_high=np.quantile(boot,.975),
              note='Six-block bootstrap is approximate; overlapping CV training and few blocks limit inference.'))
    tests=pd.DataFrame(paired)
    if len(tests):tests['wilcoxon_q_bh']=bh_adjust(tests.wilcoxon_p_naive)
    for name,df in [('pooled_metrics',pooled),('station_metrics',station),('station_summary',pd.DataFrame(summary)),
       ('paired_comparisons',tests),('rain_detection',pd.DataFrame(det)),('temperature_extremes',pd.DataFrame(extremes)),
       ('annual_diagnostics',pd.DataFrame(annual)),('monthly_metrics',pd.DataFrame(seasons))]:save_table(root,name,df)
    # Trend preservation uses OOF predictions and high-completeness annual records.
    trend=[]
    for keys,g in pd.DataFrame(annual).groupby(['target','method','station_name']):
        if len(g)<10:continue
        target,m,s=keys;v='sum' if target=='Prcp' else 'mean'
        a=stats.theilslopes(g[v+'_obs'],g.year).slope;b=stats.theilslopes(g[v+'_pred'],g.year).slope
        trend.append(dict(target=target,method=m,station_name=s,n_years=len(g),observed_slope_per_decade=a*10,predicted_slope_per_decade=b*10,slope_error_per_decade=(b-a)*10))
    save_table(root,'trend_preservation',pd.DataFrame(trend))
    # Physical consistency before any projection. Never report fit-time reconstructions as validation.
    if {'Tmax','Tmin'}<=set(z.target):
        a=z[z.target.eq('Tmax')];b=z[z.target.eq('Tmin')];viol=[]
        for m in methods:
            if not a[m].notna().any() or not b[m].notna().any():continue
            x=a[['row_id',m]].merge(b[['row_id',m]],on='row_id',suffixes=('_max','_min')).dropna()
            viol.append(dict(method=m,n=len(x),tmax_below_tmin=int((x[m+'_max']<x[m+'_min']).sum())))
        save_table(root,'physical_consistency',pd.DataFrame(viol))
    expected=len(list(split_definitions(data['full'],Config(**json.loads((root/'manifest.json').read_text())['config']),mode)))
    write_json(root/'completion.json',{'expected_folds':expected,'completed_files':len(list(root.glob('*.npz'))),
      'targets':sorted(z.target.unique()),'complete':len(list(root.glob('*.npz')))==expected*len(json.loads((root/'manifest.json').read_text())['targets'])})
    return pd.DataFrame(summary).sort_values(['target','mean_station_rmse'])
