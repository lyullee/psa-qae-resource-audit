"""Independent continuous-area ODE audit of the polymer/Pd polishing train.

The production model advances the membrane area with fixed Euler sections.  This
audit solves the same local transport equations with scipy's adaptive DOP853
integrator over all 1,920 packets in each of the 16 predeclared cases.  It then
re-sizes the finite-selectivity Pd guard and receiver against the frozen recovery,
shipment, inventory, and five-component quality gates.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import os
from pathlib import Path
import sys

import matplotlib.pyplot as plt
import numpy as np
from scipy.integrate import solve_ivp


ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"
TRAIN_DIR = RESULTS / os.environ.get("PSA_ODE_TRAIN_DIR", "stage_resolved_membrane_train")
PD_DIR = RESULTS / os.environ.get("PSA_ODE_PD_DIR", "pd_leakage_aging_sensitivity")
PD_JSON = PD_DIR / "PSA_PD_LEAKAGE_AGING_SENSITIVITY.json"
V22_JSON = RESULTS / "final_objective_evidence_v22" / "PSA_FINAL_OBJECTIVE_EVIDENCE_V22.json"
OUT = RESULTS / os.environ.get("PSA_ODE_OUTPUT_DIR", "independent_ode_membrane_audit")

sys.path.insert(0, str(ROOT))
import psa_pd_leakage_aging_sensitivity as sensitivity  # noqa: E402
import psa_public_schedule_strict_uncertainty_ensemble as strict  # noqa: E402
import psa_stage_resolved_membrane_train as train  # noqa: E402


COMPONENTS = tuple(strict.COMPONENTS)
H2 = strict.INDEX["H2"]
IMPURITIES = ("CO", "CO2", "N2", "CH4")
MW = sensitivity.MOLECULAR_WEIGHT
POLYMER_AREA_M2 = 0.18919607212953285
RTOL = 1.0e-9
ATOL = 1.0e-13
TIGHT_RTOL = 1.0e-10
TIGHT_ATOL = 1.0e-14
RECEIVER_MARGIN = 1.005


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise ValueError(f"no rows for {path}")
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def case_data() -> list[dict]:
    cases = sensitivity.load_cases()
    for case in cases:
        with np.load(case["trace_path"], allow_pickle=False) as archive:
            case["surge_outlet_mol"] = np.asarray(archive["surge_outlet_mol"], dtype=float)
            case["euler_stage1_product_mol"] = np.asarray(
                archive["stage1_product_mol"], dtype=float
            )
        case["shape"] = case["surge_outlet_mol"].shape
    return cases


def polymer_coefficients() -> np.ndarray:
    material = train.MATERIALS["polymer"]
    coefficient = np.full(len(COMPONENTS), material["h2_permeance_mol_m2_s_pa"])
    for name in COMPONENTS:
        if name != "H2":
            coefficient[strict.INDEX[name]] /= material["selectivity"][name]
    return coefficient


POLYMER_COEFFICIENT = polymer_coefficients()


def polymer_flux_batch(rate: np.ndarray) -> np.ndarray:
    rate = np.maximum(np.asarray(rate, dtype=float), 0.0)
    total = rate.sum(axis=1)
    x = np.divide(rate, total[:, None], out=np.zeros_like(rate), where=total[:, None] > 1.0e-30)
    numerator = POLYMER_COEFFICIENT[None, :] * train.CONCENTRATOR_FEED_PRESSURE_PA * x
    back = POLYMER_COEFFICIENT[None, :] * train.CONCENTRATOR_PERMEATE_PRESSURE_PA
    low = np.zeros(rate.shape[0])
    high = np.maximum(numerator.sum(axis=1), 1.0e-30)
    for _ in range(64):
        mid = 0.5 * (low + high)
        closure = np.sum(numerator / (mid[:, None] + back), axis=1)
        above = closure > 1.0
        low = np.where(above, mid, low)
        high = np.where(above, high, mid)
    total_flux = 0.5 * (low + high)
    y = numerator / (total_flux[:, None] + back)
    y /= np.maximum(y.sum(axis=1)[:, None], 1.0e-30)
    flux = total_flux[:, None] * y
    return np.where(rate <= 1.0e-20, 0.0, flux)


def integrate_polymer(
    feed_moles: np.ndarray,
    duration_s: float,
    *,
    rtol: float = RTOL,
    atol: float = ATOL,
) -> tuple[np.ndarray, np.ndarray, dict]:
    shape = feed_moles.shape
    initial_rate = np.maximum(feed_moles / duration_s, 0.0)

    def rhs(_area: float, flat: np.ndarray) -> np.ndarray:
        return -polymer_flux_batch(flat.reshape(shape)).reshape(-1)

    solution = solve_ivp(
        rhs,
        (0.0, POLYMER_AREA_M2),
        initial_rate.reshape(-1),
        method="DOP853",
        rtol=rtol,
        atol=atol,
        t_eval=[POLYMER_AREA_M2],
    )
    if not solution.success:
        raise RuntimeError(solution.message)
    retentate_rate = np.maximum(solution.y[:, -1].reshape(shape), 0.0)
    product = np.maximum(initial_rate - retentate_rate, 0.0) * duration_s
    retentate = retentate_rate * duration_s
    return product, retentate, {
        "nfev": int(solution.nfev),
        "mass_balance_max_abs_mol": float(
            np.max(np.abs(feed_moles - product - retentate))
        ),
    }


def integrate_pd(
    feed_moles: np.ndarray,
    duration_s: float,
    *,
    area_m2: float,
    retention: float,
    selectivity: dict[str, float] | None = None,
    defect_ratio: float | None = None,
    rtol: float = RTOL,
    atol: float = ATOL,
) -> tuple[np.ndarray, np.ndarray, dict]:
    if (selectivity is None) == (defect_ratio is None):
        raise ValueError("select exactly one leakage model")
    shape = feed_moles.shape
    initial_rate = np.maximum(feed_moles / duration_s, 0.0)

    def rhs(_area: float, flat: np.ndarray) -> np.ndarray:
        rate = np.maximum(flat.reshape(shape), 0.0)
        total = rate.sum(axis=1)
        x = np.divide(rate, total[:, None], out=np.zeros_like(rate), where=total[:, None] > 1.0e-30)
        x_h2 = np.maximum(x[:, H2], 1.0e-30)
        driving = np.sqrt(train.PD_FEED_PRESSURE_PA * x_h2) - math.sqrt(
            train.PD_PERMEATE_PRESSURE_PA
        )
        dense_h2 = (
            retention
            * train.PD_H2_PERMEANCE_MOL_M2_S_PA_HALF
            * np.maximum(driving, 0.0)
        )
        flux = np.zeros_like(rate)
        if selectivity is not None:
            flux[:, H2] = dense_h2
            for name in IMPURITIES:
                index = strict.INDEX[name]
                flux[:, index] = dense_h2 * (x[:, index] / x_h2) / selectivity[name]
        else:
            ratio = float(defect_ratio)
            h2_defect = ratio * dense_h2
            flux[:, H2] = dense_h2 + h2_defect
            for name in IMPURITIES:
                index = strict.INDEX[name]
                knudsen = math.sqrt(MW["H2"] / MW[name])
                flux[:, index] = h2_defect * (x[:, index] / x_h2) * knudsen
        flux = np.where(rate <= 1.0e-20, 0.0, flux)
        return -flux.reshape(-1)

    solution = solve_ivp(
        rhs,
        (0.0, float(area_m2)),
        initial_rate.reshape(-1),
        method="DOP853",
        rtol=rtol,
        atol=atol,
        t_eval=[float(area_m2)],
    )
    if not solution.success:
        raise RuntimeError(solution.message)
    retentate_rate = np.maximum(solution.y[:, -1].reshape(shape), 0.0)
    product = np.maximum(initial_rate - retentate_rate, 0.0) * duration_s
    retentate = retentate_rate * duration_s
    return product, retentate, {
        "nfev": int(solution.nfev),
        "mass_balance_max_abs_mol": float(
            np.max(np.abs(feed_moles - product - retentate))
        ),
    }


def receiver_rows(
    cases: list[dict],
    products: list[np.ndarray],
    *,
    area_m2: float,
    retention: float,
    recovery_floor: float,
    shipment_floor: float,
    gate: dict,
    module_balances: list[float],
) -> tuple[list[dict], float]:
    requirements = [
        sensitivity.receiver_capacity_requirement(product, case["cycle_time_s"])
        for case, product in zip(cases, products)
    ]
    installed = RECEIVER_MARGIN * max(requirements)
    impurity_limits = np.asarray(
        [gate["impurity_max_fraction"][name] for name in IMPURITIES], dtype=float
    )
    impurity_indices = np.asarray(
        [strict.INDEX[name] for name in IMPURITIES], dtype=np.int64
    )
    limiting_names = ("H2_min", "CO_max", "CO2_max", "N2_max", "CH4_max")
    rows = []
    for case, product, requirement, module_balance in zip(
        cases, products, requirements, module_balances
    ):
        timeline = train.build_uniform_timeline(product, case["cycle_time_s"])
        metrics = sensitivity.receiver_metrics_numba(
            timeline,
            installed,
            strict.RECEIVER_HEEL_FRACTION,
            strict.RECEIVER_DT_S,
            strict.RECEIVER_SUBSTEPS,
            float(gate["h2_min_fraction"]),
            impurity_limits,
            impurity_indices,
        )
        total_h2 = float(product[:, H2].sum())
        recovery = total_h2 / max(case["raw_h2_mol"], 1.0e-30)
        qualified = float(metrics[0])
        quality = bool(float(metrics[1]) <= 1.0 + 1.0e-10)
        event = bool(
            case["source_reserve_gate"]
            and case["source_css_gate"]
            and case["source_numerical_gate"]
            and case["surge_capacity_gate"]
            and quality
            and bool(metrics[8])
            and recovery >= recovery_floor
            and qualified >= shipment_floor
        )
        rows.append(
            {
                "validation_kind": case["validation_kind"],
                "case_id": case["case_id"],
                "pd_area_m2": area_m2,
                "permeance_retention": retention,
                "receiver_capacity_mol": installed,
                "receiver_required_capacity_mol": requirement,
                "overall_h2_recovery": recovery,
                "qualified_h2_rate_mol_s": qualified,
                "continuous_quality_gate": quality,
                "receiver_inventory_gate": bool(metrics[8]),
                "worst_gate_factor": float(metrics[1]),
                "limiting_constraint": limiting_names[int(metrics[2])],
                "minimum_h2_fraction": float(metrics[3]),
                "maximum_co_ppm": float(metrics[4]),
                "maximum_co2_ppm": float(metrics[5]),
                "maximum_n2_ppm": float(metrics[6]),
                "maximum_ch4_ppm": float(metrics[7]),
                "receiver_mass_balance_max_abs_mol": float(metrics[11]),
                "module_mass_balance_max_abs_mol": module_balance,
                "stage_train_event": event,
            }
        )
    return rows, installed


def summarize(rows: list[dict], receiver: float) -> dict:
    return {
        "pass_count": int(sum(row["stage_train_event"] for row in rows)),
        "case_count": len(rows),
        "all_pass": bool(all(row["stage_train_event"] for row in rows)),
        "minimum_recovery": min(row["overall_h2_recovery"] for row in rows),
        "minimum_qualified_h2_rate_mol_s": min(
            row["qualified_h2_rate_mol_s"] for row in rows
        ),
        "maximum_worst_gate_factor": max(row["worst_gate_factor"] for row in rows),
        "maximum_co_ppm": max(row["maximum_co_ppm"] for row in rows),
        "maximum_co2_ppm": max(row["maximum_co2_ppm"] for row in rows),
        "maximum_n2_ppm": max(row["maximum_n2_ppm"] for row in rows),
        "maximum_ch4_ppm": max(row["maximum_ch4_ppm"] for row in rows),
        "receiver_capacity_mol": receiver,
        "maximum_module_mass_balance_abs_mol": max(
            row["module_mass_balance_max_abs_mol"] for row in rows
        ),
        "maximum_receiver_mass_balance_abs_mol": max(
            row["receiver_mass_balance_max_abs_mol"] for row in rows
        ),
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    pd = json.loads(PD_JSON.read_text(encoding="utf-8"))
    v22 = json.loads(V22_JSON.read_text(encoding="utf-8"))
    decision = v22["primary_engineering_decision"]
    recovery_floor = float(decision["minimum_h2_recovery"])
    shipment_floor = float(decision["minimum_qualified_h2_rate_mol_s"])
    gate = strict.strict_gate(strict.load_contract())
    old_guard = pd["guard_banded_20_percent_retention_design"]
    old_area = float(old_guard["selected_rounded_pd_area_m2"])
    retention = float(old_guard["target_permeance_retention"])
    old_selectivity = {
        name: float(old_guard["selected_effective_selectivity"][name])
        for name in IMPURITIES
    }
    cases = case_data()

    integration_rows = []
    for case in cases:
        ode_product, ode_retentate, info = integrate_polymer(
            case["surge_outlet_mol"], case["packet_duration_s"]
        )
        case["ode_stage1_product_mol"] = ode_product
        case["ode_stage1_retentate_mol"] = ode_retentate
        case["ode_stage1_balance"] = info["mass_balance_max_abs_mol"]
        feed_h2 = float(case["surge_outlet_mol"][:, H2].sum())
        euler_h2 = float(case["euler_stage1_product_mol"][:, H2].sum())
        ode_h2 = float(ode_product[:, H2].sum())
        integration_rows.append(
            {
                "validation_kind": case["validation_kind"],
                "case_id": case["case_id"],
                "euler_stage1_h2_recovery": euler_h2 / feed_h2,
                "ode_stage1_h2_recovery": ode_h2 / feed_h2,
                "ode_minus_euler_stage1_recovery_percentage_point": 100.0
                * (ode_h2 - euler_h2)
                / feed_h2,
                "maximum_packet_component_difference_mol": float(
                    np.max(np.abs(ode_product - case["euler_stage1_product_mol"]))
                ),
                "ode_stage1_mass_balance_max_abs_mol": info[
                    "mass_balance_max_abs_mol"
                ],
                "ode_function_evaluations": info["nfev"],
            }
        )

    cache: dict[tuple, tuple[list[dict], float, dict, list[np.ndarray]]] = {}

    def evaluate(
        area: float,
        *,
        selectivity: dict[str, float] | None = None,
        defect_ratio: float | None = None,
        rtol: float = RTOL,
        atol: float = ATOL,
    ) -> tuple[list[dict], float, dict, list[np.ndarray]]:
        selectivity_key = None if selectivity is None else tuple(
            round(selectivity[name], 6) for name in IMPURITIES
        )
        key = (
            round(float(area), 10),
            selectivity_key,
            None if defect_ratio is None else round(float(defect_ratio), 14),
            rtol,
            atol,
        )
        if key not in cache:
            products = []
            balances = []
            for case in cases:
                product, _retentate, info = integrate_pd(
                    case["ode_stage1_product_mol"],
                    case["packet_duration_s"],
                    area_m2=area,
                    retention=retention,
                    selectivity=selectivity,
                    defect_ratio=defect_ratio,
                    rtol=rtol,
                    atol=atol,
                )
                products.append(product)
                balances.append(
                    max(case["ode_stage1_balance"], info["mass_balance_max_abs_mol"])
                )
            rows, receiver = receiver_rows(
                cases,
                products,
                area_m2=area,
                retention=retention,
                recovery_floor=recovery_floor,
                shipment_floor=shipment_floor,
                gate=gate,
                module_balances=balances,
            )
            cache[key] = (rows, receiver, summarize(rows, receiver), products)
        return cache[key]

    current_rows, current_receiver, current_summary, _ = evaluate(
        old_area, selectivity=old_selectivity
    )

    area_screen = []
    for area in np.linspace(old_area, 0.575, 12):
        rows, receiver, summary, _ = evaluate(float(area), selectivity=old_selectivity)
        area_screen.append(
            {
                "pd_area_m2": float(area),
                "pass_count": summary["pass_count"],
                "minimum_recovery": summary["minimum_recovery"],
                "minimum_qualified_h2_rate_mol_s": summary[
                    "minimum_qualified_h2_rate_mol_s"
                ],
                "maximum_worst_gate_factor": summary["maximum_worst_gate_factor"],
                "receiver_capacity_mol": receiver,
            }
        )

    def performance_pass(rows: list[dict]) -> bool:
        return all(
            row["overall_h2_recovery"] >= recovery_floor
            and row["qualified_h2_rate_mol_s"] >= shipment_floor
            and row["receiver_inventory_gate"]
            for row in rows
        )

    low, high = old_area, 0.70
    high_rows = evaluate(high, selectivity=old_selectivity)[0]
    if not performance_pass(high_rows):
        raise AssertionError("ODE recovery/shipment guard did not pass at the search upper bound")
    for _ in range(26):
        mid = 0.5 * (low + high)
        if performance_pass(evaluate(mid, selectivity=old_selectivity)[0]):
            high = mid
        else:
            low = mid
    minimum_area = high
    selected_area = math.ceil(minimum_area * 1000.0) / 1000.0
    selected_rows, selected_receiver, selected_summary, selected_products = evaluate(
        selected_area, selectivity=old_selectivity
    )

    base_selectivity = {
        name: old_selectivity[name] / float(old_guard["selected_common_selectivity_multiplier"])
        for name in IMPURITIES
    }

    def multiplier_pass(multiplier: float) -> bool:
        selectivity = {
            name: base_selectivity[name] * multiplier for name in IMPURITIES
        }
        return evaluate(selected_area, selectivity=selectivity)[2]["all_pass"]

    low_log, high_log = math.log(0.05), math.log(1.0e8)
    for _ in range(28):
        mid = 0.5 * (low_log + high_log)
        if multiplier_pass(math.exp(mid)):
            high_log = mid
        else:
            low_log = mid
    minimum_multiplier = math.exp(high_log)
    selected_multiplier = max(
        float(old_guard["selected_common_selectivity_multiplier"]),
        math.ceil(1.25 * minimum_multiplier * 100.0) / 100.0,
    )
    selected_selectivity = {
        name: base_selectivity[name] * selected_multiplier for name in IMPURITIES
    }
    selected_rows, selected_receiver, selected_summary, selected_products = evaluate(
        selected_area, selectivity=selected_selectivity
    )
    if not selected_summary["all_pass"]:
        raise AssertionError("final ODE selectivity guard did not pass")

    def defect_pass(ratio: float) -> bool:
        return evaluate(selected_area, defect_ratio=ratio)[2]["all_pass"]

    low_defect, high_defect = 0.0, 1.0e-3
    if defect_pass(high_defect):
        raise AssertionError("defect search upper bound still passes")
    for _ in range(28):
        mid = 0.5 * (low_defect + high_defect)
        if defect_pass(mid):
            low_defect = mid
        else:
            high_defect = mid
    maximum_defect = low_defect
    selected_defect = 0.8 * maximum_defect
    defect_rows, defect_receiver, defect_summary, _ = evaluate(
        selected_area, defect_ratio=selected_defect
    )
    if not defect_summary["all_pass"]:
        raise AssertionError("ODE defect guard did not pass")

    limiting = min(selected_rows, key=lambda row: row["overall_h2_recovery"])
    limiting_index = next(
        index for index, case in enumerate(cases) if case["case_id"] == limiting["case_id"]
    )
    tight_polymer, _tight_ret, tight_poly_info = integrate_polymer(
        cases[limiting_index]["surge_outlet_mol"],
        cases[limiting_index]["packet_duration_s"],
        rtol=TIGHT_RTOL,
        atol=TIGHT_ATOL,
    )
    tight_pd, _tight_pd_ret, tight_pd_info = integrate_pd(
        tight_polymer,
        cases[limiting_index]["packet_duration_s"],
        area_m2=selected_area,
        retention=retention,
        selectivity=selected_selectivity,
        rtol=TIGHT_RTOL,
        atol=TIGHT_ATOL,
    )
    regular_recovery = float(
        selected_products[limiting_index][:, H2].sum()
        / cases[limiting_index]["raw_h2_mol"]
    )
    tight_recovery = float(
        tight_pd[:, H2].sum() / cases[limiting_index]["raw_h2_mol"]
    )

    write_csv(OUT / "Table_ode_stage1_integrator_comparison.csv", integration_rows)
    write_csv(OUT / "Table_ode_current_guard_validation.csv", current_rows)
    write_csv(OUT / "Table_ode_revised_guard_validation.csv", selected_rows)
    write_csv(OUT / "Table_ode_defect_guard_validation.csv", defect_rows)
    write_csv(OUT / "Table_ode_pd_area_screen.csv", area_screen)

    result = {
        "schema": "psa-independent-ode-membrane-audit/v1",
        "status": "adaptive_ode_guard_redesign_completed",
        "solver": {
            "method": "scipy solve_ivp DOP853",
            "relative_tolerance": RTOL,
            "absolute_tolerance": ATOL,
            "tight_replay_relative_tolerance": TIGHT_RTOL,
            "tight_replay_absolute_tolerance": TIGHT_ATOL,
            "limiting_case": limiting["case_id"],
            "regular_limiting_recovery": regular_recovery,
            "tight_limiting_recovery": tight_recovery,
            "absolute_recovery_difference": abs(tight_recovery - regular_recovery),
            "tight_polymer_function_evaluations": tight_poly_info["nfev"],
            "tight_pd_function_evaluations": tight_pd_info["nfev"],
        },
        "frozen_gates": {
            "minimum_h2_recovery": recovery_floor,
            "minimum_qualified_h2_rate_mol_s": shipment_floor,
            "h2_min_fraction": gate["h2_min_fraction"],
            "impurity_max_fraction": gate["impurity_max_fraction"],
        },
        "stage1_integrator_comparison": {
            "minimum_ode_minus_euler_recovery_percentage_point": min(
                row["ode_minus_euler_stage1_recovery_percentage_point"]
                for row in integration_rows
            ),
            "maximum_ode_minus_euler_recovery_percentage_point": max(
                row["ode_minus_euler_stage1_recovery_percentage_point"]
                for row in integration_rows
            ),
            "maximum_ode_mass_balance_abs_mol": max(
                row["ode_stage1_mass_balance_max_abs_mol"]
                for row in integration_rows
            ),
        },
        "superseded_0p553_m2_guard": {
            "pd_area_m2": old_area,
            "summary": current_summary,
            "reason": "the independently integrated continuous-area model falls below the frozen recovery floor in at least one direct case",
        },
        "revised_guard_design": {
            "minimum_unrounded_pd_area_m2": minimum_area,
            "selected_rounded_pd_area_m2": selected_area,
            "area_increase_vs_0p553_percent": 100.0 * (selected_area / old_area - 1.0),
            "permeance_retention": retention,
            "minimum_common_selectivity_multiplier": minimum_multiplier,
            "selected_common_selectivity_multiplier": selected_multiplier,
            "selected_effective_selectivity": selected_selectivity,
            "receiver_capacity_mol": selected_receiver,
            "receiver_volume_L_at_1bar_298K": selected_receiver
            * train.R_J_MOL_K
            * train.COMPRESSION_T_K
            / train.PD_PERMEATE_PRESSURE_PA
            * 1000.0,
            "direct_confirmation": selected_summary,
        },
        "revised_defect_boundary": {
            "definition": pd["defect_leakage_boundary"]["definition"],
            "maximum_passing_ratio": maximum_defect,
            "guard_banded_ratio": selected_defect,
            "guard_banded_direct_confirmation": defect_summary,
        },
        "claim_boundary": {
            "allowed": "adaptive continuous-area ODE integration independently audits the fixed-section membrane numerics and supplies the revised numerical guard band",
            "not_allowed": "the ODE audit uses the same literature transport laws and is not experimental, Aspen, or vendor-module validation",
        },
    }
    (OUT / "PSA_INDEPENDENT_ODE_MEMBRANE_AUDIT.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )

    fig, axes = plt.subplots(2, 2, figsize=(12.5, 8.5), constrained_layout=True)
    x = np.arange(16)
    ax = axes[0, 0]
    euler = np.asarray([row["euler_stage1_h2_recovery"] for row in integration_rows])
    ode = np.asarray([row["ode_stage1_h2_recovery"] for row in integration_rows])
    ax.plot(x, 100 * euler, "o--", label="72-section Euler")
    ax.plot(x, 100 * ode, "s-", label="adaptive ODE")
    ax.set(xlabel="Predeclared case index", ylabel="Stage-1 H$_2$ recovery (%)", title="a  Polymer-stage integration")
    ax.grid(alpha=0.25)
    ax.legend(frameon=False)

    ax = axes[0, 1]
    screen_area = np.asarray([row["pd_area_m2"] for row in area_screen])
    screen_recovery = np.asarray([row["minimum_recovery"] for row in area_screen])
    ax.plot(screen_area, 100 * screen_recovery, "o-")
    ax.axhline(100 * recovery_floor, ls="--", color="#c0392b", label="frozen recovery floor")
    ax.axvline(selected_area, ls=":", color="#2c3e50", label=f"selected {selected_area:.3f} m²")
    ax.set(xlabel="Pd area (m²)", ylabel="Minimum overall H$_2$ recovery (%)", title="b  ODE Pd-area guard")
    ax.grid(alpha=0.25)
    ax.legend(frameon=False, fontsize=8)

    ax = axes[1, 0]
    current_rec = np.asarray([row["overall_h2_recovery"] for row in current_rows])
    revised_rec = np.asarray([row["overall_h2_recovery"] for row in selected_rows])
    ax.plot(x, 100 * current_rec, "o--", label="0.553 m²")
    ax.plot(x, 100 * revised_rec, "s-", label=f"revised {selected_area:.3f} m²")
    ax.axhline(100 * recovery_floor, ls="--", color="#c0392b")
    ax.set(xlabel="Predeclared case index", ylabel="Overall H$_2$ recovery (%)", title="c  Direct ODE confirmation")
    ax.grid(alpha=0.25)
    ax.legend(frameon=False)

    ax = axes[1, 1]
    maxima = np.array(
        [
            selected_summary["maximum_co_ppm"] / 0.5,
            selected_summary["maximum_co2_ppm"] / 5.0,
            selected_summary["maximum_n2_ppm"] / 300.0,
            selected_summary["maximum_ch4_ppm"] / 100.0,
        ]
    )
    ax.bar(["CO", "CO$_2$", "N$_2$", "CH$_4$"], maxima, color="#4c956c")
    ax.axhline(1.0, ls="--", color="#c0392b", label="specification limit")
    ax.set(ylabel="Worst concentration / limit", title="d  Revised finite-selectivity guard")
    ax.grid(alpha=0.25, axis="y")
    ax.legend(frameon=False, fontsize=8)
    fig.suptitle("Independent continuous-area ODE audit of the membrane train", fontsize=14)
    for suffix in ("png", "pdf", "svg"):
        fig.savefig(OUT / f"Fig_independent_ode_membrane_audit.{suffix}", dpi=300)
    plt.close(fig)

    revised = result["revised_guard_design"]
    md = f"""# Independent continuous-area ODE audit

