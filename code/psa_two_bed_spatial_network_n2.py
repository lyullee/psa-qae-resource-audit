"""Conservative five-component two-bed spatial PSA network with explicit pair ledgers.

This is a bridge model between the single-bed spatial oracle and a
schedule-faithful plant simulator.  Each bed is a cell-wise gas/solid network;
bed B is mirrored so the same counter-current four-step kernel can be reused.
Two algebraically conservative endpoint equalizations are inserted between
the staggered phases.  Purge gas is an explicit external source and all
adsorption outlets are labelled as product diagnostics.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from psa_qae.psa_spatial_network_probe_n2 import (  # noqa: E402
    COMPONENTS,
    SpatialParams,
    cell_pressure,
    cell_y,
    integrate_step,
    initial_state,
    pack,
    profile_cell_volumes,
    stored_moles,
    unpack,
)


def mirror_state(x: np.ndarray, p: SpatialParams) -> np.ndarray:
    """Mirror gas and solid axial coordinates for the reverse-oriented bed."""
    ng, q = unpack(x, p)
    return pack(ng[:, ::-1], q[:, ::-1])


def oriented_step(x: np.ndarray, step: str, duration_s: float, y_in: np.ndarray,
                  p: SpatialParams, *, reverse: bool) -> tuple[np.ndarray, dict]:
    """Run a step in the bed's local flow orientation."""
    local = mirror_state(x, p) if reverse else x
    local_next, stream = integrate_step(local, step, duration_s, y_in, p)
    return (mirror_state(local_next, p) if reverse else local_next), stream


def equalize_endpoints(state_a: np.ndarray, state_b: np.ndarray,
                       p: SpatialParams, *, index_a: int, index_b: int,
                       duration_s: float, conductance_mol_s_bar: float) -> tuple[np.ndarray, np.ndarray, dict]:
    """Transfer gas between two endpoint cells without changing pair mass."""
    a = state_a.copy(); b = state_b.copy()
    nga, qa = unpack(a, p); ngb, qb = unpack(b, p)
    Pa = float(cell_pressure(nga, p)[index_a]); Pb = float(cell_pressure(ngb, p)[index_b])
    if Pa >= Pb:
        high_name, high_ng, high_idx, low_ng, low_idx = "A_to_B", nga, index_a, ngb, index_b
    else:
        high_name, high_ng, high_idx, low_ng, low_idx = "B_to_A", ngb, index_b, nga, index_a
    dp = max(abs(Pa - Pb), 0.0)
    n_high = max(float(np.sum(high_ng[:, high_idx])), 1e-14)
    transfer_total = min(float(conductance_mol_s_bar) * dp * float(duration_s), 0.25 * n_high)
    y_high = high_ng[:, high_idx] / n_high
    transfer = transfer_total * y_high
    high_ng[:, high_idx] -= transfer
    low_ng[:, low_idx] += transfer
    a_next = pack(nga, qa); b_next = pack(ngb, qb)
    residual = (stored_moles(a_next, p) + stored_moles(b_next, p)
                - stored_moles(state_a, p) - stored_moles(state_b, p))
    return a_next, b_next, {
        "direction": high_name,
        "index_a": int(index_a), "index_b": int(index_b),
        "pressure_start_a_bar": Pa, "pressure_start_b_bar": Pb,
        "transfer_mol": transfer.tolist(),
        "pair_mass_residual_mol": residual.tolist(),
    }


def run_pair_cycle(state_a: np.ndarray, state_b: np.ndarray, p: SpatialParams,
                   *, phase_duration_s: float, equalization_duration_s: float,
                   equalization_conductance: float) -> tuple[np.ndarray, np.ndarray, list[dict], list[dict]]:
    """Run one phase-staggered four-step pair cycle."""
    y_feed = np.asarray(p.feed_y_dry, dtype=float); y_feed /= y_feed.sum()
    y_purge = np.asarray(p.purge_y_dry, dtype=float); y_purge /= y_purge.sum()
    streams: list[dict] = []
    equalizations: list[dict] = []

    # A adsorbs while B is pressurized.  Bed B has the opposite physical
    # orientation, so both calls use the same local counter-current kernel.
    state_a, s = oriented_step(state_a, "adsorption", phase_duration_s, y_feed, p, reverse=False)
    streams.append({"bed": "A", "step": "adsorption", **s})
    state_b, s = oriented_step(state_b, "pressurization", phase_duration_s, y_purge, p, reverse=True)
    streams.append({"bed": "B", "step": "pressurization", **s})
    state_a, state_b, eq = equalize_endpoints(
        state_a, state_b, p, index_a=p.n_cells - 1, index_b=0,
        duration_s=equalization_duration_s, conductance_mol_s_bar=equalization_conductance,
    )
    eq["stage"] = "product_end_equalization"; equalizations.append(eq)

    # Switch adsorption duty and equalize the feed ends after A blowdown/B ads.
    state_a, s = oriented_step(state_a, "blowdown", phase_duration_s, y_feed, p, reverse=False)
    streams.append({"bed": "A", "step": "blowdown", **s})
    state_b, s = oriented_step(state_b, "adsorption", phase_duration_s, y_feed, p, reverse=True)
    streams.append({"bed": "B", "step": "adsorption", **s})
    state_a, state_b, eq = equalize_endpoints(
        state_a, state_b, p, index_a=0, index_b=p.n_cells - 1,
        duration_s=equalization_duration_s, conductance_mol_s_bar=equalization_conductance,
    )
    eq["stage"] = "feed_end_equalization"; equalizations.append(eq)

    # Regeneration of A and B, followed by counter-current pressurization.
    state_a, s = oriented_step(state_a, "purge", phase_duration_s, y_purge, p, reverse=False)
    streams.append({"bed": "A", "step": "purge", **s})
    state_b, s = oriented_step(state_b, "blowdown", phase_duration_s, y_feed, p, reverse=True)
    streams.append({"bed": "B", "step": "blowdown", **s})
    state_a, s = oriented_step(state_a, "pressurization", phase_duration_s, y_purge, p, reverse=False)
    streams.append({"bed": "A", "step": "pressurization", **s})
    state_b, s = oriented_step(state_b, "purge", phase_duration_s, y_purge, p, reverse=True)
    streams.append({"bed": "B", "step": "purge", **s})
    return state_a, state_b, streams, equalizations


