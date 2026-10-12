"""Serialize and verify the corrected integer event without importing Qiskit.

The circuit construction follows the installed Qiskit 2.5.2 source algorithms
for WeightedAdder and the two's-complement IntegerComparator.  CCX is flattened
to the standard exact 6-CX Clifford+T decomposition, and the three-control X in
the adder uses the same one-clean-ancilla v-chain identity (three CCX gates).
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import random
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"
SOURCE_DIR = RESULTS / "pressure_consistent_physical_pd_area_qae_bridge_v1"
SPEC_PATH = SOURCE_DIR / "PSA_PHYSICAL_PD_AREA_EVENT_ORACLE_INTEGER_SPEC.json"
BRIDGE_PATH = SOURCE_DIR / "PSA_PHYSICAL_PD_AREA_QAE_BRIDGE.json"
DIRECT_PATH = SOURCE_DIR / "Table_physical_pd_area_direct_validation.csv"
OUT = RESULTS / "pressure_consistent_portable_qasm_oracle_v1"
OUT_QASM = OUT / "PSA_PHYSICAL_PD_AREA_EVENT_ORACLE_10BIT_PORTABLE.qasm"
OUT_JSON = OUT / "PSA_PRESSURE_CONSISTENT_PORTABLE_QASM_ORACLE_V1.json"
OUT_MD = OUT / "PSA_PRESSURE_CONSISTENT_PORTABLE_QASM_ORACLE_V1.md"
OUT_FIG = OUT / "Fig_pressure_consistent_portable_qasm_oracle_v1.png"
OUT_MANIFEST = OUT / "MANIFEST_SHA256.json"


Op = tuple[str, tuple[int, ...]]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def add(ops: list[Op], name: str, *qubits: int) -> None:
    ops.append((name, tuple(qubits)))


def or2(ops: list[Op], a: int, b: int, target: int) -> None:
    add(ops, "or2", a, b, target)


def weighted_adder_ops(spec: dict) -> tuple[list[Op], dict]:
    n_state = int(spec["state_qubits"])
    weights = list(map(int, spec["integer_weights"]))
    n_sum = max(1, int(math.floor(math.log2(sum(weights))) + 1))
    state = list(range(n_state))
    sums = list(range(n_state, n_state + n_sum))
    carry = list(range(n_state + n_sum, n_state + n_sum + n_sum - 1))
    control = n_state + n_sum + n_sum - 1 if n_sum > 2 else None
    ops: list[Op] = []
    for i, weight in enumerate(weights):
        if weight == 0:
            continue
        q_state = state[i]
        bits = f"{weight:b}".rjust(n_sum, "0")[::-1]
        for j, bit in enumerate(bits):
            if bit == "1":
                if n_sum == 1:
                    add(ops, "cx", q_state, sums[j])
                elif j == 0:
                    add(ops, "ccx", q_state, sums[j], carry[j])
                    add(ops, "cx", q_state, sums[j])
                elif j == n_sum - 1:
                    add(ops, "cx", q_state, sums[j])
                    add(ops, "ccx", q_state, carry[j - 1], sums[j])
                else:
                    add(ops, "x", sums[j])
                    add(ops, "x", carry[j - 1])
                    add(ops, "mcx3", q_state, sums[j], carry[j - 1], carry[j], control)
                    add(ops, "cx", q_state, carry[j])
                    add(ops, "x", sums[j])
                    add(ops, "x", carry[j - 1])
                    add(ops, "cx", q_state, sums[j])
                    add(ops, "ccx", q_state, carry[j - 1], sums[j])
            elif n_sum == 1 or j == 0:
                pass
            elif j == n_sum - 1:
                add(ops, "ccx", q_state, carry[j - 1], sums[j])
            else:
                add(ops, "mcx3", q_state, sums[j], carry[j - 1], carry[j], control)
                add(ops, "ccx", q_state, carry[j - 1], sums[j])

        for j in reversed(range(len(bits))):
            bit = bits[j]
            if bit == "1":
                if n_sum == 1:
                    pass
                elif j == 0:
                    add(ops, "x", sums[j])
                    add(ops, "ccx", q_state, sums[j], carry[j])
                    add(ops, "x", sums[j])
                elif j == n_sum - 1:
                    pass
                else:
                    add(ops, "x", carry[j - 1])
                    add(ops, "mcx3", q_state, sums[j], carry[j - 1], carry[j], control)
                    add(ops, "cx", q_state, carry[j])
                    add(ops, "x", carry[j - 1])
            elif n_sum == 1 or j == 0 or j == n_sum - 1:
                pass
            else:
                add(ops, "x", sums[j])
                add(ops, "mcx3", q_state, sums[j], carry[j - 1], carry[j], control)
                add(ops, "x", sums[j])
    registers = {
        "state": state,
        "sum": sums,
        "carry": carry,
        "control": [] if control is None else [control],
        "sum_qubits": n_sum,
        "adder_ancillas": len(carry) + int(control is not None),
    }
    return ops, registers


def twos_complement_bits(num_bits: int, value: int) -> list[int]:
    text = f"{2**num_bits - math.ceil(value):b}".rjust(num_bits, "0")
    return [1 if text[i] == "1" else 0 for i in reversed(range(len(text)))]


def comparator_ops(sums: list[int], flag: int, work: list[int], threshold: int) -> list[Op]:
    n = len(sums)
    ops: list[Op] = []
    if threshold <= 0:
        add(ops, "x", flag)
    elif threshold < 2**n:
        if n > 1:
            twos = twos_complement_bits(n, threshold)
            for i in range(n):
                if i == 0:
                    if twos[i] == 1:
                        add(ops, "cx", sums[i], work[i])
                elif i < n - 1:
                    if twos[i] == 1:
                        or2(ops, sums[i], work[i - 1], work[i])
                    else:
                        add(ops, "ccx", sums[i], work[i - 1], work[i])
                elif twos[i] == 1:
                    or2(ops, sums[i], work[i - 1], flag)
                else:
                    add(ops, "ccx", sums[i], work[i - 1], flag)
            for i in reversed(range(n - 1)):
                if i == 0:
                    if twos[i] == 1:
                        add(ops, "cx", sums[i], work[i])
                elif twos[i] == 1:
                    or2(ops, sums[i], work[i - 1], work[i])
                else:
                    add(ops, "ccx", sums[i], work[i - 1], work[i])
        else:
            add(ops, "cx", sums[0], flag)
    return ops


def build_oracle_ops(spec: dict) -> tuple[list[Op], dict]:
    adder, registers = weighted_adder_ops(spec)
    n_state = int(spec["state_qubits"])
    n_sum = int(registers["sum_qubits"])
    adder_ancillas = int(registers["adder_ancillas"])
    flag = n_state + n_sum + adder_ancillas
    comp_work = list(range(flag + 1, flag + 1 + n_sum - 1))
    comparator = comparator_ops(registers["sum"], flag, comp_work, int(spec["integer_threshold"]))
    negative = [i for i, value in enumerate(spec["negative_bit_mask"]) if value]
    ops: list[Op] = []
    for qubit in negative:
        add(ops, "x", qubit)
    ops.extend(adder)
    ops.extend(comparator)
    add(ops, "z", flag)
    ops.extend(reversed(comparator))
    ops.extend(reversed(adder))
    for qubit in negative:
        add(ops, "x", qubit)
    registers.update(
        {
            "flag": flag,
            "comparator_work": comp_work,
            "comparator_ancillas": len(comp_work),
            "total_logical_qubits": flag + 1 + len(comp_work),
        }
    )
    return ops, registers


CCX_PRIMITIVES = [
    ("h", (2,)), ("cx", (1, 2)), ("tdg", (2,)), ("cx", (0, 2)),
    ("t", (2,)), ("cx", (1, 2)), ("tdg", (2,)), ("cx", (0, 2)),
    ("t", (1,)), ("t", (2,)), ("h", (2,)), ("cx", (0, 1)),
    ("t", (0,)), ("tdg", (1,)), ("cx", (0, 1)),
]


def expand_ccx(a: int, b: int, target: int) -> list[Op]:
    q = (a, b, target)
    return [(name, tuple(q[i] for i in local)) for name, local in CCX_PRIMITIVES]


def expand_ops(ops: list[Op]) -> list[Op]:
    out: list[Op] = []
    for name, q in ops:
        if name in {"x", "z", "cx", "h", "t", "tdg"}:
            out.append((name, q))
        elif name == "ccx":
            out.extend(expand_ccx(*q))
        elif name == "mcx3":
            a, b, c, target, work = q
            out.extend(expand_ccx(a, b, work))
            out.extend(expand_ccx(work, c, target))
            out.extend(expand_ccx(a, b, work))
        elif name == "or2":
            a, b, target = q
            out.extend([("x", (target,)), ("x", (a,)), ("x", (b,))])
            out.extend(expand_ccx(a, b, target))
            out.extend([("x", (a,)), ("x", (b,))])
        else:
            raise ValueError(name)
    return out


def circuit_depth(ops: list[Op], n_qubits: int) -> int:
    available = [0] * n_qubits
    depth = 0
    for _name, qubits in ops:
        layer = max(available[q] for q in qubits) + 1
        for q in qubits:
            available[q] = layer
        depth = max(depth, layer)
    return depth


def simulate_high_level(ops: list[Op], initial: list[int]) -> tuple[list[int], int]:
    bits = initial.copy()
    phase = 1
    for name, q in ops:
        if name == "x":
            bits[q[0]] ^= 1
        elif name == "cx":
            if bits[q[0]]:
                bits[q[1]] ^= 1
        elif name == "ccx":
            if bits[q[0]] and bits[q[1]]:
                bits[q[2]] ^= 1
        elif name == "mcx3":
            if bits[q[0]] and bits[q[1]] and bits[q[2]]:
                bits[q[3]] ^= 1
        elif name == "or2":
            if bits[q[0]] or bits[q[1]]:
                bits[q[2]] ^= 1
        elif name == "z":
            if bits[q[0]]:
                phase *= -1
        else:
            raise ValueError(name)
    return bits, phase


def expected_pass(state_bits: list[int], spec: dict) -> bool:
    transformed = [1 - bit if neg else bit for bit, neg in zip(state_bits, spec["negative_bit_mask"])]
    total = sum(int(w) * bit for w, bit in zip(spec["integer_weights"], transformed))
    return total >= int(spec["integer_threshold"])


def verify_states(spec: dict, states: list[list[int]]) -> dict:
    ops, registers = build_oracle_ops(spec)
    n = int(registers["total_logical_qubits"])
    phase_errors = 0
    restoration_errors = 0
    for state in states:
        initial = state + [0] * (n - len(state))
        final, phase = simulate_high_level(ops, initial)
        expected_phase = -1 if expected_pass(state, spec) else 1
        phase_errors += int(phase != expected_phase)
        restoration_errors += int(final != initial)
    return {
        "state_count": len(states),
        "phase_label_errors": phase_errors,
        "state_or_ancilla_restoration_errors": restoration_errors,
        "all_pass": phase_errors == 0 and restoration_errors == 0,
    }


def exhaustive_states(n: int) -> list[list[int]]:
    return [[(value >> bit) & 1 for bit in range(n)] for value in range(2**n)]


def direct_states(spec: dict) -> tuple[list[list[int]], list[bool], list[str]]:
    levels = int(spec["levels_per_variable"])
    bits_per = int(spec["input_bits_per_variable"])
    states, truth, ids = [], [], []
    with DIRECT_PATH.open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            state = []
            for key in ("feed_u", "equilibrium_pc_u", "ldf_u"):
                code = int(np.rint(np.clip(float(row[key]), 0.0, 1.0) * levels))
                state.extend((code >> bit) & 1 for bit in range(bits_per))
            states.append(state)
            truth.append(row["direct_physical_event"].lower() == "true")
            ids.append(row["case_id"])
    return states, truth, ids


def qasm_text(flat: list[Op], n_qubits: int) -> str:
    lines = [
        "OPENQASM 3.0;",
        'include "stdgates.inc";',
        f"qubit[{n_qubits}] q;",
        "// Exact portable decomposition of the corrected 10-bit process event.",
    ]
    for name, q in flat:
        if len(q) == 1:
            lines.append(f"{name} q[{q[0]}];")
        elif len(q) == 2:
            lines.append(f"{name} q[{q[0]}], q[{q[1]}];")
        else:
            raise AssertionError((name, q))
    return "\n".join(lines) + "\n"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    spec_payload = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    bridge = json.loads(BRIDGE_PATH.read_text(encoding="utf-8"))
    specs = {int(x["input_bits_per_variable"]): x for x in spec_payload["integer_specs"]}
    verification = {}
    for bits in (2, 3, 4):
        verification[f"exhaustive_{bits}bit"] = verify_states(
            specs[bits], exhaustive_states(int(specs[bits]["state_qubits"]))
        )

    spec = specs[10]
    ops, registers = build_oracle_ops(spec)
    direct, direct_truth, case_ids = direct_states(spec)
    direct_check = verify_states(spec, direct)
    phase_labels = [expected_pass(state, spec) for state in direct]
    direct_label_errors = sum(a != b for a, b in zip(phase_labels, direct_truth))
    rng = random.Random(20261012)
    random_states = [
        [rng.getrandbits(1) for _ in range(int(spec["state_qubits"]))]
        for _ in range(4096)
    ]
    random_check = verify_states(spec, random_states)
    verification["direct_10bit"] = {**direct_check, "direct_engineering_label_errors": direct_label_errors, "case_ids": case_ids}
    verification["random_10bit"] = random_check
    assert all(row["all_pass"] for row in verification.values())
    assert direct_label_errors == 0

    flat = expand_ops(ops)
    OUT_QASM.write_text(qasm_text(flat, int(registers["total_logical_qubits"])), encoding="utf-8")
    high_counts = Counter(name for name, _ in ops)
    primitive_counts = Counter(name for name, _ in flat)
    resources = {
        **registers,
        "high_level_operation_counts": dict(high_counts),
        "portable_primitive_operation_counts": dict(primitive_counts),
        "portable_primitive_size": len(flat),
        "portable_primitive_depth_all_to_all": circuit_depth(flat, int(registers["total_logical_qubits"])),
        "portable_primitive_cx": primitive_counts["cx"],
        "portable_single_qubit_gates": len(flat) - primitive_counts["cx"],
        "decomposition": "exact CCX=6 CX Clifford+T; MCX3 one-clean-ancilla v-chain=3 CCX; no routing or optimization",
    }
    payload = {
        "schema": "psa-pressure-consistent-portable-qasm-oracle/v1",
        "status": "portable_qasm_serialized_and_basis_state_verified",
        "source_algorithm": "Qiskit 2.5.2 WeightedAdder and two's-complement IntegerComparator source-equivalent construction",
        "event": bridge["event"],
        "integer_spec_sha256": sha256(SPEC_PATH),
        "qasm": {"path": OUT_QASM.name, "bytes": OUT_QASM.stat().st_size, "sha256": sha256(OUT_QASM), "language": "OpenQASM 3.0"},
        "resources": resources,
        "verification": verification,
        "probability": {
            "continuous_conservative_affine": bridge["validation"]["conservative_affine_probability"],
            "ten_bit_discrete": bridge["conservative_affine_oracle"]["ten_bit_resources"]["exact_discrete_oracle_probability"],
            "absolute_discretization_error": bridge["conservative_affine_oracle"]["ten_bit_resources"]["absolute_probability_discretization_error"],
        },
        "claim_boundary": {
            "supported": "The included OpenQASM exactly implements the frozen integer weighted-sum event under the stated portable decomposition and restores all work qubits on every verified basis state.",
            "not_supported": "The CX count and depth are not Qiskit-optimized, device-routed, error-corrected, or hardware-executed resources.",
        },
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    OUT_MD.write_text(
        "\n".join(
            [
                "# Portable corrected event oracle",
                "",
                f"- Logical qubits: **{resources['total_logical_qubits']}**",
                f"- Portable exact-decomposition CX: **{resources['portable_primitive_cx']:,}**",
                f"- Portable all-to-all depth: **{resources['portable_primitive_depth_all_to_all']:,}**",
                f"- Primitive size: **{resources['portable_primitive_size']:,}**",
                f"- Direct engineering labels: **{len(direct_truth) - direct_label_errors}/{len(direct_truth)} agree**",
                "- Exhaustive 2-, 3-, and 4-bit basis-state checks and 4,096 seeded 10-bit states restore every work qubit and phase-mark the expected event.",
                "- These are exact portable decomposition resources, not optimized or hardware-routed resources.",
            ]
        ),
        encoding="utf-8",
    )

    fig, axes = plt.subplots(1, 3, figsize=(12.6, 3.7))
    axes[0].bar(["continuous", "10-bit"], [payload["probability"]["continuous_conservative_affine"], payload["probability"]["ten_bit_discrete"]], color=["#2563eb", "#0f766e"])
    axes[0].axhline(0.95, color="#dc2626", linestyle="--", linewidth=1.2, label="chance target")
    axes[0].set_ylim(0.948, 0.953)
    axes[0].set_ylabel("Pass probability")
    axes[0].set_title("(a) Frozen event probability")
    axes[0].legend(fontsize=8)
    axes[1].bar(["logical\nqubits", "CX / 100", "depth / 100"], [resources["total_logical_qubits"], resources["portable_primitive_cx"] / 100, resources["portable_primitive_depth_all_to_all"] / 100], color=["#7c3aed", "#f59e0b", "#64748b"])
    axes[1].set_title("(b) Portable circuit resources")
    axes[1].set_ylabel("Count (CX and depth scaled by 100)")
    labels = ["2-bit\nexhaustive", "3-bit\nexhaustive", "4-bit\nexhaustive", "10-bit\ndirect", "10-bit\nrandom"]
    counts = [verification["exhaustive_2bit"]["state_count"], verification["exhaustive_3bit"]["state_count"], verification["exhaustive_4bit"]["state_count"], verification["direct_10bit"]["state_count"], verification["random_10bit"]["state_count"]]
    axes[2].bar(labels, counts, color="#059669")
    axes[2].set_yscale("log")
    axes[2].set_ylabel("Verified basis states")
    axes[2].set_title("(c) Zero phase/restoration errors")
    axes[2].tick_params(axis="x", labelsize=8)
    fig.tight_layout()
    fig.savefig(OUT_FIG, dpi=300, bbox_inches="tight")
    plt.close(fig)

    outputs = [OUT_QASM, OUT_JSON, OUT_MD, OUT_FIG]
    manifest = {
        "schema": "psa-pressure-consistent-portable-qasm-manifest/v1",
        "sources": [{"path": str(path.relative_to(ROOT)), "bytes": path.stat().st_size, "sha256": sha256(path)} for path in (SPEC_PATH, BRIDGE_PATH, DIRECT_PATH)],
        "outputs": [{"path": path.name, "bytes": path.stat().st_size, "sha256": sha256(path)} for path in outputs],
    }
    OUT_MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({"status": payload["status"], "resources": resources, "verification": verification, "qasm": payload["qasm"]}, indent=2))


if __name__ == "__main__":
    main()
