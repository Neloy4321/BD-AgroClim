from __future__ import annotations
import hashlib, json, platform
from dataclasses import dataclass, asdict
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats
from scipy.spatial.distance import cdist

FILES = {
    'bmd':'bmd_clean_daily.csv', 'era':'era5land_stations_daily_v2.csv',
    'meta':'station_metadata_final.csv', 'terrain':'terrain_full.csv',
    'power':'NASA_POWER_Climate_Data_Bangladesh_2000_2026.csv',
    'legacy_skill':'terrain_skill_merged_v2.csv', 'yield':'yield_panel_final.csv'}
ISLANDS = ('Kutubdia','Sandwip')
TARGETS = {'Tmax':('obs_tmax','t2m_max'), 'Tmin':('obs_tmin','t2m_min'),
           'Prcp':('obs_prcp','era5_prcp')}
LOCAL = ['t2m_max','t2m_min','era5_prcp','ssrd','ws2','rh_mean','vpd','swvl1','sp',
         'doy_sin','doy_cos','month']
TERRAIN = ['land_frac_9km','elev_std_9km','roughness_5km','elev_dem',
           'tpi_5km','northness','eastness','dist_water_km']
SUPPORT = ['land_frac_9km','elev_std_9km']
NEIGH = ['nb_tmax','nb_tmin','nb_prcp']

@dataclass
class Config:
    seed: int = 42
    n_jobs: int = 4
    hgb_iterations: int = 120
    hgb_leaves: int = 15
    hgb_learning_rate: float = 0.08
    et_estimators: int = 100
    et_max_depth: int = 20
    et_min_leaf: int = 5
    max_train_rows: int | None = 50000
    inner_folds: int = 4
    study_start: str = '2000-01-01'
    study_end: str = '2023-12-31'
    temporal_cutoff: str = '2015-12-31'
    include_et: bool = True
    include_neighbours: bool = True
    gate_amplitudes: tuple = (0., .25, .5, .75, 1.)
    gate_bandwidths: tuple = (.5, 1., 2., 4., 1000000.)
    protocol: str = 'paper1-revision-v2'

def sha256(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(1024*1024), b''): h.update(b)
    return h.hexdigest()

def write_json(path, obj):
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    Path(path).write_text(json.dumps(obj,indent=2,default=str,ensure_ascii=False))

def save_table(out, name, df):
    Path(out).mkdir(parents=True,exist_ok=True)
    df.to_csv(Path(out)/f'{name}.csv',index=False)
    return df

def resolve_inputs(root):
    root=Path(root); resolved={}
    for key,name in FILES.items():
        matches=[root/name] if (root/name).is_file() else sorted(root.rglob(name))
        if len(matches)!=1:
            raise ValueError(f'{name}: expected exactly one file below {root}; found {matches}')
        resolved[key]=matches[0]
    return resolved

def assert_unique(df, keys, label):
    if df.duplicated(keys).any(): raise ValueError(f'Duplicate {label} keys: {keys}')

