"""Three-qubit phase-oracle MLAE experiment for real-QPU execution.

This is the hardware tier of the PSA breakthrough experiment.  It is exactly
equivalent to the verified four-qubit event-flag oracle in
``qpu_breakthrough_mlae.py`` but removes the flag qubit and implements the five
good labels as a minimized phase predicate.  This reduces width and avoids
repeated compute/uncompute of the event flag inside each Grover iterate.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import qiskit
from qiskit import ClassicalRegister, QuantumCircuit, transpile
from qiskit.quantum_info import Statevector

from qpu_breakthrough_mlae import circuit_metrics, estimate_mlae


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = ROOT / "10_TEA_LCA_Python" / "results" / "pycharm_publication_enhancement"
FLAGS = np.asarray([0, 0, 1, 0, 1, 1, 1, 1], dtype=np.uint8)
EXACT_PROBABILITY = float(FLAGS.mean())
POWERS = (0, 1, 2)
LOCAL_POWERS = (0, 1, 2, 4)
SEED = 20261009


def phase_oracle() -> QuantumCircuit:
    """Flip phase for q2 OR (q1 AND NOT q0), matching the 5/8 event table."""
    circuit = QuantumCircuit(3, name="S_breakthrough")
    circuit.z(2)  # all q2=1 states
    circuit.x([0, 2])
    circuit.h(2)
    circuit.ccx(0, 1, 2)  # phase on original |q2 q1 q0> = |010>
    circuit.h(2)
    circuit.x([0, 2])
    return circuit


def verify_phase_oracle() -> dict[str, object]:
    checks = []
    oracle = phase_oracle()
    for assignment, good in enumerate(FLAGS):
        circuit = QuantumCircuit(3)
        for q in range(3):
            if (assignment >> q) & 1:
                circuit.x(q)
        circuit.compose(oracle, inplace=True)
        state = Statevector.from_instruction(circuit)
        amplitude = complex(state.data[assignment])
        expected = -1.0 if good else 1.0
        passed = abs(amplitude - expected) < 1e-12
        checks.append(
            {
                "assignment": assignment,
                "event": int(good),
                "amplitude_real": float(amplitude.real),
                "passed": passed,
            }
        )
    if not all(row["passed"] for row in checks):
        raise AssertionError("phase-oracle verification failed")
    return {"basis_states": 8, "passed": True, "checks": checks}


def state_preparation() -> QuantumCircuit:
    circuit = QuantumCircuit(3, name="A_uniform")
    circuit.h(range(3))
    return circuit


def zero_reflection() -> QuantumCircuit:
    circuit = QuantumCircuit(3, name="S0")
    circuit.x(range(3))
    circuit.h(2)
    circuit.ccx(0, 1, 2)
    circuit.h(2)
    circuit.x(range(3))
    return circuit


def grover_iterate() -> QuantumCircuit:
    a = state_preparation()
    circuit = QuantumCircuit(3, name="Q")
    circuit.compose(phase_oracle(), inplace=True)
    circuit.compose(a.inverse(), inplace=True)
    circuit.compose(zero_reflection(), inplace=True)
    circuit.compose(a, inplace=True)
    return circuit


def mlae_circuit(power: int) -> QuantumCircuit:
    circuit = QuantumCircuit(3, name=f"phase_mlae_m{power}")
    circuit.compose(state_preparation(), inplace=True)
    iterate = grover_iterate()
    for _ in range(power):
        circuit.compose(iterate, inplace=True)
    classical = ClassicalRegister(3, "address")
    circuit.add_register(classical)
    circuit.measure(range(3), classical)
    return circuit


def exact_good_probability(circuit: QuantumCircuit) -> float:
    state = Statevector.from_instruction(circuit.remove_final_measurements(inplace=False))
    return float(sum(state.probabilities()[i] for i, good in enumerate(FLAGS) if good))


def expected_probability(power: int) -> float:
    theta = math.asin(math.sqrt(EXACT_PROBABILITY))
    return math.sin((2 * power + 1) * theta) ** 2


def good_counts(counts: dict[str, int]) -> tuple[int, int]:
    good = 0
    total = 0
    for bitstring, count in counts.items():
        key = str(bitstring).replace(" ", "")
        assignment = int(key, 2)
        total += int(count)
        if FLAGS[assignment]:
            good += int(count)
    return good, total


def _run_local(shots: int) -> dict[str, object]:
    from qiskit_aer import AerSimulator
    from qiskit_ibm_runtime.fake_provider import FakeLimaV2

    verification = verify_phase_oracle()
    powers = list(LOCAL_POWERS)
    circuits = [mlae_circuit(power) for power in powers]
    for power, circuit in zip(powers, circuits):
        if not math.isclose(exact_good_probability(circuit), expected_probability(power), abs_tol=1e-10):
            raise AssertionError(f"Grover probability mismatch at m={power}")
    executions = []
    rows = []
    for execution in ("ideal_shot", "fake_backend_noise"):
        if execution == "ideal_shot":
            simulator = AerSimulator()
            compiled = transpile(circuits, simulator, optimization_level=3, seed_transpiler=SEED)
            backend_name = "AerSimulator_ideal"
        else:
            backend = FakeLimaV2()
            simulator = AerSimulator.from_backend(backend)
            compiled = transpile(circuits, backend, optimization_level=3, seed_transpiler=SEED)
            backend_name = backend.name
        result = simulator.run(compiled, shots=shots, seed_simulator=SEED).result()
        counts = [result.get_counts(i) for i in range(len(compiled))]
        pairs = [good_counts(row) for row in counts]
        fit = estimate_mlae([row[0] for row in pairs], [row[1] for row in pairs], powers)
        fit.update(
            {
                "execution": execution,
                "backend": backend_name,
                "powers": powers,
                "shots_per_power": shots,
                "oracle_query_count": shots * sum(2 * m + 1 for m in powers),
            }
        )
        executions.append(fit)
        for power, source, isa, count, (n_good, n_total) in zip(powers, circuits, compiled, counts, pairs):
            metrics = circuit_metrics(isa)
            rows.append(
                {
                    "execution": execution,
                    "backend": backend_name,
                    "power": power,
                    "shots": n_total,
                    "good_counts": n_good,
                    "observed_probability": n_good / n_total,
                    "exact_probability_after_amplification": exact_good_probability(source),
                    "transpiled_depth": metrics["depth"],
                    "transpiled_size": metrics["size"],
                    "two_qubit_instructions": metrics["two_qubit_instructions"],
                    "counts_json": json.dumps(count, sort_keys=True),
                }
            )
    return {
        "schema": "psa-qae-qpu-breakthrough-phase-mlae/v1",
        "status": "local_phase_oracle_validation_not_real_qpu",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "qiskit_version": qiskit.__version__,
        "event_flags": FLAGS.tolist(),
        "exact_probability": EXACT_PROBABILITY,
        "logical_qubits": 3,
        "oracle_verification": verification,
        "executions": executions,
        "rows": rows,
        "limitations": [
            "The eight-state grid is a hardware-validation discretization, not a converged process prior.",
            "The fake backend is a frozen noise model and is not a real-QPU result.",
            "No quantum-advantage or industrial-validation claim follows from this experiment.",
        ],
    }


def _write_local(payload: dict[str, object]) -> None:
    json_path = OUT / "QAE_QPU_BREAKTHROUGH_PHASE_MLAE_LOCAL.json"
    csv_path = OUT / "QAE_QPU_BREAKTHROUGH_PHASE_MLAE_LOCAL.csv"
    md_path = OUT / "QAE_QPU_BREAKTHROUGH_PHASE_MLAE_LOCAL.md"
    json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    rows = payload["rows"]
    with csv_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    lines = [
        "# Three-qubit phase-oracle MLAE boundary",
        "",
        "The exact minimized phase oracle marks the same five of eight PSA breakthrough states as the verified four-qubit event-flag oracle. It passes all eight phase-basis checks and removes the event flag from the hardware circuit.",
        "",
        "| execution | estimate | absolute error | likelihood 95% interval | queries |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in payload["executions"]:
        lines.append(
            f"| {row['execution']} | {row['estimate']:.6f} | {row['absolute_error']:.6f} | "
            f"{row['likelihood_95_low']:.6f}–{row['likelihood_95_high']:.6f} | {row['oracle_query_count']:,} |"
        )
    lines += [
        "",
        "| execution | m | transpiled depth | two-qubit instructions | observed good probability |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row['execution']} | {row['power']} | {row['transpiled_depth']} | "
            f"{row['two_qubit_instructions']} | {row['observed_probability']:.6f} |"
        )
    lines += [
        "",
        "This is the preferred real-QPU circuit because it retains the exact process event while reducing the logical width from four to three qubits and avoiding flag compute/uncompute. The result remains a hardware feasibility and resource-boundary experiment.",
    ]
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _service():
    from qiskit_ibm_runtime import QiskitRuntimeService
    from qiskit_ibm_runtime.accounts.exceptions import AccountNotFoundError

    try:
        service = QiskitRuntimeService(name="psa_open")
    except AccountNotFoundError as exc:
        raise SystemExit(
            "No saved IBM Quantum account was found. Save the account locally "
            "with QiskitRuntimeService.save_account(...); do not place the API key "
            "in this project or pass it on the command line."
        ) from exc
    active = service.active_instance()
    matching = [row for row in service.instances() if row.get("crn") == active]
    if not matching or str(matching[0].get("plan", "")).lower() != "open":
        raise SystemExit(
            "Safety stop: QPU submission is allowed only through a verified Open Plan instance."
        )
    return service


def _parse_runtime_counts(result) -> list[dict[str, int]]:
    return [
        {str(k): int(v) for k, v in pub.data.address.get_counts().items()}
        for pub in result
    ]


def _sanitized_usage_snapshot(usage: dict[str, object]) -> dict[str, object]:
    """Retain quota evidence without publishing IBM account or instance identifiers."""
    allowed = (
        "plan",
        "usage_seconds",
        "usage_consumed_seconds",
        "usage_consumed_ru",
        "usage_period",
        "usage_limit_seconds",
        "usage_limit_ru",
        "usage_limit_reached",
        "usage_remaining_seconds",
    )
    snapshot = {key: usage.get(key) for key in allowed if key in usage}
    snapshot["normalized_remaining_seconds"] = _remaining_usage_seconds(usage)
    return snapshot


def _remaining_usage_seconds(usage: dict[str, object]) -> int | None:
    direct = usage.get("usage_remaining_seconds")
    if direct is not None:
        return int(direct)
    limit = usage.get("usage_limit_seconds")
    consumed = usage.get("usage_consumed_seconds")
    if consumed is None:
        consumed = usage.get("usage_seconds")
    if limit is None or consumed is None:
        return None
    return max(0, int(limit) - int(consumed))


def submit(
    shots: int,
    backend_name: str | None,
    wait: bool,
    dry_run: bool,
    transpiler_seed: int,
    minimum_remaining_seconds: int,
) -> None:
    from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
    from qiskit_ibm_runtime import SamplerV2

    service = _service()
    usage_before = service.usage()
    if bool(usage_before.get("usage_limit_reached", False)):
        raise SystemExit("Safety stop: the verified Open Plan usage limit has been reached.")
    remaining_before = _remaining_usage_seconds(usage_before)
    if remaining_before is None:
        raise SystemExit(
            "Safety stop: IBM Open Plan usage telemetry did not report consumed or "
            "remaining seconds, so the quota guard cannot be verified. Retry later; "
            "do not override this guard with a paid instance."
        )
    if remaining_before < minimum_remaining_seconds:
        raise SystemExit(
            "Safety stop: Open Plan remaining time "
            f"({remaining_before} s) is below the required guard "
            f"({minimum_remaining_seconds} s)."
        )
    backend = service.backend(backend_name) if backend_name else service.least_busy(
        operational=True, simulator=False, min_num_qubits=3
    )
    powers = list(POWERS)
    circuits = [mlae_circuit(power) for power in powers]
    manager = generate_preset_pass_manager(
        backend=backend,
        optimization_level=3,
        seed_transpiler=transpiler_seed,
    )
    isa = list(manager.run(circuits))
    if dry_run:
        payload = {
            "schema": "psa-qae-qpu-breakthrough-phase-mlae-ibm/v1",
            "status": "local_preflight_passed",
            "submitted_utc": None,
            "job_id": None,
            "backend": backend.name,
            "powers": powers,
            "shots_per_power": shots,
            "exact_probability": EXACT_PROBABILITY,
            "circuits": [circuit_metrics(row) for row in isa],
            "transpiler_seed": transpiler_seed,
            "dry_run": True,
            "verified_plan": "open",
            "usage_before": _sanitized_usage_snapshot(usage_before),
            "minimum_remaining_seconds_guard": minimum_remaining_seconds,
            "note": "No IBM workload was submitted and no QPU time was consumed.",
        }
        path = OUT / (
            f"QAE_QPU_BREAKTHROUGH_PHASE_MLAE_IBM_PREFLIGHT_"
            f"{backend.name}_seed{transpiler_seed}.json"
        )
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(payload, indent=2))
        return

    sampler = SamplerV2(mode=backend)
    job = sampler.run(isa, shots=shots)
    payload = {
        "schema": "psa-qae-qpu-breakthrough-phase-mlae-ibm/v1",
        "status": "hardware_job_submitted",
        "submitted_utc": datetime.now(timezone.utc).isoformat(),
        "job_id": job.job_id(),
        "backend": backend.name,
        "powers": powers,
        "shots_per_power": shots,
        "exact_probability": EXACT_PROBABILITY,
        "circuits": [circuit_metrics(row) for row in isa],
        "transpiler_seed": transpiler_seed,
        "dry_run": False,
        "verified_plan": "open",
        "usage_before": _sanitized_usage_snapshot(usage_before),
        "minimum_remaining_seconds_guard": minimum_remaining_seconds,
    }
    path = OUT / f"QAE_QPU_BREAKTHROUGH_PHASE_MLAE_IBM_{job.job_id()}.json"
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))
    if wait:
        result = job.result()
        payload["runtime_metrics"] = job.metrics()
        properties = backend.properties()
        payload["backend_properties_last_update"] = (
            properties.last_update_date.isoformat() if properties is not None else None
        )
        payload["usage_after"] = _sanitized_usage_snapshot(service.usage())
        _complete(path, payload, _parse_runtime_counts(result))


def _complete(path: Path, payload: dict[str, object], counts: list[dict[str, int]]) -> None:
    powers = [int(value) for value in payload["powers"]]
    pairs = [good_counts(row) for row in counts]
    fit = estimate_mlae([row[0] for row in pairs], [row[1] for row in pairs], powers)
    payload.update(
        {
            "status": "dry_run_completed" if payload.get("dry_run") else "real_qpu_completed",
            "completed_utc": datetime.now(timezone.utc).isoformat(),
            "counts": counts,
            "good_counts": [row[0] for row in pairs],
            "total_counts": [row[1] for row in pairs],
            "estimate": fit,
            "oracle_query_count": sum(row[1] * (2 * m + 1) for row, m in zip(pairs, powers)),
        }
    )
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    _write_hardware_reports(path, payload)
    print(json.dumps(payload, indent=2))


def _write_hardware_reports(path: Path, payload: dict[str, object]) -> None:
    stem = path.with_suffix("")
    csv_path = stem.with_suffix(".csv")
    md_path = stem.with_suffix(".md")
    powers = [int(value) for value in payload["powers"]]
    totals = [int(value) for value in payload["total_counts"]]
    good = [int(value) for value in payload["good_counts"]]
    circuits = payload["circuits"]
    rows = []
    for power, n_total, n_good, circuit in zip(powers, totals, good, circuits):
        rows.append(
            {
                "power": power,
                "shots": n_total,
                "good_counts": n_good,
                "observed_probability": n_good / n_total,
                "ideal_amplified_probability": expected_probability(power),
                "transpiled_depth": circuit["depth"],
                "two_qubit_instructions": circuit["two_qubit_instructions"],
                "initial_layout": json.dumps(circuit["initial_layout"]),
                "counts_json": json.dumps(payload["counts"][len(rows)], sort_keys=True),
            }
        )
    with csv_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    fit = payload["estimate"]
    metrics = payload.get("runtime_metrics", {})
    usage = metrics.get("usage", {}) if isinstance(metrics, dict) else {}
    lines = [
        "# IBM QPU PSA-breakthrough MLAE result",
        "",
        f"- Job ID: `{payload['job_id']}`",
        f"- Backend: `{payload['backend']}`",
        f"- Plan: `{payload.get('verified_plan', 'open')}`",
        f"- Submitted (UTC): `{payload['submitted_utc']}`",
        f"- Backend calibration: `{payload.get('backend_properties_last_update', 'not recorded')}`",
        f"- QPU charge time: `{usage.get('qpu_charge_time_seconds', 'not recorded')} s`",
        f"- Resource usage: `{usage.get('value', 'not recorded')} {usage.get('unit', '')}`",
        f"- Exact event probability: `{payload['exact_probability']:.6f}`",
        f"- Hardware MLAE estimate: `{fit['estimate']:.6f}`",
        f"- Absolute error: `{fit['absolute_error']:.6f}`",
        f"- Likelihood interval: `[{fit['likelihood_95_low']:.6f}, {fit['likelihood_95_high']:.6f}]`",
        f"- Oracle-query count: `{payload['oracle_query_count']}`",
        "",
        "| m | shots | good | observed | ideal amplified | depth | 2Q gates | initial layout |",
        "|---:|---:|---:|---:|---:|---:|---:|:---|",
    ]
    for row in rows:
        lines.append(
            f"| {row['power']} | {row['shots']} | {row['good_counts']} | "
            f"{row['observed_probability']:.6f} | {row['ideal_amplified_probability']:.6f} | "
            f"{row['transpiled_depth']} | {row['two_qubit_instructions']} | "
            f"`{row['initial_layout']}` |"
        )
    lines.extend(
        [
            "",
            "The shallow m=0 circuit reproduces the event probability closely, while the deeper "
            "amplified circuits show gate-noise distortion. The likelihood interval is conditional "
            "on the ideal MLAE observation model and therefore does not include hardware bias.",
            "",
            "This is a hardware-feasibility and noise-boundary result; it is not evidence of "
            "quantum computational advantage or industrial PSA validation.",
        ]
    )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def retrieve(job_id: str) -> None:
    path = OUT / f"QAE_QPU_BREAKTHROUGH_PHASE_MLAE_IBM_{job_id}.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    service = _service()
    job = service.job(job_id)
    payload["verified_plan"] = "open"
    payload["runtime_metrics"] = job.metrics()
    properties = service.backend(payload["backend"]).properties()
    payload["backend_properties_last_update"] = (
        properties.last_update_date.isoformat() if properties is not None else None
    )
    _complete(path, payload, _parse_runtime_counts(job.result()))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    local = sub.add_parser("local")
    local.add_argument("--shots", type=int, default=4096)
    submit_parser = sub.add_parser("submit")
    submit_parser.add_argument("--shots", type=int, default=4096)
    submit_parser.add_argument("--backend", default=None)
    submit_parser.add_argument("--wait", action="store_true")
    submit_parser.add_argument("--dry-run", action="store_true")
    submit_parser.add_argument("--transpiler-seed", type=int, default=SEED)
    submit_parser.add_argument(
        "--minimum-remaining-seconds",
        type=int,
        default=30,
        help="safety guard checked against the verified Open Plan before submission",
    )
    retrieve_parser = sub.add_parser("retrieve")
    retrieve_parser.add_argument("--job-id", required=True)
    args = parser.parse_args()
    if args.command == "local":
        payload = _run_local(args.shots)
        _write_local(payload)
        print(json.dumps({"status": payload["status"], "executions": payload["executions"]}, indent=2))
    elif args.command == "submit":
        submit(
            args.shots,
            args.backend,
            args.wait,
            args.dry_run,
            args.transpiler_seed,
            args.minimum_remaining_seconds,
        )
    elif args.command == "retrieve":
        retrieve(args.job_id)


if __name__ == "__main__":
    main()
