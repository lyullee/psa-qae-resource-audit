"""Extract the final-cycle phase ledger from the frozen 32-run primary PSA model.

The historical primary CSV stores only run-level outputs.  This script reruns
the exact frozen rows and traces the final eight bed phases, two equalizations,
four tank withdrawals, and two product-recycle splits.  It does not submit QPU
work.  The resulting ledger makes the primary purity/recovery event observable
from process streams and supplies an interface for a later reversible oracle.
"""

from __future__ import annotations

import csv
import json
import os
import sys
import time
from collections import deque
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RESULTS = ROOT / "10_TEA_LCA_Python" / "results" / "pycharm_publication_enhancement"
SOURCE = HERE / "psa_two_bed_spatial_tank_n2_independent_source_uncertainty_32.csv"
OUT_JSON = RESULTS / "PSA_QAE_CCE_PRIMARY_PHASE_LEDGER.json"
OUT_CSV = RESULTS / "PSA_QAE_CCE_PRIMARY_PHASE_LEDGER.csv"
OUT_MD = RESULTS / "PSA_QAE_CCE_PRIMARY_PHASE_LEDGER.md"
OUT_PNG = RESULTS / "PSA_QAE_CCE_PRIMARY_PHASE_LEDGER_FIGURE.png"
OUT_PDF = RESULTS / "PSA_QAE_CCE_PRIMARY_PHASE_LEDGER_FIGURE.pdf"

sys.path.insert(0, str(HERE.parent))


COMPONENTS = ("H2", "CO2", "CH4", "CO", "N2")
PHASE_IDENTITIES = (
    ("A", "adsorption"),
    ("B", "pressurization"),
    ("A", "blowdown"),
    ("B", "adsorption"),
    ("A", "purge"),
    ("B", "blowdown"),
    ("A", "pressurization"),
    ("B", "purge"),
)


def _float_row(row: dict[str, str], names: list[str]) -> list[float]:
    return [float(row[name]) for name in names]


def _state_summary(state, params) -> dict:
    from psa_qae.psa_spatial_network_probe_n2 import (
        cell_pressure,
        profile_cell_volumes,
        unpack,
    )

    ng, q = unpack(np.asarray(state, dtype=float), params)
    _, solid = profile_cell_volumes(params)
    gas = np.sum(ng, axis=1)
    ads = np.sum(q * solid[None, :], axis=1)
    pressure = cell_pressure(ng, params)
    return {
        "gas_component_mol": gas.tolist(),
        "adsorbed_component_mol": ads.tolist(),
        "stored_component_mol": (gas + ads).tolist(),
        "pressure_left_bar": float(pressure[0]),
        "pressure_right_bar": float(pressure[-1]),
        "pressure_min_bar": float(np.min(pressure)),
        "pressure_max_bar": float(np.max(pressure)),
    }


