"""Derive movement metrics from observed tracking; never fabricate telemetry."""
import numpy as np
import pandas as pd

def pitch_geometry(length_m,width_m):
 if not np.isfinite(length_m+width_m) or length_m<=0 or width_m<=0: raise ValueError('Pitch dimensions must be finite positive metres')
 return {'length_m':float(length_m),'width_m':float(width_m),'area_m2':float(length_m*width_m),'aspect_ratio':float(length_m/width_m),'warning':'No automatic interception or pass bonus follows from pitch size alone.'}

def derive_player_kinematics(tracking,pitch_length_m,pitch_width_m,high_intensity_mps=5.5):
 required={'player_id','timestamp','x_m','y_m'}
 if not required.issubset(tracking.columns): raise ValueError('Tracking missing: '+', '.join(sorted(required-set(tracking.columns))))
 if min(pitch_length_m,pitch_width_m,high_intensity_mps)<=0: raise ValueError('Dimensions and speed threshold must be positive')
 d=tracking.copy(); d['timestamp']=pd.to_datetime(d.timestamp,errors='coerce',utc=True)
 for c in ('x_m','y_m'): d[c]=pd.to_numeric(d[c],errors='coerce')
 d=d.dropna(subset=['player_id','timestamp','x_m','y_m']).sort_values(['player_id','timestamp'])
 if d.empty: raise ValueError('No valid tracking samples')
 if ((d.x_m<0)|(d.x_m>pitch_length_m)|(d.y_m<0)|(d.y_m>pitch_width_m)).any(): raise ValueError('Coordinates outside pitch; check units/orientation')
 if d.duplicated(['player_id','timestamp']).any(): raise ValueError('Resolve duplicate player timestamps')
 g=d.groupby('player_id'); d['dt_s']=g.timestamp.diff().dt.total_seconds(); d['dx_m']=g.x_m.diff(); d['dy_m']=g.y_m.diff(); d['speed_mps']=np.hypot(d.dx_m,d.dy_m)/d.dt_s
 d.loc[(d.dt_s<=0)|(d.dt_s>10),'speed_mps']=np.nan; d['acceleration_mps2']=d.groupby('player_id').speed_mps.diff()/d.groupby('player_id').dt_s.diff(); d['distance_m']=np.hypot(d.dx_m,d.dy_m).where(d.speed_mps.notna(),0); d['hi_distance_m']=d.distance_m.where(d.speed_mps>=high_intensity_mps,0)
 rows=[]
 for pid,x in d.groupby('player_id',sort=False): rows.append({'player_id':pid,'valid_tracking_samples':int(x.speed_mps.notna().sum()),'mean_speed_mps':float(x.speed_mps.mean()) if x.speed_mps.notna().any() else np.nan,'peak_speed_mps':float(x.speed_mps.max()) if x.speed_mps.notna().any() else np.nan,'mean_acceleration_mps2':float(x.acceleration_mps2.mean()) if x.acceleration_mps2.notna().any() else np.nan,'peak_acceleration_mps2':float(x.acceleration_mps2.max()) if x.acceleration_mps2.notna().any() else np.nan,'distance_m':float(x.distance_m.sum()),'high_intensity_distance_m':float(x.hi_distance_m.sum()),'high_intensity_threshold_mps':high_intensity_mps,'quality_note':'Check tracking frequency, coverage and provider definitions.'})
 return pd.DataFrame(rows)
