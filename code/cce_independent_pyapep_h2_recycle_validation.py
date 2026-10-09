"""Independent pyAPEP code-path check for the frozen H2 recycle policies.

This script deliberately does not import the project's finite-volume PSA
solver.  It uses the public pyAPEP column solver and only reproduces the
declared external policy semantics:

* adsorption product is split into external product and a recycle fraction;
* recycled product enters a finite product-gas tank;
* the tank supplies purge and pressurisation, with explicit source-gas makeup;
* the frozen event is H2 purity >= 0.9998 and external H2 recovery >= 0.789.

pyAPEP 0.1.8 represents one uniform adsorbent per column.  AC-only and 5A-only
columns are therefore treated as model-form brackets, not as a reproduction of
the project's layered bed.  Pressure equalisation is omitted because the
public routine is energy-balance-specific and does not share the isothermal
state interface used here.  These limits are written into every output.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from dataclasses import dataclass
from importlib.metadata import version as package_version
from pathlib import Path
from typing import Iterable

import matplotlib.pyplot as plt
import numpy as np
import scipy  # load the active environment before making pyAPEP importable


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
VENDOR = ROOT / "external" / "pyapep_vendor"
if str(VENDOR) not in sys.path:
    # Appending is intentional.  Prepending would shadow the active NumPy and
    # SciPy with vendored cp312 wheels on the project's cp311 environment.
    sys.path.append(str(VENDOR))
from pyapep import simsep  # noqa: E402


R_GAS = 8.3145
T_REF_K = 311.157539
COMPONENTS = ("H2", "CO2", "CH4", "CO", "N2")
MOLAR_MASS = np.array([0.002016, 0.04401, 0.01604, 0.02801, 0.028014])
VISCOSITY = np.array([8.9e-6, 1.5e-5, 1.1e-5, 1.8e-5, 1.76e-5])

# Corrected Ahn et al. parameter tables, ordered H2/CO2/CH4/CO/N2.
AC_A1 = np.array([16.943, 28.7973, 23.8600, 33.8500, 1.6441])
AC_A2 = np.array([0.02100, 0.07000, 0.05621, 0.09072, 0.00073])
AC_B1 = np.array([6.166e-5, 9.900e-3, 3.432e-3, 2.281e-4, 5.380e-2])
AC_B2 = np.array([1229.0, 1030.0, 1159.0, 1751.0, 326.0])
AC_LDF = np.array([0.700, 0.0355, 0.195, 0.150, 0.261])

Z5A_A1 = np.array([4.314, 10.0300, 5.8330, 11.8454, 4.8133])
Z5A_A2 = np.array([0.01060, 0.01858, 0.01192, 0.03130, 0.00668])
Z5A_B1 = np.array([2.482e-3, 1.5575, 5.9716e-4, 1.990e-2, 5.620e-4])
Z5A_B2 = np.array([458.0, 207.0, 1731.0, 763.0, 1531.0])
Z5A_LDF = np.array([0.700, 0.0135, 0.147, 0.063, 0.099])

FEED_Y = np.array([0.655, 0.283, 0.041, 0.006, 0.014], dtype=float)
POLICIES = (0.420, 0.427, 0.430)
PURITY_THRESHOLD = 0.9998
RECOVERY_THRESHOLD = 0.789


@dataclass(frozen=True)
class Draw:
    draw_index: int
    source_y: tuple[float, ...]
    capacity_factor: float
    affinity_factor: float
    ldf_factor: float
    p_low_bar: float


@dataclass(frozen=True)
class SolverConfig:
    n_nodes: int = 5
    max_cycles: int = 30
    min_cycles: int = 12
    css_tol: float = 1.0e-3
    n_sec: int = 1
    adsorption_duration_s: float = 10.0
    blowdown_duration_s: float = 5.0
    purge_duration_s: float = 5.0
    pressurisation_duration_s: float = 100.0
    p_high_bar: float = 15.65
    product_drop_bar: float = 0.80
    tank_capacity_mol: float = 100.0
    cv_m3_s_bar: float = 5.0e-3


def normalise(values: Iterable[float]) -> np.ndarray:
    y = np.maximum(np.asarray(tuple(values), dtype=float), 0.0)
    total = float(y.sum())
    if total <= 0.0:
        raise ValueError("composition must have positive total")
    return y / total


def parameter_set(adsorbent: str) -> tuple[np.ndarray, ...]:
    name = adsorbent.upper()
    if name == "AC":
        return AC_A1, AC_A2, AC_B1, AC_B2, AC_LDF
    if name in {"5A", "Z5A"}:
        return Z5A_A1, Z5A_A2, Z5A_B1, Z5A_B2, Z5A_LDF
    raise ValueError(f"unknown adsorbent {adsorbent!r}")


def make_isotherm(adsorbent: str, draw: Draw):
    a1, a2, b1, b2, _ = parameter_set(adsorbent)

    def isotherm(partial_pressure_bar, temperature_k):
        pp = np.asarray(partial_pressure_bar, dtype=float)
        temperature = np.asarray(temperature_k, dtype=float).reshape(1, -1)
        qcap = draw.capacity_factor * (a1[:, None] - a2[:, None] * temperature)
        affinity = draw.affinity_factor * b1[:, None] * np.exp(b2[:, None] / temperature)
        denominator = 1.0 + np.sum(affinity * pp, axis=0)
        return [qcap[i] * affinity[i] * pp[i] / denominator for i in range(len(COMPONENTS))]

    return isotherm


def make_column(adsorbent: str, draw: Draw, config: SolverConfig):
    length_m = 0.5
    area_m2 = float(np.pi * 0.1**2)
    column = simsep.column(length_m, area_m2, n_component=len(COMPONENTS), N_node=config.n_nodes, E_balance=False)
    isotherm = make_isotherm(adsorbent, draw)
    if adsorbent.upper() == "AC":
        void_fraction, particle_diameter_m, density_kg_m3 = 0.433, 0.0023, 522.0
    else:
        void_fraction, particle_diameter_m, density_kg_m3 = 0.357, 0.0023, 698.0
    column.adsorbent_info(
        isotherm,
        epsi=void_fraction,
        D_particle=particle_diameter_m,
        rho_s=density_kg_m3,
        P_test_range=[0.0, 17.0],
        T_test_range=[T_REF_K, T_REF_K],
    )
    column.gas_prop_info(MOLAR_MASS.tolist(), VISCOSITY.tolist())
    ldf = parameter_set(adsorbent)[4] * draw.ldf_factor
    surface = 200.0
    column.mass_trans_info(
        k_mass_transfer=(ldf / surface).tolist(),
        a_specific_surf=surface,
        D_dispersion=[1.0e-6] * len(COMPONENTS),
    )
    return column, isotherm


def initial_state(column, isotherm, pressure_bar: float, composition: Iterable[float]):
    y = normalise(composition)
    n = column._N
    pressure = np.full(n, float(pressure_bar))
    y_state = [np.full(n, float(value)) for value in y]
    q_state = isotherm([pressure * value for value in y], np.full(n, T_REF_K))
    temperature = np.full(n, T_REF_K)
    return pressure, temperature, temperature.copy(), y_state, q_state


def extract_state(column, result):
    n = column._N
    nc = len(COMPONENTS)
    concentration = [result[-1, i * n : (i + 1) * n].copy() for i in range(nc)]
    loading = [result[-1, (nc + i) * n : (nc + i + 1) * n].copy() for i in range(nc)]
    c_total = np.maximum(np.sum(concentration, axis=0), 1.0e-12)
    y = [values / c_total for values in concentration]
    pressure = c_total * R_GAS * T_REF_K / 1.0e5
    temperature = np.full(n, T_REF_K)
    return pressure, temperature, temperature.copy(), y, loading


def stored_moles(column, state) -> np.ndarray:
    pressure, _, _, y, q = state
    gas = []
    adsorbed = []
    for i in range(len(COMPONENTS)):
        concentration = np.asarray(y[i]) * pressure * 1.0e5 / (R_GAS * T_REF_K)
        gas.append(float(np.trapezoid(column._epsi * concentration, column._z) * column._A))
        adsorbed.append(
            float(
                np.trapezoid((1.0 - column._epsi) * column._rho_s * np.asarray(q[i]), column._z)
                * column._A
            )
        )
    return np.asarray(gas) + np.asarray(adsorbed)


def state_distance(old_state, new_state) -> float:
    p0, _, _, y0, q0 = old_state
    p1, _, _, y1, q1 = new_state
    pressure = float(np.max(np.abs(p1 - p0)) / max(float(np.max(np.abs(p0))), 1.0))
    composition = max(float(np.max(np.abs(y1[i] - y0[i]))) for i in range(len(COMPONENTS)))
    loading = max(
        float(np.max(np.abs(q1[i] - q0[i])) / max(float(np.max(np.abs(q0[i]))), 1.0))
        for i in range(len(COMPONENTS))
    )
    return max(pressure, composition, loading)


def run_step(
    column,
    state,
    *,
    p_out_bar: float,
    p_in_bar: float,
    y_in: Iterable[float],
    duration_s: float,
    forward: bool,
    cv_in: float,
    cv_out: float,
    n_sec: int,
):
    p0, tg0, ts0, y0, q0 = state
    inlet_y = normalise(y_in)
    column.boundaryC_info(
        P_outlet=float(p_out_bar),
        P_inlet=float(p_in_bar),
        T_inlet=T_REF_K,
        y_inlet=inlet_y,
        Cv_in=float(cv_in),
        Cv_out=float(cv_out),
        Q_inlet=None,
        assigned_v_option=False,
        foward_flow_direction=bool(forward),
    )
    column.initialC_info(p0, tg0, ts0, y0, q0)
    result, _, time_s = column.run_mamo(float(duration_s), n_sec=int(n_sec))
    next_state = extract_state(column, result)

    n = column._N
    nc = len(COMPONENTS)
    concentration = result[:, : nc * n].reshape(result.shape[0], nc, n)
    c_total = np.maximum(np.sum(concentration, axis=1), 1.0e-12)
    inlet_index = 0 if forward else n - 1
    outlet_index = n - 1 if forward else 0
    inlet_state_pressure = c_total[:, inlet_index] * R_GAS * T_REF_K / 1.0e5
    outlet_state_pressure = c_total[:, outlet_index] * R_GAS * T_REF_K / 1.0e5
    inlet_velocity = np.maximum(float(cv_in) * (float(p_in_bar) - inlet_state_pressure), 0.0)
    outlet_velocity = np.maximum(float(cv_out) * (outlet_state_pressure - float(p_out_bar)), 0.0)
    inlet_concentration = float(p_in_bar) * 1.0e5 / (R_GAS * T_REF_K)
    inlet_flow = inlet_velocity * column._epsi * column._A * inlet_concentration
    outlet_flow = outlet_velocity * column._epsi * column._A * c_total[:, outlet_index]
    outlet_y = concentration[:, :, outlet_index] / c_total[:, outlet_index, None]
    in_mol = np.trapezoid(inlet_flow, time_s) * inlet_y
    out_mol = np.asarray(
        [np.trapezoid(outlet_flow * outlet_y[:, i], time_s) for i in range(len(COMPONENTS))]
    )
    return next_state, {
        "in_mol": in_mol,
        "out_mol": out_mol,
        "outlet_y": outlet_y,
        "time_s": np.asarray(time_s),
    }


def tank_source_step(column, state, tank, makeup_y, *, config: SolverConfig, mode: str):
    tank = np.maximum(np.asarray(tank, dtype=float), 0.0)
    source_y = normalise(tank if float(tank.sum()) > 1.0e-14 else makeup_y)
    if mode == "purge":
        next_state, stream = run_step(
            column,
            state,
            p_out_bar=1.0,
            p_in_bar=max(1.10, 1.0),
            y_in=source_y,
            duration_s=config.purge_duration_s,
            forward=False,
            cv_in=config.cv_m3_s_bar,
            cv_out=config.cv_m3_s_bar,
            n_sec=config.n_sec,
        )
    elif mode == "pressurisation":
        next_state, stream = run_step(
            column,
            state,
            p_out_bar=1.0,
            p_in_bar=config.p_high_bar,
            y_in=source_y,
            duration_s=config.pressurisation_duration_s,
            # Product-gas pressurisation enters at the light-product end,
            # matching the counter-current purge connection.  Using the feed
            # end here drives previously desorbed heavy gas toward the product
            # outlet and is not the declared product-tank topology.
            forward=False,
            cv_in=config.cv_m3_s_bar,
            cv_out=0.0,
            n_sec=config.n_sec,
        )
    else:
        raise ValueError(mode)

    demand = np.maximum(np.asarray(stream["in_mol"]), 0.0)
    demand_total = float(demand.sum())
    tank_take_total = min(float(tank.sum()), demand_total)
    from_tank = tank_take_total * source_y
    makeup = np.maximum(demand - from_tank, 0.0)
    next_tank = np.maximum(tank - from_tank, 0.0)
    stream["source_y"] = source_y
    stream["tank_withdrawal_mol"] = from_tank
    stream["makeup_mol"] = makeup
    return next_state, stream, next_tank, makeup


def add_recycle(tank, product, recycle_fraction: float, capacity_mol: float):
    recycle = float(recycle_fraction) * np.maximum(np.asarray(product), 0.0)
    candidate = np.maximum(np.asarray(tank), 0.0) + recycle
    if float(candidate.sum()) <= capacity_mol:
        return candidate, recycle, np.zeros_like(candidate)
    retained = candidate * capacity_mol / float(candidate.sum())
    return retained, recycle, candidate - retained


def run_case(draw: Draw, policy: float, adsorbent: str, config: SolverConfig) -> dict[str, object]:
    column, isotherm = make_column(adsorbent, draw, config)
    state = initial_state(column, isotherm, config.p_high_bar, FEED_Y)
    tank = np.zeros(len(COMPONENTS))
    initial_inventory = stored_moles(column, state) + tank
    cumulative_feed = np.zeros(len(COMPONENTS))
    cumulative_product = np.zeros(len(COMPONENTS))
    cumulative_external_in = np.zeros(len(COMPONENTS))
    cumulative_external_out = np.zeros(len(COMPONENTS))
    history: list[dict[str, float]] = []
    stable_count = 0
    last: dict[str, object] = {}

    for cycle in range(1, config.max_cycles + 1):
        start_state = state
        start_tank = tank.copy()
        start_inventory = stored_moles(column, state) + tank
        feed = np.zeros(len(COMPONENTS))
        product_external = np.zeros(len(COMPONENTS))
        external_in = np.zeros(len(COMPONENTS))
        external_out = np.zeros(len(COMPONENTS))
        makeup_total = np.zeros(len(COMPONENTS))
        tank_withdrawal_total = np.zeros(len(COMPONENTS))
        overflow_total = np.zeros(len(COMPONENTS))

        state, adsorption = run_step(
            column,
            state,
            p_out_bar=config.p_high_bar - config.product_drop_bar,
            p_in_bar=config.p_high_bar,
            y_in=FEED_Y,
            duration_s=config.adsorption_duration_s,
            forward=True,
            cv_in=config.cv_m3_s_bar,
            cv_out=config.cv_m3_s_bar,
            n_sec=config.n_sec,
        )
        feed += adsorption["in_mol"]
        external_in += adsorption["in_mol"]
        tank, recycle, overflow = add_recycle(
            tank, adsorption["out_mol"], policy, config.tank_capacity_mol
        )
        product_external += adsorption["out_mol"] - recycle
        external_out += product_external + overflow
        overflow_total += overflow

        state, blowdown = run_step(
            column,
            state,
            p_out_bar=1.0,
            p_in_bar=draw.p_low_bar,
            y_in=FEED_Y,
            duration_s=config.blowdown_duration_s,
            forward=False,
            cv_in=0.0,
            cv_out=config.cv_m3_s_bar,
            n_sec=config.n_sec,
        )
        external_out += blowdown["out_mol"]

        state, purge, tank, makeup = tank_source_step(
            column, state, tank, draw.source_y, config=config, mode="purge"
        )
        external_in += makeup
        external_out += purge["out_mol"]
        makeup_total += makeup
        tank_withdrawal_total += purge["tank_withdrawal_mol"]

        state, pressurisation, tank, makeup = tank_source_step(
            column, state, tank, draw.source_y, config=config, mode="pressurisation"
        )
        external_in += makeup
        external_out += pressurisation["out_mol"]
        makeup_total += makeup
        tank_withdrawal_total += pressurisation["tank_withdrawal_mol"]

        end_inventory = stored_moles(column, state) + tank
        residual = external_in - external_out - (end_inventory - start_inventory)
        balance_denominator = max(float(external_in.sum() + external_out.sum()), 1.0e-12)
        balance_relative = float(np.max(np.abs(residual)) / balance_denominator)
        tank_distance = float(
            np.sum(np.abs(tank - start_tank))
            / max(float(np.sum(np.abs(start_tank))), float(np.sum(np.abs(start_inventory))), 1.0e-12)
        )
        css = max(state_distance(start_state, state), tank_distance)
        history.append({"cycle": float(cycle), "css_residual": css, "balance_relative": balance_relative})
        stable_count = stable_count + 1 if cycle >= config.min_cycles and css < config.css_tol else 0
        cumulative_feed += feed
        cumulative_product += product_external
        cumulative_external_in += external_in
        cumulative_external_out += external_out
        last = {
            "feed": feed,
            "product": product_external,
            "makeup": makeup_total,
            "tank_withdrawal": tank_withdrawal_total,
            "overflow": overflow_total,
            "external_in": external_in,
            "external_out": external_out,
            "residual": residual,
            "balance_relative": balance_relative,
        }
        if stable_count >= 2:
            break

    product = np.asarray(last["product"])
    feed = np.asarray(last["feed"])
    purity = float(product[0] / max(float(product.sum()), 1.0e-12))
    recovery_adsorption_feed_proxy = float(product[0] / max(float(feed[0]), 1.0e-12))
    recovery_external_boundary = float(
        product[0] / max(float(np.asarray(last["external_in"])[0]), 1.0e-12)
    )
    tank_withdrawal = np.asarray(last["tank_withdrawal"])
    makeup = np.asarray(last["makeup"])
    source_demand = tank_withdrawal + makeup
    tank_supply_fraction = float(tank_withdrawal.sum() / max(float(source_demand.sum()), 1.0e-12))
    product_tank_self_sufficient = bool(float(makeup.sum()) <= 1.0e-10)
    cumulative_residual = cumulative_external_in - cumulative_external_out - (
        stored_moles(column, state) + tank - initial_inventory
    )
    cumulative_denominator = max(
        float(cumulative_external_in.sum() + cumulative_external_out.sum()), 1.0e-12
    )
    return {
        "draw_index": draw.draw_index,
        "policy_recycle_fraction": float(policy),
        "adsorbent": adsorbent.upper(),
        "n_nodes": config.n_nodes,
        "cycles_completed": len(history),
        "css_residual_final": history[-1]["css_residual"],
        "css_gate": bool(history[-1]["css_residual"] < config.css_tol),
        "h2_product": purity,
        "h2_recovery_adsorption_feed_proxy": recovery_adsorption_feed_proxy,
        "h2_recovery_external_boundary": recovery_external_boundary,
        "joint_event": bool(
            purity >= PURITY_THRESHOLD and recovery_external_boundary >= RECOVERY_THRESHOLD
        ),
        "strict_same_policy_event_gate": bool(
            purity >= PURITY_THRESHOLD
            and recovery_external_boundary >= RECOVERY_THRESHOLD
            and product_tank_self_sufficient
        ),
        "purity_threshold_margin": purity - PURITY_THRESHOLD,
        "recovery_threshold_margin": recovery_external_boundary - RECOVERY_THRESHOLD,
        "cycle_mass_balance_relative": float(last["balance_relative"]),
        "cumulative_mass_balance_relative": float(
            np.max(np.abs(cumulative_residual)) / cumulative_denominator
        ),
        "source_h2": draw.source_y[0],
        "source_co2": draw.source_y[1],
        "source_ch4": draw.source_y[2],
        "source_co": draw.source_y[3],
        "source_n2": draw.source_y[4],
        "capacity_factor": draw.capacity_factor,
        "affinity_factor": draw.affinity_factor,
        "ldf_factor": draw.ldf_factor,
        "p_low_bar": draw.p_low_bar,
        "product_external_mol": product.tolist(),
        "feed_adsorption_in_mol": feed.tolist(),
        "makeup_mol": makeup.tolist(),
        "tank_withdrawal_mol": tank_withdrawal.tolist(),
        "tank_supply_fraction_total": tank_supply_fraction,
        "product_tank_self_sufficient": product_tank_self_sufficient,
        "tank_final_mol": tank.tolist(),
        "final_mean_pressure_bar": float(np.mean(state[0])),
        "css_history": history,
    }


def load_draws(indices: list[int]) -> list[Draw]:
    source_path = HERE / "psa_two_bed_spatial_tank_n2_independent_source_uncertainty_32.csv"
    rows = list(csv.DictReader(source_path.open(encoding="utf-8")))
    draws = []
    for index in indices:
        row = rows[index]
        source = normalise(float(row[f"source_{name}"]) for name in ("h2", "co2", "ch4", "co", "n2"))
        draws.append(
            Draw(
                draw_index=index,
                source_y=tuple(float(v) for v in source),
                capacity_factor=float(row["capacity_factor"]),
                affinity_factor=float(row["affinity_factor"]),
                ldf_factor=float(row["ldf_factor"]),
                p_low_bar=float(row["P_low_bar"]),
            )
        )
    return draws


def summarise(rows: list[dict[str, object]], config: SolverConfig) -> dict[str, object]:
    groups = []
    for adsorbent in sorted({str(row["adsorbent"]) for row in rows}):
        for n_nodes in sorted({int(row["n_nodes"]) for row in rows if row["adsorbent"] == adsorbent}):
            for policy in POLICIES:
                subset = [
                    row
                    for row in rows
                    if row["adsorbent"] == adsorbent
                    and int(row["n_nodes"]) == n_nodes
                    and math.isclose(float(row["policy_recycle_fraction"]), policy)
                ]
                if not subset:
                    continue
                groups.append(
                    {
                        "adsorbent": adsorbent,
                        "n_nodes": n_nodes,
                        "policy_recycle_fraction": policy,
                        "draw_count": len(subset),
                        "event_count": int(sum(bool(row["joint_event"]) for row in subset)),
                        "event_probability": float(np.mean([bool(row["joint_event"]) for row in subset])),
                        "mean_h2_product": float(np.mean([float(row["h2_product"]) for row in subset])),
                        "mean_h2_recovery": float(
                            np.mean([float(row["h2_recovery_external_boundary"]) for row in subset])
                        ),
                        "mean_h2_recovery_adsorption_feed_proxy": float(
                            np.mean([float(row["h2_recovery_adsorption_feed_proxy"]) for row in subset])
                        ),
                        "mean_h2_recovery_external_boundary": float(
                            np.mean([float(row["h2_recovery_external_boundary"]) for row in subset])
                        ),
                        "css_pass_count": int(sum(bool(row["css_gate"]) for row in subset)),
                        "strict_same_policy_event_pass_count": int(
                            sum(bool(row["strict_same_policy_event_gate"]) for row in subset)
                        ),
                        "product_tank_self_sufficient_count": int(
                            sum(bool(row["product_tank_self_sufficient"]) for row in subset)
                        ),
                        "mean_tank_supply_fraction_total": float(
                            np.mean([float(row["tank_supply_fraction_total"]) for row in subset])
                        ),
                        "max_cycle_mass_balance_relative": max(
                            float(row["cycle_mass_balance_relative"]) for row in subset
                        ),
                    }
                )

    rank_checks = []
    for adsorbent in sorted({str(row["adsorbent"]) for row in rows}):
        for n_nodes in sorted({int(row["n_nodes"]) for row in rows if row["adsorbent"] == adsorbent}):
            relevant = [g for g in groups if g["adsorbent"] == adsorbent and g["n_nodes"] == n_nodes]
            if len(relevant) != len(POLICIES):
                continue
            ordered = sorted(
                relevant,
                key=lambda g: (
                    -float(g["event_probability"]),
                    -float(g["mean_h2_recovery"]),
                    float(g["policy_recycle_fraction"]),
                ),
            )
            rank_checks.append(
                {
                    "adsorbent": adsorbent,
                    "n_nodes": n_nodes,
                    "rank_by_event_then_recovery": [float(g["policy_recycle_fraction"]) for g in ordered],
                    "selected_policy": float(ordered[0]["policy_recycle_fraction"]),
                }
            )

    numerical_resolution_checks = []
    for adsorbent in sorted({str(row["adsorbent"]) for row in rows}):
        node_counts = sorted({int(row["n_nodes"]) for row in rows if row["adsorbent"] == adsorbent})
        if len(node_counts) < 2:
            continue
        endpoint_effects_recovery = []
        endpoint_effects_purity = []
        for n_nodes in node_counts:
            low = next(
                (g for g in groups if g["adsorbent"] == adsorbent and g["n_nodes"] == n_nodes and math.isclose(float(g["policy_recycle_fraction"]), min(POLICIES))),
                None,
            )
            high = next(
                (g for g in groups if g["adsorbent"] == adsorbent and g["n_nodes"] == n_nodes and math.isclose(float(g["policy_recycle_fraction"]), max(POLICIES))),
                None,
            )
            if low is not None and high is not None:
                endpoint_effects_recovery.append(abs(float(low["mean_h2_recovery"]) - float(high["mean_h2_recovery"])))
                endpoint_effects_purity.append(abs(float(low["mean_h2_product"]) - float(high["mean_h2_product"])))
        grid_spans_recovery = []
        grid_spans_purity = []
        for policy in POLICIES:
            policy_groups = [
                g
                for g in groups
                if g["adsorbent"] == adsorbent
                and math.isclose(float(g["policy_recycle_fraction"]), policy)
            ]
            if len(policy_groups) == len(node_counts):
                recoveries = [float(g["mean_h2_recovery"]) for g in policy_groups]
                purities = [float(g["mean_h2_product"]) for g in policy_groups]
                grid_spans_recovery.append(max(recoveries) - min(recoveries))
                grid_spans_purity.append(max(purities) - min(purities))
        if endpoint_effects_recovery and grid_spans_recovery:
            max_policy_recovery = max(endpoint_effects_recovery)
            max_grid_recovery = max(grid_spans_recovery)
            max_policy_purity = max(endpoint_effects_purity)
            max_grid_purity = max(grid_spans_purity)
            numerical_resolution_checks.append(
                {
                    "adsorbent": adsorbent,
                    "node_counts": node_counts,
                    "max_endpoint_policy_effect_recovery": max_policy_recovery,
                    "max_grid_span_recovery": max_grid_recovery,
                    "policy_effect_to_grid_span_recovery": max_policy_recovery / max(max_grid_recovery, 1.0e-15),
                    "max_endpoint_policy_effect_purity": max_policy_purity,
                    "max_grid_span_purity": max_grid_purity,
                    "policy_effect_to_grid_span_purity": max_policy_purity / max(max_grid_purity, 1.0e-15),
                    "passes_policy_effect_gt_5x_grid_span": bool(
                        max_policy_recovery > 5.0 * max_grid_recovery
                        and max_policy_purity > 5.0 * max_grid_purity
                    ),
                    "event_labels_stable_across_meshes": len(
                        {bool(row["joint_event"]) for row in rows if row["adsorbent"] == adsorbent}
                    )
                    == 1,
                }
            )

    all_false = all(not bool(row["joint_event"]) for row in rows)
    return {
        "schema": "cce-independent-pyapep-h2-recycle-validation/v3",
        "solver": {
            "name": "pyAPEP",
            "version": package_version("pyapep"),
            "module": str(Path(simsep.__file__).resolve()),
            "numpy_version": np.__version__,
            "scipy_version": scipy.__version__,
        },
        "frozen_protocol": {
            "policies": list(POLICIES),
            "purity_threshold": PURITY_THRESHOLD,
            "recovery_threshold": RECOVERY_THRESHOLD,
            "feed_y": FEED_Y.tolist(),
            "policy_semantics": "adsorption product split to finite recycle tank; tank supplies counter-current purge and product-end pressurisation; source-gas makeup is explicit",
            "recovery_boundary": "external H2 product divided by all external H2 entering adsorption, purge, and product-end pressurisation; the adsorption-feed-only ratio is retained as a non-decision diagnostic",
        },
        "configuration": {
            **{k: v for k, v in config.__dict__.items() if k != "n_nodes"},
            "n_nodes": sorted({int(row["n_nodes"]) for row in rows}),
            "pressurisation_connection": "light-product end",
        },
        "run_count": len(rows),
        "group_summary": groups,
        "rank_checks": rank_checks,
        "numerical_resolution_checks": numerical_resolution_checks,
        "all_joint_events_false": all_false,
        "interpretation": (
            "The independent code path does not reproduce the frozen event over this screen; it is a negative model-form control, not same-policy validation."
            if all_false
            else "At least one frozen event is reproduced; policy ranking still requires mesh and draw stability checks."
        ),
        "claim_boundary": [
            "Independent open-source solver code path; wrapper and policy mapping are project code.",
            "Uniform AC-only and 5A-only columns bracket, but do not reproduce, the layered AC/5A bed.",
            "The isothermal public-column path omits inter-bed pressure equalisation.",
            "External high-purity source-gas makeup is included in the recovery denominator, and product-tank self-sufficiency is reported separately.",
            "A failed frozen event is retained as evidence of model-form dependence and cannot validate the primary 0.420 selection.",
        ],
    }


def write_outputs(rows: list[dict[str, object]], summary: dict[str, object], prefix: Path) -> None:
    flat_rows = []
    for row in rows:
        flat_rows.append({k: v for k, v in row.items() if k not in {"css_history", "product_external_mol", "feed_adsorption_in_mol", "makeup_mol", "tank_withdrawal_mol", "tank_final_mol"}})
    with prefix.with_suffix(".csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(flat_rows[0]))
        writer.writeheader()
        writer.writerows(flat_rows)
    payload = dict(summary)
    payload["runs"] = rows
    prefix.with_suffix(".json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    lines = [
        "# Independent pyAPEP H2 recycle-policy validation",
        "",
        "The public pyAPEP column solver was used as an independent executable code path. The frozen recycle fractions and joint purity/recovery event were not retuned. Product recycle enters a finite tank that supplies counter-current purge and light-product-end pressurisation; any shortfall is recorded as source-gas makeup.",
        "",
        "| adsorbent | nodes | recycle | event | strict gate | mean H2 purity | external-boundary recovery | tank supply | CSS pass | max cycle balance residual |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for group in summary["group_summary"]:
        lines.append(
            f"| {group['adsorbent']} | {group['n_nodes']} | {group['policy_recycle_fraction']:.3f} | "
            f"{group['event_count']}/{group['draw_count']} | {group['strict_same_policy_event_pass_count']}/{group['draw_count']} | "
            f"{group['mean_h2_product']:.6f} | {group['mean_h2_recovery']:.6f} | "
            f"{group['mean_tank_supply_fraction_total']:.4f} | {group['css_pass_count']}/{group['draw_count']} | "
            f"{group['max_cycle_mass_balance_relative']:.3e} |"
        )
    lines += [
        "",
        f"**Interpretation.** {summary['interpretation']}",
        "",
        "This is an independent solver-code-path check, not external plant validation. pyAPEP 0.1.8 uses one uniform adsorbent per column here, so AC-only and 5A-only results are model-form brackets for the local layered bed. The wrapper, recycle-tank bookkeeping, thresholds, and scenario mapping are project code. Inter-bed pressure equalisation is excluded from the isothermal path.",
    ]
    if summary["numerical_resolution_checks"]:
        lines += ["", "## Numerical-resolution audit", ""]
        for check in summary["numerical_resolution_checks"]:
            lines.append(
                f"For {check['adsorbent']} on node counts {check['node_counts']}, the largest endpoint-policy recovery effect is "
                f"`{check['max_endpoint_policy_effect_recovery']:.6g}`, while the largest mesh span is "
                f"`{check['max_grid_span_recovery']:.6g}` (effect/span `{check['policy_effect_to_grid_span_recovery']:.4g}`). "
                f"The corresponding purity effect/span is `{check['policy_effect_to_grid_span_purity']:.4g}`. "
                f"The predeclared 5x numerical-separation gate therefore "
                f"**{'passes' if check['passes_policy_effect_gt_5x_grid_span'] else 'fails'}**."
            )
    prefix.with_suffix(".md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.2), constrained_layout=True)
    marker_map = {"AC": "o", "5A": "s"}
    for adsorbent in sorted({str(row["adsorbent"]) for row in rows}):
        for n_nodes in sorted({int(row["n_nodes"]) for row in rows if row["adsorbent"] == adsorbent}):
            means_purity = []
            means_recovery = []
            for policy in POLICIES:
                subset = [row for row in rows if row["adsorbent"] == adsorbent and int(row["n_nodes"]) == n_nodes and math.isclose(float(row["policy_recycle_fraction"]), policy)]
                means_purity.append(float(np.mean([float(row["h2_product"]) for row in subset])))
                means_recovery.append(float(np.mean([float(row["h2_recovery_external_boundary"]) for row in subset])))
            label = f"{adsorbent}, N={n_nodes}"
            axes[0].plot(POLICIES, means_purity, marker=marker_map.get(adsorbent, "o"), label=label)
            axes[1].plot(POLICIES, means_recovery, marker=marker_map.get(adsorbent, "o"), label=label)
    axes[0].axhline(PURITY_THRESHOLD, color="black", linestyle="--", linewidth=1, label="frozen threshold")
    axes[1].axhline(RECOVERY_THRESHOLD, color="black", linestyle="--", linewidth=1, label="frozen threshold")
    axes[0].set(xlabel="Recycle fraction", ylabel="External-product H2 purity")
    axes[1].set(xlabel="Recycle fraction", ylabel="External-boundary H2 recovery")
    for axis in axes:
        axis.grid(alpha=0.25)
        axis.legend(fontsize=8)
    fig.suptitle("Independent pyAPEP recycle-policy code-path check")
    fig.savefig(prefix.parent / f"{prefix.name}_FIGURE.png", dpi=220)
    fig.savefig(prefix.parent / f"{prefix.name}_FIGURE.pdf")
    plt.close(fig)


def parse_csv_ints(value: str) -> list[int]:
    return [int(item.strip()) for item in value.split(",") if item.strip()]


def parse_csv_strings(value: str) -> list[str]:
    return [item.strip().upper() for item in value.split(",") if item.strip()]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--draw-indices", default="0", help="comma-separated indices from the frozen 32-draw table")
    parser.add_argument("--adsorbents", default="AC,5A", help="AC, 5A, or both")
    parser.add_argument("--nodes", default="5", help="comma-separated axial node counts")
    parser.add_argument("--max-cycles", type=int, default=30)
    parser.add_argument("--min-cycles", type=int, default=12)
    parser.add_argument("--css-tol", type=float, default=1.0e-3)
    parser.add_argument("--n-sec", type=int, default=1)
    parser.add_argument("--output-prefix", default="PSA_QAE_CCE_INDEPENDENT_PYAPEP_H2_RECYCLE_RAW_RUN")
    parser.add_argument("--resume", action="store_true", help="reuse completed runs in the output JSON")
    args = parser.parse_args()

    draw_indices = parse_csv_ints(args.draw_indices)
    adsorbents = parse_csv_strings(args.adsorbents)
    node_counts = parse_csv_ints(args.nodes)
    draws = load_draws(draw_indices)
    prefix = HERE.parent / "results" / "pycharm_publication_enhancement" / args.output_prefix
    checkpoint = prefix.with_name(prefix.name + "_CHECKPOINT").with_suffix(".json")
    rows: list[dict[str, object]] = []
    if args.resume and checkpoint.exists():
        rows = json.loads(checkpoint.read_text(encoding="utf-8")).get("runs", [])
    elif args.resume and prefix.with_suffix(".json").exists():
        candidate_rows = json.loads(prefix.with_suffix(".json").read_text(encoding="utf-8")).get("runs", [])
        if candidate_rows and "h2_recovery_adsorption_feed_proxy" in candidate_rows[0]:
            rows = candidate_rows
    completed = {
        (
            int(row["draw_index"]),
            str(row["adsorbent"]).upper(),
            int(row["n_nodes"]),
            round(float(row["policy_recycle_fraction"]), 9),
        )
        for row in rows
    }
    for adsorbent in adsorbents:
        for n_nodes in node_counts:
            config = SolverConfig(
                n_nodes=n_nodes,
                max_cycles=args.max_cycles,
                min_cycles=args.min_cycles,
                css_tol=args.css_tol,
                n_sec=args.n_sec,
            )
            for draw in draws:
                for policy in POLICIES:
                    key = (draw.draw_index, adsorbent.upper(), n_nodes, round(float(policy), 9))
                    if key in completed:
                        print(
                            f"reusing draw={draw.draw_index} adsorbent={adsorbent} nodes={n_nodes} policy={policy:.3f}",
                            flush=True,
                        )
                        continue
                    print(
                        f"running draw={draw.draw_index} adsorbent={adsorbent} nodes={n_nodes} policy={policy:.3f}",
                        flush=True,
                    )
                    rows.append(run_case(draw, policy, adsorbent, config))
                    completed.add(key)
                    checkpoint.write_text(json.dumps({"runs": rows}, indent=2), encoding="utf-8")
    config_for_summary = SolverConfig(
        n_nodes=node_counts[0],
        max_cycles=args.max_cycles,
        min_cycles=args.min_cycles,
        css_tol=args.css_tol,
        n_sec=args.n_sec,
    )
    summary = summarise(rows, config_for_summary)
    write_outputs(rows, summary, prefix)
    checkpoint.unlink(missing_ok=True)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
