"""Compile the event-active primary phase-stream affine blocks to u/CX gates."""

from __future__ import annotations

import csv
import json
import sys
import time
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import qiskit
from qiskit import QuantumCircuit, transpile
from qiskit.circuit.library import WeightedAdder


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RESULTS = ROOT / "10_TEA_LCA_Python" / "results" / "pycharm_publication_enhancement"
BRIDGE = RESULTS / "PSA_QAE_CCE_PRIMARY_PHASE_EVENT_BRIDGE.json"
SCREEN = RESULTS / "PSA_QAE_CCE_PRIMARY_PHASE_EVENT_FIXED_POINT_SCREEN.json"
OUT_JSON = RESULTS / "PSA_QAE_CCE_PRIMARY_PHASE_EVENT_BLOCK_COMPILE.json"
OUT_CSV = RESULTS / "PSA_QAE_CCE_PRIMARY_PHASE_EVENT_BLOCK_COMPILE.csv"
OUT_MD = RESULTS / "PSA_QAE_CCE_PRIMARY_PHASE_EVENT_BLOCK_COMPILE.md"
OUT_PNG = RESULTS / "PSA_QAE_CCE_PRIMARY_PHASE_EVENT_BLOCK_COMPILE_FIGURE.png"
OUT_PDF = RESULTS / "PSA_QAE_CCE_PRIMARY_PHASE_EVENT_BLOCK_COMPILE_FIGURE.pdf"

sys.path.insert(0, str(HERE.parent))
from psa_qae.cce_primary_phase_event_fixed_point_screen import integer_spec  # noqa: E402


TARGETS = [
    (10, "in_H2"),
    (15, "out_H2"),
    (16, "out_CO2"),
    (17, "out_CH4"),
    (18, "out_CO"),
    (19, "out_N2"),
]
PHASES = ("A_adsorption", "B_adsorption")


def signed_weighted_adder(weights: list[int], negative_mask: list[bool]) -> QuantumCircuit:
    adder = WeightedAdder(len(weights), weights)
    circuit = QuantumCircuit(adder.num_qubits, name="signed_phase_stream_sum")
    negative = np.flatnonzero(np.asarray(negative_mask, dtype=bool)).tolist()
    if negative:
        circuit.x(negative)
    circuit.compose(adder, inplace=True)
    if negative:
        circuit.x(negative)
    return circuit