## Numerical finding

The production membrane model uses 72 fixed area sections for the polymer stage and 144 sections for the Pd stage. An independent adaptive DOP853 integration over all 1,920 packets in each of the 16 predeclared cases lowers the polymer-stage H2 recovery by **{abs(result['stage1_integrator_comparison']['minimum_ode_minus_euler_recovery_percentage_point']):.3f}–{abs(result['stage1_integrator_comparison']['maximum_ode_minus_euler_recovery_percentage_point']):.3f} percentage point** relative to the fixed-section result.

At the former **{old_area:.3f} m²** Pd guard, only **{current_summary['pass_count']}/16** direct cases pass because the minimum recovery falls to **{100*current_summary['minimum_recovery']:.4f}%**, below the frozen **{100*recovery_floor:.4f}%** floor. That guard is therefore superseded.

## Revised guard

- minimum unrounded Pd area: **{minimum_area:.6f} m²**;
- selected rounded Pd area: **{selected_area:.3f} m²**;
- increase from 0.553 m²: **{revised['area_increase_vs_0p553_percent']:.2f}%**;
- co-sized receiver: **{selected_receiver:.6f} mol ({revised['receiver_volume_L_at_1bar_298K']:.3f} L at 1 bar and 298.15 K)**;
- direct confirmation: **{selected_summary['pass_count']}/16 pass**;
- minimum recovery: **{100*selected_summary['minimum_recovery']:.4f}%**;
- minimum qualified H2 rate: **{selected_summary['minimum_qualified_h2_rate_mol_s']:.7f} mol/s**;
- worst CO/CO2/N2/CH4: **{selected_summary['maximum_co_ppm']:.3f}/{selected_summary['maximum_co2_ppm']:.3f}/{selected_summary['maximum_n2_ppm']:.3f}/{selected_summary['maximum_ch4_ppm']:.3f} ppm**;
- tight-tolerance replay recovery difference: **{result['solver']['absolute_recovery_difference']:.3e}**.

