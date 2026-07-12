import argparse
import csv
import hashlib
import json
import time
from pathlib import Path

import numpy as np

from enkf_assimilator import ensemble_smoother_update, objective_values, summarize_objectives
from model_adapter import ForwardModelAdapter, copy_best_output, stable_json_sha256, file_sha256
from observations import build_observations
from parameters import ParameterManager, load_config, resolve_path


EVENT_PREFIX = "HM_EVENT="


def emit_event(event_type, **payload):
    event = {"type": str(event_type), **payload}
    print(
        EVENT_PREFIX + json.dumps(event, ensure_ascii=False, separators=(",", ":")),
        flush=True,
    )


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


def build_run_signature_context(config):
    history_path = resolve_path(config["history_file"], config)
    context = {
        "history_file": str(history_path.resolve()),
        "history_sha256": file_sha256(history_path),
        "case_dataset_path": config.get("case_dataset_path", ""),
        "observation": config["observation"],
        "fit_parameters": config["fit_parameters"],
        "base_params_sha256": stable_json_sha256(config["base_params"]),
        "enkf_alphas": config["enkf"].get("alphas"),
        "ensemble_size": config["enkf"].get("ensemble_size"),
        "random_seed": config.get("random_seed"),
    }
    well_control = config.get("well_control") or {}
    if (well_control.get("mode") or "free") != "free":
        context["well_control"] = well_control
    return context


def apply_well_control_overrides(config, mode=None, bhp=None):
    if mode is None and bhp is None:
        return

    if mode is None and bhp is not None:
        mode = "fixed_bhp"
    if mode not in {"free", "fixed_bhp", "fixed_gas_rate", "fixed_water_rate"}:
        raise ValueError(f"Unsupported well_control mode: {mode}")
    if mode == "free":
        if bhp is not None:
            raise ValueError("--fixed-bhp cannot be used with --well-control-mode free.")
        config["well_control"] = {"mode": "free"}
        return

    current = config.get("well_control") or {}
    if mode in {"fixed_gas_rate", "fixed_water_rate"}:
        if bhp is not None:
            raise ValueError("--fixed-bhp cannot be used with rate-control modes.")
        well_control = dict(current)
        well_control["mode"] = mode
        config["well_control"] = well_control
        return

    well_control = {"mode": "fixed_bhp"}
    if bhp is not None:
        well_control["bhp"] = float(bhp)
    else:
        if "bhp" in current:
            well_control["bhp"] = current["bhp"]
    config["well_control"] = well_control


def compact_fit_parameters(params):
    return {
        "initial_sw": params["initial_state"]["sw"],
        "well_bhp": params["well"]["bhp"],
        "hf_perm": params["hydraulic_fractures"]["hf_perm"],
        "frac_perm": params["fractures"]["frac_perm"],
        "wr_shape_factor": params["dual_porosity"]["wr_shape_factor"],
    }


def result_payload(config, results_dir, selected_objective, selected_source, selected_params, summary):
    well_control = config.get("well_control") or {}
    mode = well_control.get("mode") or "free"
    plot_path = Path(results_dir) / "history_fit_gas_water.png"
    payload = {
        "mode": mode,
        "objective": float(selected_objective),
        "selected_source": selected_source,
        "best_fit_parameters": compact_fit_parameters(selected_params),
        "physical_fit_parameters": summary["physical_fit_parameters"],
        "files": {
            "plot": str(plot_path),
            "best_fit_params": str(Path(results_dir) / "best_fit_params.json"),
            "best_fit_output": str(Path(results_dir) / "best_fit_output.csv"),
            "summary": str(Path(results_dir) / "best_fit_summary.json"),
            "assimilation_summary": str(Path(results_dir) / "assimilation_summary.csv"),
        },
    }
    if mode == "fixed_bhp":
        payload["fixed_bhp"] = selected_params["well"]["bhp"]
    return payload


def evaluate_ensemble(
    config, manager, obs, adapter, ensemble, iteration, runs_dir,
    total_iterations, progress,
):
    n_members = ensemble.shape[1]
    simulated = []
    objectives = []
    output_paths = []

    for member in range(n_members):
        run_dir = Path(runs_dir) / f"iter_{iteration:02d}" / f"member_{member:03d}"
        params = manager.vector_to_params(ensemble[:, member])
        emit_event(
            "member_started",
            iteration=iteration + 1,
            total_iterations=total_iterations,
            member=member + 1,
            total_members=n_members,
            completed_runs=progress["completed_runs"],
            total_forward_runs=progress["total_forward_runs"],
        )
        print(f"iteration={iteration} member={member} forward_start", flush=True)
        started_at = time.monotonic()
        simulation, output_path = adapter.run_member(
            params,
            run_dir,
            quiet=bool(config["enkf"].get("quiet_member_logs", True)),
        )
        y_sim = obs.transform_simulation(simulation)
        simulated.append(y_sim)
        objective = obs.objective(y_sim)
        objectives.append(objective)
        output_paths.append(str(output_path))
        elapsed_seconds = max(0.0, time.monotonic() - started_at)
        progress["completed_runs"] += 1
        previous_best = progress.get("best_objective")
        improved = previous_best is None or objective < previous_best
        if improved:
            progress["best_objective"] = float(objective)
        emit_event(
            "member_completed",
            iteration=iteration + 1,
            iteration_index=iteration,
            total_iterations=total_iterations,
            member=member + 1,
            member_index=member,
            total_members=n_members,
            objective=float(objective),
            best_objective=float(progress["best_objective"]),
            best_improved=bool(improved),
            elapsed_seconds=elapsed_seconds,
            reused=bool(getattr(adapter, "last_run_reused", False)),
            completed_runs=progress["completed_runs"],
            total_forward_runs=progress["total_forward_runs"],
        )
        print(f"iteration={iteration} member={member} objective={objective:.5f}", flush=True)

    simulated_matrix = np.column_stack(simulated)
    return simulated_matrix, np.array(objectives, dtype=float), output_paths


