"""Build a nested-holdout phase-to-event bridge for the frozen primary PSA model.

Each phase model receives the held run's aggregate bed state at the phase start
plus the frozen uncertainty/decision coordinates.  It predicts the aggregate
state increment and component inlet/outlet streams.  The two adsorption stream
predictions are then combined with the declared recycle split to reconstruct
product purity, external recovery, and the primary joint event.  Because held
phase-start states are supplied, this is a conditional observability bridge,
not a free-running cyclic oracle or plant validation.
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RESULTS = ROOT / "10_TEA_LCA_Python" / "results" / "pycharm_publication_enhancement"
LEDGER = RESULTS / "PSA_QAE_CCE_PRIMARY_PHASE_LEDGER.json"
OUT_JSON = RESULTS / "PSA_QAE_CCE_PRIMARY_PHASE_EVENT_BRIDGE.json"
OUT_CSV = RESULTS / "PSA_QAE_CCE_PRIMARY_PHASE_EVENT_BRIDGE.csv"
OUT_MD = RESULTS / "PSA_QAE_CCE_PRIMARY_PHASE_EVENT_BRIDGE.md"
OUT_PNG = RESULTS / "PSA_QAE_CCE_PRIMARY_PHASE_EVENT_BRIDGE_FIGURE.png"
OUT_PDF = RESULTS / "PSA_QAE_CCE_PRIMARY_PHASE_EVENT_BRIDGE_FIGURE.pdf"

ALPHAS = np.asarray([1.0e-5, 1.0e-4, 1.0e-3, 1.0e-2, 1.0e-1, 1.0, 10.0, 100.0])
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
COMPONENTS = ["H2", "CO2", "CH4", "CO", "N2"]


@dataclass
class RidgeModel:
    x_mean: np.ndarray
    x_scale: np.ndarray
    y_mean: np.ndarray
    y_scale: np.ndarray
    coef: np.ndarray
    alpha: float

    def predict(self, x: np.ndarray) -> np.ndarray:
        x = np.atleast_2d(np.asarray(x, dtype=float))
        return ((x - self.x_mean) / self.x_scale @ self.coef) * self.y_scale + self.y_mean

    def serialise(self, x_min: np.ndarray | None = None, x_max: np.ndarray | None = None) -> dict:
        payload = {
            "x_mean": self.x_mean.tolist(),
            "x_scale": self.x_scale.tolist(),
            "y_mean": self.y_mean.tolist(),
            "y_scale": self.y_scale.tolist(),
            "coef": self.coef.tolist(),
            "alpha": self.alpha,
        }
        if x_min is not None and x_max is not None:
            payload["x_min"] = np.asarray(x_min, dtype=float).tolist()
            payload["x_max"] = np.asarray(x_max, dtype=float).tolist()
        return payload


def fit_ridge(x: np.ndarray, y: np.ndarray, alpha: float) -> RidgeModel:
    x_mean = x.mean(axis=0)
    x_scale = x.std(axis=0)
    x_scale[x_scale < 1.0e-14] = 1.0
    y_mean = y.mean(axis=0)
    y_scale = y.std(axis=0)
    y_scale[y_scale < 1.0e-14] = 1.0
    xz = (x - x_mean) / x_scale
    yz = (y - y_mean) / y_scale
    coef = np.linalg.solve(xz.T @ xz + float(alpha) * np.eye(x.shape[1]), xz.T @ yz)
    return RidgeModel(x_mean, x_scale, y_mean, y_scale, coef, float(alpha))


def choose_alpha_nested(x: np.ndarray, y: np.ndarray) -> float:
    output_scale = y.std(axis=0)
    output_scale[output_scale < 1.0e-14] = 1.0
    scores = []
    for alpha in ALPHAS:
        errors = []
        for held in range(len(x)):
            mask = np.arange(len(x)) != held
            pred = fit_ridge(x[mask], y[mask], float(alpha)).predict(x[held])[0]
            errors.append((pred - y[held]) / output_scale)
        scores.append(float(np.mean(np.square(errors))))
    return float(ALPHAS[int(np.argmin(scores))])


def state_vector(summary: dict) -> np.ndarray:
    return np.r_[summary["gas_component_mol"], summary["adsorbed_component_mol"]]


def arrays_from_ledger(ledger: dict) -> dict[tuple[str, str], dict[str, np.ndarray]]:
    groups: dict[tuple[str, str], dict[str, list]] = defaultdict(
        lambda: {"samples": [], "x": [], "y": []}
    )
    for run in ledger["runs"]:
        params = np.asarray([run["parameters"][key] for key in PARAMETERS], dtype=float)
        for phase in run["phase_records"]:
            key = (phase["bed"], phase["step"])
            start = state_vector(phase["state_start"])
            end = state_vector(phase["state_end"])
            streams = np.r_[phase["in_component_mol"], phase["out_component_mol"]]
            groups[key]["samples"].append(run["sample"])
            groups[key]["x"].append(np.r_[start, params])
            groups[key]["y"].append(np.r_[end - start, streams])
    return {
        key: {name: np.asarray(values, dtype=int if name == "samples" else float) for name, values in group.items()}
        for key, group in groups.items()
    }


def relative_l1(pred: np.ndarray, actual: np.ndarray) -> float:
    return float(np.sum(np.abs(pred - actual)) / max(np.sum(np.abs(actual)), 1.0e-14))


def main() -> None:
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    arrays = arrays_from_ledger(ledger)
    expected_keys = {(phase["bed"], phase["step"]) for phase in ledger["runs"][0]["phase_records"]}
    if set(arrays) != expected_keys:
        raise AssertionError(sorted(arrays))

    phase_rows = []
    event_rows = []
    chosen_alphas: dict[str, list[float]] = defaultdict(list)
    for held_run in ledger["runs"]:
        held_sample = int(held_run["sample"])
        predictions: dict[tuple[str, str], np.ndarray] = {}
        for key, data in arrays.items():
            held_index = int(np.flatnonzero(data["samples"] == held_sample)[0])
            train = data["samples"] != held_sample
            alpha = choose_alpha_nested(data["x"][train], data["y"][train])
            model = fit_ridge(data["x"][train], data["y"][train], alpha)
            pred = model.predict(data["x"][held_index])[0]
            actual = data["y"][held_index]
            predictions[key] = pred
            chosen_alphas[f"{key[0]}_{key[1]}"].append(alpha)
            phase_rows.append(
                {
                    "sample": held_sample,
                    "bed": key[0],
                    "phase": key[1],
                    "alpha": alpha,
                    "state_increment_relative_l1": relative_l1(pred[:10], actual[:10]),
                    "in_stream_relative_l1": relative_l1(np.maximum(pred[10:15], 0.0), actual[10:15]),
                    "out_stream_relative_l1": relative_l1(np.maximum(pred[15:20], 0.0), actual[15:20]),
                }
            )

        recycle = float(held_run["parameters"]["recycle_fraction"])
        adsorption = [predictions[("A", "adsorption")], predictions[("B", "adsorption")]]
        pred_feed = np.sum([np.maximum(values[10:15], 0.0) for values in adsorption], axis=0)
        pred_gross_product = np.sum([np.maximum(values[15:20], 0.0) for values in adsorption], axis=0)
        pred_external = (1.0 - recycle) * pred_gross_product
        pred_purity = float(pred_external[0] / max(pred_external.sum(), 1.0e-14))
        pred_recovery = float(pred_external[0] / max(pred_feed[0], 1.0e-14))
        actual = held_run["event_observables"]
        actual_purity = float(actual["h2_product"])
        actual_recovery = float(actual["h2_recovery_external_proxy"])
        pred_event = bool(pred_purity >= 0.9998 and pred_recovery >= 0.789)
        actual_event = bool(actual["joint_event"])
        event_rows.append(
            {
                "sample": held_sample,
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
            }
        )

    phase_summary = []
    for key in sorted(arrays):
        selected = [row for row in phase_rows if (row["bed"], row["phase"]) == key]
        phase_summary.append(
            {
                "bed": key[0],
                "phase": key[1],
                "median_state_increment_relative_l1": float(np.median([row["state_increment_relative_l1"] for row in selected])),
                "p95_state_increment_relative_l1": float(np.quantile([row["state_increment_relative_l1"] for row in selected], 0.95)),
                "median_in_stream_relative_l1": float(np.median([row["in_stream_relative_l1"] for row in selected])),
                "p95_in_stream_relative_l1": float(np.quantile([row["in_stream_relative_l1"] for row in selected], 0.95)),
                "median_out_stream_relative_l1": float(np.median([row["out_stream_relative_l1"] for row in selected])),
                "p95_out_stream_relative_l1": float(np.quantile([row["out_stream_relative_l1"] for row in selected], 0.95)),
            }
        )

    actual_labels = np.asarray([row["actual_event"] for row in event_rows], dtype=bool)
    pred_labels = np.asarray([row["predicted_event"] for row in event_rows], dtype=bool)
    event_summary = {
        "held_out_runs": len(event_rows),
        "event_matches": int(np.sum(actual_labels == pred_labels)),
        "event_match_fraction": float(np.mean(actual_labels == pred_labels)),
        "false_positive_count": int(np.sum(~actual_labels & pred_labels)),
        "false_negative_count": int(np.sum(actual_labels & ~pred_labels)),
        "purity_mae": float(np.mean([row["purity_abs_error"] for row in event_rows])),
        "purity_max_abs_error": float(max(row["purity_abs_error"] for row in event_rows)),
        "recovery_mae": float(np.mean([row["recovery_abs_error"] for row in event_rows])),
        "recovery_max_abs_error": float(max(row["recovery_abs_error"] for row in event_rows)),
    }

    full_models = {}
    for key, data in arrays.items():
        alpha = choose_alpha_nested(data["x"], data["y"])
        full_models[f"{key[0]}_{key[1]}"] = fit_ridge(data["x"], data["y"], alpha).serialise(
            data["x"].min(axis=0), data["x"].max(axis=0)
        )

    payload = {
        "schema": "psa-qae-cce-primary-phase-event-bridge/v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "nested_holdout_primary_phase_stream_event_bridge_conditional_on_observed_phase_starts",
        "source": LEDGER.name,
        "sample_count": len(ledger["runs"]),
        "input_definition": {
            "phase_start_state": [f"gas_{c}_mol" for c in COMPONENTS] + [f"adsorbed_{c}_mol" for c in COMPONENTS],
            "parameters": PARAMETERS,
            "input_dimension": 10 + len(PARAMETERS),
        },
        "output_definition": {
            "state_increment": [f"delta_gas_{c}_mol" for c in COMPONENTS] + [f"delta_adsorbed_{c}_mol" for c in COMPONENTS],
            "in_stream": [f"in_{c}_mol" for c in COMPONENTS],
            "out_stream": [f"out_{c}_mol" for c in COMPONENTS],
            "output_dimension_per_phase": 20,
        },
        "validation": "outer leave-one-run-out with alpha selected by inner leave-one-out over the other runs",
        "alpha_grid": ALPHAS.tolist(),
        "selected_alpha_histories": dict(chosen_alphas),
        "phase_summary": phase_summary,
        "event_summary": event_summary,
        "phase_rows": phase_rows,
        "event_rows": event_rows,
        "full_fit_models": full_models,
        "qpu_submission": False,
        "claim_boundary": {
            "supported": "held-out reconstruction of the frozen primary event from phase-start states and predicted process streams",
            "unsupported": "free-running CSS prediction, reversible event oracle, independent physical validation, or quantum advantage",
        },
    }
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with OUT_CSV.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(event_rows[0]))
        writer.writeheader()
        writer.writerows(event_rows)

    lines = [
        "# Primary phase-stream to chance-event bridge",
        "",
        "Eight phase-specific ridge maps predict aggregate bed-state increments and five-component inlet/outlet streams. Each outer held run is predicted by maps fitted to the other 31 runs, with ridge strength selected by an inner leave-one-out loop. The two held-out adsorption stream predictions are combined with the declared product-recycle split to reconstruct purity, external recovery, and the frozen event.",
        "",
        f"Event labels match in {event_summary['event_matches']}/{event_summary['held_out_runs']} held runs ({event_summary['event_match_fraction']:.3f}); false positives={event_summary['false_positive_count']} and false negatives={event_summary['false_negative_count']}. Purity MAE is {event_summary['purity_mae']:.3e} and recovery MAE is {event_summary['recovery_mae']:.3e}.",
        "",
        "| bed | phase | p95 state-increment L1 | p95 inlet-stream L1 | p95 outlet-stream L1 |",
        "|---|---|---:|---:|---:|",
    ]
    for row in phase_summary:
        lines.append(
            f"| {row['bed']} | {row['phase']} | {row['p95_state_increment_relative_l1']:.5f} | "
            f"{row['p95_in_stream_relative_l1']:.5f} | {row['p95_out_stream_relative_l1']:.5f} |"
        )
    lines += [
        "",
        "This closes event observability only conditional on the actual held phase-start states. The phase maps are not composed through equalization and repeated CSS, and no plant or end-to-end quantum claim follows.",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    actual_purity = np.asarray([row["actual_purity"] for row in event_rows])
    pred_purity = np.asarray([row["predicted_purity"] for row in event_rows])
    actual_recovery = np.asarray([row["actual_recovery"] for row in event_rows])
    pred_recovery = np.asarray([row["predicted_recovery"] for row in event_rows])
    fig, axes = plt.subplots(1, 2, figsize=(10.8, 4.5), constrained_layout=True)
    axes[0].scatter(actual_purity, pred_purity, c=np.where(actual_labels == pred_labels, "#18794e", "#b44"))
    lo = min(actual_purity.min(), pred_purity.min())
    hi = max(actual_purity.max(), pred_purity.max())
    axes[0].plot([lo, hi], [lo, hi], "k--", linewidth=1)
    axes[0].axhline(0.9998, color="#666", linestyle=":")
    axes[0].axvline(0.9998, color="#666", linestyle=":")
    axes[0].set(xlabel="actual purity", ylabel="held-out predicted purity", title="Adsorption-stream purity")
    axes[1].scatter(actual_recovery, pred_recovery, c=np.where(actual_labels == pred_labels, "#18794e", "#b44"))
    lo = min(actual_recovery.min(), pred_recovery.min())
    hi = max(actual_recovery.max(), pred_recovery.max())
    axes[1].plot([lo, hi], [lo, hi], "k--", linewidth=1)
    axes[1].axhline(0.789, color="#666", linestyle=":")
    axes[1].axvline(0.789, color="#666", linestyle=":")
    axes[1].set(xlabel="actual recovery", ylabel="held-out predicted recovery", title="Adsorption-stream recovery")
    fig.savefig(OUT_PNG, dpi=250)
    fig.savefig(OUT_PDF)
    plt.close(fig)
    print(json.dumps({"status": payload["status"], "event_summary": event_summary, "qpu_submission": False}, indent=2))


if __name__ == "__main__":
    main()
