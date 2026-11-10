"""Fixed base estimators and a train-only, terrain-support-gated residual candidate.

TARC is a candidate method, not a claim of established novelty or superiority.
Its gate is chosen with inner station-held-out predictions, never outer labels.
"""
import numpy as np
import pandas as pd
from scipy.spatial.distance import cdist
from sklearn.ensemble import HistGradientBoostingRegressor, ExtraTreesRegressor
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.model_selection import GroupKFold
from .core import LOCAL, TERRAIN, SUPPORT, NEIGH, TARGETS, haversine_matrix

def station_weights(df):
    n=df.groupby('station_name').station_name.transform('size').to_numpy()
    w=1/n;return w/w.mean()

def training_sample(df,cfg):
    if cfg.max_train_rows is None or len(df)<=cfg.max_train_rows:return df.copy()
    # Station-balanced random subsampling WITHIN TRAINING ONLY; this is not random CV.
    names=sorted(df.station_name.unique());quota=cfg.max_train_rows//len(names)
    return pd.concat([g.sample(min(len(g),quota),random_state=cfg.seed) for _,g in df.groupby('station_name')]).sort_values('row_id')

class MonthlyCorrection:
    def __init__(self,precip=False):self.precip=precip
    def fit(self,df,obs,raw):
        self.raw=raw
        if self.precip:
            z=df.groupby(['station_name','month'])[[obs,raw]].mean().groupby('month').mean()
            self.values=(z[obs]/z[raw].clip(lower=.01)).to_dict()
        else:
            z=df.assign(res=df[obs]-df[raw]).groupby(['station_name','month']).res.mean().groupby('month').mean()
            self.values=z.to_dict()
        return self
    def predict(self,df):
        vals=df.month.map(self.values).to_numpy()
        if not np.isfinite(vals).all():raise ValueError('A month is missing from baseline training')
        return df[self.raw].to_numpy()*vals if self.precip else df[self.raw].to_numpy()+vals

class PooledEQM:
    """Pooled monthly empirical quantile mapping transferable without target observations.
    Quantiles use equal station weights; temperature tails use constant additive deltas.
    Precipitation tails use nonnegative ratio extrapolation. This is NOT trend-preserving QDM.
    """
    def fit(self,df,obs,raw,precip=False):
        self.raw=raw;self.precip=precip;self.par={};q=np.linspace(.005,.995,199)
        def wquant(x,w):
            ix=np.argsort(x);x=x[ix];w=w[ix];p=(np.cumsum(w)-.5*w)/sum(w)
            return np.interp(q,p,x)
        for mo,g in df.groupby('month'):
            w=station_weights(g);a=wquant(g[raw].to_numpy(),w);b=wquant(g[obs].to_numpy(),w)
            # Coalesce repeated model quantiles deterministically (dry-day atom).
            tab=pd.DataFrame({'a':a,'b':b}).groupby('a',as_index=False).b.mean()
            self.par[int(mo)]=(tab.a.to_numpy(),tab.b.to_numpy())
        return self
    def predict(self,df):
        out=np.empty(len(df));mo=df.month.to_numpy();x=df[self.raw].to_numpy()
        for m,(a,b) in self.par.items():
            mask=mo==m;v=x[mask];y=np.interp(v,a,b)
            if self.precip:
                y=np.where(v>a[-1],v*b[-1]/max(a[-1],.01),y);y=np.maximum(y,0)
            else:y=np.where(v<a[0],v+b[0]-a[0],np.where(v>a[-1],v+b[-1]-a[-1],y))
            out[mask]=y
        return out

def estimator(kind,cfg):
    if kind=='HGB':
        # Disable sklearn's random internal validation split.
        return HistGradientBoostingRegressor(max_iter=cfg.hgb_iterations,max_leaf_nodes=cfg.hgb_leaves,
            learning_rate=cfg.hgb_learning_rate,min_samples_leaf=25,l2_regularization=1.,
            early_stopping=False,random_state=cfg.seed)
    if kind=='ET':
        return ExtraTreesRegressor(n_estimators=cfg.et_estimators,max_depth=cfg.et_max_depth,
            min_samples_leaf=cfg.et_min_leaf,n_jobs=cfg.n_jobs,random_state=cfg.seed)
    raise ValueError(kind)

