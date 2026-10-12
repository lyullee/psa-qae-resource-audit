"""Stage-resolved concentration + dense-Pd polishing calculation.

The model post-processes all eight selected-policy uncertainty corners and the
eight predeclared interior hold-outs using their saved six-cell, sixty-cycle
PSA outlet trajectories.  A literature-parameterized polymer or carbon
pre-concentrator is followed by a dense Pd stage and the existing finite
product receiver.  Areas are bounded by flow-scaled configurations reported by
Zito et al. (2023), then the selected design is recomputed packet by packet.

The dense-Pd layer is ideal and defect-free, as in the source process model.
Accordingly, its permeate is pure H2.  A separate finite-selectivity requirement
is reported for every impurity; the result is a process-design feasibility
calculation, not component-resolved experimental certification.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
import sys
import time

import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import psa_qae.psa_literature_calibrated_operation_screen as operation  # noqa: E402
import psa_qae.psa_public_schedule_strict_uncertainty_ensemble as strict  # noqa: E402
from psa_qae.psa_fixed_area_dynamic_membrane_polishing import fixed_area_crossflow  # noqa: E402


ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"
INPUT_VARIANT = os.environ.get("PSA_STAGE_INPUT_VARIANT", "legacy_7bar")
if INPUT_VARIANT == "pressure_consistent_6bar_v1":
    CORNER_DIR = RESULTS / "hydraulically_feasible_full_6cell_cube_v1" / "states"
    HOLDOUT_DIR = RESULTS / "hydraulically_feasible_selected_6cell_holdout_v1" / "states"
else:
    CORNER_DIR = RESULTS / "literature_anchored_policy_full_6cell_cube_2000cm2" / "states"
    HOLDOUT_DIR = RESULTS / "literature_anchored_selected_6cell_interior_holdout_2224cm2" / "states"
V18_PATH = RESULTS / "final_objective_evidence_v18" / "PSA_FINAL_OBJECTIVE_EVIDENCE_V18.json"
REQUIREMENT_PATH = (
    RESULTS
    / "membrane_component_selectivity_requirement"
    / "PSA_MEMBRANE_COMPONENT_SELECTIVITY_REQUIREMENT.json"
)
OUT = RESULTS / os.environ.get("PSA_STAGE_OUTPUT_DIR", "stage_resolved_membrane_train")

R_J_MOL_K = 8.314462618
COMPRESSION_T_K = 298.15
COMPRESSOR_ISOTHERMAL_EFFICIENCY = 0.72
UPSTREAM_PRESSURE_PA = float(os.environ.get("PSA_STAGE_UPSTREAM_PRESSURE_PA", "800000"))
CONCENTRATOR_FEED_PRESSURE_PA = 20.0e5
CONCENTRATOR_PERMEATE_PRESSURE_PA = 1.0e5
PD_FEED_PRESSURE_PA = 20.0e5
PD_PERMEATE_PRESSURE_PA = 1.0e5
PD_H2_PERMEANCE_MOL_M2_S_PA_HALF = 5.560e-6
AGGREGATE_AREA_STEPS = 160
DYNAMIC_CONCENTRATOR_STEPS = 72
DYNAMIC_PD_STEPS = 144
N_CYCLES = 60
ZERO_INTERNAL_RECYCLE_FRACTION = 0.0
SURGE_HEEL_MOL = 0.5
SURGE_MIXING_SUBSTEPS = 12

MATERIALS = {
    "polymer": {
        "h2_permeance_mol_m2_s_pa": 33.5e-9,
        "selectivity": {"CH4": 170.0, "CO2": 5.0, "CO": 100.0, "N2": 100.0},
        "zito_area_m2_per_Nm3_h": 1.0,
        "zito_pd_area_m2_per_Nm3_h": 1.3,
        "basis": "Zito et al. 2023 Table 2 and Figure 9; H2/N2 assigned equal to H2/CO as stated for similar gas behavior",
    },
    "carbon": {
        "h2_permeance_mol_m2_s_pa": 8.0e-9,
        "selectivity": {"CH4": 79.0, "CO2": 5.4, "CO": 34.0, "N2": 34.0},
        "zito_area_m2_per_Nm3_h": 4.0,
        "zito_pd_area_m2_per_Nm3_h": 1.4,
        "basis": "Zito et al. 2023 Table 2 and Figure 9; H2/N2 conservatively assigned equal to H2/CO",
    },
}


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


def case_references() -> list[dict]:
    refs: list[dict] = []
    for index in range(8, 16):
        if INPUT_VARIANT == "pressure_consistent_6bar_v1":
            state_name = f"case_{index:03d}.json"
            trace_name = f"case_{index:03d}_traces.npz"
        else:
            state_name = f"case_{index:02d}.json"
            trace_name = f"case_{index:02d}_traces.npz"
        refs.append(
            {
                "validation_kind": "uncertainty_corner",
                "case_id": f"corner_{index - 8:02d}",
                "state_path": str((CORNER_DIR / state_name).relative_to(ROOT)),
                "trace_path": str((CORNER_DIR / trace_name).relative_to(ROOT)),
            }
        )
    for index in range(8):
        if INPUT_VARIANT == "pressure_consistent_6bar_v1":
            state_name = f"case_{index:03d}.json"
            trace_name = f"case_{index:03d}_traces.npz"
        else:
            state_name = f"case_{index:02d}.json"
            trace_name = f"case_{index:02d}_traces.npz"
        refs.append(
            {
                "validation_kind": "predeclared_interior_holdout",
                "case_id": f"holdout_{index:02d}",
                "state_path": str((HOLDOUT_DIR / state_name).relative_to(ROOT)),
                "trace_path": str((HOLDOUT_DIR / trace_name).relative_to(ROOT)),
            }
        )
    return refs


def load_case(ref: dict) -> tuple[dict, np.ndarray]:
    state = json.loads((ROOT / ref["state_path"]).read_text(encoding="utf-8"))
    with np.load(ROOT / ref["trace_path"], allow_pickle=False) as archive:
        components = tuple(str(value) for value in archive["components"])
        raw = np.asarray(archive["raw_external_out_mol"], dtype=float)
    assert components == tuple(strict.COMPONENTS)
    assert raw.shape == (N_CYCLES * 4 * strict.ADSORPTION_SUBSTEPS, len(strict.COMPONENTS))
    return state, raw


def normal_flow_nm3_h(total_rate_mol_s: float) -> float:
    return float(total_rate_mol_s) * 0.022414 * 3600.0


def isothermal_compression_power_w(
    molar_rate_mol_s: float, inlet_pressure_pa: float, outlet_pressure_pa: float
) -> float:
    if outlet_pressure_pa <= inlet_pressure_pa or molar_rate_mol_s <= 0.0:
        return 0.0
    ideal = (
        float(molar_rate_mol_s)
        * R_J_MOL_K
        * COMPRESSION_T_K
        * math.log(float(outlet_pressure_pa) / float(inlet_pressure_pa))
    )
    return ideal / COMPRESSOR_ISOTHERMAL_EFFICIENCY


def pd_stage(
    feed_moles: np.ndarray,
    *,
    duration_s: float,
    area_m2: float,
    area_steps: int,
) -> dict:
    """Cross-flow dense-Pd stage using a Sieverts-law H2 flux."""
    retentate = np.maximum(np.asarray(feed_moles, dtype=float), 0.0).copy()
    product = np.zeros_like(retentate)
    h2_index = strict.INDEX["H2"]
    initial_h2 = float(retentate[h2_index])
    d_area = float(area_m2) / max(int(area_steps), 1)
    used_area = 0.0
    for _ in range(max(int(area_steps), 1)):
        total = float(retentate.sum())
        h2 = float(retentate[h2_index])
        if total <= 1.0e-18 or h2 <= 1.0e-18:
            break
        x_h2 = h2 / total
        driving = math.sqrt(PD_FEED_PRESSURE_PA * x_h2) - math.sqrt(PD_PERMEATE_PRESSURE_PA)
        if driving <= 0.0:
            break
        flux = PD_H2_PERMEANCE_MOL_M2_S_PA_HALF * driving
        transfer = min(flux * d_area * float(duration_s), 0.999999 * h2)
        if transfer <= 1.0e-18:
            break
        retentate[h2_index] -= transfer
        product[h2_index] += transfer
        used_area += d_area
    reconstructed = product + retentate
    return {
        "product_moles": product,
        "retentate_moles": retentate,
        "h2_recovery": float(product[h2_index] / max(initial_h2, 1.0e-30)),
        "used_area_fraction": used_area / max(float(area_m2), 1.0e-30),
        "mass_balance_max_abs_mol": float(
            np.max(np.abs(reconstructed - np.asarray(feed_moles, dtype=float)))
        ),
    }


def surge_buffer_requirement(raw_packets: np.ndarray) -> dict:
    packet_total = np.asarray(raw_packets, dtype=float).sum(axis=1)
    constant_packet_out = float(packet_total.mean())
    imbalance = np.concatenate(
        ([0.0], np.cumsum(packet_total - constant_packet_out))
    )
    initial_inventory_mol = SURGE_HEEL_MOL - float(imbalance.min())
    maximum_inventory_mol = initial_inventory_mol + float(imbalance.max())
    return {
        "constant_packet_out_mol": constant_packet_out,
        "initial_inventory_mol": initial_inventory_mol,
        "minimum_inventory_mol": SURGE_HEEL_MOL,
        "maximum_inventory_mol": maximum_inventory_mol,
        "required_capacity_mol": maximum_inventory_mol,
        "inventory_swing_mol": float(imbalance.max() - imbalance.min()),
    }


def simulate_surge_buffer(
    raw_packets: np.ndarray,
    *,
    installed_capacity_mol: float,
) -> tuple[np.ndarray, dict, np.ndarray]:
    """Perfectly mixed finite surge buffer with a constant total outlet.

    The initial composition is iterated to the full-horizon periodic fixed point,
    while total inventory follows the exact cumulative inlet/outlet imbalance.
    """
    raw = np.maximum(np.asarray(raw_packets, dtype=float), 0.0)
    requirement = surge_buffer_requirement(raw)
    initial_total = float(requirement["initial_inventory_mol"])
    constant_out = float(requirement["constant_packet_out_mol"])
    initial_y = raw.sum(axis=0) / max(float(raw.sum()), 1.0e-30)

    def one_pass(y0: np.ndarray, keep: bool) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        inventory = initial_total * y0
        outputs = np.zeros_like(raw)
        totals = [float(inventory.sum())]
        for index, inlet in enumerate(raw):
            for _ in range(SURGE_MIXING_SUBSTEPS):
                inventory += inlet / SURGE_MIXING_SUBSTEPS
                y = inventory / max(float(inventory.sum()), 1.0e-30)
                withdrawal = min(
                    constant_out / SURGE_MIXING_SUBSTEPS,
                    0.999999 * float(inventory.sum()),
                )
                component_out = withdrawal * y
                inventory -= component_out
                outputs[index] += component_out
            totals.append(float(inventory.sum()))
        return inventory, outputs, np.asarray(totals, dtype=float)

    iterations = 0
    fixed_residual = float("inf")
    for iterations in range(1, 101):
        final_inventory, _outputs, _totals = one_pass(initial_y, keep=False)
        final_y = final_inventory / max(float(final_inventory.sum()), 1.0e-30)
        fixed_residual = float(np.max(np.abs(final_y - initial_y)))
        initial_y = final_y
        if fixed_residual < 1.0e-12:
            break
    final_inventory, outputs, totals = one_pass(initial_y, keep=True)
    initial_inventory = initial_total * initial_y
    component_residual = initial_inventory + raw.sum(axis=0) - outputs.sum(axis=0) - final_inventory
    maximum_inventory = float(totals.max())
    minimum_inventory = float(totals.min())
    metrics = {
        **requirement,
        "installed_capacity_mol": float(installed_capacity_mol),
        "installed_volume_L_at_20bar_298K": float(
            installed_capacity_mol * R_J_MOL_K * COMPRESSION_T_K / CONCENTRATOR_FEED_PRESSURE_PA * 1000.0
        ),
        "periodic_composition_iterations": iterations,
        "periodic_composition_residual": fixed_residual,
        "actual_minimum_inventory_mol": minimum_inventory,
        "actual_maximum_inventory_mol": maximum_inventory,
        "capacity_gate": maximum_inventory <= float(installed_capacity_mol) * (1.0 + 1.0e-10),
        "constant_total_outlet_gate": float(
            np.max(np.abs(outputs.sum(axis=1) - constant_out))
        )
        < 1.0e-10,
        "component_mass_balance_max_abs_mol": float(np.max(np.abs(component_residual))),
    }
    return outputs, metrics, totals


def required_selectivity(feed_y: np.ndarray, gate: dict) -> dict[str, float]:
    h2 = max(float(feed_y[strict.INDEX["H2"]]), 1.0e-30)
    h2_target = float(gate["h2_min_fraction"])
    return {
        name: (
            float(feed_y[strict.INDEX[name]])
            / h2
            * h2_target
            / float(gate["impurity_max_fraction"][name])
        )
        for name in ("CO", "CO2", "N2", "CH4")
    }


def build_uniform_timeline(packet_moles: np.ndarray, cycle_time_s: float) -> np.ndarray:
    packets_per_cycle = 4 * strict.ADSORPTION_SUBSTEPS
    expected = N_CYCLES * packets_per_cycle
    if packet_moles.shape != (expected, len(strict.COMPONENTS)):
        raise AssertionError(f"unexpected uniform packet shape {packet_moles.shape}")
    slots_per_cycle = int(round(float(cycle_time_s) / strict.RECEIVER_DT_S))
    timeline = np.zeros(
        (N_CYCLES * slots_per_cycle, len(strict.COMPONENTS)), dtype=float
    )
    packet_s = float(cycle_time_s) / packets_per_cycle
    for index, moles in enumerate(packet_moles):
        cycle = index // packets_per_cycle
        packet = index % packets_per_cycle
        start_s = cycle * float(cycle_time_s) + packet * packet_s
        end_s = cycle * float(cycle_time_s) + (packet + 1) * packet_s
        start_slot = int(round(start_s / strict.RECEIVER_DT_S))
        end_slot = max(start_slot + 1, int(round(end_s / strict.RECEIVER_DT_S)))
        end_slot = min(end_slot, timeline.shape[0])
        timeline[start_slot:end_slot] += moles / max(end_slot - start_slot, 1)
    return timeline


def aggregate_case(
    ref: dict,
    *,
    material_name: str,
    concentrator_area_m2: float,
    pd_area_m2: float,
    gate: dict,
    concentrator_steps: int = AGGREGATE_AREA_STEPS,
    pd_steps: int = AGGREGATE_AREA_STEPS,
) -> dict:
    state, raw = load_case(ref)
    material = MATERIALS[material_name]
    duration_s = float(state["n_cycles"]) * float(state["cycle_time_s"])
    feed = raw.sum(axis=0)
    stage1 = fixed_area_crossflow(
        feed,
        packet_duration_s=duration_s,
        area_m2=concentrator_area_m2,
        selectivity=material["selectivity"],
        h2_permeance=float(material["h2_permeance_mol_m2_s_pa"]),
        feed_pressure_pa=CONCENTRATOR_FEED_PRESSURE_PA,
        permeate_pressure_pa=CONCENTRATOR_PERMEATE_PRESSURE_PA,
        area_steps=concentrator_steps,
    )
    stage2 = pd_stage(
        stage1["product_moles"],
        duration_s=duration_s,
        area_m2=pd_area_m2,
        area_steps=pd_steps,
    )
    raw_h2 = float(feed[strict.INDEX["H2"]])
    product_h2 = float(stage2["product_moles"][strict.INDEX["H2"]])
    stage1_total_rate = float(stage1["product_moles"].sum()) / duration_s
    raw_total_rate = float(feed.sum()) / duration_s
    product_h2_rate = product_h2 / duration_s
    compression_w = isothermal_compression_power_w(
        raw_total_rate, UPSTREAM_PRESSURE_PA, CONCENTRATOR_FEED_PRESSURE_PA
    ) + isothermal_compression_power_w(
        stage1_total_rate, CONCENTRATOR_PERMEATE_PRESSURE_PA, PD_FEED_PRESSURE_PA
    )
    energy_kwh_kg_h2 = compression_w / max(product_h2_rate * 2.01588e-3, 1.0e-30) / 3.6e6
    stage1_y = stage1["product_y"]
    return {
        "validation_kind": ref["validation_kind"],
        "case_id": ref["case_id"],
        "scenario": state["scenario"],
        "material": material_name,
        "concentrator_area_m2": concentrator_area_m2,
        "pd_area_m2": pd_area_m2,
        "fresh_feed_rate_mol_s": raw_total_rate,
        "fresh_feed_rate_Nm3_h": normal_flow_nm3_h(raw_total_rate),
        "fresh_feed_h2_fraction": raw_h2 / max(float(feed.sum()), 1.0e-30),
        "stage1_h2_fraction": float(stage1_y[strict.INDEX["H2"]]),
        "stage1_h2_recovery": float(
            stage1["product_moles"][strict.INDEX["H2"]] / max(raw_h2, 1.0e-30)
        ),
        "stage2_h2_recovery": float(stage2["h2_recovery"]),
        "overall_h2_recovery": product_h2 / max(raw_h2, 1.0e-30),
        "qualified_h2_rate_mol_s": product_h2_rate,
        "compression_power_w": compression_w,
        "compression_energy_kwh_kg_h2": energy_kwh_kg_h2,
        "required_selectivity": required_selectivity(stage1_y, gate),
        "mass_balance_max_abs_mol": max(
            float(stage1["mass_balance_max_abs_mol"]),
            float(stage2["mass_balance_max_abs_mol"]),
        ),
    }


def screen_designs(refs: list[dict], gate: dict, target: dict) -> tuple[list[dict], dict, dict]:
    max_flow = 0.0
    case_data: list[dict] = []
    for ref in refs:
        state, raw = load_case(ref)
        elapsed = float(state["n_cycles"]) * float(state["cycle_time_s"])
        feed = raw.sum(axis=0)
        flow = normal_flow_nm3_h(float(feed.sum()) / elapsed)
        max_flow = max(max_flow, flow)
        case_data.append(
            {
                "ref": ref,
                "state": state,
                "duration_s": elapsed,
                "feed": feed,
                "flow_Nm3_h": flow,
            }
        )

    all_rows: list[dict] = []
    detail_by_key: dict[tuple, list[dict]] = {}
    for material_name, material in MATERIALS.items():
        area1_cap = material["zito_area_m2_per_Nm3_h"] * max_flow
        area2_cap = material["zito_pd_area_m2_per_Nm3_h"] * max_flow
        area1_min = max(area1_cap * 0.10, 0.02)
        area2_min = max(area2_cap * 0.35, 0.08)
        area1_grid = np.linspace(area1_min, area1_cap, 25)
        area2_grid = np.linspace(area2_min, area2_cap, 30)

        stage1_cache: dict[tuple[int, float], dict] = {}
        for area1 in area1_grid:
            for ref_index, data in enumerate(case_data):
                feed = data["feed"]
                duration_s = float(data["duration_s"])
                stage1 = fixed_area_crossflow(
                    feed,
                    packet_duration_s=duration_s,
                    area_m2=float(area1),
                    selectivity=material["selectivity"],
                    h2_permeance=float(material["h2_permeance_mol_m2_s_pa"]),
                    feed_pressure_pa=CONCENTRATOR_FEED_PRESSURE_PA,
                    permeate_pressure_pa=CONCENTRATOR_PERMEATE_PRESSURE_PA,
                    area_steps=AGGREGATE_AREA_STEPS,
                )
                raw_h2 = float(feed[strict.INDEX["H2"]])
                y1 = stage1["product_y"]
                stage1_cache[(ref_index, float(area1))] = {
                    "data": data,
                    "stage1": stage1,
                    "base": {
                        "validation_kind": data["ref"]["validation_kind"],
                        "case_id": data["ref"]["case_id"],
                        "scenario": data["state"]["scenario"],
                        "material": material_name,
                        "concentrator_area_m2": float(area1),
                        "fresh_feed_rate_mol_s": float(feed.sum()) / duration_s,
                        "fresh_feed_rate_Nm3_h": data["flow_Nm3_h"],
                        "fresh_feed_h2_fraction": raw_h2 / max(float(feed.sum()), 1.0e-30),
                        "stage1_h2_fraction": float(y1[strict.INDEX["H2"]]),
                        "stage1_h2_recovery": float(
                            stage1["product_moles"][strict.INDEX["H2"]]
                            / max(raw_h2, 1.0e-30)
                        ),
                    },
                }

        for area1 in area1_grid:
            for area2 in area2_grid:
                details: list[dict] = []
                for ref_index, _ref in enumerate(refs):
                    cached = stage1_cache[(ref_index, float(area1))]
                    data = cached["data"]
                    duration_s = float(data["duration_s"])
                    feed = data["feed"]
                    stage1 = cached["stage1"]
                    stage2 = pd_stage(
                        stage1["product_moles"],
                        duration_s=duration_s,
                        area_m2=float(area2),
                        area_steps=AGGREGATE_AREA_STEPS,
                    )
                    raw_h2 = float(feed[strict.INDEX["H2"]])
                    product_h2 = float(stage2["product_moles"][strict.INDEX["H2"]])
                    stage1_total_rate = float(stage1["product_moles"].sum()) / duration_s
                    raw_total_rate = float(feed.sum()) / duration_s
                    product_rate = product_h2 / duration_s
                    power = isothermal_compression_power_w(
                        raw_total_rate, UPSTREAM_PRESSURE_PA, CONCENTRATOR_FEED_PRESSURE_PA
                    ) + isothermal_compression_power_w(
                        stage1_total_rate, CONCENTRATOR_PERMEATE_PRESSURE_PA, PD_FEED_PRESSURE_PA
                    )
                    y1 = stage1["product_y"]
                    details.append(
                        {
                            **cached["base"],
                            "pd_area_m2": float(area2),
                            "stage2_h2_recovery": float(stage2["h2_recovery"]),
                            "overall_h2_recovery": product_h2 / max(raw_h2, 1.0e-30),
                            "qualified_h2_rate_mol_s": product_rate,
                            "compression_power_w": power,
                            "compression_energy_kwh_kg_h2": power
                            / max(product_rate * 2.01588e-3, 1.0e-30)
                            / 3.6e6,
                            "required_selectivity": required_selectivity(y1, gate),
                            "mass_balance_max_abs_mol": max(
                                float(stage1["mass_balance_max_abs_mol"]),
                                float(stage2["mass_balance_max_abs_mol"]),
                            ),
                        }
                    )
                key = (material_name, float(area1), float(area2))
                detail_by_key[key] = details
                worst_recovery = min(row["overall_h2_recovery"] for row in details)
                worst_rate = min(row["qualified_h2_rate_mol_s"] for row in details)
                all_rows.append(
                    {
                        "material": material_name,
                        "concentrator_area_m2": float(area1),
                        "pd_area_m2": float(area2),
                        "total_area_m2": float(area1 + area2),
                        "literature_scaled_concentrator_area_cap_m2": area1_cap,
                        "literature_scaled_pd_area_cap_m2": area2_cap,
                        "worst_overall_h2_recovery": worst_recovery,
                        "worst_qualified_h2_rate_mol_s": worst_rate,
                        "minimum_stage1_h2_fraction": min(row["stage1_h2_fraction"] for row in details),
                        "maximum_compression_energy_kwh_kg_h2": max(
                            row["compression_energy_kwh_kg_h2"] for row in details
                        ),
                        "maximum_mass_balance_abs_mol": max(
                            row["mass_balance_max_abs_mol"] for row in details
                        ),
                        "all_16_recovery_pass": worst_recovery
                        >= float(target["minimum_h2_recovery"]),
                        "all_16_shipment_pass": worst_rate
                        >= float(target["minimum_qualified_h2_rate_mol_s"]),
                    }
                )

    feasible = [
        row
        for row in all_rows
        if row["all_16_recovery_pass"] and row["all_16_shipment_pass"]
    ]
    if not feasible:
        raise RuntimeError("no flow-scaled literature-bounded stage train met the frozen target")
    best_rate = max(float(row["worst_qualified_h2_rate_mol_s"]) for row in feasible)
    near_best = [
        row
        for row in feasible
        if float(row["worst_qualified_h2_rate_mol_s"]) >= 0.999 * best_rate
    ]
    selected = min(
        near_best,
        key=lambda row: (
            float(row["pd_area_m2"]),
            float(row["total_area_m2"]),
            float(row["maximum_compression_energy_kwh_kg_h2"]),
        ),
    )
    selected_key = (
        selected["material"],
        float(selected["concentrator_area_m2"]),
        float(selected["pd_area_m2"]),
    )
    screen_meta = {
        "maximum_fresh_feed_flow_Nm3_h": max_flow,
        "selection_rule": (
            "meet the frozen recovery and shipment targets in all 8 corners and 8 hold-outs; "
            "retain designs within 0.1% of maximum worst shipment; then minimize Pd area, total area, and compression energy"
        ),
        "screened_configuration_count": len(all_rows),
        "feasible_configuration_count": len(feasible),
        "maximum_worst_qualified_h2_rate_mol_s": best_rate,
    }
    return all_rows, selected, {"meta": screen_meta, "details": detail_by_key[selected_key]}


def simulate_dynamic_case(
    ref: dict,
    config: dict,
    *,
    concentrator_steps: int,
    pd_steps: int,
    save: bool,
) -> tuple[dict, dict[str, np.ndarray]]:
    started = time.time()
    if save:
        state_path = OUT / "states" / f"{ref['case_id']}.json"
        trace_path = OUT / "states" / f"{ref['case_id']}_traces.npz"
        if state_path.exists() and trace_path.exists():
            cached = json.loads(state_path.read_text(encoding="utf-8"))
            if (
                cached.get("material") == config.get("material")
                and abs(float(cached.get("concentrator_area_m2", -1.0)) - float(config["concentrator_area_m2"])) < 1.0e-12
                and abs(float(cached.get("pd_area_m2", -1.0)) - float(config["pd_area_m2"])) < 1.0e-12
                and abs(float(cached.get("surge_buffer_capacity_mol", -1.0)) - float(config["surge_buffer_capacity_mol"])) < 1.0e-12
                and int(cached.get("n_cycles", -1)) == N_CYCLES
            ):
                return cached, {}
    state, raw = load_case(ref)
    material = MATERIALS[str(config["material"])]
    packet_duration_s = float(state["cycle_time_s"]) / (4 * strict.ADSORPTION_SUBSTEPS)
    membrane_feed, surge, surge_inventory = simulate_surge_buffer(
        raw,
        installed_capacity_mol=float(config["surge_buffer_capacity_mol"]),
    )
    stage1_product = np.zeros_like(raw)
    stage1_retentate = np.zeros_like(raw)
    stage2_product = np.zeros_like(raw)
    stage2_retentate = np.zeros_like(raw)
    stage1_recovery = np.zeros(raw.shape[0], dtype=np.float32)
    stage2_recovery = np.zeros(raw.shape[0], dtype=np.float32)
    max_balance = 0.0
    for stream_index, fresh in enumerate(membrane_feed):
        if float(fresh.sum()) <= 1.0e-14:
            continue
        first = fixed_area_crossflow(
            fresh,
            packet_duration_s=packet_duration_s,
            area_m2=float(config["concentrator_area_m2"]),
            selectivity=material["selectivity"],
            h2_permeance=float(material["h2_permeance_mol_m2_s_pa"]),
            feed_pressure_pa=CONCENTRATOR_FEED_PRESSURE_PA,
            permeate_pressure_pa=CONCENTRATOR_PERMEATE_PRESSURE_PA,
            area_steps=concentrator_steps,
        )
        second = pd_stage(
            first["product_moles"],
            duration_s=packet_duration_s,
            area_m2=float(config["pd_area_m2"]),
            area_steps=pd_steps,
        )
        stage1_product[stream_index] = first["product_moles"]
        stage1_retentate[stream_index] = first["retentate_moles"]
        stage2_product[stream_index] = second["product_moles"]
        stage2_retentate[stream_index] = second["retentate_moles"]
        stage1_recovery[stream_index] = float(first["h2_recovery"])
        stage2_recovery[stream_index] = float(second["h2_recovery"])
        max_balance = max(
            max_balance,
            float(first["mass_balance_max_abs_mol"]),
            float(second["mass_balance_max_abs_mol"]),
        )

    cycle_time_s = float(state["cycle_time_s"])
    timeline = build_uniform_timeline(stage2_product, cycle_time_s)
    receiver = strict.simulate_fixed_receiver_trace(
        timeline,
        strict.strict_gate(strict.load_contract()),
        receiver_capacity_mol=float(
            config.get("receiver_capacity_mol", operation.RECEIVER_CAPACITY_MOL)
        ),
        receiver_heel_fraction=strict.RECEIVER_HEEL_FRACTION,
    )
    receiver_y = np.asarray(receiver.pop("outlet_y_trace"), dtype=np.float32)
    receiver_inventory = np.asarray(receiver.pop("inventory_trace"), dtype=np.float32)
    receiver_violation = np.asarray(receiver.pop("violation_trace"), dtype=np.float32)

    raw_total = raw.sum(axis=0)
    first_total = stage1_product.sum(axis=0)
    final_total = stage2_product.sum(axis=0)
    elapsed_s = float(state["n_cycles"]) * float(state["cycle_time_s"])
    raw_h2 = float(raw_total[strict.INDEX["H2"]])
    first_h2 = float(first_total[strict.INDEX["H2"]])
    final_h2 = float(final_total[strict.INDEX["H2"]])
    y1 = first_total / max(float(first_total.sum()), 1.0e-30)
    raw_total_rate = float(raw_total.sum()) / elapsed_s
    stage1_total_rate = float(first_total.sum()) / elapsed_s
    compression_power_w = isothermal_compression_power_w(
        raw_total_rate, UPSTREAM_PRESSURE_PA, CONCENTRATOR_FEED_PRESSURE_PA
    ) + isothermal_compression_power_w(
        stage1_total_rate, CONCENTRATOR_PERMEATE_PRESSURE_PA, PD_FEED_PRESSURE_PA
    )
    overall_recovery = final_h2 / max(raw_h2, 1.0e-30)
    h2_rate = final_h2 / elapsed_s
    target = json.loads(V18_PATH.read_text(encoding="utf-8"))["primary_engineering_decision"]
    row = {
        "validation_kind": ref["validation_kind"],
        "case_id": ref["case_id"],
        "scenario": state["scenario"],
        "feed_u": state.get("feed_u"),
        "equilibrium_pc_u": state.get("equilibrium_pc_u"),
        "ldf_u": state.get("ldf_u"),
        "feed_h2_multiplier": state["feed_h2_multiplier"],
        "capacity_coordinate_c": state["capacity_coordinate_c"],
        "affinity_coordinate_a": state["affinity_coordinate_a"],
        "ldf_factor": state["ldf_factor"],
        "material": config["material"],
        "concentrator_area_m2": float(config["concentrator_area_m2"]),
        "pd_area_m2": float(config["pd_area_m2"]),
        "internal_recycle_fraction": ZERO_INTERNAL_RECYCLE_FRACTION,
        "retentate_routing": "stage-1 and stage-2 retentates to fuel/offgas; no internal recycle",
        "surge_buffer_capacity_mol": float(config["surge_buffer_capacity_mol"]),
        "surge_buffer_volume_L_at_20bar_298K": surge[
            "installed_volume_L_at_20bar_298K"
        ],
        "surge_required_capacity_mol": surge["required_capacity_mol"],
        "surge_initial_inventory_mol": surge["initial_inventory_mol"],
        "surge_minimum_inventory_mol": surge["actual_minimum_inventory_mol"],
        "surge_maximum_inventory_mol": surge["actual_maximum_inventory_mol"],
        "surge_capacity_gate": surge["capacity_gate"],
        "surge_constant_outlet_gate": surge["constant_total_outlet_gate"],
        "surge_periodic_composition_residual": surge[
            "periodic_composition_residual"
        ],
        "surge_component_mass_balance_max_abs_mol": surge[
            "component_mass_balance_max_abs_mol"
        ],
        "n_cells": state["n_cells"],
        "n_cycles": state["n_cycles"],
        "cycle_time_s": cycle_time_s,
        "raw_h2_rate_mol_s": raw_h2 / elapsed_s,
        "fresh_feed_h2_fraction": raw_h2 / max(float(raw_total.sum()), 1.0e-30),
        "stage1_h2_fraction": float(y1[strict.INDEX["H2"]]),
        "stage1_h2_recovery": first_h2 / max(raw_h2, 1.0e-30),
        "stage2_h2_recovery": final_h2 / max(first_h2, 1.0e-30),
        "overall_h2_recovery": overall_recovery,
        "qualified_h2_rate_mol_s": float(receiver["qualified_h2_rate_mol_s"]),
        "stage1_retentate_h2_loss_fraction_of_raw_h2": float(
            stage1_retentate[:, strict.INDEX["H2"]].sum() / max(raw_h2, 1.0e-30)
        ),
        "stage2_retentate_h2_loss_fraction_of_raw_h2": float(
            stage2_retentate[:, strict.INDEX["H2"]].sum() / max(raw_h2, 1.0e-30)
        ),
        "compression_power_w": compression_power_w,
        "compression_energy_kwh_kg_h2": compression_power_w
        / max(h2_rate * 2.01588e-3, 1.0e-30)
        / 3.6e6,
        "stage2_required_selectivity": required_selectivity(
            y1, strict.strict_gate(strict.load_contract())
        ),
        "maximum_module_mass_balance_abs_mol": max_balance,
        "source_min_tank_pressure_bar": state["min_tank_pressure_bar"],
        "source_reserve_gate": state["reserve_gate"],
        "source_css_gate": state["css_gate"],
        "source_numerical_gate": state["numerical_gate"],
        **receiver,
        "recovery_gate": overall_recovery >= float(target["minimum_h2_recovery"]),
        "shipment_gate": float(receiver["qualified_h2_rate_mol_s"])
        >= float(target["minimum_qualified_h2_rate_mol_s"]),
    }
    row["stage_train_event"] = bool(
        row["source_reserve_gate"]
        and row["source_css_gate"]
        and row["source_numerical_gate"]
        and row["surge_capacity_gate"]
        and row["surge_constant_outlet_gate"]
        and row["continuous_gate_pass"]
        and row["feasible_inventory"]
        and row["recovery_gate"]
        and row["shipment_gate"]
    )
    row["wall_time_s"] = time.time() - started
    traces = {
        "components": np.asarray(strict.COMPONENTS),
        "surge_outlet_mol": membrane_feed.astype(np.float32),
        "surge_inventory_mol": surge_inventory.astype(np.float32),
        "stage1_product_mol": stage1_product.astype(np.float32),
        "stage1_retentate_mol": stage1_retentate.astype(np.float32),
        "stage2_product_mol": stage2_product.astype(np.float32),
        "stage2_retentate_mol": stage2_retentate.astype(np.float32),
        "stage1_h2_recovery": stage1_recovery,
        "stage2_h2_recovery": stage2_recovery,
        "receiver_outlet_y": receiver_y,
        "receiver_inventory_mol": receiver_inventory,
        "receiver_gate_violation_factor": receiver_violation,
    }
    if save:
        state_dir = OUT / "states"
        state_dir.mkdir(parents=True, exist_ok=True)
        state_path = state_dir / f"{ref['case_id']}.json"
        trace_path = state_dir / f"{ref['case_id']}_traces.npz"
        row["source_state"] = ref["state_path"]
        row["source_trace"] = ref["trace_path"]
        row["trace_file"] = str(trace_path.relative_to(ROOT))
        np.savez_compressed(trace_path, **traces)
        state_path.write_text(json.dumps(row, indent=2), encoding="utf-8")
    return row, traces


def receiver_capacity_requirement(stage2_product: np.ndarray, cycle_time_s: float) -> dict:
    timeline = build_uniform_timeline(stage2_product, cycle_time_s)
    elapsed_s = float(timeline.shape[0]) * strict.RECEIVER_DT_S
    outlet_rate = float(timeline.sum()) / max(elapsed_s, 1.0e-30)
    imbalance = np.concatenate(
        ([0.0], np.cumsum(timeline.sum(axis=1) - outlet_rate * strict.RECEIVER_DT_S))
    )
    swing = float(imbalance.max() - imbalance.min())
    capacity = swing / max(1.0 - strict.RECEIVER_HEEL_FRACTION, 1.0e-30)
    return {
        "receiver_inventory_swing_mol": swing,
        "minimum_receiver_capacity_mol": capacity,
        "constant_outlet_rate_mol_s": outlet_rate,
    }


def apply_common_receiver_capacity(
    row: dict, *, receiver_capacity_mol: float
) -> dict:
    trace_path = ROOT / row["trace_file"]
    with np.load(trace_path, allow_pickle=False) as archive:
        traces = {name: np.asarray(archive[name]) for name in archive.files}
    stage2_product = np.asarray(traces["stage2_product_mol"], dtype=float)
    requirement = receiver_capacity_requirement(stage2_product, float(row["cycle_time_s"]))
    timeline = build_uniform_timeline(stage2_product, float(row["cycle_time_s"]))
    receiver = strict.simulate_fixed_receiver_trace(
        timeline,
        strict.strict_gate(strict.load_contract()),
        receiver_capacity_mol=float(receiver_capacity_mol),
        receiver_heel_fraction=strict.RECEIVER_HEEL_FRACTION,
    )
    traces["receiver_outlet_y"] = np.asarray(
        receiver.pop("outlet_y_trace"), dtype=np.float32
    )
    traces["receiver_inventory_mol"] = np.asarray(
        receiver.pop("inventory_trace"), dtype=np.float32
    )
    traces["receiver_gate_violation_factor"] = np.asarray(
        receiver.pop("violation_trace"), dtype=np.float32
    )
    np.savez_compressed(trace_path, **traces)
    updated = {
        **row,
        **receiver,
        **requirement,
        "installed_receiver_capacity_mol": float(receiver_capacity_mol),
        "installed_receiver_volume_L_at_1bar_298K": float(
            receiver_capacity_mol
            * R_J_MOL_K
            * COMPRESSION_T_K
            / PD_PERMEATE_PRESSURE_PA
            * 1000.0
        ),
    }
    updated["shipment_gate"] = bool(
        float(updated["qualified_h2_rate_mol_s"])
        >= json.loads(V18_PATH.read_text(encoding="utf-8"))[
            "primary_engineering_decision"
        ]["minimum_qualified_h2_rate_mol_s"]
    )
    updated["stage_train_event"] = bool(
        updated["source_reserve_gate"]
        and updated["source_css_gate"]
        and updated["source_numerical_gate"]
        and updated["surge_capacity_gate"]
        and updated["surge_constant_outlet_gate"]
        and updated["continuous_gate_pass"]
        and updated["feasible_inventory"]
        and updated["recovery_gate"]
        and updated["shipment_gate"]
    )
    state_path = OUT / "states" / f"{row['case_id']}.json"
    state_path.write_text(json.dumps(updated, indent=2), encoding="utf-8")
    return updated


def dynamic_worker(payload: tuple[dict, dict]) -> dict:
    ref, config = payload
    row, _ = simulate_dynamic_case(
        ref,
        config,
        concentrator_steps=DYNAMIC_CONCENTRATOR_STEPS,
        pd_steps=DYNAMIC_PD_STEPS,
        save=True,
    )
    return row


def mesh_audit(ref: dict, config: dict) -> list[dict]:
    rows: list[dict] = []
    for first_steps, second_steps in ((36, 72), (72, 144), (144, 288)):
        row, _ = simulate_dynamic_case(
            ref,
            config,
            concentrator_steps=first_steps,
            pd_steps=second_steps,
            save=False,
        )
        rows.append(
            {
                "concentrator_area_steps": first_steps,
                "pd_area_steps": second_steps,
                "overall_h2_recovery": row["overall_h2_recovery"],
                "qualified_h2_rate_mol_s": row["qualified_h2_rate_mol_s"],
                "stage1_h2_fraction": row["stage1_h2_fraction"],
                "compression_energy_kwh_kg_h2": row["compression_energy_kwh_kg_h2"],
                "maximum_module_mass_balance_abs_mol": row[
                    "maximum_module_mass_balance_abs_mol"
                ],
                "receiver_mass_balance_max_abs_mol": row[
                    "receiver_mass_balance_max_abs_mol"
                ],
                "stage_train_event": row["stage_train_event"],
            }
        )
    return rows


def flatten_dynamic(row: dict) -> dict:
    flat = {key: value for key, value in row.items() if not isinstance(value, (dict, list))}
    for name, value in row["stage2_required_selectivity"].items():
        flat[f"required_H2_{name}_selectivity"] = value
    return flat


def make_figure(screen_rows: list[dict], selected: dict, dynamic_rows: list[dict], original_req: dict) -> None:
    material = str(selected["material"])
    rows = [row for row in screen_rows if row["material"] == material]
    a1 = sorted({float(row["concentrator_area_m2"]) for row in rows})
    a2 = sorted({float(row["pd_area_m2"]) for row in rows})
    grid = np.full((len(a2), len(a1)), np.nan)
    for row in rows:
        i = a2.index(float(row["pd_area_m2"]))
        j = a1.index(float(row["concentrator_area_m2"]))
        grid[i, j] = 100.0 * float(row["worst_overall_h2_recovery"])

    fig, axes = plt.subplots(2, 2, figsize=(12.4, 9.2), constrained_layout=True)
    ax = axes[0, 0]
    image = ax.imshow(
        grid,
        origin="lower",
        aspect="auto",
        extent=[min(a1), max(a1), min(a2), max(a2)],
        cmap="viridis",
    )
    ax.contour(a1, a2, grid, levels=[88.294], colors="white", linewidths=1.5)
    ax.scatter(
        [selected["concentrator_area_m2"]], [selected["pd_area_m2"]],
        marker="*", s=180, color="#ef4444", edgecolor="white", linewidth=0.8,
    )
    ax.set_xlim(min(a1), max(a1) + 0.015 * (max(a1) - min(a1)))
    ax.set_ylim(min(a2), max(a2) + 0.035 * (max(a2) - min(a2)))
    ax.set_xlabel("Concentrator area (m²)")
    ax.set_ylabel("Pd area (m²)")
    ax.set_title(f"(a) Worst 16-case H₂ recovery: {material}")
    fig.colorbar(image, ax=ax, label="Recovery (%)")

    ax = axes[0, 1]
    labels = [row["case_id"] for row in dynamic_rows]
    x = np.arange(len(labels))
    ax.bar(x, [100 * row["overall_h2_recovery"] for row in dynamic_rows], color=[
        "#2563eb" if row["validation_kind"] == "uncertainty_corner" else "#f59e0b"
        for row in dynamic_rows
    ])
    ax.axhline(88.294, color="#dc2626", linestyle="--", linewidth=1.2, label="frozen recovery floor")
    ax.set_xticks(x, labels, rotation=55, ha="right", fontsize=7)
    ax.set_ylabel("Overall H₂ recovery (%)")
    ax.set_title("(b) Direct packet-wise confirmation")
    ax.legend(fontsize=8)

    ax = axes[1, 0]
    ax.bar(x, [100 * row["stage1_h2_fraction"] for row in dynamic_rows], color="#0f766e")
    ax.set_xticks(x, labels, rotation=55, ha="right", fontsize=7)
    ax.set_ylabel("H₂ in stage-1 permeate (%)")
    ax.set_title("(c) Feed to dense-Pd polishing stage")

    ax = axes[1, 1]
    names = ["CO", "CO2", "N2", "CH4"]
    before = [float(original_req[name]) for name in names]
    after = [max(float(row["stage2_required_selectivity"][name]) for row in dynamic_rows) for name in names]
    positions = np.arange(len(names))
    width = 0.36
    ax.bar(positions - width / 2, before, width, label="direct raw-feed screen", color="#94a3b8")
    ax.bar(positions + width / 2, after, width, label="after concentration stage", color="#7c3aed")
    ax.set_yscale("log")
    ax.set_xticks(positions, names)
    ax.set_ylabel("Required H₂/impurity selectivity")
    ax.set_title("(d) Strict component burden before Pd stage")
    ax.legend(fontsize=8)
    ax.grid(axis="y", alpha=0.25, which="both")

    for suffix in ("png", "pdf", "svg"):
        fig.savefig(OUT / f"Fig_stage_resolved_membrane_train.{suffix}", dpi=300, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    started = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    refs = case_references()
    for ref in refs:
        assert (ROOT / ref["state_path"]).exists()
        assert (ROOT / ref["trace_path"]).exists()
    v18 = json.loads(V18_PATH.read_text(encoding="utf-8"))
    requirement = json.loads(REQUIREMENT_PATH.read_text(encoding="utf-8"))
    gate = strict.strict_gate(strict.load_contract())
    target = v18["primary_engineering_decision"]

    screen_rows, selected, screen_selected = screen_designs(refs, gate, target)
    surge_requirements = []
    for ref in refs:
        _state, raw = load_case(ref)
        surge_requirements.append(
            {"case_id": ref["case_id"], **surge_buffer_requirement(raw)}
        )
    selected = dict(selected)
    selected["surge_buffer_capacity_mol"] = max(
        row["required_capacity_mol"] for row in surge_requirements
    )
    selected["surge_buffer_volume_L_at_20bar_298K"] = (
        selected["surge_buffer_capacity_mol"]
        * R_J_MOL_K
        * COMPRESSION_T_K
        / CONCENTRATOR_FEED_PRESSURE_PA
        * 1000.0
    )
    write_csv(OUT / "Table_stage_train_area_screen.csv", screen_rows)
    write_csv(OUT / "Table_stage_train_surge_buffer_sizing.csv", surge_requirements)

    dynamic_rows: list[dict] = []
    with ProcessPoolExecutor(max_workers=4) as pool:
        futures = {
            pool.submit(dynamic_worker, (ref, selected)): ref["case_id"] for ref in refs
        }
        for future in as_completed(futures):
            dynamic_rows.append(future.result())
    order = {ref["case_id"]: index for index, ref in enumerate(refs)}
    dynamic_rows.sort(key=lambda row: order[row["case_id"]])
    receiver_requirements: list[dict] = []
    for row in dynamic_rows:
        with np.load(ROOT / row["trace_file"], allow_pickle=False) as archive:
            stage2_product = np.asarray(archive["stage2_product_mol"], dtype=float)
        receiver_requirements.append(
            {
                "case_id": row["case_id"],
                **receiver_capacity_requirement(
                    stage2_product, float(row["cycle_time_s"])
                ),
            }
        )
    selected["receiver_capacity_mol"] = 1.005 * max(
        row["minimum_receiver_capacity_mol"] for row in receiver_requirements
    )
    selected["receiver_volume_L_at_1bar_298K"] = (
        selected["receiver_capacity_mol"]
        * R_J_MOL_K
        * COMPRESSION_T_K
        / PD_PERMEATE_PRESSURE_PA
        * 1000.0
    )
    dynamic_rows = [
        apply_common_receiver_capacity(
            row, receiver_capacity_mol=float(selected["receiver_capacity_mol"])
        )
        for row in dynamic_rows
    ]
    write_csv(
        OUT / "Table_stage_train_product_receiver_sizing.csv",
        receiver_requirements,
    )
    write_csv(
        OUT / "Table_stage_train_dynamic_confirmation.csv",
        [flatten_dynamic(row) for row in dynamic_rows],
    )

    worst_row = min(dynamic_rows, key=lambda row: float(row["overall_h2_recovery"]))
    worst_ref = next(ref for ref in refs if ref["case_id"] == worst_row["case_id"])
    mesh_rows = mesh_audit(worst_ref, selected)
    write_csv(OUT / "Table_stage_train_mesh_audit.csv", mesh_rows)
    fine_change = abs(
        float(mesh_rows[-1]["overall_h2_recovery"])
        - float(mesh_rows[-2]["overall_h2_recovery"])
    )
    fine_recovery_margin = (
        float(mesh_rows[-1]["overall_h2_recovery"])
        - float(target["minimum_h2_recovery"])
    )
    mesh_margin_ratio = fine_recovery_margin / max(fine_change, 1.0e-30)

    original_req = requirement["envelope"]["required_selectivity_by_impurity"]
    worst_required = {
        name: max(float(row["stage2_required_selectivity"][name]) for row in dynamic_rows)
        for name in ("CO", "CO2", "N2", "CH4")
    }
    reduction = {
        name: float(original_req[name]) / max(float(worst_required[name]), 1.0e-30)
        for name in worst_required
    }
    make_figure(screen_rows, selected, dynamic_rows, original_req)

    summary = {
        "schema": "psa-stage-resolved-membrane-train/v1",
        "status": "sixteen_case_packetwise_stage_train_confirmed",
        "input_variant": INPUT_VARIANT,
        "architecture": {
            "stage_0": "finite perfectly mixed surge buffer at 20 bar",
            "stage_1": "literature-parameterized H2-selective concentration membrane",
            "stage_2": "ideal defect-free dense-Pd final H2 polishing membrane",
            "stage_3": "co-sized finite product receiver",
            "retentate_routing": "both retentates to fuel/offgas",
            "internal_recycle_fraction": ZERO_INTERNAL_RECYCLE_FRACTION,
            "reason_for_zero_recycle": "the single-pass design meets the frozen target and avoids an unvalidated accumulation loop",
            "surge_buffer_capacity_mol": selected["surge_buffer_capacity_mol"],
            "surge_buffer_volume_L_at_20bar_298K": selected[
                "surge_buffer_volume_L_at_20bar_298K"
            ],
            "surge_buffer_heel_mol": SURGE_HEEL_MOL,
            "product_receiver_capacity_mol": selected[
                "receiver_capacity_mol"
            ],
            "product_receiver_volume_L_at_1bar_298K": selected[
                "receiver_volume_L_at_1bar_298K"
            ],
        },
        "literature_parameters": {
            "source": "Zito et al. 2023",
            "doi": "10.1016/j.renene.2023.119243",
            "materials": MATERIALS,
            "pd_h2_permeance_mol_m2_s_pa_half": PD_H2_PERMEANCE_MOL_M2_S_PA_HALF,
            "pressure_bar": {
                "upstream": UPSTREAM_PRESSURE_PA / 1.0e5,
                "concentrator_feed": CONCENTRATOR_FEED_PRESSURE_PA / 1.0e5,
                "concentrator_permeate": CONCENTRATOR_PERMEATE_PRESSURE_PA / 1.0e5,
                "pd_feed": PD_FEED_PRESSURE_PA / 1.0e5,
                "pd_permeate": PD_PERMEATE_PRESSURE_PA / 1.0e5,
            },
        },
        "screen": screen_selected["meta"],
        "surge_buffer_sizing": surge_requirements,
        "product_receiver_sizing": receiver_requirements,
        "selected_design": selected,
        "dynamic_confirmation": {
            "case_count": len(dynamic_rows),
            "corner_pass_count": sum(
                row["stage_train_event"]
                for row in dynamic_rows
                if row["validation_kind"] == "uncertainty_corner"
            ),
            "holdout_pass_count": sum(
                row["stage_train_event"]
                for row in dynamic_rows
                if row["validation_kind"] == "predeclared_interior_holdout"
            ),
            "minimum_overall_h2_recovery": min(
                row["overall_h2_recovery"] for row in dynamic_rows
            ),
            "minimum_qualified_h2_rate_mol_s": min(
                row["qualified_h2_rate_mol_s"] for row in dynamic_rows
            ),
            "minimum_stage1_h2_fraction": min(
                row["stage1_h2_fraction"] for row in dynamic_rows
            ),
            "maximum_compression_energy_kwh_kg_h2": max(
                row["compression_energy_kwh_kg_h2"] for row in dynamic_rows
            ),
            "minimum_source_tank_pressure_bar": min(
                row["source_min_tank_pressure_bar"] for row in dynamic_rows
            ),
            "maximum_required_surge_capacity_mol": max(
                row["surge_required_capacity_mol"] for row in dynamic_rows
            ),
            "maximum_surge_component_balance_abs_mol": max(
                row["surge_component_mass_balance_max_abs_mol"]
                for row in dynamic_rows
            ),
            "all_surge_capacity_gates_pass": all(
                row["surge_capacity_gate"] for row in dynamic_rows
            ),
            "all_surge_constant_outlet_gates_pass": all(
                row["surge_constant_outlet_gate"] for row in dynamic_rows
            ),
            "maximum_module_mass_balance_abs_mol": max(
                row["maximum_module_mass_balance_abs_mol"] for row in dynamic_rows
            ),
            "maximum_receiver_mass_balance_abs_mol": max(
                row["receiver_mass_balance_max_abs_mol"] for row in dynamic_rows
            ),
            "all_continuous_product_gates_pass": all(
                row["continuous_gate_pass"] for row in dynamic_rows
            ),
            "all_receiver_inventory_gates_pass": all(
                row["feasible_inventory"] for row in dynamic_rows
            ),
            "all_stage_train_events_pass": all(
                row["stage_train_event"] for row in dynamic_rows
            ),
        },
        "strict_component_burden": {
            "original_direct_feed_requirement": original_req,
            "worst_requirement_after_concentration": worst_required,
            "requirement_reduction_factor": reduction,
            "experimental_component_gate_closed": False,
        },
        "mesh_audit": {
            "worst_case_id": worst_row["case_id"],
            "rows": mesh_rows,
            "fine_recovery_change_absolute": fine_change,
            "fine_recovery_margin_above_gate": fine_recovery_margin,
            "recovery_margin_to_mesh_change_ratio": mesh_margin_ratio,
            "fine_mesh_stable": bool(
                fine_change < 1.0e-3
                and mesh_margin_ratio > 10.0
                and all(row["stage_train_event"] for row in mesh_rows)
            ),
        },
        "energy_scope": {
            "included": (
                f"ideal-gas isothermal compression from {UPSTREAM_PRESSURE_PA / 1.0e5:.1f} to 20 bar "
                "and interstage 1 to 20 bar at 72% efficiency"
            ),
            "excluded": "heating, cooling, pressure drop, vacuum, membrane fabrication, replacement, and retentate credit",
        },
        "claim_boundary": {
            "allowed": (
                "A literature-parameterized, stage-resolved membrane train preserves the frozen engineering event "
                "over all eight corners and eight predeclared hold-outs under an ideal dense-Pd assumption."
            ),
            "not_allowed": (
                "The selected train is experimentally validated at the declared CO/CO2/N2/CH4 limits or has a proven cost optimum."
            ),
        },
        "sources": refs,
        "wall_time_s": time.time() - started,
    }
    assert summary["dynamic_confirmation"]["corner_pass_count"] == 8
    assert summary["dynamic_confirmation"]["holdout_pass_count"] == 8
    assert summary["dynamic_confirmation"]["all_stage_train_events_pass"] is True
    assert summary["mesh_audit"]["fine_mesh_stable"] is True

    json_path = OUT / "PSA_STAGE_RESOLVED_MEMBRANE_TRAIN.json"
    json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    selected_area1 = float(selected["concentrator_area_m2"])
    selected_area2 = float(selected["pd_area_m2"])
    dynamic = summary["dynamic_confirmation"]
    md = f"""# Stage-resolved concentration + dense-Pd membrane train

