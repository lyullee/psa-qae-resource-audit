"""Rebuild and validate the local CCE gate-compilation evidence package.

Run with the project's Qiskit virtual environment.  The command rebuilds the
finite-table gate control, structured linear-surrogate oracle, empirical-copula
loader negative control, threshold-activity audit, primary final-event
arithmetic, and candidate-policy stream-to-event oracles.  It never calls an IBM
sampler and never submits a QPU job.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RESULTS = ROOT / "10_TEA_LCA_Python" / "results" / "pycharm_publication_enhancement"
OUT_JSON = RESULTS / "PSA_QAE_CCE_GATE_COMPILATION_MANIFEST.json"
OUT_MD = RESULTS / "PSA_QAE_CCE_GATE_COMPILATION_MANIFEST.md"

SCRIPTS = (
    HERE / "compile_primary_finite_oracle_gate_resources.py",
    HERE / "compile_primary_linear_surrogate_oracle.py",
    HERE / "compile_primary_copula_state_loader.py",
    HERE / "cce_primary_threshold_activity.py",
    HERE / "compile_cce_primary_final_event_arithmetic.py",
    HERE / "compile_cce_primary_policy_stream_event_oracle.py",
)
FINITE = RESULTS / "PSA_QAE_CCE_PRIMARY_FINITE_ORACLE_GATE_RESOURCES.json"
LINEAR = RESULTS / "PSA_QAE_CCE_PRIMARY_LINEAR_SURROGATE_ORACLE.json"
LOADER = RESULTS / "PSA_QAE_CCE_PRIMARY_COPULA_STATE_LOADER.json"
THRESHOLD = RESULTS / "PSA_QAE_CCE_PRIMARY_THRESHOLD_ACTIVITY.json"
FINAL_EVENT = RESULTS / "PSA_QAE_CCE_PRIMARY_FINAL_EVENT_ARITHMETIC.json"
POLICY_STREAM_EVENT = RESULTS / "PSA_QAE_CCE_PRIMARY_POLICY_STREAM_EVENT_ORACLE.json"
IBM_PREFLIGHT = RESULTS / "PSA_QAE_CCE_PRIMARY_FINITE_ORACLE_IBM_PREFLIGHT_ibm_marrakesh.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-rerun", action="store_true")
    args = parser.parse_args()

    runs = []
    if not args.skip_rerun:
        for script in SCRIPTS:
            result = subprocess.run(
                [sys.executable, str(script)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            runs.append(
                {
                    "script": str(script.relative_to(ROOT)),
                    "returncode": result.returncode,
                    "stdout_tail": result.stdout[-1000:],
                    "stderr_tail": result.stderr[-1000:],
                }
            )
            if result.returncode != 0:
                raise SystemExit(
                    f"{script.name} failed with return code {result.returncode}:\n{result.stderr}"
                )

    finite = load(FINITE)
    linear = load(LINEAR)
    loader = load(LOADER)
    threshold = load(THRESHOLD)
    final_event = load(FINAL_EVENT)
    policy_stream_event = load(POLICY_STREAM_EVENT)
    preflight = load(IBM_PREFLIGHT)
    linear7 = next(
        row for row in linear["rows"] if int(row["input_bits_per_feature"]) == 7
    )
    loader_rows = {
        int(row["bits_per_active_feature"]): row
        for row in loader["compiled_rows"]
    }
    validations = {
        "finite_gate_status": finite["status"]
        == "finite_primary_event_table_synthesized_to_primitive_gates_not_continuous_psa_oracle",
        "finite_logical_queries": finite["total_frozen_mlae_experiment"]["all_to_all_CX"]["logical_oracle_queries"] == 3500,
        "finite_all_to_all_cx": finite["total_frozen_mlae_experiment"]["all_to_all_CX"]["median_transpiled_two_qubit_gates"] == 432000.0,
        "linear_gate_status": linear["status"]
        == "structured_fixed_point_linear_response_oracle_compiled_loader_and_cyclic_psa_open",
        "linear_first_bits_below_mlae_rmse": linear["fixed_point"]["first_case_below_observed_noiseless_mlae_rmse"] == 7,
        "linear_7bit_qubits": linear7["total_logical_qubits"] == 99,
        "linear_7bit_cx": linear7["transpiled_cx"] == 35160,
        "linear_7bit_schedule_lower_bound": linear7["frozen_schedule_cx_lower_bound_excluding_loader"] == 52740000,
        "loader_status": loader["status"]
        == "exact_low_bit_empirical_copula_loader_compiled_accuracy_tier_dense_loader_intractable",
        "loader_1bit_fidelity": abs(loader_rows[1]["statevector_fidelity_check"] - 1.0) < 1e-12,
        "loader_2bit_cx": loader_rows[2]["transpiled_cx_prepare"] == 262125,
        "loader_7bit_dense_boundary": loader["accuracy_tier"]["loader_qubits"] == 63
        and loader["accuracy_tier"]["dense_probability_table_eib"] == 64.0,
        "threshold_status": threshold["status"]
        == "frozen_threshold_activity_audit_not_primary_threshold_retuning",
        "frozen_purity_inactive": threshold["frozen_primary_row"]["p427_purity_marginal"] == 1.0,
        "active_joint_sensitivity_rows": len(threshold["active_joint_rows_selecting_0420"]) == 8,
        "final_event_status": final_event["status"]
        == "primary_quantized_joint_event_arithmetic_compiled_clean_phase_oracle_stream_aggregation_and_css_open",
        "final_event_precision": final_event["precision_screen"]["selected"]["bits"] == 16
        and final_event["coefficient_screen"]["selected"]["coefficient_bits"] == 8,
        "final_event_labels": final_event["verification"]["integer_event_matches"] == 32
        and final_event["verification"]["false_positives"] == 0
        and final_event["verification"]["false_negatives"] == 0,
        "final_event_primitive_resources": final_event["primitive_gate_compile"]["clean_phase_oracle"]["logical_qubits"] == 125
        and final_event["primitive_gate_compile"]["clean_phase_oracle"]["cx"] == 182981,
        "policy_stream_event_status": policy_stream_event["status"]
        == "candidate_policy_collapsed_stream_aggregation_and_joint_event_compiled_physical_css_open",
        "policy_stream_event_precision": policy_stream_event["precision_screen"]["selected"]["aggregate_bits"] == 19
        and policy_stream_event["precision_screen"]["selected"]["within_both_budgets_and_labels"] is True,
        "policy_stream_event_labels": policy_stream_event["verification"]["candidate_integer_event_matches_vs_float"] == 96
        and policy_stream_event["verification"]["ledger_support_event_matches_vs_actual"] == 32
        and policy_stream_event["verification"]["candidate_input_clip_count"] == 0,
        "policy_stream_event_resources": max(
            row["clean_phase_oracle"]["logical_qubits"]
            for row in policy_stream_event["primitive_gate_compile"]["policy_resources"]
        ) == 510
        and max(
            row["clean_phase_oracle"]["cx"]
            for row in policy_stream_event["primitive_gate_compile"]["policy_resources"]
        ) == 1286021,
        "ibm_preflight_no_submission": preflight["submission"]["job_submitted"] is False
        and preflight["submission"]["qpu_quota_consumed"] is False,
    }
    status = "pass" if all(validations.values()) else "fail"

    artifacts = [
        HERE / "psa_two_bed_spatial_tank_n2_independent_source_uncertainty_32.csv",
        HERE / "psa_independent_source_surrogate_same_prior_qmc_32.py",
        *SCRIPTS,
        FINITE,
        RESULTS / "PSA_QAE_CCE_PRIMARY_FINITE_ORACLE_GATE_RESOURCES.csv",
        RESULTS / "PSA_QAE_CCE_PRIMARY_FINITE_ORACLE_GATE_RESOURCES.md",
        RESULTS / "PSA_QAE_CCE_PRIMARY_FINITE_ORACLE_GATE_RESOURCES_FIGURE.png",
        LINEAR,
        RESULTS / "PSA_QAE_CCE_PRIMARY_LINEAR_SURROGATE_ORACLE.csv",
        RESULTS / "PSA_QAE_CCE_PRIMARY_LINEAR_SURROGATE_ORACLE.md",
        RESULTS / "PSA_QAE_CCE_PRIMARY_LINEAR_SURROGATE_ORACLE_FIGURE.png",
        LOADER,
        RESULTS / "PSA_QAE_CCE_PRIMARY_COPULA_STATE_LOADER.csv",
        RESULTS / "PSA_QAE_CCE_PRIMARY_COPULA_STATE_LOADER.md",
        RESULTS / "PSA_QAE_CCE_PRIMARY_COPULA_STATE_LOADER_FIGURE.png",
        THRESHOLD,
        RESULTS / "PSA_QAE_CCE_PRIMARY_THRESHOLD_ACTIVITY.csv",
        RESULTS / "PSA_QAE_CCE_PRIMARY_THRESHOLD_ACTIVITY.md",
        RESULTS / "PSA_QAE_CCE_PRIMARY_THRESHOLD_ACTIVITY_FIGURE.png",
        FINAL_EVENT,
        RESULTS / "PSA_QAE_CCE_PRIMARY_FINAL_EVENT_ARITHMETIC.csv",
        RESULTS / "PSA_QAE_CCE_PRIMARY_FINAL_EVENT_ARITHMETIC.md",
        RESULTS / "PSA_QAE_CCE_PRIMARY_FINAL_EVENT_ARITHMETIC_FIGURE.png",
        RESULTS / "PSA_QAE_CCE_PRIMARY_FINAL_EVENT_ARITHMETIC_FIGURE.pdf",
        POLICY_STREAM_EVENT,
        RESULTS / "PSA_QAE_CCE_PRIMARY_POLICY_STREAM_EVENT_ORACLE.csv",
        RESULTS / "PSA_QAE_CCE_PRIMARY_POLICY_STREAM_EVENT_ORACLE.md",
        RESULTS / "PSA_QAE_CCE_PRIMARY_POLICY_STREAM_EVENT_ORACLE_FIGURE.png",
        RESULTS / "PSA_QAE_CCE_PRIMARY_POLICY_STREAM_EVENT_ORACLE_FIGURE.pdf",
        IBM_PREFLIGHT,
        RESULTS / "PSA_QAE_CCE_PRIMARY_FINITE_ORACLE_IBM_PREFLIGHT_ibm_marrakesh.csv",
        RESULTS / "PSA_QAE_CCE_PRIMARY_FINITE_ORACLE_IBM_PREFLIGHT_ibm_marrakesh.md",
    ]
    missing = [str(path) for path in artifacts if not path.exists()]
    if missing:
        raise FileNotFoundError(f"missing manifest artifacts: {missing}")
    hashes = [
        {
            "path": str(path.relative_to(ROOT)),
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
        }
        for path in artifacts
    ]
    payload = {
        "schema": "psa-qae-cce-gate-compilation-manifest/v1",
        "status": status,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "python": sys.version,
        "executable": sys.executable,
        "rerun_performed": not args.skip_rerun,
        "runs": runs,
        "validations": validations,
        "artifacts": hashes,
        "qpu_submission": False,
        "qpu_quota_consumed": False,
        "note": "The live-backend preflight artifact is hashed and checked but is not regenerated by this local runner.",
    }
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# CCE gate-compilation reproducibility manifest",
        "",
        f"Status: **{status.upper()}**",
        "",
        f"Local rebuild performed: `{not args.skip_rerun}`. QPU submission: `False`. QPU quota consumed: `False`.",
        "",
        "| validation | pass |",
        "|---|---|",
    ]
    for key, value in validations.items():
        lines.append(f"| {key} | {value} |")
    lines += [
        "",
        f"The manifest records SHA-256 hashes for `{len(hashes)}` code, input, result, report, and figure files. The IBM backend preflight is verified as a no-submission artifact but is not regenerated by the local runner because backend calibration is time-varying.",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"status": status, "validations": validations, "artifacts": len(hashes)}, indent=2))
    if status != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
