"""Fit and audit a phasewise one-cycle bridge from the physical PSA ledger.

The eight-dimensional bed state (four gas inventories and four adsorbed
loadings) is preserved. Ridge phase maps are evaluated with nested
leave-one-run-out prediction and then composed through one synchronized cycle;
the original conservative equalization equation is retained. The artifact is
a calibrated reduced-model bridge, not yet a reversible fixed-point oracle.
"""

from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import MaxNLocator


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RESULTS = ROOT / "10_TEA_LCA_Python" / "results" / "pycharm_publication_enhancement"
LEDGER = RESULTS / "PSA_QAE_DIRECT_PHYSICAL_PHASE_LEDGER.json"
SOURCE = HERE / "psa_two_bed_parameter_uncertainty.csv"
OUT_JSON = RESULTS / "PSA_QAE_CCE_CALIBRATED_ONE_CYCLE_PHASE_MAP.json"
OUT_CSV = RESULTS / "PSA_QAE_CCE_CALIBRATED_ONE_CYCLE_PHASE_MAP.csv"
OUT_MD = RESULTS / "PSA_QAE_CCE_CALIBRATED_ONE_CYCLE_PHASE_MAP.md"
OUT_PNG = RESULTS / "PSA_QAE_CCE_CALIBRATED_ONE_CYCLE_PHASE_MAP_FIGURE.png"
OUT_PDF = RESULTS / "PSA_QAE_CCE_CALIBRATED_ONE_CYCLE_PHASE_MAP_FIGURE.pdf"

sys.path.insert(0, str(HERE.parent))
from psa_qae import psa_two_bed_lumped_probe as lumped  # noqa: E402
from psa_qae.extract_direct_physical_phase_ledger import make_params  # noqa: E402
from psa_qae.psa_two_bed_parameter_uncertainty import feed_cases  # noqa: E402


ALPHAS = np.asarray([1.0e-5, 1.0e-4, 1.0e-3, 1.0e-2, 1.0e-1, 1.0, 10.0, 100.0])
PHASE_ORDER = (
    ("A", "adsorption"),
    ("B", "pressurization"),
    ("A", "blowdown"),
    ("B", "adsorption"),
    ("A", "purge"),
    ("B", "blowdown"),
    ("A", "pressurization"),
    ("B", "purge"),
)


@dataclass
class RidgeModel:
    x_mean: np.ndarray
    x_scale: np.ndarray
    y_mean: np.ndarray
    y_scale: np.ndarray
    coef: np.ndarray
    alpha: float

    def predict(self, x: np.ndarray) -> np.ndarray:
        x2 = np.atleast_2d(np.asarray(x, dtype=float))
        return (((x2 - self.x_mean) / self.x_scale) @ self.coef) * self.y_scale + self.y_mean


def static_features(row: dict[str, str], cases: dict[str, dict]) -> np.ndarray:
    feed = np.asarray(cases[row["feed_case_id"]]["feed_y_dry"], dtype=float)
    feed /= feed.sum()
    return np.asarray(
        [
            float(row["capacity_factor"]),
            float(row["affinity_factor"]),
            float(row["ldf_factor"]),
            float(feed[0]),
            float(feed[1]),
            float(feed[2]),
        ]
    )


def fit_ridge(x: np.ndarray, y: np.ndarray, alpha: float) -> RidgeModel:
    x_mean = x.mean(axis=0)
    x_scale = x.std(axis=0)
    x_scale[x_scale < 1.0e-12] = 1.0
    y_mean = y.mean(axis=0)
    y_scale = y.std(axis=0)
    y_scale[y_scale < 1.0e-12] = 1.0
    xz = (x - x_mean) / x_scale
    yz = (y - y_mean) / y_scale
    coef = np.linalg.solve(
        xz.T @ xz + float(alpha) * np.eye(x.shape[1]), xz.T @ yz
    )
    return RidgeModel(x_mean, x_scale, y_mean, y_scale, coef, float(alpha))


def choose_alpha_nested(x: np.ndarray, y: np.ndarray) -> float:
    scale = y.std(axis=0)
    scale[scale < 1.0e-12] = 1.0
    scores = []
    for alpha in ALPHAS:
        errors = []
        for holdout in range(len(x)):
            mask = np.arange(len(x)) != holdout
            prediction = fit_ridge(x[mask], y[mask], float(alpha)).predict(x[holdout])[0]
            errors.append((prediction - y[holdout]) / scale)
        scores.append(float(np.mean(np.square(errors))))
    return float(ALPHAS[int(np.argmin(scores))])


