"""Optional, correctly labelled held-out SHAP analysis."""
from pathlib import Path
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits
from .core import Config,LOCAL,TERRAIN,write_json,save_table
from .models import ResidualModel
from .experiments import split_definitions

def heldout_shap(data,out,cfg=Config(),rows_per_block=200):
    out=Path(out);root=out/'interpretation';root.mkdir(exist_ok=True)
    try:import shap
    except ImportError:
        result={'status':'not_executed_dependency_unavailable','dependency':'shap',
          'note':'No impurity importance is substituted or labelled SHAP. Held-out feature ablations are available in the main experiments.'}
        write_json(root/'shap_status.json',result);return result
    frames=[]
    with threadpool_limits(limits=cfg.n_jobs):
        for fold,tr,te in split_definitions(data['full'],cfg,'spatial_block'):
            tr=tr.dropna(subset=['obs_tmax','t2m_max']);te=te.dropna(subset=['obs_tmax','t2m_max'])
            mdl=ResidualModel().fit(tr,'obs_tmax','t2m_max',LOCAL+TERRAIN,cfg,kind='ET')
            sample=te.sample(min(len(te),rows_per_block),random_state=cfg.seed)
            x=mdl.imputer.transform(sample[LOCAL+TERRAIN]);ex=shap.TreeExplainer(mdl.model)
            values=ex.shap_values(x,check_additivity=True)
            frame=pd.DataFrame(values,columns=LOCAL+TERRAIN);frame['row_id']=sample.row_id.to_numpy();frame['fold']=fold;frames.append(frame)
    values=pd.concat(frames,ignore_index=True)
    values.to_csv(root/'heldout_shap_values.csv.gz',index=False,compression='gzip')
    importance=values[LOCAL+TERRAIN].abs().mean().sort_values(ascending=False).rename('mean_abs_shap').reset_index(names='feature')
    save_table(root,'heldout_shap_importance',importance)
    result={'status':'executed','model':'ET_TERRAIN residual predictor','evaluation':'Four spatial block held-out samples',
            'n_rows':len(values),'scope':'Explains the ET baseline only; does not explain the full TARC gate or establish causality.'}
    write_json(root/'shap_status.json',result);return importance