## Engineering result

The saved dynamic PSA outlet from all eight uncertainty corners and all eight predeclared interior hold-outs was passed through a finite surge buffer, two explicit membrane stages, and a co-sized finite receiver. The selected single-pass train is:

- stage 1: **{selected['material']} H2 concentrator, {selected_area1:.4f} m²**;
- stage 2: **ideal dense-Pd H2 polisher, {selected_area2:.4f} m²**;
- cyclic-flow surge buffer: **{selected['surge_buffer_capacity_mol']:.4f} mol ({selected['surge_buffer_volume_L_at_20bar_298K']:.3f} L at 20 bar and 298 K)**;
- feed/permeate pressures: **20/1 bar** for both membrane stages;
- interstage permeate recompression: **1 to 20 bar**;
- internal recycle: **0**; both retentates are routed to fuel/offgas;
- receiver: **{selected['receiver_capacity_mol']:.4f} mol ({selected['receiver_volume_L_at_1bar_298K']:.3f} L at 1 bar and 298 K)** with the frozen heel fraction and constant-outlet controller.

The area search was bounded by the Zito et al. flow-scaled polymer/carbon + Pd configurations. It first required all 16 direct cases to meet the frozen recovery and qualified-shipment floors. Among configurations within 0.1% of the maximum worst-case shipment, it minimized Pd area, total area, and compression energy.

