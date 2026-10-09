"""Five-component two-bed spatial PSA bridge with an explicit finite purge tank.

The tank variant keeps purge and pressurization gas as an internal inventory.
Adsorption product is split into an external product stream and a configurable
recycle fraction. If the tank cannot supply a requested source stream, the
shortfall is explicit makeup gas with the same composition used for the
withdrawal. This is a bookkeeping bridge; tank composition and valve
schedule still require plant calibration.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from psa_qae.psa_spatial_network_probe_n2 import COMPONENTS, SpatialParams, initial_state, stored_moles
from psa_qae.psa_two_bed_spatial_network_n2 import equalize_endpoints, oriented_step


def _normalise(y: np.ndarray) -> np.ndarray:
    y = np.maximum(np.asarray(y, dtype=float), 0.0)
    return y / max(float(y.sum()), 1e-14)


def _tank_step(state: np.ndarray, step: str, duration_s: float, p: SpatialParams,
               tank: np.ndarray, makeup_y: np.ndarray, *, reverse: bool) -> tuple[np.ndarray, dict, np.ndarray, np.ndarray]:
    """Run a tank-sourced step and return (state, stream, new_tank, makeup)."""
    tank = np.maximum(np.asarray(tank, dtype=float), 0.0)
    tank_total = float(tank.sum())
    source_y = _normalise(tank) if tank_total > 1e-14 else _normalise(makeup_y)
    state_next, stream = oriented_step(state, step, duration_s, source_y, p, reverse=reverse)
    incoming = np.asarray(stream["in_mol"], dtype=float)
    incoming_total = float(incoming.sum())
    withdraw_total = min(incoming_total, tank_total)
    from_tank = withdraw_total * source_y
    makeup = incoming - from_tank
    tank_next = tank - from_tank
    stream["source_y"] = source_y.tolist()
    stream["tank_withdrawal_mol"] = from_tank.tolist()
    stream["makeup_mol"] = makeup.tolist()
    return state_next, stream, tank_next, makeup


def _add_recycle(tank: np.ndarray, product: np.ndarray, recycle_fraction: float,
                 capacity_mol: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    recycle = float(recycle_fraction) * np.maximum(np.asarray(product, dtype=float), 0.0)
    candidate = np.maximum(tank, 0.0) + recycle
    total = float(candidate.sum())
    if total <= capacity_mol:
        return candidate, recycle, np.zeros_like(candidate)
    keep = candidate * (capacity_mol / total)
    overflow = candidate - keep
    return keep, recycle, overflow


def run_cycle(n_cycles: int = 50, p: SpatialParams | None = None, *,
              phase_duration_s: float | None = None,
              adsorption_duration_s: float | None = None,
              non_adsorption_duration_s: float | None = None,
              equalization_duration_s: float = 2.0,
              equalization_conductance: float = 0.10,
              recycle_fraction: float = 0.50,
              tank_capacity_mol: float = 100.0,
              initial_tank_moles: float = 0.0,
              trace_cycle_states: bool = False) -> dict:
    p = SpatialParams() if p is None else p
    duration = float(p.phase_duration_s if phase_duration_s is None else phase_duration_s)
    # The historical API used one duration for every step.  Keep that default
    # for all existing studies, but allow external experiments that vary only
    # the adsorption step while keeping purge/blowdown/pressurization fixed.
    adsorption_duration = float(duration if adsorption_duration_s is None else adsorption_duration_s)
    non_adsorption_duration = float(duration if non_adsorption_duration_s is None else non_adsorption_duration_s)
    y_feed = _normalise(np.asarray(p.feed_y_dry, dtype=float))
    y_purge = _normalise(np.asarray(p.purge_y_dry, dtype=float))
    state_a = initial_state(p.P_high_bar, y_feed, p)
    state_b = initial_state(p.P_low_bar, y_feed, p)
    tank = initial_tank_moles * y_purge
    history = []
    last_external_in = np.zeros(p.n_component)
    last_external_out = np.zeros(p.n_component)
    last_product = np.zeros(p.n_component)
    last_feed = np.zeros(p.n_component)
    last_makeup = np.zeros(p.n_component)
    last_overflow = np.zeros(p.n_component)
    last_residual = np.zeros(p.n_component)
    # Keep the last-cycle ledger for CSS diagnostics, but also retain a
    # cumulative ledger so the external product boundary is defined over the
    # full simulated campaign rather than only the final cycle.
    cumulative_external_in = np.zeros(p.n_component)
    cumulative_external_out = np.zeros(p.n_component)
    cumulative_product = np.zeros(p.n_component)
    cumulative_feed = np.zeros(p.n_component)
    cumulative_makeup = np.zeros(p.n_component)
    cumulative_overflow = np.zeros(p.n_component)
    initial_inventory = stored_moles(state_a, p) + stored_moles(state_b, p) + tank
    max_step_balance = 0.0
    max_equalization_residual = 0.0

    for cycle in range(1, int(n_cycles) + 1):
        start_a = state_a.copy(); start_b = state_b.copy(); start_tank = tank.copy()
        external_in = np.zeros(p.n_component); external_out = np.zeros(p.n_component)
        product_external = np.zeros(p.n_component); feed_in = np.zeros(p.n_component)
        makeup_cycle = np.zeros(p.n_component); overflow_cycle = np.zeros(p.n_component)

        # A adsorption / B tank-sourced pressurization.
        state_a, sa = oriented_step(state_a, "adsorption", adsorption_duration, y_feed, p, reverse=False)
        state_b, sb, tank, makeup = _tank_step(state_b, "pressurization", non_adsorption_duration, p, tank, y_purge, reverse=True)
        external_in += np.asarray(sa["in_mol"]); external_in += makeup
        external_out += np.asarray(sb["out_mol"])
        feed_in += np.asarray(sa["in_mol"])
        tank, recycle, overflow = _add_recycle(tank, np.asarray(sa["out_mol"]), recycle_fraction, tank_capacity_mol)
        product_external += np.asarray(sa["out_mol"]) - recycle
        external_out += np.asarray(sa["out_mol"]) - recycle + overflow
        overflow_cycle += overflow; makeup_cycle += makeup
        max_step_balance = max(max_step_balance, float(sa["mass_balance_relative_max"]), float(sb["mass_balance_relative_max"]))

        state_a, state_b, eq = equalize_endpoints(
            state_a, state_b, p, index_a=p.n_cells - 1, index_b=0,
            duration_s=equalization_duration_s, conductance_mol_s_bar=equalization_conductance,
        )
        max_equalization_residual = max(max_equalization_residual, float(np.max(np.abs(eq["pair_mass_residual_mol"]))))

        # A blowdown / B adsorption.
        state_a, sa = oriented_step(state_a, "blowdown", non_adsorption_duration, y_feed, p, reverse=False)
        state_b, sb = oriented_step(state_b, "adsorption", adsorption_duration, y_feed, p, reverse=True)
        external_in += np.asarray(sb["in_mol"])
        external_out += np.asarray(sa["out_mol"])
        feed_in += np.asarray(sb["in_mol"])
        tank, recycle, overflow = _add_recycle(tank, np.asarray(sb["out_mol"]), recycle_fraction, tank_capacity_mol)
        product_external += np.asarray(sb["out_mol"]) - recycle
        external_out += np.asarray(sb["out_mol"]) - recycle + overflow
        overflow_cycle += overflow
        max_step_balance = max(max_step_balance, float(sa["mass_balance_relative_max"]), float(sb["mass_balance_relative_max"]))

        state_a, state_b, eq = equalize_endpoints(
            state_a, state_b, p, index_a=0, index_b=p.n_cells - 1,
            duration_s=equalization_duration_s, conductance_mol_s_bar=equalization_conductance,
        )
        max_equalization_residual = max(max_equalization_residual, float(np.max(np.abs(eq["pair_mass_residual_mol"]))))

        # A tank-sourced purge / B blowdown.
        state_a, sa, tank, makeup = _tank_step(state_a, "purge", non_adsorption_duration, p, tank, y_purge, reverse=False)
        state_b, sb = oriented_step(state_b, "blowdown", non_adsorption_duration, y_feed, p, reverse=True)
        external_in += np.asarray(sb["in_mol"]) + makeup
        external_out += np.asarray(sa["out_mol"]) + np.asarray(sb["out_mol"])
        makeup_cycle += makeup
        max_step_balance = max(max_step_balance, float(sa["mass_balance_relative_max"]), float(sb["mass_balance_relative_max"]))

        # Both beds are tank-sourced for final pressurization/purge.
        state_a, sa, tank, makeup_a = _tank_step(state_a, "pressurization", non_adsorption_duration, p, tank, y_purge, reverse=False)
        state_b, sb, tank, makeup_b = _tank_step(state_b, "purge", non_adsorption_duration, p, tank, y_purge, reverse=True)
        external_in += makeup_a + makeup_b
        external_out += np.asarray(sa["out_mol"]) + np.asarray(sb["out_mol"])
        makeup_cycle += makeup_a + makeup_b
        max_step_balance = max(max_step_balance, float(sa["mass_balance_relative_max"]), float(sb["mass_balance_relative_max"]))

        inventory_start = stored_moles(start_a, p) + stored_moles(start_b, p) + start_tank
        inventory_end = stored_moles(state_a, p) + stored_moles(state_b, p) + tank
        residual = external_in - external_out - (inventory_end - inventory_start)
        css = max(
            float(np.max(np.abs(state_a - start_a) / np.maximum(np.abs(start_a), 1e-10))),
            float(np.max(np.abs(state_b - start_b) / np.maximum(np.abs(start_b), 1e-10))),
            float(np.max(np.abs(tank - start_tank) / np.maximum(np.abs(start_tank), 1e-10))) if np.any(start_tank) else float(np.max(np.abs(tank - start_tank) / 1e-10)),
        )
        state_l1_a = float(np.sum(np.abs(state_a - start_a)) / max(float(np.sum(np.abs(start_a))), 1.0e-12))
        state_l1_b = float(np.sum(np.abs(state_b - start_b)) / max(float(np.sum(np.abs(start_b))), 1.0e-12))
        tank_l1 = float(np.sum(np.abs(tank - start_tank)) / max(float(np.sum(np.abs(start_tank))), 1.0e-12)) if np.any(start_tank) else float(np.sum(np.abs(tank - start_tank)) / max(float(np.sum(np.abs(start_a)) + np.sum(np.abs(start_b))), 1.0e-12))
        css_l1 = max(state_l1_a, state_l1_b, tank_l1)
        cycle_purity = float(product_external[0] / max(float(product_external.sum()), 1e-12))
        cycle_recovery = float(product_external[0] / max(float(feed_in[0]), 1e-12))
        cycle_record = {
            "cycle": cycle,
            "css_residual_max": css,
            "css_residual_l1": css_l1,
            "tank_moles": float(tank.sum()),
            "h2_product": cycle_purity,
            "h2_recovery_external_proxy": cycle_recovery,
            "joint_anchor_event": bool(cycle_purity >= 0.9998 and cycle_recovery >= 0.789),
            "product_external_mol": product_external.tolist(),
            "feed_adsorption_in_mol": feed_in.tolist(),
        }
        if trace_cycle_states:
            cycle_record.update(
                {
                    "state_a_start": np.asarray(start_a, dtype=float).tolist(),
                    "state_b_start": np.asarray(start_b, dtype=float).tolist(),
                    "tank_start_mol": np.asarray(start_tank, dtype=float).tolist(),
                    "state_a_end": np.asarray(state_a, dtype=float).tolist(),
                    "state_b_end": np.asarray(state_b, dtype=float).tolist(),
                    "tank_end_mol": np.asarray(tank, dtype=float).tolist(),
                }
            )
        history.append(cycle_record)
        last_external_in, last_external_out = external_in, external_out
        last_product, last_feed = product_external, feed_in
        last_makeup, last_overflow = makeup_cycle, overflow_cycle
        last_residual = residual
        cumulative_external_in += external_in
        cumulative_external_out += external_out
        cumulative_product += product_external
        cumulative_feed += feed_in
        cumulative_makeup += makeup_cycle
        cumulative_overflow += overflow_cycle

    denom = max(float(last_external_in.sum() + last_external_out.sum()), 1e-12)
    cumulative_denom = max(float(cumulative_external_in.sum() + cumulative_external_out.sum()), 1e-12)
    cumulative_residual = cumulative_external_in - cumulative_external_out - (inventory_end - initial_inventory)
    return {
        "n_cycles": int(n_cycles), "n_cells": int(p.n_cells), "phase_duration_s": duration,
        "adsorption_duration_s": adsorption_duration,
        "non_adsorption_duration_s": non_adsorption_duration,
        "recycle_fraction": float(recycle_fraction), "tank_capacity_mol": float(tank_capacity_mol),
        "initial_tank_moles": float(initial_tank_moles), "final_tank_moles": float(tank.sum()),
        "css_residual_final": history[-1]["css_residual_max"],
        "css_gate_1e-4": bool(history[-1]["css_residual_max"] < 1e-4),
        "css_residual_l1_final": history[-1]["css_residual_l1"],
        "css_l1_gate_1e-4": bool(history[-1]["css_residual_l1"] < 1e-4),
        "step_mass_balance_relative_max": max_step_balance,
        "cycle_mass_balance_relative_max": float(np.max(np.abs(last_external_in - last_external_out - (inventory_end - inventory_start))) / denom),
        "equalization_pair_mass_residual_max_mol": max_equalization_residual,
        "external_in_mol": last_external_in.tolist(), "external_out_mol": last_external_out.tolist(),
        "cycle_mass_balance_residual_mol": last_residual.tolist(),
        "product_external_mol": last_product.tolist(), "feed_adsorption_in_mol": last_feed.tolist(),
        "makeup_mol": last_makeup.tolist(), "overflow_mol": last_overflow.tolist(),
        "product_external_y": (last_product / max(float(last_product.sum()), 1e-12)).tolist(),
        "h2_recovery_external_proxy": float(last_product[0] / max(last_feed[0], 1e-12)),
        "cumulative_external_in_mol": cumulative_external_in.tolist(),
        "cumulative_external_out_mol": cumulative_external_out.tolist(),
        "cumulative_product_external_mol": cumulative_product.tolist(),
        "cumulative_feed_adsorption_in_mol": cumulative_feed.tolist(),
        "cumulative_makeup_mol": cumulative_makeup.tolist(),
        "cumulative_overflow_mol": cumulative_overflow.tolist(),
        "cumulative_mass_balance_residual_mol": cumulative_residual.tolist(),
        "cumulative_mass_balance_relative": float(np.max(np.abs(cumulative_residual)) / cumulative_denom),
        "cumulative_product_external_y": (cumulative_product / max(float(cumulative_product.sum()), 1e-12)).tolist(),
        "cumulative_h2_recovery_external_proxy": float(cumulative_product[0] / max(cumulative_feed[0], 1e-12)),
        "components": list(COMPONENTS),
        "model_status": "two_bed_spatial_finite_purge_tank_internal_bridge_external_validation_open",
        "css_history": history,
    }


if __name__ == "__main__":
    print(json.dumps(run_cycle(), indent=2))

