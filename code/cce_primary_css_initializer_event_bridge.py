"""Nested-held-out parameter-to-CSS initializer and one-cycle event bridge.

The held run contributes only its frozen uncertainty/decision parameters.
An aggregate A/B cycle-start state is predicted from those parameters using
the other 31 runs, then independently held-out phase and equalization maps are
composed for one cycle.  No held dynamic state is supplied.  This evaluates a
surrogate CSS-initializer route, not iterative physical CSS convergence.
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from cce_primary_phase_event_bridge import (
    PARAMETERS,
    arrays_from_ledger,
    choose_alpha_nested,
    fit_ridge,
    relative_l1,
    state_vector,
)
from cce_primary_phase_event_free_running import actual_phase_map, equalization_arrays
from cce_primary_phase_event_repeated_cycle_screen import predict_cycle


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RESULTS = ROOT / "10_TEA_LCA_Python" / "results" / "pycharm_publication_enhancement"
LEDGER = RESULTS / "PSA_QAE_CCE_PRIMARY_PHASE_LEDGER.json"
OUT_JSON = RESULTS / "PSA_QAE_CCE_PRIMARY_CSS_INITIALIZER_EVENT_BRIDGE.json"
OUT_CSV = RESULTS / "PSA_QAE_CCE_PRIMARY_CSS_INITIALIZER_EVENT_BRIDGE.csv"
OUT_MD = RESULTS / "PSA_QAE_CCE_PRIMARY_CSS_INITIALIZER_EVENT_BRIDGE.md"
OUT_PNG = RESULTS / "PSA_QAE_CCE_PRIMARY_CSS_INITIALIZER_EVENT_BRIDGE_FIGURE.png"
OUT_PDF = RESULTS / "PSA_QAE_CCE_PRIMARY_CSS_INITIALIZER_EVENT_BRIDGE_FIGURE.pdf"


def css_arrays(ledger: dict) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    samples = []
    x = []
    y = []
    for run in ledger["runs"]:
        phases = actual_phase_map(run)
        samples.append(int(run["sample"]))
        x.append([run["parameters"][key] for key in PARAMETERS])
        y.append(
            np.r_[
                state_vector(phases[("A", "adsorption")]["state_start"]),
                state_vector(phases[("B", "pressurization")]["state_start"]),
            ]
        )
    return np.asarray(samples, dtype=int), np.asarray(x, dtype=float), np.asarray(y, dtype=float)


def main() -> None:
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    samples, css_x, css_y = css_arrays(ledger)
    phase_arrays = arrays_from_ledger(ledger)
    eq_arrays = equalization_arrays(ledger)
    event_rows = []
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
        actual_css = css_y[held_index]
        state_a0 = np.maximum(predicted_css[:10], 0.0)
        state_b0 = np.maximum(predicted_css[10:20], 0.0)
        initial_clipped = int(np.sum(predicted_css < 0.0))
        params = css_x[held_index]

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

        state_a1, state_b1, feed, gross_product, diagnostics = predict_cycle(
            state_a0,
            state_b0,
            params,
            phase_models,
            eq_models,
            phase_support,
            eq_support,
        )
        recycle = float(held_run["parameters"]["recycle_fraction"])
        external = (1.0 - recycle) * gross_product
        purity = float(external[0] / max(float(external.sum()), 1.0e-14))
        recovery = float(external[0] / max(float(feed[0]), 1.0e-14))
        predicted_event = bool(purity >= 0.9998 and recovery >= 0.789)
        actual = held_run["event_observables"]
        actual_event = bool(actual["joint_event"])
        event_rows.append(
            {
                "sample": sample,
                "actual_purity": float(actual["h2_product"]),
                "predicted_purity": purity,
                "purity_abs_error": abs(purity - float(actual["h2_product"])),
                "actual_recovery": float(actual["h2_recovery_external_proxy"]),
                "predicted_recovery": recovery,
                "recovery_abs_error": abs(recovery - float(actual["h2_recovery_external_proxy"])),
                "actual_event": actual_event,
                "predicted_event": predicted_event,
                "event_match": predicted_event == actual_event,
                "css_initializer_relative_l1": relative_l1(predicted_css, actual_css),
                "predicted_cycle_closure_relative_l1": relative_l1(np.r_[state_a1, state_b1], np.r_[state_a0, state_b0]),
                "final_state_vs_actual_css_relative_l1": relative_l1(np.r_[state_a1, state_b1], actual_css),
                "initial_clipped_state_entries": initial_clipped,
                "cycle_clipped_state_entries": diagnostics["clipped_state_entries"],
                "cycle_clipped_stream_entries": diagnostics["clipped_stream_entries"],
                "outside_training_state_fraction": diagnostics["outside_training_state_coordinates"] / max(diagnostics["evaluated_state_coordinates"], 1),
            }
        )

    actual_labels = np.asarray([row["actual_event"] for row in event_rows], dtype=bool)
    predicted_labels = np.asarray([row["predicted_event"] for row in event_rows], dtype=bool)
    summary = {
        "held_out_runs": len(event_rows),
        "event_matches": int(np.sum(actual_labels == predicted_labels)),
        "event_match_fraction": float(np.mean(actual_labels == predicted_labels)),
        "false_positive_count": int(np.sum(~actual_labels & predicted_labels)),
        "false_negative_count": int(np.sum(actual_labels & ~predicted_labels)),
        "purity_mae": float(np.mean([row["purity_abs_error"] for row in event_rows])),
        "purity_p95_abs_error": float(np.quantile([row["purity_abs_error"] for row in event_rows], 0.95)),
        "recovery_mae": float(np.mean([row["recovery_abs_error"] for row in event_rows])),
        "recovery_p95_abs_error": float(np.quantile([row["recovery_abs_error"] for row in event_rows], 0.95)),
        "median_css_initializer_relative_l1": float(np.median([row["css_initializer_relative_l1"] for row in event_rows])),
        "p95_css_initializer_relative_l1": float(np.quantile([row["css_initializer_relative_l1"] for row in event_rows], 0.95)),
        "median_predicted_cycle_closure_relative_l1": float(np.median([row["predicted_cycle_closure_relative_l1"] for row in event_rows])),
        "p95_predicted_cycle_closure_relative_l1": float(np.quantile([row["predicted_cycle_closure_relative_l1"] for row in event_rows], 0.95)),
        "median_final_state_vs_actual_css_relative_l1": float(np.median([row["final_state_vs_actual_css_relative_l1"] for row in event_rows])),
        "p95_final_state_vs_actual_css_relative_l1": float(np.quantile([row["final_state_vs_actual_css_relative_l1"] for row in event_rows], 0.95)),
        "total_initial_clipped_state_entries": int(sum(row["initial_clipped_state_entries"] for row in event_rows)),
        "total_cycle_clipped_state_entries": int(sum(row["cycle_clipped_state_entries"] for row in event_rows)),
        "total_cycle_clipped_stream_entries": int(sum(row["cycle_clipped_stream_entries"] for row in event_rows)),
        "median_outside_training_state_fraction": float(np.median([row["outside_training_state_fraction"] for row in event_rows])),
        "max_outside_training_state_fraction": float(max(row["outside_training_state_fraction"] for row in event_rows)),
    }
    full_css_alpha = choose_alpha_nested(css_x, css_y)
    full_css_model = fit_ridge(css_x, css_y, full_css_alpha).serialise(
        css_x.min(axis=0), css_x.max(axis=0)
    )
    payload = {
        "schema": "psa-qae-cce-primary-css-initializer-event-bridge/v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "nested_holdout_parameter_to_css_initializer_one_cycle_event_bridge_no_held_dynamic_state",
        "source": LEDGER.name,
        "held_run_inputs": PARAMETERS,
        "held_run_dynamic_states_supplied": 0,
        "css_initializer_output": "20 aggregate state coordinates: A/B gas and adsorbed component moles",
        "validation": "outer leave-one-run-out for CSS initializer, every phase map, and both equalization maps; inner leave-one-out ridge selection",
        "css_alpha_history": css_alphas,
        "full_fit_css_initializer": full_css_model,
        "phase_alpha_histories": dict(phase_alphas),
        "equalization_alpha_histories": dict(eq_alphas),
        "summary": summary,
        "event_rows": event_rows,
        "qpu_submission": False,
        "claim_boundary": {
            "supported": "surrogate-conditioned event reconstruction from held parameters with no held dynamic state supplied",
            "unsupported": "iterative physical CSS convergence, tank-state or profile-resolved propagation, reversible CSS/event logic, external validation, hardware execution, or quantum advantage",
        },
    }
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with OUT_CSV.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(event_rows[0]))
        writer.writeheader()
        writer.writerows(event_rows)

    lines = [
        "# Primary parameter-to-CSS initializer event bridge",
        "",
        "The held run supplies only its 11 frozen uncertainty/decision parameters. A nested-held-out ridge map predicts the 20 aggregate cycle-start state coordinates, after which independently held-out phase and equalization maps generate one cycle and the event streams.",
        "",
        f"Event labels match **{summary['event_matches']}/{summary['held_out_runs']}** runs (false positives={summary['false_positive_count']}, false negatives={summary['false_negative_count']}). Purity/recovery MAE are **{summary['purity_mae']:.3e}/{summary['recovery_mae']:.3e}**.",
        "",
        f"CSS-initializer median/p95 state L1 are **{summary['median_css_initializer_relative_l1']:.3e}/{summary['p95_css_initializer_relative_l1']:.3e}**. Predicted-cycle closure median/p95 are **{summary['median_predicted_cycle_closure_relative_l1']:.3e}/{summary['p95_predicted_cycle_closure_relative_l1']:.3e}**. No-held-state initialization causes {summary['total_initial_clipped_state_entries']} initial-state clips, {summary['total_cycle_clipped_state_entries']} cycle-state clips, and {summary['total_cycle_clipped_stream_entries']} stream clips.",
        "",
        "This removes all held dynamic-state inputs, but the initializer is a fitted surrogate of already converged rows. It is not an iterative physical CSS solver, tank/profile propagation, or a reversible circuit.",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    actual_recovery = np.asarray([row["actual_recovery"] for row in event_rows])
    predicted_recovery = np.asarray([row["predicted_recovery"] for row in event_rows])
    init_error = np.asarray([row["css_initializer_relative_l1"] for row in event_rows])
    closure = np.asarray([row["predicted_cycle_closure_relative_l1"] for row in event_rows])
    fig, axes = plt.subplots(1, 2, figsize=(11.2, 4.5), constrained_layout=True)
    axes[0].scatter(actual_recovery, predicted_recovery, c=np.where(actual_labels == predicted_labels, "#18794e", "#b44"))
    lo = min(actual_recovery.min(), predicted_recovery.min())
    hi = max(actual_recovery.max(), predicted_recovery.max())
    axes[0].plot([lo, hi], [lo, hi], "k--", linewidth=1)
    axes[0].axhline(0.789, color="#666", linestyle=":")
    axes[0].axvline(0.789, color="#666", linestyle=":")
    axes[0].set(xlabel="actual recovery", ylabel="parameter-only predicted recovery", title="No held dynamic-state event bridge")
    axes[1].scatter(init_error, closure, c=np.where(actual_labels == predicted_labels, "#18794e", "#b44"))
    axes[1].set(xlabel="CSS initializer relative L1", ylabel="predicted-cycle closure relative L1", title="Initializer and one-cycle closure")
    fig.savefig(OUT_PNG, dpi=250)
    fig.savefig(OUT_PDF)
    plt.close(fig)
    print(json.dumps({"status": payload["status"], "summary": summary, "qpu_submission": False}, indent=2))


if __name__ == "__main__":
    main()