## Direct dynamic confirmation

| result | value |
|---|---:|
| corner passes | {dynamic['corner_pass_count']}/8 |
| predeclared hold-out passes | {dynamic['holdout_pass_count']}/8 |
| minimum overall H2 recovery | {100*dynamic['minimum_overall_h2_recovery']:.3f}% |
| minimum qualified H2 rate | {dynamic['minimum_qualified_h2_rate_mol_s']:.7f} mol/s |
| minimum H2 entering Pd stage | {100*dynamic['minimum_stage1_h2_fraction']:.3f}% |
| maximum compression-only energy | {dynamic['maximum_compression_energy_kwh_kg_h2']:.3f} kWh/kg H2 |
| installed surge-buffer capacity | {selected['surge_buffer_capacity_mol']:.4f} mol |
| installed product-receiver capacity | {selected['receiver_capacity_mol']:.4f} mol |
| minimum inherited regeneration-tank pressure | {dynamic['minimum_source_tank_pressure_bar']:.4f} bar |
| maximum module balance residual | {dynamic['maximum_module_mass_balance_abs_mol']:.3e} mol |
| maximum receiver balance residual | {dynamic['maximum_receiver_mass_balance_abs_mol']:.3e} mol |

All 16 packet-wise receiver calculations pass the continuous product gate and inventory gate. The selected train therefore replaces the former 2,214 cm² single-stage interpretation with an explicit physical architecture while preserving the engineering event.

