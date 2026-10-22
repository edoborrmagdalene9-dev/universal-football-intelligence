"""Time-decay weighted Dixon-Coles model for football scores.

Input rows: date, home_team, away_team, home_goals, away_goals.
Dates may be ISO strings or datetime-like objects. This is a compact research
implementation; evaluate calibration chronologically before production use.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from math import exp, log
from typing import Iterable, Mapping
import numpy as np
from scipy.optimize import minimize
from scipy.special import gammaln

@dataclass
class DixonColesFit:
    teams: list[str]
    attack: dict[str, float]
    defense: dict[str, float]
    home_advantage: float
    rho: float
    xi: float
    fitted_at: datetime

def _date(value):
    if isinstance(value, datetime): return value
    return datetime.fromisoformat(str(value).replace("Z", "+00:00")).replace(tzinfo=None)

def _tau(x, y, lam, mu, rho):
    if x == 0 and y == 0: return 1.0 - lam * mu * rho
    if x == 0 and y == 1: return 1.0 + lam * rho
    if x == 1 and y == 0: return 1.0 + mu * rho
    if x == 1 and y == 1: return 1.0 - rho
    return 1.0

def _poisson_logpmf(k, rate):
    return k * np.log(np.maximum(rate, 1e-12)) - rate - gammaln(k + 1)

def fit_dixon_coles(matches: Iterable[Mapping], xi: float = 0.0065,
                    maxiter: int = 1500) -> DixonColesFit:
    rows = []
    for r in matches:
        rows.append((_date(r["date"]), str(r["home_team"]), str(r["away_team"]),
                     int(r["home_goals"]), int(r["away_goals"])))
    if len(rows) < 10: raise ValueError("At least 10 matches are required to fit the model")
    if any(x[3] < 0 or x[4] < 0 for x in rows): raise ValueError("Goals must be non-negative")
    rows.sort(key=lambda r: r[0])
    teams = sorted({r[1] for r in rows} | {r[2] for r in rows})
    if len(teams) < 2: raise ValueError("At least two teams are required")
    idx = {t:i for i,t in enumerate(teams)}
    newest = rows[-1][0]
    weights = np.array([exp(-xi * max(0.0, (newest-r[0]).total_seconds()/86400.0)) for r in rows])
    hi = np.array([idx[r[1]] for r in rows]); ai = np.array([idx[r[2]] for r in rows])
    hg = np.array([r[3] for r in rows], dtype=float); ag = np.array([r[4] for r in rows], dtype=float)
    n = len(teams)
    # params: attack[n], defense[n], home advantage, rho. Sum-to-zero is imposed by centering.
    def unpack(p):
        attack = p[:n] - np.mean(p[:n])
        defense = p[n:2*n] - np.mean(p[n:2*n])
        return attack, defense, p[-2], p[-1]
    def objective(p):
        attack, defense, home, rho = unpack(p)
        lh = np.exp(np.clip(home + attack[hi] + defense[ai], -5, 4))
        la = np.exp(np.clip(attack[ai] + defense[hi], -5, 4))
        logp = _poisson_logpmf(hg, lh) + _poisson_logpmf(ag, la)
        for j,(x,y) in enumerate(zip(hg.astype(int), ag.astype(int))):
            tau = _tau(x,y,lh[j],la[j],rho)
            if tau <= 0: return 1e12
            if x <= 1 and y <= 1: logp[j] += log(tau)
        return -float(np.sum(weights * logp)) + 0.001 * float(np.sum(p[:2*n]**2))
    initial = np.zeros(2*n+2)
    initial[-2] = 0.15
    initial[-1] = -0.05
    bounds = [(None,None)]*(2*n) + [(-1.5,1.5),(-0.95,0.95)]
    result = minimize(objective, initial, method="L-BFGS-B", bounds=bounds,
                      options={"maxiter": maxiter})
    if not result.success and not np.isfinite(result.fun):
        raise RuntimeError(f"Dixon-Coles optimization failed: {result.message}")
    attack, defense, home, rho = unpack(result.x)
    return DixonColesFit(teams, dict(zip(teams, attack.tolist())),
                         dict(zip(teams, defense.tolist())), float(home), float(rho), xi, newest)

def score_grid(fit: DixonColesFit, home_team: str, away_team: str,
               max_goals: int = 10) -> np.ndarray:
    if home_team not in fit.attack or away_team not in fit.attack:
        raise KeyError("Both teams must be present in the fitted historical data")
    lam = exp(np.clip(fit.home_advantage + fit.attack[home_team] + fit.defense[away_team], -5, 4))
    mu = exp(np.clip(fit.attack[away_team] + fit.defense[home_team], -5, 4))
    goals = np.arange(max_goals+1)
    lh = _poisson_logpmf(goals[:,None], lam)
    la = _poisson_logpmf(goals[None,:], mu)
    grid = np.exp(lh + la)
    for x in (0,1):
        for y in (0,1):
            grid[x,y] *= max(0.0, _tau(x,y,lam,mu,fit.rho))
    total = grid.sum()
    if total <= 0: raise RuntimeError("Invalid score probability grid")
    return grid / total

def match_probabilities(grid: np.ndarray) -> dict[str,float]:
    return {"home_win": float(np.tril(grid, -1).sum()),
            "draw": float(np.trace(grid)),
            "away_win": float(np.triu(grid, 1).sum()),
            "home_clean_sheet": float(grid[:,0].sum()),
            "away_clean_sheet": float(grid[0,:].sum()),
            "home_expected_goals": float((grid * np.arange(grid.shape[0])[:,None]).sum()),
            "away_expected_goals": float((grid * np.arange(grid.shape[1])[None,:]).sum())}
