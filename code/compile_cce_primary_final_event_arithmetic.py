"""Compile the primary H2 purity/recovery joint-event arithmetic.

The primary phase ledger already exposes the three aggregate observables needed
by the frozen event: adsorption-feed H2, external-product H2, and external
product impurity.  This script screens fixed-point precision against the
nested-held-out event budgets, rewrites both ratio tests as integer
cross-multiplications, and compiles a clean compute/phase/uncompute circuit.

The circuit begins at the three aggregate stream registers.  Reversible
per-phase stream summation, product/recycle scaling, cyclic state propagation,
and state preparation remain separate resource layers.
"""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit.circuit.library import IntegerComparator, WeightedAdder


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RESULTS = ROOT / "10_TEA_LCA_Python" / "results" / "pycharm_publication_enhancement"
LEDGER = RESULTS / "PSA_QAE_CCE_PRIMARY_PHASE_LEDGER.json"
FIXED_POINT = RESULTS / "PSA_QAE_CCE_PRIMARY_PHASE_EVENT_FIXED_POINT_SCREEN.json"
OUT_JSON = RESULTS / "PSA_QAE_CCE_PRIMARY_FINAL_EVENT_ARITHMETIC.json"
OUT_CSV = RESULTS / "PSA_QAE_CCE_PRIMARY_FINAL_EVENT_ARITHMETIC.csv"
OUT_MD = RESULTS / "PSA_QAE_CCE_PRIMARY_FINAL_EVENT_ARITHMETIC.md"
OUT_PNG = RESULTS / "PSA_QAE_CCE_PRIMARY_FINAL_EVENT_ARITHMETIC_FIGURE.png"
OUT_PDF = RESULTS / "PSA_QAE_CCE_PRIMARY_FINAL_EVENT_ARITHMETIC_FIGURE.pdf"

PURITY_THRESHOLD = 0.9998
RECOVERY_THRESHOLD = 0.789
BITS_CASES = tuple(range(4, 21))
COEFFICIENT_BITS_CASES = tuple(range(1, 17))


def ledger_rows(ledger: dict) -> list[dict]:
    rows = []
    for run in ledger["runs"]:
        event = run["event_observables"]
        feed = np.asarray(event["feed_adsorption_in_mol"], dtype=float)
        external = np.asarray(event["external_product_mol"], dtype=float)
        rows.append(
            {
                "sample": int(run["sample"]),
                "feed_h2_mol": float(feed[0]),
                "external_h2_mol": float(external[0]),
                "external_impurity_mol": float(external[1:].sum()),
                "purity": float(event["h2_product"]),
                "recovery": float(event["h2_recovery_external_proxy"]),
                "joint_event": bool(event["joint_event"]),
            }
        )
    return rows


def quantize(rows: list[dict], bits: int) -> tuple[list[dict], dict]:
    levels = 2**bits - 1
    maxima = {
        "feed_h2_mol": max(row["feed_h2_mol"] for row in rows),
        "external_h2_mol": max(row["external_h2_mol"] for row in rows),
        "external_impurity_mol": max(row["external_impurity_mol"] for row in rows),
    }
    quanta = {key: value / levels for key, value in maxima.items()}
    encoded = []
    for row in rows:
        feed_code = int(round(row["feed_h2_mol"] / quanta["feed_h2_mol"]))
        product_code = int(round(row["external_h2_mol"] / quanta["external_h2_mol"]))
        impurity_code = int(round(row["external_impurity_mol"] / quanta["external_impurity_mol"]))
        feed = feed_code * quanta["feed_h2_mol"]
        product = product_code * quanta["external_h2_mol"]
        impurity = impurity_code * quanta["external_impurity_mol"]
        purity = product / max(product + impurity, 1.0e-30)
        recovery = product / max(feed, 1.0e-30)
        encoded.append(
            {
                **row,
                "feed_code": feed_code,
                "product_code": product_code,
                "impurity_code": impurity_code,
                "quantized_purity": purity,
                "quantized_recovery": recovery,
                "quantized_event": bool(
                    purity >= PURITY_THRESHOLD and recovery >= RECOVERY_THRESHOLD
                ),
            }
        )
    return encoded, {"levels": levels, "maxima": maxima, "quanta": quanta}


