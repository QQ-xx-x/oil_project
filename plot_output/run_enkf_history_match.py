import argparse
import csv
import json
from pathlib import Path

import numpy as np

from enkf_assimilator import ensemble_smoother_update, objective_values, summarize_objectives
from model_adapter import ForwardModelAdapter, copy_best_output
from observations import build_observations
from parameters import ParameterManager, load_config, resolve_path


def write_csv(path, rows, fieldnames=None):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    if fieldnames is None:
        fieldnames = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def evaluate_ensemble(config, manager, obs, adapter, ensemble, iteration, runs_dir):
    n_members = ensemble.shape[1]
    simulated = []
    objectives = []
    output_paths = []

    for member in range(n_members):
        run_dir = Path(runs_dir) / f"iter_{iteration:02d}" / f"member_{member:03d}"
        params = manager.vector_to_params(ensemble[:, member])
        print(f"iteration={iteration} member={member} forward_start", flush=True)
        simulation, output_path = adapter.run_member(
            params,
            run_dir,
            quiet=bool(config["enkf"].get("quiet_member_logs", True)),
        )
        y_sim = obs.transform_simulation(simulation)
        simulated.append(y_sim)
        objectives.append(obs.objective(y_sim))
        output_paths.append(str(output_path))
        print(f"iteration={iteration} member={member} objective={objectives[-1]:.5f}", flush=True)

    simulated_matrix = np.column_stack(simulated)
    return simulated_matrix, np.array(objectives, dtype=float), output_paths


def main():
    parser = argparse.ArgumentParser(description="Run first-version ES-MDA/EnKF gas-water history matching.")
    parser.add_argument("--config", default="enkf_config.json", help="Path to EnKF config JSON.")
    parser.add_argument("--dry-run", action="store_true", help="Validate config and write the initial ensemble only.")
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = Path(__file__).resolve().parent / config_path
    config = load_config(config_path)

    results_dir = resolve_path(config["results_dir"], config)
    runs_dir = resolve_path(config["runs_dir"], config)
    results_dir.mkdir(parents=True, exist_ok=True)
    runs_dir.mkdir(parents=True, exist_ok=True)

    manager = ParameterManager(config)
    obs = build_observations(config)
    seed = int(config.get("random_seed", 20260521))
    rng = np.random.default_rng(seed)
    ensemble_size = int(config["enkf"]["ensemble_size"])
    ensemble = manager.sample_initial_ensemble(ensemble_size, seed)

    write_csv(
        results_dir / "ensemble_initial.csv",
        manager.ensemble_physical_rows(ensemble, iteration=0),
    )
    write_json(
        results_dir / "observation_summary.json",
        {
            "n_observations": int(obs.values.size),
            "n_days": int(obs.days.size),
            "days": obs.days.tolist(),
            "channels": [channel["name"] for channel in obs.channels],
        },
    )

    if args.dry_run:
        print(f"dry_run=true")
        print(f"config={config_path}")
        print(f"ensemble_size={ensemble_size}")
        print(f"n_parameters={len(manager.names)}")
        print(f"n_observations={obs.values.size}")
        print(f"results_dir={results_dir}")
        return

    adapter = ForwardModelAdapter(config)
    lower = manager.lower_vector()
    upper = manager.upper_vector()
    alphas = [float(alpha) for alpha in config["enkf"]["alphas"]]
    summary_rows = []
    best_seen = None

    for iteration, alpha in enumerate(alphas):
        print(f"=== EnKF/ES-MDA iteration {iteration + 1}/{len(alphas)}, alpha={alpha:g} ===", flush=True)
        simulated, objectives, output_paths = evaluate_ensemble(config, manager, obs, adapter, ensemble, iteration, runs_dir)
        obj_summary = summarize_objectives(objectives)
        print(
            "iteration="
            f"{iteration} objective_min={obj_summary['min']:.5f} "
            f"objective_mean={obj_summary['mean']:.5f} objective_max={obj_summary['max']:.5f}",
            flush=True,
        )
        summary_rows.append({"iteration": iteration, "alpha": alpha, **obj_summary})
        write_csv(
            results_dir / f"ensemble_iter_{iteration:02d}.csv",
            manager.ensemble_physical_rows(ensemble, iteration=iteration),
        )
        write_csv(
            results_dir / f"objectives_iter_{iteration:02d}.csv",
            [
                {
                    "iteration": iteration,
                    "member": member,
                    "objective": float(objectives[member]),
                    "output_path": output_paths[member],
                }
                for member in range(ensemble_size)
            ],
        )

        best_member = int(np.argmin(objectives))
        if best_seen is None or objectives[best_member] < best_seen["objective"]:
            best_seen = {
                "iteration": iteration,
                "member": best_member,
                "objective": float(objectives[best_member]),
                "params": manager.vector_to_physical(ensemble[:, best_member]),
                "output_path": output_paths[best_member],
            }

        ensemble = ensemble_smoother_update(
            ensemble=ensemble,
            simulated_obs=simulated,
            obs_values=obs.values,
            obs_std=obs.std,
            alpha=alpha,
            rng=rng,
            lower=lower,
            upper=upper,
        )

    write_csv(results_dir / "assimilation_summary.csv", summary_rows)
    write_json(results_dir / "best_seen_member.json", best_seen)
    write_csv(
        results_dir / "ensemble_final.csv",
        manager.ensemble_physical_rows(ensemble, iteration=len(alphas)),
    )

    best_params, best_physical = manager.mean_params(ensemble)
    final_run_dir = Path(runs_dir) / "best_fit_mean"
    final_simulation, final_output_path = adapter.run_member(best_params, final_run_dir, quiet=True)
    final_vector = obs.transform_simulation(final_simulation)
    final_objective = obs.objective(final_vector)

    selected_source = "final_ensemble_mean"
    selected_params = best_params
    selected_output_path = final_output_path
    selected_objective = final_objective
    if best_seen is not None and best_seen["objective"] < final_objective:
        selected_source = "best_seen_member"
        selected_objective = best_seen["objective"]
        selected_output_path = Path(best_seen["output_path"])
        selected_params_path = selected_output_path.parent / "params.json"
        selected_params = json.loads(selected_params_path.read_text(encoding="utf-8"))

    write_json(results_dir / "best_fit_params.json", selected_params)
    write_json(
        results_dir / "best_fit_summary.json",
        {
            "objective": selected_objective,
            "selected_source": selected_source,
            "final_ensemble_mean_objective": final_objective,
            "best_seen_member_objective": best_seen["objective"] if best_seen else None,
            "physical_fit_parameters": (
                best_seen["params"] if selected_source == "best_seen_member" else best_physical
            ),
            "simulation_output": str(selected_output_path),
        },
    )
    copy_best_output(selected_output_path, results_dir / "best_fit_output.csv")

    print(f"best_fit_objective={selected_objective:.5f}", flush=True)
    print(f"best_fit_selected_source={selected_source}", flush=True)
    print(f"best_fit_params={results_dir / 'best_fit_params.json'}", flush=True)
    print(f"best_fit_output={results_dir / 'best_fit_output.csv'}", flush=True)


if __name__ == "__main__":
    main()
