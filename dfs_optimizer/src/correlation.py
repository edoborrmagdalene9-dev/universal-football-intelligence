"""Covariance utilities for correlated fantasy-point simulations.

Inputs must be estimates learned from historical data or supplied as explicit
research assumptions. The module does not infer real-world correlations by itself.
"""
from __future__ import annotations
import numpy as np


def covariance_from_std_corr(std_devs, correlation):
    """Build a covariance matrix from standard deviations and correlations."""
    std = np.asarray(std_devs, dtype=float)
    corr = np.asarray(correlation, dtype=float)
    if std.ndim != 1 or corr.shape != (len(std), len(std)):
        raise ValueError("correlation must be an NxN matrix matching std_devs")
    if not np.all(np.isfinite(std)) or np.any(std < 0):
        raise ValueError("standard deviations must be finite and non-negative")
    if not np.all(np.isfinite(corr)) or not np.allclose(corr, corr.T, atol=1e-8):
        raise ValueError("correlation matrix must be finite and symmetric")
    if not np.allclose(np.diag(corr), 1.0, atol=1e-6):
        raise ValueError("correlation matrix diagonal must equal 1")
    if np.any(corr < -1.0 - 1e-8) or np.any(corr > 1.0 + 1e-8):
        raise ValueError("correlations must lie between -1 and 1")
    cov = corr * np.outer(std, std)
    if np.linalg.eigvalsh(cov).min(initial=0.0) < -1e-7:
        raise ValueError("covariance matrix must be positive semidefinite")
    return cov


def nearest_psd(matrix, epsilon=1e-9):
    """Return a symmetric positive-semidefinite approximation by eigenvalue clipping."""
    a = np.asarray(matrix, dtype=float)
    if a.ndim != 2 or a.shape[0] != a.shape[1] or not np.all(np.isfinite(a)):
        raise ValueError("matrix must be a finite square matrix")
    sym = (a + a.T) / 2.0
    values, vectors = np.linalg.eigh(sym)
    fixed = (vectors * np.maximum(values, epsilon)) @ vectors.T
    return (fixed + fixed.T) / 2.0


def portfolio_variance(covariance, indices):
    """Variance of a sum of selected player outcomes."""
    cov = np.asarray(covariance, dtype=float)
    idx = list(indices)
    if cov.ndim != 2 or cov.shape[0] != cov.shape[1]:
        raise ValueError("covariance must be square")
    if not idx:
        return 0.0
    return float(cov[np.ix_(idx, idx)].sum())
