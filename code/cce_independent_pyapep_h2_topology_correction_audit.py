"""Audit the corrected pyAPEP product-end topology and recovery boundary.

The original wrapper connected product-gas pressurisation at the feed end and
classified recovery against adsorption feed only despite external high-purity
makeup.  This audit supersedes that result with a corrected three-policy
short-horizon screen and a 450-cycle baseline stress control.  Neither tier is
called a CSS validation.
"""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
RESULTS = ROOT / "results" / "pycharm_publication_enhancement"
SHORT = RESULTS / "PSA_QAE_CCE_INDEPENDENT_PYAPEP_H2_RECYCLE_DIRECTION_QUICK_V3.json"
LONG = RESULTS / "PSA_QAE_CCE_INDEPENDENT_PYAPEP_H2_RECYCLE_LONG_HORIZON_RAW.json"
SUPERSEDED = RESULTS / "PSA_QAE_CCE_INDEPENDENT_PYAPEP_H2_RECYCLE_VALIDATION_SUPERSEDED_V1.json"
PREFIX = RESULTS / "PSA_QAE_CCE_INDEPENDENT_PYAPEP_H2_RECYCLE_VALIDATION"

PURITY_THRESHOLD = 0.9998
RECOVERY_THRESHOLD = 0.789
CSS_THRESHOLD = 1.0e-3


def compact(row: dict, tier: str) -> dict:
    return {
        "tier": tier,
        "adsorbent": row["adsorbent"],
        "n_nodes": int(row["n_nodes"]),
        "policy_recycle_fraction": float(row["policy_recycle_fraction"]),
        "cycles_completed": int(row["cycles_completed"]),
        "css_residual_final": float(row["css_residual_final"]),
        "css_gate": bool(row["css_gate"]),
        "h2_product": float(row["h2_product"]),
        "h2_recovery_external_boundary": float(row["h2_recovery_external_boundary"]),
        "h2_recovery_adsorption_feed_proxy": float(row["h2_recovery_adsorption_feed_proxy"]),
        "tank_supply_fraction_total": float(row["tank_supply_fraction_total"]),
        "product_tank_self_sufficient": bool(row["product_tank_self_sufficient"]),
        "joint_event": bool(row["joint_event"]),
        "strict_same_policy_event_gate": bool(row["strict_same_policy_event_gate"]),
        "cycle_mass_balance_relative": float(row["cycle_mass_balance_relative"]),
    }


