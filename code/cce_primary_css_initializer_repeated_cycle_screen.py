"""Repeat the nested-held-out parameter-only CSS initializer cycle map.

The held run supplies only its 11 frozen parameters.  A held-out affine CSS
initializer predicts both aggregate bed states, and held-out phase/equalization
maps are iterated for 50 cycles.  The screen tests local surrogate fixed-point
stability without any held dynamic state; it does not propagate tank state or
spatial profiles and does not implement reversible CSS control.
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from cce_primary_css_initializer_event_bridge import css_arrays
from cce_primary_phase_event_bridge import (
    PARAMETERS,
    arrays_from_ledger,
    choose_alpha_nested,
    fit_ridge,
    relative_l1,
)
from cce_primary_phase_event_free_running import equalization_arrays
from cce_primary_phase_event_repeated_cycle_screen import predict_cycle


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RESULTS = ROOT / "10_TEA_LCA_Python" / "results" / "pycharm_publication_enhancement"
LEDGER = RESULTS / "PSA_QAE_CCE_PRIMARY_PHASE_LEDGER.json"
OUT_JSON = RESULTS / "PSA_QAE_CCE_PRIMARY_CSS_INITIALIZER_REPEATED_CYCLE_SCREEN.json"
OUT_CSV = RESULTS / "PSA_QAE_CCE_PRIMARY_CSS_INITIALIZER_REPEATED_CYCLE_SCREEN.csv"
OUT_MD = RESULTS / "PSA_QAE_CCE_PRIMARY_CSS_INITIALIZER_REPEATED_CYCLE_SCREEN.md"
OUT_PNG = RESULTS / "PSA_QAE_CCE_PRIMARY_CSS_INITIALIZER_REPEATED_CYCLE_SCREEN_FIGURE.png"
OUT_PDF = RESULTS / "PSA_QAE_CCE_PRIMARY_CSS_INITIALIZER_REPEATED_CYCLE_SCREEN_FIGURE.pdf"

N_CYCLES = 50
TAIL_CYCLES = 10
CSS_L1_GATE = 1.0e-4


def main() -> None:
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    samples, css_x, css_y = css_arrays(ledger)
    phase_arrays = arrays_from_ledger(ledger)
    eq_arrays = equalization_arrays(ledger)
    run_rows = []
    cycle_rows = []
    css_alphas = []
    phase_alphas: dict[str, list[float]] = defaultdict(list)
    eq_alphas: dict[str, list[float]] = defaultdict(list)

    for held_run in ledger["runs"]:
        sample = int(held_run["sample"])
        held_index = int(np.flatnonzero(samples == sample)[0])
        train_css = samples != sample
        css_alpha = choose_alpha_nested(css_x[train_css], css_y[train_css])
        css_model = fit_ridge(css_x[train_css], css_y[train_css], css_alpha)
        predicted_css = css_model.predict(css_x[held_index])[0]
        css_alphas.append(css_alpha)
        state_a0 = np.maximum(predicted_css[:10], 0.0)
        state_b0 = np.maximum(predicted_css[10:20], 0.0)
        params = np.asarray([held_run["parameters"][key] for key in PARAMETERS], dtype=float)

        phase_models = {}
        phase_support = {}
        for key, data in phase_arrays.items():
            train = data["samples"] != sample
            alpha = choose_alpha_nested(data["x"][train], data["y"][train])
            phase_models[key] = fit_ridge(data["x"][train], data["y"][train], alpha)
            phase_support[key] = (data["x"][train, :10].min(axis=0), data["x"][train, :10].max(axis=0))
            phase_alphas[f"{key[0]}_{key[1]}"].append(alpha)

        eq_models = {}
        eq_support = {}
        for index, data in eq_arrays.items():
            train = data["samples"] != sample
            alpha = choose_alpha_nested(data["x"][train], data["y"][train])
            eq_models[index] = fit_ridge(data["x"][train], data["y"][train], alpha)
            eq_support[index] = (data["x"][train, :20].min(axis=0), data["x"][train, :20].max(axis=0))
            eq_alphas[f"equalization_{index + 1}"].append(alpha)

        state_a = state_a0.copy()
        state_b = state_b0.copy()
        recycle = float(held_run["parameters"]["recycle_fraction"])
        actual_event = bool(held_run["event_observables"]["joint_event"])
        labels = []
        residuals = []
        drifts = []
        purities = []
        recoveries = []
        total_clipped_state = 0
        total_clipped_stream = 0
        total_outside = 0
        total_coordinates = 0
        for cycle in range(1, N_CYCLES + 1):
            before_a = state_a.copy()
            before_b = state_b.copy()
            state_a, state_b, feed, gross_product, diagnostics = predict_cycle(
                state_a,
                state_b,
                params,
                phase_models,
                eq_models,
                phase_support,
                eq_support,
            )
            external = (1.0 - recycle) * gross_product
            purity = float(external[0] / max(float(external.sum()), 1.0e-14))
            recovery = float(external[0] / max(float(feed[0]), 1.0e-14))
            label = bool(purity >= 0.9998 and recovery >= 0.789)
            residual = relative_l1(np.r_[state_a, state_b], np.r_[before_a, before_b])
            drift = relative_l1(np.r_[state_a, state_b], np.r_[state_a0, state_b0])
            labels.append(label)
            residuals.append(residual)
            drifts.append(drift)
            purities.append(purity)
            recoveries.append(recovery)
            total_clipped_state += diagnostics["clipped_state_entries"]
            total_clipped_stream += diagnostics["clipped_stream_entries"]
            total_outside += diagnostics["outside_training_state_coordinates"]
            total_coordinates += diagnostics["evaluated_state_coordinates"]
            cycle_rows.append(
                {
                    "sample": sample,
                    "cycle": cycle,
                    "cycle_residual_relative_l1": residual,
                    "drift_from_predicted_css_initializer_relative_l1": drift,
                    "predicted_purity": purity,
                    "predicted_recovery": recovery,
                    "predicted_event": label,
                }
            )

        tail_residuals = residuals[-TAIL_CYCLES:]
        run_rows.append(
            {
                "sample": sample,
                "actual_event": actual_event,
                "cycle_1_event": labels[0],
                "terminal_event": labels[-1],
                "terminal_event_match": labels[-1] == actual_event,
                "tail_event_constant": len(set(labels[-TAIL_CYCLES:])) == 1,
                "tail_css_gate_1e_4": max(tail_residuals) < CSS_L1_GATE,
                "terminal_purity": purities[-1],
                "terminal_recovery": recoveries[-1],
                "terminal_cycle_residual_relative_l1": residuals[-1],
                "tail_max_cycle_residual_relative_l1": max(tail_residuals),
                "terminal_drift_from_predicted_css_initializer_relative_l1": drifts[-1],
                "max_drift_from_predicted_css_initializer_relative_l1": max(drifts),
                "outside_training_state_fraction": total_outside / max(total_coordinates, 1),
                "clipped_state_entries": total_clipped_state,
                "clipped_stream_entries": total_clipped_stream,
            }
        )

    actual_labels = np.asarray([row["actual_event"] for row in run_rows], dtype=bool)
    terminal_labels = np.asarray([row["terminal_event"] for row in run_rows], dtype=bool)
    summary = {
        "held_out_runs": len(run_rows),
        "cycles_per_run": N_CYCLES,
        "terminal_event_matches": int(np.sum(actual_labels == terminal_labels)),
        "terminal_event_match_fraction": float(np.mean(actual_labels == terminal_labels)),
        "terminal_false_positive_count": int(np.sum(~actual_labels & terminal_labels)),
        "terminal_false_negative_count": int(np.sum(actual_labels & ~terminal_labels)),
        "tail_event_constant_count": int(sum(row["tail_event_constant"] for row in run_rows)),
        "tail_css_gate_1e_4_count": int(sum(row["tail_css_gate_1e_4"] for row in run_rows)),
        "median_terminal_cycle_residual_relative_l1": float(np.median([row["terminal_cycle_residual_relative_l1"] for row in run_rows])),
        "p95_terminal_cycle_residual_relative_l1": float(np.quantile([row["terminal_cycle_residual_relative_l1"] for row in run_rows], 0.95)),
        "median_terminal_drift_from_initializer_relative_l1": float(np.median([row["terminal_drift_from_predicted_css_initializer_relative_l1"] for row in run_rows])),
        "p95_terminal_drift_from_initializer_relative_l1": float(np.quantile([row["terminal_drift_from_predicted_css_initializer_relative_l1"] for row in run_rows], 0.95)),
        "median_outside_training_state_fraction": float(np.median([row["outside_training_state_fraction"] for row in run_rows])),
        "max_outside_training_state_fraction": float(max(row["outside_training_state_fraction"] for row in run_rows)),
        "total_clipped_state_entries": int(sum(row["clipped_state_entries"] for row in run_rows)),
        "total_clipped_stream_entries": int(sum(row["clipped_stream_entries"] for row in run_rows)),
    }
    payload = {
        "schema": "psa-qae-cce-primary-css-initializer-repeated-cycle-screen/v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "nested_holdout_parameter_only_css_initializer_repeated_aggregate_cycle_screen_tank_and_reversible_css_open",
        "source": LEDGER.name,
        "cycles_per_run": N_CYCLES,
        "tail_cycles": TAIL_CYCLES,
        "aggregate_css_l1_gate": CSS_L1_GATE,
        "held_run_dynamic_states_supplied": 0,
        "css_alpha_history": css_alphas,
        "phase_alpha_histories": dict(phase_alphas),
        "equalization_alpha_histories": dict(eq_alphas),
        "summary": summary,
        "run_rows": run_rows,
        "cycle_rows": cycle_rows,
        "qpu_submission": False,
        "claim_boundary": {
            "supported": "local repeated-cycle stability and event retention of a nested-held-out parameter-only aggregate CSS initializer and phase-map composition",
            "unsupported": "tank-state or spatial-profile propagation, global physical CSS convergence, reversible CSS logic, external validation, hardware execution, or quantum advantage",
        },
    }
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with OUT_CSV.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(run_rows[0]))
        writer.writeheader()
        writer.writerows(run_rows)

    lines = [
        "# Parameter-only CSS initializer repeated-cycle screen",
        "",
        f"For each outer held run, 11 frozen parameters generate both aggregate bed states and the held-out phase/equalization map is iterated for {N_CYCLES} cycles. No held dynamic state is supplied.",
        "",
        f"Terminal labels match **{summary['terminal_event_matches']}/{summary['held_out_runs']}** runs. The final {TAIL_CYCLES} labels are constant in **{summary['tail_event_constant_count']}/{summary['held_out_runs']}**, and the tail aggregate CSS gate `{CSS_L1_GATE:.0e}` passes in **{summary['tail_css_gate_1e_4_count']}/{summary['held_out_runs']}**. Median/p95 terminal cycle residuals are **{summary['median_terminal_cycle_residual_relative_l1']:.3e}/{summary['p95_terminal_cycle_residual_relative_l1']:.3e}**.",
        "",
        f"Median/p95 terminal drift from the predicted initializer are **{summary['median_terminal_drift_from_initializer_relative_l1']:.3e}/{summary['p95_terminal_drift_from_initializer_relative_l1']:.3e}**. State/stream clipping counts are **{summary['total_clipped_state_entries']}/{summary['total_clipped_stream_entries']}**.",
        "",
        "This is a local stability test of fitted aggregate maps. The finite tank state and spatial profiles are absent, and no global physical or reversible CSS claim follows.",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    residual = np.asarray([row["terminal_cycle_residual_relative_l1"] for row in run_rows])
    drift = np.asarray([row["terminal_drift_from_predicted_css_initializer_relative_l1"] for row in run_rows])
    representative = sorted(run_rows, key=lambda row: row["terminal_cycle_residual_relative_l1"])[len(run_rows) // 2]["sample"]
    trace = [row for row in cycle_rows if row["sample"] == representative]
    fig, axes = plt.subplots(1, 2, figsize=(11.2, 4.5), constrained_layout=True)
    axes[0].scatter(drift, residual, c=np.where(actual_labels == terminal_labels, "#18794e", "#b44"))
    axes[0].axhline(CSS_L1_GATE, color="black", linestyle="--", linewidth=1)
    axes[0].set(xlabel="terminal drift from initializer", ylabel="terminal cycle residual", yscale="log", title="Parameter-only repeated-cycle endpoint")
    axes[1].plot([row["cycle"] for row in trace], [row["cycle_residual_relative_l1"] for row in trace], label=f"sample {representative}")
    axes[1].axhline(CSS_L1_GATE, color="black", linestyle="--", linewidth=1, label="aggregate gate")
    axes[1].set(xlabel="composed cycle", ylabel="cycle residual relative L1", yscale="log", title="Representative local stability")
    axes[1].legend(frameon=False)
    fig.savefig(OUT_PNG, dpi=250)
    fig.savefig(OUT_PDF)
    plt.close(fig)
    print(json.dumps({"status": payload["status"], "summary": summary, "qpu_submission": False}, indent=2))


if __name__ == "__main__":
    main()
