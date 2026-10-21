"""Optional CVXPY MIQP adapter; requires a compatible installed non-convex MIQP solver."""
import numpy as np

def optimize_miqp(means, covariance, salaries, salary_cap, roster_size, ownership=None, variance_weight=0.05, ownership_penalty=0.0, solver=None):
    try:
        import cvxpy as cp
    except ImportError as exc:
        raise RuntimeError('Optional MIQP requires CVXPY installed separately') from exc
    mu, salary, cov = np.asarray(means, float), np.asarray(salaries, float), np.asarray(covariance, float)
    own = np.zeros_like(mu) if ownership is None else np.asarray(ownership, float)
    n = len(mu)
    if mu.ndim != 1 or salary.shape != (n,) or own.shape != (n,) or cov.shape != (n,n):
        raise ValueError('input dimensions must match')
    if not np.allclose(cov, cov.T, atol=1e-8) or not np.all(np.isfinite(cov)):
        raise ValueError('covariance must be finite and symmetric')
    if np.any(salary < 0) or salary_cap <= 0 or not 1 <= roster_size <= n:
        raise ValueError('invalid roster or salary constraints')
    if np.any((own < 0) | (own > 1)) or variance_weight < 0 or ownership_penalty < 0:
        raise ValueError('invalid ownership or objective weights')
    x = cp.Variable(n, boolean=True)
    objective = cp.Maximize(mu @ x + variance_weight * cp.quad_form(x, cp.psd_wrap(cov)) - ownership_penalty * (own @ x))
    problem = cp.Problem(objective, [cp.sum(x) == roster_size, salary @ x <= salary_cap])
    candidates = [solver] if solver else ['SCIP', 'GUROBI', 'CPLEX', 'MOSEK']
    available = [s for s in candidates if s in cp.installed_solvers()]
    if not available:
        raise RuntimeError('No compatible MIQP solver installed; no silent MILP fallback was used')
    problem.solve(solver=available[0])
    if problem.status not in {cp.OPTIMAL, cp.OPTIMAL_INACCURATE} or x.value is None:
        raise RuntimeError(f'MIQP failed with status {problem.status}')
    return {'indices': np.flatnonzero(np.asarray(x.value).ravel() > 0.5).tolist(), 'objective': float(problem.value), 'status': problem.status, 'solver': available[0]}
