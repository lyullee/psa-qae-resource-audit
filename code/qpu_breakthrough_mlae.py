"""Hardware-ready MLAE experiment for the reduced PSA breakthrough event.

The experiment encodes the centered 1-bit-per-variable grid of the existing
140 s breakthrough event.  The eight grid states have labels
``[0, 0, 1, 0, 1, 1, 1, 1]`` and therefore an exact finite probability of
5/8.  Four logical qubits are used: three address qubits and one event flag.

The default ``local`` command is safe and requires no cloud credentials.  It
verifies the reversible oracle exhaustively, runs ideal and fake-backend noisy
MLAE circuits, and compares a minterm implementation with a logic-minimized
implementation.  The ``submit`` command uses saved IBM Quantum credentials;
it never accepts or writes an API key.

Examples
--------
Local validation::

    .venv-qpu\\Scripts\\python.exe qpu_breakthrough_mlae.py local

Inspect accessible IBM backends without submitting a job::

    .venv-qpu\\Scripts\\python.exe qpu_breakthrough_mlae.py inspect

Submit the optimized circuits as one hardware job::

    .venv-qpu\\Scripts\\python.exe qpu_breakthrough_mlae.py submit --shots 4096

Retrieve a submitted job::

    .venv-qpu\\Scripts\\python.exe qpu_breakthrough_mlae.py retrieve --job-id ID
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import platform
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import numpy as np
import qiskit
from qiskit import ClassicalRegister, QuantumCircuit, transpile
from qiskit.quantum_info import Statevector


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = ROOT / "10_TEA_LCA_Python" / "results" / "pycharm_publication_enhancement"
OUT.mkdir(parents=True, exist_ok=True)

ADDRESS = (0, 1, 2)
FLAG = 3
N_QUBITS = 4
EVENT_FLAGS = np.asarray([0, 0, 1, 0, 1, 1, 1, 1], dtype=np.uint8)
EXACT_PROBABILITY = float(EVENT_FLAGS.mean())
DEFAULT_POWERS = (0, 1, 2)
LOCAL_POWERS = (0, 1, 2, 4)
SEED = 20261009


def minterm_oracle() -> QuantumCircuit:
    """Return the direct sum-of-minterms reversible event oracle."""
    oracle = QuantumCircuit(N_QUBITS, name="Uf_minterm")
    for assignment, enabled in enumerate(EVENT_FLAGS):
        if not enabled:
            continue
        zeros = [q for q in ADDRESS if not ((assignment >> q) & 1)]
        if zeros:
            oracle.x(zeros)
        oracle.mcx(list(ADDRESS), FLAG)
        if zeros:
            oracle.x(zeros)
    return oracle


def minimized_oracle() -> QuantumCircuit:
    """Return an exact mixed-polarity implementation of the same event.

    For q2, q1, q0 in big-to-small significance, the event is
    ``q2 OR (q1 AND NOT q0)``.  XOR construction of OR adds the overlap term,
    yielding one CNOT, one Toffoli, and one three-control X while q0 is
    inverted.
    """
    oracle = QuantumCircuit(N_QUBITS, name="Uf_minimized")
    oracle.cx(2, FLAG)
    oracle.x(0)
    oracle.ccx(1, 0, FLAG)
    oracle.mcx([2, 1, 0], FLAG)
    oracle.x(0)
    return oracle


def verify_oracle(oracle: QuantumCircuit) -> dict[str, object]:
    """Exhaustively verify |x,y> -> |x,y xor f(x)> for all 16 states."""
    checks = []
    for assignment in range(8):
        for target in (0, 1):
            circuit = QuantumCircuit(N_QUBITS)
            for q in ADDRESS:
                if (assignment >> q) & 1:
                    circuit.x(q)
            if target:
                circuit.x(FLAG)
            circuit.compose(oracle, inplace=True)
            state = Statevector.from_instruction(circuit)
            probabilities = state.probabilities()
            output_index = int(np.argmax(probabilities))
            expected_target = target ^ int(EVENT_FLAGS[assignment])
            expected_index = assignment | (expected_target << FLAG)
            passed = bool(
                output_index == expected_index
                and math.isclose(float(probabilities[output_index]), 1.0, abs_tol=1e-12)
            )
            checks.append(
                {
                    "assignment": assignment,
                    "target_in": target,
                    "target_out": output_index >> FLAG,
                    "expected_target_out": expected_target,
                    "passed": passed,
                }
            )
    if not all(row["passed"] for row in checks):
        raise AssertionError(f"oracle verification failed for {oracle.name}")
    return {"oracle": oracle.name, "basis_checks": len(checks), "passed": True}


def state_preparation(oracle: QuantumCircuit) -> QuantumCircuit:
    circuit = QuantumCircuit(N_QUBITS, name=f"A_{oracle.name}")
    circuit.h(list(ADDRESS))
    circuit.compose(oracle, inplace=True)
    return circuit


def zero_reflection() -> QuantumCircuit:
    reflection = QuantumCircuit(N_QUBITS, name="S0")
    reflection.x(range(N_QUBITS))
    reflection.h(FLAG)
    reflection.mcx(list(ADDRESS), FLAG)
    reflection.h(FLAG)
    reflection.x(range(N_QUBITS))
    return reflection


def good_reflection() -> QuantumCircuit:
    reflection = QuantumCircuit(N_QUBITS, name="S_good")
    reflection.z(FLAG)
    return reflection


def grover_iterate(oracle: QuantumCircuit) -> QuantumCircuit:
    """Build Q = A S0 A^-1 S_good, up to an irrelevant global phase."""
    a = state_preparation(oracle)
    iterate = QuantumCircuit(N_QUBITS, name=f"Q_{oracle.name}")
    iterate.compose(good_reflection(), inplace=True)
    iterate.compose(a.inverse(), inplace=True)
    iterate.compose(zero_reflection(), inplace=True)
    iterate.compose(a, inplace=True)
    return iterate


def mlae_circuit(power: int, oracle: QuantumCircuit) -> QuantumCircuit:
    circuit = QuantumCircuit(N_QUBITS, name=f"mlae_m{power}_{oracle.name}")
    circuit.compose(state_preparation(oracle), inplace=True)
    iterate = grover_iterate(oracle)
    for _ in range(power):
        circuit.compose(iterate, inplace=True)
    classical = ClassicalRegister(1, "flag")
    circuit.add_register(classical)
    circuit.measure(FLAG, classical[0])
    return circuit


def exact_good_probability(circuit: QuantumCircuit) -> float:
    unmeasured = circuit.remove_final_measurements(inplace=False)
    state = Statevector.from_instruction(unmeasured)
    probabilities = state.probabilities()
    return float(sum(probabilities[i] for i in range(len(probabilities)) if (i >> FLAG) & 1))


def expected_amplified_probability(power: int, p: float = EXACT_PROBABILITY) -> float:
    theta = math.asin(math.sqrt(p))
    return math.sin((2 * power + 1) * theta) ** 2


def estimate_mlae(good_counts: Iterable[int], shots: Iterable[int], powers: Iterable[int]) -> dict[str, float]:
    good = np.asarray(list(good_counts), dtype=float)
    totals = np.asarray(list(shots), dtype=float)
    m = np.asarray(list(powers), dtype=float)
    grid = np.linspace(1e-8, 1.0 - 1e-8, 200_001)
    theta = np.arcsin(np.sqrt(grid))
    probabilities = np.sin((2.0 * m[:, None] + 1.0) * theta[None, :]) ** 2
    probabilities = np.clip(probabilities, 1e-12, 1.0 - 1e-12)
    log_likelihood = np.sum(
        good[:, None] * np.log(probabilities)
        + (totals - good)[:, None] * np.log1p(-probabilities),
        axis=0,
    )
    best = int(np.argmax(log_likelihood))
    estimate = float(grid[best])
    cutoff = float(log_likelihood[best] - 1.920729410347062)  # chi2_1(0.95)/2
    support = grid[log_likelihood >= cutoff]
    return {
        "estimate": estimate,
        "absolute_error": abs(estimate - EXACT_PROBABILITY),
        "likelihood_95_low": float(support[0]),
        "likelihood_95_high": float(support[-1]),
    }


def circuit_metrics(circuit: QuantumCircuit) -> dict[str, object]:
    operations = {str(k): int(v) for k, v in circuit.count_ops().items()}
    two_qubit = 0
    for instruction in circuit.data:
        if instruction.operation.num_qubits == 2:
            two_qubit += 1
    layout = None
    if getattr(circuit, "layout", None) is not None:
        try:
            layout = list(circuit.layout.initial_index_layout(filter_ancillas=True))
        except Exception:
            layout = str(circuit.layout)
    return {
        "name": circuit.name,
        "num_qubits": circuit.num_qubits,
        "depth": int(circuit.depth()),
        "size": int(circuit.size()),
        "two_qubit_instructions": two_qubit,
        "operations": operations,
        "initial_layout": layout,
    }


def counts_good(counts: dict[str, int]) -> tuple[int, int]:
    normalized = {str(key).replace(" ", ""): int(value) for key, value in counts.items()}
    good = sum(value for key, value in normalized.items() if key.endswith("1"))
    return good, sum(normalized.values())


def _run_aer(circuits: list[QuantumCircuit], shots: int, noisy: bool) -> tuple[list[dict[str, int]], list[QuantumCircuit], str]:
    from qiskit_aer import AerSimulator

    if noisy:
        from qiskit_ibm_runtime.fake_provider import FakeLimaV2

        backend = FakeLimaV2()
        executable = transpile(
            circuits,
            backend=backend,
            optimization_level=3,
            seed_transpiler=SEED,
        )
        simulator = AerSimulator.from_backend(backend)
        backend_name = backend.name
    else:
        simulator = AerSimulator()
        executable = transpile(
            circuits,
            backend=simulator,
            optimization_level=3,
            seed_transpiler=SEED,
        )
        backend_name = "AerSimulator_ideal"
    result = simulator.run(executable, shots=shots, seed_simulator=SEED).result()
    return [result.get_counts(i) for i in range(len(executable))], list(executable), backend_name


def local_experiment(shots: int) -> dict[str, object]:
    powers = list(LOCAL_POWERS)
    oracle_builders = {"minterm": minterm_oracle, "minimized": minimized_oracle}
    rows: list[dict[str, object]] = []
    verifications = []
    estimates = []
    for oracle_name, builder in oracle_builders.items():
        oracle = builder()
        verifications.append(verify_oracle(oracle))
        circuits = [mlae_circuit(power, oracle) for power in powers]
        for power, circuit in zip(powers, circuits):
            observed = exact_good_probability(circuit)
            expected = expected_amplified_probability(power)
            if not math.isclose(observed, expected, abs_tol=1e-10):
                raise AssertionError(
                    f"amplification mismatch for {oracle_name}, m={power}: {observed} != {expected}"
                )
        for noisy in (False, True):
            result_counts, executable, backend_name = _run_aer(circuits, shots, noisy)
            good_counts = []
            total_counts = []
            for power, source, compiled, counts in zip(powers, circuits, executable, result_counts):
                good, total = counts_good(counts)
                good_counts.append(good)
                total_counts.append(total)
                rows.append(
                    {
                        "oracle": oracle_name,
                        "execution": "fake_backend_noise" if noisy else "ideal_shot",
                        "backend": backend_name,
                        "power": power,
                        "shots": total,
                        "good_counts": good,
                        "observed_good_probability": good / total,
                        "exact_good_probability": exact_good_probability(source),
                        "expected_formula_probability": expected_amplified_probability(power),
                        "logical_depth": int(source.depth()),
                        "transpiled_depth": int(compiled.depth()),
                        "transpiled_size": int(compiled.size()),
                        "transpiled_two_qubit_instructions": circuit_metrics(compiled)["two_qubit_instructions"],
                    }
                )
            fit = estimate_mlae(good_counts, total_counts, powers)
            fit.update(
                {
                    "oracle": oracle_name,
                    "execution": "fake_backend_noise" if noisy else "ideal_shot",
                    "backend": backend_name,
                    "powers": powers,
                    "shots_per_power": shots,
                    "oracle_query_count": int(shots * sum(2 * m + 1 for m in powers)),
                }
            )
            estimates.append(fit)
    return {
        "schema": "psa-qae-qpu-breakthrough-mlae-local/v1",
        "status": "local_ideal_and_fake_backend_validation_not_real_qpu",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "software": {"python": platform.python_version(), "qiskit": qiskit.__version__},
        "process_event": {
            "description": "CO breakthrough safety margin >= 0.40 at 140 s",
            "grid": "three variables, one centered binary level per variable",
            "flags": EVENT_FLAGS.tolist(),
            "event_states": int(EVENT_FLAGS.sum()),
            "states": int(EVENT_FLAGS.size),
            "exact_probability": EXACT_PROBABILITY,
        },
        "oracle_verification": verifications,
        "powers": powers,
        "shots_per_power": shots,
        "estimates": estimates,
        "rows": rows,
        "limitations": [
            "The one-bit-per-variable grid is a circuit validation tier, not a converged PSA uncertainty discretization.",
            "FakeLimaV2 is a frozen noise/connectivity model and does not represent a contemporaneous hardware calibration.",
            "The finite probability is process-linked but its prior widths remain scenario assumptions.",
            "A real-QPU result is required before using the term hardware execution in the manuscript.",
        ],
    }


def _write_local_artifacts(payload: dict[str, object]) -> None:
    json_path = OUT / "QAE_QPU_BREAKTHROUGH_MLAE_LOCAL.json"
    csv_path = OUT / "QAE_QPU_BREAKTHROUGH_MLAE_LOCAL.csv"
    md_path = OUT / "QAE_QPU_BREAKTHROUGH_MLAE_LOCAL.md"
    json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    rows = payload["rows"]
    with csv_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    estimates = payload["estimates"]
    lines = [
        "# Hardware-ready MLAE validation for the reduced PSA breakthrough event",
        "",
        "The three-variable centered binary grid has eight states and five event states, giving an exact finite probability of `0.625`. Both the direct minterm oracle and the logic-minimized oracle pass all 16 address/target basis checks. This report contains local ideal-shot and frozen fake-backend results; it is not a real-QPU execution.",
        "",
        "| oracle | execution | estimate | absolute error | likelihood 95% interval | queries |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for row in estimates:
        lines.append(
            f"| {row['oracle']} | {row['execution']} | {row['estimate']:.6f} | "
            f"{row['absolute_error']:.6f} | {row['likelihood_95_low']:.6f}–{row['likelihood_95_high']:.6f} | "
            f"{row['oracle_query_count']:,} |"
        )
    lines += [
        "",
        "## Transpiled circuit boundary",
        "",
        "| oracle | execution | m | depth | two-qubit instructions | observed flag probability |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row['oracle']} | {row['execution']} | {row['power']} | {row['transpiled_depth']} | "
            f"{row['transpiled_two_qubit_instructions']} | {row['observed_good_probability']:.6f} |"
        )
    lines += [
        "",
        "The minimized oracle is the hardware candidate. Real-QPU reporting must add backend identity, job ID, calibration timestamp, logical-to-physical layout, raw counts, and QPU usage. The one-bit grid is retained as a circuit-validation tier and is not used as evidence of industrial PSA accuracy or quantum advantage.",
    ]
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def ibm_service():
    from qiskit_ibm_runtime import QiskitRuntimeService
    from qiskit_ibm_runtime.accounts.exceptions import AccountNotFoundError

    try:
        return QiskitRuntimeService()
    except AccountNotFoundError as exc:
        raise SystemExit(
            "No saved IBM Quantum account was found. Save the account locally "
            "with QiskitRuntimeService.save_account(...); do not place the API key "
            "in this project or pass it on the command line."
        ) from exc


def inspect_ibm() -> None:
    service = ibm_service()
    rows = []
    for backend in service.backends(operational=True, simulator=False):
        status = backend.status()
        rows.append(
            {
                "name": backend.name,
                "num_qubits": int(backend.num_qubits),
                "pending_jobs": int(getattr(status, "pending_jobs", -1)),
                "status": str(getattr(status, "status_msg", "")),
            }
        )
    print(json.dumps(sorted(rows, key=lambda row: (row["pending_jobs"], row["name"])), indent=2))


def _select_backend(service, backend_name: str | None):
    if backend_name:
        return service.backend(backend_name)
    return service.least_busy(operational=True, simulator=False, min_num_qubits=N_QUBITS)


def _ibm_counts(result, circuits: list[QuantumCircuit]) -> list[dict[str, int]]:
    output = []
    for pub_result, circuit in zip(result, circuits):
        register_name = circuit.cregs[0].name
        register_data = getattr(pub_result.data, register_name)
        output.append({str(k): int(v) for k, v in register_data.get_counts().items()})
    return output


def submit_ibm(shots: int, backend_name: str | None, wait: bool, dry_run: bool) -> None:
    from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
    from qiskit_ibm_runtime.executor_sampler import Sampler

    service = ibm_service()
    backend = _select_backend(service, backend_name)
    powers = list(DEFAULT_POWERS)
    circuits = [mlae_circuit(power, minimized_oracle()) for power in powers]
    pass_manager = generate_preset_pass_manager(backend=backend, optimization_level=3)
    isa_circuits = list(pass_manager.run(circuits))
    sampler = Sampler(mode=backend)
    job = sampler.run(isa_circuits, shots=shots, dry_run=dry_run)
    pending = {
        "schema": "psa-qae-qpu-breakthrough-mlae-ibm/v1",
        "status": "dry_run_submitted" if dry_run else "hardware_job_submitted",
        "submitted_utc": datetime.now(timezone.utc).isoformat(),
        "job_id": job.job_id(),
        "backend": backend.name,
        "backend_num_qubits": int(backend.num_qubits),
        "powers": powers,
        "shots_per_power": shots,
        "exact_probability": EXACT_PROBABILITY,
        "oracle": "logic_minimized_process_label_oracle",
        "circuits": [circuit_metrics(circuit) for circuit in isa_circuits],
        "dry_run": dry_run,
    }
    pending_path = OUT / f"QAE_QPU_BREAKTHROUGH_MLAE_IBM_{job.job_id()}.json"
    pending_path.write_text(json.dumps(pending, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(pending, indent=2))
    if wait:
        result = job.result()
        counts = _ibm_counts(result, isa_circuits)
        _write_ibm_result(pending_path, pending, counts)


def _write_ibm_result(path: Path, payload: dict[str, object], counts: list[dict[str, int]]) -> None:
    powers = [int(value) for value in payload["powers"]]
    good_counts, total_counts = zip(*(counts_good(row) for row in counts))
    fit = estimate_mlae(good_counts, total_counts, powers)
    payload.update(
        {
            "status": "dry_run_completed" if payload.get("dry_run") else "real_qpu_completed",
            "completed_utc": datetime.now(timezone.utc).isoformat(),
            "counts": counts,
            "good_counts": list(good_counts),
            "total_counts": list(total_counts),
            "estimate": fit,
            "oracle_query_count": int(sum(n * (2 * m + 1) for n, m in zip(total_counts, powers))),
        }
    )
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))


def retrieve_ibm(job_id: str) -> None:
    path = OUT / f"QAE_QPU_BREAKTHROUGH_MLAE_IBM_{job_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"missing submission metadata: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    service = ibm_service()
    job = service.job(job_id)
    result = job.result()
    powers = [int(value) for value in payload["powers"]]
    circuits = [mlae_circuit(power, minimized_oracle()) for power in powers]
    counts = _ibm_counts(result, circuits)
    _write_ibm_result(path, payload, counts)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    local = subparsers.add_parser("local", help="run exhaustive, ideal, and fake-backend validation")
    local.add_argument("--shots", type=int, default=4096)
    subparsers.add_parser("inspect", help="list accessible real IBM backends without submitting")
    submit = subparsers.add_parser("submit", help="submit the minimized MLAE circuits to IBM Quantum")
    submit.add_argument("--shots", type=int, default=4096)
    submit.add_argument("--backend", default=None)
    submit.add_argument("--wait", action="store_true")
    submit.add_argument("--dry-run", action="store_true")
    retrieve = subparsers.add_parser("retrieve", help="retrieve a previously submitted IBM job")
    retrieve.add_argument("--job-id", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.command == "local":
        payload = local_experiment(args.shots)
        _write_local_artifacts(payload)
        print(json.dumps({"status": payload["status"], "estimates": payload["estimates"]}, indent=2))
    elif args.command == "inspect":
        inspect_ibm()
    elif args.command == "submit":
        submit_ibm(args.shots, args.backend, args.wait, args.dry_run)
    elif args.command == "retrieve":
        retrieve_ibm(args.job_id)
    else:
        raise ValueError(args.command)


if __name__ == "__main__":
    main()
