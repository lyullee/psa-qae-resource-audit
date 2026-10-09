"""Audit a fixed physical CSS horizon and explicit state-register scale.

The frozen 32-run primary model already propagates two spatial beds and a
finite product/purge tank for 100 cycles.  This script reruns those exact rows,
retains every cycle-boundary state and stream ledger, and asks three questions:

1. What fixed cycle horizon is sufficient for every row to remain below the
   physical CSS tolerance and retain its final event label?
2. What fixed-point precision preserves final CSS/event classification while
   keeping state quantization below 10% of the CSS L1 tolerance?
3. What data-register scale follows for an explicit clean out-of-place
   architecture before nonlinear transport and its workspace are counted?

This is a physical-horizon and register-floor audit.  It does not synthesize
the nonlinear ODE transport map and therefore does not claim a completed
reversible CSS oracle.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RESULTS = ROOT / "10_TEA_LCA_Python" / "results" / "pycharm_publication_enhancement"
SOURCE = HERE / "psa_two_bed_spatial_tank_n2_independent_source_uncertainty_32.csv"
CACHE = HERE / "cce_primary_physical_css_horizon_cache.npz"
OUT_JSON = RESULTS / "PSA_QAE_CCE_PRIMARY_PHYSICAL_CSS_HORIZON_AUDIT.json"
OUT_CSV = RESULTS / "PSA_QAE_CCE_PRIMARY_PHYSICAL_CSS_HORIZON_AUDIT.csv"
OUT_MD = RESULTS / "PSA_QAE_CCE_PRIMARY_PHYSICAL_CSS_HORIZON_AUDIT.md"
OUT_PNG = RESULTS / "PSA_QAE_CCE_PRIMARY_PHYSICAL_CSS_HORIZON_AUDIT_FIGURE.png"
OUT_PDF = RESULTS / "PSA_QAE_CCE_PRIMARY_PHYSICAL_CSS_HORIZON_AUDIT_FIGURE.pdf"

CSS_GATE = 1.0e-4
STATE_ERROR_BUDGET = 0.1 * CSS_GATE
N_CYCLES = 100
BITS = [8, 10, 12, 14, 16, 18, 20, 22, 24]

sys.path.insert(0, str(HERE.parent))


def _float_row(row: dict[str, str], names: list[str]) -> list[float]:
    return [float(row[name]) for name in names]


def _run_one(row: dict[str, str]) -> dict:
    from psa_qae.psa_spatial_network_probe_n2 import SpatialParams
    from psa_qae.psa_two_bed_spatial_tank_n2 import run_cycle

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
    started = time.perf_counter()
    result = run_cycle(
        n_cycles=N_CYCLES,
        p=params,
        equalization_duration_s=2.0,
        equalization_conductance=float(row["equalization_conductance"]),
        recycle_fraction=float(row["recycle_fraction"]),
        tank_capacity_mol=100.0,
        initial_tank_moles=0.0,
        trace_cycle_states=True,
    )
    history = result["css_history"]
    first = history[0]
    boundaries = [
        np.r_[first["state_a_start"], first["state_b_start"], first["tank_start_mol"]]
    ]
    boundaries.extend(
        np.r_[record["state_a_end"], record["state_b_end"], record["tank_end_mol"]]
        for record in history
    )
    products = np.asarray([record["product_external_mol"] for record in history], dtype=float)
    feeds = np.asarray([record["feed_adsorption_in_mol"] for record in history], dtype=float)
    residual_max = np.asarray([record["css_residual_max"] for record in history], dtype=float)
    residual_l1 = np.asarray([record["css_residual_l1"] for record in history], dtype=float)
    labels = np.asarray([record["joint_anchor_event"] for record in history], dtype=bool)
    expected_purity = float(row["h2_product"])
    expected_recovery = float(row["h2_recovery_external_proxy"])
    if abs(float(result["product_external_y"][0]) - expected_purity) > 1.0e-9:
        raise AssertionError((row["sample"], "purity replay"))
    if abs(float(result["h2_recovery_external_proxy"]) - expected_recovery) > 1.0e-9:
        raise AssertionError((row["sample"], "recovery replay"))
    return {
        "sample": int(row["sample"]),
        "boundaries": np.asarray(boundaries, dtype=float),
        "products": products,
        "feeds": feeds,
        "residual_max": residual_max,
        "residual_l1": residual_l1,
        "labels": labels,
        "runtime_seconds": float(time.perf_counter() - started),
    }


def _save_cache(records: list[dict]) -> None:
    records = sorted(records, key=lambda item: item["sample"])
    np.savez_compressed(
        CACHE,
        samples=np.asarray([item["sample"] for item in records], dtype=int),
        boundaries=np.stack([item["boundaries"] for item in records]),
        products=np.stack([item["products"] for item in records]),
        feeds=np.stack([item["feeds"] for item in records]),
        residual_max=np.stack([item["residual_max"] for item in records]),
        residual_l1=np.stack([item["residual_l1"] for item in records]),
        labels=np.stack([item["labels"] for item in records]),
        runtime_seconds=np.asarray([item["runtime_seconds"] for item in records]),
    )


def _build_cache() -> None:
    with SOURCE.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    workers = int(os.environ.get("CCE_PHYSICAL_CSS_WORKERS", min(8, os.cpu_count() or 1)))
    workers = max(1, min(workers, len(rows)))
    records: list[dict] = []
    with ProcessPoolExecutor(max_workers=workers) as pool:
        pending = {pool.submit(_run_one, row): int(row["sample"]) for row in rows}
        for index, future in enumerate(as_completed(pending), start=1):
            record = future.result()
            records.append(record)
            print(
                f"physical CSS {index}/{len(rows)} sample={record['sample']} "
                f"runtime={record['runtime_seconds']:.1f}s",
                flush=True,
            )
    _save_cache(records)


def _tail_horizon(mask: np.ndarray) -> int | None:
    """Return one-based first cycle from which every remaining mask value is true."""
    suffix = np.logical_and.accumulate(np.asarray(mask, dtype=bool)[::-1])[::-1]
    indices = np.flatnonzero(suffix)
    return int(indices[0] + 1) if len(indices) else None


def _event_horizon(labels: np.ndarray) -> int | None:
    final = bool(labels[-1])
    return _tail_horizon(np.asarray(labels, dtype=bool) == final)


def _quantize(values: np.ndarray, scales: np.ndarray, bits: int) -> np.ndarray:
    levels = float((1 << bits) - 1)
    codes = np.rint(np.clip(values / scales, 0.0, 1.0) * levels)
    return codes * scales / levels


def _css_from_boundaries(boundaries: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    previous = boundaries[:, :-1, :]
    current = boundaries[:, 1:, :]
    delta = np.abs(current - previous)
    strict = np.max(delta / np.maximum(np.abs(previous), 1.0e-10), axis=2)
    a_prev, b_prev, tank_prev = previous[:, :, :40], previous[:, :, 40:80], previous[:, :, 80:]
    a_delta, b_delta, tank_delta = delta[:, :, :40], delta[:, :, 40:80], delta[:, :, 80:]
    a_l1 = np.sum(a_delta, axis=2) / np.maximum(np.sum(np.abs(a_prev), axis=2), 1.0e-12)
    b_l1 = np.sum(b_delta, axis=2) / np.maximum(np.sum(np.abs(b_prev), axis=2), 1.0e-12)
    tank_den = np.sum(np.abs(tank_prev), axis=2)
    empty_den = np.sum(np.abs(a_prev), axis=2) + np.sum(np.abs(b_prev), axis=2)
    tank_l1 = np.sum(tank_delta, axis=2) / np.maximum(np.where(tank_den > 0.0, tank_den, empty_den), 1.0e-12)
    return strict, np.maximum.reduce([a_l1, b_l1, tank_l1])


def _event_from_streams(products: np.ndarray, feeds: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    purity = products[:, :, 0] / np.maximum(products.sum(axis=2), 1.0e-12)
    recovery = products[:, :, 0] / np.maximum(feeds[:, :, 0], 1.0e-12)
    return purity, recovery, (purity >= 0.9998) & (recovery >= 0.789)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rerun", action="store_true", help="repeat all 32 physical 100-cycle runs")
    args = parser.parse_args()
    if args.rerun or not CACHE.exists():
        _build_cache()

    cache = np.load(CACHE)
    samples = cache["samples"]
    boundaries = cache["boundaries"]
    products = cache["products"]
    feeds = cache["feeds"]
    residual_max = cache["residual_max"]
    residual_l1 = cache["residual_l1"]
    labels = cache["labels"]
    runtimes = cache["runtime_seconds"]
    if boundaries.shape != (32, 101, 85):
        raise AssertionError(boundaries.shape)

    strict_horizons = [_tail_horizon(row < CSS_GATE) for row in residual_max]
    l1_horizons = [_tail_horizon(row < CSS_GATE) for row in residual_l1]
    event_horizons = [_event_horizon(row) for row in labels]
    if any(value is None for value in strict_horizons + l1_horizons + event_horizons):
        raise AssertionError("one or more physical rows fail to settle within 100 cycles")
    physical_joint_horizons = [max(a, b) for a, b in zip(strict_horizons, event_horizons)]

    state_scales = np.maximum(np.max(boundaries, axis=(0, 1)), 1.0e-14)[None, None, :]
    stream_values = np.concatenate([products, feeds], axis=2)
    stream_scales = np.maximum(np.max(stream_values, axis=(0, 1)), 1.0e-14)[None, None, :]
    _, _, event_reference = _event_from_streams(products, feeds)

    quant_rows = []
    for bits in BITS:
        qb = _quantize(boundaries, state_scales, bits)
        qs = _quantize(stream_values, stream_scales, bits)
        q_strict, q_l1 = _css_from_boundaries(qb)
        _, _, q_event = _event_from_streams(qs[:, :, :5], qs[:, :, 5:])
        q_strict_horizons = [_tail_horizon(row < CSS_GATE) for row in q_strict]
        q_l1_horizons = [_tail_horizon(row < CSS_GATE) for row in q_l1]
        q_event_horizons = [_event_horizon(row) for row in q_event]
        final_state_error = np.sum(np.abs(qb[:, -1, :] - boundaries[:, -1, :]), axis=1) / np.maximum(
            np.sum(np.abs(boundaries[:, -1, :]), axis=1), 1.0e-12
        )
        all_horizons = q_strict_horizons + q_l1_horizons + q_event_horizons
        quantized_settles = all(value is not None for value in all_horizons)
        quantized_joint = (
            [max(a, b) for a, b in zip(q_strict_horizons, q_event_horizons)]
            if quantized_settles
            else []
        )
        row = {
            "bits_per_scalar": bits,
            "p95_final_state_relative_l1_error": float(np.quantile(final_state_error, 0.95)),
            "max_final_state_relative_l1_error": float(np.max(final_state_error)),
            "strict_css_classification_match_fraction_all_cycles": float(np.mean((q_strict < CSS_GATE) == (residual_max < CSS_GATE))),
            "l1_css_classification_match_fraction_all_cycles": float(np.mean((q_l1 < CSS_GATE) == (residual_l1 < CSS_GATE))),
            "event_label_match_fraction_all_cycles": float(np.mean(q_event == event_reference)),
            "final_strict_css_pass_count": int(np.sum(q_strict[:, -1] < CSS_GATE)),
            "final_l1_css_pass_count": int(np.sum(q_l1[:, -1] < CSS_GATE)),
            "final_event_label_match_count": int(np.sum(q_event[:, -1] == event_reference[:, -1])),
            "quantized_settles_within_100_cycles": quantized_settles,
            "max_quantized_joint_tail_horizon": max(quantized_joint) if quantized_joint else None,
            "safe_fixed_horizon": max(max(physical_joint_horizons), max(quantized_joint)) if quantized_joint else None,
            "physical_tail_horizon_exact_match_count": int(sum(q == p for q, p in zip(q_strict_horizons, strict_horizons) if q is not None)),
            "within_state_error_budget": float(np.quantile(final_state_error, 0.95)) <= STATE_ERROR_BUDGET,
        }
        row["passes_register_floor_gate"] = bool(
            row["within_state_error_budget"]
            and row["final_strict_css_pass_count"] == 32
            and row["final_l1_css_pass_count"] == 32
            and row["final_event_label_match_count"] == 32
            and row["quantized_settles_within_100_cycles"]
        )
        quant_rows.append(row)

    selected = next((row for row in quant_rows if row["passes_register_floor_gate"]), None)
    if selected is None:
        raise AssertionError("no fixed-point precision passes the declared register-floor gate")

    state_scalars = int(boundaries.shape[2])
    stream_scalars = int(stream_values.shape[2])
    bits = int(selected["bits_per_scalar"])
    fixed_horizon = int(selected["safe_fixed_horizon"])
    per_run_rows = []
    for index, sample in enumerate(samples):
        per_run_rows.append(
            {
                "sample": int(sample),
                "strict_css_tail_horizon": int(strict_horizons[index]),
                "l1_css_tail_horizon": int(l1_horizons[index]),
                "event_tail_horizon": int(event_horizons[index]),
                "joint_strict_css_event_horizon": int(physical_joint_horizons[index]),
                "final_event": bool(labels[index, -1]),
                "final_strict_css_residual": float(residual_max[index, -1]),
                "final_l1_css_residual": float(residual_l1[index, -1]),
                "runtime_seconds": float(runtimes[index]),
            }
        )

    payload = {
        "schema": "psa-qae-cce-primary-physical-css-horizon-audit/v1",
        "status": "physical_tank_spatial_css_horizon_and_register_accounting_quantified_transport_unitary_open",
        "qpu_submission": False,
        "source": {
            "runs": int(len(samples)),
            "cycles_per_run": N_CYCLES,
            "cells_per_bed": 4,
            "components": 5,
            "bed_state_scalars_each": 40,
            "tank_state_scalars": 5,
            "total_cycle_boundary_state_scalars": state_scalars,
            "event_stream_scalars": stream_scalars,
            "physical_model": "two spatial finite-volume beds plus finite five-component recycle/purge tank",
        },
        "physical_horizon": {
            "css_gate": CSS_GATE,
            "strict_css_final_pass_count": int(np.sum(residual_max[:, -1] < CSS_GATE)),
            "l1_css_final_pass_count": int(np.sum(residual_l1[:, -1] < CSS_GATE)),
            "final_event_count": int(np.sum(labels[:, -1])),
            "max_strict_css_tail_horizon": int(max(strict_horizons)),
            "max_l1_css_tail_horizon": int(max(l1_horizons)),
            "max_event_tail_horizon": int(max(event_horizons)),
            "max_joint_strict_css_event_horizon": int(max(physical_joint_horizons)),
            "median_joint_strict_css_event_horizon": float(np.median(physical_joint_horizons)),
            "all_rows_settle_within_100_cycles": True,
        },
        "fixed_point_screen": {
            "state_relative_l1_error_budget": STATE_ERROR_BUDGET,
            "rows": quant_rows,
            "selected": selected,
        },
        "reversible_register_accounting": {
            "bits_per_scalar": bits,
            "state_scalars": state_scalars,
            "stream_scalars": stream_scalars,
            "single_physical_state_data_qubits": state_scalars * bits,
            "out_of_place_current_plus_next_state_data_qubits": 2 * state_scalars * bits,
            "out_of_place_current_next_state_plus_raw_event_stream_data_qubits": (2 * state_scalars + stream_scalars) * bits,
            "interpretation": "explicit clean out-of-place data registers; an architectural accounting point, not a universal circuit lower bound",
            "safe_fixed_cycle_horizon": fixed_horizon,
            "forward_cycle_map_invocations": fixed_horizon,
            "clean_compute_uncompute_cycle_map_invocations": 2 * fixed_horizon,
            "excluded": [
                "nonlinear ODE transport arithmetic",
                "valve and equilibrium-function workspace",
                "cycle-map state update and checkpoint/uncomputation workspace",
                "uncertainty-state loading",
                "routing, noise correction, and fault tolerance",
            ],
        },
        "per_run": per_run_rows,
        "claim_boundary": {
            "supported": "fixed physical tank/spatial CSS horizon across the frozen 32-row design and an accuracy-screened clean out-of-place state/stream data-register accounting point",
            "unsupported": "a synthesized reversible nonlinear physical cycle map, end-to-end physical CSS oracle, hardware feasibility, external H2 validation, or quantum advantage",
        },
    }
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with OUT_CSV.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(per_run_rows[0]))
        writer.writeheader()
        writer.writerows(per_run_rows)

    lines = [
        "# Physical tank/spatial CSS horizon and reversible register accounting",
        "",
        "The frozen 32 primary rows were rerun for 100 cycles with all 85 cycle-boundary physical state scalars retained: 40 gas/adsorbed coordinates per bed and five finite-tank component inventories. Per-cycle product and feed streams were retained for the frozen purity/recovery event.",
        "",
        f"All 32 rows pass both final strict and L1 CSS gates `{CSS_GATE:.0e}`. The latest tail-stable strict-CSS horizon is cycle **{max(strict_horizons)}**, the latest event-label horizon is cycle **{max(event_horizons)}**, and the latest joint physical horizon is cycle **{max(physical_joint_horizons)}**.",
        "",
        f"The first fixed-point precision satisfying the final CSS/event conditions and p95 state-error budget `{STATE_ERROR_BUDGET:.0e}` is **{bits} bits per scalar**. Conservatively combining the physical and quantized horizons gives a fixed horizon of **{fixed_horizon} cycles**.",
        "",
        f"At {bits} bits, one 85-scalar physical state occupies **{state_scalars * bits:,} data qubits**. An explicit clean out-of-place layout with separate current/next states uses **{2 * state_scalars * bits:,}**, and retaining all ten raw feed/product stream scalars raises that accounting point to **{(2 * state_scalars + stream_scalars) * bits:,} qubits** before nonlinear transport or workspace. These are architectural data-register counts, not universal circuit lower bounds. A clean fixed-horizon probability oracle calls an eventual reversible cycle unitary **{fixed_horizon}** times forward and **{fixed_horizon}** times in reverse.",
        "",
        "This closes the physical-horizon and data-register accounting gap. The nonlinear pressure/flow/equilibrium/kinetic cycle unitary is not synthesized, so stable physical/reversible CSS remains an open implementation gate rather than a completed circuit.",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    fig, axes = plt.subplots(1, 3, figsize=(13.2, 4.4), constrained_layout=True)
    order = np.argsort(physical_joint_horizons)
    axes[0].plot(np.arange(1, 33), np.asarray(strict_horizons)[order], "o-", label="strict CSS")
    axes[0].plot(np.arange(1, 33), np.asarray(event_horizons)[order], "s-", label="event label")
    axes[0].plot(np.arange(1, 33), np.asarray(physical_joint_horizons)[order], "^-", label="joint")
    axes[0].set(xlabel="run, sorted by joint horizon", ylabel="tail-stable cycle", title="Physical convergence horizon")
    axes[0].grid(alpha=0.25); axes[0].legend(fontsize=8)

    bit_values = [row["bits_per_scalar"] for row in quant_rows]
    errors = [row["p95_final_state_relative_l1_error"] for row in quant_rows]
    axes[1].semilogy(bit_values, errors, "o-", color="#2563eb")
    axes[1].axhline(STATE_ERROR_BUDGET, color="#b91c1c", ls="--", label="10% of CSS gate")
    axes[1].axvline(bits, color="#166534", ls=":", label=f"selected {bits} bits")
    axes[1].set(xlabel="bits per physical scalar", ylabel="p95 final-state relative L1 error", title="Fixed-point state precision")
    axes[1].grid(alpha=0.25, which="both"); axes[1].legend(fontsize=8)

    data_qubits = [(2 * state_scalars + stream_scalars) * value for value in bit_values]
    axes[2].plot(bit_values, data_qubits, "o-", color="#7c3aed")
    axes[2].scatter([bits], [(2 * state_scalars + stream_scalars) * bits], color="#b91c1c", s=70, zorder=3)
    axes[2].set(xlabel="bits per physical scalar", ylabel="out-of-place state + raw-stream qubits", title="Explicit register accounting")
    axes[2].grid(alpha=0.25)
    axes[2].annotate(
        f"{(2 * state_scalars + stream_scalars) * bits:,} qubits\ntransport workspace excluded",
        (bits, (2 * state_scalars + stream_scalars) * bits),
        xytext=(bits - 5.0, (2 * state_scalars + stream_scalars) * bits + 500),
        arrowprops={"arrowstyle": "->", "color": "#b91c1c"},
        fontsize=8.5,
    )
    fig.suptitle("Physical CSS settles, while explicit reversible spatial/tank registers remain large", fontsize=14, fontweight="bold")
    fig.savefig(OUT_PNG, dpi=260)
    fig.savefig(OUT_PDF)
    plt.close(fig)

    print(
        json.dumps(
            {
                "status": payload["status"],
                "max_physical_joint_horizon": max(physical_joint_horizons),
                "selected_bits": bits,
                "safe_fixed_horizon": fixed_horizon,
                "out_of_place_data_qubits_with_raw_streams": (2 * state_scalars + stream_scalars) * bits,
                "qpu_submission": False,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
