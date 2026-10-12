"""Read-only verification of the final-event IBM QPU job and archived counts."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from qiskit_ibm_runtime import QiskitRuntimeService


HERE = Path(__file__).resolve().parent
OUT = HERE / "results" / "ibm_final_event_2bit_probe"
SOURCE = OUT / "PSA_IBM_FINAL_EVENT_2BIT_PROBE.json"
VERIFICATION = OUT / "PSA_IBM_FINAL_EVENT_2BIT_JOB_VERIFICATION.json"
ACCOUNT_NAME = "psa_open"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    archived = json.loads(SOURCE.read_text(encoding="utf-8"))
    rows = archived["routing_rows"]
    if len(rows) != 64:
        raise AssertionError(f"expected 64 archived states, got {len(rows)}")
    service = QiskitRuntimeService(name=ACCOUNT_NAME)
    instances = service.instances()
    if len(instances) != 1 or instances[0].get("plan") != "open" or instances[0].get("pricing_type") != "free":
        raise RuntimeError("verification guard: active instance is not a single free Open Plan")
    job = service.job(str(archived["qpu_job"]["job_id"]))
    if str(job.status()) != "DONE":
        raise RuntimeError(f"job is not complete: {job.status()}")
    live = list(job.result())
    if len(live) != 64:
        raise AssertionError(f"expected 64 live results, got {len(live)}")
    comparisons = []
    for row, item in zip(rows, live):
        live_counts = {str(key): int(value) for key, value in item.data.flag.get_counts().items()}
        archived_counts = {str(key): int(value) for key, value in row["qpu_counts"].items()}
        shots = sum(live_counts.values())
        comparisons.append({
            "input_state": int(row["input_state"]),
            "expected_flag": int(row["expected_flag"]),
            "archived_counts": archived_counts,
            "live_counts": live_counts,
            "exact_count_match": live_counts == archived_counts,
            "majority_correct": int(live_counts.get(str(row["expected_flag"]), 0)) > shots / 2,
        })
    usage = service.usage()
    backend = job.backend()
    payload = {
        "schema": "psa-ibm-final-event-2bit-job-verification/v1",
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "read_only_retrieval": True,
        "submission_performed": False,
        "account_guard": {
            "saved_account_name": ACCOUNT_NAME,
            "plan": instances[0].get("plan"),
            "pricing_type": instances[0].get("pricing_type"),
            "region": instances[0].get("region"),
            "usage_limit_reached": usage.get("usage_limit_reached"),
            "usage_remaining_seconds": usage.get("usage_remaining_seconds"),
        },
        "job": {
            "job_id": job.job_id(),
            "status": str(job.status()),
            "backend": backend.name,
            "qpu_usage_seconds": job.usage(),
            "calibration_last_update": str(getattr(backend.properties(), "last_update_date", None)),
            "result_items": len(live),
            "shots_per_item": int(archived["experiment"]["shots_per_circuit"]),
        },
        "comparison": {
            "exact_count_matches": sum(row["exact_count_match"] for row in comparisons),
            "majority_correct_items": sum(row["majority_correct"] for row in comparisons),
            "total_items": len(comparisons),
            "rows": comparisons,
        },
        "source": {"path": SOURCE.name, "sha256": sha256(SOURCE)},
        "claim_boundary": (
            "This read-only retrieval verifies all 64 basis-state count dictionaries for the exact "
            "two-bit reduction of the final pressure-consistent event. It is not coherent amplitude "
            "estimation, execution of the 42- or 66-logical-qubit arithmetic oracle, or quantum advantage."
        ),
    }
    VERIFICATION.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({
        "job_id": job.job_id(),
        "backend": backend.name,
        "qpu_usage_seconds": job.usage(),
        "exact_count_matches": payload["comparison"]["exact_count_matches"],
        "majority_correct_items": payload["comparison"]["majority_correct_items"],
        "total_items": payload["comparison"]["total_items"],
        "free_seconds_remaining": usage.get("usage_remaining_seconds"),
        "output": str(VERIFICATION),
    }, indent=2))


if __name__ == "__main__":
    main()
