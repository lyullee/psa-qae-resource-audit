"""Full eight-corner six-cell cube for the pressure-consistent PSA policies."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from itertools import product
from pathlib import Path
import sys

import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import psa_qae.psa_hydraulically_feasible_policy_6cell_confirmation_v1 as confirm
import psa_qae.psa_literature_anchored_policy_full_6cell_cube as old_cube


HERE = Path(__file__).resolve().parent
OUT = HERE / "results" / "hydraulically_feasible_full_6cell_cube_v1"
REUSE = HERE / "results" / "hydraulically_feasible_policy_6cell_confirmation_v1"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def policies() -> list[dict]:
    return [
        {
            "policy": "comparison",
            "tank_setpoint_bar": 6.0,
            "purge_active_s": 6.0,
            "adsorption_stage_s": 480.0,
        },
        {
            "policy": "selected",
            "tank_setpoint_bar": 6.0,
            "purge_active_s": 4.0,
            "adsorption_stage_s": 540.0,
        },
    ]


def scenarios() -> list[dict]:
    return old_cube.corner_scenarios()


def cases() -> list[dict]:
    return [
        {"case_index": index, **policy, **scenario}
        for index, (policy, scenario) in enumerate(product(policies(), scenarios()))
    ]


def signature() -> dict:
    source_files = [
        Path(confirm.__file__).resolve(),
        Path(old_cube.__file__).resolve(),
        old_cube.core.REQUIREMENT.resolve(),
    ]
    return {
        "schema": "psa-hydraulically-feasible-full-6cell-cube-state/v1",
        "n_cells": 6,
        "n_cycles": 60,
        "area_cm2": float(old_cube.AREA_CM2),
        "selectivity_multiplier": float(old_cube.SELECTIVITY_MULTIPLIER),
        "area_steps": int(old_cube.AREA_STEPS),
        "qualified_h2_target_mol_s": float(confirm.base.strict.DESIGN_TARGET_H2_RATE_MOL_S),
        "passive_fill_driving_margin_bar": float(
            confirm.screen.PASSIVE_FILL_DRIVING_MARGIN_BAR
        ),
        "booster_efficiency": float(confirm.screen.BOOSTER_EFFICIENCY),
        "policies": policies(),
        "scenarios": scenarios(),
        "source_sha256": {str(path.relative_to(HERE)): sha256(path) for path in source_files},
        "reusable_source": str(REUSE.relative_to(HERE)),
    }


RAW_KEYS = (
    "tank_capacity_mol",
    "min_tank_pressure_bar",
    "final_tank_pressure_bar",
    "reserve_threshold_bar",
    "reserve_margin_bar",
    "product_manifold_backpressure_bar",
    "passive_fill_pressure_margin_bar",
    "passive_fill_gate",
    "maximum_booster_pressure_ratio",
    "cumulative_internal_h2_demand_mol",
    "booster_discharge_pressure_bar",
    "booster_suction_temperature_K",
    "css_residual_final",
    "tail3_to_previous3_ratio",
    "cycle_mass_balance_relative_max",
    "step_mass_balance_relative_max",
    "reserve_gate",
    "css_gate",
    "numerical_gate",
)


def find_reusable(case: dict) -> tuple[Path, Path] | None:
    for path in sorted((REUSE / "states").glob("case_*.json")):
        state = json.loads(path.read_text(encoding="utf-8"))
        if (
            float(state["tank_setpoint_bar"]) == float(case["tank_setpoint_bar"])
            and float(state["purge_active_s"]) == float(case["purge_active_s"])
            and float(state["adsorption_stage_s"]) == float(case["adsorption_stage_s"])
            and state["scenario"] == case["scenario"]
        ):
            trace = path.with_name(path.stem + "_traces.npz")
            if trace.exists():
                return path, trace
    return None


def reusable_raw(state_path: Path, trace_path: Path) -> tuple[np.ndarray, dict, dict]:
    state = json.loads(state_path.read_text(encoding="utf-8"))
    with np.load(trace_path, allow_pickle=False) as archive:
        raw = np.asarray(archive["raw_external_out_mol"], dtype=float)
        arrays = {
            "cycle_h2_rate_mol_s": np.asarray(archive["cycle_h2_rate_mol_s"]),
            "cycle_tank_pressure_bar": np.asarray(archive["cycle_tank_pressure_bar"]),
            "cycle_css_residual": np.asarray(archive["cycle_css_residual"]),
        }
    metrics = {key: state[key] for key in RAW_KEYS}
    metrics.update(
        {
            "raw_provenance": "exact_reuse_of_pressure_consistent_six_cell_trajectory",
            "reused_state": str(state_path.relative_to(HERE)),
            "reused_trace": str(trace_path.relative_to(HERE)),
            "reused_state_sha256": sha256(state_path),
            "reused_trace_sha256": sha256(trace_path),
        }
    )
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
    reusable = find_reusable(case)
    if reusable is None:
        raw, raw_metrics, raw_arrays = confirm.dynamic_raw(case)
        raw_metrics["raw_provenance"] = "direct_six_cell_sixty_cycle_integration"
    else:
        raw, raw_metrics, raw_arrays = reusable_raw(*reusable)
    polished, polish_metrics, polish_arrays = old_cube.polish(
        raw, float(case["adsorption_stage_s"]), area_cm2=old_cube.AREA_CM2
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
        >= float(confirm.base.strict.DESIGN_TARGET_H2_RATE_MOL_S)
    )
    qualified_h2_mol = float(polish_metrics["qualified_h2_rate_mol_s"]) * float(
        polish_metrics["elapsed_s"]
    )
    work_j = float(raw_metrics["cumulative_internal_h2_demand_mol"]) * confirm.screen.booster_work_j_per_mol(
        float(raw_metrics["min_tank_pressure_bar"]),
        float(raw_metrics["booster_discharge_pressure_bar"]),
        float(raw_metrics["booster_suction_temperature_K"]),
    )
    booster_kwh_per_kg = work_j / 3.6e6 / max(
        qualified_h2_mol * confirm.screen.HYDROGEN_MOLAR_MASS_KG_MOL, 1.0e-30
    )
    np.savez_compressed(
        trace_path,
        components=np.asarray(confirm.base.strict.COMPONENTS),
        raw_external_out_mol=raw.astype(np.float32),
        **raw_arrays,
        **polish_arrays,
    )
    row = {
        "run_signature": expected,
        **case,
        "n_cells": 6,
        "n_cycles": 60,
        **raw_metrics,
        "raw_h2_rate_mol_s": float(
            raw[:, confirm.base.strict.INDEX["H2"]].sum()
            / (60 * float(polish_metrics["cycle_time_s"]))
        ),
        "polished_h2_rate_mol_s": float(
            polished[:, confirm.base.strict.INDEX["H2"]].sum()
            / (60 * float(polish_metrics["cycle_time_s"]))
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
        state_path = out / "states" / f"case_{case['case_index']:03d}.json"
        trace_path = out / "states" / f"case_{case['case_index']:03d}_traces.npz"
        row = json.loads(state_path.read_text(encoding="utf-8"))
        if row.get("run_signature") != expected:
            raise AssertionError(f"signature mismatch: {state_path}")
        with np.load(trace_path, allow_pickle=False) as archive:
            for name in archive.files:
                values = np.asarray(archive[name])
                if values.dtype.kind in "biufc" and not np.isfinite(values).all():
                    raise AssertionError(f"non-finite trace: {trace_path}:{name}")
        rows.append(row)
    paired = []
    for scenario in scenarios():
        comp = next(row for row in rows if row["policy"] == "comparison" and row["scenario"] == scenario["scenario"])
        sel = next(row for row in rows if row["policy"] == "selected" and row["scenario"] == scenario["scenario"])
        paired.append(
            {
                "scenario": scenario["scenario"],
                "comparison_qualified_h2_rate_mol_s": comp["qualified_h2_rate_mol_s"],
                "selected_qualified_h2_rate_mol_s": sel["qualified_h2_rate_mol_s"],
                "shipment_improvement_percent": 100.0 * (
                    sel["qualified_h2_rate_mol_s"] / comp["qualified_h2_rate_mol_s"] - 1.0
                ),
                "comparison_reserve_margin_bar": comp["reserve_margin_bar"],
                "selected_reserve_margin_bar": sel["reserve_margin_bar"],
                "reserve_margin_gain_bar": sel["reserve_margin_bar"] - comp["reserve_margin_bar"],
                "comparison_worst_gate_factor": comp["worst_gate_factor"],
                "selected_worst_gate_factor": sel["worst_gate_factor"],
                "comparison_design_event": comp["conditional_design_event"],
                "selected_design_event": sel["conditional_design_event"],
            }
        )
    summary = {
        "case_count": len(rows),
        "new_dynamic_trajectories": int(sum(row["raw_provenance"] == "direct_six_cell_sixty_cycle_integration" for row in rows)),
        "reused_dynamic_trajectories": int(sum(row["raw_provenance"] != "direct_six_cell_sixty_cycle_integration" for row in rows)),
        "comparison_pass_count": int(sum(row["comparison_design_event"] for row in paired)),
        "selected_pass_count": int(sum(row["selected_design_event"] for row in paired)),
        "minimum_shipment_improvement_percent": min(row["shipment_improvement_percent"] for row in paired),
        "maximum_shipment_improvement_percent": max(row["shipment_improvement_percent"] for row in paired),
        "minimum_reserve_margin_gain_bar": min(row["reserve_margin_gain_bar"] for row in paired),
        "selected_minimum_qualified_h2_rate_mol_s": min(row["selected_qualified_h2_rate_mol_s"] for row in paired),
        "selected_minimum_reserve_margin_bar": min(row["selected_reserve_margin_bar"] for row in paired),
        "selected_maximum_booster_kwh_per_kg_qualified_h2": max(
            row["conservative_booster_kwh_per_kg_qualified_h2"]
            for row in rows if row["policy"] == "selected"
        ),
        "maximum_css_residual_final": max(row["css_residual_final"] for row in rows),
        "maximum_cycle_mass_balance_relative": max(row["cycle_mass_balance_relative_max"] for row in rows),
        "all_trace_integrity_checks_pass": True,
    }
    payload = {
        "schema": "psa-hydraulically-feasible-full-6cell-cube/v1",
        "status": "full_pressure_consistent_six_cell_uncertainty_cube_complete",
        "run_signature": expected,
        "rows": rows,
        "paired_comparisons": paired,
        "summary": summary,
        "claim_limits": [
            "The eight corners are a deterministic engineering envelope, not a plant-calibrated probability distribution.",
            "The 0.2-bar passive-fill margin is static; pressure-dependent refill-valve dynamics remain a separate topology refinement.",
            "Booster energy is a conservative ideal-gas estimate evaluated at the minimum tank pressure for all internal hydrogen demand.",
        ],
    }
    (out / "PSA_HYDRAULICALLY_FEASIBLE_FULL_6CELL_CUBE_V1.json").write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )
    flat = [{key: value for key, value in row.items() if not isinstance(value, (dict, list))} for row in rows]
    fieldnames = []
    for row in flat:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with (out / "PSA_HYDRAULICALLY_FEASIBLE_FULL_6CELL_CUBE_V1.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames); writer.writeheader(); writer.writerows(flat)
    with (out / "PSA_HYDRAULICALLY_FEASIBLE_FULL_6CELL_CUBE_PAIRED_V1.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(paired[0])); writer.writeheader(); writer.writerows(paired)

    labels = [row["scenario"].replace("feed_", "").replace("__joint_", "\nJ").replace("__ldf_", "\nL") for row in paired]
    x = np.arange(len(paired)); width = 0.36
    fig, axes = plt.subplots(2, 2, figsize=(13.5, 8.5), constrained_layout=True)
    axes[0, 0].bar(x-width/2,[row["comparison_qualified_h2_rate_mol_s"] for row in paired],width,label="comparison",color="#9ca3af")
    axes[0, 0].bar(x+width/2,[row["selected_qualified_h2_rate_mol_s"] for row in paired],width,label="selected",color="#2563eb")
    axes[0, 0].axhline(float(confirm.base.strict.DESIGN_TARGET_H2_RATE_MOL_S),color="#dc2626",ls="--")
    axes[0, 0].set_ylabel("Qualified H2 (mol/s)"); axes[0, 0].legend(frameon=False)
    axes[0, 1].bar(x-width/2,[row["comparison_worst_gate_factor"] for row in paired],width,color="#9ca3af")
    axes[0, 1].bar(x+width/2,[row["selected_worst_gate_factor"] for row in paired],width,color="#059669")
    axes[0, 1].axhline(1.0,color="#dc2626",ls="--"); axes[0, 1].set_ylabel("Worst strict-gate factor")
    axes[1, 0].bar(x,[row["shipment_improvement_percent"] for row in paired],color="#7c3aed")
    axes[1, 0].set_ylabel("Selected improvement (%)")
    axes[1, 1].bar(x,[row["reserve_margin_gain_bar"] for row in paired],color="#f59e0b")
    axes[1, 1].set_ylabel("Reserve-margin gain (bar)")
    for axis in axes.flat:
        axis.set_xticks(x, labels, fontsize=7); axis.grid(axis="y", alpha=0.25)
    fig.suptitle("Pressure-consistent full six-cell uncertainty cube", fontweight="bold")
    fig.savefig(out / "PSA_HYDRAULICALLY_FEASIBLE_FULL_6CELL_CUBE_V1.png", dpi=220)
    plt.close(fig)
    md = f"""# Pressure-consistent full six-cell uncertainty cube

