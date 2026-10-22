"""Leakage-aware probability calibration with isotonic regression and diagnostics."""
from __future__ import annotations
import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import brier_score_loss, log_loss

class ChronologicalIsotonicCalibrator:
    """Fit on older observations only, then evaluate on a later holdout."""
    def __init__(self, min_train: int = 100, min_unique: int = 10):
        self.min_train=int(min_train); self.min_unique=int(min_unique); self.model=None; self.fit_cutoff=None
    def fit(self, probabilities, outcomes, dates=None):
        p=np.asarray(probabilities,dtype=float); y=np.asarray(outcomes,dtype=float)
        if p.ndim!=1 or y.ndim!=1 or len(p)!=len(y) or len(p)<self.min_train: raise ValueError(f"Need at least {self.min_train} aligned observations")
        if not np.all(np.isfinite(p)) or not np.all(np.isfinite(y)) or np.any((p<0)|(p>1)) or np.any((y<0)|(y>1)): raise ValueError("Probabilities/outcomes must be finite in [0,1]")
        if len(np.unique(p))<self.min_unique: raise ValueError("Too few unique probability values for stable isotonic calibration")
        if dates is not None:
            dt=pd.to_datetime(dates,utc=True,errors="raise")
            if len(dt)!=len(p) or not dt.is_monotonic_increasing: raise ValueError("Calibration rows must be chronological; sort by date before fitting")
            self.fit_cutoff=dt.max().isoformat()
        self.model=IsotonicRegression(y_min=0,y_max=1,out_of_bounds="clip").fit(p,y)
        return self
    def predict(self, probabilities):
        if self.model is None: raise RuntimeError("Call fit before predict")
        p=np.asarray(probabilities,dtype=float)
        if np.any(~np.isfinite(p)) or np.any((p<0)|(p>1)): raise ValueError("Input probabilities must be in [0,1]")
        return np.asarray(self.model.predict(p),dtype=float)
    def evaluate(self, probabilities, outcomes, bins=10):
        raw=np.asarray(probabilities,dtype=float); y=np.asarray(outcomes,dtype=int); cal=self.predict(raw)
        if len(raw)!=len(y) or len(y)==0 or np.any(~np.isin(y,[0,1])): raise ValueError("Need aligned non-empty binary outcomes")
        edges=np.linspace(0,1,int(bins)+1); bucket=np.clip(np.digitize(cal,edges[1:-1]),0,bins-1); rows=[]
        for b in range(bins):
            m=bucket==b
            if m.any(): rows.append({"bin":b,"count":int(m.sum()),"mean_predicted":float(cal[m].mean()),"observed_rate":float(y[m].mean()),"abs_gap":float(abs(cal[m].mean()-y[m].mean()))})
        return {"raw_brier":float(brier_score_loss(y,raw)),"calibrated_brier":float(brier_score_loss(y,cal)),
                "raw_log_loss":float(log_loss(y,np.clip(raw,1e-7,1-1e-7),labels=[0,1])),
                "calibrated_log_loss":float(log_loss(y,np.clip(cal,1e-7,1-1e-7),labels=[0,1])),
                "expected_calibration_error":float(sum(r["count"]/len(y)*r["abs_gap"] for r in rows)),
                "n":len(y),"bins":rows,"warning":"Fit the calibrator only on an earlier training/calibration window; report metrics on a later untouched holdout."}

def chronological_split(frame: pd.DataFrame, date_col: str, train_fraction: float = .7):
    if date_col not in frame or not 0.5<=train_fraction<=.9: raise ValueError("date column required and train_fraction must be 0.5..0.9")
    d=frame.copy(); d[date_col]=pd.to_datetime(d[date_col],utc=True,errors="raise"); d=d.sort_values(date_col).reset_index(drop=True)
    cut=max(1,min(len(d)-1,int(len(d)*train_fraction)))
    return d.iloc[:cut].copy(),d.iloc[cut:].copy()
