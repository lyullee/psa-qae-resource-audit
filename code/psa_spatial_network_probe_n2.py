"""Mass-conservative five-component spatial PSA network oracle with N2.

The vendor pyAPEP probe is useful for a PDE cross-check, but its public
boundary reconstruction leaves a non-negligible flux residual at the coarse
meshes needed for the uncertainty screen.  This file provides an independent
finite-volume-like network: each axial cell has gas moles and adsorbed loading,
internal face flows are pressure-driven, and every external stream is an
explicit boundary flux.  The model is isothermal and still requires spatial
validation; it is not a plant simulator.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy.integrate import solve_ivp

R = 8.314462618
BAR = 1.0e5
COMPONENTS = ("H2", "CO2", "CH4", "CO", "N2")

# Corrected Ahn et al. layered-bed table, H2/CO2/CH4/CO/N2 order.  The
# corrigendum reports the parameters in mol/kg, mol/(kg K), 1/bar, K, and 1/s.
# Values are transcribed without using a fitted N2 placeholder.
A1 = np.array([16.943, 28.7973, 23.8600, 33.8500, 1.6441], dtype=float)
A2 = np.array([0.02100, 0.07000, 0.05621, 0.09072, 0.00073], dtype=float)
B1 = np.array([6.166e-5, 9.900e-3, 3.432e-3, 2.281e-4, 5.380e-2], dtype=float)
B2 = np.array([1229.0, 1030.0, 1159.0, 1751.0, 326.0], dtype=float)
LDF = np.array([0.700, 0.0355, 0.195, 0.150, 0.261], dtype=float)
# Corrected zeolite 5A table, reordered to H2/CO2/CH4/CO/N2.
Z_A1 = np.array([4.314, 10.0300, 5.8330, 11.8454, 4.8133], dtype=float)
Z_A2 = np.array([0.01060, 0.01858, 0.01192, 0.03130, 0.00668], dtype=float)
Z_B1 = np.array([2.482e-3, 1.5575, 5.9716e-4, 1.990e-2, 5.620e-4], dtype=float)
Z_B2 = np.array([458.0, 207.0, 1731.0, 763.0, 1531.0], dtype=float)
Z_LDF = np.array([0.700, 0.0135, 0.147, 0.063, 0.099], dtype=float)


@dataclass(frozen=True)
class SpatialParams:
    n_cells: int = 16
    bed_volume_m3: float = 0.0785  # reference bed volume used in Wu et al.
    void_fraction: float = 0.433
    rho_s_kg_m3: float = 522.0
    temperature_K: float = 311.157539
    P_high_bar: float = 15.65
    P_low_bar: float = 1.10
    feed_y_dry: tuple[float, ...] = (0.674827, 0.270497, 0.043196, 0.011480, 0.0)
    purge_y_dry: tuple[float, ...] = (0.99, 0.003, 0.004, 0.003, 0.0)
    # Conservative valve conductances keep each explicit gas cell positive;
    # they are numerical settings until a plant valve map is available.
    k_internal_mol_s_bar: float = 2.0
    k_in_mol_s_bar: float = 0.30
    k_out_mol_s_bar: float = 0.30
    # Product-manifold back-pressure represented as a drop below the high
    # pressure level.  The historical 0.8 bar default is retained; exposing
    # it makes the HP product boundary a declared uncertainty/calibration
    # parameter for schedule-faithful external comparisons.
    product_outlet_drop_bar: float = 0.80
    # Optional constant feed flow for comparison with laboratory PSA data
    # reported at a fixed NL/min.  None preserves the historical
    # pressure-driven inlet boundary.
    fixed_feed_flow_mol_s: float | None = None
    # Purge inlet valve conductance can differ from the adsorption feed valve.
    # None preserves the historical shared-conductance boundary.
    k_purge_in_mol_s_bar: float | None = None
    phase_duration_s: float = 30.0
    solver_method: str = "BDF"
    max_step_points: int = 25
    # "AC" preserves the single-layer probe. "AC_Z5A" places AC at the feed
    # end and zeolite 5A in the downstream half of the bed.
    adsorbent_profile: str = "AC"
    zeolite_fraction: float = 0.50
    # When a bed is mirrored into its local flow coordinate, the layered
    # adsorbent profile must be mirrored with it.  The default preserves all
    # historical forward-oriented runs.
    profile_reversed: bool = False
    capacity_factor: float = 1.0
    affinity_factor: float = 1.0
    ldf_factor: float = 1.0

    @property
    def n_component(self) -> int:
        return len(COMPONENTS)

    @property
    def gas_cell_volume_m3(self) -> float:
        return self.void_fraction * self.bed_volume_m3 / self.n_cells

    @property
    def solid_cell_mass_kg(self) -> float:
        return (1.0 - self.void_fraction) * self.rho_s_kg_m3 * self.bed_volume_m3 / self.n_cells


def qstar(P_bar: np.ndarray, y: np.ndarray, p: SpatialParams) -> np.ndarray:
    P = np.maximum(np.asarray(P_bar, dtype=float), 0.0)
    Y = np.asarray(y, dtype=float)
    partial = np.maximum(Y, 0.0) * P[None, :]
    a1, a2, b1, b2, _ = profile_parameter_arrays(p)
    qcap = p.capacity_factor * (a1 - a2 * p.temperature_K)
    b = p.affinity_factor * b1 * np.exp(b2 / p.temperature_K)
    den = 1.0 + np.sum(b * partial, axis=0)
    return qcap * b * partial / den


def profile_parameter_arrays(p: SpatialParams) -> tuple[np.ndarray, ...]:
    """Return component-by-cell adsorption arrays and kinetic rates."""
    ac = [v[:, None] * np.ones((1, p.n_cells)) for v in (A1, A2, B1, B2, LDF)]
    if p.adsorbent_profile.upper() != "AC_Z5A":
        return tuple(ac)
    split = int(round(p.n_cells * (1.0 - p.zeolite_fraction)))
    mask = np.arange(p.n_cells) >= split
    zeo = [v[:, None] * np.ones((1, p.n_cells)) for v in (Z_A1, Z_A2, Z_B1, Z_B2, Z_LDF)]
    arrays = tuple(np.where(mask[None, :], z, a) for a, z in zip(ac, zeo))
    if p.profile_reversed:
        arrays = tuple(np.flip(v, axis=1) for v in arrays)
    return arrays


def profile_cell_volumes(p: SpatialParams) -> tuple[np.ndarray, np.ndarray]:
    """Return gas volume and solid mass per axial cell."""
    if p.adsorbent_profile.upper() != "AC_Z5A":
        gas = np.full(p.n_cells, p.void_fraction * p.bed_volume_m3 / p.n_cells)
        solid = np.full(p.n_cells, (1.0 - p.void_fraction) * p.rho_s_kg_m3 * p.bed_volume_m3 / p.n_cells)
        return gas, solid
    split = int(round(p.n_cells * (1.0 - p.zeolite_fraction)))
    eps = np.where(np.arange(p.n_cells) < split, 0.433, 0.357)
    rho = np.where(np.arange(p.n_cells) < split, 522.0, 698.0)
    gas = eps * p.bed_volume_m3 / p.n_cells
    solid = (1.0 - eps) * rho * p.bed_volume_m3 / p.n_cells
    if p.profile_reversed:
        gas = gas[::-1]
        solid = solid[::-1]
    return gas, solid


def unpack(x: np.ndarray, p: SpatialParams) -> tuple[np.ndarray, np.ndarray]:
    n = p.n_component * p.n_cells
    ng = np.maximum(np.asarray(x[:n], dtype=float).reshape(p.n_component, p.n_cells), 1e-14)
    q = np.maximum(np.asarray(x[n:2 * n], dtype=float).reshape(p.n_component, p.n_cells), 0.0)
    return ng, q


def pack(ng: np.ndarray, q: np.ndarray) -> np.ndarray:
    return np.concatenate([np.asarray(ng, dtype=float).ravel(), np.asarray(q, dtype=float).ravel()])


def cell_pressure(ng: np.ndarray, p: SpatialParams) -> np.ndarray:
    gas, _ = profile_cell_volumes(p)
    return np.sum(ng, axis=0) * R * p.temperature_K / gas / BAR


def cell_y(ng: np.ndarray) -> np.ndarray:
    return ng / np.maximum(np.sum(ng, axis=0, keepdims=True), 1e-14)


def initial_state(P_bar: float, y: np.ndarray, p: SpatialParams) -> np.ndarray:
    y = np.asarray(y, dtype=float); y = y / y.sum()
    gas, _ = profile_cell_volumes(p)
    nt = P_bar * BAR * gas / (R * p.temperature_K)
    ng = nt * y[:, None] * np.ones((1, p.n_cells))
    q = qstar(np.full(p.n_cells, P_bar), np.repeat(y[:, None], p.n_cells, axis=1), p)
    return pack(ng, q)


def stored_moles(x: np.ndarray, p: SpatialParams) -> np.ndarray:
    ng, q = unpack(x, p)
    _, solid = profile_cell_volumes(p)
    return np.sum(ng, axis=1) + np.sum(q * solid[None, :], axis=1)


def boundary_fluxes(ng: np.ndarray, step: str, y_in: np.ndarray, p: SpatialParams) -> tuple[float, float, np.ndarray, np.ndarray]:
    """Return (left inlet, right inlet, left outlet, right outlet) molar streams."""
    P = cell_pressure(ng, p); Y = cell_y(ng)
    y_in = np.asarray(y_in, dtype=float); y_in = y_in / y_in.sum()
    left_in = right_in = 0.0
    left_out = right_out = 0.0
    if step == "adsorption":
        left_in = (
            float(p.fixed_feed_flow_mol_s)
            if p.fixed_feed_flow_mol_s is not None
            else p.k_in_mol_s_bar * max(p.P_high_bar - P[0], 0.0)
        )
        right_out = p.k_out_mol_s_bar * max(P[-1] - (p.P_high_bar - p.product_outlet_drop_bar), 0.0)
    elif step == "blowdown":
        left_out = p.k_out_mol_s_bar * max(P[0] - p.P_low_bar, 0.0)
    elif step == "purge":
        purge_k = p.k_in_mol_s_bar if p.k_purge_in_mol_s_bar is None else p.k_purge_in_mol_s_bar
        right_in = purge_k * max(p.P_high_bar - P[-1], 0.0)
        left_out = p.k_out_mol_s_bar * max(P[0] - p.P_low_bar, 0.0)
    elif step == "provide_purge":
        # Co-current depressurization: withdraw H2-rich gas from the
        # product end to supply another bed's purge or pressurization step.
        right_out = p.k_out_mol_s_bar * max(P[-1] - (p.P_high_bar - p.product_outlet_drop_bar), 0.0)
    elif step == "pressurization":
        left_in = p.k_in_mol_s_bar * max(p.P_high_bar - P[0], 0.0)
    else:
        raise ValueError(step)
    return float(left_in), float(right_in), np.asarray(left_out * Y[:, 0]), np.asarray(right_out * Y[:, -1])


def rhs_factory(step: str, y_in: np.ndarray, p: SpatialParams):
    y_in = np.asarray(y_in, dtype=float); y_in = y_in / y_in.sum()

    def rhs(_t: float, x: np.ndarray) -> np.ndarray:
        ng, q = unpack(x, p); P = cell_pressure(ng, p); Y = cell_y(ng)
        _, _, _, _, k_ldf = profile_parameter_arrays(p)
        qeq = qstar(P, Y, p)
        dq = p.ldf_factor * k_ldf * (qeq - q)
        # Positive face flow is left -> right.  Upwind component fluxes make
        # every internal transfer conservative even when pressure reverses.
        f = p.k_internal_mol_s_bar * (P[:-1] - P[1:])
        face = np.zeros((p.n_component, max(p.n_cells - 1, 0)))
        for j in range(max(p.n_cells - 1, 0)):
            face[:, j] = f[j] * (Y[:, j] if f[j] >= 0 else Y[:, j + 1])
        left_in, right_in, left_out, right_out = boundary_fluxes(ng, step, y_in, p)
        _, solid = profile_cell_volumes(p)
        dng = -solid[None, :] * dq
        if p.n_cells > 1:
            # Positive face flow leaves the left cell and enters the right
            # cell.  This sign convention is what makes internal transfers
            # exactly conservative component by component.
            dng[:, :-1] -= face
            dng[:, 1:] += face
        if step in ("adsorption", "pressurization"):
            dng[:, 0] += left_in * y_in
        if step == "purge":
            dng[:, -1] += right_in * y_in
        if step in ("adsorption", "provide_purge"):
            dng[:, -1] -= right_out
        if step in ("blowdown", "purge"):
            dng[:, 0] -= left_out
        return pack(dng, dq)

    return rhs


def integrate_step(x: np.ndarray, step: str, duration_s: float, y_in: np.ndarray, p: SpatialParams) -> tuple[np.ndarray, dict]:
    sol = solve_ivp(
        rhs_factory(step, y_in, p), (0.0, float(duration_s)), x,
        method=p.solver_method, rtol=2e-7, atol=2e-10,
        max_step=max(float(duration_s) / max(int(p.max_step_points), 1), 1e-3), dense_output=False,
    )
    if not sol.success:
        raise RuntimeError(sol.message)
    x_end = np.maximum(sol.y[:, -1], 0.0)
    in_stream = []; out_stream = []
    for col in sol.y.T:
        ng, _ = unpack(col, p)
        li, ri, lo, ro = boundary_fluxes(ng, step, y_in, p)
        yin = np.asarray(y_in, dtype=float) / np.sum(y_in)
        in_stream.append((li * yin) + (ri * yin))
        out_stream.append(lo + ro)
    in_mol = np.asarray([np.trapezoid(np.asarray(in_stream)[:, i], sol.t) for i in range(p.n_component)])
    out_mol = np.asarray([np.trapezoid(np.asarray(out_stream)[:, i], sol.t) for i in range(p.n_component)])
    residual = in_mol - out_mol - (stored_moles(x_end, p) - stored_moles(x, p))
    return x_end, {
        "step": step, "duration_s": float(duration_s), "in_mol": in_mol.tolist(), "out_mol": out_mol.tolist(),
        "mass_balance_residual_mol": residual.tolist(),
        "mass_balance_relative_max": float(np.max(np.abs(residual)) / max(float(np.sum(in_mol) + np.sum(out_mol)), 1e-12)),
        "outlet_y": (out_mol / max(float(np.sum(out_mol)), 1e-12)).tolist(),
    }


def run_cycle(n_cycles: int = 100, p: SpatialParams | None = None) -> dict:
    p = SpatialParams() if p is None else p
    y_feed = np.asarray(p.feed_y_dry, dtype=float); y_feed /= y_feed.sum()
    y_purge = np.asarray(p.purge_y_dry, dtype=float); y_purge /= y_purge.sum()
    x = initial_state(p.P_high_bar, y_feed, p)
    history = []; last = []; start_last = x.copy()
    for cycle in range(1, int(n_cycles) + 1):
        start = x.copy(); last = []
        start_last = start
        for step, yin in (("adsorption", y_feed), ("blowdown", y_feed), ("purge", y_purge), ("pressurization", y_purge)):
            x, stream = integrate_step(x, step, p.phase_duration_s, yin, p); last.append(stream)
        css = float(np.max(np.abs(x - start) / np.maximum(np.abs(start), 1e-10)))
        history.append({"cycle": cycle, "css_residual": css})
    prod = np.asarray(last[0]["out_mol"], dtype=float)
    feed = np.asarray(last[0]["in_mol"], dtype=float)
    cycle_in = np.sum([np.asarray(s["in_mol"]) for s in last], axis=0)
    cycle_out = np.sum([np.asarray(s["out_mol"]) for s in last], axis=0)
    inv_delta = stored_moles(x, p) - stored_moles(start_last, p)
    residual = cycle_in - cycle_out - inv_delta
    return {
        "n_cycles": int(n_cycles), "n_cells": int(p.n_cells), "phase_duration_s": float(p.phase_duration_s),
        "css_residual_final": history[-1]["css_residual"], "css_gate_1e-4": history[-1]["css_residual"] < 1e-4,
        "step_mass_balance_relative_max": float(max(s["mass_balance_relative_max"] for s in last)),
        "cycle_mass_balance_relative_max": float(np.max(np.abs(residual)) / max(float(np.sum(cycle_in) + np.sum(cycle_out)), 1e-12)),
        "adsorption_product_y": (prod / max(float(np.sum(prod)), 1e-12)).tolist(),
        "adsorption_h2_recovery_proxy": float(prod[0] / max(float(feed[0]), 1e-12)),
        "cycle_input_mol": cycle_in.tolist(), "cycle_output_mol": cycle_out.tolist(), "cycle_inventory_delta_mol": inv_delta.tolist(),
        "cycle_mass_balance_residual_mol": residual.tolist(), "components": list(COMPONENTS),
        "model_status": "spatial_isothermal_pressure_network_four_component_unvalidated",
        "source_parameter_note": "AC Extended-Langmuir and LDF rates from hydrogen-PSA literature",
        "css_history": history,
    }


if __name__ == "__main__":
    print(json.dumps(run_cycle(), indent=2))