class ResidualModel:
    def fit(self,df,obs,raw,features,cfg,kind='HGB',baseline=None):
        self.features=list(features);self.raw=raw;self.baseline=baseline
        self.imputer=SimpleImputer(strategy='median',keep_empty_features=True)
        sampled=training_sample(df,cfg);self.n_train=len(sampled)
        x=self.imputer.fit_transform(sampled[self.features])
        offset=sampled[raw].to_numpy() if baseline is None else baseline.predict(sampled)
        y=sampled[obs].to_numpy()-offset
        self.model=estimator(kind,cfg).fit(x,y,sample_weight=station_weights(sampled))
        return self
    def predict(self,df):
        x=self.imputer.transform(df[self.features]);offset=df[self.raw].to_numpy() if self.baseline is None else self.baseline.predict(df)
        return offset+self.model.predict(x)

class TerrainSupport:
    def fit(self,df):
        z=df[['station_name']+SUPPORT].drop_duplicates('station_name').sort_values('station_name')
        self.names=z.station_name.to_numpy();x=z[SUPPORT].to_numpy(float);x[:,1]=np.log1p(x[:,1])
        self.center=np.median(x,axis=0);self.scale=np.std(x,axis=0);self.scale=np.where(self.scale>1e-8,self.scale,1)
        self.x=(x-self.center)/self.scale
        ds=cdist(self.x,self.x)/np.sqrt(len(SUPPORT));np.fill_diagonal(ds,np.inf)
        self.normalizer=max(float(np.median(np.min(ds,axis=1))),.1)
        return self
    def predict(self,df):
        z=df[['station_name']+SUPPORT].drop_duplicates('station_name');x=z[SUPPORT].to_numpy(float);x[:,1]=np.log1p(x[:,1])
        ds=cdist((x-self.center)/self.scale,self.x)/np.sqrt(len(SUPPORT))
        # Leave self out at known stations too, so production support uses the CV convention.
        ds[z.station_name.to_numpy()[:,None]==self.names[None,:]]=np.inf
        vals=np.min(ds,axis=1)/self.normalizer
        return df.station_name.map(dict(zip(z.station_name,vals))).to_numpy()

def gate_weights(distance,amplitude,bandwidth):
    return amplitude*np.exp(-.5*(np.asarray(distance)/bandwidth)**2)

def select_gates(train,obs,raw,cfg):
    """Inner GroupKFold OOF predictions: equal station contribution to the selection loss."""
    nfold=min(cfg.inner_folds,train.station_name.nunique())
    if nfold<2:raise ValueError('Need at least two training stations for inner selection')
    records=[];fold_log=[]
    splitter=GroupKFold(n_splits=nfold)
    for fold,(tr_idx,va_idx) in enumerate(splitter.split(train,groups=train.station_name)):
        tr=train.iloc[tr_idx];va=train.iloc[va_idx]
        assert not set(tr.station_name)&set(va.station_name)
        base=MonthlyCorrection().fit(tr,obs,raw)
        mdl=ResidualModel().fit(tr,obs,raw,LOCAL+TERRAIN,cfg,baseline=base)
        b=base.predict(va);pred=mdl.predict(va);d=TerrainSupport().fit(tr).predict(va)
        rec=va[['station_name']].copy();rec['error_base']=b-va[obs].to_numpy();rec['increment']=pred-b;rec['distance']=d
        records.append(rec)
        fold_log.append({'inner_fold':fold,'train_stations':sorted(tr.station_name.unique()),
          'validation_stations':sorted(va.station_name.unique()),'n_training_rows_used':mdl.n_train})
    oof=pd.concat(records,ignore_index=True);risk=[]
    for amp in cfg.gate_amplitudes:
        for bandwidth in cfg.gate_bandwidths:
            w=gate_weights(oof.distance,amp,bandwidth)
            err=oof.error_base.to_numpy()+w*oof.increment.to_numpy()
            station_mse=pd.Series(err**2).groupby(oof.station_name).mean()
            risk.append({'amplitude':amp,'bandwidth':bandwidth,'mean_station_rmse':np.sqrt(station_mse).mean()})
    risk=pd.DataFrame(risk)
    # Deterministic ties favour a fixed/full gate, hence lower complexity.
    risk=risk.sort_values(['mean_station_rmse','bandwidth','amplitude'],ascending=[True,False,False])
    selected=risk.iloc[0].to_dict()
    constant=risk[risk.bandwidth.eq(max(cfg.gate_bandwidths))].iloc[0].to_dict()
    return selected,constant,risk,fold_log

