"""Prepare a multi-backend QPU replication campaign without submitting jobs."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

from qpu_breakthrough_mlae import circuit_metrics
from qpu_breakthrough_phase_mlae import (
    EXACT_PROBABILITY,
    POWERS,
    _remaining_usage_seconds,
    _service,
    _sanitized_usage_snapshot,
    expected_probability,
    mlae_circuit,
    verify_phase_oracle,
)

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = ROOT / "10_TEA_LCA_Python" / "results" / "pycharm_publication_enhancement"
DEFAULT_BACKENDS = ("ibm_marrakesh", "ibm_fez", "ibm_kingston")
DEFAULT_SEEDS = (20261009, 20261010, 20261011)
PRIOR_OBSERVED_QPU_CHARGE_SECONDS = 5.0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backends", nargs="+", default=list(DEFAULT_BACKENDS))
    parser.add_argument("--seeds", nargs="+", type=int, default=list(DEFAULT_SEEDS))
    parser.add_argument("--shots", type=int, default=4096)
    args = parser.parse_args()

    verification = verify_phase_oracle()
    service = _service()
    instance = service.active_instance()
    usage = service.usage()
    if bool(usage.get("usage_limit_reached", False)):
        raise SystemExit("Safety stop: the Open Plan usage limit has been reached.")
    remaining_seconds = _remaining_usage_seconds(usage)
    if remaining_seconds is None:
        raise SystemExit(
            "Safety stop: IBM Open Plan usage telemetry is unavailable; campaign quota "
            "cannot be verified. Retry planning later."
        )
    rows: list[dict[str, object]] = []
    backend_summary = []
    for backend_name in args.backends:
        backend = service.backend(backend_name)
        status = backend.status()
        properties = backend.properties()
        calibration = properties.last_update_date.isoformat() if properties else None
        backend_summary.append({
            "backend": backend.name,
            "operational": bool(status.operational),
            "pending_jobs_at_preflight": int(status.pending_jobs),
            "status_message": status.status_msg,
            "num_qubits": int(backend.num_qubits),
            "calibration_at_preflight": calibration,
        })
        circuits = [mlae_circuit(power) for power in POWERS]
        for seed in args.seeds:
            manager = generate_preset_pass_manager(
                backend=backend,
                optimization_level=3,
                seed_transpiler=seed,
            )
            isa = list(manager.run(circuits))
            for power, compiled in zip(POWERS, isa):
                metrics = circuit_metrics(compiled)
                rows.append({
                    "backend": backend.name,
                    "transpiler_seed": seed,
                    "power": power,
                    "shots": args.shots,
                    "ideal_amplified_probability": expected_probability(power),
                    "transpiled_depth": metrics["depth"],
                    "transpiled_size": metrics["size"],
                    "two_qubit_instructions": metrics["two_qubit_instructions"],
                    "initial_layout": json.dumps(metrics["initial_layout"]),
                    "calibration_at_preflight": calibration,
                    "submitted": False,
                })

    job_count = len(args.backends) * len(args.seeds)
    estimated_charge = job_count * PRIOR_OBSERVED_QPU_CHARGE_SECONDS
    payload = {
        "schema": "psa-qae-qpu-replication-campaign-plan/v1",
        "status": "preflight_only_no_qpu_submission_no_quantum_quota_consumed",
        "qpu_submission": False,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "verified_instance_present": bool(instance),
        "verified_plan": "open",
        "usage_snapshot": _sanitized_usage_snapshot(usage),
        "event_probability": EXACT_PROBABILITY,
        "oracle_verification": verification,
        "powers": list(POWERS),
        "shots_per_circuit": args.shots,
        "backends": backend_summary,
        "transpiler_seeds": args.seeds,
        "planned_job_count": job_count,
        "planned_circuit_count": job_count * len(POWERS),
        "planned_total_shots": job_count * len(POWERS) * args.shots,
        "quota_estimate": {
            "prior_job_charge_seconds": PRIOR_OBSERVED_QPU_CHARGE_SECONDS,
            "estimated_total_charge_seconds": estimated_charge,
            "basis": "linear extrapolation from job db42v34lf4us73c24q50",
            "guaranteed": False,
        },
        "analysis_plan": [
            "Fit ideal-model MLAE separately for each backend/seed job.",
            "Report observed amplified probabilities by power and their deviations from ideal values.",
            "Use backend and transpiler seed as crossed factors for estimate bias and absolute error.",
            "Keep ideal likelihood intervals separate from between-run hardware variability.",
            "Add readout mitigation only as a paired sensitivity using the same backend and seed.",
        ],
        "stop_rules": [
            "Do not submit if the active IBM instance is not the Open plan.",
            "Do not submit when consumed or remaining Open-plan seconds cannot be verified from live usage telemetry.",
            "Do not add higher Grover powers until the m=1 and m=2 bias is characterized.",
            "Do not interpret the campaign as a PSA speedup or industrial validation.",
        ],
        "rows": rows,
    }
    json_path = OUT / "PSA_QAE_QPU_REPLICATION_CAMPAIGN_PLAN.json"
    csv_path = OUT / "PSA_QAE_QPU_REPLICATION_CAMPAIGN_PLAN.csv"
    md_path = OUT / "PSA_QAE_QPU_REPLICATION_CAMPAIGN_PLAN.md"
    json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    lines = [
        "# IBM Open multi-backend QPU replication campaign plan",
        "",
        "Status: **PREFLIGHT ONLY**. No sampler job was submitted and no QPU quota was consumed.",
        "",
        f"The frozen experiment uses the exact three-qubit `p={EXACT_PROBABILITY:.3f}` phase oracle, Grover powers `{list(POWERS)}`, and `{args.shots:,}` shots per circuit. The matrix contains `{len(args.backends)}` backends × `{len(args.seeds)}` fixed transpiler seeds = `{job_count}` planned jobs and `{job_count * len(POWERS)}` circuits.",
        "",
        f"If future jobs were charged like the existing 5 s Open-plan job, the matrix would use about `{estimated_charge:.0f} s` of QPU allowance. This is an extrapolation, not a guarantee. The campaign has not been executed so the quota remains available to other sessions.",
        "",
        f"At this preflight, the verified Open instance reported `{remaining_seconds} s` remaining of `{int(usage.get('usage_limit_seconds', 0))} s`; the usage limit was not reached. Usage must be queried again immediately before execution.",
        "",
        "| backend | seed | m | depth | 2Q gates | initial layout |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row['backend']} | {row['transpiler_seed']} | {row['power']} | "
            f"{row['transpiled_depth']} | {row['two_qubit_instructions']} | `{row['initial_layout']}` |"
        )
    lines += [
        "",
        "Each future job must be submitted separately with its recorded backend and transpiler seed. Calibration time, runtime metrics, counts, and Open-plan verification are recorded at execution/retrieval time; preflight calibration is not substituted for execution calibration.",
        "",
        "The primary analysis treats backend and seed as crossed variability sources. Ideal likelihood intervals remain conditional diagnostics and are not used as hardware-aware confidence intervals.",
    ]
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": payload["status"],
        "planned_jobs": job_count,
        "estimated_charge_seconds": estimated_charge,
        "backends": [row["backend"] for row in backend_summary],
        "artifacts": [str(json_path), str(csv_path), str(md_path)],
    }, indent=2))


if __name__ == "__main__":
    main()