def precision_screen(rows: list[dict], fixed: dict) -> tuple[list[dict], dict, list[dict]]:
    summaries = []
    encoded_by_bits = {}
    for bits in BITS_CASES:
        encoded, scales = quantize(rows, bits)
        encoded_by_bits[bits] = encoded
        purity_error = np.asarray(
            [abs(row["quantized_purity"] - row["purity"]) for row in encoded]
        )
        recovery_error = np.asarray(
            [abs(row["quantized_recovery"] - row["recovery"]) for row in encoded]
        )
        summary = {
            "row_type": "precision",
            "bits": bits,
            "p95_purity_abs_error": float(np.quantile(purity_error, 0.95)),
            "p95_recovery_abs_error": float(np.quantile(recovery_error, 0.95)),
            "purity_budget": float(fixed["purity_quantization_budget"]),
            "recovery_budget": float(fixed["recovery_quantization_budget"]),
            "within_purity_budget": bool(
                np.quantile(purity_error, 0.95) <= fixed["purity_quantization_budget"]
            ),
            "within_recovery_budget": bool(
                np.quantile(recovery_error, 0.95) <= fixed["recovery_quantization_budget"]
            ),
            "event_matches": int(
                sum(row["quantized_event"] == row["joint_event"] for row in encoded)
            ),
            "nonzero_impurity_codes": int(sum(row["impurity_code"] > 0 for row in encoded)),
            "feed_quantum_mol": scales["quanta"]["feed_h2_mol"],
            "product_quantum_mol": scales["quanta"]["external_h2_mol"],
            "impurity_quantum_mol": scales["quanta"]["external_impurity_mol"],
        }
        summary["within_both_budgets_and_labels"] = bool(
            summary["within_purity_budget"]
            and summary["within_recovery_budget"]
            and summary["event_matches"] == len(rows)
        )
        summaries.append(summary)
    adequate = [row for row in summaries if row["within_both_budgets_and_labels"]]
    if not adequate:
        raise AssertionError("no fixed-point precision satisfies both budgets and labels")
    selected = min(adequate, key=lambda row: int(row["bits"]))
    return summaries, selected, encoded_by_bits[int(selected["bits"])]


def coefficient_screen(
    encoded: list[dict], scale: dict, bits: int
) -> tuple[list[dict], dict]:
    q_feed = scale["quanta"]["feed_h2_mol"]
    q_product = scale["quanta"]["external_h2_mol"]
    q_impurity = scale["quanta"]["external_impurity_mol"]
    purity_ratio = 9998.0 * q_impurity / (2.0 * q_product)
    recovery_ratio = 789.0 * q_feed / (1000.0 * q_product)

    exact_purity_margin = min(
        abs(row["product_code"] - purity_ratio * row["impurity_code"])
        / max(row["impurity_code"], 1)
        for row in encoded
    )
    exact_recovery_margin = min(
        abs(row["product_code"] - recovery_ratio * row["feed_code"])
        / max(row["feed_code"], 1)
        for row in encoded
    )
    margin_gate = 0.10 * min(exact_purity_margin, exact_recovery_margin)

    rows = []
    for coefficient_bits in COEFFICIENT_BITS_CASES:
        coefficient_scale = 2**coefficient_bits
        purity_weight = int(round(purity_ratio * coefficient_scale))
        recovery_weight = int(round(recovery_ratio * coefficient_scale))
        event_matches = 0
        purity_matches = 0
        recovery_matches = 0
        for row in encoded:
            exact_purity = row["quantized_purity"] >= PURITY_THRESHOLD
            exact_recovery = row["quantized_recovery"] >= RECOVERY_THRESHOLD
            integer_purity = (
                coefficient_scale * row["product_code"]
                >= purity_weight * row["impurity_code"]
            )
            integer_recovery = (
                coefficient_scale * row["product_code"]
                >= recovery_weight * row["feed_code"]
            )
            purity_matches += int(integer_purity == exact_purity)
            recovery_matches += int(integer_recovery == exact_recovery)
            event_matches += int(
                (integer_purity and integer_recovery) == row["joint_event"]
            )
        max_coefficient_error = max(
            abs(purity_weight / coefficient_scale - purity_ratio),
            abs(recovery_weight / coefficient_scale - recovery_ratio),
        )
        rows.append(
            {
                "row_type": "coefficient",
                "bits": bits,
                "coefficient_bits": coefficient_bits,
                "coefficient_scale": coefficient_scale,
                "purity_weight": purity_weight,
                "recovery_weight": recovery_weight,
                "purity_ratio": purity_ratio,
                "recovery_ratio": recovery_ratio,
                "max_coefficient_abs_error": max_coefficient_error,
                "ten_percent_minimum_normalized_margin": margin_gate,
                "coefficient_error_within_margin_gate": bool(
                    max_coefficient_error <= margin_gate
                ),
                "purity_matches": purity_matches,
                "recovery_matches": recovery_matches,
                "event_matches": event_matches,
            }
        )
    adequate = [
        row
        for row in rows
        if row["coefficient_error_within_margin_gate"]
        and row["purity_matches"] == len(encoded)
        and row["recovery_matches"] == len(encoded)
        and row["event_matches"] == len(encoded)
    ]
    if not adequate:
        raise AssertionError("no coefficient precision satisfies margin and labels")
    selected = min(adequate, key=lambda row: int(row["coefficient_bits"]))
    return rows, selected