def _run_one(row: dict[str, str]) -> dict:
    from psa_qae.psa_spatial_network_probe_n2 import SpatialParams
    from psa_qae import psa_two_bed_spatial_tank_n2 as model

    sample = int(row["sample"])
    base_feed = np.asarray([0.655, 0.283, 0.041, 0.006, 0.014], dtype=float)
    base_feed /= base_feed.sum()
    source_y = tuple(
        _float_row(row, ["source_h2", "source_co2", "source_ch4", "source_co", "source_n2"])
    )
    params = SpatialParams(
        n_cells=4,
        P_high_bar=15.65,
        P_low_bar=float(row["P_low_bar"]),
        phase_duration_s=10.0,
        feed_y_dry=tuple(base_feed.tolist()),
        purge_y_dry=source_y,
        k_in_mol_s_bar=1.0,
        k_out_mol_s_bar=1.0,
        k_internal_mol_s_bar=5.0,
        capacity_factor=float(row["capacity_factor"]),
        affinity_factor=float(row["affinity_factor"]),
        ldf_factor=float(row["ldf_factor"]),
        max_step_points=12,
        solver_method="BDF",
    )

    phase_calls: deque[dict] = deque(maxlen=8)
    equalizations: deque[dict] = deque(maxlen=2)
    tank_calls: deque[dict] = deque(maxlen=4)
    recycle_calls: deque[dict] = deque(maxlen=2)

    original_oriented = model.oriented_step
    original_equalize = model.equalize_endpoints
    original_tank_step = model._tank_step
    original_add_recycle = model._add_recycle

    def traced_oriented(state, step, duration_s, y_in, p, *, reverse):
        before = np.asarray(state, dtype=float).copy()
        after, stream = original_oriented(
            state, step, duration_s, y_in, p, reverse=reverse
        )
        phase_calls.append(
            {
                "step": step,
                "reverse": bool(reverse),
                "duration_s": float(duration_s),
                "state_start": _state_summary(before, p),
                "state_end": _state_summary(after, p),
                "in_component_mol": np.asarray(stream["in_mol"], dtype=float).tolist(),
                "out_component_mol": np.asarray(stream["out_mol"], dtype=float).tolist(),
                "mass_balance_relative_max": float(stream["mass_balance_relative_max"]),
            }
        )
        return after, stream

    def traced_equalize(state_a, state_b, p, **kwargs):
        before_a = np.asarray(state_a, dtype=float).copy()
        before_b = np.asarray(state_b, dtype=float).copy()
        after_a, after_b, record = original_equalize(state_a, state_b, p, **kwargs)
        equalizations.append(
            {
                "state_a_start": _state_summary(before_a, p),
                "state_b_start": _state_summary(before_b, p),
                "state_a_end": _state_summary(after_a, p),
                "state_b_end": _state_summary(after_b, p),
                "record": {
                    key: (np.asarray(value, dtype=float).tolist() if isinstance(value, (np.ndarray, list, tuple)) else value)
                    for key, value in record.items()
                },
            }
        )
        return after_a, after_b, record

    def traced_tank_step(state, step, duration_s, p, tank, makeup_y, *, reverse):
        tank_before = np.asarray(tank, dtype=float).copy()
        out = original_tank_step(
            state, step, duration_s, p, tank, makeup_y, reverse=reverse
        )
        _, stream, tank_after, makeup = out
        tank_calls.append(
            {
                "step": step,
                "reverse": bool(reverse),
                "tank_start_mol": tank_before.tolist(),
                "tank_end_mol": np.asarray(tank_after, dtype=float).tolist(),
                "tank_withdrawal_mol": np.asarray(stream["tank_withdrawal_mol"], dtype=float).tolist(),
                "makeup_mol": np.asarray(makeup, dtype=float).tolist(),
            }
        )
        return out

    def traced_add_recycle(tank, product, recycle_fraction, capacity_mol):
        before = np.asarray(tank, dtype=float).copy()
        tank_after, recycle, overflow = original_add_recycle(
            tank, product, recycle_fraction, capacity_mol
        )
        product = np.asarray(product, dtype=float)
        recycle_calls.append(
            {
                "tank_start_mol": before.tolist(),
                "adsorption_product_mol": product.tolist(),
                "recycle_mol": np.asarray(recycle, dtype=float).tolist(),
                "external_product_mol": (product - np.asarray(recycle, dtype=float)).tolist(),
                "overflow_mol": np.asarray(overflow, dtype=float).tolist(),
                "tank_end_mol": np.asarray(tank_after, dtype=float).tolist(),
                "recycle_fraction": float(recycle_fraction),
            }
        )
        return tank_after, recycle, overflow

    model.oriented_step = traced_oriented
    model.equalize_endpoints = traced_equalize
    model._tank_step = traced_tank_step
    model._add_recycle = traced_add_recycle
    started = time.perf_counter()
    try:
        result = model.run_cycle(
            n_cycles=100,
            p=params,
            equalization_duration_s=2.0,
            equalization_conductance=float(row["equalization_conductance"]),
            recycle_fraction=float(row["recycle_fraction"]),
            tank_capacity_mol=100.0,
            initial_tank_moles=0.0,
        )
    finally:
        model.oriented_step = original_oriented
        model.equalize_endpoints = original_equalize
        model._tank_step = original_tank_step
        model._add_recycle = original_add_recycle

    phases = list(phase_calls)
    if len(phases) != 8 or len(equalizations) != 2 or len(tank_calls) != 4 or len(recycle_calls) != 2:
        raise AssertionError(
            f"sample {sample}: phase={len(phases)}, eq={len(equalizations)}, tank={len(tank_calls)}, recycle={len(recycle_calls)}"
        )
    for phase, (bed, expected_step) in zip(phases, PHASE_IDENTITIES):
        phase["bed"] = bed
        if phase["step"] != expected_step:
            raise AssertionError((sample, bed, phase["step"], expected_step))

    adsorption_phases = [phase for phase in phases if phase["step"] == "adsorption"]
    feed = np.sum([phase["in_component_mol"] for phase in adsorption_phases], axis=0)
    external_product = np.sum(
        [record["external_product_mol"] for record in recycle_calls], axis=0
    )
    purity = float(external_product[0] / external_product.sum())
    recovery = float(external_product[0] / feed[0])
    expected_purity = float(row["h2_product"])
    expected_recovery = float(row["h2_recovery_external_proxy"])
    if abs(purity - expected_purity) > 1.0e-9 or abs(recovery - expected_recovery) > 1.0e-9:
        raise AssertionError(
            f"sample {sample}: replay mismatch purity={purity-expected_purity}, recovery={recovery-expected_recovery}"
        )

    return {
        "sample": sample,
        "parameters": {
            key: float(row[key])
            for key in [
                "source_h2",
                "source_co2",
                "source_ch4",
                "source_co",
                "source_n2",
                "capacity_factor",
                "affinity_factor",
                "ldf_factor",
                "P_low_bar",
                "equalization_conductance",
                "recycle_fraction",
            ]
        },
        "phase_records": phases,
        "equalization_records": list(equalizations),
        "tank_withdrawal_records": list(tank_calls),
        "product_recycle_records": list(recycle_calls),
        "event_observables": {
            "feed_adsorption_in_mol": feed.tolist(),
            "external_product_mol": external_product.tolist(),
            "h2_product": purity,
            "h2_recovery_external_proxy": recovery,
            "purity_threshold": 0.9998,
            "recovery_threshold": 0.789,
            "joint_event": bool(purity >= 0.9998 and recovery >= 0.789),
        },
        "run_checks": {
            "css_residual_final": float(result["css_residual_final"]),
            "css_gate_1e_4": bool(result["css_gate_1e-4"]),
            "step_mass_balance_relative_max": float(result["step_mass_balance_relative_max"]),
            "cycle_mass_balance_relative_max": float(result["cycle_mass_balance_relative_max"]),
            "equalization_pair_mass_residual_max_mol": float(result["equalization_pair_mass_residual_max_mol"]),
            "replay_purity_abs_error": abs(purity - expected_purity),
            "replay_recovery_abs_error": abs(recovery - expected_recovery),
        },
        "runtime_seconds": float(time.perf_counter() - started),
    }


