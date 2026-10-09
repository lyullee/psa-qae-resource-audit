"""Compile the calibrated phase-map variable weighted sums to primitive gates.

This is deliberately a partial resource audit.  It compiles each scalar affine
map's variable term as a Qiskit WeightedAdder with sign handling.  Constant
injection, state update, equalization, cyclic-steady-state iteration, event
comparison, state preparation, routing, and fault tolerance remain out of scope.
"""

from __future__ import annotations

import csv
import json
import sys
import time
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit.circuit.library import WeightedAdder


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RESULTS = ROOT / "10_TEA_LCA_Python" / "results" / "pycharm_publication_enhancement"
BRIDGE = RESULTS / "PSA_QAE_CCE_CALIBRATED_ONE_CYCLE_PHASE_MAP.json"
SCREEN = RESULTS / "PSA_QAE_CCE_PHASE_MAP_FIXED_POINT_SCREEN.json"
OUT_JSON = RESULTS / "PSA_QAE_CCE_PHASE_MAP_AFFINE_BLOCK_COMPILE.json"
OUT_CSV = RESULTS / "PSA_QAE_CCE_PHASE_MAP_AFFINE_BLOCK_COMPILE.csv"
OUT_MD = RESULTS / "PSA_QAE_CCE_PHASE_MAP_AFFINE_BLOCK_COMPILE.md"
OUT_PNG = RESULTS / "PSA_QAE_CCE_PHASE_MAP_AFFINE_BLOCK_COMPILE_FIGURE.png"
OUT_PDF = RESULTS / "PSA_QAE_CCE_PHASE_MAP_AFFINE_BLOCK_COMPILE_FIGURE.pdf"

sys.path.insert(0, str(HERE.parent))
from psa_qae.cce_phase_map_fixed_point_screen import integer_spec  # noqa: E402


TARGET_NAMES = [
    "delta_gas_h2",
    "delta_gas_co2",
    "delta_gas_ch4",
    "delta_gas_n2",
    "delta_q_h2",
    "delta_q_co2",
    "delta_q_ch4",
    "delta_q_n2",
    "outlet_h2",
]


def signed_weighted_adder(weights: list[int], negative: np.ndarray) -> QuantumCircuit:
    adder = WeightedAdder(len(weights), weights)
    circuit = QuantumCircuit(adder.num_qubits, name="signed_weighted_sum")
    negative_indices = np.flatnonzero(negative)
    for index in negative_indices:
        circuit.x(int(index))
    circuit.compose(adder, inplace=True)
    for index in negative_indices:
        circuit.x(int(index))
    return circuit