def main() -> None:
    short = json.loads(SHORT.read_text(encoding="utf-8"))
    long_raw = json.loads(LONG.read_text(encoding="utf-8"))
    superseded = json.loads(SUPERSEDED.read_text(encoding="utf-8"))
    if short["schema"] != "cce-independent-pyapep-h2-recycle-validation/v3":
        raise RuntimeError("short screen must use corrected v3 semantics")
    short_rows = short["runs"]
    long_rows = long_raw["runs"]
    if len(short_rows) != 3 or len(long_rows) != 1:
        raise RuntimeError("expected three short policy rows and one long baseline row")
    if sorted(round(float(row["policy_recycle_fraction"]), 3) for row in short_rows) != [0.420, 0.427, 0.430]:
        raise RuntimeError("short screen policy grid changed")
    if any(row["css_gate"] or row["joint_event"] or row["product_tank_self_sufficient"] for row in short_rows + long_rows):
        raise RuntimeError("corrected stress controls unexpectedly passed a declared gate")

    short_compact = [compact(row, "15-cycle policy-direction screen") for row in short_rows]
    long_row = long_rows[0]
    long_compact = compact(long_row, "450-cycle baseline stress control")
    policies = np.asarray([row["policy_recycle_fraction"] for row in short_compact], dtype=float)
    recoveries = np.asarray([row["h2_recovery_external_boundary"] for row in short_compact])
    purities = np.asarray([row["h2_product"] for row in short_compact])
    tank_supply = np.asarray([row["tank_supply_fraction_total"] for row in short_compact])

    payload = {
        "schema": "cce-independent-pyapep-h2-topology-correction-audit/v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "corrected_product_end_topology_stress_test_not_css_or_external_selection_validation",
        "solver": short["solver"],
        "frozen_protocol": short["frozen_protocol"],
        "corrections": [
            {
                "item": "pressurisation connection",
                "superseded": "product gas entered at the feed end",
                "corrected": "product gas enters at the light-product end, matching the declared product-tank topology",
            },
            {
                "item": "recovery boundary",
                "superseded": "external product H2 divided only by adsorption-feed H2",
                "corrected": "external product H2 divided by all external H2 entering adsorption, purge, and pressurisation",
            },
            {
                "item": "operability",
                "superseded": "source-gas makeup was recorded but not used as a validation gate",
                "corrected": "product-tank supply fraction and self-sufficiency are explicit, with strict validation requiring self-sufficiency",
            },
        ],
        "superseded_artifact": {
            "path": SUPERSEDED.name,
            "schema": superseded.get("schema"),
            "run_count": superseded.get("run_count"),
            "status": "retained_for_audit_trail_not_admissible_evidence",
        },
        "short_policy_screen": {
            "purpose": "direction and boundary check before CSS; not a converged process result",
            "rows": short_compact,
            "purity_range": [float(purities.min()), float(purities.max())],
            "external_boundary_recovery_range": [float(recoveries.min()), float(recoveries.max())],
            "tank_supply_fraction_range": [float(tank_supply.min()), float(tank_supply.max())],
            "recovery_direction_0p420_gt_0p427_gt_0p430": bool(np.all(np.diff(recoveries) < 0.0)),
        },
        "long_horizon_control": {
            "purpose": "test whether the corrected 0.420 baseline approaches the frozen event and CSS under an extended fixed horizon",
            "row": long_compact,
            "purity_shortfall": PURITY_THRESHOLD - long_compact["h2_product"],
            "recovery_shortfall": RECOVERY_THRESHOLD - long_compact["h2_recovery_external_boundary"],
            "css_excess": long_compact["css_residual_final"] - CSS_THRESHOLD,
            "css_history": long_row["css_history"],
        },
        "gates": {
            "all_short_rows_fail_joint_event": all(not row["joint_event"] for row in short_compact),
            "all_short_rows_fail_css": all(not row["css_gate"] for row in short_compact),
            "all_short_rows_fail_tank_self_sufficiency": all(
                not row["product_tank_self_sufficient"] for row in short_compact
            ),
            "long_row_fails_joint_event": not long_compact["joint_event"],
            "long_row_fails_css": not long_compact["css_gate"],
            "long_row_fails_tank_self_sufficiency": not long_compact["product_tank_self_sufficient"],
            "counts_as_same_policy_css_validation": False,
            "counts_as_external_h2_selection_validation": False,
        },
        "interpretation": (
            "Correcting the product-end connection removes the unphysical low-H2 product reported by the superseded wrapper, "
            "but the finite tank supplies only a few percent of purge/pressurisation demand. Even the 450-cycle 0.420 control "
            "does not satisfy the declared CSS, purity, recovery, or tank-self-sufficiency gates. The result is a transparent "
            "topology-feasibility stress test and cannot be used as a CSS-converged same-policy negative control."
        ),
        "claim_boundary": [
            "The pyAPEP column solver is external; the schedule, tank, recycle, and makeup wrapper are project code.",
            "The uniform 5A single-column schedule does not reproduce the layered, alternating-bed primary process.",
            "The 15-cycle policy screen is directional only, and the 450-cycle control remains outside the CSS gate.",
            "No corrected row validates the frozen event or the local 0.420 policy selection.",
        ],
        "qpu_submission": False,
    }
    PREFIX.with_suffix(".json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    flat_rows = short_compact + [long_compact]
    with PREFIX.with_suffix(".csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(flat_rows[0]))
        writer.writeheader()
        writer.writerows(flat_rows)

    lines = [
        "# Corrected independent pyAPEP H2 topology stress test",
        "",
        "The previous wrapper connected product-gas pressurisation at the feed end and used an adsorption-feed-only recovery proxy even when external high-purity makeup entered the system. That result is retained only as a superseded audit artifact. The corrected wrapper injects purge and pressurisation gas at the light-product end, counts all external H2 in the recovery denominator, and reports product-tank self-sufficiency.",
        "",
        "| tier | nodes | recycle | cycles | CSS residual | H2 purity | external-boundary recovery | tank supply fraction | joint event | tank self-sufficient |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in flat_rows:
        lines.append(
            f"| {row['tier']} | {row['n_nodes']} | {row['policy_recycle_fraction']:.3f} | {row['cycles_completed']} | "
            f"{row['css_residual_final']:.6g} | {row['h2_product']:.6f} | {row['h2_recovery_external_boundary']:.6f} | "
            f"{row['tank_supply_fraction_total']:.4f} | {row['joint_event']} | {row['product_tank_self_sufficient']} |"
        )
    lines += [
        "",
        f"At 450 cycles, the corrected 0.420 control has H2 purity `{long_compact['h2_product']:.6f}`, external-boundary recovery `{long_compact['h2_recovery_external_boundary']:.6f}`, tank supply fraction `{long_compact['tank_supply_fraction_total']:.4f}`, and CSS residual `{long_compact['css_residual_final']:.6g}`. It fails all four declared gates.",
        "",
        f"**Interpretation.** {payload['interpretation']}",
    ]
    PREFIX.with_suffix(".md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    fig, axes = plt.subplots(2, 2, figsize=(10.6, 7.8), constrained_layout=True)
    axes[0, 0].plot(policies, purities, marker="o", color="#2563eb")
    axes[0, 0].axhline(PURITY_THRESHOLD, color="#c00000", linestyle="--", label="frozen threshold")
    axes[0, 0].set(xlabel="recycle fraction", ylabel="H2 purity", title="(a) Corrected 15-cycle policy screen")
    axes[0, 0].legend(fontsize=8)

    axes[0, 1].plot(policies, recoveries, marker="o", color="#059669", label="external-boundary recovery")
    axes[0, 1].plot(policies, tank_supply, marker="s", color="#7c3aed", label="tank supply fraction")
    axes[0, 1].axhline(RECOVERY_THRESHOLD, color="#c00000", linestyle="--", label="recovery threshold")
    axes[0, 1].set(xlabel="recycle fraction", ylabel="fraction", title="(b) Recovery and tank feasibility")
    axes[0, 1].legend(fontsize=8)

    history = payload["long_horizon_control"]["css_history"]
    cycles = [row["cycle"] for row in history]
    residuals = [row["css_residual"] for row in history]
    axes[1, 0].semilogy(cycles, residuals, color="#d97706")
    axes[1, 0].axhline(CSS_THRESHOLD, color="#c00000", linestyle="--", label="CSS gate")
    axes[1, 0].set(xlabel="cycle", ylabel="CSS residual", title="(c) Corrected 0.420 long-horizon control")
    axes[1, 0].legend(fontsize=8)

    labels = ["purity\nshortfall", "recovery\nshortfall", "tank supply"]
    values = [
        PURITY_THRESHOLD - long_compact["h2_product"],
        RECOVERY_THRESHOLD - long_compact["h2_recovery_external_boundary"],
        long_compact["tank_supply_fraction_total"],
    ]
    axes[1, 1].bar(labels, values, color=["#2563eb", "#059669", "#7c3aed"])
    axes[1, 1].set(ylabel="fraction", title="(d) 450-cycle decision boundary")
    axes[1, 1].text(0.02, 0.96, "all validation gates fail", transform=axes[1, 1].transAxes, va="top")

    for axis in axes.flat:
        axis.grid(alpha=0.22)
    fig.suptitle("Corrected pyAPEP product-end topology and external recovery boundary")
    fig.savefig(PREFIX.parent / f"{PREFIX.name}_FIGURE.png", dpi=220)
    fig.savefig(PREFIX.parent / f"{PREFIX.name}_FIGURE.pdf")
    plt.close(fig)
    print(json.dumps({"status": payload["status"], "short_rows": len(short_rows), "long_rows": len(long_rows)}, indent=2))


if __name__ == "__main__":
    main()
