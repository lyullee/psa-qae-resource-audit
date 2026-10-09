"""Nested-held-out free-running one-cycle bridge for the primary PSA event.

Only the two aggregate bed states at the beginning of the held run's final
cycle are observed.  Eight phase maps and two equalization maps are then
composed in physical schedule order.  Predicted phase-end states feed the
next map, so no intermediate held phase-start state is supplied.  The two
predicted adsorption streams reconstruct purity, recovery, and the frozen
joint event.  This is a one-cycle aggregate-state validation; it is not a
repeated-CSS oracle, plant validation, or quantum execution.
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
    COMPONENTS,
    PARAMETERS,
    arrays_from_ledger,
    choose_alpha_nested,
    fit_ridge,
    relative_l1,
    state_vector,
)


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RESULTS = ROOT / "10_TEA_LCA_Python" / "results" / "pycharm_publication_enhancement"
LEDGER = RESULTS / "PSA_QAE_CCE_PRIMARY_PHASE_LEDGER.json"
OUT_JSON = RESULTS / "PSA_QAE_CCE_PRIMARY_PHASE_EVENT_FREE_RUNNING.json"
OUT_CSV = RESULTS / "PSA_QAE_CCE_PRIMARY_PHASE_EVENT_FREE_RUNNING.csv"
OUT_MD = RESULTS / "PSA_QAE_CCE_PRIMARY_PHASE_EVENT_FREE_RUNNING.md"
OUT_PNG = RESULTS / "PSA_QAE_CCE_PRIMARY_PHASE_EVENT_FREE_RUNNING_FIGURE.png"
OUT_PDF = RESULTS / "PSA_QAE_CCE_PRIMARY_PHASE_EVENT_FREE_RUNNING_FIGURE.pdf"

PHASE_SCHEDULE = [
    (("A", "adsorption"), ("B", "pressurization")),
    (("A", "blowdown"), ("B", "adsorption")),
    (("A", "purge"), ("B", "blowdown")),
    (("A", "pressurization"), ("B", "purge")),
]


def equalization_arrays(ledger: dict) -> dict[int, dict[str, np.ndarray]]:
    groups = {
        index: {"samples": [], "x": [], "y": []}
        for index in range(2)
    }
    for run in ledger["runs"]:
        params = np.asarray([run["parameters"][key] for key in PARAMETERS], dtype=float)
        for index, record in enumerate(run["equalization_records"]):
            a0 = state_vector(record["state_a_start"])
            b0 = state_vector(record["state_b_start"])
            a1 = state_vector(record["state_a_end"])
            b1 = state_vector(record["state_b_end"])
            groups[index]["samples"].append(int(run["sample"]))
            groups[index]["x"].append(np.r_[a0, b0, params])
            groups[index]["y"].append(np.r_[a1 - a0, b1 - b0])
    return {
        index: {
            name: np.asarray(values, dtype=int if name == "samples" else float)
            for name, values in group.items()
        }
        for index, group in groups.items()
    }


def actual_phase_map(run: dict) -> dict[tuple[str, str], dict]:
    return {(record["bed"], record["step"]): record for record in run["phase_records"]}


def joint_state_error(pred_a: np.ndarray, pred_b: np.ndarray, actual_a: np.ndarray, actual_b: np.ndarray) -> float:
    return relative_l1(np.r_[pred_a, pred_b], np.r_[actual_a, actual_b])


def main() -> None:
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    phase_arrays = arrays_from_ledger(ledger)
    eq_arrays = equalization_arrays(ledger)
    event_rows: list[dict] = []
    trajectory_rows: list[dict] = []
    phase_alphas: dict[str, list[float]] = defaultdict(list)
    equalization_alphas: dict[str, list[float]] = defaultdict(list)

    for held_run in ledger["runs"]:
        sample = int(held_run["sample"])
        params = np.asarray([held_run["parameters"][key] for key in PARAMETERS], dtype=float)
        actual_phases = actual_phase_map(held_run)

        phase_models = {}
        for key, data in phase_arrays.items():
            train = data["samples"] != sample
            alpha = choose_alpha_nested(data["x"][train], data["y"][train])
            phase_models[key] = fit_ridge(data["x"][train], data["y"][train], alpha)
            phase_alphas[f"{key[0]}_{key[1]}"].append(alpha)

        eq_models = {}
        for index, data in eq_arrays.items():
            train = data["samples"] != sample
            alpha = choose_alpha_nested(data["x"][train], data["y"][train])
            eq_models[index] = fit_ridge(data["x"][train], data["y"][train], alpha)
            equalization_alphas[f"equalization_{index + 1}"].append(alpha)

        # The only held-run dynamic observations supplied to the chain.
        state_a0 = state_vector(actual_phases[("A", "adsorption")]["state_start"])
        state_b0 = state_vector(actual_phases[("B", "pressurization")]["state_start"])
        state_a = state_a0.copy()
        state_b = state_b0.copy()
        adsorption_streams: list[tuple[np.ndarray, np.ndarray]] = []
        clipped_state_entries = 0
        clipped_stream_entries = 0

        for stage, pair in enumerate(PHASE_SCHEDULE):
            predicted_ends = {}
            for key in pair:
                bed_state = state_a if key[0] == "A" else state_b
                pred = phase_models[key].predict(np.r_[bed_state, params])[0]
                next_state_raw = bed_state + pred[:10]
                clipped_state_entries += int(np.sum(next_state_raw < 0.0))
                next_state = np.maximum(next_state_raw, 0.0)
                inlet_raw = pred[10:15]
                outlet_raw = pred[15:20]
                clipped_stream_entries += int(np.sum(inlet_raw < 0.0) + np.sum(outlet_raw < 0.0))
                inlet = np.maximum(inlet_raw, 0.0)
                outlet = np.maximum(outlet_raw, 0.0)
                predicted_ends[key[0]] = next_state
                if key[1] == "adsorption":
                    adsorption_streams.append((inlet, outlet))

            state_a = predicted_ends["A"]
            state_b = predicted_ends["B"]
            actual_a = state_vector(actual_phases[pair[0]]["state_end"])
            actual_b = state_vector(actual_phases[pair[1]]["state_end"])
            trajectory_rows.append(
                {
                    "sample": sample,
                    "stage": f"phase_pair_{stage + 1}",
                    "joint_state_relative_l1": joint_state_error(state_a, state_b, actual_a, actual_b),
                }
            )

            if stage < 2:
                pred_eq = eq_models[stage].predict(np.r_[state_a, state_b, params])[0]
                a_raw = state_a + pred_eq[:10]
                b_raw = state_b + pred_eq[10:20]
                clipped_state_entries += int(np.sum(a_raw < 0.0) + np.sum(b_raw < 0.0))
                state_a = np.maximum(a_raw, 0.0)
                state_b = np.maximum(b_raw, 0.0)
                actual_eq = held_run["equalization_records"][stage]
                actual_a = state_vector(actual_eq["state_a_end"])
                actual_b = state_vector(actual_eq["state_b_end"])
                trajectory_rows.append(
                    {
                        "sample": sample,
                        "stage": f"equalization_{stage + 1}",
                        "joint_state_relative_l1": joint_state_error(state_a, state_b, actual_a, actual_b),
                    }
                )

        pred_feed = np.sum([item[0] for item in adsorption_streams], axis=0)
        pred_gross_product = np.sum([item[1] for item in adsorption_streams], axis=0)
        recycle = float(held_run["parameters"]["recycle_fraction"])
        pred_external = (1.0 - recycle) * pred_gross_product
        pred_purity = float(pred_external[0] / max(float(pred_external.sum()), 1.0e-14))
        pred_recovery = float(pred_external[0] / max(float(pred_feed[0]), 1.0e-14))
        actual = held_run["event_observables"]
        actual_purity = float(actual["h2_product"])
        actual_recovery = float(actual["h2_recovery_external_proxy"])
        pred_event = bool(pred_purity >= float(actual["purity_threshold"]) and pred_recovery >= float(actual["recovery_threshold"]))
        actual_event = bool(actual["joint_event"])
        final_closure = joint_state_error(state_a, state_b, state_a0, state_b0)
        event_rows.append(
            {
                "sample": sample,
                "recycle_fraction": recycle,
                "actual_purity": actual_purity,
                "predicted_purity": pred_purity,
                "purity_abs_error": abs(pred_purity - actual_purity),
                "actual_recovery": actual_recovery,
                "predicted_recovery": pred_recovery,
                "recovery_abs_error": abs(pred_recovery - actual_recovery),
                "actual_event": actual_event,
                "predicted_event": pred_event,
                "event_match": pred_event == actual_event,
                "final_cycle_closure_relative_l1": final_closure,
                "clipped_state_entries": clipped_state_entries,
                "clipped_stream_entries": clipped_stream_entries,
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
        "median_final_cycle_closure_relative_l1": float(np.median([row["final_cycle_closure_relative_l1"] for row in event_rows])),
        "p95_final_cycle_closure_relative_l1": float(np.quantile([row["final_cycle_closure_relative_l1"] for row in event_rows], 0.95)),
        "total_clipped_state_entries": int(sum(row["clipped_state_entries"] for row in event_rows)),
        "total_clipped_stream_entries": int(sum(row["clipped_stream_entries"] for row in event_rows)),
    }

    stage_summary = []
    for stage in ["phase_pair_1", "equalization_1", "phase_pair_2", "equalization_2", "phase_pair_3", "phase_pair_4"]:
        values = [row["joint_state_relative_l1"] for row in trajectory_rows if row["stage"] == stage]
        stage_summary.append(
            {
                "stage": stage,
                "median_joint_state_relative_l1": float(np.median(values)),
                "p95_joint_state_relative_l1": float(np.quantile(values, 0.95)),
                "max_joint_state_relative_l1": float(np.max(values)),
            }
        )

    payload = {
        "schema": "psa-qae-cce-primary-phase-event-free-running/v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "nested_holdout_primary_one_cycle_free_running_aggregate_state_bridge_repeated_css_open",
        "source": LEDGER.name,
        "sample_count": len(event_rows),
        "held_run_dynamic_inputs": "only aggregate A/B bed states at the beginning of the final cycle plus frozen parameters",
        "composition": "eight phase maps and two learned equalization maps in physical schedule order; predicted states feed subsequent maps",
        "validation": "outer leave-one-run-out with ridge alpha chosen by inner leave-one-out on the other runs",
        "phase_alpha_histories": dict(phase_alphas),
        "equalization_alpha_histories": dict(equalization_alphas),
        "event_summary": summary,
        "stage_summary": stage_summary,
        "event_rows": event_rows,
        "trajectory_rows": trajectory_rows,
        "qpu_submission": False,
        "claim_boundary": {
            "supported": "nested-held-out one-cycle aggregate-state composition from one observed cycle-start state to the frozen primary event",
            "unsupported": "profile-resolved dynamics, tank-state propagation, repeated free-running CSS, reversible event arithmetic, independent physical validation, hardware execution, or quantum advantage",
        },
    }
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with OUT_CSV.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(event_rows[0]))
        writer.writeheader()
        writer.writerows(event_rows)

    lines = [
        "# Primary one-cycle free-running phase-stream event bridge",
        "",
        "The held run supplies only the aggregate A/B bed states at the beginning of its final cycle and the frozen parameters. Eight phase maps and two equalization maps, fitted without that run, are composed in schedule order; every predicted phase/equalization state becomes the next map input.",
        "",
        f"The frozen event matches in **{summary['event_matches']}/{summary['held_out_runs']}** runs (false positives={summary['false_positive_count']}, false negatives={summary['false_negative_count']}). Purity/recovery MAE are **{summary['purity_mae']:.3e}/{summary['recovery_mae']:.3e}**. Median/p95 final-cycle closure L1 are **{summary['median_final_cycle_closure_relative_l1']:.3e}/{summary['p95_final_cycle_closure_relative_l1']:.3e}**.",
        "",
        "| composed stage | median joint-state L1 | p95 joint-state L1 | max joint-state L1 |",
        "|---|---:|---:|---:|",
    ]
    for row in stage_summary:
        lines.append(
            f"| {row['stage']} | {row['median_joint_state_relative_l1']:.5e} | {row['p95_joint_state_relative_l1']:.5e} | {row['max_joint_state_relative_l1']:.5e} |"
        )
    lines += [
        "",
        f"Nonnegative clipping affected {summary['total_clipped_state_entries']} state entries and {summary['total_clipped_stream_entries']} stream entries over all held runs.",
        "",
        "This removes the earlier use of actual intermediate held phase-start states. It remains a one-cycle aggregate-state bridge anchored at the actual final-cycle start; tank-state propagation, profile-resolved dynamics, repeated CSS, reversible event arithmetic, and external validation remain open.",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    actual_recovery = np.asarray([row["actual_recovery"] for row in event_rows])
    predicted_recovery = np.asarray([row["predicted_recovery"] for row in event_rows])
    stage_names = [row["stage"] for row in stage_summary]
    stage_median = [row["median_joint_state_relative_l1"] for row in stage_summary]
    stage_p95 = [row["p95_joint_state_relative_l1"] for row in stage_summary]
    fig, axes = plt.subplots(1, 2, figsize=(11.3, 4.6), constrained_layout=True)
    axes[0].scatter(actual_recovery, predicted_recovery, c=np.where(actual_labels == predicted_labels, "#18794e", "#b44"))
    lo = min(actual_recovery.min(), predicted_recovery.min())
    hi = max(actual_recovery.max(), predicted_recovery.max())
    axes[0].plot([lo, hi], [lo, hi], "k--", linewidth=1)
    axes[0].axhline(0.789, color="#666", linestyle=":")
    axes[0].axvline(0.789, color="#666", linestyle=":")
    axes[0].set(xlabel="actual recovery", ylabel="free-running predicted recovery", title="Held-out one-cycle event bridge")
    x = np.arange(len(stage_names))
    axes[1].plot(x, stage_median, "o-", label="median")
    axes[1].plot(x, stage_p95, "s--", label="p95")
    axes[1].set_xticks(x, [name.replace("_", "\n") for name in stage_names])
    axes[1].set(ylabel="joint-state relative L1", title="Composed-state error growth")
    axes[1].legend(frameon=False)
    fig.savefig(OUT_PNG, dpi=250)
    fig.savefig(OUT_PDF)
    plt.close(fig)
    print(json.dumps({"status": payload["status"], "event_summary": summary, "qpu_submission": False}, indent=2))


if __name__ == "__main__":
    main()