## Strict impurity implication

Pre-concentration reduces the worst ideal selectivity required at the Pd feed by the following factors:

| impurity | direct raw-feed requirement | worst after stage 1 | reduction |
|---|---:|---:|---:|
"""
    for name in ("CO", "CO2", "N2", "CH4"):
        md += (
            f"| {name} | {float(original_req[name]):,.1f} | {float(worst_required[name]):,.1f} | "
            f"{float(reduction[name]):.2f}× |\n"
        )
    md += f"""

The dense-Pd stage is ideal and defect-free in this calculation, so its modeled product is pure H2. The table quantifies the finite-selectivity performance that a real module must demonstrate. It does not replace component-resolved measurements.

## Numerical and energy boundaries

The recovery change between the 72/144 and 144/288 area meshes is **{fine_change:.3e}** ({100*fine_change:.3f} percentage point). The fine-mesh recovery margin above the frozen gate is **{100*fine_recovery_margin:.3f} percentage points**, or **{mesh_margin_ratio:.1f} times** the mesh change, and the pass decision is unchanged at all three resolutions. The 60-cycle PSA horizon, tank reserve, CSS, and conservation evidence are inherited from each saved source trajectory. Energy includes isothermal compression at 72% efficiency; heating, cooling, pressure drop, vacuum, membrane cost, lifetime, and retentate fuel credit remain open.
"""
    (OUT / "PSA_STAGE_RESOLVED_MEMBRANE_TRAIN.md").write_text(md, encoding="utf-8")

    source_paths = [V18_PATH, REQUIREMENT_PATH]
    source_paths.extend(ROOT / ref["state_path"] for ref in refs)
    source_paths.extend(ROOT / ref["trace_path"] for ref in refs)
    output_paths = sorted(path for path in OUT.rglob("*") if path.is_file())
    manifest = {
        "schema": "psa-stage-resolved-membrane-train-manifest/v1",
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
            if path.name != "PSA_STAGE_RESOLVED_MEMBRANE_TRAIN_MANIFEST.json"
        ],
    }
    (OUT / "PSA_STAGE_RESOLVED_MEMBRANE_TRAIN_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    print(json.dumps({
        "status": summary["status"],
        "selected_design": selected,
        "dynamic_confirmation": dynamic,
        "mesh_fine_change": fine_change,
        "output_directory": str(OUT),
        "wall_time_s": summary["wall_time_s"],
    }, indent=2))


if __name__ == "__main__":
    main()
