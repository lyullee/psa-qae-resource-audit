"""Route and optionally execute the final pressure-consistent PSA event on IBM QPU.

This is an exact reversible Boolean compilation of the two-bit-per-variable
integer event in the final pressure-consistent affine oracle.  The full
arithmetic construction uses 42 logical qubits at this resolution.  For a
basis-state truth-table probe only, its complement has an exact three-cube
cover, allowing all 64 input states to be tested with seven logical qubits.

Submission is refused unless the saved ``psa_open`` account resolves to one
free IBM Open Plan instance with at least 60 seconds remaining.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
from functools import lru_cache
from itertools import product
import json
import math
from pathlib import Path
import sys

import matplotlib.pyplot as plt
import numpy as np
from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister, qasm3
from qiskit.quantum_info import Statevector
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import psa_pressure_consistent_portable_qasm_oracle_v1 as portable  # noqa: E402


SOURCE = HERE / "results" / "pressure_consistent_physical_pd_area_qae_bridge_v1" / "PSA_PHYSICAL_PD_AREA_QAE_BRIDGE.json"
OUT = HERE / "results" / "ibm_final_event_2bit_probe"
ACCOUNT_NAME = "psa_open"
SHOTS = 256
SEED = 17
N_INPUT = 6
FLAG = 6


def exact_disjoint_cover(target_states: set[int], n_input: int) -> list[tuple[int | None, ...]]:
    """Return a low-control, exact, disjoint cube cover."""
    states = sorted(target_states)
    target_mask = (1 << len(states)) - 1
    # Relative optimization weights approximate the growth of controlled-X
    # decompositions.  Exactness is independently verified below.
    control_cost = {0: 0, 1: 1, 2: 6, 3: 14, 4: 36, 5: 80, 6: 160}
    candidates: list[tuple[tuple[int | None, ...], int, int]] = []
    for cube in product((None, 0, 1), repeat=n_input):
        covered = {
            state
            for state in range(2**n_input)
            if all(value is None or ((state >> qubit) & 1) == value for qubit, value in enumerate(cube))
        }
        if not covered or not covered.issubset(target_states):
            continue
        cover_mask = sum(1 << states.index(state) for state in covered)
        n_controls = sum(value is not None for value in cube)
        candidates.append((cube, cover_mask, control_cost[n_controls]))

    @lru_cache(maxsize=None)
    def solve(covered_mask: int):
        if covered_mask == target_mask:
            return (0, 0, ())
        first_missing = next(bit for bit in range(len(states)) if not (covered_mask & (1 << bit)))
        options = []
        for index, (_cube, cube_mask, cost) in enumerate(candidates):
            if not (cube_mask & (1 << first_missing)) or (cube_mask & covered_mask):
                continue
            tail = solve(covered_mask | cube_mask)
            if tail is not None:
                options.append((cost + tail[0], 1 + tail[1], (index,) + tail[2]))
        return min(options, key=lambda item: (item[0], item[1])) if options else None

    solution = solve(0)
    if solution is None:
        raise AssertionError("no exact disjoint cover found")
    return [candidates[index][0] for index in solution[2]]


def complement_cover_oracle(failing_cubes: list[tuple[int | None, ...]]) -> QuantumCircuit:
    """Compile f(x)=1 except on the disjoint failing cubes."""
    qc = QuantumCircuit(N_INPUT + 1, name="final_PSA_2bit_event")
    qc.x(FLAG)
    for cube in failing_cubes:
        zeros = [q for q, value in enumerate(cube) if value == 0]
        controls = [q for q, value in enumerate(cube) if value is not None]
        for qubit in zeros:
            qc.x(qubit)
        if len(controls) == 1:
            qc.cx(controls[0], FLAG)
        else:
            qc.mcx(controls, FLAG)
        for qubit in reversed(zeros):
            qc.x(qubit)
    return qc


def verify_oracle(oracle: QuantumCircuit, marked: set[int]) -> dict:
    failures = []
    for state in range(2**N_INPUT):
        for initial_flag in (0, 1):
            basis = state | (initial_flag << FLAG)
            output = Statevector.from_int(basis, 2 ** (N_INPUT + 1)).evolve(oracle)
            actual = int(np.argmax(np.abs(output.data) ** 2))
            expected = state | ((initial_flag ^ int(state in marked)) << FLAG)
            if actual != expected:
                failures.append({"state": state, "initial_flag": initial_flag, "actual": actual, "expected": expected})
    return {
        "basis_states_checked": 2 ** (N_INPUT + 1),
        "failure_count": len(failures),
        "all_pass": not failures,
        "failures": failures,
    }


def basis_probe_circuit(oracle: QuantumCircuit, state: int) -> QuantumCircuit:
    qreg = QuantumRegister(N_INPUT + 1, "q")
    creg = ClassicalRegister(1, "flag")
    circuit = QuantumCircuit(qreg, creg, name=f"final2b_{state:02d}")
    for qubit in range(N_INPUT):
        if (state >> qubit) & 1:
            circuit.x(qubit)
    circuit.compose(oracle, inplace=True)
    circuit.measure(qreg[FLAG], creg[0])
    return circuit


def physical_layout(circuit: QuantumCircuit) -> list[int]:
    layout = circuit.layout
    if layout is None or layout.initial_layout is None:
        return []
    pairs = []
    for virtual, physical in layout.initial_layout.get_virtual_bits().items():
        register = getattr(virtual, "_register", None)
        index = getattr(virtual, "_index", 10**9)
        if register is not None and getattr(register, "name", "") == "q" and index < N_INPUT + 1:
            pairs.append((int(index), int(physical)))
    return [physical for _, physical in sorted(pairs)]


def independent_calibration_survival(circuit: QuantumCircuit, backend) -> tuple[float, int]:
    log_survival = 0.0
    used = 0
    for instruction in circuit.data:
        name = instruction.operation.name
        if name in {"delay", "barrier"} or name not in backend.target.operation_names:
            continue
        qubits = tuple(circuit.find_bit(qubit).index for qubit in instruction.qubits)
        props = backend.target[name].get(qubits)
        error = getattr(props, "error", None) if props is not None else None
        if error is not None and 0.0 <= float(error) < 1.0:
            log_survival += math.log1p(-float(error))
            used += 1
    return float(math.exp(log_survival)), used


def free_open_plan(service: QiskitRuntimeService) -> bool:
    instances = service.instances()
    return len(instances) == 1 and instances[0].get("plan") == "open" and instances[0].get("pricing_type") == "free"


def result_flag_counts(pub_result) -> dict[str, int]:
    return {str(key): int(value) for key, value in pub_result.data.flag.get_counts().items()}


def route_for_backend(backend, circuits: list[QuantumCircuit]) -> list[QuantumCircuit]:
    manager = generate_preset_pass_manager(optimization_level=3, backend=backend, seed_transpiler=SEED)
    routed = manager.run(circuits)
    return routed if isinstance(routed, list) else [routed]


def select_backend(service: QiskitRuntimeService, logical: list[QuantumCircuit]):
    # These include passing and failing states; input X gates do not change the
    # reversible event core, but the set prevents a one-class preflight.
    representative_indices = [0, 3, 7, 19, 32, 39, 55, 63]
    rows, backends = [], {}
    for backend in service.backends(operational=True, min_num_qubits=N_INPUT + 1):
        try:
            routed = route_for_backend(backend, [logical[index] for index in representative_indices])
            survivals = [independent_calibration_survival(circuit, backend)[0] for circuit in routed]
            cz = [int(circuit.count_ops().get("cz", 0)) for circuit in routed]
            status = backend.status()
            rows.append({
                "backend": backend.name,
                "pending_jobs": int(status.pending_jobs),
                "status": str(status.status_msg),
                "mean_calibration_survival_proxy": float(np.mean(survivals)),
                "min_calibration_survival_proxy": float(np.min(survivals)),
                "mean_cz": float(np.mean(cz)),
                "min_cz": int(np.min(cz)),
                "max_cz": int(np.max(cz)),
            })
            backends[backend.name] = backend
        except Exception as exc:
            rows.append({"backend": backend.name, "routing_error": f"{type(exc).__name__}: {exc}"})
    valid = [row for row in rows if "routing_error" not in row]
    if not valid:
        raise RuntimeError("no operational accessible backend could route the final-event probe")
    chosen = max(valid, key=lambda row: (row["mean_calibration_survival_proxy"], -row["mean_cz"], -row["pending_jobs"]))
    for row in valid:
        row["selected"] = row is chosen
    return backends[chosen["backend"]], rows


def cube_text(cube: tuple[int | None, ...]) -> str:
    literals = []
    for index, value in enumerate(cube):
        if value is not None:
            literals.append(f"b{index}" if value else f"~b{index}")
    return " & ".join(literals) if literals else "1"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--submit", action="store_true")
    args = parser.parse_args()

    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    spec = next(row for row in source["conservative_affine_oracle"]["integer_specs"] if int(row["input_bits_per_variable"]) == 2)
    marked = {
        state
        for state in range(2**N_INPUT)
        if portable.expected_pass([(state >> bit) & 1 for bit in range(N_INPUT)], spec)
    }
    failing = set(range(2**N_INPUT)) - marked
    failing_cubes = exact_disjoint_cover(failing, N_INPUT)
    oracle = complement_cover_oracle(failing_cubes)
    verification = verify_oracle(oracle, marked)
    if not verification["all_pass"]:
        raise AssertionError(verification)
    _ops, arithmetic_registers = portable.build_oracle_ops(spec)

    logical = [basis_probe_circuit(oracle, state) for state in range(2**N_INPUT)]
    service = QiskitRuntimeService(name=ACCOUNT_NAME)
    if not free_open_plan(service):
        raise RuntimeError("submission guard: saved IBM instance is not the free Open Plan")
    usage_before = service.usage()
    backend, backend_selection = select_backend(service, logical)
    routed = route_for_backend(backend, logical)

    rows = []
    for state, circuit in enumerate(routed):
        counts = circuit.count_ops()
        survival, n_calibrated = independent_calibration_survival(circuit, backend)
        rows.append({
            "input_state": state,
            "input_bits_little_endian": [(state >> bit) & 1 for bit in range(N_INPUT)],
            "expected_flag": int(state in marked),
            "shots": SHOTS,
            "isa_depth": int(circuit.depth()),
            "isa_size": int(circuit.size()),
            "isa_cz": int(counts.get("cz", 0)),
            "isa_sx": int(counts.get("sx", 0)),
            "isa_rz": int(counts.get("rz", 0)),
            "isa_x": int(counts.get("x", 0)),
            "physical_qubits": physical_layout(circuit),
            "independent_calibration_survival_proxy": survival,
            "calibrated_instructions_in_proxy": n_calibrated,
        })

    OUT.mkdir(parents=True, exist_ok=True)
    qasm_index = next(index for index, row in enumerate(rows) if row["expected_flag"] == 0)
    (OUT / "PSA_FINAL_EVENT_2BIT_REPRESENTATIVE_ISA.qasm").write_text(qasm3.dumps(routed[qasm_index]), encoding="utf-8")
    payload = {
        "schema": "psa-ibm-final-event-2bit-probe/v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "submission_requested": bool(args.submit),
        "source": str(SOURCE.relative_to(HERE)),
        "account_guard": {
            "saved_account_name": ACCOUNT_NAME,
            "plan": "open",
            "pricing_type": "free",
            "usage_consumed_seconds_before": usage_before["usage_consumed_seconds"],
            "usage_limit_seconds": usage_before["usage_limit_seconds"],
            "usage_remaining_seconds_before": usage_before["usage_remaining_seconds"],
            "usage_limit_reached_before": usage_before["usage_limit_reached"],
        },
        "event_compilation": {
            "input_bits_per_variable": 2,
            "variables": 3,
            "state_qubits": N_INPUT,
            "flag_qubits": 1,
            "compact_logical_qubits": N_INPUT + 1,
            "portable_arithmetic_logical_qubits": arithmetic_registers["total_logical_qubits"],
            "uniform_grid_states": 2**N_INPUT,
            "marked_states": len(marked),
            "failing_states": len(failing),
            "uniform_grid_event_fraction": len(marked) / 2**N_INPUT,
            "failing_state_indices": sorted(failing),
            "failing_disjoint_cubes": [[value for value in cube] for cube in failing_cubes],
            "failing_cube_expression": " OR ".join(f"({cube_text(cube)})" for cube in failing_cubes),
            "exhaustive_reversible_verification": verification,
        },
        "backend": {
            "name": backend.name,
            "num_qubits": backend.num_qubits,
            "status": str(backend.status().status_msg),
            "pending_jobs_at_routing": int(backend.status().pending_jobs),
            "calibration_last_update": str(getattr(backend.properties(), "last_update_date", None)),
        },
        "backend_selection": backend_selection,
        "experiment": {
            "shots_per_circuit": SHOTS,
            "routed_circuits": len(routed),
            "qpu_submitted_circuits": len(routed) if args.submit else 0,
            "transpiler_optimization_level": 3,
            "transpiler_seed": SEED,
        },
        "routing_summary": {
            "cz_range": [min(row["isa_cz"] for row in rows), max(row["isa_cz"] for row in rows)],
            "depth_range": [min(row["isa_depth"] for row in rows), max(row["isa_depth"] for row in rows)],
            "size_range": [min(row["isa_size"] for row in rows), max(row["isa_size"] for row in rows)],
            "mean_calibration_survival_proxy": float(np.mean([row["independent_calibration_survival_proxy"] for row in rows])),
        },
        "routing_rows": rows,
        "qpu_job": None,
        "claim_limits": [
            "This exhaustively tests the reversible truth mapping of the exact final-model two-bit event, not coherent amplitude estimation.",
            "The compact Boolean circuit is truth-table equivalent at two-bit resolution; it is not the 42-qubit arithmetic implementation or the 66-qubit ten-bit implementation.",
            "The two-bit uniform-grid event fraction is a coarse-discretization diagnostic and is not used as the reported process probability.",
            "Basis-state classification on one IBM QPU does not establish quantum advantage or validate the dynamic PSA equations.",
        ],
    }
    json_path = OUT / "PSA_IBM_FINAL_EVENT_2BIT_PROBE.json"
    json_path.write_text(json.dumps(payload, indent=2, allow_nan=False), encoding="utf-8")

    if args.submit:
        if usage_before["usage_limit_reached"] or float(usage_before["usage_remaining_seconds"]) < 60.0:
            raise RuntimeError("submission guard: fewer than 60 free Open Plan seconds remain")
        sampler = SamplerV2(mode=backend, options={"environment": {"job_tags": ["psa-qae-final-event", "pressure-consistent", "open-plan-only"]}})
        job = sampler.run(routed, shots=SHOTS)
        payload["qpu_job"] = {
            "job_id": job.job_id(),
            "status": str(job.status()),
            "backend": backend.name,
            "submitted_at": datetime.now(timezone.utc).isoformat(),
            "shots_per_circuit": SHOTS,
        }
        json_path.write_text(json.dumps(payload, indent=2, allow_nan=False), encoding="utf-8")
        print(json.dumps({"submitted_job_id": job.job_id(), "backend": backend.name, "circuits": len(routed), "shots": SHOTS}), flush=True)
        result = job.result()
        for row, pub_result in zip(rows, result):
            counts = result_flag_counts(pub_result)
            success = int(counts.get(str(row["expected_flag"]), 0))
            row["qpu_counts"] = counts
            row["qpu_expected_probability"] = success / SHOTS
            row["qpu_majority_correct"] = success > SHOTS / 2
        usage_after = service.usage()
        expected_probabilities = [float(row["qpu_expected_probability"]) for row in rows]
        payload["qpu_job"].update({
            "status": str(job.status()),
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "usage_seconds": json.loads(json.dumps(job.usage(), default=str)),
            "usage_consumed_seconds_after": usage_after["usage_consumed_seconds"],
            "usage_remaining_seconds_after": usage_after["usage_remaining_seconds"],
            "majority_correct_circuits": sum(int(row["qpu_majority_correct"]) for row in rows),
            "total_circuits": len(rows),
            "mean_expected_flag_probability": float(np.mean(expected_probabilities)),
            "min_expected_flag_probability": float(np.min(expected_probabilities)),
            "max_expected_flag_probability": float(np.max(expected_probabilities)),
            "passing_state_mean_expected_probability": float(np.mean([row["qpu_expected_probability"] for row in rows if row["expected_flag"] == 1])),
            "failing_state_mean_expected_probability": float(np.mean([row["qpu_expected_probability"] for row in rows if row["expected_flag"] == 0])),
        })
        json_path.write_text(json.dumps(payload, indent=2, allow_nan=False), encoding="utf-8")

    with (OUT / "PSA_IBM_FINAL_EVENT_2BIT_PROBE.csv").open("w", newline="", encoding="utf-8") as handle:
        flat = [{key: json.dumps(value) if isinstance(value, (list, dict)) else value for key, value in row.items()} for row in rows]
        writer = csv.DictWriter(handle, fieldnames=list(flat[0]))
        writer.writeheader()
        writer.writerows(flat)

    qpu = payload["qpu_job"]
    lines = [
        "# IBM QPU probe of the final pressure-consistent PSA event",
        "",
        f"The exact two-bit event has `{len(marked)}/64` marked states. Its failing complement is represented by three disjoint cubes and the resulting seven-qubit reversible circuit passed all `{verification['basis_states_checked']}` input/flag basis checks locally.",
        "",
        f"Backend: `{backend.name}`. Routed CZ range: `{payload['routing_summary']['cz_range'][0]}–{payload['routing_summary']['cz_range'][1]}`; depth range: `{payload['routing_summary']['depth_range'][0]}–{payload['routing_summary']['depth_range'][1]}`.",
    ]
    if qpu and "majority_correct_circuits" in qpu:
        lines += [
            "",
            "## QPU result",
            "",
            f"- job: `{qpu['job_id']}`",
            f"- majority-correct truth-table states: `{qpu['majority_correct_circuits']}/{qpu['total_circuits']}`",
            f"- mean expected-label probability: `{qpu['mean_expected_flag_probability']:.4f}`",
            f"- minimum expected-label probability: `{qpu['min_expected_flag_probability']:.4f}`",
            f"- reported QPU usage: `{qpu['usage_seconds']}`",
            f"- free Open Plan seconds remaining: `{qpu['usage_remaining_seconds_after']}`",
        ]
    lines += ["", "## Claim limits", "", *[f"- {item}" for item in payload["claim_limits"]], ""]
    (OUT / "PSA_IBM_FINAL_EVENT_2BIT_PROBE.md").write_text("\n".join(lines), encoding="utf-8")

    fig, axes = plt.subplots(1, 2, figsize=(11.2, 4.25), constrained_layout=True)
    state_index = [row["input_state"] for row in rows]
    colors = ["#1f77b4" if row["expected_flag"] else "#d95f02" for row in rows]
    axes[0].scatter(state_index, [row["isa_cz"] for row in rows], c=colors, s=25)
    axes[0].set(xlabel="two-bit input state", ylabel="routed CZ count", title="Exact final-event circuit routing")
    axes[0].grid(alpha=0.2)
    if qpu and "majority_correct_circuits" in qpu:
        axes[1].scatter(state_index, [row["qpu_expected_probability"] for row in rows], c=colors, s=25)
        axes[1].axhline(0.5, color="black", lw=1, ls="--")
        axes[1].set_ylim(0, 1.02)
        axes[1].set(xlabel="two-bit input state", ylabel="expected-label probability", title="Actual IBM QPU truth-table probe")
        axes[1].grid(alpha=0.2)
    else:
        axes[1].scatter(state_index, [row["independent_calibration_survival_proxy"] for row in rows], c=colors, s=25)
        axes[1].set(xlabel="two-bit input state", ylabel="calibration survival proxy", title="Preflight fidelity proxy")
        axes[1].grid(alpha=0.2)
    fig.suptitle(f"Final pressure-consistent PSA event on {backend.name}", fontweight="bold")
    fig.savefig(OUT / "PSA_IBM_FINAL_EVENT_2BIT_PROBE.png", dpi=240)
    plt.close(fig)

    print(json.dumps({
        "mode": "submitted" if args.submit else "route_only",
        "backend": backend.name,
        "free_seconds_before": usage_before["usage_remaining_seconds"],
        "marked_states": len(marked),
        "failing_cubes": [cube_text(cube) for cube in failing_cubes],
        "local_basis_checks": verification["basis_states_checked"],
        "cz_range": payload["routing_summary"]["cz_range"],
        "depth_range": payload["routing_summary"]["depth_range"],
        "mean_survival_proxy": payload["routing_summary"]["mean_calibration_survival_proxy"],
        "output": str(OUT),
    }, indent=2), flush=True)


if __name__ == "__main__":
    main()
