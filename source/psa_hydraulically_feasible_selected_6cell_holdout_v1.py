"""Predeclared six-cell/60-cycle hold-out for the pressure-consistent PSA design."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
import sys

import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import psa_qae.psa_hydraulically_feasible_policy_6cell_confirmation_v1 as confirm
import psa_qae.psa_literature_anchored_policy_full_6cell_cube as old_cube


HERE = Path(__file__).resolve().parent
PREDECLARED_SOURCE = (
    HERE
    / "results"
    / "literature_anchored_continuous_holdout_2000cm2"
    / "PSA_FINAL_CODESIGN_CONTINUOUS_HOLDOUT.json"
)
OUT = HERE / "results" / "hydraulically_feasible_selected_6cell_holdout_v1"
N_CELLS = 6
N_CYCLES = 60


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def holdout_scenarios() -> list[dict]:
    payload = json.loads(PREDECLARED_SOURCE.read_text(encoding="utf-8"))
    return payload["run_signature"]["holdout_scenarios"]


def selected_policy() -> dict:
    return {
        "policy": "selected",
        "tank_setpoint_bar": 6.0,
        "purge_active_s": 4.0,
        "adsorption_stage_s": 540.0,
    }


def cases() -> list[dict]:
    policy = selected_policy()
    return [
        {"case_index": index, **policy, **scenario}
        for index, scenario in enumerate(holdout_scenarios())
    ]


def signature() -> dict:
    sources = [
        Path(__file__).resolve(),
        Path(confirm.__file__).resolve(),
        Path(old_cube.__file__).resolve(),
        PREDECLARED_SOURCE.resolve(),
        old_cube.core.REQUIREMENT.resolve(),
    ]
    return {
        "schema": "psa-hydraulically-feasible-selected-6cell-holdout-state/v1",
        "n_cells": N_CELLS,
        "n_cycles": N_CYCLES,
        "area_cm2": float(old_cube.AREA_CM2),
        "selectivity_multiplier": float(old_cube.SELECTIVITY_MULTIPLIER),
        "area_steps": int(old_cube.AREA_STEPS),
        "qualified_h2_target_mol_s": float(
            confirm.base.strict.DESIGN_TARGET_H2_RATE_MOL_S
        ),
        "passive_fill_driving_margin_bar": float(
            confirm.screen.PASSIVE_FILL_DRIVING_MARGIN_BAR
        ),
        "booster_efficiency": float(confirm.screen.BOOSTER_EFFICIENCY),
        "policy": selected_policy(),
        "holdout_scenarios": holdout_scenarios(),
        "predeclared_source": str(PREDECLARED_SOURCE.relative_to(HERE)),
        "predeclared_before_current_design": True,
        "role": "independent interior validation excluded from policy selection",
        "source_sha256": {
            str(path.relative_to(HERE)): sha256(path) for path in sources
        },
    }


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
    raw, raw_metrics, raw_arrays = confirm.dynamic_raw(case)
    polished, polish_metrics, polish_arrays = old_cube.polish(
        raw,
        float(case["adsorption_stage_s"]),
        area_cm2=float(old_cube.AREA_CM2),
    )
    strict_event = bool(
        polish_metrics["continuous_gate_pass"]
        and polish_metrics["feasible_inventory"]
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
    work_j = float(
        raw_metrics["cumulative_internal_h2_demand_mol"]
    ) * confirm.screen.booster_work_j_per_mol(
        float(raw_metrics["min_tank_pressure_bar"]),
        float(raw_metrics["booster_discharge_pressure_bar"]),
        float(raw_metrics["booster_suction_temperature_K"]),
    )
    booster_kwh_per_kg = work_j / 3.6e6 / max(
        qualified_h2_mol * confirm.screen.HYDROGEN_MOLAR_MASS_KG_MOL,
        1.0e-30,
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
        "n_cells": N_CELLS,
        "n_cycles": N_CYCLES,
        **raw_metrics,
        "raw_h2_rate_mol_s": float(
            raw[:, confirm.base.strict.INDEX["H2"]].sum()
            / (N_CYCLES * float(polish_metrics["cycle_time_s"]))
        ),
        "polished_h2_rate_mol_s": float(
            polished[:, confirm.base.strict.INDEX["H2"]].sum()
            / (N_CYCLES * float(polish_metrics["cycle_time_s"]))
        ),
        **polish_metrics,
        "signed_quality_margin": 1.0 - float(polish_metrics["worst_gate_factor"]),
        "conservative_booster_kwh_per_kg_qualified_h2": booster_kwh_per_kg,
        "strict_event": strict_event,
        "confirmation_gate": confirmation_gate,
        "conditional_design_event": design_event,
        "trace_file": str(trace_path.relative_to(out)),
        "wall_time_s": time.time() - started,
    }
    state_path.write_text(json.dumps(row, indent=2) + "\n", encoding="utf-8")
    return row


def audit_trace(path: Path) -> None:
    with np.load(path, allow_pickle=False) as archive:
        if list(archive["components"]) != list(confirm.base.strict.COMPONENTS):
            raise AssertionError(f"component mismatch: {path}")
        for name in archive.files:
            values = np.asarray(archive[name])
            if values.dtype.kind in "biufc" and not np.isfinite(values).all():
                raise AssertionError(f"non-finite values: {path}:{name}")


def aggregate(out: Path) -> dict:
    expected = signature()
    rows = []
    for case in cases():
        index = int(case["case_index"])
        state_path = out / "states" / f"case_{index:03d}.json"
        trace_path = out / "states" / f"case_{index:03d}_traces.npz"
        row = json.loads(state_path.read_text(encoding="utf-8"))
        if row.get("run_signature") != expected:
            raise AssertionError(f"signature mismatch: {state_path}")
        audit_trace(trace_path)
        rows.append(row)
    rows.sort(key=lambda row: int(row["case_index"]))

    summary = {
        "holdout_count": len(rows),
        "direct_pass_count": int(sum(row["conditional_design_event"] for row in rows)),
        "direct_fail_count": int(sum(not row["conditional_design_event"] for row in rows)),
        "minimum_qualified_h2_rate_mol_s": min(
            float(row["qualified_h2_rate_mol_s"]) for row in rows
        ),
        "minimum_h2_recovery": min(float(row["aggregate_h2_recovery"]) for row in rows),
        "minimum_tank_pressure_bar": min(
            float(row["min_tank_pressure_bar"]) for row in rows
        ),
        "minimum_reserve_margin_bar": min(
            float(row["reserve_margin_bar"]) for row in rows
        ),
        "maximum_worst_gate_factor": max(
            float(row["worst_gate_factor"]) for row in rows
        ),
        "maximum_n2_ppm": max(float(row["maximum_n2_ppm"]) for row in rows),
        "maximum_booster_kwh_per_kg_qualified_h2": max(
            float(row["conservative_booster_kwh_per_kg_qualified_h2"])
            for row in rows
        ),
        "maximum_css_residual_final": max(
            float(row["css_residual_final"]) for row in rows
        ),
        "maximum_cycle_mass_balance_relative": max(
            float(row["cycle_mass_balance_relative_max"]) for row in rows
        ),
        "all_passive_fill_checks_pass": bool(
            all(row["passive_fill_gate"] for row in rows)
        ),
        "all_trace_integrity_checks_pass": True,
    }
    payload = {
        "schema": "psa-hydraulically-feasible-selected-6cell-holdout/v1",
        "status": "predeclared_pressure_consistent_six_cell_holdout_complete",
        "run_signature": expected,
        "rows": rows,
        "summary": summary,
        "claim_limits": [
            "The eight Sobol interior points were declared before the pressure-consistent design was selected.",
            "The hold-out set tests interpolation inside the deterministic engineering envelope; it is not a plant-calibrated probability sample.",
            "The passive refill check uses a static 0.2-bar driving margin and the booster duty is a conservative ideal-gas estimate.",
        ],
    }
    out.mkdir(parents=True, exist_ok=True)
    json_path = out / "PSA_HYDRAULICALLY_FEASIBLE_SELECTED_6CELL_HOLDOUT_V1.json"
    json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    flat = [
        {key: value for key, value in row.items() if not isinstance(value, (dict, list))}
        for row in rows
    ]
    fieldnames = []
    for row in flat:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with (
        out / "PSA_HYDRAULICALLY_FEASIBLE_SELECTED_6CELL_HOLDOUT_V1.csv"
    ).open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(flat)

    labels = [f"H{i}" for i in range(len(rows))]
    x = np.arange(len(rows))
    fig, axes = plt.subplots(2, 2, figsize=(11.5, 8.0), constrained_layout=True)
    axes[0, 0].bar(x, [row["qualified_h2_rate_mol_s"] for row in rows], color="#2563eb")
    axes[0, 0].axhline(float(confirm.base.strict.DESIGN_TARGET_H2_RATE_MOL_S), color="#dc2626", linestyle="--")
    axes[0, 0].set(ylabel="Qualified H2 (mol/s)", title="Shipment target")
    axes[0, 1].bar(x, [row["worst_gate_factor"] for row in rows], color="#059669")
    axes[0, 1].axhline(1.0, color="#dc2626", linestyle="--")
    axes[0, 1].set(ylabel="Worst strict-gate factor", title="Product specification")
    axes[1, 0].bar(x, [row["reserve_margin_bar"] for row in rows], color="#f59e0b")
    axes[1, 0].axhline(0.0, color="#dc2626", linestyle="--")
    axes[1, 0].set(ylabel="Reserve margin (bar)", title="Tank reserve")
    axes[1, 1].bar(x, [row["conservative_booster_kwh_per_kg_qualified_h2"] for row in rows], color="#7c3aed")
    axes[1, 1].set(ylabel="Booster duty (kWh/kg H2)", title="Conservative internal-H2 compression")
    for axis in axes.flat:
        axis.set_xticks(x, labels)
        axis.grid(axis="y", alpha=0.25)
    fig.suptitle("Predeclared pressure-consistent six-cell hold-out", fontweight="bold")
    fig.savefig(
        out / "PSA_HYDRAULICALLY_FEASIBLE_SELECTED_6CELL_HOLDOUT_V1.png",
        dpi=220,
    )
    plt.close(fig)

    report = f"""# Pressure-consistent selected-policy six-cell hold-out