def main() -> None:
    bridge = json.loads(BRIDGE.read_text(encoding="utf-8"))
    screen = json.loads(SCREEN.read_text(encoding="utf-8"))
    selected = screen["minimum_register_proxy_configuration_within_both_budgets"]
    if selected is None:
        raise RuntimeError("The fixed-point screen has no accuracy-feasible configuration.")
    input_bits = int(selected["bits_per_input"])
    sum_bits = int(selected["sum_bits_per_scalar_output"])

    rows: list[dict] = []
    started = time.perf_counter()
    phase_order = list(bridge["full_fit_models"])
    for phase_index, phase in enumerate(phase_order, start=1):
        spec = bridge["full_fit_models"][phase]
        for target_index, target_name in enumerate(TARGET_NAMES):
            isum = integer_spec(spec, input_bits, target_index, sum_bits)
            weights = [int(value) for value in isum["integer_weights"]]
            negative = np.asarray(isum["negative_mask"], dtype=bool)
            circuit = signed_weighted_adder(weights, negative)
            t0 = time.perf_counter()
            compiled = transpile(
                circuit,
                basis_gates=["u", "cx"],
                optimization_level=0,
            )
            elapsed = time.perf_counter() - t0
            operations = compiled.count_ops()
            rows.append(
                {
                    "phase": phase,
                    "target_index": target_index,
                    "target": target_name,
                    "input_bits_per_active_feature": input_bits,
                    "active_features": len(isum["active_indices"]),
                    "state_qubits": len(weights),
                    "sum_qubits": sum_bits,
                    "ancilla_qubits": int(circuit.num_qubits - len(weights) - sum_bits),
                    "logical_qubits": int(compiled.num_qubits),
                    "nonzero_integer_weights": int(np.count_nonzero(weights)),
                    "negative_bit_controls": int(np.count_nonzero(negative)),
                    "forward_depth_all_to_all": int(compiled.depth()),
                    "forward_size": int(compiled.size()),
                    "forward_cx": int(operations.get("cx", 0)),
                    "forward_u": int(operations.get("u", 0)),
                    "clean_compute_uncompute_depth_serial_bound": int(2 * compiled.depth()),
                    "clean_compute_uncompute_cx": int(2 * operations.get("cx", 0)),
                    "clean_compute_uncompute_u": int(2 * operations.get("u", 0)),
                    "transpile_seconds": float(elapsed),
                }
            )
        print(f"compiled phase {phase_index}/{len(phase_order)}: {phase}", flush=True)

    phase_summaries = []
    for phase in phase_order:
        selected_rows = [row for row in rows if row["phase"] == phase]
        phase_summaries.append(
            {
                "phase": phase,
                "scalar_blocks": len(selected_rows),
                "max_logical_qubits_reusing_scalar_workspace": max(
                    row["logical_qubits"] for row in selected_rows
                ),
                "serial_forward_depth": sum(
                    row["forward_depth_all_to_all"] for row in selected_rows
                ),
                "serial_forward_cx": sum(row["forward_cx"] for row in selected_rows),
                "serial_clean_compute_uncompute_depth_bound": sum(
                    row["clean_compute_uncompute_depth_serial_bound"]
                    for row in selected_rows
                ),
                "serial_clean_compute_uncompute_cx": sum(
                    row["clean_compute_uncompute_cx"] for row in selected_rows
                ),
            }
        )

    full_cycle = {
        "scalar_blocks": len(rows),
        "max_logical_qubits_reusing_scalar_workspace": max(
            row["logical_qubits"] for row in rows
        ),
        "serial_forward_depth": sum(row["forward_depth_all_to_all"] for row in rows),
        "serial_forward_cx": sum(row["forward_cx"] for row in rows),
        "serial_clean_compute_uncompute_depth_bound": sum(
            row["clean_compute_uncompute_depth_serial_bound"] for row in rows
        ),
        "serial_clean_compute_uncompute_cx": sum(
            row["clean_compute_uncompute_cx"] for row in rows
        ),
        "total_transpile_seconds": float(time.perf_counter() - started),
    }
    payload = {
        "schema": "psa-qae-cce-phase-map-affine-block-compile/v1",
        "status": "calibrated_affine_variable_terms_compiled_cycle_oracle_still_open",
        "source_bridge": BRIDGE.name,
        "source_fixed_point_screen": SCREEN.name,
        "selected_accuracy_feasible_fixed_point_configuration": selected,
        "compile_basis": ["u", "cx"],
        "coupling_assumption": "all_to_all_no_backend_routing",
        "optimization_level": 0,
        "scalar_blocks": rows,
        "phase_summaries": phase_summaries,
        "full_cycle_affine_block_serial_bound": full_cycle,
        "limitations": [
            "Only variable weighted sums of the fitted affine maps are compiled.",
            "Constant injection and state-register update are not compiled.",
            "The exact classical equalization step is not reversible here.",
            "Repeated cyclic-steady-state convergence and the primary purity/recovery event comparator are not compiled.",
            "State preparation, device routing, noise, and fault-tolerant overhead are excluded.",
            "Compute-uncompute numbers are twice the compiled forward blocks and assume serial workspace reuse.",
        ],
    }
    OUT_JSON.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    with OUT_CSV.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    lines = [
        "# Primitive-gate compilation of calibrated phase-map affine blocks",
        "",
        f"The accuracy-feasible fixed-point point is {input_bits} input bits per active feature and a {sum_bits}-bit scalar accumulator. Each of the 72 scalar variable weighted sums was transpiled independently to `u`/`cx` with all-to-all connectivity and optimization level 0.",
        "",
        "| phase | max logical qubits | forward CX | forward serial depth | clean compute-uncompute CX |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in phase_summaries:
        lines.append(
            f"| {row['phase']} | {row['max_logical_qubits_reusing_scalar_workspace']:,} | "
            f"{row['serial_forward_cx']:,} | {row['serial_forward_depth']:,} | "
            f"{row['serial_clean_compute_uncompute_cx']:,} |"
        )
    lines += [
        "",
        f"Across the eight-phase schedule, the 72 affine variable blocks require {full_cycle['max_logical_qubits_reusing_scalar_workspace']:,} logical qubits with scalar-workspace reuse, {full_cycle['serial_forward_cx']:,} forward CX gates, and a serial forward depth of {full_cycle['serial_forward_depth']:,}. A clean compute-uncompute accounting doubles this to {full_cycle['serial_clean_compute_uncompute_cx']:,} CX gates before state update, equalization, CSS, event logic, loading, or routing.",
        "",
        "This is a measured primitive-gate resource layer, not a complete cyclic PSA oracle.",
        "",
        f"Artifacts: {OUT_JSON.name}, {OUT_CSV.name}, {OUT_PNG.name}.",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    labels = [row["phase"] for row in phase_summaries]
    forward_cx = [row["serial_forward_cx"] for row in phase_summaries]
    clean_cx = [row["serial_clean_compute_uncompute_cx"] for row in phase_summaries]
    x = np.arange(len(labels))
    width = 0.36
    fig, ax = plt.subplots(figsize=(11.5, 5.0), constrained_layout=True)
    ax.bar(x - width / 2, forward_cx, width, label="forward affine blocks")
    ax.bar(x + width / 2, clean_cx, width, label="clean compute-uncompute")
    ax.set(
        ylabel="compiled CX gates",
        title="Primitive-gate cost of calibrated phase-map variable weighted sums",
        xticks=x,
        xticklabels=labels,
        yscale="log",
    )
    ax.tick_params(axis="x", rotation=28)
    ax.grid(axis="y", alpha=0.25)
    ax.legend()
    fig.savefig(OUT_PNG, dpi=250)
    fig.savefig(OUT_PDF)
    plt.close(fig)
    print(json.dumps({"status": payload["status"], "full_cycle": full_cycle}, indent=2))


if __name__ == "__main__":
    main()