The ODE audit verifies the numerical area integration using a different algorithm. It still uses the same literature membrane transport equations and does not replace Aspen, vendor-module, or experimental validation.
"""
    (OUT / "PSA_INDEPENDENT_ODE_MEMBRANE_AUDIT.md").write_text(md, encoding="utf-8")

    source_paths = [
        Path(__file__),
        ROOT / "psa_stage_resolved_membrane_train.py",
        ROOT / "psa_pd_leakage_aging_sensitivity.py",
        ROOT / "psa_public_schedule_strict_uncertainty_ensemble.py",
        ROOT / "psa_fixed_area_dynamic_membrane_polishing.py",
        PD_JSON,
        V22_JSON,
        TRAIN_DIR / "Table_stage_train_mesh_audit.csv",
    ]
    source_paths.extend(sorted((TRAIN_DIR / "states").glob("*_traces.npz")))
    output_paths = [
        OUT / "Table_ode_stage1_integrator_comparison.csv",
        OUT / "Table_ode_current_guard_validation.csv",
        OUT / "Table_ode_revised_guard_validation.csv",
        OUT / "Table_ode_defect_guard_validation.csv",
        OUT / "Table_ode_pd_area_screen.csv",
        OUT / "PSA_INDEPENDENT_ODE_MEMBRANE_AUDIT.json",
        OUT / "PSA_INDEPENDENT_ODE_MEMBRANE_AUDIT.md",
        OUT / "Fig_independent_ode_membrane_audit.png",
        OUT / "Fig_independent_ode_membrane_audit.pdf",
        OUT / "Fig_independent_ode_membrane_audit.svg",
    ]
    manifest = {
        "schema": "psa-independent-ode-membrane-audit-manifest/v1",
        "sources": [
            {
                "path": str(path.relative_to(ROOT)),
                "sha256": sha256(path),
                "bytes": path.stat().st_size,
            }
            for path in source_paths
        ],
        "outputs": [
            {
                "path": str(path.relative_to(ROOT)),
                "sha256": sha256(path),
                "bytes": path.stat().st_size,
            }
            for path in output_paths
        ],
    }
    (OUT / "MANIFEST_SHA256.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
