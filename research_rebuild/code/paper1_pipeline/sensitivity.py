"""Explicit sensitivity analyses; none silently alter the source dataset."""
from pathlib import Path
import numpy as np
import pandas as pd
from .core import Config,TARGETS,metrics,detection,save_table,write_json

def lag_holdout_check(out,cfg=Config()):
    out=Path(out);train=pd.read_csv(out/'training_lag_sensitivity.csv')
    paired=pd.read_pickle(out/'paired.pkl');rows=[];choices=[];det=[]
    for (product,var),g in train.groupby(['product','variable']):
        selected=int(g.groupby('lag_days').r.mean().idxmax())
        choices.append(dict(product=product,target=var,lag_days_selected_from_2000_2015=selected))
        obs,raw=TARGETS[var]
        col=raw if product=='ERA5-Land' else {'Tmax':'pw_tmax','Tmin':'pw_tmin','Prcp':'pw_prcp'}[var]
        for station,z in paired.groupby('station_name'):
            z=z.set_index('date').asfreq('D')
            shifted=z[col].shift(selected)
            mask=(z.index>pd.Timestamp(cfg.temporal_cutoff))&z[obs].notna()&z[col].notna()&shifted.notna()
            for mode,pred in [('original_date_labels',z[col]),('training_selected_lag_sensitivity',shifted)]:
                rows.append(dict(product=product,target=var,station_name=station,mode=mode,selected_lag=selected,
                            **metrics(pred[mask],z.loc[mask,obs],var!='Prcp')))
                if var=='Prcp':
                    for t in [1,10,20,50]:det.append(dict(product=product,station_name=station,mode=mode,**detection(pred[mask],z.loc[mask,obs],t)))
    r=pd.DataFrame(rows);save_table(out,'lag_holdout_station_metrics',r);save_table(out,'lag_selected_training',pd.DataFrame(choices))
    save_table(out,'lag_holdout_rain_detection',pd.DataFrame(det))
    summary=r.groupby(['product','target','mode'])[['r','rmse','bias']].mean().reset_index();save_table(out,'lag_holdout_summary',summary)
    write_json(out/'lag_interpretation.json',{'positive_lag':'Compare observation labelled day t with reanalysis day t-lag.',
      'selection':'One global lag per product/variable selected using only 2000-2015 mean station correlation.',
      'evaluation':'2016-2023 station metrics on common original/shifted rows; previously available years, not newly collected blind data.',
      'decision':'Diagnostic only. Do not change rainfall dates without the supplied BMD archive convention and ERA5/POWER extraction metadata.',
      'supporting_source':'https://www.bmd.gov.bd/file/2026/06/24/pdf/205828.pdf',
      'source_limit':'A 2026 operational bulletin describes a 24-hour rainfall window ending 06 AM. It does not establish the date convention of this 2000-2023 archive.'})
    return summary
