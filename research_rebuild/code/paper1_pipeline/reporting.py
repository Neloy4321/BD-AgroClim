from pathlib import Path
import json,pickle
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from threadpoolctl import threadpool_limits
from .core import Config,ISLANDS,TARGETS,LOCAL,TERRAIN,NEIGH,save_table,write_json,metrics
from .models import ResidualModel,MonthlyCorrection,PooledEQM,TerrainSupport,select_gates,gate_weights,neighbour_features
from .experiments import load_predictions

def make_figures(data,out,mode='loso'):
    out=Path(out);figdir=out/'figures';figdir.mkdir(exist_ok=True)
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'savefig.dpi':220})
    def save(fig,name):
        fig.tight_layout();fig.savefig(figdir/f'{name}.png',bbox_inches='tight');fig.savefig(figdir/f'{name}.pdf',bbox_inches='tight');plt.close(fig)
    meta=data['full'][['station_name','lat','lon','elev_m','era5_source']].drop_duplicates('station_name')
    fig,ax=plt.subplots(figsize=(7,8));sc=ax.scatter(meta.lon,meta.lat,c=meta.elev_m,cmap='viridis',s=45,edgecolor='black',lw=.4)
    for _,r in meta.iterrows():ax.annotate(r.station_name,(r.lon,r.lat),fontsize=5,xytext=(3,2),textcoords='offset points')
    isl=meta[meta.station_name.isin(ISLANDS)];ax.scatter(isl.lon,isl.lat,facecolors='none',edgecolors='#d55e00',s=110,label='Focal-filled')
    ax.set(xlabel='Longitude (degrees E)',ylabel='Latitude (degrees N)',title='Station coordinates supplied by authors (verification pending)');ax.legend();fig.colorbar(sc,ax=ax,label='Station elevation (m)');save(fig,'F1_station_locations')
    av=pd.read_csv(out/'monthly_valid_counts.csv')
    fig,axs=plt.subplots(1,3,figsize=(15,8),sharey=True)
    for ax,c,lab in zip(axs,['obs_tmax','obs_tmin','obs_prcp'],['Tmax','Tmin','Precipitation']):
        p=av.pivot(index='station_name',columns='ym',values=c).fillna(0)
        im=ax.imshow(p,aspect='auto',cmap='viridis',vmin=0,vmax=31,interpolation='nearest');ix=np.arange(0,len(p.columns),48)
        ax.set_xticks(ix,p.columns[ix].str[:4],rotation=45);ax.set_title(lab);ax.set_xlabel('Year')
    axs[0].set_yticks(np.arange(len(p)),p.index,fontsize=6);fig.colorbar(im,ax=axs.tolist(),label='Valid observed days / month',fraction=.02,pad=.02)
    # Explicit layout avoids overlapping shared colorbar.
    fig.subplots_adjust(right=.88,bottom=.12,wspace=.08);fig.savefig(figdir/'F2_observation_availability.png',bbox_inches='tight');plt.close(fig)
    sk=pd.read_csv(out/'station_skill_recomputed.csv');fig,axs=plt.subplots(1,2,figsize=(11,4))
    for ax,x,y,lab in [(axs[0],'land_frac_9km','tmax_bias','Mean Tmax bias (C)'),(axs[1],'elev_std_9km','tmax_r','Tmax correlation')]:
        ax.scatter(sk[x],sk[y],c='#0072b2',edgecolor='white',s=40)
        b=np.polyfit(sk[x],sk[y],1);xs=np.linspace(sk[x].min(),sk[x].max(),100);ax.plot(xs,np.polyval(b,xs),color='black',lw=1)
        ax.set(xlabel=x,ylabel=lab,title='Exploratory station-level association (n=36)')
    save(fig,'F3_terrain_associations')
    root=out/'experiments'/mode
    if not (root/'station_metrics.csv').exists():return sorted(figdir.glob('*.png'))
    sm=pd.read_csv(root/'station_metrics.csv');z=load_predictions(data,out,mode)
    for target,g in sm.groupby('target'):
        order=g.groupby('method').rmse.mean().sort_values().index.tolist();fig,ax=plt.subplots(figsize=(11,5))
        ax.boxplot([g[g.method.eq(m)].rmse for m in order],tick_labels=order,showfliers=True)
        rng=np.random.default_rng(42)
        for i,m in enumerate(order):
            v=g[g.method.eq(m)].rmse;ax.scatter(np.full(len(v),i+1)+rng.uniform(-.12,.12,len(v)),v,s=9,alpha=.55)
        ax.tick_params(axis='x',labelrotation=45);ax.set(ylabel='Station RMSE (mm/day)' if target=='Prcp' else 'Station RMSE (C)',
            title=f'{target}: {mode} station distributions (identical evaluation rows)');save(fig,f'F4_{mode}_{target}_station_rmse')
    g=sm[sm.target.eq('Tmax')];wide=g.pivot(index='station_name',columns='method',values='rmse')
    ref='ET_TERRAIN' if 'ET_TERRAIN' in wide else 'HGB_TERRAIN'
    if 'TARC_SUPPORT' in wide:
        d=(wide[ref]-wide.TARC_SUPPORT).sort_values();fig,ax=plt.subplots(figsize=(10,7))
        ax.barh(d.index,d,color=np.where(d>=0,'#009e73','#d55e00'));ax.axvline(0,color='black',lw=.8)
        ax.tick_params(axis='y',labelsize=7);ax.set(xlabel=f'{ref} RMSE minus candidate RMSE (C)',title='Candidate improvement and degradation by station');save(fig,'F5_candidate_station_gains')
    fig,axs=plt.subplots(2,1,figsize=(11,6))
    for ax,station in zip(axs,['Ishurdi',"Cox's Bazar"]):
        g=z[z.target.eq('Tmax')&z.station_name.eq(station)].set_index('date')
        for m,col in [('observed','black'),('RAW','#d55e00'),(ref,'#0072b2')]:
            if m in g:
                v=g[m].resample('MS').mean();ax.plot(v.index,v,label=m,color=col,lw=.8)
        ax.set(title=f'{station}: held-out monthly means',ylabel='Tmax (C)');ax.legend(fontsize=8,ncol=3)
    save(fig,'F6_actual_oof_time_series')
    for filename,title in [('rain_detection','Rainfall'),('temperature_extremes','Temperature')]:
        path=root/f'{filename}.csv'
        if path.stat().st_size<10:continue
        det=pd.read_csv(path)
        if len(det)==0:continue
        for target,g in det.groupby('target'):
            fig,axs=plt.subplots(1,3,figsize=(12,4))
            for ax,score in zip(axs,['POD','FAR','CSI']):
                for m in ['RAW','MONTHLY','EQM','HGB_TERRAIN',ref]:
                    v=g[g.method.eq(m)]
                    if len(v):ax.plot(v.threshold,v[score],marker='o',label=m)
                ax.set(xlabel='Threshold',ylabel=score,ylim=(0,1),title=f'{target} {score}')
            axs[-1].legend(fontsize=7);save(fig,f'F7_{target}_detection')
    # Island annotations are generated from the SAME prediction-derived table.
    ip=out/'experiments/islands/station_metrics.csv'
    if ip.exists():
        g=pd.read_csv(ip).query("target=='Tmax'");w=g.pivot(index='station_name',columns='method',values='rmse');fig,ax=plt.subplots(figsize=(8,5))
        x=np.arange(len(w));ax.bar(x-.18,w.RAW,width=.36,label='RAW');ax.bar(x+.18,w[ref],width=.36,label=ref)
        for i,s in enumerate(w.index):ax.text(i,w.loc[s,'RAW']+.05,f'{100*(1-w.loc[s,ref]/w.loc[s,"RAW"]):.1f}% reduction',ha='center')
        ax.set_xticks(x,w.index);ax.set(ylabel='Tmax RMSE (C)',title='Previously inspected island transfer diagnostics');ax.legend();save(fig,'F8_islands_consistent_metrics')
    return sorted(figdir.glob('*.png'))