def make_phase_arrays(
    ledger: dict,
    source_by_sample: dict[int, dict[str, str]],
    cases: dict[str, dict],
) -> dict[tuple[str, str], dict[str, np.ndarray]]:
    grouped: dict[tuple[str, str], dict[str, list]] = defaultdict(
        lambda: {"sample": [], "x": [], "y": []}
    )
    for run in ledger["runs"]:
        sample = int(run["sample"])
        static = static_features(source_by_sample[sample], cases)
        for record in run["phase_records"]:
            key = (record["bed"], record["step"])
            start = np.asarray(record["state_start"], dtype=float)
            end = np.asarray(record["state_end"], dtype=float)
            grouped[key]["sample"].append(sample)
            grouped[key]["x"].append(np.r_[start, static])
            grouped[key]["y"].append(np.r_[end - start, record["outlet_h2_fraction"]])
    return {
        key: {
            name: np.asarray(values, dtype=int if name == "sample" else float)
            for name, values in payload.items()
        }
        for key, payload in grouped.items()
    }


def train_models_excluding(arrays, held_sample: int):
    models = {}
    selected = {}
    for key, data in arrays.items():
        mask = data["sample"] != held_sample
        alpha = choose_alpha_nested(data["x"][mask], data["y"][mask])
        models[key] = fit_ridge(data["x"][mask], data["y"][mask], alpha)
        selected[f"{key[0]}_{key[1]}"] = alpha
    return models, selected


def phase_predict(model: RidgeModel, state: np.ndarray, static: np.ndarray):
    values = model.predict(np.r_[state, static])[0]
    raw_end = state + values[:8]
    clipped = int(np.count_nonzero(raw_end < 0.0))
    return np.maximum(raw_end, 0.0), float(np.clip(values[8], 0.0, 1.0)), clipped


def relative_l1(prediction: np.ndarray, actual: np.ndarray) -> float:
    return float(
        np.sum(np.abs(prediction - actual)) / max(np.sum(np.abs(actual)), 1.0e-12)
    )


def pressure(state: np.ndarray, params) -> float:
    return float(lumped.pressure_bar(np.asarray(state[:4], dtype=float), params))


