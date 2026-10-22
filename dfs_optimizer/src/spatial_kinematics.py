"""Derive 2D/3D movement metrics from observed tracking; never fabricate telemetry."""
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
 for c in ('x_m','y_m')+(('z_m',) if 'z_m' in d else ()): d[c]=pd.to_numeric(d[c],errors='coerce')
 d=d.dropna(subset=['player_id','timestamp','x_m','y_m']).sort_values(['player_id','timestamp'])
 if d.empty: raise ValueError('No valid tracking samples')
 if ((d.x_m<0)|(d.x_m>pitch_length_m)|(d.y_m<0)|(d.y_m>pitch_width_m)).any(): raise ValueError('Coordinates outside pitch; check units/orientation')
 if 'z_m' in d and (d.z_m.dropna()<0).any(): raise ValueError('z_m height must be non-negative')
 if d.duplicated(['player_id','timestamp']).any(): raise ValueError('Resolve duplicate player timestamps')
 g=d.groupby('player_id'); d['dt_s']=g.timestamp.diff().dt.total_seconds(); d['dx_m']=g.x_m.diff(); d['dy_m']=g.y_m.diff(); d['dz_m']=g.z_m.diff() if 'z_m' in d else 0.0
 d['distance_2d_m']=np.hypot(d.dx_m,d.dy_m); d['distance_3d_m']=np.sqrt(d.dx_m**2+d.dy_m**2+pd.to_numeric(d.dz_m,errors='coerce').fillna(0)**2)
 d['speed_2d_mps']=d.distance_2d_m/d.dt_s; d['speed_3d_mps']=d.distance_3d_m/d.dt_s if 'z_m' in d else np.nan
 d.loc[(d.dt_s<=0)|(d.dt_s>10),['speed_2d_mps','speed_3d_mps']]=np.nan
 d['acceleration_2d_mps2']=d.groupby('player_id').speed_2d_mps.diff()/d.groupby('player_id').dt_s.diff(); d['acceleration_3d_mps2']=d.groupby('player_id').speed_3d_mps.diff()/d.groupby('player_id').dt_s.diff() if 'z_m' in d else np.nan
 d['distance_m']=d.distance_3d_m.where(d.speed_3d_mps.notna(),d.distance_2d_m).where(d.speed_2d_mps.notna(),0); d['hi_distance_m']=d.distance_m.where(d.speed_2d_mps>=high_intensity_mps,0)
 rows=[]
 for pid,x in d.groupby('player_id',sort=False): rows.append({'player_id':pid,'coordinate_dimension':3 if 'z_m' in d and d.z_m.notna().all() else 2,'valid_tracking_samples':int(x.speed_2d_mps.notna().sum()),'mean_speed_mps':float(x.speed_2d_mps.mean()) if x.speed_2d_mps.notna().any() else np.nan,'peak_speed_mps':float(x.speed_2d_mps.max()) if x.speed_2d_mps.notna().any() else np.nan,'peak_speed_3d_mps':float(x.speed_3d_mps.max()) if x.speed_3d_mps.notna().any() else np.nan,'mean_acceleration_mps2':float(x.acceleration_2d_mps2.mean()) if x.acceleration_2d_mps2.notna().any() else np.nan,'peak_acceleration_mps2':float(x.acceleration_2d_mps2.max()) if x.acceleration_2d_mps2.notna().any() else np.nan,'distance_m':float(x.distance_m.sum()),'high_intensity_distance_m':float(x.hi_distance_m.sum()),'high_intensity_threshold_mps':high_intensity_mps,'quality_note':'3D only when z_m is measured; check tracking frequency, coverage and provider definitions.'})
 return pd.DataFrame(rows)

def wingback_penetration_index(events,pitch_length_m,attacking_direction=1):
 """Final-third entry rate from timestamped event coordinates; not inferred from screenshots."""
 required={'player_id','timestamp','x_m'}
 if not required.issubset(events.columns): raise ValueError('Events missing: '+', '.join(sorted(required-set(events.columns))))
 if attacking_direction not in (-1,1) or pitch_length_m<=0: raise ValueError('Invalid pitch orientation or length')
 d=events.copy(); d['timestamp']=pd.to_datetime(d.timestamp,errors='coerce',utc=True); d['x_m']=pd.to_numeric(d.x_m,errors='coerce'); d=d.dropna(subset=['player_id','timestamp','x_m'])
 if ((d.x_m<0)|(d.x_m>pitch_length_m)).any(): raise ValueError('x_m outside pitch')
 d['attacking_x']=d.x_m if attacking_direction==1 else pitch_length_m-d.x_m; d['final_third_entry']=d.attacking_x>=2*pitch_length_m/3
 out=d.groupby('player_id').agg(final_third_entries=('final_third_entry','sum'),first_event=('timestamp','min'),last_event=('timestamp','max')).reset_index(); out['observed_window_seconds']=(out.last_event-out.first_event).dt.total_seconds(); out['penetration_entries_per_second']=out.final_third_entries/out.observed_window_seconds.replace(0,np.nan); out['warning']='Event feed coverage and player role labels are required; entries do not prove assists or shots on target.'; return out