def load_inputs(root, out=None):
    paths=resolve_inputs(root)
    d={k:pd.read_csv(p) for k,p in paths.items()}
    d['bmd']['date']=pd.to_datetime(d['bmd']['date'],errors='raise')
    d['era']['date']=pd.to_datetime(d['era']['date'],errors='raise')
    d['power']=d['power'].rename(columns={'Date':'date'})
    d['power']['date']=pd.to_datetime(d['power']['date'],errors='raise')
    for key in ['bmd','era']: assert_unique(d[key],['station_name','date'],key)
    for key in ['meta','terrain','legacy_skill']: assert_unique(d[key],['station_name'],key)
    assert_unique(d['power'],['LAT','LON','date'],'POWER')
    power_num=d['power'].select_dtypes('number').columns
    sentinel=(d['power'][power_num]==-999).sum().to_dict()
    d['power'][power_num]=d['power'][power_num].replace(-999,np.nan)
    long=d['bmd'][d['bmd'].record_type.eq('long')].copy()
    names=set(d['meta'].station_name)
    if set(long.station_name)!=names or set(d['era'].station_name)!=names:
        raise ValueError('Station identity mismatch')
    if set(d['terrain'].station_name)!=names: raise ValueError('Terrain identity mismatch')
    obs=long.rename(columns={'tmax':'obs_tmax','tmin':'obs_tmin','prcp':'obs_prcp'})
    full=d['era'].rename(columns={'prcp':'era5_prcp'}).merge(
        d['meta'],on='station_name',how='left',validate='many_to_one').merge(
        d['terrain'].drop(columns='point_id'),on='station_name',how='left',validate='many_to_one').merge(
        obs,on=['station_name','date'],how='left',validate='one_to_one')
    full=full.sort_values(['station_name','date']).reset_index(drop=True)
    full['row_id']=np.arange(len(full))
    full['month']=full.date.dt.month
    full['year']=full.date.dt.year
    full['doy_sin']=np.sin(2*np.pi*(full.date.dt.dayofyear-1)/365.25)
    full['doy_cos']=np.cos(2*np.pi*(full.date.dt.dayofyear-1)/365.25)
    full['landscape']=np.where(full.elev_std_9km>=12,'Hill-adjacent',
                        np.where(full.land_frac_9km<.8,'Coastal/island','Interior plain'))
    if (full.era5_prcp<0).any() or (full.obs_prcp<0).any():
        raise ValueError('Negative source precipitation: inspect rather than silently clip')
    if (full.t2m_max<full.t2m_min).any() or (full.obs_tmax<full.obs_tmin).any():
        raise ValueError('Source Tmax < Tmin')
    d['full']=full; d['long']=long; d['paths']=paths; d['power_sentinels']=sentinel
    if out:
        import sklearn, scipy
        write_json(Path(out)/'input_manifest.json',{
            'files':{k:{'filename':p.name,'sha256':sha256(p),'bytes':p.stat().st_size} for k,p in paths.items()},
            'versions':{'python':platform.python_version(),'numpy':np.__version__,
                        'pandas':pd.__version__,'scipy':scipy.__version__,'sklearn':sklearn.__version__}})
    return d

def metrics(sim,obs,temperature=False):
    a=np.asarray(sim,float); b=np.asarray(obs,float)
    keep=np.isfinite(a)&np.isfinite(b); a=a[keep];b=b[keep]
    if len(a)<3:return dict(n=len(a),r=np.nan,bias=np.nan,mae=np.nan,rmse=np.nan,nse=np.nan,kge=np.nan)
    r=np.corrcoef(a,b)[0,1] if a.std()>0 and b.std()>0 else np.nan
    err=a-b; var=b.var()
    # KGE temperature mean ratio is computed in Kelvin, avoiding arbitrary Celsius-origin dependence.
    shift=273.15 if temperature else 0
    beta=(a.mean()+shift)/(b.mean()+shift) if b.mean()+shift else np.nan
    alpha=a.std()/b.std() if b.std() else np.nan
    return dict(n=len(a),r=r,bias=err.mean(),mae=np.abs(err).mean(),rmse=np.sqrt(np.mean(err**2)),
                nse=1-np.mean(err**2)/var if var else np.nan,
                kge=1-np.sqrt((r-1)**2+(alpha-1)**2+(beta-1)**2))

def detection(sim,obs,threshold):
    a=np.asarray(sim,float);b=np.asarray(obs,float);m=np.isfinite(a)&np.isfinite(b)
    f=a[m]>=threshold;o=b[m]>=threshold
    h=int((f&o).sum());miss=int((~f&o).sum());fa=int((f&~o).sum());cn=int((~f&~o).sum())
    div=lambda x,y:x/y if y else np.nan
    return dict(threshold=threshold,n=int(m.sum()),H=h,M=miss,F=fa,C=cn,
      POD=div(h,h+miss),FAR=div(fa,h+fa),CSI=div(h,h+miss+fa),
      HSS=div(2*(h*cn-fa*miss),(h+miss)*(miss+cn)+(h+fa)*(fa+cn)))