def main() -> None:
    bridge = json.loads(BRIDGE.read_text(encoding="utf-8"))
    screen = json.loads(SCREEN.read_text(encoding="utf-8"))
    selected = screen["minimum_configuration_within_budgets_and_all_labels"]
    if selected is None:
        raise RuntimeError("No accuracy-feasible fixed-point configuration.")
    input_bits = int(selected["bits_per_input"])
    sum_bits = int(selected["sum_bits_per_scalar_output"])

    rows = []
    started = time.perf_counter()
    for phase in PHASES:
        model = bridge["full_fit_models"][phase]
        for output_index, target in TARGETS:
            spec = integer_spec(model, input_bits, output_index, sum_bits)
            weights = [int(value) for value in spec["integer_weights"]]
            circuit = signed_weighted_adder(weights, spec["negative_mask"])
            t0 = time.perf_counter()
            compiled = transpile(circuit, basis_gates=["u", "cx"], optimization_level=0)
            elapsed = time.perf_counter() - t0
            operations = compiled.count_ops()
            rows.append(
                {
                    "phase": phase,
                    "target": target,
                    "output_index": output_index,
                    "input_bits_per_active_feature": input_bits,
                    "active_features": len(spec["active_indices"]),
                    "state_qubits": len(weights),
                    "sum_qubits": sum_bits,
                    "ancilla_qubits": int(circuit.num_qubits - len(weights) - sum_bits),
                    "logical_qubits": int(compiled.num_qubits),
                    "nonzero_integer_weights": int(np.count_nonzero(weights)),
                    "negative_bit_controls": int(np.count_nonzero(spec["negative_mask"])),
                    "forward_depth_all_to_all": int(compiled.depth()),
                    "forward_size": int(compiled.size()),
                    "forward_cx": int(operations.get("cx", 0)),
                    "forward_u": int(operations.get("u", 0)),
                    "clean_compute_uncompute_depth_serial_bound": int(2 * compiled.depth()),
                    "clean_compute_uncompute_cx": int(2 * operations.get("cx", 0)),
                    "transpile_seconds": float(elapsed),
                }
            )
            print(f"compiled {phase} {target}", flush=True)

    phase_summaries = []
    for phase in PHASES:
        selected_rows = [row for row in rows if row["phase"] == phase]
        phase_summaries.append(
            {
                "phase": phase,
                "scalar_blocks": len(selected_rows),
                "max_logical_qubits_reusing_scalar_workspace": max(row["logical_qubits"] for row in selected_rows),
                "serial_forward_depth": sum(row["forward_depth_all_to_all"] for row in selected_rows),
                "serial_forward_cx": sum(row["forward_cx"] for row in selected_rows),
                "serial_clean_compute_uncompute_cx": sum(row["clean_compute_uncompute_cx"] for row in selected_rows),
            }
        )
    aggregate = {
        "scalar_blocks": len(rows),
        "max_logical_qubits_reusing_scalar_workspace": max(row["logical_qubits"] for row in rows),
        "serial_forward_depth": sum(row["forward_depth_all_to_all"] for row in rows),
        "serial_forward_cx": sum(row["forward_cx"] for row in rows),
        "serial_clean_compute_uncompute_depth_bound": sum(row["clean_compute_uncompute_depth_serial_bound"] for row in rows),
        "serial_clean_compute_uncompute_cx": sum(row["clean_compute_uncompute_cx"] for row in rows),
        "total_transpile_seconds": float(time.perf_counter() - started),
    }
    payload = {
        "schema": "psa-qae-cce-primary-phase-event-block-compile/v1",
        "status": "event_active_primary_phase_stream_affine_blocks_compiled_event_arithmetic_css_and_loader_open",
        "source_bridge": BRIDGE.name,
        "source_fixed_point_screen": SCREEN.name,
        "selected_fixed_point_configuration": selected,
        "qiskit_version": qiskit.__version__,
        "compile_basis": ["u", "cx"],
        "coupling_assumption": "all_to_all_no_backend_routing",
        "optimization_level": 0,
        "blocks": rows,
        "phase_summaries": phase_summaries,
        "aggregate": aggregate,
        "qpu_submission": False,
        "claim_boundary": {
            "supported": "primitive-gate cost of the 12 event-active stream affine blocks at the accuracy-feasible fixed-point configuration",
            "unsupported": "stream summation, recycle scaling, joint-event comparison, free-running CSS, state loading, hardware execution, or quantum advantage",
        },
    }
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with OUT_CSV.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    lines = [
        "# Primitive-gate compilation of primary event-active phase-stream blocks",
        "",
        f"The fixed-point screen selects {input_bits} bits per active input and a {sum_bits}-bit scalar accumulator. The six event-active stream outputs for each of the two adsorption phases are compiled independently to `u`/`cx` with all-to-all connectivity and optimization level 0.",
        "",
        "| phase | scalar blocks | max logical qubits | forward CX | clean compute-uncompute CX | forward serial depth |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in phase_summaries:
        lines.append(
            f"| {row['phase']} | {row['scalar_blocks']} | {row['max_logical_qubits_reusing_scalar_workspace']:,} | "
            f"{row['serial_forward_cx']:,} | {row['serial_clean_compute_uncompute_cx']:,} | {row['serial_forward_depth']:,} |"
        )
    lines += [
        "",
        f"Across both adsorption phases, the 12 event-active blocks require up to {aggregate['max_logical_qubits_reusing_scalar_workspace']:,} logical qubits with scalar-workspace reuse, {aggregate['serial_forward_cx']:,} forward CX, and {aggregate['serial_clean_compute_uncompute_cx']:,} clean compute-uncompute CX under serial composition.",
        "",
        "This is a measured process-to-event arithmetic layer conditional on observed phase-start states. Stream summation, fixed-policy recycle scaling, joint purity/recovery comparison, CSS repetition, loading, routing, and fault tolerance remain open.",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    labels = [f"{row['phase'].split('_')[0]} {row['target']}" for row in rows]
    forward = [row["forward_cx"] for row in rows]
    clean = [row["clean_compute_uncompute_cx"] for row in rows]
    x = np.arange(len(rows))
    width = 0.37
    fig, ax = plt.subplots(figsize=(12.2, 5.0), constrained_layout=True)
    ax.bar(x - width / 2, forward, width, label="forward")
    ax.bar(x + width / 2, clean, width, label="clean compute-uncompute")
    ax.set(ylabel="compiled CX gates", title="Primary event-active phase-stream affine blocks", xticks=x, xticklabels=labels, yscale="log")
    ax.tick_params(axis="x", rotation=35)
    ax.grid(axis="y", alpha=0.25)
    ax.legend()
    fig.savefig(OUT_PNG, dpi=250)
    fig.savefig(OUT_PDF)
    plt.close(fig)
    print(json.dumps({"status": payload["status"], "aggregate": aggregate, "qpu_submission": False}, indent=2))


if __name__ == "__main__":
    main()
