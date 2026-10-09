"""Design audit for a future decision-active and externally resolvable policy grid.

The frozen 0.420/0.427/0.430 primary experiment is not changed.  This script
maps its conditional surrogate probability over the observed recycle support
and combines that map with the independent H2 recovery-resolution audit.  It
quantifies what data precision or policy spacing a future confirmatory study
would require, without presenting an ex-post sensitivity grid as a new primary
result.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import qmc


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RESULTS = ROOT / "10_TEA_LCA_Python" / "results" / "pycharm_publication_enhancement"
DATA = HERE / "psa_two_bed_spatial_tank_n2_independent_source_uncertainty_32.csv"
PROTOCOL = RESULTS / "PSA_QAE_CCE_PRIMARY_CASE_PROTOCOL.json"
H2_RESOLUTION = RESULTS / "PSA_QAE_CCE_INDEPENDENT_H2_POLICY_RESOLUTION_AUDIT.json"
OUT_JSON = RESULTS / "PSA_QAE_CCE_PROSPECTIVE_POLICY_DESIGN_AUDIT.json"
OUT_CSV = RESULTS / "PSA_QAE_CCE_PROSPECTIVE_POLICY_DESIGN_AUDIT.csv"
OUT_MD = RESULTS / "PSA_QAE_CCE_PROSPECTIVE_POLICY_DESIGN_AUDIT.md"
OUT_PNG = RESULTS / "PSA_QAE_CCE_PROSPECTIVE_POLICY_DESIGN_AUDIT_FIGURE.png"
OUT_PDF = RESULTS / "PSA_QAE_CCE_PROSPECTIVE_POLICY_DESIGN_AUDIT_FIGURE.pdf"

sys.path.insert(0, str(HERE))
from psa_independent_source_surrogate_same_prior_qmc_32 import (  # noqa: E402
    FEATURES,
    draw_inputs,
    fit_surrogate,
    gaussian_copula_parameters,
    predict_event,
)


TARGET = 0.50
REFERENCE_N = 2**16
REFERENCE_REPLICATES = 4
GRID_POINTS = 101


def interpolate_crossing(policy: np.ndarray, probability: np.ndarray) -> float:
    for left in range(len(policy) - 1):
        y0 = probability[left] - TARGET
        y1 = probability[left + 1] - TARGET
        if y0 == 0:
            return float(policy[left])
        if y0 * y1 <= 0:
            return float(
                policy[left]
                + (TARGET - probability[left])
                * (policy[left + 1] - policy[left])
                / (probability[left + 1] - probability[left])
            )
    raise RuntimeError("No p=0.5 crossing inside observed recycle support")


def main() -> None:
    with DATA.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    h2 = json.loads(H2_RESOLUTION.read_text(encoding="utf-8"))
    x, mu, sd, coef = fit_surrogate(rows)
    _, chol = gaussian_copula_parameters(x)

    recycle = x[:, FEATURES.index("recycle_fraction")]
    support_min = float(recycle.min())
    support_max = float(recycle.max())
    support_span = support_max - support_min
    grid = np.linspace(support_min, support_max, GRID_POINTS)
    replicate_probability = np.empty((REFERENCE_REPLICATES, GRID_POINTS), dtype=float)
    for replicate in range(REFERENCE_REPLICATES):
        u = qmc.Sobol(
            d=len(FEATURES), scramble=True, seed=20261110 + replicate
        ).random_base2(int(np.log2(REFERENCE_N)))
        inputs = draw_inputs(u, x, chol)
        for index, policy in enumerate(grid):
            replicate_probability[replicate, index] = float(
                predict_event(inputs, mu, sd, coef, float(policy)).mean()
            )

    mean_probability = replicate_probability.mean(axis=0)
    sd_probability = replicate_probability.std(axis=0, ddof=1)
    crossing = interpolate_crossing(grid, mean_probability)
    derivative = float(
        np.gradient(mean_probability, grid)[np.argmin(np.abs(grid - crossing))]
    )

    independent_coefficient = abs(
        float(h2["recovery_model"]["purge_to_feed_coefficient_pct_point_per_unit"])
    )
    independent_rmse = float(
        h2["recovery_model"]["leave_one_stage_out_rmse_pct_point"]
    )
    spacing_for_one_rmse = independent_rmse / independent_coefficient
    spacing_for_five_rmse = 5.0 * spacing_for_one_rmse
    support_effect = independent_coefficient * support_span
    support_effect_to_rmse = support_effect / independent_rmse
    required_rmse_for_support_5x = support_effect / 5.0
    primary = [float(v) for v in protocol["outer_decision"]["candidate_values"]]
    primary_span = max(primary) - min(primary)
    required_rmse_for_primary_5x = independent_coefficient * primary_span / 5.0

    curve_rows = []
    for index, policy in enumerate(grid):
        curve_rows.append(
            {
                "recycle_fraction": float(policy),
                "reference_probability_mean": float(mean_probability[index]),
                "reference_probability_scramble_sd": float(sd_probability[index]),
                "external_product_fraction": float(1.0 - policy),
                "recycle_to_external_product_ratio": float(policy / (1.0 - policy)),
            }
        )

    payload = {
        "schema": "psa-qae-cce-prospective-policy-design-audit/v1",
        "status": "prospective_design_requirements_quantified_primary_protocol_unchanged",
        "primary_protocol_unchanged": True,
        "conditional_surrogate_curve": {
            "training_recycle_support": [support_min, support_max],
            "support_span": support_span,
            "grid_points": GRID_POINTS,
            "rqmc_points_per_scramble": REFERENCE_N,
            "scrambles": REFERENCE_REPLICATES,
            "p50_crossing_recycle": crossing,
            "local_probability_slope_per_recycle_unit": derivative,
            "rows": curve_rows,
        },
        "independent_h2_resolution_design": {
            "source_control": "Voigt purge/feed ratio",
            "primary_control": protocol["outer_decision"]["variable"],
            "same_control_semantics": False,
            "group_held_out_recovery_rmse_pct_point": independent_rmse,
            "absolute_recovery_coefficient_pct_point_per_unit": independent_coefficient,
            "spacing_for_effect_equal_to_one_rmse": spacing_for_one_rmse,
            "spacing_for_effect_equal_to_five_rmse": spacing_for_five_rmse,
            "observed_support_effect_pct_point": support_effect,
            "observed_support_effect_to_rmse": support_effect_to_rmse,
            "max_recovery_rmse_for_full_support_to_pass_5x_pct_point": required_rmse_for_support_5x,
            "max_recovery_rmse_for_primary_0p010_span_to_pass_5x_pct_point": required_rmse_for_primary_5x,
            "current_rmse_reduction_needed_for_full_support": independent_rmse
            / required_rmse_for_support_5x,
            "five_rmse_spacing_fits_inside_training_support": spacing_for_five_rmse
            <= support_span,
        },
        "future_confirmatory_design_rule": [
            "retain 0.420/0.427/0.430 as the frozen estimator benchmark",
            "use a broad within-support sensitivity panel only as disclosed secondary analysis",
            f"before a new confirmatory H2 campaign, achieve group-held-out recovery RMSE <= {required_rmse_for_support_5x:.3f} percentage points if the full observed recycle span is used",
            "measure continuous purity and use the same physical product-recycle control",
            "freeze candidate values and thresholds before collecting confirmatory outcomes",
        ],
        "claim_boundary": {
            "supported": "prospective data-precision and candidate-spacing requirements conditional on the current surrogate and independent H2 error scale",
            "unsupported": "a new validated optimum, external confirmation of 0.420, or equivalence of purge/feed and product recycle",
        },
    }
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with OUT_CSV.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(curve_rows[0]))
        writer.writeheader()
        writer.writerows(curve_rows)

    lines = [
        "# Prospective recycle-policy design audit",
        "",
        "The frozen primary candidates remain unchanged. This audit asks what spacing and validation precision a future confirmatory H2 study would need.",
        "",
        f"- Observed recycle support: `{support_min:.4f}–{support_max:.4f}` (span `{support_span:.4f}`).",
        f"- Conditional-surrogate p=0.50 crossing: recycle `{crossing:.5f}`; local slope `{derivative:.2f}` probability per recycle unit.",
        f"- Independent H2 recovery error: `{independent_rmse:.3f}` percentage points.",
        f"- Spacing for an effect equal to 1×/5× that error: `{spacing_for_one_rmse:.4f}` / `{spacing_for_five_rmse:.4f}`.",
        f"- The full observed support gives effect/RMSE `{support_effect_to_rmse:.3f}`, so even the widest in-support contrast fails the 5× gate.",
        f"- A full-support confirmatory campaign would require recovery group-CV RMSE `<= {required_rmse_for_support_5x:.3f}` percentage points; the current primary 0.010 span would require `<= {required_rmse_for_primary_5x:.3f}` percentage point.",
        "",
        "The correct next experiment is therefore a broader, same-control H2 campaign with continuous purity and substantially lower held-out recovery error. Expanding the present surrogate beyond its observed support or relabeling purge/feed as product recycle would not close the validation gate.",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    fig, axes = plt.subplots(1, 2, figsize=(11.8, 4.5), constrained_layout=True)
    axes[0].plot(grid, mean_probability, color="#1d4ed8", lw=2, label="conditional RQMC reference")
    axes[0].fill_between(
        grid,
        np.clip(mean_probability - 2 * sd_probability, 0, 1),
        np.clip(mean_probability + 2 * sd_probability, 0, 1),
        color="#93c5fd",
        alpha=0.45,
        label="±2 scramble SD",
    )
    axes[0].axhline(TARGET, color="#b91c1c", ls="--", label="chance target")
    axes[0].axvline(crossing, color="#111827", ls=":", label=f"p=0.5 at {crossing:.4f}")
    for value in primary:
        axes[0].axvline(value, color="#f59e0b", alpha=0.65, lw=1)
    axes[0].set(
        xlabel="product-gas recycle fraction",
        ylabel="joint-event probability",
        title="(a) Decision-active region within observed support",
        ylim=(-0.02, 1.02),
    )
    axes[0].grid(alpha=0.25)
    axes[0].legend(fontsize=7.8)

    spacing = np.linspace(0.0, support_span, 200)
    required_rmse = independent_coefficient * spacing / 5.0
    axes[1].plot(spacing, required_rmse, color="#059669", lw=2, label="maximum RMSE allowed by 5× gate")
    axes[1].axhline(independent_rmse, color="#b91c1c", ls="--", label="current H2 group-CV RMSE")
    axes[1].axvline(primary_span, color="#f59e0b", ls=":", label="current primary span")
    axes[1].axvline(support_span, color="#111827", ls=":", label="observed support span")
    axes[1].set(
        xlabel="candidate spacing",
        ylabel="maximum recovery RMSE, %-point",
        title="(b) Validation precision required for future design",
    )
    axes[1].grid(alpha=0.25)
    axes[1].legend(fontsize=7.8)
    fig.savefig(OUT_PNG, dpi=250)
    fig.savefig(OUT_PDF)
    plt.close(fig)

    print(
        json.dumps(
            {
                "status": payload["status"],
                "crossing": crossing,
                "support": [support_min, support_max],
                "support_effect_to_rmse": support_effect_to_rmse,
                "required_full_support_rmse": required_rmse_for_support_5x,
                "five_rmse_spacing_fits": spacing_for_five_rmse <= support_span,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
