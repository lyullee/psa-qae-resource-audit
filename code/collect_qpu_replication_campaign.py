"""Poll and collect the frozen IBM Open-plan QPU replication campaign.

This utility never submits a workload.  It discovers the nine backend/seed
pairs declared in ``PSA_QAE_QPU_REPLICATION_CAMPAIGN_PLAN.json``, records their
live status, and retrieves only jobs that IBM already reports as completed.
It is therefore safe to rerun while jobs are queued.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from qpu_breakthrough_phase_mlae import (
    OUT,
    _complete,
    _parse_runtime_counts,
    _sanitized_usage_snapshot,
    _service,
)

PLAN = OUT / "PSA_QAE_QPU_REPLICATION_CAMPAIGN_PLAN.json"
STATUS = OUT / "PSA_QAE_QPU_REPLICATION_CAMPAIGN_STATUS.json"


def normalized_status(value: object) -> str:
    name = getattr(value, "name", None)
    return str(name if name is not None else value).upper()


def is_done(status: str) -> bool:
    return status in {"DONE", "COMPLETED"} or status.endswith((".DONE", ".COMPLETED"))


def main() -> None:
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    planned = {
        (str(row["backend"]), int(row["transpiler_seed"]))
        for row in plan["rows"]
    }
    files: dict[tuple[str, int], Path] = {}
    for path in OUT.glob("QAE_QPU_BREAKTHROUGH_PHASE_MLAE_IBM_*.json"):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        seed = payload.get("transpiler_seed")
        key = (str(payload.get("backend")), int(seed)) if seed is not None else None
        if key in planned and payload.get("job_id") and not payload.get("dry_run", False):
            files[key] = path

    missing = sorted(planned - set(files))
    service = _service()
    rows: list[dict[str, object]] = []
    retrieved = 0
    for key in sorted(files):
        path = files[key]
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("status") == "real_qpu_completed":
            rows.append({
                "backend": key[0],
                "transpiler_seed": key[1],
                "job_id": payload["job_id"],
                "status": "DONE",
                "artifact_status": payload["status"],
                "retrieved_now": False,
            })
            continue

        job = service.job(str(payload["job_id"]))
        status = normalized_status(job.status())
        retrieved_now = False
        if is_done(status):
            payload["verified_plan"] = "open"
            payload["runtime_metrics"] = job.metrics()
            properties = service.backend(str(payload["backend"])).properties()
            payload["backend_properties_last_update"] = (
                properties.last_update_date.isoformat() if properties is not None else None
            )
            payload["usage_after"] = _sanitized_usage_snapshot(service.usage())
            _complete(path, payload, _parse_runtime_counts(job.result()))
            retrieved += 1
            retrieved_now = True
        rows.append({
            "backend": key[0],
            "transpiler_seed": key[1],
            "job_id": payload["job_id"],
            "status": status,
            "artifact_status": "real_qpu_completed" if retrieved_now else payload.get("status"),
            "retrieved_now": retrieved_now,
        })

    completed = sum(row["artifact_status"] == "real_qpu_completed" for row in rows)
    summary = {
        "schema": "psa-qae-qpu-replication-campaign-status/v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "planned_jobs": len(planned),
        "discovered_jobs": len(files),
        "completed_jobs": completed,
        "retrieved_now": retrieved,
        "missing_pairs": [
            {"backend": backend, "transpiler_seed": seed}
            for backend, seed in missing
        ],
        "all_completed": completed == len(planned) and not missing,
        "usage_snapshot": _sanitized_usage_snapshot(service.usage()),
        "rows": rows,
    }
    STATUS.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