def haversine_matrix(a,b):
    a=np.radians(np.asarray(a));b=np.radians(np.asarray(b))
    v=np.sin((a[:,None,0]-b[None,:,0])/2)**2+np.cos(a[:,None,0])*np.cos(b[None,:,0])*np.sin((a[:,None,1]-b[None,:,1])/2)**2
    return 6371*2*np.arcsin(np.sqrt(np.clip(v,0,1)))

def bh_adjust(p):
    p=np.asarray(p,float);q=np.full(len(p),np.nan);m=np.isfinite(p)
    vals=p[m];order=np.argsort(vals);adj=vals[order]*len(vals)/np.arange(1,len(vals)+1)
    adj=np.minimum.accumulate(adj[::-1])[::-1];tmp=np.empty(len(vals));tmp[order]=np.clip(adj,0,1);q[m]=tmp
    return q

def foundation(data,out,cfg=Config()):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    full=data['full'];paired=full[full.date.between(cfg.study_start,cfg.study_end)].copy()
    cells=data['power'][['LAT','LON']].drop_duplicates().reset_index(drop=True)
    meta=data['meta'].copy();dist=haversine_matrix(meta[['lat','lon']],cells[['LAT','LON']]);ind=dist.argmin(1)
    meta['pw_lat']=cells.LAT.to_numpy()[ind];meta['pw_lon']=cells.LON.to_numpy()[ind]
    meta['pw_distance_km']=dist[np.arange(len(meta)),ind]
    save_table(out,'station_power_map',meta)
    pw=data['power'][['LAT','LON','date','T2M_MAX','T2M_MIN','PRECTOTCORR']].rename(
        columns={'T2M_MAX':'pw_tmax','T2M_MIN':'pw_tmin','PRECTOTCORR':'pw_prcp'})
    paired=paired.merge(meta[['station_name','pw_lat','pw_lon']],on='station_name',validate='many_to_one').merge(
        pw,left_on=['pw_lat','pw_lon','date'],right_on=['LAT','LON','date'],how='left',validate='many_to_one')
    rows=[];det=[];per=[]
    for lab,(obs,raw) in TARGETS.items():
        pwcol={'Tmax':'pw_tmax','Tmin':'pw_tmin','Prcp':'pw_prcp'}[lab]
        for mode in ['all_available','common_product_rows']:
            g=paired if mode=='all_available' else paired.dropna(subset=[obs,raw,pwcol])
            for prod,col in [('ERA5-Land',raw),('NASA POWER',pwcol)]:
                rows.append(dict(variable=lab,product=prod,sample=mode,**metrics(g[col],g[obs],lab!='Prcp')))
                for st,z in g.groupby('station_name'):
                    per.append(dict(station_name=st,variable=lab,product=prod,sample=mode,**metrics(z[col],z[obs],lab!='Prcp')))
                if lab=='Prcp':
                    for t in [1,10,20,50]:det.append(dict(product=prod,sample=mode,**detection(g[col],g[obs],t)))
    save_table(out,'baseline_metrics',pd.DataFrame(rows));save_table(out,'baseline_station_metrics',pd.DataFrame(per))
    save_table(out,'baseline_rain_detection',pd.DataFrame(det))
    inventory=[];ndays=len(pd.date_range(cfg.study_start,cfg.study_end))
    for s,g in data['long'].groupby('station_name'):
        r=dict(station_name=s,expected_days=ndays,source_rows=len(g))
        for v in ['tmax','tmin','prcp']:
            valid=g.dropna(subset=[v]);r[v+'_n']=len(valid);r[v+'_complete_pct']=100*len(valid)/ndays
            r[v+'_first']=str(valid.date.min().date());r[v+'_last']=str(valid.date.max().date())
        eg=full[full.station_name.eq(s)];r.update(era_first=str(eg.date.min().date()),era_last=str(eg.date.max().date()),
               era_source=eg.era5_source.iloc[0],landscape=eg.landscape.iloc[0])
        inventory.append(r)
    inv=pd.DataFrame(inventory).merge(data['meta'],on='station_name').merge(data['terrain'][['station_name']+SUPPORT],on='station_name')
    save_table(out,'station_inventory',inv)
    # Use valid observations, not calendar-completed row counts, for availability.
    av=paired.assign(ym=paired.date.dt.to_period('M').astype(str)).groupby(['station_name','ym'])[['obs_tmax','obs_tmin','obs_prcp']].count().reset_index()
    save_table(out,'monthly_valid_counts',av)
    # Training-period lag diagnostic on identical rows across candidate lags; NEVER auto-shift dates.
    lagrows=[]
    for s,g in paired[paired.date.le(cfg.temporal_cutoff)].groupby('station_name'):
        g=g.set_index('date').asfreq('D')
        for lab,(obs,raw) in TARGETS.items():
            pwcol={'Tmax':'pw_tmax','Tmin':'pw_tmin','Prcp':'pw_prcp'}[lab]
            for product,col in [('ERA5-Land',raw),('NASA POWER',pwcol)]:
                shifts=pd.DataFrame({lag:g[col].shift(lag) for lag in [-2,-1,0,1,2]})
                mask=shifts.notna().all(axis=1)&g[obs].notna()
                for lag in shifts:
                    lagrows.append(dict(station_name=s,variable=lab,product=product,lag_days=lag,
                                        **metrics(shifts.loc[mask,lag],g.loc[mask,obs],lab!='Prcp')))
    save_table(out,'training_lag_sensitivity',pd.DataFrame(lagrows))
    quality={
      'long_stations':int(data['long'].station_name.nunique()),'short_stations_excluded':int(data['bmd'].query("record_type=='short'").station_name.nunique()),
      'power_cells':len(cells),'power_lat_step':sorted(set(np.diff(np.sort(cells.LAT.unique())))),
      'power_lon_step':sorted(set(np.diff(np.sort(cells.LON.unique())))),
      'power_minus999_counts':data['power_sentinels'],'metadata_coord_source_counts':data['meta'].coord_source.value_counts().to_dict(),
      'paired_rows':len(paired),'era_end':str(full.date.max().date()),
      'yield_rows':len(data['yield']),'yield_analysis_ready_rows':int(data['yield'].analysis_ready.sum()),
      'unresolved':['All coordinates labelled draft; verify authoritative coordinates and extraction consistency.',
      'BMD observing-day windows and POWER API time-standard unavailable in supplied CSVs.',
      'Pre-QC observations and removal log unavailable; extreme-event deletion cannot be audited or reversed.',
      'GEE terrain geometry, water-mask threshold and resampling provenance unavailable.',
      'BMD redistribution terms and derived-data licensing must be documented before public release.'],
      'disclosure':'Islands were inspected in the earlier paper; they are spatially excluded diagnostics, not a fresh blind test.'}
    write_json(out/'quality_audit.json',quality)
    save_table(out,'yield_audit',pd.DataFrame([dict(rows=len(data['yield']),ready_rows=int(data['yield'].analysis_ready.sum()),
        duplicate_panel_keys=int(data['yield'].duplicated(['district','season','harvest_year']).sum()),
        use='Inventory only; yield is not independent weather ground truth and is excluded from algorithm selection.')]))
    paired.to_pickle(out/'paired.pkl')
    homogeneity_diagnostics(paired,out,cfg)
    return pd.DataFrame(rows)

