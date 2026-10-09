"""Verify every artifact hash in the local CCE submission package manifest."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RESULTS = ROOT / "10_TEA_LCA_Python" / "results" / "pycharm_publication_enhancement"
MANIFEST = RESULTS / "PSA_QAE_CCE_SUBMISSION_PACKAGE_MANIFEST.json"
OUT_JSON = RESULTS / "PSA_QAE_CCE_SUBMISSION_PACKAGE_VERIFICATION.json"
OUT_MD = RESULTS / "PSA_QAE_CCE_SUBMISSION_PACKAGE_VERIFICATION.md"


def checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    rows = []
    for expected in manifest["artifacts"]:
        path = ROOT / expected["path"]
        exists = path.exists()
        observed_size = path.stat().st_size if exists else None
        observed_sha256 = checksum(path) if exists else None
        rows.append(
            {
                "path": expected["path"],
                "exists": exists,
                "size_match": exists and observed_size == expected["bytes"],
                "sha256_match": exists and observed_sha256 == expected["sha256"],
                "expected_bytes": expected["bytes"],
                "observed_bytes": observed_size,
            }
        )
    passed = all(row["exists"] and row["size_match"] and row["sha256_match"] for row in rows)
    payload = {
        "schema": "psa-qae-cce-submission-package-verification/v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "pass" if passed else "fail",
        "manifest_status": manifest["status"],
        "submission_ready": manifest["submission_ready"],
        "qpu_submission": manifest["qpu_submission"],
        "artifact_count_expected": manifest["artifact_count"],
        "artifact_count_checked": len(rows),
        "all_exist": all(row["exists"] for row in rows),
        "all_sizes_match": all(row["size_match"] for row in rows),
        "all_sha256_match": all(row["sha256_match"] for row in rows),
        "rows": rows,
        "note": "Pass proves file presence and integrity against the local manifest only; external evidence gates remain open.",
    }
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# CCE submission package verification",
        "",
        f"Status: **{payload['status']}**",
        "",
        f"Artifacts checked: **{len(rows)}**. All exist: **{payload['all_exist']}**. All sizes match: **{payload['all_sizes_match']}**. All SHA-256 hashes match: **{payload['all_sha256_match']}**.",
        "",
        f"Submission ready remains **{payload['submission_ready']}**. QPU submission recorded by the package assembly: **{payload['qpu_submission']}**.",
        "",
        payload["note"],
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({key: payload[key] for key in ["status", "artifact_count_checked", "all_exist", "all_sizes_match", "all_sha256_match", "submission_ready", "qpu_submission"]}, indent=2))
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