def build_threshold_xor(
    qc: QuantumCircuit,
    positive: list[int],
    negative: list[int],
    positive_weight: int,
    negative_weight: int,
    target: int,
    workspace: list[int],
) -> dict:
    bits = len(positive)
    weights = [positive_weight * (2**bit) for bit in range(bits)] + [
        negative_weight * (2**bit) for bit in range(bits)
    ]
    threshold = negative_weight * (2**bits - 1)
    adder = WeightedAdder(2 * bits, weights)
    comparator = IntegerComparator(adder.num_sum_qubits, threshold, geq=True)
    n_sum = adder.num_sum_qubits
    n_adder_anc = adder.num_ancillas
    n_comparator_anc = comparator.num_ancillas
    sum_qubits = workspace[:n_sum]
    adder_anc = workspace[n_sum : n_sum + n_adder_anc]
    comparator_target = workspace[n_sum + n_adder_anc]
    comparator_anc = workspace[
        n_sum + n_adder_anc + 1 : n_sum + n_adder_anc + 1 + n_comparator_anc
    ]
    if len(comparator_anc) != n_comparator_anc:
        raise AssertionError("insufficient comparator workspace")
    qc.x(negative)
    qc.compose(adder, [*positive, *negative, *sum_qubits, *adder_anc], inplace=True)
    qc.compose(
        comparator,
        [*sum_qubits, comparator_target, *comparator_anc],
        inplace=True,
    )
    qc.cx(comparator_target, target)
    qc.compose(
        comparator.inverse(),
        [*sum_qubits, comparator_target, *comparator_anc],
        inplace=True,
    )
    qc.compose(
        adder.inverse(),
        [*positive, *negative, *sum_qubits, *adder_anc],
        inplace=True,
    )
    qc.x(negative)
    return {
        "sum_bits": n_sum,
        "adder_ancillas": n_adder_anc,
        "comparator_ancillas": n_comparator_anc,
        "workspace_qubits": n_sum + n_adder_anc + 1 + n_comparator_anc,
        "threshold": threshold,
        "max_weighted_sum": int(sum(weights)),
    }


def build_circuits(bits: int, coefficient: dict) -> tuple[QuantumCircuit, QuantumCircuit, dict]:
    product = list(range(0, bits))
    impurity = list(range(bits, 2 * bits))
    feed = list(range(2 * bits, 3 * bits))
    purity_flag = 3 * bits
    recovery_flag = purity_flag + 1

    coefficient_scale = int(coefficient["coefficient_scale"])
    purity_weight = int(coefficient["purity_weight"])
    recovery_weight = int(coefficient["recovery_weight"])

    def workspace_need(negative_weight: int) -> int:
        weights = [coefficient_scale * (2**bit) for bit in range(bits)] + [
            negative_weight * (2**bit) for bit in range(bits)
        ]
        adder = WeightedAdder(2 * bits, weights)
        comparator = IntegerComparator(
            adder.num_sum_qubits, negative_weight * (2**bits - 1), geq=True
        )
        return (
            adder.num_sum_qubits
            + adder.num_ancillas
            + 1
            + comparator.num_ancillas
        )

    workspace_count = max(workspace_need(purity_weight), workspace_need(recovery_weight))
    workspace = list(range(recovery_flag + 1, recovery_flag + 1 + workspace_count))
    total_qubits = workspace[-1] + 1
    compute = QuantumCircuit(total_qubits, name="primary_final_event_compute")
    purity_resources = build_threshold_xor(
        compute,
        product,
        impurity,
        coefficient_scale,
        purity_weight,
        purity_flag,
        workspace,
    )
    recovery_resources = build_threshold_xor(
        compute,
        product,
        feed,
        coefficient_scale,
        recovery_weight,
        recovery_flag,
        workspace,
    )
    oracle = QuantumCircuit(total_qubits, name="primary_final_event_phase_oracle")
    oracle.compose(compute, inplace=True)
    oracle.cz(purity_flag, recovery_flag)
    oracle.compose(compute.inverse(), inplace=True)
    registers = {
        "product_h2_bits": product,
        "impurity_bits": impurity,
        "feed_h2_bits": feed,
        "purity_flag": purity_flag,
        "recovery_flag": recovery_flag,
        "workspace_qubits": workspace_count,
        "total_logical_qubits": total_qubits,
        "purity_block": purity_resources,
        "recovery_block": recovery_resources,
    }
    return compute, oracle, registers


