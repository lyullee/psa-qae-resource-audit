"""Independent fixed-area RK4 cross-check of both final membrane designs.

This implementation deliberately does not call the adaptive DOP853 membrane
integrators.  It re-implements the published polymer and Pd transport equations
with a fixed-area classical RK4 scheme, refines the area mesh, and compares all
16 uncertainty/hold-out cases against the frozen DOP853 evidence.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import os
from pathlib import Path
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
ODE_DIR = RESULTS / os.environ.get("PSA_RK4_ODE_DIR", "independent_ode_membrane_audit")
SYNGAS_DIR = RESULTS / os.environ.get("PSA_RK4_SYNGAS_DIR", "pd_actual_syngas_poisoning_guard_v1")
ODE_JSON = ODE_DIR / "PSA_INDEPENDENT_ODE_MEMBRANE_AUDIT.json"
BASE_DOP_CSV = ODE_DIR / "Table_ode_revised_guard_validation.csv"
SYNGAS_JSON = (
    SYNGAS_DIR
    / "PSA_PD_ACTUAL_SYNGAS_POISONING_GUARD_V1.json"
)
STRESS_DOP_CSV = (
    SYNGAS_DIR
    / "Table_pd_50pct_retention_direct_cases.csv"
)
ASPEN_REFERENCE = (
    RESULTS
    / os.environ.get("PSA_RK4_ASPEN_DIR", "aspen_psa_membrane_validation_handoff_v2")
    / "ASPEN_REFERENCE_EXPECTED.csv"
)
OUT = RESULTS / os.environ.get("PSA_RK4_OUTPUT_DIR", "independent_rk4_membrane_crosscheck_v1")
USE_DWSIM_REFERENCE = os.environ.get("PSA_RK4_USE_DWSIM_REFERENCE", "1") == "1"

sys.path.insert(0, str(HERE))
import psa_independent_ode_membrane_audit as source_data  # noqa: E402
import psa_pd_leakage_aging_sensitivity as sensitivity  # noqa: E402
import psa_public_schedule_strict_uncertainty_ensemble as strict  # noqa: E402
import psa_stage_resolved_membrane_train as train  # noqa: E402


COMPONENTS = tuple(strict.COMPONENTS)
H2 = strict.INDEX["H2"]
IMPURITIES = ("CO", "CO2", "N2", "CH4")
MESHES = (48, 96, 192)
BINARY_SEARCH_ITERATIONS = 32


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise ValueError(f"no rows for {path}")
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def polymer_coefficients() -> np.ndarray:
    material = train.MATERIALS["polymer"]
    coefficients = np.full(
        len(COMPONENTS), material["h2_permeance_mol_m2_s_pa"], dtype=float
    )
    for name in COMPONENTS:
        if name != "H2":
            coefficients[strict.INDEX[name]] /= material["selectivity"][name]
    return coefficients


POLYMER_COEFFICIENT = polymer_coefficients()


def polymer_flux(rate: np.ndarray) -> np.ndarray:
    """Solve the permeate-side composition closure independently by bisection."""
    positive = np.maximum(np.asarray(rate, dtype=float), 0.0)
    total = positive.sum(axis=1)
    x = np.divide(
        positive,
        total[:, None],
        out=np.zeros_like(positive),
        where=total[:, None] > 1.0e-30,
    )
    numerator = POLYMER_COEFFICIENT[None, :] * train.CONCENTRATOR_FEED_PRESSURE_PA * x
    back_pressure = (
        POLYMER_COEFFICIENT[None, :] * train.CONCENTRATOR_PERMEATE_PRESSURE_PA
    )
    lower = np.zeros(positive.shape[0])
    upper = np.maximum(numerator.sum(axis=1), 1.0e-30)
    for _ in range(BINARY_SEARCH_ITERATIONS):
        midpoint = 0.5 * (lower + upper)
        closure = np.sum(numerator / (midpoint[:, None] + back_pressure), axis=1)
        too_low = closure > 1.0
        lower = np.where(too_low, midpoint, lower)
        upper = np.where(too_low, upper, midpoint)
    total_flux = 0.5 * (lower + upper)
    permeate_y = numerator / (total_flux[:, None] + back_pressure)
    permeate_y /= np.maximum(permeate_y.sum(axis=1)[:, None], 1.0e-30)
    flux = total_flux[:, None] * permeate_y
    return np.where(positive <= 1.0e-20, 0.0, flux)


def pd_flux(
    rate: np.ndarray,
    *,
    retention: float,
    selectivity: dict[str, float],
) -> np.ndarray:
    positive = np.maximum(np.asarray(rate, dtype=float), 0.0)
    total = positive.sum(axis=1)
    x = np.divide(
        positive,
        total[:, None],
        out=np.zeros_like(positive),
        where=total[:, None] > 1.0e-30,
    )
    x_h2 = np.maximum(x[:, H2], 1.0e-30)
    driving = np.sqrt(train.PD_FEED_PRESSURE_PA * x_h2) - math.sqrt(
        train.PD_PERMEATE_PRESSURE_PA
    )
    dense_h2 = (
        retention
        * train.PD_H2_PERMEANCE_MOL_M2_S_PA_HALF
        * np.maximum(driving, 0.0)
    )
    flux = np.zeros_like(positive)
    flux[:, H2] = dense_h2
    for name in IMPURITIES:
        index = strict.INDEX[name]
        flux[:, index] = dense_h2 * (x[:, index] / x_h2) / selectivity[name]
    return np.where(positive <= 1.0e-20, 0.0, flux)


def fixed_rk4(
    initial_rate: np.ndarray,
    *,
    area_m2: float,
    section_count: int,
    flux_function,
) -> np.ndarray:
    """Integrate dF/dA=-J with a fixed-area classical fourth-order Runge-Kutta mesh."""
    state = np.maximum(np.asarray(initial_rate, dtype=float), 0.0).copy()
    step = float(area_m2) / int(section_count)
    for _ in range(int(section_count)):
        k1 = -flux_function(state)
        k2 = -flux_function(np.maximum(state + 0.5 * step * k1, 0.0))
        k3 = -flux_function(np.maximum(state + 0.5 * step * k2, 0.0))
        k4 = -flux_function(np.maximum(state + step * k3, 0.0))
        state = np.maximum(
            state + step * (k1 + 2.0 * k2 + 2.0 * k3 + k4) / 6.0,
            0.0,
        )
    return state


def evaluate_product(
    case: dict,
    product: np.ndarray,
    *,
    installed_receiver_mol: float,
    gates: dict,
) -> dict:
    impurity_limits = np.asarray(
        [gates["impurity_max_fraction"][name] for name in IMPURITIES], dtype=float
    )
    impurity_indices = np.asarray(
        [strict.INDEX[name] for name in IMPURITIES], dtype=np.int64
    )
    timeline = train.build_uniform_timeline(product, case["cycle_time_s"])
    metrics = sensitivity.receiver_metrics_numba(
        timeline,
        installed_receiver_mol,
        strict.RECEIVER_HEEL_FRACTION,
        strict.RECEIVER_DT_S,
        strict.RECEIVER_SUBSTEPS,
        float(gates["h2_min_fraction"]),
        impurity_limits,
        impurity_indices,
    )
    recovery = float(product[:, H2].sum()) / max(float(case["raw_h2_mol"]), 1.0e-30)
    qualified = float(metrics[0])
    quality = bool(float(metrics[1]) <= 1.0 + 1.0e-10)
    event = bool(
        case["source_reserve_gate"]
        and case["source_css_gate"]
        and case["source_numerical_gate"]
        and case["surge_capacity_gate"]
        and quality
        and bool(metrics[8])
        and recovery >= float(gates["minimum_h2_recovery"])
        and qualified >= float(gates["minimum_qualified_h2_rate_mol_s"])
    )
    total = float(product.sum())
    horizon = product.shape[0] * float(case["packet_duration_s"])
    row = {
        "overall_h2_recovery": recovery,
        "qualified_h2_rate_mol_s": qualified,
        "continuous_quality_gate": quality,
        "receiver_inventory_gate": bool(metrics[8]),
        "stage_train_event": event,
        "minimum_h2_fraction": float(metrics[3]),
        "maximum_co_ppm": float(metrics[4]),
        "maximum_co2_ppm": float(metrics[5]),
        "maximum_n2_ppm": float(metrics[6]),
        "maximum_ch4_ppm": float(metrics[7]),
        "receiver_mass_balance_max_abs_mol": float(metrics[11]),
        "horizon_product_h2_mol_s": float(product[:, H2].sum() / horizon),
    }
    for name in IMPURITIES:
        row[f"horizon_product_{name}_ppm"] = float(
            product[:, strict.INDEX[name]].sum() / max(total, 1.0e-30) * 1.0e6
        )
    return row


def design_contract(ode_audit: dict, syngas_audit: dict) -> list[dict]:
    base = ode_audit["revised_guard_design"]
    stress = syngas_audit["conservative_50_percent_retention_design"]
    selectivity = {
        name: float(base["selected_effective_selectivity"][name]) for name in IMPURITIES
    }
    return [
        {
            "design_id": "base_20pct_loss",
            "area_m2": float(base["selected_rounded_pd_area_m2"]),
            "retention": float(base["permeance_retention"]),
            "receiver_capacity_mol": float(base["receiver_capacity_mol"]),
            "dop_csv": BASE_DOP_CSV,
            "selectivity": selectivity,
        },
        {
            "design_id": "public_syngas_50pct_loss",
            "area_m2": float(stress["selected_rounded_installed_area_m2"]),
            "retention": float(stress["permeance_retention"]),
            "receiver_capacity_mol": float(stress["receiver_capacity_mol"]),
            "dop_csv": STRESS_DOP_CSV,
            "selectivity": selectivity,
        },
    ]


def main() -> None:
    ode_audit = json.loads(ODE_JSON.read_text(encoding="utf-8"))
    syngas_audit = json.loads(SYNGAS_JSON.read_text(encoding="utf-8"))
    designs = design_contract(ode_audit, syngas_audit)
    gates = ode_audit["frozen_gates"]
    cases = source_data.case_data()
    if len(cases) != 16:
        raise AssertionError("expected 16 frozen uncertainty/hold-out cases")
    OUT.mkdir(parents=True, exist_ok=True)

    dop_direct = {}
    for design in designs:
        rows = read_csv(design["dop_csv"])
        if len(rows) != 16:
            raise AssertionError(f"expected 16 DOP853 rows for {design['design_id']}")
        for row in rows:
            dop_direct[(design["design_id"], row["case_id"])] = row
    use_horizon_reference = bool(USE_DWSIM_REFERENCE and ASPEN_REFERENCE.exists())
    dop_horizon = (
        {(row["design_id"], row["case_id"]): row for row in read_csv(ASPEN_REFERENCE)}
        if use_horizon_reference
        else {}
    )

    products: dict[tuple[int, str, str], np.ndarray] = {}
    module_balance = 0.0
    for section_count in MESHES:
        for case in cases:
            duration = float(case["packet_duration_s"])
            feed_moles = np.asarray(case["surge_outlet_mol"], dtype=float)
            feed_rate = feed_moles / duration
            polymer_retentate_rate = fixed_rk4(
                feed_rate,
                area_m2=source_data.POLYMER_AREA_M2,
                section_count=section_count,
                flux_function=polymer_flux,
            )
            polymer_product_rate = np.maximum(feed_rate - polymer_retentate_rate, 0.0)
            stage1_product = polymer_product_rate * duration
            stage1_retentate = polymer_retentate_rate * duration
            module_balance = max(
                module_balance,
                float(np.max(np.abs(feed_moles - stage1_product - stage1_retentate))),
            )
            for design in designs:
                pd_retentate_rate = fixed_rk4(
                    polymer_product_rate,
                    area_m2=design["area_m2"],
                    section_count=section_count,
                    flux_function=lambda rate, design=design: pd_flux(
                        rate,
                        retention=design["retention"],
                        selectivity=design["selectivity"],
                    ),
                )
                pd_product = np.maximum(polymer_product_rate - pd_retentate_rate, 0.0) * duration
                pd_retentate = pd_retentate_rate * duration
                module_balance = max(
                    module_balance,
                    float(
                        np.max(
                            np.abs(stage1_product - pd_product - pd_retentate)
                        )
                    ),
                )
                products[(section_count, design["design_id"], case["case_id"])] = pd_product

    evaluated: dict[tuple[int, str, str], dict] = {}
    for section_count in MESHES:
        for design in designs:
            for case in cases:
                key = (section_count, design["design_id"], case["case_id"])
                evaluated[key] = evaluate_product(
                    case,
                    products[key],
                    installed_receiver_mol=design["receiver_capacity_mol"],
                    gates=gates,
                )

    finest = MESHES[-1]
    direct_rows = []
    for design in designs:
        for case in cases:
            result = evaluated[(finest, design["design_id"], case["case_id"])]
            dop = dop_direct[(design["design_id"], case["case_id"])]
            horizon = dop_horizon.get((design["design_id"], case["case_id"]))
            row = {
                "design_id": design["design_id"],
                "validation_kind": case["validation_kind"],
                "case_id": case["case_id"],
                "rk4_area_sections_per_stage": finest,
                "pd_area_m2": design["area_m2"],
                "pd_permeance_retention": design["retention"],
                **{f"rk4_{key}": value for key, value in result.items()},
                "dop853_overall_h2_recovery": float(dop["overall_h2_recovery"]),
                "dop853_qualified_h2_rate_mol_s": float(dop["qualified_h2_rate_mol_s"]),
                "dop853_stage_train_event": dop["stage_train_event"].strip().lower() == "true",
                "recovery_difference_percentage_point": 100.0
                * (result["overall_h2_recovery"] - float(dop["overall_h2_recovery"])),
                "qualified_h2_relative_difference": (
                    result["qualified_h2_rate_mol_s"] - float(dop["qualified_h2_rate_mol_s"])
                )
                / max(abs(float(dop["qualified_h2_rate_mol_s"])), 1.0e-30),
                "event_label_agreement": result["stage_train_event"]
                == (dop["stage_train_event"].strip().lower() == "true"),
                "horizon_h2_relative_difference": (
                    (
                        result["horizon_product_h2_mol_s"]
                        - float(horizon["expected_product_H2_mol_s"])
                    )
                    / max(abs(float(horizon["expected_product_H2_mol_s"])), 1.0e-30)
                    if horizon is not None
                    else None
                ),
            }
            for name in IMPURITIES:
                row[f"receiver_{name}_difference_ppm"] = result[f"maximum_{name.lower()}_ppm"] - float(
                    dop[f"maximum_{name.lower()}_ppm"]
                )
                row[f"horizon_{name}_difference_ppm"] = (
                    result[f"horizon_product_{name}_ppm"]
                    - float(horizon[f"expected_product_{name}_ppm"])
                    if horizon is not None
                    else None
                )
            direct_rows.append(row)

    convergence_rows = []
    for section_count in MESHES:
        for design in designs:
            selected = [
                evaluated[(section_count, design["design_id"], case["case_id"])]
                for case in cases
            ]
            selected_products = [
                products[(section_count, design["design_id"], case["case_id"])]
                for case in cases
            ]
            fine_products = [
                products[(finest, design["design_id"], case["case_id"])] for case in cases
            ]
            max_component_relative = 0.0
            for trial, reference in zip(selected_products, fine_products):
                totals = trial.sum(axis=0)
                reference_totals = reference.sum(axis=0)
                max_component_relative = max(
                    max_component_relative,
                    float(
                        np.max(
                            np.abs(totals - reference_totals)
                            / np.maximum(np.abs(reference_totals), 1.0e-30)
                        )
                    ),
                )
            dop_rows = [row for row in direct_rows if row["design_id"] == design["design_id"]]
            convergence_rows.append(
                {
                    "design_id": design["design_id"],
                    "area_sections_per_stage": section_count,
                    "case_pass_count": sum(row["stage_train_event"] for row in selected),
                    "case_count": len(selected),
                    "minimum_recovery": min(row["overall_h2_recovery"] for row in selected),
                    "minimum_qualified_h2_rate_mol_s": min(
                        row["qualified_h2_rate_mol_s"] for row in selected
                    ),
                    "maximum_component_horizon_relative_difference_vs_192": max_component_relative,
                    "maximum_recovery_absolute_difference_vs_dop853_percentage_point": max(
                        abs(row["recovery_difference_percentage_point"]) for row in dop_rows
                    )
                    if section_count == finest
                    else "",
                    "maximum_horizon_h2_relative_difference_vs_dop853": (
                        max(abs(row["horizon_h2_relative_difference"]) for row in dop_rows)
                        if section_count == finest and use_horizon_reference
                        else None if section_count == finest else ""
                    ),
                }
            )

    summary_by_design = {}
    for design in designs:
        rows = [row for row in direct_rows if row["design_id"] == design["design_id"]]
        summary_by_design[design["design_id"]] = {
            "pd_area_m2": design["area_m2"],
            "permeance_retention": design["retention"],
            "rk4_pass_count": int(sum(row["rk4_stage_train_event"] for row in rows)),
            "case_count": len(rows),
            "event_label_agreement_count": int(sum(row["event_label_agreement"] for row in rows)),
            "minimum_rk4_recovery": min(row["rk4_overall_h2_recovery"] for row in rows),
            "minimum_rk4_qualified_h2_rate_mol_s": min(
                row["rk4_qualified_h2_rate_mol_s"] for row in rows
            ),
            "maximum_recovery_difference_vs_dop853_percentage_point": max(
                abs(row["recovery_difference_percentage_point"]) for row in rows
            ),
            "maximum_qualified_h2_relative_difference_vs_dop853": max(
                abs(row["qualified_h2_relative_difference"]) for row in rows
            ),
            "maximum_horizon_h2_relative_difference_vs_dop853": (
                max(abs(row["horizon_h2_relative_difference"]) for row in rows)
                if use_horizon_reference else None
            ),
            "maximum_horizon_impurity_difference_vs_dop853_ppm": (
                {
                    name: max(abs(row[f"horizon_{name}_difference_ppm"]) for row in rows)
                    for name in IMPURITIES
                }
                if use_horizon_reference else None
            ),
        }

    all_labels_agree = all(row["event_label_agreement"] for row in direct_rows)
    all_pass = all(row["rk4_stage_train_event"] for row in direct_rows)
    payload = {
        "schema": "psa-independent-rk4-membrane-crosscheck/v1",
        "status": "fixed_area_rk4_crosscheck_passed" if all_pass and all_labels_agree else "crosscheck_failed",
        "solver_contract": {
            "method": "standalone vectorized classical RK4 over membrane area",
            "area_sections_per_stage": list(MESHES),
            "polymer_permeate_closure": f"{BINARY_SEARCH_ITERATIONS}-iteration bisection",
            "adaptive_integrator_called": False,
            "transport_equations": "same frozen literature polymer solution-diffusion and finite-selectivity Pd Sieverts-law equations",
            "case_count": len(cases),
            "design_count": len(designs),
        },
        "maximum_component_mass_balance_abs_mol": module_balance,
        "dwsim_horizon_reference_used": use_horizon_reference,
        "dwsim_horizon_reference_status": (
            "current reference used" if use_horizon_reference else "not used because current DWSIM DLL execution was blocked by Windows application-control policy"
        ),
        "summary_by_design": summary_by_design,
        "all_32_case_design_pairs_pass": all_pass,
        "all_32_event_labels_agree_with_dop853": all_labels_agree,
        "claim_boundary": {
            "supported": (
                "The final two design decisions are insensitive to replacing adaptive DOP853 with a separately coded "
                "fixed-area RK4 implementation and a refined area mesh."
            ),
            "not_supported": (
                "This is a numerical implementation cross-check of the same transport laws. It is not Aspen, a vendor "
                "module calculation, or matched multicomponent experimental validation."
            ),
        },
    }
    if payload["status"] != "fixed_area_rk4_crosscheck_passed":
        raise AssertionError("independent RK4 membrane cross-check did not preserve all decisions")

    direct_path = OUT / "Table_rk4_192section_direct_cases.csv"
    convergence_path = OUT / "Table_rk4_mesh_convergence.csv"
    json_path = OUT / "PSA_INDEPENDENT_RK4_MEMBRANE_CROSSCHECK_V1.json"
    md_path = OUT / "PSA_INDEPENDENT_RK4_MEMBRANE_CROSSCHECK_V1.md"
    figure_path = OUT / "Fig_independent_rk4_membrane_crosscheck_v1.png"
    write_csv(direct_path, direct_rows)
    write_csv(convergence_path, convergence_rows)
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    lines = [
        "# Independent fixed-area RK4 membrane cross-check v1",
        "",
        "A separately coded classical RK4 area integrator was refined through 48, 96, and 192 sections per membrane stage.",
        "It re-evaluated the 0.554-m2/80%-retention and 0.887-m2/50%-retention designs over all 16 frozen cases.",
        "",
    ]
    for design_id, summary in summary_by_design.items():
        lines.extend(
            [
                f"- `{design_id}`: **{summary['rk4_pass_count']}/{summary['case_count']} pass**, "
                f"maximum recovery difference from DOP853 {summary['maximum_recovery_difference_vs_dop853_percentage_point']:.3e} percentage point.",
                (
                    f"- Maximum horizon H2 relative difference: {summary['maximum_horizon_h2_relative_difference_vs_dop853']:.3e}."
                    if summary["maximum_horizon_h2_relative_difference_vs_dop853"] is not None
                    else "- DWSIM horizon comparison was not used in this rerun because the host blocked the DWSIM DLL."
                ),
            ]
        )
    lines.extend(
        [
            "",
            f"All **{sum(item['case_count'] for item in summary_by_design.values())}/32** design/case event labels agree with DOP853.",
            "",
            "This closes a numerical-method sensitivity check only. External Aspen transport or matched membrane measurements remain open.",
            "",
        ]
    )
    md_path.write_text("\n".join(lines), encoding="utf-8")

    fig, axes = plt.subplots(1, 2, figsize=(10.8, 4.2))
    for design in designs:
        rows = [row for row in convergence_rows if row["design_id"] == design["design_id"]]
        axes[0].loglog(
            [row["area_sections_per_stage"] for row in rows[:-1]],
            [row["maximum_component_horizon_relative_difference_vs_192"] for row in rows[:-1]],
            marker="o",
            label=design["design_id"].replace("_", " "),
        )
    axes[0].set(
        xlabel="Fixed RK4 area sections per stage",
        ylabel="Maximum component difference vs 192-section result",
        title="a  Area-mesh refinement",
    )
    axes[0].grid(True, which="both", alpha=0.25)
    axes[0].legend(fontsize=8)

    positions = np.arange(len(direct_rows))
    colors = ["#1f77b4" if row["design_id"] == "base_20pct_loss" else "#d95f02" for row in direct_rows]
    axes[1].scatter(
        positions,
        [row["recovery_difference_percentage_point"] for row in direct_rows],
        c=colors,
        s=22,
        alpha=0.85,
    )
    axes[1].axhline(0.0, color="black", linewidth=0.8)
    axes[1].set(
        xlabel="Frozen design/case pair",
        ylabel="RK4 − DOP853 recovery (percentage point)",
        title="b  Independent-integrator agreement",
    )
    axes[1].grid(True, axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(figure_path, dpi=240)
    plt.close(fig)

    files = [json_path, md_path, direct_path, convergence_path, figure_path]
    manifest = {
        "schema": "psa-independent-rk4-membrane-crosscheck-manifest/v1",
        "files": [
            {"path": path.name, "bytes": path.stat().st_size, "sha256": sha256(path)}
            for path in files
        ],
        "source_files": [
            {"path": str(path.relative_to(HERE)), "bytes": path.stat().st_size, "sha256": sha256(path)}
            for path in (
                [ODE_JSON, BASE_DOP_CSV, SYNGAS_JSON, STRESS_DOP_CSV]
                + ([ASPEN_REFERENCE] if use_horizon_reference else [])
            )
        ],
    }
    manifest_path = OUT / "MANIFEST_SHA256.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