- selected policy: 6.0 bar / 4 s / 540 s
- predeclared direct passes: **{summary['direct_pass_count']}/{summary['holdout_count']}**
- minimum qualified H2: **{summary['minimum_qualified_h2_rate_mol_s']:.8f} mol/s**
- maximum strict-gate factor: **{summary['maximum_worst_gate_factor']:.6f}**
- minimum reserve margin: **{summary['minimum_reserve_margin_bar']:.4f} bar**
- maximum conservative booster duty: **{summary['maximum_booster_kwh_per_kg_qualified_h2']:.4f} kWh/kg H2**
- maximum CSS residual: **{summary['maximum_css_residual_final']:.3e}**
- maximum cycle mass-balance relative error: **{summary['maximum_cycle_mass_balance_relative']:.3e}**
"""
    (out / "PSA_HYDRAULICALLY_FEASIBLE_SELECTED_6CELL_HOLDOUT_V1.md").write_text(
        report,
        encoding="utf-8",
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
                print(
                    json.dumps(
                        {
                            "completed": row["case_index"],
                            "scenario": row["scenario"],
                            "design_event": row["conditional_design_event"],
                            "worst_gate_factor": row["worst_gate_factor"],
                            "qualified_h2_rate_mol_s": row["qualified_h2_rate_mol_s"],
                            "wall_time_s": row["wall_time_s"],
                        }
                    ),
                    flush=True,
                )
    else:
        for task in tasks:
            row = evaluate(task)
            print(json.dumps({"completed": row["case_index"], "wall_time_s": row["wall_time_s"]}), flush=True)
    if all(
        (OUT / "states" / f"case_{i:03d}.json").exists()
        and (OUT / "states" / f"case_{i:03d}_traces.npz").exists()
        for i in range(len(cases()))
    ):
        payload = aggregate(OUT)
        print(json.dumps({"status": payload["status"], "summary": payload["summary"]}, indent=2))


if __name__ == "__main__":
    main()
