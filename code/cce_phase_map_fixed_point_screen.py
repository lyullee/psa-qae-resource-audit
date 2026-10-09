"""Screen fixed-point resolution for the calibrated one-cycle phase maps."""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RESULTS = ROOT / "10_TEA_LCA_Python" / "results" / "pycharm_publication_enhancement"
BRIDGE = RESULTS / "PSA_QAE_CCE_CALIBRATED_ONE_CYCLE_PHASE_MAP.json"
LEDGER = RESULTS / "PSA_QAE_DIRECT_PHYSICAL_PHASE_LEDGER.json"
SOURCE = HERE / "psa_two_bed_parameter_uncertainty.csv"
OUT_JSON = RESULTS / "PSA_QAE_CCE_PHASE_MAP_FIXED_POINT_SCREEN.json"
OUT_CSV = RESULTS / "PSA_QAE_CCE_PHASE_MAP_FIXED_POINT_SCREEN.csv"
OUT_MD = RESULTS / "PSA_QAE_CCE_PHASE_MAP_FIXED_POINT_SCREEN.md"
OUT_PNG = RESULTS / "PSA_QAE_CCE_PHASE_MAP_FIXED_POINT_SCREEN_FIGURE.png"
OUT_PDF = RESULTS / "PSA_QAE_CCE_PHASE_MAP_FIXED_POINT_SCREEN_FIGURE.pdf"

sys.path.insert(0, str(HERE.parent))
from psa_qae.cce_calibrated_one_cycle_phase_map import static_features  # noqa: E402
from psa_qae.psa_two_bed_parameter_uncertainty import feed_cases  # noqa: E402


INPUT_BITS_CASES = tuple(range(2, 17))
SUM_BITS_CASES = (12, 14, 16, 18)


def raw_affine(spec: dict) -> tuple[np.ndarray, np.ndarray]:
    x_mean = np.asarray(spec["x_mean"], dtype=float)
    x_scale = np.asarray(spec["x_scale"], dtype=float)
    y_mean = np.asarray(spec["y_mean"], dtype=float)
    y_scale = np.asarray(spec["y_scale"], dtype=float)
    standardized = np.asarray(spec["standardized_coefficients"], dtype=float)
    slopes = standardized * y_scale[None, :] / x_scale[:, None]
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
    if float(magnitude.sum()) < 1.0e-18:
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
        "negative_mask": negative,
        "integer_weights": integer_weights,
        "scale": float(scale),
        "constant": transformed_constant,
    }


def encode_inputs(values: np.ndarray, spec: dict, input_bits: int) -> np.ndarray:
    xmin = np.asarray(spec["x_min"], dtype=float)
    xmax = np.asarray(spec["x_max"], dtype=float)
    active = (xmax - xmin) > 1.0e-14
    levels = 2**input_bits - 1
    clipped = np.clip(values[:, active], xmin[active], xmax[active])
    return np.rint(
        (clipped - xmin[active]) / (xmax[active] - xmin[active]) * levels
    ).astype(int)


def decode(codes: np.ndarray, isum: dict) -> np.ndarray:
    bits = int(isum["input_bits"])
    bit_matrix = np.column_stack(
        [
            ((codes[:, feature, None] >> np.arange(bits)) & 1)
            for feature in range(codes.shape[1])
        ]
    ).reshape(len(codes), -1)
    negative = np.asarray(isum["negative_mask"], dtype=bool)
    bit_matrix[:, negative] = 1 - bit_matrix[:, negative]
    weights = np.asarray(isum["integer_weights"], dtype=int)
    return float(isum["constant"]) + (bit_matrix @ weights) / float(isum["scale"])