def neighbour_features(frame,reanalysis,training_names,k=3):
    """Only ERA5 values, never observed values. Pool excludes outer validation stations/islands."""
    names=sorted(set(training_names));meta=reanalysis[['station_name','lat','lon']].drop_duplicates('station_name').set_index('station_name')
    pools={};out=frame.copy();lookup={}
    for col,nb in [('t2m_max','nb_tmax'),('t2m_min','nb_tmin'),('era5_prcp','nb_prcp')]:
        lookup[col]=reanalysis.pivot(index='date',columns='station_name',values=col)
    for s in frame.station_name.unique():
        candidates=[n for n in names if n!=s]
        ds=haversine_matrix(meta.loc[[s],['lat','lon']],meta.loc[candidates,['lat','lon']])[0]
        pools[s]=[candidates[i] for i in np.argsort(ds,kind='stable')[:k]]
        if len(pools[s])<k:raise ValueError('Insufficient neighbour candidates')
        for col,nb in [('t2m_max','nb_tmax'),('t2m_min','nb_tmin'),('era5_prcp','nb_prcp')]:
            vals=lookup[col][pools[s]].mean(axis=1,skipna=False)
            mask=out.station_name.eq(s);out.loc[mask,nb]=out.loc[mask,'date'].map(vals).to_numpy()
    if out[NEIGH].isna().any().any():raise ValueError('Missing training-pool reanalysis neighbour values')
    return out,pools

def fit_predict_suite(train,test,reanalysis,cfg,target='Tmax',candidate=True):
    obs,raw=TARGETS[target];train=train.dropna(subset=[obs,raw]).copy();test=test.dropna(subset=[obs,raw]).copy()
    assert not set(train.row_id)&set(test.row_id)
    if set(train.station_name)&{'Kutubdia','Sandwip'}:raise AssertionError('Island in training')
    preds={'RAW':test[raw].to_numpy()};models={};info={'n_train_available':len(train),'n_test':len(test),'training_stations':sorted(train.station_name.unique())}
    base=MonthlyCorrection(target=='Prcp').fit(train,obs,raw);models['MONTHLY']=base;preds['MONTHLY']=base.predict(test)
    eqm=PooledEQM().fit(train,obs,raw,target=='Prcp');models['EQM']=eqm;preds['EQM']=eqm.predict(test)
    for name,features,kind in [('HGB_LOCAL',LOCAL,'HGB'),('HGB_TERRAIN',LOCAL+TERRAIN,'HGB')]+(
      [('ET_LOCAL',LOCAL,'ET'),('ET_TERRAIN',LOCAL+TERRAIN,'ET')] if cfg.include_et else []):
        mdl=ResidualModel().fit(train,obs,raw,features,cfg,kind=kind);models[name]=mdl;preds[name]=mdl.predict(test)
        info[name+'_n_training_rows_used']=mdl.n_train
    # A parametric baseline trained under the exact same outer split.
    sample=training_sample(train,cfg);features=LOCAL+TERRAIN
    ridge=make_pipeline(SimpleImputer(strategy='median'),StandardScaler(),Ridge(alpha=10.))
    ridge.fit(sample[features],sample[obs]-sample[raw],ridge__sample_weight=station_weights(sample))
    preds['RIDGE']=test[raw].to_numpy()+ridge.predict(test[features]);models['RIDGE']=ridge
    if cfg.include_neighbours and cfg.include_et:
        # Temporal test may share station names; this is explicitly a different validation question.
        trn,pools=neighbour_features(train,reanalysis,train.station_name.unique())
        ten,testpools=neighbour_features(test,reanalysis,train.station_name.unique())
        mdl=ResidualModel().fit(trn,obs,raw,LOCAL+TERRAIN+NEIGH,cfg,kind='ET')
        models['ET_NEIGH']=mdl;preds['ET_NEIGH']=mdl.predict(ten)
        info['neighbour_pool']=pools;info['test_neighbour_pool']=testpools
    if target=='Tmax' and candidate:
        selected,constant,risk,inner=select_gates(train,obs,raw,cfg)
        mdl=ResidualModel().fit(train,obs,raw,LOCAL+TERRAIN,cfg,baseline=base)
        p=mdl.predict(test);b=base.predict(test);support=TerrainSupport().fit(train);d=support.predict(test)
        preds['TARC_UNGATED']=p
        preds['TARC_CONSTANT']=b+constant['amplitude']*(p-b)
        weights=gate_weights(d,selected['amplitude'],selected['bandwidth'])
        preds['TARC_SUPPORT']=b+weights*(p-b)
        models.update(TARC=mdl,TARC_SUPPORT_GEOMETRY=support)
        info.update(gate=selected,constant_gate=constant,inner_folds=inner,gate_risk=risk.to_dict('records'))
        test=test.assign(terrain_distance=d,gate_weight=weights)
    if target=='Prcp':
        info['negative_predictions_clipped']={k:int((v<0).sum()) for k,v in preds.items()}
        preds={k:np.maximum(v,0) for k,v in preds.items()}
    return test,preds,info,models
