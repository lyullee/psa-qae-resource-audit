"""Audit whether public H2 data can resolve the frozen policy spacing.

The Voigt H2/CH4 cycle table supports a group-held-out recovery model whose
purge/feed-ratio coefficient is reported in the existing empirical calibration
artifact.  This script applies only the *spacing* of the frozen recycle
candidates to that independent H2 coefficient and compares the implied
recovery effects with held-out error.  Purge/feed ratio and product recycle are
not treated as the same control, so this is a resolution/identifiability audit,
not external policy validation.
"""

from __future__ import annotations

import csv
import itertools
import json
from pathlib import Path

import matplotlib.pyplot as plt


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RESULTS = ROOT / "10_TEA_LCA_Python" / "results" / "pycharm_publication_enhancement"
EMPIRICAL = RESULTS / "PSA_QAE_EMPIRICAL_VALVE_TANK_PRODUCT_CALIBRATION.json"
PROTOCOL = RESULTS / "PSA_QAE_CCE_PRIMARY_CASE_PROTOCOL.json"
OUT_JSON = RESULTS / "PSA_QAE_CCE_INDEPENDENT_H2_POLICY_RESOLUTION_AUDIT.json"
OUT_CSV = RESULTS / "PSA_QAE_CCE_INDEPENDENT_H2_POLICY_RESOLUTION_AUDIT.csv"
OUT_MD = RESULTS / "PSA_QAE_CCE_INDEPENDENT_H2_POLICY_RESOLUTION_AUDIT.md"
OUT_PNG = RESULTS / "PSA_QAE_CCE_INDEPENDENT_H2_POLICY_RESOLUTION_AUDIT_FIGURE.png"
OUT_PDF = RESULTS / "PSA_QAE_CCE_INDEPENDENT_H2_POLICY_RESOLUTION_AUDIT_FIGURE.pdf"

RESOLUTION_MULTIPLE = 5.0