def main() -> None:
    with SOURCE.open(newline="", encoding="utf-8-sig") as handle:
        source_rows = list(csv.DictReader(handle))
    workers = int(os.environ.get("CCE_LEDGER_WORKERS", min(8, os.cpu_count() or 1)))
    workers = max(1, min(workers, len(source_rows)))
    started = time.perf_counter()
    runs: list[dict] = []
    with ProcessPoolExecutor(max_workers=workers) as pool:
        pending = {pool.submit(_run_one, row): int(row["sample"]) for row in source_rows}
        for index, future in enumerate(as_completed(pending), start=1):
            run = future.result()
            runs.append(run)
            print(
                f"completed {index}/{len(source_rows)} sample={run['sample']} "
                f"runtime={run['runtime_seconds']:.1f}s",
                flush=True,
            )
    runs.sort(key=lambda row: row["sample"])

    event_count = sum(run["event_observables"]["joint_event"] for run in runs)
    max_purity_error = max(run["run_checks"]["replay_purity_abs_error"] for run in runs)
    max_recovery_error = max(run["run_checks"]["replay_recovery_abs_error"] for run in runs)
    payload = {
        "schema": "psa-qae-cce-primary-phase-ledger/v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "frozen_primary_spatial_tank_final_cycle_phase_ledger_replayed_event_observable_not_reversible",
        "source": SOURCE.name,
        "sample_count": len(runs),
        "workers": workers,
        "components": list(COMPONENTS),
        "state_summary_per_bed": "5 gas component moles + 5 adsorbed component moles; spatial profiles retained only through endpoint pressure summaries",
        "trace_per_run": {
            "bed_phases": 8,
            "equalizations": 2,
            "tank_withdrawals": 4,
            "product_recycle_splits": 2,
        },
        "event": {
            "definition": "external H2 purity >= 0.9998 AND external H2 recovery proxy >= 0.789",
            "joint_event_count": int(event_count),
            "joint_event_fraction": float(event_count / len(runs)),
            "purity_range": [
                min(run["event_observables"]["h2_product"] for run in runs),
                max(run["event_observables"]["h2_product"] for run in runs),
            ],
            "recovery_range": [
                min(run["event_observables"]["h2_recovery_external_proxy"] for run in runs),
                max(run["event_observables"]["h2_recovery_external_proxy"] for run in runs),
            ],
        },
        "verification": {
            "css_pass_count": sum(run["run_checks"]["css_gate_1e_4"] for run in runs),
            "max_replay_purity_abs_error": float(max_purity_error),
            "max_replay_recovery_abs_error": float(max_recovery_error),
            "max_equalization_pair_mass_residual_mol": max(
                run["run_checks"]["equalization_pair_mass_residual_max_mol"] for run in runs
            ),
            "all_phase_counts_complete": all(len(run["phase_records"]) == 8 for run in runs),
            "all_event_outputs_replay_source_csv": bool(max(max_purity_error, max_recovery_error) <= 1.0e-9),
        },
        "wall_seconds": float(time.perf_counter() - started),
        "qpu_submission": False,
        "runs": runs,
        "claim_boundary": {
            "supported": "primary-model final-cycle process streams reproduce every frozen CSV purity/recovery event and expose a calibrated interface for reversible resource analysis",
            "unsupported": "plant validation, an already compiled cyclic oracle, or end-to-end quantum advantage",
        },
    }
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    rows = []
    for run in runs:
        obs = run["event_observables"]
        rows.append(
            {
                "sample": run["sample"],
                "recycle_fraction": run["parameters"]["recycle_fraction"],
                "h2_product": obs["h2_product"],
                "h2_recovery_external_proxy": obs["h2_recovery_external_proxy"],
                "joint_event": obs["joint_event"],
                "css_residual_final": run["run_checks"]["css_residual_final"],
                "replay_purity_abs_error": run["run_checks"]["replay_purity_abs_error"],
                "replay_recovery_abs_error": run["run_checks"]["replay_recovery_abs_error"],
                "runtime_seconds": run["runtime_seconds"],
            }
        )
    with OUT_CSV.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    lines = [
        "# Frozen primary PSA final-cycle phase ledger",
        "",
        f"All {len(runs)} frozen spatial-tank runs were replayed. Each final cycle records eight bed phases, two equalizations, four tank withdrawals, and two product/recycle splits. The reconstructed event outputs match the source CSV to maximum absolute errors {max_purity_error:.3e} in purity and {max_recovery_error:.3e} in recovery.",
        "",
        f"The joint event is true for {event_count}/{len(runs)} rows. All {payload['verification']['css_pass_count']}/{len(runs)} rows pass the original CSS gate. No QPU job was submitted.",
        "",
        "This closes the missing process-stream observability link for the frozen primary model. It does not compile the spatial dynamics, equalization law, tank logic, CSS repetition, or final event into one reversible circuit.",
        "",
        "| sample | recycle | purity | recovery | event | CSS residual | replay error max |",
        "|---:|---:|---:|---:|---|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row['sample']} | {row['recycle_fraction']:.6f} | {row['h2_product']:.9f} | "
            f"{row['h2_recovery_external_proxy']:.9f} | {row['joint_event']} | "
            f"{row['css_residual_final']:.3e} | {max(row['replay_purity_abs_error'], row['replay_recovery_abs_error']):.3e} |"
        )
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    purity = np.asarray([row["h2_product"] for row in rows])
    recovery = np.asarray([row["h2_recovery_external_proxy"] for row in rows])
    event = np.asarray([row["joint_event"] for row in rows], dtype=bool)
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.6), constrained_layout=True)
    axes[0].scatter(purity[~event], recovery[~event], color="#b44", label="event false")
    axes[0].scatter(purity[event], recovery[event], color="#18794e", label="event true")
    axes[0].axvline(0.9998, color="black", linestyle="--", linewidth=1)
    axes[0].axhline(0.789, color="black", linestyle="--", linewidth=1)
    axes[0].set(xlabel="external H2 purity", ylabel="external H2 recovery proxy", title="Replayed primary event")
    axes[0].legend(frameon=False)
    errors = np.maximum(
        [row["replay_purity_abs_error"] for row in rows],
        [row["replay_recovery_abs_error"] for row in rows],
    )
    axes[1].bar(np.arange(len(rows)), np.maximum(errors, 1e-18), color="#4c78a8")
    axes[1].axhline(1e-9, color="black", linestyle="--", linewidth=1, label="replay gate")
    axes[1].set(xlabel="frozen sample", ylabel="max absolute replay error", title="Stream-ledger reproduction", yscale="log")
    axes[1].legend(frameon=False)
    fig.savefig(OUT_PNG, dpi=250)
    fig.savefig(OUT_PDF)
    plt.close(fig)
    print(json.dumps({"status": payload["status"], "runs": len(runs), "events": event_count, "wall_seconds": payload["wall_seconds"], "qpu_submission": False}, indent=2))


if __name__ == "__main__":
    main()