def relative_l1(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    return np.sum(np.abs(a - b), axis=1) / np.maximum(np.sum(np.abs(b), axis=1), 1.0e-12)


def main() -> None:
    bridge = json.loads(BRIDGE.read_text(encoding="utf-8"))
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    with SOURCE.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    source = {int(row["sample"]): row for row in rows}
    cases = {case["case_id"]: case for case in feed_cases()}

    phase_records: dict[str, list[tuple[np.ndarray, np.ndarray]]] = {}
    for run in ledger["runs"]:
        static = static_features(source[int(run["sample"])], cases)
        for record in run["phase_records"]:
            key = f"{record['bed']}_{record['step']}"
            start = np.asarray(record["state_start"], dtype=float)
            phase_records.setdefault(key, []).append((np.r_[start, static], start))

    holdout_state = np.asarray(
        [row["state_relative_l1"] for row in bridge["one_step_rows"]], dtype=float
    )
    holdout_outlet = np.asarray(
        [row["outlet_h2_abs_error"] for row in bridge["one_step_rows"]], dtype=float
    )
    state_budget = 0.10 * float(np.quantile(holdout_state, 0.95))
    outlet_budget = 0.10 * float(np.quantile(holdout_outlet, 0.95))
    summaries = []
    detailed = []

    for sum_bits in SUM_BITS_CASES:
        for bits in INPUT_BITS_CASES:
            state_errors = []
            outlet_errors = []
            nonzero_weights = []
            active_inputs = []
            for phase, spec in bridge["full_fit_models"].items():
                pairs = phase_records[phase]
                x = np.asarray([item[0] for item in pairs], dtype=float)
                start = np.asarray([item[1] for item in pairs], dtype=float)
                intercept, slopes = raw_affine(spec)
                float_y = intercept[None, :] + x @ slopes
                codes = encode_inputs(x, spec, bits)
                quantized_y = np.column_stack(
                    [
                        decode(codes, integer_spec(spec, bits, target, sum_bits))
                        for target in range(float_y.shape[1])
                    ]
                )
                state_error = relative_l1(
                    start + quantized_y[:, :8], start + float_y[:, :8]
                )
                outlet_error = np.abs(quantized_y[:, 8] - float_y[:, 8])
                state_errors.extend(state_error.tolist())
                outlet_errors.extend(outlet_error.tolist())
                for target in range(float_y.shape[1]):
                    ispec = integer_spec(spec, bits, target, sum_bits)
                    nonzero_weights.append(
                        int(np.count_nonzero(ispec["integer_weights"]))
                    )
                    active_inputs.append(len(ispec["active_indices"]))
                detailed.append(
                    {
                        "bits_per_input": bits,
                        "sum_bits_per_scalar_output": sum_bits,
                        "phase": phase,
                        "median_state_quantization_relative_l1": float(np.median(state_error)),
                        "p95_state_quantization_relative_l1": float(np.quantile(state_error, 0.95)),
                        "median_outlet_h2_quantization_abs_error": float(np.median(outlet_error)),
                        "p95_outlet_h2_quantization_abs_error": float(np.quantile(outlet_error, 0.95)),
                    }
                )
            summary = {
                "bits_per_input": bits,
                "sum_bits_per_scalar_output": sum_bits,
                "median_state_quantization_relative_l1": float(np.median(state_errors)),
                "p95_state_quantization_relative_l1": float(np.quantile(state_errors, 0.95)),
                "median_outlet_h2_quantization_abs_error": float(np.median(outlet_errors)),
                "p95_outlet_h2_quantization_abs_error": float(np.quantile(outlet_errors, 0.95)),
                "state_budget_10pct_holdout_p95": state_budget,
                "outlet_budget_10pct_holdout_p95": outlet_budget,
                "within_state_budget": float(np.quantile(state_errors, 0.95)) <= state_budget,
                "within_outlet_budget": float(np.quantile(outlet_errors, 0.95)) <= outlet_budget,
                "max_active_inputs": int(max(active_inputs)),
                "median_nonzero_integer_bit_weights_per_scalar_output": float(
                    np.median(nonzero_weights)
                ),
            }
            summary["within_both_budgets"] = bool(
                summary["within_state_budget"] and summary["within_outlet_budget"]
            )
            summary["sequential_register_proxy_qubits"] = int(
                summary["max_active_inputs"] * bits + sum_bits
            )
            summaries.append(summary)

    adequate = [row for row in summaries if row["within_both_budgets"]]
    first_adequate = (
        min(
            adequate,
            key=lambda row: (
                row["sequential_register_proxy_qubits"],
                row["bits_per_input"],
                row["sum_bits_per_scalar_output"],
            ),
        )
        if adequate
        else None
    )
    payload = {
        "schema": "psa-qae-cce-phase-map-fixed-point-screen/v1",
        "status": "calibrated_phase_map_fixed_point_screen_not_reversible_cycle_compilation",
        "source_bridge": BRIDGE.name,
        "input_bits_cases": list(INPUT_BITS_CASES),
        "sum_bits_cases": list(SUM_BITS_CASES),
        "budget_definition": "fixed-point p95 error <= 10% of nested-holdout p95 phase-map error",
        "nested_holdout_p95_state_relative_l1": float(np.quantile(holdout_state, 0.95)),
        "nested_holdout_p95_outlet_h2_abs_error": float(np.quantile(holdout_outlet, 0.95)),
        "state_quantization_budget": state_budget,
        "outlet_quantization_budget": outlet_budget,
        "minimum_register_proxy_configuration_within_both_budgets": first_adequate,
        "summaries": summaries,
        "phase_details": detailed,
        "limitations": [
            "This screens affine-map quantization only; it does not implement state update, equalization, CSS iteration, or the chance-event comparator.",
            "The 10% allocation is an explicit engineering error budget, not a theorem or journal requirement.",
            "Integer weights are apportioned to a 14-bit scalar accumulator; routing, ancillas, uncomputation, and fault tolerance are not counted here.",
        ],
    }
    OUT_JSON.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    with OUT_CSV.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summaries[0]))
        writer.writeheader()
        writer.writerows(summaries)

    lines = [
        "# Fixed-point resolution screen for calibrated phase maps",
        "",
        f"The quantization budget assigns 10% of nested-holdout p95 error to fixed-point arithmetic: state relative L1 {state_budget:.3e} and outlet-H2 absolute error {outlet_budget:.3e}. Input and scalar-output accumulator precision are screened jointly.",
        "",
        "| input bits | output bits | p95 state quantization L1 | p95 outlet-H2 error | state budget | outlet budget | both | register proxy |",
        "|---:|---:|---:|---:|---|---|---|---:|",
    ]
    for row in summaries:
        lines.append(
            f"| {row['bits_per_input']} | {row['sum_bits_per_scalar_output']} | {row['p95_state_quantization_relative_l1']:.3e} | "
            f"{row['p95_outlet_h2_quantization_abs_error']:.3e} | "
            f"{row['within_state_budget']} | {row['within_outlet_budget']} | "
            f"{row['within_both_budgets']} | {row['sequential_register_proxy_qubits']} |"
        )
    lines += [
        "",
        f"The minimum sequential-register proxy configuration within both declared budgets is {first_adequate}.",
        "",
        "This closes the numerical fixed-point screen only. Actual reversible state update, equalization, repeated CSS, event comparison, primitive gates, and loader remain separate resource steps.",
        "",
        f"Artifacts: {OUT_JSON.name}, {OUT_CSV.name}, {OUT_PNG.name}.",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    fig, axes = plt.subplots(1, 2, figsize=(10.8, 4.2), constrained_layout=True)
    for sum_bits in SUM_BITS_CASES:
        selected = [row for row in summaries if row["sum_bits_per_scalar_output"] == sum_bits]
        bits = [row["bits_per_input"] for row in selected]
        axes[0].plot(bits, [row["p95_state_quantization_relative_l1"] for row in selected], "o-", label=f"output {sum_bits} bit")
        axes[1].plot(bits, [row["p95_outlet_h2_quantization_abs_error"] for row in selected], "o-", label=f"output {sum_bits} bit")
    axes[0].axhline(state_budget, color="#c00000", linestyle="--", label="10% holdout budget")
    axes[0].set(
        xlabel="bits per active input",
        ylabel="p95 state relative L1",
        title="State-transition quantization",
        yscale="log",
    )
    axes[0].grid(alpha=0.25)
    axes[0].legend(fontsize=8)

    axes[1].axhline(outlet_budget, color="#c00000", linestyle="--", label="10% holdout budget")
    axes[1].set(
        xlabel="bits per active input",
        ylabel="p95 outlet-H2 absolute error",
        title="Outlet-composition quantization",
        yscale="log",
    )
    axes[1].grid(alpha=0.25)
    axes[1].legend(fontsize=8)
    fig.savefig(OUT_PNG, dpi=250)
    fig.savefig(OUT_PDF)
    plt.close(fig)
    print(
        json.dumps(
            {
                "status": payload["status"],
                "minimum_register_proxy_configuration_within_both_budgets": first_adequate,
                "state_budget": state_budget,
                "outlet_budget": outlet_budget,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