- comparison policy: 6.0 bar / 6 s / 480 s
- selected policy: 6.0 bar / 4 s / 540 s
- comparison design passes: **{summary['comparison_pass_count']}/8**
- selected design passes: **{summary['selected_pass_count']}/8**
- qualified-H2 improvement: **{summary['minimum_shipment_improvement_percent']:.3f}% to {summary['maximum_shipment_improvement_percent']:.3f}%**
- minimum reserve-margin gain: **{summary['minimum_reserve_margin_gain_bar']:.4f} bar**
- selected minimum qualified H2: **{summary['selected_minimum_qualified_h2_rate_mol_s']:.8f} mol/s**
- selected maximum conservative booster duty: **{summary['selected_maximum_booster_kwh_per_kg_qualified_h2']:.4f} kWh/kg H2**
"""
    (out / "PSA_HYDRAULICALLY_FEASIBLE_FULL_6CELL_CUBE_V1.md").write_text(md, encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--workers",type=int,default=1); parser.add_argument("--indices",type=int,nargs="*"); args=parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    indices=list(range(len(cases()))) if args.indices is None else list(args.indices)
    tasks=[(index,str(OUT)) for index in indices]
    if args.workers>1 and len(tasks)>1:
        with ProcessPoolExecutor(max_workers=args.workers) as pool:
            futures={pool.submit(evaluate,task):task[0] for task in tasks}
            for future in as_completed(futures):
                row=future.result(); print(json.dumps({"completed":row["case_index"],"policy":row["policy"],"scenario":row["scenario"],"provenance":row["raw_provenance"],"design_event":row["conditional_design_event"],"wall_time_s":row["wall_time_s"]}),flush=True)
    else:
        for task in tasks:
            row=evaluate(task); print(json.dumps({"completed":row["case_index"],"wall_time_s":row["wall_time_s"]}),flush=True)
    if all((OUT/"states"/f"case_{i:03d}.json").exists() and (OUT/"states"/f"case_{i:03d}_traces.npz").exists() for i in range(len(cases()))):
        payload=aggregate(OUT); print(json.dumps({"status":payload["status"],"summary":payload["summary"]},indent=2))


if __name__ == "__main__":
    main()