def main() -> None:
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    with SOURCE.open(newline="", encoding="utf-8-sig") as handle:
        source_rows = list(csv.DictReader(handle))
    source_by_sample = {int(row["sample"]): row for row in source_rows}
    cases = {case["case_id"]: case for case in feed_cases()}
    arrays = make_phase_arrays(ledger, source_by_sample, cases)
    if set(arrays) != set(PHASE_ORDER):
        raise AssertionError(f"unexpected phase keys: {sorted(arrays)}")

    one_step_rows = []
    cycle_rows = []
    selected_alphas: dict[str, list[float]] = defaultdict(list)

    for run in ledger["runs"]:
        sample = int(run["sample"])
        source = source_by_sample[sample]
        static = static_features(source, cases)
        params = make_params(source, cases)
        models, alphas = train_models_excluding(arrays, sample)
        for key, alpha in alphas.items():
            selected_alphas[key].append(alpha)
        records = {(row["bed"], row["step"]): row for row in run["phase_records"]}

        for key in PHASE_ORDER:
            record = records[key]
            start = np.asarray(record["state_start"], dtype=float)
            actual = np.asarray(record["state_end"], dtype=float)
            predicted, outlet, clipped = phase_predict(models[key], start, static)
            one_step_rows.append(
                {
                    "sample": sample,
                    "bed": key[0],
                    "phase": key[1],
                    "state_relative_l1": relative_l1(predicted, actual),
                    "persistence_relative_l1": relative_l1(start, actual),
                    "pressure_abs_error_bar": abs(
                        pressure(predicted, params) - float(record["P_end_bar"])
                    ),
                    "outlet_h2_abs_error": abs(
                        outlet - float(record["outlet_h2_fraction"])
                    ),
                    "negative_state_values_clipped": clipped,
                }
            )

        state_a = np.asarray(records[("A", "adsorption")]["state_start"], dtype=float)
        state_b = np.asarray(records[("B", "pressurization")]["state_start"], dtype=float)
        initial_a = state_a.copy()
        initial_b = state_b.copy()
        clipped_total = 0
        direction_matches = 0

        state_a, _, clipped = phase_predict(models[("A", "adsorption")], state_a, static)
        clipped_total += clipped
        state_b, _, clipped = phase_predict(models[("B", "pressurization")], state_b, static)
        clipped_total += clipped
        state_a, state_b, eq = lumped.equalize_pair(state_a, state_b, params, 2.0, 0.10)
        direction_matches += int(
            eq["direction"] == run["equalization_records"][0]["direction"]
        )

        state_a, _, clipped = phase_predict(models[("A", "blowdown")], state_a, static)
        clipped_total += clipped
        state_b, _, clipped = phase_predict(models[("B", "adsorption")], state_b, static)
        clipped_total += clipped
        state_a, state_b, eq = lumped.equalize_pair(state_a, state_b, params, 2.0, 0.10)
        direction_matches += int(
            eq["direction"] == run["equalization_records"][1]["direction"]
        )

        for key in (("A", "purge"), ("B", "blowdown"), ("A", "pressurization"), ("B", "purge")):
            if key[0] == "A":
                state_a, _, clipped = phase_predict(models[key], state_a, static)
            else:
                state_b, _, clipped = phase_predict(models[key], state_b, static)
            clipped_total += clipped

        actual_a = np.asarray(records[("A", "pressurization")]["state_end"], dtype=float)
        actual_b = np.asarray(records[("B", "purge")]["state_end"], dtype=float)
        cycle_rows.append(
            {
                "sample": sample,
                "state_relative_l1_a": relative_l1(state_a, actual_a),
                "state_relative_l1_b": relative_l1(state_b, actual_b),
                "state_relative_l1_joint": relative_l1(
                    np.r_[state_a, state_b], np.r_[actual_a, actual_b]
                ),
                "persistence_relative_l1_joint": relative_l1(
                    np.r_[initial_a, initial_b], np.r_[actual_a, actual_b]
                ),
                "pressure_abs_error_a_bar": abs(
                    pressure(state_a, params) - pressure(actual_a, params)
                ),
                "pressure_abs_error_b_bar": abs(
                    pressure(state_b, params) - pressure(actual_b, params)
                ),
                "equalization_direction_matches": direction_matches,
                "negative_state_values_clipped": clipped_total,
            }
        )

    phase_summary = []
    for key in PHASE_ORDER:
        rows = [
            row
            for row in one_step_rows
            if (row["bed"], row["phase"]) == key
        ]
        phase_summary.append(
            {
                "bed": key[0],
                "phase": key[1],
                "records": len(rows),
                "median_state_relative_l1": float(
                    np.median([row["state_relative_l1"] for row in rows])
                ),
                "p95_state_relative_l1": float(
                    np.quantile([row["state_relative_l1"] for row in rows], 0.95)
                ),
                "median_persistence_relative_l1": float(
                    np.median([row["persistence_relative_l1"] for row in rows])
                ),
                "median_pressure_abs_error_bar": float(
                    np.median([row["pressure_abs_error_bar"] for row in rows])
                ),
                "p95_pressure_abs_error_bar": float(
                    np.quantile([row["pressure_abs_error_bar"] for row in rows], 0.95)
                ),
                "median_outlet_h2_abs_error": float(
                    np.median([row["outlet_h2_abs_error"] for row in rows])
                ),
                "p95_outlet_h2_abs_error": float(
                    np.quantile([row["outlet_h2_abs_error"] for row in rows], 0.95)
                ),
                "median_nested_alpha": float(
                    np.median(selected_alphas[f"{key[0]}_{key[1]}"])
                ),
            }
        )

    cycle_joint = np.asarray([row["state_relative_l1_joint"] for row in cycle_rows])
    cycle_persistence = np.asarray(
        [row["persistence_relative_l1_joint"] for row in cycle_rows]
    )
    cycle_summary = {
        "runs": len(cycle_rows),
        "median_joint_state_relative_l1": float(np.median(cycle_joint)),
        "p95_joint_state_relative_l1": float(np.quantile(cycle_joint, 0.95)),
        "max_joint_state_relative_l1": float(np.max(cycle_joint)),
        "median_persistence_relative_l1": float(np.median(cycle_persistence)),
        "median_error_ratio_vs_persistence": float(
            np.median(cycle_joint / np.maximum(cycle_persistence, 1.0e-12))
        ),
        "median_pressure_abs_error_a_bar": float(
            np.median([row["pressure_abs_error_a_bar"] for row in cycle_rows])
        ),
        "median_pressure_abs_error_b_bar": float(
            np.median([row["pressure_abs_error_b_bar"] for row in cycle_rows])
        ),
        "p95_pressure_abs_error_a_bar": float(
            np.quantile([row["pressure_abs_error_a_bar"] for row in cycle_rows], 0.95)
        ),
        "p95_pressure_abs_error_b_bar": float(
            np.quantile([row["pressure_abs_error_b_bar"] for row in cycle_rows], 0.95)
        ),
        "equalization_direction_match_fraction": float(
            sum(row["equalization_direction_matches"] for row in cycle_rows)
            / (2 * len(cycle_rows))
        ),
        "total_negative_state_values_clipped": int(
            sum(row["negative_state_values_clipped"] for row in cycle_rows)
        ),
    }
    full_fit_models = {}
    for key, data in arrays.items():
        alpha = choose_alpha_nested(data["x"], data["y"])
        model = fit_ridge(data["x"], data["y"], alpha)
        full_fit_models[f"{key[0]}_{key[1]}"] = {
            "alpha": alpha,
            "x_min": data["x"].min(axis=0).tolist(),
            "x_max": data["x"].max(axis=0).tolist(),
            "x_mean": model.x_mean.tolist(),
            "x_scale": model.x_scale.tolist(),
            "y_mean": model.y_mean.tolist(),
            "y_scale": model.y_scale.tolist(),
            "standardized_coefficients": model.coef.tolist(),
        }
    payload = {
        "schema": "psa-qae-cce-calibrated-one-cycle-phase-map/v1",
        "status": "nested_leave_one_run_out_phase_map_bridge_quantified_not_reversible_cyclic_oracle",
        "source_rows": len(source_rows),
        "phase_records": len(one_step_rows),
        "state_dimension_per_bed": 8,
        "static_feature_names": [
            "capacity_factor",
            "affinity_factor",
            "ldf_factor",
            "feed_H2",
            "feed_CO2",
            "feed_CH4",
        ],
        "ridge_alpha_grid": ALPHAS.tolist(),
        "validation": "outer leave-one-run-out with nested leave-one-out alpha selection",
        "phase_summary": phase_summary,
        "cycle_summary": cycle_summary,
        "full_fit_models": full_fit_models,
        "one_step_rows": one_step_rows,
        "cycle_rows": cycle_rows,
        "limitations": [
            "The maps are trained on 20 one-cycle runs of one reduced H2 PSA model, not plant data or an independent solver.",
            "The validation holds out one run at a time but the candidate ridge family and static feature set were chosen for this study.",
            "The exact classical equalization equation is retained; it is not yet encoded as reversible fixed-point arithmetic.",
            "The composed bridge covers one initialized cycle, not repeated convergence to cyclic steady state.",
            "No purity/recovery chance event, primitive gate count, loader, or QPU advantage is inferred from this artifact.",
        ],
    }
    OUT_JSON.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    csv_rows = [{"row_type": "phase_summary", **row} for row in phase_summary]
    csv_rows += [{"row_type": "cycle_holdout", **row} for row in cycle_rows]
    fields = sorted({key for row in csv_rows for key in row})
    with OUT_CSV.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(csv_rows)

    c = cycle_summary
    lines = [
        "# Calibrated one-cycle PSA phase-map bridge",
        "",
        "The full eight-dimensional bed state is retained from the physical phase ledger. Eight phase-specific ridge maps predict state increments and outlet H2. Each held-out run is predicted by models fitted to the other 19 runs, with ridge strength chosen by an inner leave-one-out loop. The original conservative equalization equation is used between phase maps.",
        "",
        "| bed | phase | median state L1 | p95 state L1 | persistence median | median P error (bar) | p95 P error (bar) | median outlet-H2 error | p95 outlet-H2 error |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in phase_summary:
        lines.append(
            f"| {row['bed']} | {row['phase']} | {row['median_state_relative_l1']:.5f} | "
            f"{row['p95_state_relative_l1']:.5f} | {row['median_persistence_relative_l1']:.5f} | "
            f"{row['median_pressure_abs_error_bar']:.5f} | {row['p95_pressure_abs_error_bar']:.5f} | "
            f"{row['median_outlet_h2_abs_error']:.5f} | {row['p95_outlet_h2_abs_error']:.5f} |"
        )
    lines += [
        "",
        f"After composing the held-out phase maps through one synchronized cycle, median joint-state relative L1 error is {c['median_joint_state_relative_l1']:.5f} and p95 is {c['p95_joint_state_relative_l1']:.5f}. The median error is {c['median_error_ratio_vs_persistence']:.3f}x the initial-state persistence baseline. Median final pressure errors are {c['median_pressure_abs_error_a_bar']:.5f} bar for bed A and {c['median_pressure_abs_error_b_bar']:.5f} bar for bed B. Equalization direction agrees in {c['equalization_direction_match_fraction']:.3f} of calls.",
        "",
        "This is a calibrated reduced-model bridge, not a reversible cyclic PSA oracle. It adds held-out phase and one-cycle evidence while leaving fixed-point equalization, repeated CSS convergence, the primary purity/recovery event, and primitive-gate synthesis open.",
        "",
        f"Artifacts: {OUT_JSON.name}, {OUT_CSV.name}, {OUT_PNG.name}.",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    phase_labels = [f"{row['bed']} {row['phase']}" for row in phase_summary]
    fig, axes = plt.subplots(2, 2, figsize=(11.2, 7.5), constrained_layout=True)
    axes[0, 0].barh(
        phase_labels,
        [row["median_state_relative_l1"] for row in phase_summary],
        color="#4472c4",
        label="ridge phase map",
    )
    axes[0, 0].scatter(
        [row["median_persistence_relative_l1"] for row in phase_summary],
        np.arange(len(phase_summary)),
        color="#ed7d31",
        marker="x",
        label="persistence",
    )
    axes[0, 0].set(
        xlabel="median state relative L1",
        title="Nested holdout one-step state error",
    )
    axes[0, 0].set_xscale("log")
    axes[0, 0].legend(fontsize=8)
    axes[0, 0].grid(axis="x", alpha=0.25)

    axes[0, 1].barh(
        phase_labels,
        [row["median_outlet_h2_abs_error"] for row in phase_summary],
        color="#70ad47",
    )
    axes[0, 1].set(
        xlabel="median absolute H2 fraction error",
        title="Holdout outlet-composition error",
    )
    axes[0, 1].xaxis.set_major_locator(MaxNLocator(5))
    axes[0, 1].ticklabel_format(axis="x", style="sci", scilimits=(-3, 3))
    axes[0, 1].grid(axis="x", alpha=0.25)

    samples = [row["sample"] for row in cycle_rows]
    axes[1, 0].plot(samples, cycle_persistence, "x", color="#ed7d31", label="persistence")
    axes[1, 0].plot(samples, cycle_joint, "o", color="#8b3a50", label="phase-map bridge")
    axes[1, 0].set(
        xlabel="held-out run",
        ylabel="joint-state relative L1",
        title="Held-out one-cycle state error",
    )
    axes[1, 0].set_yscale("log")
    axes[1, 0].legend(fontsize=8)
    axes[1, 0].grid(alpha=0.25)

    axes[1, 1].scatter(
        [row["pressure_abs_error_a_bar"] for row in cycle_rows],
        [row["pressure_abs_error_b_bar"] for row in cycle_rows],
        color="#5b9bd5",
        alpha=0.8,
    )
    axes[1, 1].set(
        xlabel="bed A final pressure error (bar)",
        ylabel="bed B final pressure error (bar)",
        title="Composed one-cycle pressure error",
    )
    axes[1, 1].grid(alpha=0.25)
    fig.savefig(OUT_PNG, dpi=250)
    fig.savefig(OUT_PDF)
    plt.close(fig)

    print(
        json.dumps(
            {
                "status": payload["status"],
                "median_cycle_relative_l1": c["median_joint_state_relative_l1"],
                "p95_cycle_relative_l1": c["p95_joint_state_relative_l1"],
                "median_ratio_vs_persistence": c["median_error_ratio_vs_persistence"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