def main() -> None:
    empirical = json.loads(EMPIRICAL.read_text(encoding="utf-8"))
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    recovery = empirical["tuwien"]["recovery_summary"]
    coefficient = float(
        recovery["coefficients_pct_point_per_native_unit"]["purge_to_feed_ratio"]
    )
    cv_rmse = float(recovery["leave_one_stage_out_rmse_pct_point"])
    cv_mae = float(recovery["leave_one_stage_out_mae_pct_point"])
    train_rmse = float(recovery["training_rmse_pct_point"])
    policies = [float(value) for value in protocol["outer_decision"]["candidate_values"]]

    rows = []
    for low, high in itertools.combinations(policies, 2):
        spacing = high - low
        signed_effect = coefficient * spacing
        effect = abs(signed_effect)
        ratio = effect / cv_rmse
        required_rmse = effect / RESOLUTION_MULTIPLE
        rows.append(
            {
                "lower_numeric_candidate": low,
                "upper_numeric_candidate": high,
                "candidate_spacing": spacing,
                "voigt_recovery_effect_pct_point": signed_effect,
                "absolute_effect_pct_point": effect,
                "group_cv_rmse_pct_point": cv_rmse,
                "group_cv_mae_pct_point": cv_mae,
                "effect_to_group_cv_rmse": ratio,
                "required_max_rmse_for_5x_gate_pct_point": required_rmse,
                "rmse_reduction_factor_needed": cv_rmse / required_rmse,
                "passes_5x_resolution_gate": effect > RESOLUTION_MULTIPLE * cv_rmse,
            }
        )

    best = max(rows, key=lambda row: row["effect_to_group_cv_rmse"])
    uncertainty_values = [
        float(row["recovery_uncertainty_pct"])
        for row in csv.DictReader(
            (HERE / "psa_qae_tuwien_h2_digitized_cycle_table.csv").open(
                newline="", encoding="utf-8-sig"
            )
        )
    ]
    payload = {
        "schema": "psa-qae-cce-independent-h2-policy-resolution-audit/v1",
        "status": "independent_h2_policy_resolution_gate_failed_semantics_and_error",
        "source": {
            "doi": empirical["sources"]["tuwien_h2_ch4"]["doi"],
            "runs": int(recovery["n_runs"]),
            "control_in_source": "purge-to-feed ratio",
            "control_in_primary_case": protocol["outer_decision"]["variable"],
        },
        "frozen_numeric_candidates": policies,
        "recovery_model": {
            "purge_to_feed_coefficient_pct_point_per_unit": coefficient,
            "training_rmse_pct_point": train_rmse,
            "leave_one_stage_out_rmse_pct_point": cv_rmse,
            "leave_one_stage_out_mae_pct_point": cv_mae,
            "reported_recovery_uncertainty_range_pct_point": [
                min(uncertainty_values),
                max(uncertainty_values),
            ],
            "continuous_purity_status": recovery["continuous_purity_model_status"],
        },
        "predeclared_resolution_rule": (
            "absolute policy effect must exceed five times group-held-out RMSE"
        ),
        "pairwise_rows": rows,
        "best_available_pair": best,
        "gate": {
            "all_pairs_fail_5x_resolution": all(
                not row["passes_5x_resolution_gate"] for row in rows
            ),
            "same_control_semantics": False,
            "continuous_frozen_purity_event_identifiable": False,
            "counts_as_external_selection_validation": False,
        },
        "interpretation": (
            "The widest frozen spacing implies only "
            f"{best['absolute_effect_pct_point']:.3f} recovery percentage point under the independent H2/CH4 coefficient, "
            f"or {best['effect_to_group_cv_rmse']:.3f} of group-held-out RMSE. "
            "The public H2 table therefore cannot resolve the candidate grid, and its purge/feed coordinate is not product recycle."
        ),
        "claim_boundary": {
            "supported": "independent public-H2 policy-spacing resolution and identifiability audit",
            "unsupported": "same-policy recycle validation, frozen joint-event validation, or confirmation of the 0.420 selection",
        },
    }

    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with OUT_CSV.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    lines = [
        "# Independent H2 policy-spacing resolution audit",
        "",
        "The public Voigt H2/CH4 table provides a purge/feed-ratio recovery coefficient and group-held-out error. The frozen recycle candidate spacings are applied numerically to that coefficient only to test resolution. Purge/feed ratio is not asserted to be product-gas recycle.",
        "",
        "| numeric pair | implied recovery effect, %-point | group-CV RMSE, %-point | effect/RMSE | RMSE reduction needed for 5x gate | pass |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row['lower_numeric_candidate']:.3f}–{row['upper_numeric_candidate']:.3f} | "
            f"{row['voigt_recovery_effect_pct_point']:+.3f} | {row['group_cv_rmse_pct_point']:.3f} | "
            f"{row['effect_to_group_cv_rmse']:.4f} | {row['rmse_reduction_factor_needed']:.1f}× | "
            f"{row['passes_5x_resolution_gate']} |"
        )
    lines += [
        "",
        f"The widest pair resolves only `{best['effect_to_group_cv_rmse']:.4f}` of the held-out RMSE and would require a `{best['rmse_reduction_factor_needed']:.1f}×` RMSE reduction to satisfy the declared 5× gate. Reported recovery uncertainty spans `{min(uncertainty_values):.1f}–{max(uncertainty_values):.1f}` percentage points. Continuous purity is not identifiable because only one Type-2 run exists and the analyser is detection-limit censored.",
        "",
        "This is a stronger quantified negative control, not external validation of recycle 0.420. It shows that the available independent H2 table cannot distinguish the frozen 0.007–0.010 candidate spacing even before control-semantic mismatch is considered.",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    labels = [
        f"{row['lower_numeric_candidate']:.3f}–{row['upper_numeric_candidate']:.3f}"
        for row in rows
    ]
    ratios = [row["effect_to_group_cv_rmse"] for row in rows]
    fig, ax = plt.subplots(figsize=(8.0, 4.5), constrained_layout=True)
    bars = ax.bar(labels, ratios, color="#2563eb")
    ax.axhline(RESOLUTION_MULTIPLE, color="#b91c1c", ls="--", label="declared 5× resolution gate")
    for bar, value in zip(bars, ratios):
        ax.text(bar.get_x() + bar.get_width() / 2, value * 1.08, f"{value:.3f}×", ha="center", va="bottom")
    ax.set(
        xlabel="frozen numeric candidate pair",
        ylabel="implied recovery effect / group-held-out RMSE",
        title="Independent H$_2$ data cannot resolve the frozen policy spacing",
        yscale="log",
    )
    ax.set_ylim(0.02, 10.0)
    ax.grid(axis="y", which="both", alpha=0.25)
    ax.legend()
    fig.savefig(OUT_PNG, dpi=250)
    fig.savefig(OUT_PDF)
    plt.close(fig)

    print(
        json.dumps(
            {
                "status": payload["status"],
                "best_effect_to_rmse": best["effect_to_group_cv_rmse"],
                "best_rmse_reduction_needed": best["rmse_reduction_factor_needed"],
                "all_pairs_fail": payload["gate"]["all_pairs_fail_5x_resolution"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