def reconstruct(data,out,cfg=Config(),methods=None,save_models=False):
    """Refit exact evaluated specifications. Output is a research candidate, not a public release.
    OOF values are separately named; refit values are never evaluated as held-out predictions.
    """
    out=Path(out);root=out/'reconstruction';root.mkdir(exist_ok=True)
    full=data['full'];native=~full.station_name.isin(ISLANDS)
    train=full[native&full.date.between(cfg.study_start,cfg.study_end)]
    if methods is None:methods={'Tmax':'ET_TERRAIN' if cfg.include_et else 'HGB_TERRAIN',
                               'Tmin':'HGB_TERRAIN','Prcp':'HGB_TERRAIN'}
    result=full[['row_id','station_name','date','lat','lon','era5_source','t2m_max','t2m_min','era5_prcp']].copy()
    details={};oof=load_predictions(data,out,'loso') if (out/'experiments/loso').exists() else None
    with threadpool_limits(limits=cfg.n_jobs):
        for target,(obs,raw) in TARGETS.items():
            name=methods[target];tr=train.dropna(subset=[obs,raw]);base=MonthlyCorrection(target=='Prcp').fit(tr,obs,raw)
            if name in ['HGB_TERRAIN','ET_TERRAIN','HGB_LOCAL','ET_LOCAL']:
                feats=LOCAL+TERRAIN if name.endswith('TERRAIN') else LOCAL
                mdl=ResidualModel().fit(tr,obs,raw,feats,cfg,kind=name.split('_')[0]);pred=mdl.predict(full)
            elif name=='MONTHLY':mdl=base;pred=base.predict(full)
            elif name=='EQM':mdl=PooledEQM().fit(tr,obs,raw,target=='Prcp');pred=mdl.predict(full)
            elif name=='TARC_SUPPORT' and target=='Tmax':
                selected,_,risk,inner=select_gates(tr,obs,raw,cfg)
                mdl=ResidualModel().fit(tr,obs,raw,LOCAL+TERRAIN,cfg,baseline=base);support=TerrainSupport().fit(tr)
                b=base.predict(full);pred=b+gate_weights(support.predict(full),selected['amplitude'],selected['bandwidth'])*(mdl.predict(full)-b)
                details['production_gate']=selected
                if save_models:
                    with open(root/'Tmax_gate_support.pkl','wb') as f:pickle.dump({'support':support,'gate':selected},f)
            else:raise ValueError(f'Production method not supported: {target} {name}')
            if target=='Prcp':pred=np.maximum(pred,0)
            tag=target.lower();result[tag+'_corrected_refit']=pred
            result[tag+'_observation_available']=full[obs].notna().to_numpy()
            result[tag+'_corrected_oof']=np.nan
            if oof is not None:
                z=oof[oof.target.eq(target)]
                if name in z:result[tag+'_corrected_oof']=result.row_id.map(z.set_index('row_id')[name])
            details[target]={'method':name,'training_rows_available':len(tr),'training_rows_used':getattr(mdl,'n_train',len(tr)),
                             'training_end':str(tr.date.max().date())}
            if save_models:
                with open(root/f'{target}_model.pkl','wb') as f:pickle.dump(mdl,f)
    # Keep unprojected predictions and provide explicitly named physical projection.
    cross=result.tmax_corrected_refit<result.tmin_corrected_refit
    middle=(result.tmax_corrected_refit+result.tmin_corrected_refit)/2
    result['temperature_projection_applied']=cross
    result['tmax_corrected_physical']=np.where(cross,middle,result.tmax_corrected_refit)
    result['tmin_corrected_physical']=np.where(cross,middle,result.tmin_corrected_refit)
    result['within_observation_study_period']=result.date.between(cfg.study_start,cfg.study_end)
    result['post2023_unvalidated']=result.date.gt(cfg.study_end)
    result['partial_year']=result.date.dt.year.eq(result.date.max().year)
    result['focal_filled']=result.era5_source.eq('focal_filled')
    result.to_csv(root/'bd_agroclim_candidate.csv.gz',index=False,float_format='%.6f',compression='gzip')
    details.update(rows=len(result),temperature_projection_count=int(cross.sum()),status='research_candidate_not_public_release',
        limitation='Observed-day alignment, draft station coordinates, original QC provenance and redistribution terms unresolved.',
        license='UNSPECIFIED: do not infer BMD redistribution rights',
        distinction='corrected_refit is full-training production output; corrected_oof is station-held-out evaluation output. Post-2023 has no observation validation.',
        model_selection='Methods declared explicitly; no hardcoded manuscript performance numbers.')
    write_json(root/'data_descriptor.json',details)
    save_table(root,'station_summary',result.groupby('station_name').agg(n_rows=('date','size'),start=('date','min'),end=('date','max'),
        mean_tmax=('tmax_corrected_refit','mean'),n_tmax_oof=('tmax_corrected_oof','count')).reset_index())
    return result,details
