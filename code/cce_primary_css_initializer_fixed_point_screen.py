"""Screen fixed-point precision for the parameter-only CSS initializer."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from cce_primary_css_initializer_event_bridge import css_arrays
from cce_primary_phase_event_bridge import (
    PARAMETERS,
    arrays_from_ledger,
    choose_alpha_nested,
    fit_ridge,
)
from cce_primary_phase_event_fixed_point_screen import (
    decode,
    encode_inputs,
    integer_spec,
    raw_affine,
)
from cce_primary_phase_event_free_running import equalization_arrays
from cce_primary_phase_event_repeated_cycle_screen import predict_cycle


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RESULTS = ROOT / "10_TEA_LCA_Python" / "results" / "pycharm_publication_enhancement"
LEDGER = RESULTS / "PSA_QAE_CCE_PRIMARY_PHASE_LEDGER.json"
BRIDGE = RESULTS / "PSA_QAE_CCE_PRIMARY_CSS_INITIALIZER_EVENT_BRIDGE.json"
OUT_JSON = RESULTS / "PSA_QAE_CCE_PRIMARY_CSS_INITIALIZER_FIXED_POINT_SCREEN.json"
OUT_CSV = RESULTS / "PSA_QAE_CCE_PRIMARY_CSS_INITIALIZER_FIXED_POINT_SCREEN.csv"
OUT_MD = RESULTS / "PSA_QAE_CCE_PRIMARY_CSS_INITIALIZER_FIXED_POINT_SCREEN.md"
OUT_PNG = RESULTS / "PSA_QAE_CCE_PRIMARY_CSS_INITIALIZER_FIXED_POINT_SCREEN_FIGURE.png"
OUT_PDF = RESULTS / "PSA_QAE_CCE_PRIMARY_CSS_INITIALIZER_FIXED_POINT_SCREEN_FIGURE.pdf"

INPUT_BITS_CASES = tuple(range(2, 19))
SUM_BITS_CASES = (12, 14, 16, 18, 20)


def event_outputs(
    states: np.ndarray,
    parameters: np.ndarray,
    recycles: np.ndarray,
    phase_models: dict,
    eq_models: dict,
    phase_support: dict,
    eq_support: dict,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    purities = []
    recoveries = []
    labels = []
    for index in range(len(states)):
        _, _, feed, gross_product, _ = predict_cycle(
            np.maximum(states[index, :10], 0.0),
            np.maximum(states[index, 10:20], 0.0),
            parameters[index],
            phase_models,
            eq_models,
            phase_support,
            eq_support,
        )
        external = (1.0 - recycles[index]) * gross_product
        purity = float(external[0] / max(float(external.sum()), 1.0e-14))
        recovery = float(external[0] / max(float(feed[0]), 1.0e-14))
        purities.append(purity)
        recoveries.append(recovery)
        labels.append(purity >= 0.9998 and recovery >= 0.789)
    return np.asarray(purities), np.asarray(recoveries), np.asarray(labels, dtype=bool)


def main() -> None:
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    bridge = json.loads(BRIDGE.read_text(encoding="utf-8"))
    _, parameters, _ = css_arrays(ledger)
    recycles = np.asarray([run["parameters"]["recycle_fraction"] for run in ledger["runs"]], dtype=float)
    actual_labels = np.asarray([run["event_observables"]["joint_event"] for run in ledger["runs"]], dtype=bool)
    model = bridge["full_fit_css_initializer"]
    intercept, slopes = raw_affine(model)
    float_states = intercept[None, :] + parameters @ slopes

    phase_models = {}
    phase_support = {}
    for key, data in arrays_from_ledger(ledger).items():
        alpha = choose_alpha_nested(data["x"], data["y"])
        phase_models[key] = fit_ridge(data["x"], data["y"], alpha)
        phase_support[key] = (data["x"][:, :10].min(axis=0), data["x"][:, :10].max(axis=0))
    eq_models = {}
    eq_support = {}
    for index, data in equalization_arrays(ledger).items():
        alpha = choose_alpha_nested(data["x"], data["y"])
        eq_models[index] = fit_ridge(data["x"], data["y"], alpha)
        eq_support[index] = (data["x"][:, :20].min(axis=0), data["x"][:, :20].max(axis=0))

    float_purity, float_recovery, float_labels = event_outputs(
        float_states, parameters, recycles, phase_models, eq_models, phase_support, eq_support
    )
    initializer_budget = 0.10 * float(bridge["summary"]["p95_css_initializer_relative_l1"])
    event_purity_budget = 0.10 * float(bridge["summary"]["purity_p95_abs_error"])
    event_recovery_budget = 0.10 * float(bridge["summary"]["recovery_p95_abs_error"])
    summaries = []
    for sum_bits in SUM_BITS_CASES:
        for bits in INPUT_BITS_CASES:
            codes = encode_inputs(parameters, model, bits)
            quantized_states = np.column_stack(
                [decode(codes, integer_spec(model, bits, output, sum_bits)) for output in range(20)]
            )
            state_errors = np.sum(np.abs(quantized_states - float_states), axis=1) / np.maximum(
                np.sum(np.abs(float_states), axis=1), 1.0e-14
            )
            purity, recovery, labels = event_outputs(
                quantized_states,
                parameters,
                recycles,
                phase_models,
                eq_models,
                phase_support,
                eq_support,
            )
            purity_error = np.abs(purity - float_purity)
            recovery_error = np.abs(recovery - float_recovery)
            active_counts = []
            nonzero_counts = []
            for output in range(20):
                spec = integer_spec(model, bits, output, sum_bits)
                active_counts.append(len(spec["active_indices"]))
                nonzero_counts.append(int(np.count_nonzero(spec["integer_weights"])))
            row = {
                "bits_per_input": bits,
                "sum_bits_per_scalar_output": sum_bits,
                "p95_css_state_quantization_relative_l1": float(np.quantile(state_errors, 0.95)),
                "p95_purity_quantization_abs_error": float(np.quantile(purity_error, 0.95)),
                "p95_recovery_quantization_abs_error": float(np.quantile(recovery_error, 0.95)),
                "css_state_budget_10pct_nested_holdout_p95": initializer_budget,
                "purity_budget_10pct_nested_holdout_p95": event_purity_budget,
                "recovery_budget_10pct_nested_holdout_p95": event_recovery_budget,
                "within_css_state_budget": bool(np.quantile(state_errors, 0.95) <= initializer_budget),
                "within_purity_budget": bool(np.quantile(purity_error, 0.95) <= event_purity_budget),
                "within_recovery_budget": bool(np.quantile(recovery_error, 0.95) <= event_recovery_budget),
                "event_matches_vs_actual": int(np.sum(labels == actual_labels)),
                "event_matches_vs_float_map": int(np.sum(labels == float_labels)),
                "max_active_inputs": int(max(active_counts)),
                "median_nonzero_bit_weights": float(np.median(nonzero_counts)),
                "negative_state_entries": int(np.sum(quantized_states < 0.0)),
            }
            row["within_all_budgets"] = bool(
                row["within_css_state_budget"] and row["within_purity_budget"] and row["within_recovery_budget"]
            )
            row["all_event_labels_match"] = bool(row["event_matches_vs_actual"] == len(actual_labels))
            row["sequential_scalar_register_proxy_qubits"] = int(row["max_active_inputs"] * bits + sum_bits)
            summaries.append(row)

    adequate = [row for row in summaries if row["within_all_budgets"] and row["all_event_labels_match"]]
    selected = min(
        adequate,
        key=lambda row: (
            row["sequential_scalar_register_proxy_qubits"],
            row["bits_per_input"],
            row["sum_bits_per_scalar_output"],
        ),
    ) if adequate else None
    payload = {
        "schema": "psa-qae-cce-primary-css-initializer-fixed-point-screen/v1",
        "status": "parameter_only_css_initializer_fixed_point_screen_reversible_state_update_and_physical_css_open",
        "source_ledger": LEDGER.name,
        "source_bridge": BRIDGE.name,
        "scalar_outputs": 20,
        "budget_definition": "initializer and event quantization p95 errors <=10% of corresponding nested-holdout p95 errors; 32/32 labels retained",
        "float_full_fit_event_matches_vs_actual": int(np.sum(float_labels == actual_labels)),
        "minimum_configuration_within_all_budgets_and_labels": selected,
        "summaries": summaries,
        "qpu_submission": False,
        "claim_boundary": {
            "supported": "fixed-point precision for the parameter-only aggregate CSS initializer while retaining the full-fit one-cycle event",
            "unsupported": "reversible state-register update, physical CSS iteration, tank/profile propagation, hardware execution, or quantum advantage",
        },
    }
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with OUT_CSV.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summaries[0]))
        writer.writeheader()
        writer.writerows(summaries)
    lines = [
        "# Fixed-point screen for the parameter-only CSS initializer",
        "",
        f"The p95 quantization budgets are 10% of nested-held-out p95 errors: CSS state L1 `{initializer_budget:.3e}`, purity `{event_purity_budget:.3e}`, and recovery `{event_recovery_budget:.3e}`. Every configuration is propagated through the full-fit aggregate one-cycle maps and must retain 32/32 event labels.",
        "",
        f"The minimum accuracy-feasible configuration is `{selected}`.",
        "",
        "This screens the 20 scalar affine CSS-state outputs. Reversible state injection/update, tank and spatial states, physical CSS iteration, final event arithmetic, loading, routing, and hardware execution remain separate.",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    fig, axes = plt.subplots(1, 2, figsize=(10.8, 4.3), constrained_layout=True)
    for sum_bits in SUM_BITS_CASES:
        rows = [row for row in summaries if row["sum_bits_per_scalar_output"] == sum_bits]
        axes[0].plot([row["bits_per_input"] for row in rows], [row["p95_css_state_quantization_relative_l1"] for row in rows], "o-", label=f"output {sum_bits} bit")
        axes[1].plot([row["bits_per_input"] for row in rows], [row["p95_recovery_quantization_abs_error"] for row in rows], "o-", label=f"output {sum_bits} bit")
    axes[0].axhline(initializer_budget, color="#c00000", linestyle="--", label="10% holdout budget")
    axes[0].set(xlabel="bits per parameter input", ylabel="p95 CSS-state quantization L1", title="CSS initializer precision", yscale="log")
    axes[1].axhline(event_recovery_budget, color="#c00000", linestyle="--", label="10% holdout budget")
    axes[1].set(xlabel="bits per parameter input", ylabel="p95 recovery quantization error", title="Event preservation", yscale="log")
    for ax in axes:
        ax.grid(alpha=0.25)
        ax.legend(fontsize=7)
    fig.savefig(OUT_PNG, dpi=250)
    fig.savefig(OUT_PDF)
    plt.close(fig)
    print(json.dumps({"status": payload["status"], "selected": selected, "qpu_submission": False}, indent=2))


if __name__ == "__main__":
    main()
