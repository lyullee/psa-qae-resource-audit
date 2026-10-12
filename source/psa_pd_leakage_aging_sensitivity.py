"""Finite dense-Pd leakage, defect, and permeance-retention sensitivity.

The stage-resolved train used an ideal defect-free Pd polishing layer.  This
audit replays the saved stage-1 permeate packets through two finite models:

1. constant effective H2/impurity module selectivities; and
2. an H2-equivalent Knudsen defect-leak conductance ratio.

It solves for the permeance-retention, membrane-area, selectivity, receiver,
and defect-leak boundaries required to preserve the frozen recovery,
shipment, reserve, and simultaneous CO/CO2/N2/CH4 product gates in all eight
uncertainty corners and eight predeclared interior hold-outs.
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
from numba import njit

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import psa_qae.psa_public_schedule_strict_uncertainty_ensemble as strict  # noqa: E402
import psa_qae.psa_stage_resolved_membrane_train as train  # noqa: E402


ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"
TRAIN_DIR = RESULTS / os.environ.get("PSA_PD_TRAIN_DIR", "stage_resolved_membrane_train")
TRAIN_JSON = TRAIN_DIR / "PSA_STAGE_RESOLVED_MEMBRANE_TRAIN.json"
V20_JSON = RESULTS / "final_objective_evidence_v20" / "PSA_FINAL_OBJECTIVE_EVIDENCE_V20.json"
REQUIREMENT_JSON = (
    RESULTS
    / "membrane_component_selectivity_requirement"
    / "PSA_MEMBRANE_COMPONENT_SELECTIVITY_REQUIREMENT.json"
)
OUT = RESULTS / os.environ.get("PSA_PD_SENSITIVITY_OUTPUT_DIR", "pd_leakage_aging_sensitivity")
OUT_JSON = OUT / "PSA_PD_LEAKAGE_AGING_SENSITIVITY.json"
OUT_MD = OUT / "PSA_PD_LEAKAGE_AGING_SENSITIVITY.md"
OUT_GRID = OUT / "Table_pd_retention_selectivity_screen.csv"
OUT_THRESHOLDS = OUT / "Table_pd_component_thresholds.csv"
OUT_CASES = OUT / "Table_pd_guard_banded_design_validation.csv"
OUT_LITERATURE = OUT / "Table_pd_literature_anchor_scenarios.csv"
OUT_FIGURE = OUT / "Fig_pd_leakage_aging_sensitivity"
OUT_MANIFEST = OUT / "PSA_PD_LEAKAGE_AGING_SENSITIVITY_MANIFEST.json"

PD_STEPS = 144
COMPONENTS = tuple(strict.COMPONENTS)
H2_INDEX = strict.INDEX["H2"]
IMPURITIES = ("CO", "CO2", "N2", "CH4")
MOLECULAR_WEIGHT = {"H2": 2.01588, "CO": 28.0101, "CO2": 44.0095, "N2": 28.0134, "CH4": 16.0425}
TARGET_RETENTION = 0.80
SELECTIVITY_SAFETY_FACTOR = 1.25
RECEIVER_CAPACITY_MARGIN = 1.005


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


def load_cases() -> list[dict]:
    cases = []
    for kind, prefix in (("uncertainty_corner", "corner"), ("predeclared_interior_holdout", "holdout")):
        for index in range(8):
            case_id = f"{prefix}_{index:02d}"
            state_path = TRAIN_DIR / "states" / f"{case_id}.json"
            trace_path = TRAIN_DIR / "states" / f"{case_id}_traces.npz"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            with np.load(trace_path, allow_pickle=False) as archive:
                stage1 = np.asarray(archive["stage1_product_mol"], dtype=float)
            cases.append(
                {
                    "validation_kind": kind,
                    "case_id": case_id,
                    "state_path": state_path,
                    "trace_path": trace_path,
                    "stage1_product_mol": stage1,
                    "packet_duration_s": float(state["cycle_time_s"])
                    / (4 * strict.ADSORPTION_SUBSTEPS),
                    "cycle_time_s": float(state["cycle_time_s"]),
                    "elapsed_s": float(state["n_cycles"]) * float(state["cycle_time_s"]),
                    "raw_h2_mol": float(state["raw_h2_rate_mol_s"])
                    * float(state["n_cycles"])
                    * float(state["cycle_time_s"]),
                    "source_reserve_gate": bool(state["source_reserve_gate"]),
                    "source_css_gate": bool(state["source_css_gate"]),
                    "source_numerical_gate": bool(state["source_numerical_gate"]),
                    "surge_capacity_gate": bool(state["surge_capacity_gate"]),
                }
            )
    return cases


def finite_pd_packets(
    feed_packets: np.ndarray,
    *,
    duration_s: float,
    area_m2: float,
    permeance_retention: float,
    selectivity: dict[str, float] | None = None,
    defect_h2_equivalent_ratio: float | None = None,
) -> tuple[np.ndarray, np.ndarray, float]:
    """Vectorized cross-flow Pd stage with one finite-leakage model."""
    if (selectivity is None) == (defect_h2_equivalent_ratio is None):
        raise ValueError("select exactly one finite-leakage model")
    retentate = np.maximum(np.asarray(feed_packets, dtype=float), 0.0).copy()
    product = np.zeros_like(retentate)
    d_area = float(area_m2) / PD_STEPS
    maximum_balance = 0.0
    for _ in range(PD_STEPS):
        total = retentate.sum(axis=1)
        h2 = retentate[:, H2_INDEX]
        active = (total > 1.0e-18) & (h2 > 1.0e-18)
        x = np.divide(
            retentate,
            total[:, None],
            out=np.zeros_like(retentate),
            where=total[:, None] > 1.0e-18,
        )
        driving = np.sqrt(train.PD_FEED_PRESSURE_PA * x[:, H2_INDEX]) - math.sqrt(
            train.PD_PERMEATE_PRESSURE_PA
        )
        dense_h2 = (
            float(permeance_retention)
            * train.PD_H2_PERMEANCE_MOL_M2_S_PA_HALF
            * np.maximum(driving, 0.0)
            * d_area
            * float(duration_s)
        )
        dense_h2 = np.minimum(dense_h2, 0.999999 * h2)
        dense_h2[~active] = 0.0
        transfer = np.zeros_like(retentate)
        if selectivity is not None:
            transfer[:, H2_INDEX] = dense_h2
            x_h2 = np.maximum(x[:, H2_INDEX], 1.0e-30)
            for name in IMPURITIES:
                index = strict.INDEX[name]
                leak = dense_h2 * (x[:, index] / x_h2) / float(selectivity[name])
                transfer[:, index] = np.minimum(leak, 0.999999 * retentate[:, index])
        else:
            ratio = float(defect_h2_equivalent_ratio)
            x_h2 = np.maximum(x[:, H2_INDEX], 1.0e-30)
            h2_defect = ratio * dense_h2
            transfer[:, H2_INDEX] = np.minimum(
                dense_h2 + h2_defect, 0.999999 * retentate[:, H2_INDEX]
            )
            for name in IMPURITIES:
                index = strict.INDEX[name]
                knudsen = math.sqrt(MOLECULAR_WEIGHT["H2"] / MOLECULAR_WEIGHT[name])
                leak = h2_defect * (x[:, index] / x_h2) * knudsen
                transfer[:, index] = np.minimum(leak, 0.999999 * retentate[:, index])
        before = retentate.copy()
        retentate -= transfer
        product += transfer
        maximum_balance = max(
            maximum_balance,
            float(np.max(np.abs(before - retentate - transfer))),
        )
    return product, retentate, maximum_balance


def receiver_capacity_requirement(product_packets: np.ndarray, cycle_time_s: float) -> float:
    timeline = train.build_uniform_timeline(product_packets, cycle_time_s)
    total = timeline.sum(axis=1)
    outlet_per_slot = float(total.mean())
    imbalance = np.concatenate(([0.0], np.cumsum(total - outlet_per_slot)))
    swing = float(imbalance.max() - imbalance.min())
    return swing / max(1.0 - strict.RECEIVER_HEEL_FRACTION, 1.0e-30)


@njit(cache=True)
def receiver_metrics_numba(
    timeline: np.ndarray,
    capacity_mol: float,
    heel_fraction: float,
    receiver_dt_s: float,
    receiver_substeps: int,
    h2_min_fraction: float,
    impurity_limits: np.ndarray,
    impurity_indices: np.ndarray,
) -> tuple:
    total_in = np.zeros(timeline.shape[1])
    for k in range(timeline.shape[0]):
        total_in += timeline[k]
    elapsed_s = timeline.shape[0] * receiver_dt_s
    outlet_rate = total_in.sum() / max(elapsed_s, 1.0e-30)
    imbalance = 0.0
    imbalance_min = 0.0
    for k in range(timeline.shape[0]):
        imbalance += timeline[k].sum() - outlet_rate * receiver_dt_s
        if imbalance < imbalance_min:
            imbalance_min = imbalance
    mean_y = total_in / max(total_in.sum(), 1.0e-30)
    initial_total = heel_fraction * capacity_mol - imbalance_min
    inventory = initial_total * mean_y
    initial_inventory = inventory.copy()
    outlet_component = np.zeros(timeline.shape[1])
    maximum_fraction = np.zeros(timeline.shape[1])
    minimum_h2 = 1.0
    max_inventory = 0.0
    min_inventory = 1.0e300
    worst_factor = 0.0
    limiting_index = 0
    dt = receiver_dt_s / receiver_substeps
    for k in range(timeline.shape[0]):
        inlet_rate = timeline[k] / receiver_dt_s
        for _ in range(receiver_substeps):
            total_inventory = inventory.sum()
            y = inventory / max(total_inventory, 1.0e-30)
            h2_factor = h2_min_fraction / max(y[H2_INDEX], 1.0e-30)
            if h2_factor > worst_factor:
                worst_factor = h2_factor
                limiting_index = 0
            if y[H2_INDEX] < minimum_h2:
                minimum_h2 = y[H2_INDEX]
            for j in range(timeline.shape[1]):
                if y[j] > maximum_fraction[j]:
                    maximum_fraction[j] = y[j]
            for j in range(4):
                component_index = impurity_indices[j]
                factor = y[component_index] / max(impurity_limits[j], 1.0e-30)
                if factor > worst_factor:
                    worst_factor = factor
                    limiting_index = component_index
            if total_inventory > max_inventory:
                max_inventory = total_inventory
            if total_inventory < min_inventory:
                min_inventory = total_inventory
            outlet_component += outlet_rate * y * dt
            inventory += (inlet_rate - outlet_rate * y) * dt
            for j in range(timeline.shape[1]):
                if inventory[j] < 0.0:
                    inventory[j] = 0.0
    residual = initial_inventory + total_in - outlet_component - inventory
    maximum_residual = 0.0
    for value in residual:
        if abs(value) > maximum_residual:
            maximum_residual = abs(value)
    feasible = initial_total <= capacity_mol * (1.0 + 1.0e-10) and max_inventory <= capacity_mol * (1.0 + 2.0e-9)
    return (
        outlet_component[H2_INDEX] / max(elapsed_s, 1.0e-30),
        worst_factor,
        limiting_index,
        minimum_h2,
        maximum_fraction[impurity_indices[0]] * 1.0e6,
        maximum_fraction[impurity_indices[1]] * 1.0e6,
        maximum_fraction[impurity_indices[2]] * 1.0e6,
        maximum_fraction[impurity_indices[3]] * 1.0e6,
        feasible,
        min_inventory,
        max_inventory,
        maximum_residual,
    )


def evaluate_configuration(
    cases: list[dict],
    *,
    area_m2: float,
    permeance_retention: float,
    recovery_floor: float,
    shipment_floor: float,
    gate: dict,
    selectivity: dict[str, float] | None = None,
    defect_h2_equivalent_ratio: float | None = None,
    receiver_capacity_mol: float | None = None,
) -> tuple[list[dict], float]:
    products = []
    receiver_requirements = []
    for case in cases:
        product, _retentate, balance = finite_pd_packets(
            case["stage1_product_mol"],
            duration_s=case["packet_duration_s"],
            area_m2=area_m2,
            permeance_retention=permeance_retention,
            selectivity=selectivity,
            defect_h2_equivalent_ratio=defect_h2_equivalent_ratio,
        )
        products.append((case, product, balance))
        receiver_requirements.append(
            receiver_capacity_requirement(product, case["cycle_time_s"])
        )
    installed_receiver = (
        RECEIVER_CAPACITY_MARGIN * max(receiver_requirements)
        if receiver_capacity_mol is None
        else float(receiver_capacity_mol)
    )
    impurity_limits = np.asarray(
        [gate["impurity_max_fraction"][name] for name in IMPURITIES], dtype=float
    )
    impurity_indices = np.asarray([strict.INDEX[name] for name in IMPURITIES], dtype=np.int64)
    rows = []
    limiting_names = ("H2_min", "CO_max", "CO2_max", "N2_max", "CH4_max")
    for (case, product, balance), receiver_required in zip(products, receiver_requirements):
        timeline = train.build_uniform_timeline(product, case["cycle_time_s"])
        metrics = receiver_metrics_numba(
            timeline,
            installed_receiver,
            strict.RECEIVER_HEEL_FRACTION,
            strict.RECEIVER_DT_S,
            strict.RECEIVER_SUBSTEPS,
            float(gate["h2_min_fraction"]),
            impurity_limits,
            impurity_indices,
        )
        total_h2 = float(product[:, H2_INDEX].sum())
        recovery = total_h2 / max(case["raw_h2_mol"], 1.0e-30)
        qualified_rate = float(metrics[0])
        quality_gate = bool(float(metrics[1]) <= 1.0 + 1.0e-10)
        event = bool(
            case["source_reserve_gate"]
            and case["source_css_gate"]
            and case["source_numerical_gate"]
            and case["surge_capacity_gate"]
            and quality_gate
            and bool(metrics[8])
            and recovery >= recovery_floor
            and qualified_rate >= shipment_floor
        )
        rows.append(
            {
                "validation_kind": case["validation_kind"],
                "case_id": case["case_id"],
                "pd_area_m2": float(area_m2),
                "permeance_retention": float(permeance_retention),
                "receiver_capacity_mol": installed_receiver,
                "receiver_required_capacity_mol": receiver_required,
                "overall_h2_recovery": recovery,
                "qualified_h2_rate_mol_s": qualified_rate,
                "continuous_quality_gate": quality_gate,
                "receiver_inventory_gate": bool(metrics[8]),
                "worst_gate_factor": float(metrics[1]),
                "limiting_constraint": limiting_names[int(metrics[2])],
                "minimum_h2_fraction": float(metrics[3]),
                "maximum_co_ppm": float(metrics[4]),
                "maximum_co2_ppm": float(metrics[5]),
                "maximum_n2_ppm": float(metrics[6]),
                "maximum_ch4_ppm": float(metrics[7]),
                "receiver_mass_balance_max_abs_mol": float(metrics[11]),
                "module_mass_balance_max_abs_mol": balance,
                "stage_train_event": event,
            }
        )
    return rows, installed_receiver


def summarize(rows: list[dict], receiver_capacity: float) -> dict:
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
        "receiver_capacity_mol": receiver_capacity,
        "maximum_receiver_mass_balance_abs_mol": max(
            row["receiver_mass_balance_max_abs_mol"] for row in rows
        ),
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    train_summary = json.loads(TRAIN_JSON.read_text(encoding="utf-8"))
    v20 = json.loads(V20_JSON.read_text(encoding="utf-8"))
    requirement = json.loads(REQUIREMENT_JSON.read_text(encoding="utf-8"))
    cases = load_cases()
    gate = strict.strict_gate(strict.load_contract())
    decision = v20["primary_engineering_decision"]
    recovery_floor = float(decision["minimum_h2_recovery"])
    shipment_floor = float(decision["minimum_qualified_h2_rate_mol_s"])
    installed = train_summary["selected_design"]
    original_area = float(installed["pd_area_m2"])
    original_receiver = float(installed["receiver_capacity_mol"])
    base_selectivity = {
        name: float(train_summary["strict_component_burden"]["worst_requirement_after_concentration"][name])
        for name in IMPURITIES
    }
    ideal_selectivity = {name: 1.0e12 for name in IMPURITIES}
    cache: dict[tuple, tuple[list[dict], float, dict]] = {}

    def evaluate(
        area: float,
        retention: float,
        *,
        selectivity: dict[str, float] | None = None,
        defect: float | None = None,
        fixed_receiver: float | None = None,
    ) -> tuple[list[dict], float, dict]:
        selectivity_key = None if selectivity is None else tuple(round(float(selectivity[name]), 8) for name in IMPURITIES)
        key = (
            round(float(area), 10),
            round(float(retention), 10),
            selectivity_key,
            None if defect is None else round(float(defect), 14),
            None if fixed_receiver is None else round(float(fixed_receiver), 10),
        )
        if key not in cache:
            rows, receiver = evaluate_configuration(
                cases,
                area_m2=area,
                permeance_retention=retention,
                recovery_floor=recovery_floor,
                shipment_floor=shipment_floor,
                gate=gate,
                selectivity=selectivity,
                defect_h2_equivalent_ratio=defect,
                receiver_capacity_mol=fixed_receiver,
            )
            cache[key] = (rows, receiver, summarize(rows, receiver))
        return cache[key]

    def minimum_passing_scalar(low: float, high: float, evaluator, iterations: int = 22) -> float:
        if evaluator(low):
            return low
        if not evaluator(high):
            raise RuntimeError("upper search bound does not pass")
        for _ in range(iterations):
            middle = 0.5 * (low + high)
            if evaluator(middle):
                high = middle
            else:
                low = middle
        return high

    def minimum_passing_positive_log(low: float, high: float, evaluator, iterations: int = 24) -> float:
        if low <= 0.0 or high <= low:
            raise ValueError("positive logarithmic bounds are required")
        if evaluator(low):
            return low
        if not evaluator(high):
            raise RuntimeError("upper logarithmic search bound does not pass")
        for _ in range(iterations):
            middle = math.sqrt(low * high)
            if evaluator(middle):
                high = middle
            else:
                low = middle
        return high

    minimum_retention_original = minimum_passing_scalar(
        0.40,
        1.0,
        lambda value: evaluate(
            original_area,
            value,
            selectivity=ideal_selectivity,
            fixed_receiver=original_receiver,
        )[2]["all_pass"],
    )
    minimum_effective_area = minimum_passing_scalar(
        0.25,
        original_area,
        lambda value: evaluate(
            value,
            1.0,
            selectivity=ideal_selectivity,
            fixed_receiver=None,
        )[2]["all_pass"],
    )
    area_for_20pct_retention = minimum_effective_area / TARGET_RETENTION
    guard_area = math.ceil(area_for_20pct_retention * 1000.0) / 1000.0

    def multiplier_pass(value: float) -> bool:
        selectivity = {name: base_selectivity[name] * value for name in IMPURITIES}
        return evaluate(
            guard_area,
            TARGET_RETENTION,
            selectivity=selectivity,
            fixed_receiver=None,
        )[2]["all_pass"]

    minimum_common_multiplier = minimum_passing_positive_log(
        0.05, 1.0e8, multiplier_pass
    )
    guard_multiplier = math.ceil(
        minimum_common_multiplier * SELECTIVITY_SAFETY_FACTOR * 100.0
    ) / 100.0
    guard_selectivity = {
        name: base_selectivity[name] * guard_multiplier for name in IMPURITIES
    }
    guard_rows, guard_receiver, guard_summary = evaluate(
        guard_area,
        TARGET_RETENTION,
        selectivity=guard_selectivity,
        fixed_receiver=None,
    )
    if not guard_summary["all_pass"]:
        raise AssertionError("guard-banded finite-selectivity design did not pass all direct cases")

    threshold_rows = []
    for name in IMPURITIES:
        def component_pass(value: float, component=name) -> bool:
            selectivity = dict(ideal_selectivity)
            selectivity[component] = value
            return evaluate(
                guard_area,
                TARGET_RETENTION,
                selectivity=selectivity,
                fixed_receiver=guard_receiver,
            )[2]["all_pass"]

        minimum_alpha = minimum_passing_positive_log(
            1.0, 1.0e12, component_pass, iterations=24
        )
        threshold_rows.append(
            {
                "impurity": name,
                "low_stage_screen_selectivity": base_selectivity[name],
                "dynamic_minimum_effective_selectivity": minimum_alpha,
                "dynamic_to_low_stage_ratio": minimum_alpha / base_selectivity[name],
                "guard_banded_selected_selectivity": guard_selectivity[name],
                "guard_to_dynamic_threshold_ratio": guard_selectivity[name] / minimum_alpha,
            }
        )

    def defect_pass(value: float) -> bool:
        return evaluate(
            guard_area,
            TARGET_RETENTION,
            defect=value,
            fixed_receiver=guard_receiver,
        )[2]["all_pass"]

    if defect_pass(0.1):
        maximum_defect_ratio = 0.1
    else:
        low, high = 0.0, 0.1
        for _ in range(28):
            middle = 0.5 * (low + high)
            if defect_pass(middle):
                low = middle
            else:
                high = middle
        maximum_defect_ratio = low
    defect_guard_ratio = 0.8 * maximum_defect_ratio
    defect_rows, _defect_receiver, defect_summary = evaluate(
        guard_area,
        TARGET_RETENTION,
        defect=defect_guard_ratio,
        fixed_receiver=guard_receiver,
    )
    if not defect_summary["all_pass"]:
        raise AssertionError("guard-banded defect scenario failed")

    retention_values = (0.70, 0.80, 0.85, 0.90, 0.95, 1.00)
    multiplier_values = (0.50, 1.00, 2.00, 5.00, 10.00, 20.00, 50.00, 100.00, 200.00)
    grid_rows = []
    for retention in retention_values:
        for multiplier in multiplier_values:
            selectivity = {
                name: base_selectivity[name] * multiplier for name in IMPURITIES
            }
            _rows, receiver, summary = evaluate(
                original_area,
                retention,
                selectivity=selectivity,
                fixed_receiver=original_receiver,
            )
            grid_rows.append(
                {
                    "pd_area_m2": original_area,
                    "permeance_retention": retention,
                    "common_selectivity_multiplier": multiplier,
                    **summary,
                }
            )

    pdau_selectivity = {"CO": 1.0e12, "CO2": 630.0, "N2": 500.0, "CH4": 350.0}
    _pdau_rows, pdau_receiver, pdau_summary = evaluate(
        original_area,
        1.0,
        selectivity=pdau_selectivity,
        fixed_receiver=original_receiver,
    )
    pure_pd_n2 = {"CO": 1.0e12, "CO2": 1.0e12, "N2": 6000.0, "CH4": 1.0e12}
    _pure_rows, pure_receiver, pure_summary = evaluate(
        original_area,
        1.0,
        selectivity=pure_pd_n2,
        fixed_receiver=original_receiver,
    )
    literature_rows = [
        {
            "scenario": "Pd-Au 2018 reported pure-gas selectivities; CO treated ideal",
            "co_selectivity": "unresolved/idealized",
            "co2_selectivity": 630.0,
            "n2_selectivity": 500.0,
            "ch4_selectivity": 350.0,
            "pass_count": pdau_summary["pass_count"],
            "case_count": pdau_summary["case_count"],
            "maximum_co2_ppm": pdau_summary["maximum_co2_ppm"],
            "maximum_n2_ppm": pdau_summary["maximum_n2_ppm"],
            "maximum_ch4_ppm": pdau_summary["maximum_ch4_ppm"],
            "doi_or_source": "10.1016/j.cattod.2018.04.029",
            "interpretation": "component selectivities are pure-gas anchors and do not close the simultaneous project gate",
        },
        {
            "scenario": "pure Pd H2/N2 lower-bound anchor; other impurities ideal",
            "co_selectivity": "idealized",
            "co2_selectivity": "idealized",
            "n2_selectivity": 6000.0,
            "ch4_selectivity": "idealized",
            "pass_count": pure_summary["pass_count"],
            "case_count": pure_summary["case_count"],
            "maximum_co2_ppm": pure_summary["maximum_co2_ppm"],
            "maximum_n2_ppm": pure_summary["maximum_n2_ppm"],
            "maximum_ch4_ppm": pure_summary["maximum_ch4_ppm"],
            "doi_or_source": "OSTI 898816",
            "interpretation": "supports the N2 gate only; simultaneous CO/CO2/CH4 evidence remains absent",
        },
        {
            "scenario": "2026 defect-free mixed-gas Pd membrane",
            "co_selectivity": "no impurity detected",
            "co2_selectivity": "no impurity detected",
            "n2_selectivity": "no impurity detected",
            "ch4_selectivity": "not reported in the accessible mixed-gas statement",
            "pass_count": "not numerically assignable",
            "case_count": 16,
            "maximum_co2_ppm": "detection limit not matched to 5 ppm gate",
            "maximum_n2_ppm": "detection limit not matched to 300 ppm gate",
            "maximum_ch4_ppm": "not closed",
            "doi_or_source": "10.1016/j.ijhydene.2026.154365",
            "interpretation": "300 h stability and mixed-gas integrity are encouraging, but project-specific detection limits are required",
        },
    ]

    write_csv(OUT_GRID, grid_rows)
    write_csv(OUT_THRESHOLDS, threshold_rows)
    write_csv(OUT_CASES, guard_rows)
    write_csv(OUT_LITERATURE, literature_rows)

    max_balance = max(
        max(row["receiver_mass_balance_max_abs_mol"] for row in guard_rows),
        max(row["module_mass_balance_max_abs_mol"] for row in guard_rows),
    )
    payload = {
        "schema": "psa-pd-leakage-aging-sensitivity/v1",
        "status": "finite_pd_leakage_aging_guard_band_quantified",
        "original_literature_bounded_design": {
            "pd_area_m2": original_area,
            "receiver_capacity_mol": original_receiver,
            "minimum_ideal_selectivity_permeance_retention_for_all_16": minimum_retention_original,
            "maximum_tolerable_permeance_loss_fraction": 1.0 - minimum_retention_original,
        },
        "guard_banded_20_percent_retention_design": {
            "target_permeance_retention": TARGET_RETENTION,
            "minimum_effective_pd_area_at_full_permeance_m2": minimum_effective_area,
            "minimum_scaled_pd_area_m2": area_for_20pct_retention,
            "selected_rounded_pd_area_m2": guard_area,
            "area_increase_vs_original_percent": 100.0 * (guard_area / original_area - 1.0),
            "minimum_common_selectivity_multiplier": minimum_common_multiplier,
            "selected_common_selectivity_multiplier": guard_multiplier,
            "selected_effective_selectivity": guard_selectivity,
            "co_sized_receiver_capacity_mol": guard_receiver,
            "co_sized_receiver_volume_L_at_1bar_298K": guard_receiver
            * train.R_J_MOL_K
            * train.COMPRESSION_T_K
            / train.PD_PERMEATE_PRESSURE_PA
            * 1000.0,
            "direct_confirmation": guard_summary,
            "maximum_mass_balance_abs_mol": max_balance,
        },
        "component_thresholds": threshold_rows,
        "defect_leakage_boundary": {
            "definition": (
                "local H2-equivalent Knudsen defect H2 transfer divided by dense-Pd H2 transfer; "
                "this is a conductance ratio, not a geometric pinhole-area fraction"
            ),
            "maximum_passing_ratio": maximum_defect_ratio,
            "guard_banded_ratio": defect_guard_ratio,
            "guard_banded_direct_confirmation": defect_summary,
            "approximate_effective_selectivity_at_maximum_ratio": {
                name: (1.0 + maximum_defect_ratio)
                / max(
                    maximum_defect_ratio
                    * math.sqrt(MOLECULAR_WEIGHT["H2"] / MOLECULAR_WEIGHT[name]),
                    1.0e-30,
                )
                for name in IMPURITIES
            },
        },
        "literature_anchors": [
            {
                "source": "Iulianelli et al. Pd-Au membrane",
                "doi": "10.1016/j.cattod.2018.04.029",
                "use": "reported finite pure-gas H2/N2, H2/CO2, and H2/CH4 selectivities",
            },
            {
                "source": "continuous-flow electroless pore-plated Pd membrane",
                "doi": "10.1016/j.ijhydene.2026.154365",
                "use": "mixed-gas integrity, approximately plus/minus 20 percent permeance reproducibility, and 300 h stability; detection limits remain unmatched",
            },
            {
                "source": "Zito et al. multistage concentration plus Pd process",
                "doi": "10.1016/j.renene.2023.119243",
                "use": "Pd permeance, pressure, and flow-scaled architecture anchor; source Pd selectivity is ideal",
            },
        ],
        "literature_scenario_results": literature_rows,
        "model_scope": {
            "included": (
                "packet-wise finite effective selectivity, Pd permeance retention, Knudsen-like defect leakage, "
                "co-sized product receiver, frozen recovery/shipment thresholds, and all 16 dynamic cases"
            ),
            "excluded": (
                "temperature-dependent inhibition kinetics, healing or crack growth, concentration polarization, "
                "module pressure drop, heating duty, and experimentally measured detection limits"
            ),
        },
        "claim_boundary": {
            "allowed": (
                "The conditional model quantifies the effective selectivity, conductance-leak, area, and receiver "
                "guard bands required to preserve the declared engineering event under 20 percent Pd permeance loss."
            ),
            "not_allowed": (
                "A commercial Pd module has demonstrated simultaneous compliance with the declared CO/CO2/N2/CH4 "
                "limits or that the calculated conductance ratio equals a measured geometric defect fraction."
            ),
        },
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Finite Pd leakage and aging sensitivity",
        "",
        f"The original {original_area:.4f}-m² Pd design tolerates only **{100*(1-minimum_retention_original):.2f}%** permeance loss while retaining all 16 direct engineering events under effectively infinite selectivity.",
        "",
        f"A design intended to retain only 80% of the source permeance requires **{guard_area:.3f} m²** of Pd area and a co-sized **{guard_receiver:.4f}-mol** product receiver. This is **{100*(guard_area/original_area-1):.2f}%** more Pd area than the literature-bounded reference.",
        "",
        f"The minimum common effective-selectivity multiplier is **{minimum_common_multiplier:.4f}** relative to the stage-1 screening requirements. Applying a 25% guard band gives **{guard_multiplier:.2f}×** and passes **{guard_summary['pass_count']}/16** direct cases.",
        "",
        f"The maximum passing H2-equivalent Knudsen defect conductance ratio is **{maximum_defect_ratio:.3e}**. This is a conductance ratio, not a pinhole-area fraction.",
        "",
        "The available public experiments do not report all four project impurity limits together at matching detection limits. The result therefore defines module acceptance tests; it does not certify an existing membrane.",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    fig, axes = plt.subplots(2, 2, figsize=(12.4, 8.8), constrained_layout=True)
    matrix = np.zeros((len(retention_values), len(multiplier_values)))
    for row in grid_rows:
        i = retention_values.index(row["permeance_retention"])
        j = multiplier_values.index(row["common_selectivity_multiplier"])
        matrix[i, j] = row["pass_count"]
    image = axes[0, 0].imshow(matrix, origin="lower", aspect="auto", cmap="viridis", vmin=0, vmax=16)
    axes[0, 0].set_xticks(range(len(multiplier_values)), [str(value) for value in multiplier_values], rotation=45)
    axes[0, 0].set_yticks(range(len(retention_values)), [f"{value:.2f}" for value in retention_values])
    axes[0, 0].set(xlabel="Selectivity multiplier", ylabel="Pd permeance retention", title="(a) Passing direct cases at 0.4799 m²")
    fig.colorbar(image, ax=axes[0, 0], label="Pass count (of 16)")

    ideal_rows = []
    for retention in np.linspace(0.70, 1.0, 9):
        _rows, _receiver, summary = evaluate(
            original_area,
            float(retention),
            selectivity=ideal_selectivity,
            fixed_receiver=original_receiver,
        )
        ideal_rows.append((retention, summary))
    axes[0, 1].plot(
        [row[0] for row in ideal_rows],
        [100 * row[1]["minimum_recovery"] for row in ideal_rows],
        "o-",
        label="minimum recovery",
        color="#2563eb",
    )
    axes[0, 1].axhline(100 * recovery_floor, color="#2563eb", linestyle=":")
    twin = axes[0, 1].twinx()
    twin.plot(
        [row[0] for row in ideal_rows],
        [row[1]["minimum_qualified_h2_rate_mol_s"] for row in ideal_rows],
        "s--",
        label="minimum shipment",
        color="#ef4444",
    )
    twin.axhline(shipment_floor, color="#ef4444", linestyle=":")
    axes[0, 1].axvline(minimum_retention_original, color="#059669", linestyle="--")
    axes[0, 1].set(xlabel="Pd permeance retention", ylabel="H2 recovery (%)", title="(b) Aging margin at fixed Pd area")
    twin.set_ylabel("Qualified H2 rate (mol s$^{-1}$)")
    h1, l1 = axes[0, 1].get_legend_handles_labels()
    h2, l2 = twin.get_legend_handles_labels()
    axes[0, 1].legend(h1 + h2, l1 + l2, fontsize=8, frameon=False)

    names = [row["impurity"] for row in threshold_rows]
    x = np.arange(len(names))
    width = 0.36
    axes[1, 0].bar(
        x - width / 2,
        [row["dynamic_minimum_effective_selectivity"] for row in threshold_rows],
        width,
        label="dynamic minimum",
        color="#f59e0b",
    )
    axes[1, 0].bar(
        x + width / 2,
        [row["guard_banded_selected_selectivity"] for row in threshold_rows],
        width,
        label="selected guard band",
        color="#7c3aed",
    )
    axes[1, 0].set_yscale("log")
    axes[1, 0].set_xticks(x, names)
    axes[1, 0].set(ylabel="Effective H2/impurity selectivity", title="(c) Component acceptance thresholds")
    axes[1, 0].legend(fontsize=8, frameon=False)

    defect_scan = np.logspace(-7, -2, 17)
    defect_factors = []
    for value in defect_scan:
        _rows, _receiver, summary = evaluate(
            guard_area,
            TARGET_RETENTION,
            defect=float(value),
            fixed_receiver=guard_receiver,
        )
        defect_factors.append(summary["maximum_worst_gate_factor"])
    axes[1, 1].loglog(defect_scan, defect_factors, "o-", color="#0f766e", markersize=3)
    axes[1, 1].axhline(1.0, color="#dc2626", linestyle=":", label="strict product gate")
    axes[1, 1].axvline(maximum_defect_ratio, color="#7c3aed", linestyle="--", label="maximum passing ratio")
    axes[1, 1].set(xlabel="H2-equivalent defect conductance ratio", ylabel="Worst product-gate factor", title="(d) Defect leakage boundary")
    axes[1, 1].legend(fontsize=8, frameon=False)
    for axis in axes.flat:
        axis.grid(alpha=0.25)
    for suffix in ("png", "pdf", "svg"):
        fig.savefig(OUT / f"{OUT_FIGURE.name}.{suffix}", dpi=300, bbox_inches="tight")
    plt.close(fig)

    source_paths = [TRAIN_JSON, V20_JSON, REQUIREMENT_JSON]
    for case in cases:
        source_paths.extend([case["state_path"], case["trace_path"]])
    output_paths = [
        OUT_JSON,
        OUT_MD,
        OUT_GRID,
        OUT_THRESHOLDS,
        OUT_CASES,
        OUT_LITERATURE,
        OUT / f"{OUT_FIGURE.name}.png",
        OUT / f"{OUT_FIGURE.name}.pdf",
        OUT / f"{OUT_FIGURE.name}.svg",
    ]
    manifest = {
        "schema": "psa-pd-leakage-aging-sensitivity-manifest/v1",
        "sources": [
            {
                "path": str(path.relative_to(ROOT)),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
            for path in source_paths
        ],
        "outputs": [
            {
                "path": str(path.relative_to(ROOT)),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
            for path in output_paths
        ],
    }
    OUT_MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": payload["status"],
                "original_design": payload["original_literature_bounded_design"],
                "guard_banded_design": payload["guard_banded_20_percent_retention_design"],
                "defect_boundary": payload["defect_leakage_boundary"],
                "outputs": [str(path) for path in output_paths] + [str(OUT_MANIFEST)],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
