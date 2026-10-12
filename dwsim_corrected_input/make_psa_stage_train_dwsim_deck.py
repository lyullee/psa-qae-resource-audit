"""Build steady, horizon-averaged DWSIM cases from the dynamic PSA membrane traces.

The membrane transfer fractions remain outputs of the packet-resolved Python
model.  DWSIM receives those fractions as Component Separator specifications
and independently checks stream thermodynamics, compression/cooling duties,
pressure states, and material closure for every uncertainty/hold-out case.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path

import numpy as np


PROJECT = Path(__file__).resolve().parents[2]
QAE = PROJECT / "10_TEA_LCA_Python" / "psa_qae"
RESULTS = QAE / "results"
TRAIN = RESULTS / os.environ.get("PSA_DWSIM_TRAIN_DIR", "stage_resolved_membrane_train")
SENSITIVITY = RESULTS / os.environ.get("PSA_DWSIM_SENSITIVITY_DIR", "pd_leakage_aging_sensitivity") / "PSA_PD_LEAKAGE_AGING_SENSITIVITY.json"
ODE_AUDIT = RESULTS / os.environ.get("PSA_DWSIM_ODE_DIR", "independent_ode_membrane_audit") / "PSA_INDEPENDENT_ODE_MEMBRANE_AUDIT.json"
TRAIN_TABLE = TRAIN / "Table_stage_train_dynamic_confirmation.csv"

if str(QAE) not in sys.path:
    sys.path.insert(0, str(QAE))

import psa_pd_leakage_aging_sensitivity as sensitivity  # noqa: E402
import psa_independent_ode_membrane_audit as ode_audit  # noqa: E402
import psa_stage_resolved_membrane_train as train_model  # noqa: E402


COMPONENTS = ("H2", "CO", "CO2", "N2", "CH4")


def safe_fraction(numerator: float, denominator: float) -> float:
    if denominator <= 1.0e-30:
        return 0.0
    return min(max(numerator / denominator, 0.0), 1.0)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    ode_result = json.loads(ODE_AUDIT.read_text(encoding="utf-8"))
    design = ode_result["revised_guard_design"]
    area_m2 = float(design["selected_rounded_pd_area_m2"])
    retention = float(design["permeance_retention"])
    selectivity = {
        key: float(value)
        for key, value in design["selected_effective_selectivity"].items()
    }

    with TRAIN_TABLE.open(encoding="utf-8", newline="") as handle:
        train_rows = {row["case_id"]: row for row in csv.DictReader(handle)}

    rows: list[dict[str, object]] = []
    for prefix, kind in (("corner", "uncertainty_corner"), ("holdout", "predeclared_interior_holdout")):
        for index in range(8):
            case_id = f"{prefix}_{index:02d}"
            state = train_rows[case_id]
            trace_path = TRAIN / "states" / f"{case_id}_traces.npz"
            with np.load(trace_path, allow_pickle=False) as archive:
                names = [str(value) for value in archive["components"]]
                feed = np.asarray(archive["surge_outlet_mol"], dtype=float)
            component_index = {name: idx for idx, name in enumerate(names)}
            duration_s = float(state["cycle_time_s"]) / (4.0 * sensitivity.strict.ADSORPTION_SUBSTEPS)
            elapsed_s = float(state["n_cycles"]) * float(state["cycle_time_s"])

            stage1_product, stage1_retentate, stage1_info = ode_audit.integrate_polymer(
                feed,
                duration_s,
            )
            stage2_product, stage2_retentate, stage2_info = ode_audit.integrate_pd(
                stage1_product,
                duration_s,
                area_m2=area_m2,
                retention=retention,
                selectivity=selectivity,
            )

            feed_total = feed.sum(axis=0)
            stage1_total = stage1_product.sum(axis=0)
            stage2_total = stage2_product.sum(axis=0)
            row: dict[str, object] = {
                "validation_kind": kind,
                "case_id": case_id,
                "temperature_K": 298.15,
                "raw_feed_pressure_Pa": 8.0e5,
                "membrane_feed_pressure_Pa": 20.0e5,
                "permeate_pressure_Pa": 1.0e5,
                "compressor_efficiency": 0.72,
                "elapsed_s": elapsed_s,
                "pd_area_m2": area_m2,
                "pd_permeance_retention": retention,
                "membrane_integration_method": "adaptive_DOP853_continuous_area",
                "python_stage2_balance_max_abs_mol": max(
                    stage1_info["mass_balance_max_abs_mol"],
                    stage2_info["mass_balance_max_abs_mol"],
                ),
                "python_isothermal_compression_power_W": (
                    train_model.isothermal_compression_power_w(
                        float(feed_total.sum()) / elapsed_s,
                        train_model.UPSTREAM_PRESSURE_PA,
                        train_model.CONCENTRATOR_FEED_PRESSURE_PA,
                    )
                    + train_model.isothermal_compression_power_w(
                        float(stage1_total.sum()) / elapsed_s,
                        train_model.CONCENTRATOR_PERMEATE_PRESSURE_PA,
                        train_model.PD_FEED_PRESSURE_PA,
                    )
                ),
            }
            for name in COMPONENTS:
                idx = component_index[name]
                row[f"feed_{name}_mol_s"] = float(feed_total[idx] / elapsed_s)
                row[f"stage1_permeate_fraction_{name}"] = safe_fraction(
                    float(stage1_total[idx]), float(feed_total[idx])
                )
                row[f"stage2_permeate_fraction_{name}"] = safe_fraction(
                    float(stage2_total[idx]), float(stage1_total[idx])
                )
                row[f"python_product_{name}_mol_s"] = float(stage2_total[idx] / elapsed_s)
                row[f"python_stage2_retentate_{name}_mol_s"] = float(
                    stage2_retentate[:, idx].sum() / elapsed_s
                )
            rows.append(row)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    print(f"WROTE={args.output}")
    print(f"CASES={len(rows)}")
    print(f"PD_AREA_M2={area_m2:.9g}")
    print(f"RETENTION={retention:.9g}")


if __name__ == "__main__":
    main()
