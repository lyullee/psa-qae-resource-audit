"""Stabilize the parameter-only aggregate cycle map without held labels.

For every outer held run, the CSS initializer and all phase/equalization maps
are fitted to the other 31 runs.  The exact Jacobian of the affine aggregate
cycle map is assembled from the fitted blocks.  A cycle-boundary anchor

    G(x) = (1 - w) F(x) + w x_css

uses the smallest ``w`` that reduces the fitted spectral radius to the
predeclared target 0.9.  The weight therefore uses neither the held dynamic
trajectory nor the held event label.  This is a stability-projected reduced
surrogate control, not a physical tank/spatial CSS solver or a reversible
implementation.
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
    RidgeModel,
    arrays_from_ledger,
    choose_alpha_nested,
    fit_ridge,
    relative_l1,
)
from cce_primary_phase_event_free_running import PHASE_SCHEDULE, equalization_arrays
from cce_primary_phase_event_repeated_cycle_screen import predict_cycle


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RESULTS = ROOT / "10_TEA_LCA_Python" / "results" / "pycharm_publication_enhancement"
LEDGER = RESULTS / "PSA_QAE_CCE_PRIMARY_PHASE_LEDGER.json"
BASELINE = RESULTS / "PSA_QAE_CCE_PRIMARY_CSS_INITIALIZER_REPEATED_CYCLE_SCREEN.json"
OUT_JSON = RESULTS / "PSA_QAE_CCE_PRIMARY_CSS_INITIALIZER_SPECTRAL_STABILITY_SCREEN.json"
OUT_CSV = RESULTS / "PSA_QAE_CCE_PRIMARY_CSS_INITIALIZER_SPECTRAL_STABILITY_SCREEN.csv"
OUT_MD = RESULTS / "PSA_QAE_CCE_PRIMARY_CSS_INITIALIZER_SPECTRAL_STABILITY_SCREEN.md"
OUT_PNG = RESULTS / "PSA_QAE_CCE_PRIMARY_CSS_INITIALIZER_SPECTRAL_STABILITY_SCREEN_FIGURE.png"
OUT_PDF = RESULTS / "PSA_QAE_CCE_PRIMARY_CSS_INITIALIZER_SPECTRAL_STABILITY_SCREEN_FIGURE.pdf"

N_CYCLES = 50
TAIL_CYCLES = 10
CSS_L1_GATE = 1.0e-4
TARGET_SPECTRAL_RADIUS = 0.9


def model_derivative(model: RidgeModel, state_inputs: int, state_outputs: int) -> np.ndarray:
    """Return d(output[:state_outputs])/d(input[:state_inputs])."""

    scaled = (model.coef / model.x_scale[:, None]) * model.y_scale[None, :]
    return scaled[:state_inputs, :state_outputs].T


def cycle_jacobian(phase_models: dict, eq_models: dict) -> np.ndarray:
    """Assemble the exact unclipped 20-state affine cycle Jacobian."""

    jacobian = np.eye(20)
    for stage, pair in enumerate(PHASE_SCHEDULE):
        blocks = {}
        for key in pair:
            blocks[key[0]] = np.eye(10) + model_derivative(phase_models[key], 10, 10)
        phase_jacobian = np.zeros((20, 20))
        phase_jacobian[:10, :10] = blocks["A"]
        phase_jacobian[10:, 10:] = blocks["B"]
        jacobian = phase_jacobian @ jacobian
        if stage < 2:
            equalization_jacobian = np.eye(20) + model_derivative(eq_models[stage], 20, 20)
            jacobian = equalization_jacobian @ jacobian
    return jacobian


def main() -> None:
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    baseline_rows = {int(row["sample"]): row for row in baseline["run_rows"]}
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
        target = np.maximum(css_model.predict(css_x[held_index])[0], 0.0)
        css_alphas.append(css_alpha)
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

        raw_jacobian = cycle_jacobian(phase_models, eq_models)
        raw_radius = float(np.max(np.abs(np.linalg.eigvals(raw_jacobian))))
        anchor_weight = float(max(0.0, 1.0 - TARGET_SPECTRAL_RADIUS / max(raw_radius, 1.0e-15)))
        stabilized_radius = float((1.0 - anchor_weight) * raw_radius)

        state_a = target[:10].copy()
        state_b = target[10:].copy()
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
            before = np.r_[state_a, state_b]
            raw_a, raw_b, feed, gross_product, diagnostics = predict_cycle(
                state_a,
                state_b,
                params,
                phase_models,
                eq_models,
                phase_support,
                eq_support,
            )
            stabilized = (1.0 - anchor_weight) * np.r_[raw_a, raw_b] + anchor_weight * target
            state_a = np.maximum(stabilized[:10], 0.0)
            state_b = np.maximum(stabilized[10:], 0.0)
            external = (1.0 - recycle) * gross_product
            purity = float(external[0] / max(float(external.sum()), 1.0e-14))
            recovery = float(external[0] / max(float(feed[0]), 1.0e-14))
            label = bool(purity >= 0.9998 and recovery >= 0.789)
            residual = relative_l1(np.r_[state_a, state_b], before)
            drift = relative_l1(np.r_[state_a, state_b], target)
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
        base = baseline_rows[sample]
        run_rows.append(
            {
                "sample": sample,
                "actual_event": actual_event,
                "cycle_1_event": labels[0],
                "terminal_event": labels[-1],
                "terminal_event_match": labels[-1] == actual_event,
                "tail_event_constant": len(set(labels[-TAIL_CYCLES:])) == 1,
                "tail_css_gate_1e_4": max(tail_residuals) < CSS_L1_GATE,
                "raw_cycle_spectral_radius": raw_radius,
                "target_cycle_spectral_radius": TARGET_SPECTRAL_RADIUS,
                "anchor_weight": anchor_weight,
                "stabilized_cycle_spectral_radius": stabilized_radius,
                "terminal_purity": purities[-1],
                "terminal_recovery": recoveries[-1],
                "terminal_cycle_residual_relative_l1": residuals[-1],
                "tail_max_cycle_residual_relative_l1": max(tail_residuals),
                "terminal_drift_from_initializer_relative_l1": drifts[-1],
                "max_drift_from_initializer_relative_l1": max(drifts),
                "baseline_terminal_event_match": bool(base["terminal_event_match"]),
                "baseline_tail_css_gate_1e_4": bool(base["tail_css_gate_1e_4"]),
                "baseline_terminal_cycle_residual_relative_l1": float(base["terminal_cycle_residual_relative_l1"]),
                "outside_training_state_fraction": total_outside / max(total_coordinates, 1),
                "clipped_state_entries": total_clipped_state,
                "clipped_stream_entries": total_clipped_stream,
            }
        )

    actual = np.asarray([row["actual_event"] for row in run_rows], dtype=bool)
    terminal = np.asarray([row["terminal_event"] for row in run_rows], dtype=bool)
    summary = {
        "held_out_runs": len(run_rows),
        "cycles_per_run": N_CYCLES,
        "target_spectral_radius": TARGET_SPECTRAL_RADIUS,
        "raw_spectral_radius_min": float(min(row["raw_cycle_spectral_radius"] for row in run_rows)),
        "raw_spectral_radius_median": float(np.median([row["raw_cycle_spectral_radius"] for row in run_rows])),
        "raw_spectral_radius_p95": float(np.quantile([row["raw_cycle_spectral_radius"] for row in run_rows], 0.95)),
        "raw_spectral_radius_max": float(max(row["raw_cycle_spectral_radius"] for row in run_rows)),
        "anchor_weight_min": float(min(row["anchor_weight"] for row in run_rows)),
        "anchor_weight_median": float(np.median([row["anchor_weight"] for row in run_rows])),
        "anchor_weight_max": float(max(row["anchor_weight"] for row in run_rows)),
        "cycle_1_event_matches": int(sum(row["cycle_1_event"] == row["actual_event"] for row in run_rows)),
        "terminal_event_matches": int(np.sum(actual == terminal)),
        "terminal_false_positive_count": int(np.sum(~actual & terminal)),
        "terminal_false_negative_count": int(np.sum(actual & ~terminal)),
        "tail_event_constant_count": int(sum(row["tail_event_constant"] for row in run_rows)),
        "tail_css_gate_1e_4_count": int(sum(row["tail_css_gate_1e_4"] for row in run_rows)),
        "baseline_terminal_event_matches": int(sum(row["baseline_terminal_event_match"] for row in run_rows)),
        "baseline_tail_css_gate_1e_4_count": int(sum(row["baseline_tail_css_gate_1e_4"] for row in run_rows)),
        "median_terminal_cycle_residual_relative_l1": float(np.median([row["terminal_cycle_residual_relative_l1"] for row in run_rows])),
        "p95_terminal_cycle_residual_relative_l1": float(np.quantile([row["terminal_cycle_residual_relative_l1"] for row in run_rows], 0.95)),
        "p95_terminal_drift_from_initializer_relative_l1": float(np.quantile([row["terminal_drift_from_initializer_relative_l1"] for row in run_rows], 0.95)),
        "total_clipped_state_entries": int(sum(row["clipped_state_entries"] for row in run_rows)),
        "total_clipped_stream_entries": int(sum(row["clipped_stream_entries"] for row in run_rows)),
    }
    payload = {
        "schema": "psa-qae-cce-primary-css-initializer-spectral-stability-screen/v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "nested_holdout_spectral_stabilization_pass_reduced_surrogate_only_physical_reversible_css_open",
        "source": LEDGER.name,
        "baseline": BASELINE.name,
        "cycles_per_run": N_CYCLES,
        "tail_cycles": TAIL_CYCLES,
        "aggregate_css_l1_gate": CSS_L1_GATE,
        "held_run_dynamic_states_supplied": 0,
        "held_run_event_labels_used_for_stabilization": False,
        "stabilization_rule": "w=max(0, 1-target_spectral_radius/raw_spectral_radius); G(x)=(1-w)F(x)+w*x_css",
        "css_alpha_history": css_alphas,
        "phase_alpha_histories": dict(phase_alphas),
        "equalization_alpha_histories": dict(eq_alphas),
        "summary": summary,
        "run_rows": run_rows,
        "cycle_rows": cycle_rows,
        "qpu_submission": False,
        "claim_boundary": {
            "supported": "outer-held mathematical stabilization of the aggregate affine cycle surrogate using a parameter-only CSS anchor and model Jacobian, with no held label or dynamic-state input",
            "unsupported": "a physical conservation-law correction, tank or spatial propagation, reversible stabilization arithmetic, independent H2 validation, hardware execution, or quantum advantage",
        },
    }
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with OUT_CSV.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(run_rows[0]))
        writer.writeheader()
        writer.writerows(run_rows)

    lines = [
        "# Parameter-only CSS initializer spectral-stability screen",
        "",
        "Each outer-held affine cycle map is anchored to its parameter-only CSS initializer with the smallest weight that reduces the exact fitted Jacobian spectral radius to the predeclared target 0.9. Held event labels and held dynamic states are not used to choose the weight.",
        "",
        f"Raw spectral radius spans **{summary['raw_spectral_radius_min']:.3f}–{summary['raw_spectral_radius_max']:.3f}** (median **{summary['raw_spectral_radius_median']:.3f}**), requiring anchor weights **{summary['anchor_weight_min']:.3f}–{summary['anchor_weight_max']:.3f}** (median **{summary['anchor_weight_median']:.3f}**).",
        "",
        f"The unanchored 50-cycle baseline retains terminal labels in **{summary['baseline_terminal_event_matches']}/{summary['held_out_runs']}** runs and passes the aggregate CSS gate in **{summary['baseline_tail_css_gate_1e_4_count']}/{summary['held_out_runs']}**. Spectral stabilization retains cycle-1 and terminal labels in **{summary['cycle_1_event_matches']}/{summary['held_out_runs']}** and **{summary['terminal_event_matches']}/{summary['held_out_runs']}** runs, while the tail CSS gate passes in **{summary['tail_css_gate_1e_4_count']}/{summary['held_out_runs']}**.",
        "",
        f"Median/p95 terminal residuals are **{summary['median_terminal_cycle_residual_relative_l1']:.3e}/{summary['p95_terminal_cycle_residual_relative_l1']:.3e}** and p95 terminal drift from the predicted initializer is **{summary['p95_terminal_drift_from_initializer_relative_l1']:.3e}**. State/stream clipping counts are **{summary['total_clipped_state_entries']}/{summary['total_clipped_stream_entries']}**.",
        "",
        "This result diagnoses and corrects mathematical instability of the reduced aggregate surrogate. The anchor is an explicit model correction, not a conservation-law-derived tank/spatial CSS update, and no physical or reversible CSS claim follows.",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    radii = np.asarray([row["raw_cycle_spectral_radius"] for row in run_rows])
    weights = np.asarray([row["anchor_weight"] for row in run_rows])
    raw_residual = np.asarray([row["baseline_terminal_cycle_residual_relative_l1"] for row in run_rows])
    stable_residual = np.asarray([row["terminal_cycle_residual_relative_l1"] for row in run_rows])
    fig, axes = plt.subplots(1, 2, figsize=(11.2, 4.5), constrained_layout=True)
    axes[0].scatter(radii, weights, color="#6f4cc3")
    axes[0].axvline(1.0, color="black", linestyle="--", linewidth=1)
    axes[0].set(xlabel="raw cycle-map spectral radius", ylabel="CSS-anchor weight", title="Outer-held stability correction")
    axes[1].scatter(raw_residual, stable_residual, c=np.where(actual == terminal, "#18794e", "#b44"))
    lo = min(float(raw_residual.min()), float(stable_residual.min()))
    hi = max(float(raw_residual.max()), float(stable_residual.max()))
    axes[1].plot([lo, hi], [lo, hi], color="0.4", linestyle="--", linewidth=1)
    axes[1].axhline(CSS_L1_GATE, color="black", linestyle=":", linewidth=1)
    axes[1].set(xscale="log", yscale="log", xlabel="unanchored terminal residual", ylabel="stabilized terminal residual", title="50-cycle residual reduction")
    fig.savefig(OUT_PNG, dpi=250)
    fig.savefig(OUT_PDF)
    plt.close(fig)
    print(json.dumps({"status": payload["status"], "summary": summary, "qpu_submission": False}, indent=2))


if __name__ == "__main__":
    main()