def homogeneity_diagnostics(paired,out,cfg):
    rng=np.random.default_rng(cfg.seed);rows=[];cache={}
    for s,g in paired.groupby('station_name'):
        for lab,(obs,raw) in TARGETS.items():
            for series,col in [('observation',obs),('obs_minus_era',None)]:
                a=g[['date',obs,raw]].copy();a['value']=a[obs] if col else a[obs]-a[raw]
                a['year']=a.date.dt.year
                ann=a.groupby('year').value.agg(['mean','sum','count'])
                expected=np.array([366 if pd.Timestamp(f'{y}-12-31').is_leap_year else 365 for y in ann.index])
                ann=ann[ann['count'].to_numpy()/expected >= (.95 if lab=='Prcp' else .90)]
                v=ann['sum' if lab=='Prcp' and series=='observation' else 'mean'].to_numpy();n=len(v)
                if n<10 or np.std(v)==0:continue
                u=2*np.cumsum(stats.rankdata(v))-np.arange(1,n+1)*(n+1);k=np.argmax(np.abs(u))
                pp=min(1,2*np.exp(-6*u[k]**2/(n**3+n**2)))
                z=(v-v.mean())/v.std();a1=np.arange(1,n);c=np.cumsum(z)[:-1]
                ts=c*c/a1+(c[-1]+z[-1]-c)**2/(n-a1);sn=float(ts.max())
                if n not in cache:
                    null=rng.normal(size=(2000,n));null=(null-null.mean(1)[:,None])/null.std(1)[:,None]
                    c0=np.cumsum(null,axis=1)[:,:-1]
                    cache[n]=(c0*c0/a1+c0*c0/(n-a1)).max(1)
                sp=(1+np.sum(cache[n]>=sn))/(len(cache[n])+1)
                rows.append(dict(station_name=s,variable=lab,series=series,n_complete_years=n,
                      pettitt_p_approx=pp,pettitt_break_year=int(ann.index[k]),snht_stat=sn,snht_p_iid_mc=sp))
    r=pd.DataFrame(rows)
    for c in ['pettitt_p_approx','snht_p_iid_mc']:r[c+'_fdr']=bh_adjust(r[c])
    r['interpretation']='Exploratory break screen; IID null, climate trends and autocorrelation limit inference. No automatic adjustment.'
    save_table(out,'homogeneity_screen',r)

