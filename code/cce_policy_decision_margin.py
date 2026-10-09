"""Quantify engineering and statistical margins of the frozen recycle choice."""

from __future__ import annotations

import csv
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RESULTS = ROOT / "10_TEA_LCA_Python" / "results" / "pycharm_publication_enhancement"
PROTOCOL = RESULTS / "PSA_QAE_CCE_PRIMARY_CASE_PROTOCOL.json"
SELECTION = RESULTS / "PSA_QAE_CONTINUOUS_POLICY_SELECTION.json"
DISCREPANCY = RESULTS / "QAE_SURROGATE_MODEL_DISCREPANCY_BOUNDARY.json"
OUT = RESULTS / "PSA_QAE_CCE_POLICY_DECISION_MARGIN"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    protocol = load(PROTOCOL)
    selection = load(SELECTION)
    discrepancy = load(DISCREPANCY)
    policies = [float(value) for value in protocol["outer_decision"]["candidate_values"]]
    target = float(protocol["chance_constraint_target"])
    probabilities = {
        float(key): float(value)
        for key, value in selection["reference_probability_by_policy"].items()
    }
    selected = float(selection["true_selected_policy"])
    methods = {
        row["method"]: float(row["rmse_across_policy_estimates"])
        for row in selection["method_summary"]
    }
    residual_half_width = 0.5 * (
        float(discrepancy["discrepancy_stress_probability_p975"])
        - float(discrepancy["discrepancy_stress_probability_p025"])
    )

    rows = []
    for policy in policies:
        p_event = probabilities[policy]
        probability_margin = p_event - target
        external_fraction = 1.0 - policy
        rows.append(
            {
                "policy_recycle_fraction": policy,
                "selected": policy == selected,
                "reference_event_probability": p_event,
                "probability_margin_to_target": probability_margin,
                "feasible": p_event >= target,
                "external_product_fraction_of_gross_product": external_fraction,
                "internal_recycle_fraction_of_gross_product": policy,
                "internal_recycle_per_external_product": policy / external_fraction,
                "incremental_internal_allocation_vs_selected_gross_fraction": policy - selected,
                "incremental_external_product_vs_selected_gross_fraction": selected - policy,
                "absolute_margin_over_mc_rmse": abs(probability_margin) / methods["MC_same_query"],
                "absolute_margin_over_rqmc_rmse": abs(probability_margin) / methods["Sobol_RQMC"],
                "absolute_margin_over_mlae_rmse": abs(probability_margin) / methods["MLAE_0.00"],
                "absolute_margin_over_residual_stress_half_width": abs(probability_margin)
                / residual_half_width,
            }
        )

    failed = [row for row in rows if not row["feasible"]]
    nearest_failed = min(failed, key=lambda row: abs(float(row["probability_margin_to_target"])))
    payload = {
        "schema": "psa-qae-cce-policy-decision-margin/v1",
        "status": "surrogate_level_engineering_allocation_and_decision_margin_not_economic_optimum",
        "decision_rule": protocol["outer_decision"]["rule"],
        "selected_policy": selected,
        "target_probability": target,
        "rows": rows,
        "nearest_failed_policy": nearest_failed["policy_recycle_fraction"],
        "nearest_failed_probability_shortfall": abs(float(nearest_failed["probability_margin_to_target"])),
        "nearest_failed_shortfall_over_rqmc_rmse": nearest_failed["absolute_margin_over_rqmc_rmse"],
        "nearest_failed_shortfall_over_mlae_rmse": nearest_failed["absolute_margin_over_mlae_rmse"],
        "nearest_failed_shortfall_over_residual_stress_half_width": nearest_failed[
            "absolute_margin_over_residual_stress_half_width"
        ],
        "selected_external_product_fraction": 1.0 - selected,
        "selected_internal_recycle_per_external_product": selected / (1.0 - selected),
        "residual_stress_half_width": residual_half_width,
        "interpretation": (
            "Within the frozen surrogate, estimator uncertainty is small relative to the nearest chance-constraint classification margin. "
            "The outer decision therefore does not benefit from estimator precision below the present RQMC scale. "
            "This is a product-split allocation and decision-margin calculation, not compressor duty, operating cost, plant profit, or global optimization."
        ),
        "limitations": [
            "The product split is exact bookkeeping, but no compressor, tank-pressure, or monetary model is available.",
            "Reference probabilities are conditional on the 32-run affine surrogate and empirical copula.",
            "The residual-stress half-width is not a calibrated plant model-discrepancy posterior.",
            "Independent process-model changes exceed these estimator-scale margins elsewhere in the evidence package.",
        ],
        "sources": [PROTOCOL.name, SELECTION.name, DISCREPANCY.name],
    }
    OUT.with_suffix(".json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    with OUT.with_suffix(".csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    lines = [
        "# Frozen recycle-policy engineering and decision margin",
        "",
        "The primary rule chooses the largest recycle candidate whose joint-event probability is at least 0.50. Product-split quantities are exact bookkeeping identities. They are reported to give the outer decision a concrete process interpretation without inventing compressor or economic data.",
        "",
        "| recycle | event probability | margin to 0.50 | feasible | external product / gross | recycle / external product | |margin| / RQMC RMSE | |margin| / residual-stress half-width |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row['policy_recycle_fraction']:.3f} | {row['reference_event_probability']:.6f} | "
            f"{row['probability_margin_to_target']:+.6f} | {row['feasible']} | "
            f"{row['external_product_fraction_of_gross_product']:.3f} | "
            f"{row['internal_recycle_per_external_product']:.4f} | "
            f"{row['absolute_margin_over_rqmc_rmse']:.2f} | "
            f"{row['absolute_margin_over_residual_stress_half_width']:.2f} |"
        )
    lines += [
        "",
        f"The nearest failed candidate is `{nearest_failed['policy_recycle_fraction']:.3f}`. Its probability shortfall is `{payload['nearest_failed_probability_shortfall']:.6f}`, or `{payload['nearest_failed_shortfall_over_rqmc_rmse']:.2f}` RQMC RMSE, `{payload['nearest_failed_shortfall_over_mlae_rmse']:.2f}` noiseless-MLAE RMSE, and `{payload['nearest_failed_shortfall_over_residual_stress_half_width']:.2f}` residual-stress half-widths. Estimator-scale refinement therefore does not change the frozen surrogate decision.",
        "",
        payload["interpretation"],
    ]
    OUT.with_suffix(".md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
