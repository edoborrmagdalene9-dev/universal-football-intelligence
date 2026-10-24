"""Joint Monte Carlo outcomes for DFS research; not a match engine or guarantee."""
from __future__ import annotations
import numpy as np


def simulate_correlated_points(means, covariance, n_simulations=10_000, seed=None,
                               floor_at_zero=False):
    """Sample joint player fantasy points from a multivariate-normal approximation.

    Player order in means must match covariance row/column order. Normal tails can
    be unrealistic for bounded/discrete points; compare against event-level models.
    """
    mu = np.asarray(means, dtype=float)
    cov = np.asarray(covariance, dtype=float)
    if mu.ndim != 1 or cov.shape != (len(mu), len(mu)):
        raise ValueError("covariance shape must match means")
    if not np.all(np.isfinite(mu)) or not np.all(np.isfinite(cov)):
        raise ValueError("means and covariance must be finite")
    if not np.allclose(cov, cov.T, atol=1e-8):
        raise ValueError("covariance must be symmetric")
    if np.linalg.eigvalsh((cov + cov.T) / 2.0).min(initial=0.0) < -1e-7:
        raise ValueError("covariance must be positive semidefinite")
    if isinstance(n_simulations, bool) or int(n_simulations) < 1:
        raise ValueError("n_simulations must be a positive integer")
    rng = np.random.default_rng(seed)
    samples = rng.multivariate_normal(mu, cov, size=int(n_simulations), check_valid="raise")
    if floor_at_zero:
        samples = np.maximum(samples, 0.0)
    return samples


def summarize_player_samples(samples):
    """Summarize columns of a simulation matrix (one column per player)."""
    x = np.asarray(samples, dtype=float)
    if x.ndim != 2 or x.shape[0] < 1 or not np.all(np.isfinite(x)):
        raise ValueError("samples must be a finite 2D matrix")
    return {
        "mean": x.mean(axis=0),
        "std": x.std(axis=0, ddof=1) if x.shape[0] > 1 else np.zeros(x.shape[1]),
        "p50": np.quantile(x, 0.50, axis=0),
        "p75": np.quantile(x, 0.75, axis=0),
        "p90": np.quantile(x, 0.90, axis=0),
        "p95": np.quantile(x, 0.95, axis=0),
    }


def lineup_ceiling(samples, player_indices, quantile=0.90):
    """Quantile of total lineup points across joint simulation rows."""
    x = np.asarray(samples, dtype=float)
    idx = list(player_indices)
    if x.ndim != 2 or not idx or min(idx) < 0 or max(idx) >= x.shape[1]:
        raise ValueError("valid non-empty player_indices are required")
    if not 0 < quantile < 1:
        raise ValueError("quantile must be between 0 and 1")
    return float(np.quantile(x[:, idx].sum(axis=1), quantile))
