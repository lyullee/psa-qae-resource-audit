"""Regenerate and validate the frozen CCE primary PSA/QAE evidence package."""

from __future__ import annotations

import csv
import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import matplotlib
import numpy as np
import scipy

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
RESULTS = ROOT / "results" / "pycharm_publication_enhancement"
MANIFEST_JSON = RESULTS / "PSA_QAE_CCE_PRIMARY_REPRODUCIBILITY_MANIFEST.json"
MANIFEST_MD = RESULTS / "PSA_QAE_CCE_PRIMARY_REPRODUCIBILITY_MANIFEST.md"

SCRIPTS = [
    HERE / "qae_continuous_policy_selection.py",
    HERE / "cce_primary_resource_boundary.py",
]

ARTIFACTS = [
    HERE / "qae_continuous_policy_selection.py",
    HERE / "cce_primary_resource_boundary.py",
    HERE / "psa_independent_source_surrogate_same_prior_qmc_32.py",
    HERE / "psa_two_bed_spatial_tank_n2_independent_source_uncertainty_32.csv",
    HERE / "qae_controlled_oracle_resource_screen.json",
    HERE / "qae_stateprep_resource_screen.json",
    RESULTS / "PSA_QAE_CCE_PRIMARY_CASE_PROTOCOL.json",
    RESULTS / "PSA_QAE_CCE_PRIMARY_CASE_PROTOCOL.md",
    RESULTS / "PSA_QAE_CONTINUOUS_POLICY_SELECTION.json",
    RESULTS / "PSA_QAE_CONTINUOUS_POLICY_SELECTION.csv",
    RESULTS / "PSA_QAE_CONTINUOUS_POLICY_SELECTION.md",
    RESULTS / "PSA_QAE_CONTINUOUS_POLICY_SELECTION_FIGURE.png",
    RESULTS / "PSA_QAE_CONTINUOUS_POLICY_SELECTION_FIGURE.pdf",
    RESULTS / "PSA_QAE_CCE_PRIMARY_RESOURCE_BOUNDARY.json",
    RESULTS / "PSA_QAE_CCE_PRIMARY_RESOURCE_BOUNDARY.csv",
    RESULTS / "PSA_QAE_CCE_PRIMARY_RESOURCE_BOUNDARY.md",
    RESULTS / "PSA_QAE_CCE_PRIMARY_RESOURCE_BOUNDARY_FIGURE.png",
    RESULTS / "PSA_QAE_CCE_PRIMARY_RESOURCE_BOUNDARY_FIGURE.pdf",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def relative(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")


def run_scripts() -> list[dict[str, object]]:
    runs = []
    for script in SCRIPTS:
        completed = subprocess.run(
            [sys.executable, str(script)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        runs.append({
            "script": relative(script),
            "returncode": completed.returncode,
            "stdout_last_line": completed.stdout.strip().splitlines()[-1] if completed.stdout.strip() else "",
            "stderr": completed.stderr.strip(),
        })
        if completed.returncode != 0:
            raise RuntimeError(
                f"{script.name} failed with code {completed.returncode}: {completed.stderr}"
            )
    return runs


def validate() -> dict[str, object]:
    benchmark = json.loads(
        (RESULTS / "PSA_QAE_CONTINUOUS_POLICY_SELECTION.json").read_text(encoding="utf-8")
    )
    protocol = json.loads(
        (RESULTS / "PSA_QAE_CCE_PRIMARY_CASE_PROTOCOL.json").read_text(encoding="utf-8")
    )
    resource = json.loads(
        (RESULTS / "PSA_QAE_CCE_PRIMARY_RESOURCE_BOUNDARY.json").read_text(encoding="utf-8")
    )
    records = list(
        csv.DictReader(
            (RESULTS / "PSA_QAE_CONTINUOUS_POLICY_SELECTION.csv").open(encoding="utf-8")
        )
    )
    methods = {row["method"] for row in benchmark["method_summary"]}
    required_methods = {
        "MC_same_query",
        "Sobol_RQMC",
        "defensive_mixture_IS",
        "MLAE_0.00",
        "MLAE_0.01",
        "MLAE_0.05",
    }
    checks = {
        "benchmark_schema_v2": benchmark["schema"] == "psa-qae-continuous-policy-selection/v2",
        "protocol_event_matches_benchmark": protocol["inner_estimand"] == benchmark["event"],
        "protocol_policies_match_benchmark": protocol["outer_decision"]["candidate_values"] == benchmark["policies"],
        "record_count_200x6x3": len(records) == 200 * 6 * 3,
        "all_required_methods_present": methods == required_methods,
        "qae_query_arithmetic": benchmark["qae_queries"] == sum(100 * (2 * power + 1) for power in [0, 1, 2, 4, 8]),
        "frozen_reference_selection": benchmark["true_selected_policy"] == 0.420,
        "resource_uses_primary_benchmark": resource["source_benchmark"] == "PSA_QAE_CONTINUOUS_POLICY_SELECTION.json",
        "proxy_beats_equal_rmse_mc": resource["spatial_tank_proxy"]["qae_over_equal_RMSE_MC_cost"] < 1.0,
        "proxy_loses_to_observed_rqmc": resource["spatial_tank_proxy"]["qae_over_observed_RQMC_cost"] > 1.0,
        "rqmc_rmse_below_mlae": resource["observed_errors"]["RQMC_RMSE"] < resource["observed_errors"]["MLAE_zero_noise_RMSE"],
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise AssertionError(f"CCE primary package validation failed: {failed}")
    return {
        "status": "pass",
        "checks": checks,
        "record_count": len(records),
        "method_count": len(methods),
        "selected_policy": benchmark["true_selected_policy"],
    }


def main() -> None:
    runs = run_scripts()
    validation = validate()
    missing = [str(path) for path in ARTIFACTS if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing CCE primary artifacts: {missing}")
    artifacts = [
        {
            "path": relative(path),
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
        }
        for path in ARTIFACTS
    ]
    payload = {
        "schema": "psa-qae-cce-primary-reproducibility-manifest/v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "pass",
        "entry_command": f'"{sys.executable}" "{Path(__file__).resolve()}"',
        "environment": {
            "python": platform.python_version(),
            "implementation": platform.python_implementation(),
            "platform": platform.platform(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "matplotlib": matplotlib.__version__,
        },
        "script_runs": runs,
        "validation": validation,
        "artifacts": artifacts,
        "scope": "local deterministic estimator/resource package; excludes live IBM QPU resubmission",
    }
    MANIFEST_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# CCE primary PSA–QAE reproducibility manifest",
        "",
        f"Status: **{payload['status'].upper()}**",
        "",
        "One command regenerates the frozen estimator benchmark and the primary resource boundary, validates the shared event/policy definitions and expected record structure, and hashes the inputs, code, and outputs. Live IBM QPU resubmission is excluded so the command consumes no quantum quota.",
        "",
        "```powershell",
        payload["entry_command"],
        "```",
        "",
        f"Validated `{validation['record_count']:,}` estimator records across `{validation['method_count']}` method/noise rows. The selected policy is recycle `{validation['selected_policy']:.3f}`.",
        "",
        "| artifact | bytes | SHA-256 |",
        "|---|---:|---|",
    ]
    for artifact in artifacts:
        lines.append(
            f"| `{artifact['path']}` | {artifact['bytes']:,} | `{artifact['sha256']}` |"
        )
    MANIFEST_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": payload["status"],
        "validation": validation,
        "artifacts": len(artifacts),
        "manifest": relative(MANIFEST_JSON),
    }, indent=2))


if __name__ == "__main__":
    main()
