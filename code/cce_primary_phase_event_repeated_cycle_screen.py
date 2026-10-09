"""Screen repeated composition of held-out primary aggregate phase maps.

For every outer held run, the phase and equalization maps are fitted to the
other 31 runs.  Starting from the held run's final-cycle aggregate A/B bed
states, the learned one-cycle map is applied 50 times without intermediate
held states.  This tests local fixed-point stability and event-label retention
of the aggregate surrogate.  Tank state, spatial profiles, reversible control,
and independent process validation remain outside the screen.
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
from cce_primary_phase_event_free_running import (
    PHASE_SCHEDULE,
    actual_phase_map,
    equalization_arrays,
)


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RESULTS = ROOT / "10_TEA_LCA_Python" / "results" / "pycharm_publication_enhancement"
LEDGER = RESULTS / "PSA_QAE_CCE_PRIMARY_PHASE_LEDGER.json"
OUT_JSON = RESULTS / "PSA_QAE_CCE_PRIMARY_PHASE_EVENT_REPEATED_CYCLE_SCREEN.json"
OUT_CSV = RESULTS / "PSA_QAE_CCE_PRIMARY_PHASE_EVENT_REPEATED_CYCLE_SCREEN.csv"
OUT_MD = RESULTS / "PSA_QAE_CCE_PRIMARY_PHASE_EVENT_REPEATED_CYCLE_SCREEN.md"
OUT_PNG = RESULTS / "PSA_QAE_CCE_PRIMARY_PHASE_EVENT_REPEATED_CYCLE_SCREEN_FIGURE.png"
OUT_PDF = RESULTS / "PSA_QAE_CCE_PRIMARY_PHASE_EVENT_REPEATED_CYCLE_SCREEN_FIGURE.pdf"

N_CYCLES = 50
CSS_L1_GATE = 1.0e-4
TAIL_CYCLES = 10


def predict_cycle(
    state_a: np.ndarray,
    state_b: np.ndarray,
    params: np.ndarray,
    phase_models: dict,
    eq_models: dict,
    phase_support: dict,
    eq_support: dict,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, dict]:
    adsorption_streams = []
    clipped_state = 0
    clipped_stream = 0
    outside_state = 0
    state_coordinates = 0
    for stage, pair in enumerate(PHASE_SCHEDULE):
        next_states = {}
        for key in pair:
            current = state_a if key[0] == "A" else state_b
            lo, hi = phase_support[key]
            outside_state += int(np.sum((current < lo) | (current > hi)))
            state_coordinates += len(current)
            pred = phase_models[key].predict(np.r_[current, params])[0]
            raw_state = current + pred[:10]
            clipped_state += int(np.sum(raw_state < 0.0))
            next_states[key[0]] = np.maximum(raw_state, 0.0)
            raw_in = pred[10:15]
            raw_out = pred[15:20]
            clipped_stream += int(np.sum(raw_in < 0.0) + np.sum(raw_out < 0.0))
            if key[1] == "adsorption":
                adsorption_streams.append((np.maximum(raw_in, 0.0), np.maximum(raw_out, 0.0)))
        state_a = next_states["A"]
        state_b = next_states["B"]
        if stage < 2:
            lo, hi = eq_support[stage]
            joined = np.r_[state_a, state_b]
            outside_state += int(np.sum((joined < lo) | (joined > hi)))
            state_coordinates += len(joined)
            pred = eq_models[stage].predict(np.r_[joined, params])[0]
            raw_a = state_a + pred[:10]
            raw_b = state_b + pred[10:20]
            clipped_state += int(np.sum(raw_a < 0.0) + np.sum(raw_b < 0.0))
            state_a = np.maximum(raw_a, 0.0)
            state_b = np.maximum(raw_b, 0.0)
    feed = np.sum([row[0] for row in adsorption_streams], axis=0)
    gross_product = np.sum([row[1] for row in adsorption_streams], axis=0)
    diagnostics = {
        "clipped_state_entries": clipped_state,
        "clipped_stream_entries": clipped_stream,
        "outside_training_state_coordinates": outside_state,
        "evaluated_state_coordinates": state_coordinates,
    }
    return state_a, state_b, feed, gross_product, diagnostics


def main() -> None:
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    phase_arrays = arrays_from_ledger(ledger)
    eq_arrays = equalization_arrays(ledger)
    run_rows = []
    cycle_rows = []
    phase_alphas: dict[str, list[float]] = defaultdict(list)
    eq_alphas: dict[str, list[float]] = defaultdict(list)

    for held_run in ledger["runs"]:
        sample = int(held_run["sample"])
        params = np.asarray([held_run["parameters"][key] for key in PARAMETERS], dtype=float)
        phases = actual_phase_map(held_run)
        state_a0 = state_vector(phases[("A", "adsorption")]["state_start"])
        state_b0 = state_vector(phases[("B", "pressurization")]["state_start"])

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
        total_clipped_state = 0
        total_clipped_stream = 0
        total_outside = 0
        total_coordinates = 0
        labels = []
        residuals = []
        drifts = []
        recoveries = []
        purities = []
        recycle = float(held_run["parameters"]["recycle_fraction"])
        actual_event = bool(held_run["event_observables"]["joint_event"])

        for cycle in range(1, N_CYCLES + 1):
            start_a = state_a.copy()
            start_b = state_b.copy()
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
            residual = relative_l1(np.r_[state_a, state_b], np.r_[start_a, start_b])
            drift = relative_l1(np.r_[state_a, state_b], np.r_[state_a0, state_b0])
            labels.append(label)
            residuals.append(residual)
            drifts.append(drift)
            recoveries.append(recovery)
            purities.append(purity)
            total_clipped_state += diagnostics["clipped_state_entries"]
            total_clipped_stream += diagnostics["clipped_stream_entries"]
            total_outside += diagnostics["outside_training_state_coordinates"]
            total_coordinates += diagnostics["evaluated_state_coordinates"]
            cycle_rows.append(
                {
                    "sample": sample,
                    "cycle": cycle,
                    "cycle_residual_relative_l1": residual,
                    "drift_from_observed_start_relative_l1": drift,
                    "predicted_purity": purity,
                    "predicted_recovery": recovery,
                    "predicted_event": label,
                }
            )

        tail_residual = residuals[-TAIL_CYCLES:]
        terminal_label = labels[-1]
        run_rows.append(
            {
                "sample": sample,
                "actual_event": actual_event,
                "cycle_1_event": labels[0],
                "terminal_event": terminal_label,
                "terminal_event_match": terminal_label == actual_event,
                "tail_event_constant": len(set(labels[-TAIL_CYCLES:])) == 1,
                "terminal_purity": purities[-1],
                "terminal_recovery": recoveries[-1],
                "terminal_cycle_residual_relative_l1": residuals[-1],
                "tail_max_cycle_residual_relative_l1": max(tail_residual),
                "tail_css_gate_1e_4": max(tail_residual) < CSS_L1_GATE,
                "terminal_drift_from_observed_start_relative_l1": drifts[-1],
                "max_drift_from_observed_start_relative_l1": max(drifts),
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
        "median_terminal_drift_from_observed_start_relative_l1": float(np.median([row["terminal_drift_from_observed_start_relative_l1"] for row in run_rows])),
        "p95_terminal_drift_from_observed_start_relative_l1": float(np.quantile([row["terminal_drift_from_observed_start_relative_l1"] for row in run_rows], 0.95)),
        "median_outside_training_state_fraction": float(np.median([row["outside_training_state_fraction"] for row in run_rows])),
        "max_outside_training_state_fraction": float(max(row["outside_training_state_fraction"] for row in run_rows)),
        "total_clipped_state_entries": int(sum(row["clipped_state_entries"] for row in run_rows)),
        "total_clipped_stream_entries": int(sum(row["clipped_stream_entries"] for row in run_rows)),
    }
    payload = {
        "schema": "psa-qae-cce-primary-phase-event-repeated-cycle-screen/v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "nested_holdout_primary_aggregate_map_repeated_cycle_stability_screen_tank_and_reversible_css_open",
        "source": LEDGER.name,
        "cycles_per_run": N_CYCLES,
        "tail_cycles": TAIL_CYCLES,
        "aggregate_css_l1_gate": CSS_L1_GATE,
        "initial_condition": "held final-cycle aggregate A/B bed start states; no held intermediate phase states",
        "phase_alpha_histories": dict(phase_alphas),
        "equalization_alpha_histories": dict(eq_alphas),
        "summary": summary,
        "run_rows": run_rows,
        "cycle_rows": cycle_rows,
        "qpu_submission": False,
        "claim_boundary": {
            "supported": "local repeated-cycle stability and event retention of nested-held-out aggregate bed-state maps initialized at an observed CSS-cycle start",
            "unsupported": "tank-state or spatial-profile propagation, globally valid CSS convergence, reversible CSS logic, external physical validation, hardware execution, or quantum advantage",
        },
    }
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with OUT_CSV.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(run_rows[0]))
        writer.writeheader()
        writer.writerows(run_rows)

    lines = [
        "# Primary repeated-cycle aggregate-map stability screen",
        "",
        f"Each outer-held aggregate phase/equalization map is applied for {N_CYCLES} cycles from the held run's observed final-cycle start. No held intermediate phase state is supplied.",
        "",
        f"Terminal event labels match **{summary['terminal_event_matches']}/{summary['held_out_runs']}** runs. The last {TAIL_CYCLES} labels are constant in **{summary['tail_event_constant_count']}/{summary['held_out_runs']}** runs, and the tail aggregate CSS L1 gate `{CSS_L1_GATE:.0e}` passes in **{summary['tail_css_gate_1e_4_count']}/{summary['held_out_runs']}** runs. Median/p95 terminal cycle residuals are **{summary['median_terminal_cycle_residual_relative_l1']:.3e}/{summary['p95_terminal_cycle_residual_relative_l1']:.3e}**.",
        "",
        f"Median/p95 terminal drift from the observed cycle start are **{summary['median_terminal_drift_from_observed_start_relative_l1']:.3e}/{summary['p95_terminal_drift_from_observed_start_relative_l1']:.3e}**. Median/max state-coordinate outside-range fractions are **{summary['median_outside_training_state_fraction']:.3e}/{summary['max_outside_training_state_fraction']:.3e}**. State/stream clipping counts are **{summary['total_clipped_state_entries']}/{summary['total_clipped_stream_entries']}**.",
        "",
        "This is a local aggregate-map stability screen initialized at an observed CSS-cycle start. It does not propagate the finite tank state or spatial profiles, establish global CSS convergence, compile reversible CSS control, or validate the process externally.",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    terminal_residual = np.asarray([row["terminal_cycle_residual_relative_l1"] for row in run_rows])
    terminal_drift = np.asarray([row["terminal_drift_from_observed_start_relative_l1"] for row in run_rows])
    representative = sorted(run_rows, key=lambda row: row["terminal_cycle_residual_relative_l1"])[len(run_rows) // 2]["sample"]
    trace = [row for row in cycle_rows if row["sample"] == representative]
    fig, axes = plt.subplots(1, 2, figsize=(11.2, 4.5), constrained_layout=True)
    axes[0].scatter(terminal_drift, terminal_residual, c=np.where(actual_labels == terminal_labels, "#18794e", "#b44"))
    axes[0].axhline(CSS_L1_GATE, color="black", linestyle="--", linewidth=1)
    axes[0].set(xlabel="terminal drift from observed start", ylabel="terminal cycle residual", yscale="log", title="Held-out repeated-cycle endpoint")
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
