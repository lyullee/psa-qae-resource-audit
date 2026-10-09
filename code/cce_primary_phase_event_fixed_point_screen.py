"""Screen fixed-point precision for the primary phase-stream event bridge."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RESULTS = ROOT / "10_TEA_LCA_Python" / "results" / "pycharm_publication_enhancement"
LEDGER = RESULTS / "PSA_QAE_CCE_PRIMARY_PHASE_LEDGER.json"
BRIDGE = RESULTS / "PSA_QAE_CCE_PRIMARY_PHASE_EVENT_BRIDGE.json"
OUT_JSON = RESULTS / "PSA_QAE_CCE_PRIMARY_PHASE_EVENT_FIXED_POINT_SCREEN.json"
OUT_CSV = RESULTS / "PSA_QAE_CCE_PRIMARY_PHASE_EVENT_FIXED_POINT_SCREEN.csv"
OUT_MD = RESULTS / "PSA_QAE_CCE_PRIMARY_PHASE_EVENT_FIXED_POINT_SCREEN.md"
OUT_PNG = RESULTS / "PSA_QAE_CCE_PRIMARY_PHASE_EVENT_FIXED_POINT_SCREEN_FIGURE.png"
OUT_PDF = RESULTS / "PSA_QAE_CCE_PRIMARY_PHASE_EVENT_FIXED_POINT_SCREEN_FIGURE.pdf"

INPUT_BITS_CASES = tuple(range(2, 19))
SUM_BITS_CASES = (12, 14, 16, 18, 20)
EVENT_OUTPUT_INDICES = (10, 15, 16, 17, 18, 19)  # H2 feed; all gross-product components
PARAMETERS = [
    "source_h2",
    "source_co2",
    "source_ch4",
    "source_co",
    "source_n2",
    "capacity_factor",
    "affinity_factor",
    "ldf_factor",
    "P_low_bar",
    "equalization_conductance",
    "recycle_fraction",
]


def state_vector(summary: dict) -> np.ndarray:
    return np.r_[summary["gas_component_mol"], summary["adsorbed_component_mol"]]


def raw_affine(spec: dict) -> tuple[np.ndarray, np.ndarray]:
    x_mean = np.asarray(spec["x_mean"], dtype=float)
    x_scale = np.asarray(spec["x_scale"], dtype=float)
    y_mean = np.asarray(spec["y_mean"], dtype=float)
    y_scale = np.asarray(spec["y_scale"], dtype=float)
    coef = np.asarray(spec["coef"], dtype=float)
    slopes = coef * y_scale[None, :] / x_scale[:, None]
    intercept = y_mean - x_mean @ slopes
    return intercept, slopes


def integer_spec(spec: dict, input_bits: int, output_index: int, sum_bits: int) -> dict:
    intercept, slopes = raw_affine(spec)
    xmin = np.asarray(spec["x_min"], dtype=float)
    xmax = np.asarray(spec["x_max"], dtype=float)
    span = xmax - xmin
    active = span > 1.0e-14
    levels = 2**input_bits - 1
    base = float(intercept[output_index] + xmin @ slopes[:, output_index])
    bit_weights = np.asarray(
        [
            slopes[j, output_index] * span[j] / levels * (2**bit)
            for j in range(len(span))
            if active[j]
            for bit in range(input_bits)
        ],
        dtype=float,
    )
    negative = bit_weights < 0.0
    transformed_constant = base - float(np.abs(bit_weights[negative]).sum())
    magnitude = np.abs(bit_weights)
    if float(magnitude.sum()) < 1.0e-20:
        integer_weights = np.zeros_like(magnitude, dtype=int)
        scale = 1.0
    else:
        target = 2**sum_bits - 1
        ideal = magnitude / magnitude.sum() * target
        integer_weights = np.floor(ideal).astype(int)
        residual = target - int(integer_weights.sum())
        if residual:
            order = np.argsort(-(ideal - integer_weights), kind="mergesort")
            integer_weights[order[:residual]] += 1
        scale = target / float(magnitude.sum())
    return {
        "active_indices": np.flatnonzero(active).tolist(),
        "input_bits": input_bits,
        "sum_bits": sum_bits,
        "negative_mask": negative.tolist(),
        "integer_weights": integer_weights.tolist(),
        "scale": float(scale),
        "constant": transformed_constant,
    }


def encode_inputs(values: np.ndarray, spec: dict, input_bits: int) -> np.ndarray:
    xmin = np.asarray(spec["x_min"], dtype=float)
    xmax = np.asarray(spec["x_max"], dtype=float)
    active = (xmax - xmin) > 1.0e-14
    levels = 2**input_bits - 1
    clipped = np.clip(values[:, active], xmin[active], xmax[active])
    return np.rint((clipped - xmin[active]) / (xmax[active] - xmin[active]) * levels).astype(int)


def decode(codes: np.ndarray, spec: dict) -> np.ndarray:
    bits = int(spec["input_bits"])
    bit_matrix = np.column_stack(
        [((codes[:, feature, None] >> np.arange(bits)) & 1) for feature in range(codes.shape[1])]
    ).reshape(len(codes), -1)
    negative = np.asarray(spec["negative_mask"], dtype=bool)
    bit_matrix[:, negative] = 1 - bit_matrix[:, negative]
    weights = np.asarray(spec["integer_weights"], dtype=int)
    return float(spec["constant"]) + (bit_matrix @ weights) / float(spec["scale"])


def phase_inputs(ledger: dict, bed: str) -> np.ndarray:
    rows = []
    for run in ledger["runs"]:
        phase = next(row for row in run["phase_records"] if row["bed"] == bed and row["step"] == "adsorption")
        params = [run["parameters"][key] for key in PARAMETERS]
        rows.append(np.r_[state_vector(phase["state_start"]), params])
    return np.asarray(rows, dtype=float)


def event_from_phase_outputs(outputs_a: np.ndarray, outputs_b: np.ndarray, recycle: np.ndarray):
    feed_h2 = np.maximum(outputs_a[:, 0], 0.0) + np.maximum(outputs_b[:, 0], 0.0)
    gross = np.maximum(outputs_a[:, 1:6], 0.0) + np.maximum(outputs_b[:, 1:6], 0.0)
    external = (1.0 - recycle[:, None]) * gross
    purity = external[:, 0] / np.maximum(external.sum(axis=1), 1.0e-14)
    recovery = external[:, 0] / np.maximum(feed_h2, 1.0e-14)
    label = (purity >= 0.9998) & (recovery >= 0.789)
    return purity, recovery, label


def main() -> None:
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    bridge = json.loads(BRIDGE.read_text(encoding="utf-8"))
    models = bridge["full_fit_models"]
    x_a = phase_inputs(ledger, "A")
    x_b = phase_inputs(ledger, "B")
    recycle = np.asarray([run["parameters"]["recycle_fraction"] for run in ledger["runs"]], dtype=float)
    actual_purity = np.asarray([run["event_observables"]["h2_product"] for run in ledger["runs"]], dtype=float)
    actual_recovery = np.asarray([run["event_observables"]["h2_recovery_external_proxy"] for run in ledger["runs"]], dtype=float)
    actual_label = (actual_purity >= 0.9998) & (actual_recovery >= 0.789)

    float_outputs = {}
    for bed, x in [("A", x_a), ("B", x_b)]:
        spec = models[f"{bed}_adsorption"]
        intercept, slopes = raw_affine(spec)
        float_outputs[bed] = intercept[None, EVENT_OUTPUT_INDICES] + x @ slopes[:, EVENT_OUTPUT_INDICES]
    float_purity, float_recovery, float_label = event_from_phase_outputs(float_outputs["A"], float_outputs["B"], recycle)

    nested_purity_errors = np.asarray([row["purity_abs_error"] for row in bridge["event_rows"]], dtype=float)
    nested_recovery_errors = np.asarray([row["recovery_abs_error"] for row in bridge["event_rows"]], dtype=float)
    purity_budget = 0.10 * float(np.quantile(nested_purity_errors, 0.95))
    recovery_budget = 0.10 * float(np.quantile(nested_recovery_errors, 0.95))

    summaries = []
    for sum_bits in SUM_BITS_CASES:
        for bits in INPUT_BITS_CASES:
            quantized_outputs = {}
            active_counts = []
            nonzero_counts = []
            for bed, x in [("A", x_a), ("B", x_b)]:
                model = models[f"{bed}_adsorption"]
                codes = encode_inputs(x, model, bits)
                decoded = []
                for output_index in EVENT_OUTPUT_INDICES:
                    isum = integer_spec(model, bits, output_index, sum_bits)
                    decoded.append(decode(codes, isum))
                    active_counts.append(len(isum["active_indices"]))
                    nonzero_counts.append(int(np.count_nonzero(isum["integer_weights"])))
                quantized_outputs[bed] = np.column_stack(decoded)
            purity, recovery, label = event_from_phase_outputs(quantized_outputs["A"], quantized_outputs["B"], recycle)
            purity_q_error = np.abs(purity - float_purity)
            recovery_q_error = np.abs(recovery - float_recovery)
            row = {
                "bits_per_input": bits,
                "sum_bits_per_scalar_output": sum_bits,
                "p95_purity_quantization_abs_error": float(np.quantile(purity_q_error, 0.95)),
                "p95_recovery_quantization_abs_error": float(np.quantile(recovery_q_error, 0.95)),
                "purity_budget_10pct_nested_holdout_p95": purity_budget,
                "recovery_budget_10pct_nested_holdout_p95": recovery_budget,
                "within_purity_budget": bool(np.quantile(purity_q_error, 0.95) <= purity_budget),
                "within_recovery_budget": bool(np.quantile(recovery_q_error, 0.95) <= recovery_budget),
                "event_matches_vs_actual": int(np.sum(label == actual_label)),
                "event_matches_vs_float_map": int(np.sum(label == float_label)),
                "false_positives_vs_actual": int(np.sum(~actual_label & label)),
                "false_negatives_vs_actual": int(np.sum(actual_label & ~label)),
                "max_active_inputs": int(max(active_counts)),
                "median_nonzero_bit_weights": float(np.median(nonzero_counts)),
            }
            row["within_both_budgets"] = bool(row["within_purity_budget"] and row["within_recovery_budget"])
            row["all_event_labels_match"] = bool(row["event_matches_vs_actual"] == len(actual_label))
            row["sequential_scalar_register_proxy_qubits"] = int(row["max_active_inputs"] * bits + sum_bits)
            summaries.append(row)

    adequate = [row for row in summaries if row["within_both_budgets"] and row["all_event_labels_match"]]
    selected = min(
        adequate,
        key=lambda row: (
            row["sequential_scalar_register_proxy_qubits"],
            row["bits_per_input"],
            row["sum_bits_per_scalar_output"],
        ),
    ) if adequate else None

    payload = {
        "schema": "psa-qae-cce-primary-phase-event-fixed-point-screen/v1",
        "status": "primary_phase_event_fixed_point_precision_screen_event_arithmetic_and_css_open",
        "source_ledger": LEDGER.name,
        "source_bridge": BRIDGE.name,
        "event_active_phase_maps": ["A_adsorption", "B_adsorption"],
        "event_active_scalar_outputs_per_map": ["in_H2", "out_H2", "out_CO2", "out_CH4", "out_CO", "out_N2"],
        "budget_definition": "fixed-point p95 event-observable error <= 10% of nested-holdout p95 phase-stream event error and 32/32 event labels retained",
        "nested_holdout_p95_purity_abs_error": float(np.quantile(nested_purity_errors, 0.95)),
        "nested_holdout_p95_recovery_abs_error": float(np.quantile(nested_recovery_errors, 0.95)),
        "purity_quantization_budget": purity_budget,
        "recovery_quantization_budget": recovery_budget,
        "float_full_fit_event_matches_vs_actual": int(np.sum(float_label == actual_label)),
        "minimum_configuration_within_budgets_and_all_labels": selected,
        "summaries": summaries,
        "qpu_submission": False,
        "claim_boundary": {
            "supported": "fixed-point precision required to preserve all 32 primary event labels for stream maps conditional on observed phase starts",
            "unsupported": "compiled division/cross-multiplication event arithmetic, free-running CSS, loader, hardware execution, or quantum advantage",
        },
    }
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with OUT_CSV.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summaries[0]))
        writer.writeheader()
        writer.writerows(summaries)

    lines = [
        "# Fixed-point screen for the primary phase-stream event bridge",
        "",
        f"The fixed-point budget is 10% of nested-holdout p95 event-observable error: purity {purity_budget:.3e}, recovery {recovery_budget:.3e}. A configuration must also retain all 32 frozen event labels.",
        "",
        "| input bits | output bits | p95 purity q-error | p95 recovery q-error | both budgets | labels | register proxy |",
        "|---:|---:|---:|---:|---|---:|---:|",
    ]
    for row in summaries:
        lines.append(
            f"| {row['bits_per_input']} | {row['sum_bits_per_scalar_output']} | "
            f"{row['p95_purity_quantization_abs_error']:.3e} | {row['p95_recovery_quantization_abs_error']:.3e} | "
            f"{row['within_both_budgets']} | {row['event_matches_vs_actual']}/32 | {row['sequential_scalar_register_proxy_qubits']} |"
        )
    lines += [
        "",
        f"The minimum configuration within both budgets while retaining every event label is `{selected}`.",
        "",
        "This screen covers the two adsorption maps and the six event-active stream outputs per map. Reversible stream summation, constant recycle scaling, threshold cross-multiplication, phase marking, uncomputation, CSS iteration, and state loading remain separate modules.",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    fig, axes = plt.subplots(1, 2, figsize=(10.8, 4.3), constrained_layout=True)
    for sum_bits in SUM_BITS_CASES:
        rows = [row for row in summaries if row["sum_bits_per_scalar_output"] == sum_bits]
        axes[0].plot([row["bits_per_input"] for row in rows], [row["p95_purity_quantization_abs_error"] for row in rows], "o-", label=f"output {sum_bits} bit")
        axes[1].plot([row["bits_per_input"] for row in rows], [row["p95_recovery_quantization_abs_error"] for row in rows], "o-", label=f"output {sum_bits} bit")
    axes[0].axhline(purity_budget, color="#c00000", linestyle="--", label="10% holdout budget")
    axes[0].set(xlabel="bits per active input", ylabel="p95 purity quantization error", title="Purity preservation", yscale="log")
    axes[0].grid(alpha=0.25)
    axes[1].axhline(recovery_budget, color="#c00000", linestyle="--", label="10% holdout budget")
    axes[1].set(xlabel="bits per active input", ylabel="p95 recovery quantization error", title="Recovery preservation", yscale="log")
    axes[1].grid(alpha=0.25)
    axes[0].legend(fontsize=7)
    axes[1].legend(fontsize=7)
    fig.savefig(OUT_PNG, dpi=250)
    fig.savefig(OUT_PDF)
    plt.close(fig)
    print(json.dumps({"status": payload["status"], "selected": selected, "qpu_submission": False}, indent=2))


if __name__ == "__main__":
    main()