def main():
    parser = argparse.ArgumentParser(description="Run first-version ES-MDA/EnKF gas-water history matching.")
    parser.add_argument("--config", default="enkf_config.json", help="Path to EnKF config JSON.")
    parser.add_argument("--dry-run", action="store_true", help="Validate config and write the initial ensemble only.")
    parser.add_argument(
        "--well-control-mode",
        choices=["free", "fixed_bhp", "fixed_gas_rate", "fixed_water_rate"],
        default=None,
        help="Override well_control.mode from config. Default keeps config, missing config means free.",
    )
    parser.add_argument(
        "--fixed-bhp",
        type=float,
        default=None,
        help="Fixed bottom-hole pressure for fixed_bhp mode. If set without --well-control-mode, mode becomes fixed_bhp.",
    )
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = Path(__file__).resolve().parent / config_path
    config = load_config(config_path)
    apply_well_control_overrides(config, args.well_control_mode, args.fixed_bhp)

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

    adapter = ForwardModelAdapter(config, run_signature_context=build_run_signature_context(config))
    lower = manager.lower_vector()
    upper = manager.upper_vector()
    alphas = [float(alpha) for alpha in config["enkf"]["alphas"]]
    summary_rows = []
    best_seen = None
    progress = {
        "completed_runs": 0,
        "total_forward_runs": ensemble_size * len(alphas) + 1,
        "best_objective": None,
    }
    emit_event(
        "run_started",
        total_iterations=len(alphas),
        total_members=ensemble_size,
        total_forward_runs=progress["total_forward_runs"],
    )

    for iteration, alpha in enumerate(alphas):
        emit_event(
            "iteration_started",
            iteration=iteration + 1,
            total_iterations=len(alphas),
            total_members=ensemble_size,
            alpha=alpha,
        )
        print(f"=== EnKF/ES-MDA iteration {iteration + 1}/{len(alphas)}, alpha={alpha:g} ===", flush=True)
        simulated, objectives, output_paths = evaluate_ensemble(
            config, manager, obs, adapter, ensemble, iteration, runs_dir,
            len(alphas), progress,
        )
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

        emit_event(
            "iteration_completed",
            iteration=iteration + 1,
            iteration_index=iteration,
            total_iterations=len(alphas),
            objective_min=obj_summary["min"],
            objective_mean=obj_summary["mean"],
            objective_max=obj_summary["max"],
            best_objective=float(progress["best_objective"]),
            completed_runs=progress["completed_runs"],
            total_forward_runs=progress["total_forward_runs"],
        )

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
    emit_event(
        "final_mean_started",
        completed_runs=progress["completed_runs"],
        total_forward_runs=progress["total_forward_runs"],
    )
    final_started_at = time.monotonic()
    final_simulation, final_output_path = adapter.run_member(best_params, final_run_dir, quiet=True)
    final_vector = obs.transform_simulation(final_simulation)
    final_objective = obs.objective(final_vector)
    final_elapsed_seconds = max(0.0, time.monotonic() - final_started_at)
    progress["completed_runs"] += 1
    previous_best = progress.get("best_objective")
    final_improved = previous_best is None or final_objective < previous_best
    if final_improved:
        progress["best_objective"] = float(final_objective)
    emit_event(
        "final_mean_completed",
        objective=float(final_objective),
        best_objective=float(progress["best_objective"]),
        best_improved=bool(final_improved),
        elapsed_seconds=final_elapsed_seconds,
        reused=bool(getattr(adapter, "last_run_reused", False)),
        completed_runs=progress["completed_runs"],
        total_forward_runs=progress["total_forward_runs"],
    )

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
    summary = {
        "objective": selected_objective,
        "selected_source": selected_source,
        "final_ensemble_mean_objective": final_objective,
        "best_seen_member_objective": best_seen["objective"] if best_seen else None,
        "physical_fit_parameters": (
            best_seen["params"] if selected_source == "best_seen_member" else best_physical
        ),
        "simulation_output": str(selected_output_path),
    }
    write_json(results_dir / "best_fit_summary.json", summary)
    copy_best_output(selected_output_path, results_dir / "best_fit_output.csv")
    payload = result_payload(config, results_dir, selected_objective, selected_source, selected_params, summary)
    write_json(results_dir / "run_result.json", payload)

    print(f"best_fit_objective={selected_objective:.5f}", flush=True)
    print(f"best_fit_selected_source={selected_source}", flush=True)
    print(f"best_fit_params={results_dir / 'best_fit_params.json'}", flush=True)
    print(f"best_fit_output={results_dir / 'best_fit_output.csv'}", flush=True)
    print(f"RESULT_JSON={json.dumps(payload, ensure_ascii=False, separators=(',', ':'))}", flush=True)
    emit_event(
        "run_completed",
        objective=float(selected_objective),
        selected_source=selected_source,
        completed_runs=progress["completed_runs"],
        total_forward_runs=progress["total_forward_runs"],
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        emit_event("run_failed", error_type=type(exc).__name__, message=str(exc))
        raise