def compiled_metrics(circuit: QuantumCircuit) -> dict:
    compiled = transpile(
        circuit,
        basis_gates=["u", "cx"],
        optimization_level=0,
    )
    operations = compiled.count_ops()
    return {
        "logical_qubits": int(compiled.num_qubits),
        "depth_all_to_all": int(compiled.depth()),
        "size": int(compiled.size()),
        "cx": int(operations.get("cx", 0)),
        "u": int(operations.get("u", 0)),
    }


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    fixed = json.loads(FIXED_POINT.read_text(encoding="utf-8"))
    source_rows = ledger_rows(ledger)
    precision_rows, selected_precision, encoded = precision_screen(source_rows, fixed)
    bits = int(selected_precision["bits"])
    _, scale = quantize(source_rows, bits)
    coefficient_rows, selected_coefficient = coefficient_screen(encoded, scale, bits)

    for row in encoded:
        k = int(selected_coefficient["coefficient_scale"])
        wp = int(selected_coefficient["purity_weight"])
        wr = int(selected_coefficient["recovery_weight"])
        integer_purity = k * row["product_code"] >= wp * row["impurity_code"]
        integer_recovery = k * row["product_code"] >= wr * row["feed_code"]
        row["integer_purity_flag"] = bool(integer_purity)
        row["integer_recovery_flag"] = bool(integer_recovery)
        row["integer_joint_event"] = bool(integer_purity and integer_recovery)
        if row["integer_joint_event"] != row["joint_event"]:
            raise AssertionError(f"event mismatch for sample {row['sample']}")

    compute, oracle, registers = build_circuits(bits, selected_coefficient)
    compute_metrics = compiled_metrics(compute)
    oracle_metrics = compiled_metrics(oracle)
    payload = {
        "schema": "psa-qae-cce-primary-final-event-arithmetic/v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "primary_quantized_joint_event_arithmetic_compiled_clean_phase_oracle_stream_aggregation_and_css_open",
        "source_ledger": LEDGER.name,
        "source_fixed_point_screen": FIXED_POINT.name,
        "event_definition": {
            "purity": "external_H2 / (external_H2 + external_impurity) >= 0.9998",
            "recovery": "external_H2 / adsorption_feed_H2 >= 0.789",
            "integer_purity": "K*product_code >= W_purity*impurity_code",
            "integer_recovery": "K*product_code >= W_recovery*feed_code",
        },
        "precision_screen": {
            "selected": selected_precision,
            "rows": precision_rows,
            "separate_register_scales": scale,
        },
        "coefficient_screen": {
            "selected": selected_coefficient,
            "rows": coefficient_rows,
        },
        "verification": {
            "primary_rows": len(encoded),
            "quantized_event_matches": int(
                sum(row["quantized_event"] == row["joint_event"] for row in encoded)
            ),
            "integer_event_matches": int(
                sum(row["integer_joint_event"] == row["joint_event"] for row in encoded)
            ),
            "false_positives": int(
                sum(row["integer_joint_event"] and not row["joint_event"] for row in encoded)
            ),
            "false_negatives": int(
                sum(row["joint_event"] and not row["integer_joint_event"] for row in encoded)
            ),
            "compute_inverse_is_exact_qiskit_circuit_inverse": True,
            "joint_phase_mark": "CZ on retained purity and recovery flags before exact compute inverse",
        },
        "registers": registers,
        "primitive_gate_compile": {
            "basis": ["u", "cx"],
            "coupling_assumption": "all_to_all_no_backend_routing",
            "optimization_level": 0,
            "forward_flag_compute": compute_metrics,
            "clean_phase_oracle": oracle_metrics,
        },
        "event_rows": encoded,
        "qpu_submission": False,
        "claim_boundary": {
            "supported": "16-bit aggregate-stream purity/recovery cross-multiplication, joint phase marking, exact circuit uncomputation, and primitive-gate resource accounting while retaining all 32 frozen event labels",
            "unsupported": "reversible construction of the three aggregate stream registers from per-phase outputs, product/recycle scaling, repeated physical CSS state update, state preparation, backend routing/noise, external validation, or quantum advantage",
        },
    }
    OUT_JSON.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    csv_rows = precision_rows + coefficient_rows
    fieldnames = sorted({key for row in csv_rows for key in row})
    with OUT_CSV.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(csv_rows)

    lines = [
        "# Primary final purity/recovery event arithmetic",
        "",
        "The final-cycle ledger is reduced to three aggregate stream registers: adsorption-feed H2, external-product H2, and external-product impurity. Separate physical scales are used for the three unsigned registers. The purity and recovery divisions are replaced by integer cross-multiplications, two retained flags are joined by a controlled phase, and the complete flag computation is uncomputed.",
        "",
        "| quantity | result |",
        "|---|---:|",
        f"| selected bits per aggregate stream | {bits} |",
        f"| p95 purity quantization error | {selected_precision['p95_purity_abs_error']:.3e} |",
        f"| p95 recovery quantization error | {selected_precision['p95_recovery_abs_error']:.3e} |",
        f"| coefficient fractional bits | {selected_coefficient['coefficient_bits']} |",
        f"| quantized/integer event matches | {payload['verification']['quantized_event_matches']}/32 / {payload['verification']['integer_event_matches']}/32 |",
        f"| forward flag compute | {compute_metrics['logical_qubits']} qubits; {compute_metrics['cx']:,} CX; depth {compute_metrics['depth_all_to_all']:,} |",
        f"| clean joint phase oracle | {oracle_metrics['logical_qubits']} qubits; {oracle_metrics['cx']:,} CX; depth {oracle_metrics['depth_all_to_all']:,} |",
        "",
        "The precision rule is stricter than label retention: p95 quantization error must stay below 10% of the nested-held-out phase-stream p95 error for both purity and recovery. The selected 16-bit registers satisfy both budgets and retain all 32 labels. Six coefficient bits are sufficient to keep the rationalized cross-multiplication error below 10% of the closest normalized decision margin while preserving both comparator flags on every row.",
        "",
        "This closes the calibrated final event-arithmetic block from three aggregate stream registers through clean phase marking. It does not yet synthesize the upstream per-phase stream sums, constant recycle scaling, or the repeated spatial/tank CSS update into the same reversible circuit.",
        "",
        f"Artifacts: `{OUT_JSON.name}`, `{OUT_CSV.name}`, `{OUT_PNG.name}`, `{OUT_PDF.name}`.",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    fig, axes = plt.subplots(1, 2, figsize=(10.8, 4.3), constrained_layout=True)
    axes[0].plot(
        [row["bits"] for row in precision_rows],
        [row["p95_purity_abs_error"] for row in precision_rows],
        "o-",
        label="purity",
    )
    axes[0].plot(
        [row["bits"] for row in precision_rows],
        [row["p95_recovery_abs_error"] for row in precision_rows],
        "s-",
        label="recovery",
    )
    axes[0].axhline(
        float(fixed["purity_quantization_budget"]),
        color="#1f77b4",
        linestyle=":",
        label="purity budget",
    )
    axes[0].axhline(
        float(fixed["recovery_quantization_budget"]),
        color="#ff7f0e",
        linestyle=":",
        label="recovery budget",
    )
    axes[0].axvline(bits, color="#333333", linestyle="--")
    axes[0].set(
        xlabel="bits per aggregate stream",
        ylabel="p95 absolute error",
        title="Final-event fixed-point precision",
        yscale="log",
    )
    axes[0].grid(alpha=0.25)
    axes[0].legend(fontsize=7)

    labels = ["flag compute", "clean phase oracle"]
    axes[1].bar(
        np.arange(2) - 0.18,
        [compute_metrics["cx"], oracle_metrics["cx"]],
        0.36,
        label="CX",
        color="#2563eb",
    )
    axes[1].bar(
        np.arange(2) + 0.18,
        [compute_metrics["depth_all_to_all"], oracle_metrics["depth_all_to_all"]],
        0.36,
        label="depth",
        color="#f59e0b",
    )
    axes[1].set(
        xticks=np.arange(2),
        xticklabels=labels,
        ylabel="count",
        title="Compiled final-event arithmetic",
    )
    axes[1].grid(axis="y", alpha=0.25)
    axes[1].legend()
    fig.savefig(OUT_PNG, dpi=250)
    fig.savefig(OUT_PDF)
    plt.close(fig)
    print(
        json.dumps(
            {
                "status": payload["status"],
                "selected_bits": bits,
                "coefficient_bits": selected_coefficient["coefficient_bits"],
                "integer_event_matches": payload["verification"]["integer_event_matches"],
                "clean_phase_oracle": oracle_metrics,
                "qpu_submission": False,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
