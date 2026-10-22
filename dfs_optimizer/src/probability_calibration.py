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


class MulticlassIsotonicCalibrator:
    """One-vs-rest isotonic calibration for 1X2 outcomes, followed by row normalization."""
    labels=("H","D","A")
    def __init__(self,min_train=300,min_class_outcomes=20,min_unique=10):
        self.min_train=int(min_train); self.min_class_outcomes=int(min_class_outcomes); self.min_unique=int(min_unique); self.models={}; self.fit_cutoff=None
    def fit(self,probabilities,outcomes,dates=None):
        p=np.asarray(probabilities,float); y=np.asarray(outcomes).astype(str)
        if p.ndim!=2 or p.shape[1]!=3 or len(p)!=len(y) or len(p)<self.min_train: raise ValueError(f"Need at least {self.min_train} rows with three aligned probabilities")
        if not np.isfinite(p).all() or np.any((p<0)|(p>1)) or not np.allclose(p.sum(axis=1),1,atol=.03): raise ValueError("Each H/D/A probability row must be finite, in [0,1] and sum approximately to 1")
        if not set(y).issubset(set(self.labels)): raise ValueError("outcomes must be H, D or A")
        if any(int((y==label).sum())<self.min_class_outcomes for label in self.labels): raise ValueError("Insufficient examples of one or more 1X2 outcomes")
        if dates is not None:
            dt=pd.to_datetime(dates,utc=True,errors="raise")
            if len(dt)!=len(p) or not dt.is_monotonic_increasing: raise ValueError("Rows must be chronological before fitting")
            self.fit_cutoff=dt.max().isoformat()
        self.models={}
        for j,label in enumerate(self.labels):
            if len(np.unique(p[:,j]))<self.min_unique: raise ValueError(f"Too few unique probabilities for class {label}")
            self.models[label]=IsotonicRegression(y_min=0,y_max=1,out_of_bounds="clip").fit(p[:,j],(y==label).astype(int))
        return self
    def predict(self,probabilities):
        if len(self.models)!=3: raise RuntimeError("Call fit before predict")
        p=np.asarray(probabilities,float)
        if p.ndim!=2 or p.shape[1]!=3 or not np.isfinite(p).all() or np.any((p<0)|(p>1)): raise ValueError("Expected an Nx3 probability matrix")
        calibrated=np.column_stack([self.models[label].predict(p[:,j]) for j,label in enumerate(self.labels)])
        totals=calibrated.sum(axis=1,keepdims=True)
        zero=totals[:,0]<=1e-12
        calibrated[~zero]=calibrated[~zero]/totals[~zero]
        calibrated[zero]=p[zero]/p[zero].sum(axis=1,keepdims=True).clip(min=1e-12)
        return calibrated
    def evaluate(self,probabilities,outcomes):
        p=np.asarray(probabilities,float); y=np.asarray(outcomes).astype(str); cal=self.predict(p)
        if len(y)!=len(p) or not set(y).issubset(set(self.labels)): raise ValueError("Need aligned H/D/A outcomes")
        onehot=np.column_stack([(y==label).astype(float) for label in self.labels])
        raw_brier=float(np.mean(np.sum((p-onehot)**2,axis=1))); cal_brier=float(np.mean(np.sum((cal-onehot)**2,axis=1)))
        raw_log=float(log_loss(y,p,labels=list(self.labels))); cal_log=float(log_loss(y,cal,labels=list(self.labels)))
        class_metrics={}
        for j,label in enumerate(self.labels):
            class_metrics[label]={"raw_brier":float(brier_score_loss(onehot[:,j],p[:,j])),"calibrated_brier":float(brier_score_loss(onehot[:,j],cal[:,j]))}
        return {"raw_multiclass_brier":raw_brier,"calibrated_multiclass_brier":cal_brier,"raw_log_loss":raw_log,"calibrated_log_loss":cal_log,"n":len(y),"class_metrics":class_metrics,"warning":"Fit only on an earlier calibration window; report these metrics on an untouched later holdout."}
