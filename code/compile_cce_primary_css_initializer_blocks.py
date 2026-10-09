"""Compile the parameter-only CSS initializer affine blocks to u/CX gates."""

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
BRIDGE = RESULTS / "PSA_QAE_CCE_PRIMARY_CSS_INITIALIZER_EVENT_BRIDGE.json"
SCREEN = RESULTS / "PSA_QAE_CCE_PRIMARY_CSS_INITIALIZER_FIXED_POINT_SCREEN.json"
OUT_JSON = RESULTS / "PSA_QAE_CCE_PRIMARY_CSS_INITIALIZER_BLOCK_COMPILE.json"
OUT_CSV = RESULTS / "PSA_QAE_CCE_PRIMARY_CSS_INITIALIZER_BLOCK_COMPILE.csv"
OUT_MD = RESULTS / "PSA_QAE_CCE_PRIMARY_CSS_INITIALIZER_BLOCK_COMPILE.md"
OUT_PNG = RESULTS / "PSA_QAE_CCE_PRIMARY_CSS_INITIALIZER_BLOCK_COMPILE_FIGURE.png"
OUT_PDF = RESULTS / "PSA_QAE_CCE_PRIMARY_CSS_INITIALIZER_BLOCK_COMPILE_FIGURE.pdf"

sys.path.insert(0, str(HERE.parent))
from psa_qae.cce_primary_phase_event_fixed_point_screen import integer_spec  # noqa: E402


TARGETS = [
    *(f"A_gas_{name}" for name in ["H2", "CO2", "CH4", "CO", "N2"]),
    *(f"A_adsorbed_{name}" for name in ["H2", "CO2", "CH4", "CO", "N2"]),
    *(f"B_gas_{name}" for name in ["H2", "CO2", "CH4", "CO", "N2"]),
    *(f"B_adsorbed_{name}" for name in ["H2", "CO2", "CH4", "CO", "N2"]),
]


def signed_weighted_adder(weights: list[int], negative_mask: list[bool]) -> QuantumCircuit:
    adder = WeightedAdder(len(weights), weights)
    circuit = QuantumCircuit(adder.num_qubits, name="signed_css_initializer_sum")
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
    selected = screen["minimum_configuration_within_all_budgets_and_labels"]
    if selected is None:
        raise RuntimeError("No accuracy-feasible CSS-initializer configuration.")
    input_bits = int(selected["bits_per_input"])
    sum_bits = int(selected["sum_bits_per_scalar_output"])
    model = bridge["full_fit_css_initializer"]
    rows = []
    started = time.perf_counter()
    for output_index, target in enumerate(TARGETS):
        spec = integer_spec(model, input_bits, output_index, sum_bits)
        weights = [int(value) for value in spec["integer_weights"]]
        circuit = signed_weighted_adder(weights, spec["negative_mask"])
        t0 = time.perf_counter()
        compiled = transpile(circuit, basis_gates=["u", "cx"], optimization_level=0)
        elapsed = time.perf_counter() - t0
        operations = compiled.count_ops()
        rows.append(
            {
                "target_index": output_index,
                "target": target,
                "input_bits_per_active_parameter": input_bits,
                "active_parameters": len(spec["active_indices"]),
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
        print(f"compiled CSS initializer {output_index + 1}/{len(TARGETS)}: {target}", flush=True)

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
        "schema": "psa-qae-cce-primary-css-initializer-block-compile/v1",
        "status": "parameter_only_css_initializer_affine_blocks_compiled_state_update_physical_css_and_loader_open",
        "source_bridge": BRIDGE.name,
        "source_fixed_point_screen": SCREEN.name,
        "selected_fixed_point_configuration": selected,
        "qiskit_version": qiskit.__version__,
        "compile_basis": ["u", "cx"],
        "coupling_assumption": "all_to_all_no_backend_routing",
        "optimization_level": 0,
        "blocks": rows,
        "aggregate": aggregate,
        "qpu_submission": False,
        "claim_boundary": {
            "supported": "primitive-gate cost of 20 parameter-only aggregate CSS-initializer scalar affine blocks at the accuracy-feasible fixed-point configuration",
            "unsupported": "constant injection, reversible state-register update, physical CSS iteration, tank/profile propagation, state loading, hardware execution, or quantum advantage",
        },
    }
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with OUT_CSV.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    lines = [
        "# Primitive-gate compilation of parameter-only CSS initializer blocks",
        "",
        f"The accuracy-feasible configuration uses {input_bits} bits per active parameter and a {sum_bits}-bit scalar accumulator. Twenty aggregate A/B gas and adsorbed-state outputs are compiled independently to `u`/`cx` with all-to-all connectivity and optimization level 0.",
        "",
        f"With scalar-workspace reuse, the maximum block requires **{aggregate['max_logical_qubits_reusing_scalar_workspace']:,} logical qubits**. The 20-block serial total is **{aggregate['serial_forward_cx']:,} forward CX** and **{aggregate['serial_clean_compute_uncompute_cx']:,} clean compute-uncompute CX**.",
        "",
        "These are affine variable weighted sums only. Constant injection, reversible state-register update, physical CSS iteration, tank/profile propagation, final event arithmetic, loading, routing, and hardware execution remain open.",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    groups = ["A gas", "A ads", "B gas", "B ads"]
    group_cx = [sum(row["forward_cx"] for row in rows[index * 5:(index + 1) * 5]) for index in range(4)]
    group_clean = [2 * value for value in group_cx]
    x = np.arange(len(groups))
    width = 0.36
    fig, ax = plt.subplots(figsize=(8.8, 4.6), constrained_layout=True)
    ax.bar(x - width / 2, group_cx, width, label="forward")
    ax.bar(x + width / 2, group_clean, width, label="clean compute-uncompute")
    ax.set(ylabel="compiled CX gates", title="Parameter-only CSS initializer affine blocks", xticks=x, xticklabels=groups, yscale="log")
    ax.grid(axis="y", alpha=0.25)
    ax.legend(frameon=False)
    fig.savefig(OUT_PNG, dpi=250)
    fig.savefig(OUT_PDF)
    plt.close(fig)
    print(json.dumps({"status": payload["status"], "aggregate": aggregate, "qpu_submission": False}, indent=2))


if __name__ == "__main__":
    main()