def run_cycle(n_cycles: int = 50, p: SpatialParams | None = None,
              *, phase_duration_s: float | None = None,
              equalization_duration_s: float = 2.0,
              equalization_conductance: float = 0.10) -> dict:
    p = SpatialParams() if p is None else p
    duration = float(p.phase_duration_s if phase_duration_s is None else phase_duration_s)
    y_feed = np.asarray(p.feed_y_dry, dtype=float); y_feed /= y_feed.sum()
    state_a = initial_state(p.P_high_bar, y_feed, p)
    state_b = initial_state(p.P_low_bar, y_feed, p)
    history = []
    last_streams: list[dict] = []; last_equalizations: list[dict] = []
    max_step_balance = 0.0
    for cycle in range(1, int(n_cycles) + 1):
        start_a = state_a.copy(); start_b = state_b.copy()
        state_a, state_b, last_streams, last_equalizations = run_pair_cycle(
            state_a, state_b, p, phase_duration_s=duration,
            equalization_duration_s=equalization_duration_s,
            equalization_conductance=equalization_conductance,
        )
        css_a = np.max(np.abs(state_a - start_a) / np.maximum(np.abs(start_a), 1e-10))
        css_b = np.max(np.abs(state_b - start_b) / np.maximum(np.abs(start_b), 1e-10))
        max_step_balance = max(max_step_balance, *(float(s["mass_balance_relative_max"]) for s in last_streams))
        history.append({"cycle": cycle, "css_residual_max": float(max(css_a, css_b))})

    n = p.n_component
    external_in = np.sum([np.asarray(s["in_mol"], dtype=float) for s in last_streams], axis=0)
    external_out = np.sum([np.asarray(s["out_mol"], dtype=float) for s in last_streams], axis=0)
    product_out = np.sum([
        np.asarray(s["out_mol"], dtype=float) for s in last_streams if s["step"] == "adsorption"
    ], axis=0)
    feed_in = np.sum([
        np.asarray(s["in_mol"], dtype=float) for s in last_streams if s["step"] == "adsorption"
    ], axis=0)
    inventory_start = stored_moles(start_a, p) + stored_moles(start_b, p)
    inventory_end = stored_moles(state_a, p) + stored_moles(state_b, p)
    residual = external_in - external_out - (inventory_end - inventory_start)
    eq_residual = max(float(np.max(np.abs(e["pair_mass_residual_mol"]))) for e in last_equalizations)
    denom = max(float(np.sum(external_in) + np.sum(external_out)), 1e-12)
    return {
        "n_cycles": int(n_cycles), "n_cells": int(p.n_cells), "phase_duration_s": duration,
        "equalization_duration_s": float(equalization_duration_s),
        "equalization_conductance_mol_s_bar": float(equalization_conductance),
        "css_residual_final": history[-1]["css_residual_max"],
        "css_gate_1e-4": bool(history[-1]["css_residual_max"] < 1e-4),
        "step_mass_balance_relative_max": max_step_balance,
        "cycle_mass_balance_relative_max": float(np.max(np.abs(residual)) / denom),
        "equalization_pair_mass_residual_max_mol": eq_residual,
        "external_in_mol": external_in.tolist(), "external_out_mol": external_out.tolist(),
        "pair_inventory_delta_mol": (inventory_end - inventory_start).tolist(),
        "pair_mass_balance_residual_mol": residual.tolist(),
        "adsorption_feed_mol": feed_in.tolist(), "adsorption_product_mol": product_out.tolist(),
        "adsorption_product_y": (product_out / max(float(np.sum(product_out)), 1e-12)).tolist(),
        "adsorption_h2_recovery_proxy": float(product_out[0] / max(feed_in[0], 1e-12)),
        "components": list(COMPONENTS),
        "model_status": "two_bed_spatial_isothermal_network_internal_schedule_bridge_unvalidated",
        "css_history": history,
        "last_equalizations": last_equalizations,
    }


if __name__ == "__main__":
    print(json.dumps(run_cycle(), indent=2))