def ols_fit(x,y):
    x=np.column_stack([np.ones(len(x)),np.asarray(x,float)]);y=np.asarray(y,float)
    beta=np.linalg.lstsq(x,y,rcond=None)[0];err=y-x@beta;n,p=x.shape;sse=err@err;tss=np.sum((y-y.mean())**2)
    inv=np.linalg.pinv(x.T@x);h=np.sum((x@inv)*x,axis=1)
    meat=x.T@((err/np.clip(1-h,1e-8,None))[:,None]**2*x)
    se=np.sqrt(np.maximum(0,np.diag(inv@meat@inv)));pv=2*stats.t.sf(np.abs(beta/np.maximum(se,1e-12)),max(n-p,1))
    cooks=err**2/max(sse/(n-p),1e-12)/p*h/np.maximum((1-h)**2,1e-12)
    ll=n*np.log(max(sse/n,1e-15))+n*(1+np.log(2*np.pi))
    return dict(beta=beta,se=se,p=pv,cooks=cooks,R2=1-sse/tss,adjR2=1-(sse/(n-p))/(tss/(n-1)),
                AIC=ll+2*(p+1),AICc=ll+2*(p+1)+2*(p+1)*(p+2)/(n-p-2))

def terrain_diagnostics(data,out):
    out=Path(out);paired=pd.read_pickle(out/'paired.pkl');rows=[]
    for s,g in paired.groupby('station_name'):
        r={'station_name':s}
        for lab,(obs,raw) in TARGETS.items():
            z=metrics(g[raw],g[obs],lab!='Prcp');r.update({lab.lower()+'_'+k:z[k] for k in ['r','bias','rmse']})
        rows.append(r)
    sk=pd.DataFrame(rows).merge(data['terrain'],on='station_name').merge(data['meta'][['station_name','lat','lon','elev_m']],on='station_name')
    save_table(out,'station_skill_recomputed',sk)
    legacy=data['legacy_skill'];checks=[]
    for c in ['tmax_r','tmax_bias','tmax_rmse','tmin_r','prcp_r']:
        z=sk[['station_name',c]].merge(legacy[['station_name',c]],on='station_name',suffixes=('_new','_legacy'))
        z['difference']=z[c+'_new']-z[c+'_legacy'];z['metric']=c;checks.append(z[['station_name','metric','difference']])
    save_table(out,'legacy_skill_comparison',pd.concat(checks))
    tests=[]
    for tv in TERRAIN+['slope_mean_9km']:
        for sv in ['tmax_bias','tmax_r','tmin_r','prcp_r']:
            rho,p=stats.spearmanr(sk[tv],sk[sv],nan_policy='omit')
            tests.append(dict(terrain=tv,skill=sv,n=len(sk),rho=rho,p=p))
    corr=pd.DataFrame(tests);corr['q_bh']=bh_adjust(corr.p);save_table(out,'terrain_correlations_fdr',corr)
    sets={'land_only':['land_frac_9km'],'land_relief':SUPPORT,
          'land_relief_slope':SUPPORT+['slope_mean_9km'],
          'land_relief_slope_elev_distance':SUPPORT+['slope_mean_9km','elev_dem','dist_water_km'],
          'conventional':['lat','elev_m'],'conventional_land_relief':['lat','elev_m']+SUPPORT}
    fits=[];coefs=[];loo=[]
    for name,cols in sets.items():
        x=sk[cols].to_numpy();y=sk.tmax_bias.to_numpy();r=ols_fit(x,y)
        pred=[]
        for i in range(len(sk)):
            keep=np.arange(len(sk))!=i;b=ols_fit(x[keep],y[keep])['beta'];pred.append(np.r_[1,x[i]]@b)
        pred=np.asarray(pred);fits.append(dict(model=name,predictors=' + '.join(cols),n=len(sk),k=len(cols),
          **{k:r[k] for k in ['R2','adjR2','AIC','AICc']},LOSO_RMSE=np.sqrt(np.mean((pred-y)**2)),
          LOSO_R2=1-np.sum((pred-y)**2)/np.sum((y-y.mean())**2)))
        for term,b,se,p in zip(['intercept']+cols,r['beta'],r['se'],r['p']):
            coefs.append(dict(model=name,term=term,coefficient=b,hc3_se=se,p_hc3=p))
        for s,a,b,c in zip(sk.station_name,y,pred,r['cooks']):loo.append(dict(model=name,station_name=s,observed_bias=a,predicted_bias=b,cooks_distance=c))
    f=pd.DataFrame(fits)
    if (np.diff(f.iloc[:4].R2)<-1e-10).any():raise AssertionError('Nested OLS R2 decreased')
    save_table(out,'terrain_regression',f);save_table(out,'terrain_coefficients_hc3',pd.DataFrame(coefs));save_table(out,'terrain_loo_influence',pd.DataFrame(loo))
    # Influence sensitivity; disclose all deletions instead of selecting the strongest fit.
    sens=[]
    for excluded in [('none',[]),('islands',list(ISLANDS))]+[(s,[s]) for s in sk.station_name]:
        z=sk[~sk.station_name.isin(excluded[1])];r=ols_fit(z[SUPPORT],z.tmax_bias)
        sens.append(dict(excluded=excluded[0],n=len(z),R2=r['R2'],land_coefficient=r['beta'][1],relief_coefficient=r['beta'][2]))
    save_table(out,'terrain_influence_sensitivity',pd.DataFrame(sens))
    return f
