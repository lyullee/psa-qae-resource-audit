"""Six-cell confirmation of the hydraulically feasible operating window."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import replace
from itertools import product
from pathlib import Path
import sys

import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import psa_qae.psa_hydraulically_feasible_extended_operation_screen_v1 as screen
import psa_qae.psa_literature_calibrated_policy_6cell_confirmation as base
import psa_qae.psa_literature_anchored_policy_full_6cell_cube as full_cube


HERE = Path(__file__).resolve().parent
OUT = HERE / "results" / "hydraulically_feasible_policy_6cell_confirmation_v1"
N_CELLS = 6
N_CYCLES = 60


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def policies() -> list[dict]:
    return [
        {
            "policy": "corrected_conservative",
            "tank_setpoint_bar": 6.0,
            "purge_active_s": 4.0,
            "adsorption_stage_s": 540.0,
            "role": "hydraulically feasible correction of the prior selected policy",
        },
        {
            "policy": "candidate",
            "tank_setpoint_bar": 6.0,
            "purge_active_s": 3.0,
            "adsorption_stage_s": 540.0,
            "role": "low-resolution extended-screen optimum",
        },
        {
            "policy": "short_purge_boundary",
            "tank_setpoint_bar": 6.0,
            "purge_active_s": 2.0,
            "adsorption_stage_s": 540.0,
            "role": "nearest low-purge failure boundary",
        },
        {
            "policy": "long_adsorption_boundary",
            "tank_setpoint_bar": 6.0,
            "purge_active_s": 3.0,
            "adsorption_stage_s": 600.0,
            "role": "nearest high-throughput breakthrough boundary",
        },
        {
            "policy": "low_tank_tradeoff",
            "tank_setpoint_bar": 4.5,
            "purge_active_s": 4.0,
            "adsorption_stage_s": 540.0,
            "role": "reserve-versus-booster-energy tradeoff",
        },
    ]


def scenarios() -> list[dict]:
    return base.confirmation_scenarios()


def cases() -> list[dict]:
    return [
        {"case_index": index, **policy, **scenario}
        for index, (policy, scenario) in enumerate(product(policies(), scenarios()))
    ]


def signature() -> dict:
    source_files = [
        Path(screen.__file__).resolve(),
        Path(base.__file__).resolve(),
        Path(full_cube.__file__).resolve(),
        full_cube.core.REQUIREMENT.resolve(),
    ]
    lowres_json = (
        HERE
        / "results"
        / "hydraulically_feasible_extended_operation_screen_v1"
        / "PSA_HYDRAULICALLY_FEASIBLE_EXTENDED_OPERATION_SCREEN_V1.json"
    )
    return {
        "schema": "psa-hydraulically-feasible-policy-6cell-state/v1",
        "n_cells": N_CELLS,
        "n_cycles": N_CYCLES,
        "area_cm2": float(full_cube.AREA_CM2),
        "selectivity_multiplier": float(full_cube.SELECTIVITY_MULTIPLIER),
        "area_steps": int(full_cube.AREA_STEPS),
        "qualified_h2_target_mol_s": float(base.strict.DESIGN_TARGET_H2_RATE_MOL_S),
        "passive_fill_driving_margin_bar": float(screen.PASSIVE_FILL_DRIVING_MARGIN_BAR),
        "booster_efficiency": float(screen.BOOSTER_EFFICIENCY),
        "policies": policies(),
        "scenarios": scenarios(),
        "source_sha256": {str(path.relative_to(HERE)): sha256(path) for path in source_files},
        "low_resolution_source": str(lowres_json.relative_to(HERE)),
        "low_resolution_source_sha256": sha256(lowres_json),
    }


def dynamic_raw(case: dict) -> tuple[np.ndarray, dict, dict[str, np.ndarray]]:
    process_contract = base.strict.load_contract()
    p0 = base.public_params(process_contract, n_cells=N_CELLS, max_step_points=24)
    feed_y = np.asarray(p0.feed_y_dry, dtype=float)
    feed_y[base.strict.INDEX["H2"]] *= float(case["feed_h2_multiplier"])
    feed_y /= max(float(feed_y.sum()), 1.0e-30)
    c = float(case["capacity_coordinate_c"])
    a = float(case["affinity_coordinate_a"])
    p = replace(
        p0,
        feed_y_dry=tuple(float(value) for value in feed_y),
        k_purge_in_mol_s_bar=base.operation.K_PURGE_IN_MOL_S_BAR,
        ldf_factor=float(case["ldf_factor"]),
        zeolite_capacity_factor=1.5 * c,
        zeolite_affinity_factor=1.5 * a,
        component_affinity_factors=(1.0, 1.0, 1.0, 2.0 * a, 2.0 * a),
    )
    setpoint = float(case["tank_setpoint_bar"])
    tank_capacity = base.tank_moles_at_pressure(
        setpoint,
        volume_m3=base.strict.TANK_VOLUME_M3,
        temperature_K=p.temperature_K,
    )
    stage_s = float(case["adsorption_stage_s"])
    result = base.run_cycle(
        n_cycles=N_CYCLES,
        p=p,
        stage_durations_s=(stage_s,) * 4,
        equalization_duration_s=base.strict.EQUALIZATION_S,
        equalization_conductance=0.01,
        equalization_pressure_bar=float(
            process_contract["experiment"]["equalization_pressure_bar_abs"]
        ),
        recycle_fraction=0.0,
        tank_capacity_mol=tank_capacity,
        initial_tank_moles=tank_capacity,
        tank_volume_m3=base.strict.TANK_VOLUME_M3,
        adsorption_substeps=base.strict.ADSORPTION_SUBSTEPS,
        quality_gate=None,
        purge_active_duration_s=float(case["purge_active_s"]),
        pressurization_active_duration_s=stage_s,
        product_routing_mode="regulated_product_manifold",
    )
    raw = np.asarray(
        [stream["external_out_mol"] for stream in result["all_adsorption_streams"]],
        dtype=float,
    )
    _, _, cycle_time_s = base.operation.build_variable_timeline(raw, N_CYCLES, stage_s)
    cycle_moles = raw.reshape(
        N_CYCLES,
        4 * base.strict.ADSORPTION_SUBSTEPS,
        len(base.strict.COMPONENTS),
    ).sum(axis=1)
    cycle_h2_rates = cycle_moles[:, base.strict.INDEX["H2"]] / cycle_time_s
    tail_ratio = float(np.mean(cycle_h2_rates[-3:])) / max(
        float(np.mean(cycle_h2_rates[-6:-3])), 1.0e-30
    )
    minimum_tank_pressure = float(result["min_tank_pressure_bar"])
    reserve_threshold = float(p.P_low_bar) + base.strict.MINIMUM_RESERVE_ABOVE_P_LOW_BAR
    reserve_gate = bool(minimum_tank_pressure >= reserve_threshold)
    css_gate = bool(
        float(result["css_residual_final"])
        <= base.strict.MAXIMUM_ENGINEERING_CSS_STATE_RESIDUAL
    )
    numerical_gate = bool(
        float(result["cycle_mass_balance_relative_max"])
        <= base.strict.MAXIMUM_CYCLE_BALANCE_RELATIVE
        and base.strict.TAIL_STABILITY_RATIO_RANGE[0]
        <= tail_ratio
        <= base.strict.TAIL_STABILITY_RATIO_RANGE[1]
        and float(result["final_tank_pressure_bar"]) >= setpoint - 0.1
        and css_gate
    )
    product_manifold_bar = float(p.P_high_bar - p.product_outlet_drop_bar)
    passive_fill_margin = product_manifold_bar - setpoint
    passive_fill_gate = bool(
        passive_fill_margin >= screen.PASSIVE_FILL_DRIVING_MARGIN_BAR - 1.0e-12
    )
    internal_demand = np.asarray(result["cumulative_internal_product_demand_mol"], dtype=float)
    metrics = {
        "raw_provenance": "direct_six_cell_sixty_cycle_integration",
        "tank_capacity_mol": float(tank_capacity),
        "min_tank_pressure_bar": minimum_tank_pressure,
        "final_tank_pressure_bar": float(result["final_tank_pressure_bar"]),
        "reserve_threshold_bar": reserve_threshold,
        "reserve_margin_bar": minimum_tank_pressure - reserve_threshold,
        "product_manifold_backpressure_bar": product_manifold_bar,
        "passive_fill_pressure_margin_bar": passive_fill_margin,
        "passive_fill_gate": passive_fill_gate,
        "maximum_booster_pressure_ratio": float(
            p.P_high_bar / max(minimum_tank_pressure, 0.05)
        ),
        "cumulative_internal_h2_demand_mol": float(
            internal_demand[base.strict.INDEX["H2"]]
        ),
        "booster_discharge_pressure_bar": float(p.P_high_bar),
        "booster_suction_temperature_K": float(p.temperature_K),
        "css_residual_final": float(result["css_residual_final"]),
        "tail3_to_previous3_ratio": tail_ratio,
        "cycle_mass_balance_relative_max": float(result["cycle_mass_balance_relative_max"]),
        "step_mass_balance_relative_max": float(result["step_mass_balance_relative_max"]),
        "reserve_gate": reserve_gate,
        "css_gate": css_gate,
        "numerical_gate": numerical_gate,
    }
    arrays = {
        "cycle_h2_rate_mol_s": cycle_h2_rates.astype(np.float32),
        "cycle_tank_pressure_bar": np.asarray(
            [row["tank_pressure_bar"] for row in result["css_history"]], dtype=np.float32
        ),
        "cycle_css_residual": np.asarray(
            [row["css_residual_max"] for row in result["css_history"]], dtype=np.float32
        ),
    }
    return raw, metrics, arrays


def evaluate(task: tuple[int, str]) -> dict:
    index, out_text = task
    out = Path(out_text)
    state_dir = out / "states"
    state_dir.mkdir(parents=True, exist_ok=True)
    state_path = state_dir / f"case_{index:03d}.json"
    trace_path = state_dir / f"case_{index:03d}_traces.npz"
    expected = signature()
    if state_path.exists() and trace_path.exists():
        cached = json.loads(state_path.read_text(encoding="utf-8"))
        if cached.get("run_signature") == expected:
            return cached

    started = time.time()
    case = cases()[index]
    raw, raw_metrics, raw_arrays = dynamic_raw(case)
    polished, polish_metrics, polish_arrays = full_cube.polish(
        raw, float(case["adsorption_stage_s"]), area_cm2=full_cube.AREA_CM2
    )
    strict_event = bool(
        polish_metrics["continuous_gate_pass"] and polish_metrics["feasible_inventory"]
    )
    confirmation_gate = bool(
        raw_metrics["reserve_gate"]
        and raw_metrics["numerical_gate"]
        and raw_metrics["passive_fill_gate"]
        and strict_event
    )
    design_event = bool(
        confirmation_gate
        and float(polish_metrics["qualified_h2_rate_mol_s"])
        >= float(base.strict.DESIGN_TARGET_H2_RATE_MOL_S)
    )
    qualified_h2_mol = float(polish_metrics["qualified_h2_rate_mol_s"]) * float(
        polish_metrics["elapsed_s"]
    )
    work_j = float(raw_metrics["cumulative_internal_h2_demand_mol"]) * screen.booster_work_j_per_mol(
        float(raw_metrics["min_tank_pressure_bar"]),
        float(raw_metrics["booster_discharge_pressure_bar"]),
        float(raw_metrics["booster_suction_temperature_K"]),
    )
    booster_kwh_per_kg = work_j / 3.6e6 / max(
        qualified_h2_mol * screen.HYDROGEN_MOLAR_MASS_KG_MOL, 1.0e-30
    )
    np.savez_compressed(
        trace_path,
        components=np.asarray(base.strict.COMPONENTS),
        raw_external_out_mol=raw.astype(np.float32),
        **raw_arrays,
        **polish_arrays,
    )
    row = {
        "run_signature": expected,
        **case,
        "n_cells": N_CELLS,
        "n_cycles": N_CYCLES,
        **raw_metrics,
        "raw_h2_rate_mol_s": float(
            raw[:, base.strict.INDEX["H2"]].sum()
            / (N_CYCLES * float(polish_metrics["cycle_time_s"]))
        ),
        "polished_h2_rate_mol_s": float(
            polished[:, base.strict.INDEX["H2"]].sum()
            / (N_CYCLES * float(polish_metrics["cycle_time_s"]))
        ),
        **polish_metrics,
        "conservative_booster_kwh_per_kg_qualified_h2": booster_kwh_per_kg,
        "strict_event": strict_event,
        "confirmation_gate": confirmation_gate,
        "conditional_design_event": design_event,
        "trace_file": str(trace_path.relative_to(out)),
        "wall_time_s": time.time() - started,
    }
    state_path.write_text(json.dumps(row, indent=2) + "\n", encoding="utf-8")
    return row


def aggregate(out: Path) -> dict:
    rows = []
    expected = signature()
    for case in cases():
        path = out / "states" / f"case_{case['case_index']:03d}.json"
        trace = out / "states" / f"case_{case['case_index']:03d}_traces.npz"
        row = json.loads(path.read_text(encoding="utf-8"))
        if row.get("run_signature") != expected:
            raise AssertionError(f"signature mismatch: {path}")
        with np.load(trace, allow_pickle=False) as archive:
            for name in archive.files:
                values = np.asarray(archive[name])
                if values.dtype.kind in "biufc" and not np.isfinite(values).all():
                    raise AssertionError(f"non-finite trace: {trace}:{name}")
        rows.append(row)

    policy_summary = []
    for policy in policies():
        subset = [row for row in rows if row["policy"] == policy["policy"]]
        policy_summary.append(
            {
                **policy,
                "scenario_count": len(subset),
                "confirmation_pass_count": int(sum(row["confirmation_gate"] for row in subset)),
                "design_pass_count": int(sum(row["conditional_design_event"] for row in subset)),
                "minimum_qualified_h2_rate_mol_s": min(
                    row["qualified_h2_rate_mol_s"] for row in subset
                ),
                "maximum_worst_gate_factor": max(row["worst_gate_factor"] for row in subset),
                "minimum_reserve_margin_bar": min(row["reserve_margin_bar"] for row in subset),
                "maximum_booster_pressure_ratio": max(
                    row["maximum_booster_pressure_ratio"] for row in subset
                ),
                "maximum_conservative_booster_kwh_per_kg_qualified_h2": max(
                    row["conservative_booster_kwh_per_kg_qualified_h2"] for row in subset
                ),
                "all_scenarios_pass": bool(
                    all(row["conditional_design_event"] for row in subset)
                ),
            }
        )
    robust = [row for row in policy_summary if row["all_scenarios_pass"]]
    selected = max(
        robust,
        key=lambda row: float(row["minimum_qualified_h2_rate_mol_s"]),
    ) if robust else None
    payload = {
        "schema": "psa-hydraulically-feasible-policy-6cell-confirmation/v1",
        "status": "six_cell_sixty_cycle_hydraulic_window_confirmation_complete",
        "run_signature": expected,
        "rows": rows,
        "policy_summary": policy_summary,
        "selected_robust_policy": selected,
        "summary": {
            "case_count": len(rows),
            "policy_count": len(policy_summary),
            "robust_policy_count": len(robust),
            "selected_policy": None if selected is None else selected["policy"],
            "maximum_css_residual_final": max(row["css_residual_final"] for row in rows),
            "maximum_cycle_mass_balance_relative": max(
                row["cycle_mass_balance_relative_max"] for row in rows
            ),
            "all_trace_integrity_checks_pass": True,
        },
        "claim_limits": [
            "The three scenarios are the center and two adverse cases selected before this high-resolution calculation.",
            "Passive refill is enforced by a static 0.2-bar margin; the next topology step is a pressure-dependent refill-valve transient.",
            "The booster estimate uses the minimum tank pressure for every internal mole and is conservative; no vendor compressor map is claimed.",
        ],
    }
    out.mkdir(parents=True, exist_ok=True)
    (out / "PSA_HYDRAULICALLY_FEASIBLE_POLICY_6CELL_CONFIRMATION_V1.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )
    flat = [
        {key: value for key, value in row.items() if not isinstance(value, (dict, list))}
        for row in rows
    ]
    with (out / "PSA_HYDRAULICALLY_FEASIBLE_POLICY_6CELL_CONFIRMATION_V1.csv").open(
        "w", newline="", encoding="utf-8-sig"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(flat[0]))
        writer.writeheader()
        writer.writerows(flat)
    with (out / "PSA_HYDRAULICALLY_FEASIBLE_POLICY_6CELL_SUMMARY_V1.csv").open(
        "w", newline="", encoding="utf-8-sig"
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(policy_summary[0]))
        writer.writeheader()
        writer.writerows(policy_summary)

    labels = [row["policy"].replace("_", "\n") for row in policy_summary]
    x = np.arange(len(policy_summary))
    colors = ["#059669" if row["all_scenarios_pass"] else "#9ca3af" for row in policy_summary]
    fig, axes = plt.subplots(2, 2, figsize=(13.2, 8.6), constrained_layout=True)
    axes[0, 0].bar(x, [row["minimum_qualified_h2_rate_mol_s"] for row in policy_summary], color=colors)
    axes[0, 0].axhline(float(base.strict.DESIGN_TARGET_H2_RATE_MOL_S), color="#dc2626", linestyle="--")
    axes[0, 0].set_ylabel("Minimum qualified H2 (mol/s)")
    axes[0, 1].bar(x, [row["maximum_worst_gate_factor"] for row in policy_summary], color=colors)
    axes[0, 1].axhline(1.0, color="#dc2626", linestyle="--")
    axes[0, 1].set_ylabel("Maximum strict-gate factor")
    axes[1, 0].bar(x, [row["minimum_reserve_margin_bar"] for row in policy_summary], color=colors)
    axes[1, 0].axhline(0.0, color="#dc2626", linestyle="--")
    axes[1, 0].set_ylabel("Minimum reserve margin (bar)")
    axes[1, 1].bar(x, [row["maximum_conservative_booster_kwh_per_kg_qualified_h2"] for row in policy_summary], color=colors)
    axes[1, 1].set_ylabel("Conservative booster duty (kWh/kg H2)")
    for axis in axes.flat:
        axis.set_xticks(x, labels, fontsize=8)
        axis.grid(axis="y", alpha=0.25)
    fig.suptitle("Six-cell hydraulic operating-window confirmation", fontweight="bold")
    fig.savefig(out / "PSA_HYDRAULICALLY_FEASIBLE_POLICY_6CELL_CONFIRMATION_V1.png", dpi=220)
    plt.close(fig)

    lines = [
        "# Six-cell hydraulic operating-window confirmation",
        "",
        "| Policy | Controls (bar / s / s) | Passes | Min qualified H2 (mol/s) | Max gate factor | Min reserve (bar) | Max booster (kWh/kg) |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in policy_summary:
        lines.append(
            f"| {row['policy']} | {row['tank_setpoint_bar']:.1f} / {row['purge_active_s']:.0f} / {row['adsorption_stage_s']:.0f} | "
            f"{row['design_pass_count']}/{row['scenario_count']} | {row['minimum_qualified_h2_rate_mol_s']:.8f} | "
            f"{row['maximum_worst_gate_factor']:.6f} | {row['minimum_reserve_margin_bar']:.4f} | "
            f"{row['maximum_conservative_booster_kwh_per_kg_qualified_h2']:.4f} |"
        )
    if selected is not None:
        lines.extend([
            "",
            f"The robust high-resolution recommendation is **{selected['tank_setpoint_bar']:.1f} bar, {selected['purge_active_s']:.0f} s purge, and {selected['adsorption_stage_s']:.0f} s adsorption**.",
        ])
    (out / "PSA_HYDRAULICALLY_FEASIBLE_POLICY_6CELL_CONFIRMATION_V1.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--indices", type=int, nargs="*")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    indices = list(range(len(cases()))) if args.indices is None else list(args.indices)
    tasks = [(index, str(OUT)) for index in indices]
    if args.workers > 1 and len(tasks) > 1:
        with ProcessPoolExecutor(max_workers=args.workers) as pool:
            futures = {pool.submit(evaluate, task): task[0] for task in tasks}
            for future in as_completed(futures):
                row = future.result()
                print(json.dumps({
                    "completed": row["case_index"],
                    "policy": row["policy"],
                    "scenario": row["scenario"],
                    "design_event": row["conditional_design_event"],
                    "wall_time_s": row["wall_time_s"],
                }), flush=True)
    else:
        for task in tasks:
            row = evaluate(task)
            print(json.dumps({"completed": row["case_index"], "wall_time_s": row["wall_time_s"]}), flush=True)
    if all(
        (OUT / "states" / f"case_{index:03d}.json").exists()
        and (OUT / "states" / f"case_{index:03d}_traces.npz").exists()
        for index in range(len(cases()))
    ):
        payload = aggregate(OUT)
        print(json.dumps({"status": payload["status"], "summary": payload["summary"]}, indent=2))


if __name__ == "__main__":
    main()
