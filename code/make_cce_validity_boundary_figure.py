"""Create CCE Figure 6: process-model and external-validation boundaries."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RESULTS = ROOT / "10_TEA_LCA_Python" / "results" / "pycharm_publication_enhancement"
DISCREPANCY = RESULTS / "QAE_SURROGATE_MODEL_DISCREPANCY_BOUNDARY.json"
EXTERNAL = RESULTS / "PSA_QAE_CCE_EXTERNAL_LIGHT_PRODUCT_POLICY_VALIDATION.json"
REFINEMENT = RESULTS / "PSA_QAE_CCE_EXTERNAL_POLICY_NUMERICAL_REFINEMENT.json"
OUT_PNG = RESULTS / "PSA_QAE_CCE_VALIDITY_BOUNDARY_FIGURE.png"
OUT_PDF = RESULTS / "PSA_QAE_CCE_VALIDITY_BOUNDARY_FIGURE.pdf"
OUT_JSON = RESULTS / "PSA_QAE_CCE_VALIDITY_BOUNDARY_FIGURE.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    discrepancy = load(DISCREPANCY)
    external = load(EXTERNAL)
    refinement = load(REFINEMENT)
    plt.rcParams.update(
        {
            "font.size": 9.2,
            "axes.titlesize": 10.5,
            "axes.labelsize": 9.5,
            "legend.fontsize": 7.6,
            "xtick.labelsize": 8.4,
            "ytick.labelsize": 8.4,
        }
    )
    fig, axes = plt.subplots(2, 2, figsize=(12.4, 8.2), constrained_layout=True)

    # (a) Probability-scale model discrepancy.
    ax = axes[0, 0]
    base = float(discrepancy["base_surrogate_probability"])
    mean = float(discrepancy["discrepancy_stress_probability_mean"])
    low = float(discrepancy["discrepancy_stress_probability_p025"])
    high = float(discrepancy["discrepancy_stress_probability_p975"])
    ax.errorbar(
        [mean],
        [1],
        xerr=[[mean - low], [high - mean]],
        fmt="o",
        capsize=5,
        lw=2,
        color="#1f77b4",
        label="LOOCV-residual stress 95% range",
    )
    ax.scatter([base], [0], marker="D", s=50, color="#ff7f0e", label="base surrogate")
    ax.axvline(0.50, color="#c00000", ls="--", label="chance target")
    ax.set(
        xlabel="event probability at recycle 0.427",
        title="(a) Residual-stress probability boundary",
        yticks=[0, 1],
        yticklabels=["base", "residual stress"],
    )
    ax.set_xlim(min(low, base) - 0.006, 0.505)
    ax.set_ylim(-0.65, 1.65)
    ax.grid(alpha=0.25, axis="x")
    ax.legend(loc="lower right")
    ax.text(
        0.02,
        0.95,
        f"base {base:.4f}\nstress 95% [{low:.4f}, {high:.4f}]",
        transform=ax.transAxes,
        va="top",
        bbox={"facecolor": "white", "edgecolor": "0.8", "alpha": 0.9, "pad": 3},
    )

    # (b) Numerical estimator target versus process-model scale.
    ax = axes[0, 1]
    values = [
        discrepancy["qae_target_epsilon"],
        discrepancy["holdout_recovery_rmse"],
        0.5 * (high - low),
    ]
    labels = ["QAE target\n$\\epsilon$", "recovery\nLOOCV RMSE", "residual-stress\n95% half-width"]
    colors = ["#ff7f0e", "#70ad47", "#7f7f7f"]
    bars = ax.bar(labels, values, color=colors, width=0.62)
    for bar, value in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, value * 1.08, f"{value:.4g}", ha="center", va="bottom", fontsize=8)
    ax.set(ylabel="probability or response scale", title="(b) Estimator precision versus model-form scale", yscale="log")
    ax.set_ylim(4.0e-4, 5.5e-3)
    ax.grid(alpha=0.25, axis="y", which="both")

    # (c) External public-model purity direction.
    ax = axes[1, 0]
    policies = sorted({float(row["policy_light_product_purge_to_feed_conductance_ratio"]) for row in external["rows"]})
    scenarios = external["scenarios"]
    for scenario in scenarios:
        rows = sorted([row for row in external["rows"] if row["scenario"] == scenario], key=lambda row: row["policy_light_product_purge_to_feed_conductance_ratio"])
        base_purity = float(rows[0]["n2_purity_pct"])
        ax.plot(
            [row["policy_light_product_purge_to_feed_conductance_ratio"] for row in rows],
            [float(row["n2_purity_pct"]) - base_purity for row in rows],
            "o-",
            ms=4,
            label=scenario.replace("t14_", "").replace("t9_", ""),
        )
    ax.axhline(0.0, color="0.35", ls=":")
    ax.set(xlabel="light-product purge/feed conductance ratio", ylabel="N2-purity change from 0.420 (percentage point)", title="(c) Independent public-model direction control")
    ax.set_xticks(policies)
    ax.grid(alpha=0.25)
    ax.legend(loc="lower left", ncol=2)

    # (d) Policy signal relative to the public solver's numerical-resolution shift.
    ax = axes[1, 1]
    summaries = refinement["summaries"]
    labels = [row["scenario"].replace("t9_", "").replace("t14_", "") for row in summaries]
    ratios = [row["abs_policy_recovery_effect_over_abs_quadrature_shift"] for row in summaries]
    bars = ax.bar(labels, ratios, color=["#1f77b4", "#d62728"], width=0.58)
    ax.axhline(1.0, color="#c00000", ls="--", label="policy effect = quadrature shift")
    for bar, ratio in zip(bars, ratios):
        ax.text(bar.get_x() + bar.get_width() / 2, ratio * 1.18, f"{100*ratio:.2f}%", ha="center", va="bottom")
    ax.set(ylabel="|policy recovery effect| / |quadrature shift|", title="(d) External policy signal versus numerical scale", yscale="log")
    ax.set_ylim(1e-3, 2.0)
    ax.tick_params(axis="x", rotation=12)
    ax.grid(alpha=0.25, axis="y", which="both")
    ax.legend(loc="upper left")

    fig.savefig(OUT_PNG, dpi=300)
    fig.savefig(OUT_PDF)
    plt.close(fig)

    payload = {
        "schema": "psa-qae-cce-validity-boundary-figure/v1",
        "status": "main_text_validity_boundary_assembled_external_h2_selection_gate_open",
        "source_files": [DISCREPANCY.name, EXTERNAL.name, REFINEMENT.name],
        "panels": {
            "a": {"base_probability": base, "stress_mean": mean, "stress_p025": low, "stress_p975": high},
            "b": {"qae_target_epsilon": values[0], "holdout_recovery_rmse": values[1], "stress_half_width": values[2]},
            "c": {"scenarios": scenarios, "purity_direction_match_count": external["purity_endpoint_direction_match_count"]},
            "d": {"scenario_ratios": {row["scenario"]: row["abs_policy_recovery_effect_over_abs_quadrature_shift"] for row in summaries}},
        },
        "claim_boundary": "Model discrepancy and external numerical resolution exceed or compete with the estimator target; the public CO2/N2 model is not same-H2 policy validation.",
    }
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": payload["status"], "figure": OUT_PNG.name}, indent=2))


if __name__ == "__main__":
    main()
