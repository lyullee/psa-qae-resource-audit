"""Compile a small coherent PSA-oracle connection control.

This circuit is a structural bridge between the calibrated affine-block
resource audit and a complete cyclic oracle.  Two three-bit bed-inventory
registers undergo reversible constant updates, a conservative one-unit
equalization controlled by their coarse pressure regions, two threshold
comparisons, a joint-event phase mark, and exact uncomputation.  The circuit
is exhaustively verified in coherent superposition over all 64 data states.

The integer map and thresholds are deliberately a small control, not fitted
H2 PSA kinetics and not the primary purity/recovery event.  Its role is to
prove that the missing modules can be connected coherently and to measure the
primitive-gate overhead of that connection without calling a QPU.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit.circuit.library import IntegerComparator
from qiskit.quantum_info import Statevector


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = ROOT / "10_TEA_LCA_Python" / "results" / "pycharm_publication_enhancement"

BITS = 3
MODULUS = 1 << BITS
THRESHOLD_A = 5
THRESHOLD_B = 3

A = [0, 1, 2]
B = [3, 4, 5]
DIR_AB = 6
DIR_BA = 7
CMP_A = 8
CMP_B = 9
EVENT = 10
ANC_A = [11, 12]
ANC_B = [13, 14]
N_QUBITS = 15


def increment(qc: QuantumCircuit, register: list[int]) -> None:
    """Add one modulo 2**n to a little-endian register."""
    for target in range(len(register) - 1, 0, -1):
        qc.mcx(register[:target], register[target])
    qc.x(register[0])


def controlled_increment(
    qc: QuantumCircuit, control: int, register: list[int]
) -> None:
    """Conditionally add one modulo 2**n."""
    for target in range(len(register) - 1, 0, -1):
        qc.mcx([control, *register[:target]], register[target])
    qc.cx(control, register[0])


def controlled_decrement(
    qc: QuantumCircuit, control: int, register: list[int]
) -> None:
    """Inverse of controlled_increment."""
    qc.cx(control, register[0])
    for target in range(1, len(register)):
        qc.mcx([control, *register[:target]], register[target])


def build_compute() -> QuantumCircuit:
    qc = QuantumCircuit(N_QUBITS, name="small_psa_compute")

    # Reversible constant/state update for one coarse phase.
    increment(qc, A)
    increment(qc, B)
    qc.barrier()

    # Coarse equalization direction is retained in two ledger ancillas.
    # DIR_AB = A high and B low; DIR_BA = B high and A low.
    qc.x(B[-1])
    qc.mcx([A[-1], B[-1]], DIR_AB)
    qc.x(B[-1])
    qc.x(A[-1])
    qc.mcx([B[-1], A[-1]], DIR_BA)
    qc.x(A[-1])

    # Transfer one inventory unit conservatively in the selected direction.
    controlled_decrement(qc, DIR_AB, A)
    controlled_increment(qc, DIR_AB, B)
    controlled_decrement(qc, DIR_BA, B)
    controlled_increment(qc, DIR_BA, A)
    qc.barrier()

    cmp_a = IntegerComparator(BITS, THRESHOLD_A, geq=True)
    cmp_b = IntegerComparator(BITS, THRESHOLD_B, geq=True)
    qc.compose(cmp_a, [*A, CMP_A, *ANC_A], inplace=True)
    qc.compose(cmp_b, [*B, CMP_B, *ANC_B], inplace=True)
    qc.mcx([CMP_A, CMP_B], EVENT)
    return qc


def classical_forward(a: int, b: int) -> dict[str, int]:
    a_out = (a + 1) % MODULUS
    b_out = (b + 1) % MODULUS
    dir_ab = int(a_out >= MODULUS // 2 and b_out < MODULUS // 2)
    dir_ba = int(b_out >= MODULUS // 2 and a_out < MODULUS // 2)
    if dir_ab:
        a_out = (a_out - 1) % MODULUS
        b_out = (b_out + 1) % MODULUS
    if dir_ba:
        b_out = (b_out - 1) % MODULUS
        a_out = (a_out + 1) % MODULUS
    cmp_a = int(a_out >= THRESHOLD_A)
    cmp_b = int(b_out >= THRESHOLD_B)
    return {
        "a_in": a,
        "b_in": b,
        "a_out": a_out,
        "b_out": b_out,
        "dir_ab": dir_ab,
        "dir_ba": dir_ba,
        "cmp_a": cmp_a,
        "cmp_b": cmp_b,
        "event": int(cmp_a and cmp_b),
    }


def basis_index(row: dict[str, int], forward: bool) -> int:
    if not forward:
        return int(row["a_in"] | (row["b_in"] << BITS))
    value = int(row["a_out"] | (row["b_out"] << BITS))
    value |= int(row["dir_ab"]) << DIR_AB
    value |= int(row["dir_ba"]) << DIR_BA
    value |= int(row["cmp_a"]) << CMP_A
    value |= int(row["cmp_b"]) << CMP_B
    value |= int(row["event"]) << EVENT
    return value


def verify_coherent(compute: QuantumCircuit, rows: list[dict]) -> dict:
    amplitude = 1.0 / np.sqrt(len(rows))

    forward = QuantumCircuit(N_QUBITS)
    forward.h([*A, *B])
    forward.compose(compute, inplace=True)
    forward_state = np.asarray(Statevector.from_instruction(forward).data)
    forward_expected = np.zeros_like(forward_state)
    for row in rows:
        forward_expected[basis_index(row, forward=True)] = amplitude

    oracle = QuantumCircuit(N_QUBITS, name="small_psa_phase_oracle")
    oracle.compose(compute, inplace=True)
    oracle.z(EVENT)
    oracle.compose(compute.inverse(), inplace=True)
    coherent = QuantumCircuit(N_QUBITS)
    coherent.h([*A, *B])
    coherent.compose(oracle, inplace=True)
    oracle_state = np.asarray(Statevector.from_instruction(coherent).data)
    oracle_expected = np.zeros_like(oracle_state)
    for row in rows:
        sign = -1.0 if row["event"] else 1.0
        oracle_expected[basis_index(row, forward=False)] = sign * amplitude

    forward_error = float(np.max(np.abs(forward_state - forward_expected)))
    oracle_error = float(np.max(np.abs(oracle_state - oracle_expected)))
    support = np.flatnonzero(np.abs(oracle_state) > 1.0e-12)
    ancilla_clean = bool(all(int(index) < (1 << (2 * BITS)) for index in support))
    phase_labels_match = bool(oracle_error < 1.0e-10)
    if forward_error >= 1.0e-10:
        raise AssertionError(f"forward coherent mapping failed: {forward_error}")
    if not ancilla_clean or not phase_labels_match:
        raise AssertionError(
            f"oracle verification failed: error={oracle_error}, clean={ancilla_clean}"
        )
    return {
        "basis_states_checked_in_one_coherent_superposition": len(rows),
        "forward_mapping_max_abs_amplitude_error": forward_error,
        "phase_oracle_max_abs_amplitude_error": oracle_error,
        "oracle_support_states": int(len(support)),
        "all_work_and_event_qubits_clean_after_uncompute": ancilla_clean,
        "all_event_phase_labels_match": phase_labels_match,
    }, oracle


def compiled_metrics(circuit: QuantumCircuit) -> dict[str, int]:
    compiled = transpile(
        circuit,
        basis_gates=["u", "cx"],
        optimization_level=0,
    )
    operations = compiled.count_ops()
    return {
        "logical_qubits": int(compiled.num_qubits),
        "depth_all_to_all": int(compiled.depth()),
        "size": int(compiled.size()),
        "cx": int(operations.get("cx", 0)),
        "u": int(operations.get("u", 0)),
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rows = [classical_forward(a, b) for b in range(MODULUS) for a in range(MODULUS)]
    compute = build_compute()
    verification, oracle = verify_coherent(compute, rows)
    compute_metrics = compiled_metrics(compute)
    oracle_metrics = compiled_metrics(oracle)
    event_count = int(sum(row["event"] for row in rows))

    payload = {
        "schema": "psa-qae-cce-small-end-to-end-oracle/v1",
        "status": "small_structural_end_to_end_oracle_compiled_and_coherently_verified_not_calibrated_cycle",
        "purpose": "primitive-gate connection control for state update, conservative transfer, joint comparison, phase mark, and exact uncomputation",
        "registers": {
            "bed_a_inventory_bits": BITS,
            "bed_b_inventory_bits": BITS,
            "direction_ledger_qubits": 2,
            "comparator_output_qubits": 2,
            "event_qubits": 1,
            "comparator_work_qubits": 4,
            "total_logical_qubits": N_QUBITS,
        },
        "integer_control": {
            "modulus": MODULUS,
            "constant_state_update": "A <- A+1 mod 8; B <- B+1 mod 8",
            "equalization": "one unit moves from the high-MSB register to the low-MSB register; direction retained until uncompute",
            "joint_event": f"A >= {THRESHOLD_A} and B >= {THRESHOLD_B} after update/equalization",
            "event_count": event_count,
            "event_probability_over_uniform_basis": event_count / len(rows),
        },
        "verification": verification,
        "primitive_gate_compile": {
            "basis": ["u", "cx"],
            "coupling_assumption": "all_to_all_no_backend_routing",
            "optimization_level": 0,
            "forward_compute": compute_metrics,
            "clean_phase_oracle": oracle_metrics,
        },
        "limitations": [
            "The three-bit integer dynamics are a structural control, not fitted H2 PSA kinetics or transport.",
            "The joint inventory threshold is not the primary H2 purity/recovery event.",
            "The circuit proves coherent module connection and clean uncomputation, not calibrated cyclic-steady-state prediction.",
            "The calibrated 11-bit-input/16-bit-output affine resource layer remains the relevant full-scale arithmetic estimate.",
            "State preparation, repeated CSS, backend routing, noise, and fault-tolerant overhead are excluded.",
        ],
    }

    json_path = OUT / "PSA_QAE_CCE_SMALL_END_TO_END_ORACLE.json"
    csv_path = OUT / "PSA_QAE_CCE_SMALL_END_TO_END_ORACLE.csv"
    md_path = OUT / "PSA_QAE_CCE_SMALL_END_TO_END_ORACLE.md"
    png_path = OUT / "PSA_QAE_CCE_SMALL_END_TO_END_ORACLE_FIGURE.png"
    pdf_path = OUT / "PSA_QAE_CCE_SMALL_END_TO_END_ORACLE_FIGURE.pdf"
    json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    with csv_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    lines = [
        "# Small coherent end-to-end PSA-oracle connection control",
        "",
        "Two three-bit inventory registers undergo reversible constant updates, a one-unit conservative equalization with retained direction ancillas, two integer threshold comparisons, a joint-event phase mark, and exact uncomputation. All 64 data basis states are verified simultaneously in coherent superposition.",
        "",
        "| layer | logical qubits | depth | CX | u |",
        "|---|---:|---:|---:|---:|",
        f"| forward compute | {compute_metrics['logical_qubits']} | {compute_metrics['depth_all_to_all']} | {compute_metrics['cx']} | {compute_metrics['u']} |",
        f"| clean phase oracle | {oracle_metrics['logical_qubits']} | {oracle_metrics['depth_all_to_all']} | {oracle_metrics['cx']} | {oracle_metrics['u']} |",
        "",
        f"The proxy joint event holds for `{event_count}/64 = {event_count / 64:.6f}` basis states. The forward mapping maximum amplitude error is `{verification['forward_mapping_max_abs_amplitude_error']:.3e}` and the compute–phase–uncompute oracle error is `{verification['phase_oracle_max_abs_amplitude_error']:.3e}`. All nine work/event qubits return to zero and all 64 phase labels match.",
        "",
        "This is a structural circuit control. It demonstrates coherent connection of the previously separate modules but does not replace the calibrated 11/16-bit affine resource estimate, repeated CSS, or the primary H2 purity/recovery event.",
        "",
        f"Artifacts: `{json_path.name}`, `{csv_path.name}`, `{png_path.name}`.",
    ]
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    labels = ["forward compute", "clean phase oracle"]
    cx = [compute_metrics["cx"], oracle_metrics["cx"]]
    depth = [compute_metrics["depth_all_to_all"], oracle_metrics["depth_all_to_all"]]
    x = np.arange(len(labels))
    width = 0.36
    fig, ax = plt.subplots(figsize=(7.6, 4.2), constrained_layout=True)
    ax.bar(x - width / 2, cx, width, label="CX gates", color="#2563eb")
    ax.bar(x + width / 2, depth, width, label="depth", color="#f59e0b")
    ax.set(
        title="Coherent connection control: primitive-gate cost",
        ylabel="count (all-to-all, optimization level 0)",
        xticks=x,
        xticklabels=labels,
    )
    ax.grid(axis="y", alpha=0.25)
    ax.legend()
    fig.savefig(png_path, dpi=250)
    fig.savefig(pdf_path)
    plt.close(fig)

    print(
        json.dumps(
            {
                "status": payload["status"],
                "event_probability": event_count / len(rows),
                "verification": verification,
                "clean_phase_oracle": oracle_metrics,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
