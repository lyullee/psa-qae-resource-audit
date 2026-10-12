"""Audit hydraulic consistency of the frozen PSA regeneration-tank policy.

This audit is deliberately separate from the inventory balance.  A component
ledger can close while the implied pressure routing is physically impossible.
The script compares the adsorption-bed product-manifold pressure, regeneration
tank set point, and the pressure assumed by the purge/pressurization boundary.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from psa_qae.psa_public_schedule_strict_uncertainty_ensemble import load_contract
from psa_qae.psa_thelen_va10_dynamic_validation import public_params


HERE = Path(__file__).resolve().parent
OUT = HERE / "results" / "pressure_consistency_audit_v1"
FULL_CUBE = (
    HERE
    / "results"
    / "literature_anchored_policy_full_6cell_cube_2000cm2"
    / "PSA_LITERATURE_ANCHORED_POLICY_FULL_6CELL_CUBE.json"
)


def main() -> None:
    source = json.loads(FULL_CUBE.read_text(encoding="utf-8"))
    p = public_params(load_contract(), n_cells=6, max_step_points=24)
    product_manifold_bar = float(p.P_high_bar - p.product_outlet_drop_bar)
    source_header_bar = float(p.P_high_bar)

    rows = []
    for row in source["rows"]:
        setpoint = float(row["tank_setpoint_bar"])
        minimum = float(row["min_tank_pressure_bar"])
        passive_fill_margin = product_manifold_bar - setpoint
        minimum_delivery_margin = minimum - source_header_bar
        rows.append(
            {
                "policy": row["policy"],
                "scenario": row["scenario"],
                "adsorber_high_pressure_bar": source_header_bar,
                "product_manifold_backpressure_bar": product_manifold_bar,
                "tank_setpoint_bar": setpoint,
                "minimum_tank_pressure_bar": minimum,
                "passive_fill_pressure_margin_bar": passive_fill_margin,
                "minimum_unboosted_delivery_margin_bar": minimum_delivery_margin,
                "passive_fill_possible_at_setpoint": bool(passive_fill_margin > 0.0),
                "unboosted_delivery_possible_at_minimum": bool(
                    minimum_delivery_margin >= 0.0
                ),
                "hydraulic_gate_without_booster": bool(
                    passive_fill_margin > 0.0 and minimum_delivery_margin >= 0.0
                ),
            }
        )

    selected = [row for row in rows if row["policy"] == "selected"]
    baseline = [row for row in rows if row["policy"] == "baseline"]
    payload = {
        "schema": "psa-pressure-consistency-audit/v1",
        "status": "inventory_ledger_passes_but_unboosted_hydraulic_gate_fails",
        "source": str(FULL_CUBE.relative_to(HERE)),
        "routing_contract": {
            "adsorber_high_pressure_bar": source_header_bar,
            "product_outlet_drop_bar": float(p.product_outlet_drop_bar),
            "product_manifold_backpressure_bar": product_manifold_bar,
            "current_regulated_product_manifold_behavior": (
                "purge and pressurization are computed from a constant-composition "
                "source and charged later to the component inventory ledger; the "
                "tank-to-bed and bed-to-tank hydraulic pressure differences are not "
                "integrated in that routing mode"
            ),
        },
        "rows": rows,
        "summary": {
            "case_count": len(rows),
            "hydraulic_pass_count_without_booster": int(
                sum(row["hydraulic_gate_without_booster"] for row in rows)
            ),
            "selected_pass_count_without_booster": int(
                sum(row["hydraulic_gate_without_booster"] for row in selected)
            ),
            "baseline_pass_count_without_booster": int(
                sum(row["hydraulic_gate_without_booster"] for row in baseline)
            ),
            "selected_passive_fill_margin_bar": float(
                min(row["passive_fill_pressure_margin_bar"] for row in selected)
            ),
            "selected_minimum_delivery_margin_bar": float(
                min(row["minimum_unboosted_delivery_margin_bar"] for row in selected)
            ),
            "selected_minimum_tank_pressure_bar": float(
                min(row["minimum_tank_pressure_bar"] for row in selected)
            ),
        },
        "decision": {
            "previous_7bar_unboosted_claim_valid": False,
            "required_correction": (
                "Either add and size a regeneration-gas booster or constrain the "
                "tank set point below the 6.2 bar product manifold and still boost "
                "tank withdrawal whenever tank pressure is below the 6.5 bar source header."
            ),
            "recommended_topology_for_rescreen": (
                "passive product-to-tank refill with set point <= 6.0 bar plus a "
                "tank-discharge booster to the 6.5 bar purge/pressurization header"
            ),
            "claim_boundary": (
                "The prior component ledger remains a valid mass-allocation result, "
                "but it does not by itself prove an uncompressed hydraulic connection."
            ),
        },
    }

    assert payload["summary"]["hydraulic_pass_count_without_booster"] == 0
    assert payload["summary"]["selected_passive_fill_margin_bar"] < 0.0
    assert payload["summary"]["selected_minimum_delivery_margin_bar"] < 0.0

    OUT.mkdir(parents=True, exist_ok=True)
    json_path = OUT / "PSA_PRESSURE_CONSISTENCY_AUDIT_V1.json"
    json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    summary = payload["summary"]
    md = f"""# PSA regeneration-tank pressure consistency audit

The frozen six-cell inventory ledger was checked against the pressures used by
the adsorption and regeneration boundaries.

- adsorption/source header: **{source_header_bar:.3f} bar**
- adsorption product-manifold backpressure: **{product_manifold_bar:.3f} bar**
- selected tank set point: **7.000 bar**
- selected passive-fill margin: **{summary['selected_passive_fill_margin_bar']:.3f} bar**
- selected minimum tank pressure: **{summary['selected_minimum_tank_pressure_bar']:.3f} bar**
- worst unboosted delivery margin: **{summary['selected_minimum_delivery_margin_bar']:.3f} bar**
- unboosted hydraulic passes: **{summary['hydraulic_pass_count_without_booster']}/{summary['case_count']}**

The component ledger closes, but an uncompressed 6.2-bar product manifold
cannot refill a 7.0-bar tank.  The tank also falls below the 6.5-bar pressure
assumed by the purge and pressurization source boundary.  The next operating
screen therefore uses passive refill at a tank set point no greater than 6.0
bar and explicitly treats tank discharge as a boosted service.
"""
    (OUT / "PSA_PRESSURE_CONSISTENCY_AUDIT_V1.md").write_text(md, encoding="utf-8")
    print(json.dumps({"output": str(json_path), "summary": summary}, indent=2))


if __name__ == "__main__":
    main()
