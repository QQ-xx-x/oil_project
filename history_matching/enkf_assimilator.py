import numpy as np


def ensemble_smoother_update(ensemble, simulated_obs, obs_values, obs_std, alpha, rng, lower, upper):
    """One ES-MDA/EnKF parameter update.

    ensemble:      (n_params, n_members), internal parameter space
    simulated_obs: (n_obs, n_members), transformed observation space
    obs_values:    (n_obs,)
    obs_std:       (n_obs,)
    alpha:         ES-MDA inflation factor
    """
    n_members = ensemble.shape[1]
    if n_members < 2:
        raise ValueError("EnKF requires at least two ensemble members.")

    x_mean = np.mean(ensemble, axis=1, keepdims=True)
    y_mean = np.mean(simulated_obs, axis=1, keepdims=True)
    x_anom = ensemble - x_mean
    y_anom = simulated_obs - y_mean

    c_xy = (x_anom @ y_anom.T) / float(n_members - 1)
    c_yy = (y_anom @ y_anom.T) / float(n_members - 1)
    inflated_r_diag = alpha * obs_std * obs_std
    a_matrix = c_yy + np.diag(inflated_r_diag)
    a_matrix += np.eye(a_matrix.shape[0]) * max(1e-10, 1e-8 * np.mean(inflated_r_diag))

    gain = np.linalg.solve(a_matrix.T, c_xy.T).T
    perturbations = rng.normal(0.0, np.sqrt(alpha) * obs_std[:, None], size=simulated_obs.shape)
    perturbed_obs = obs_values[:, None] + perturbations
    updated = ensemble + gain @ (perturbed_obs - simulated_obs)
    return np.clip(updated, lower[:, None], upper[:, None])


def objective_values(simulated_obs, obs_values, obs_std):
    residual = (simulated_obs - obs_values[:, None]) / np.maximum(obs_std[:, None], 1e-12)
    return np.sqrt(np.mean(residual * residual, axis=0))


def summarize_objectives(values):
    arr = np.asarray(values, dtype=float)
    return {
        "min": float(np.min(arr)),
        "mean": float(np.mean(arr)),
        "max": float(np.max(arr)),
        "std": float(np.std(arr)),
    }
