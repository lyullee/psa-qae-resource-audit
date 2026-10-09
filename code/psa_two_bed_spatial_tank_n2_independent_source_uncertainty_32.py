"""Uncertainty screen for the five-component N2 spatial tank oracle around an independent published source composition."""

from __future__ import annotations

import csv
import json
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from psa_qae.psa_spatial_network_probe_n2 import SpatialParams
from psa_qae.psa_two_bed_spatial_tank_n2 import run_cycle


BASE_FEED = np.array([0.655, 0.283, 0.041, 0.006, 0.014], dtype=float)
BASE_FEED /= BASE_FEED.sum()
BASE_SOURCE = np.array([0.99999, 0.0, 1e-6, 2e-6, 5e-6], dtype=float)
BASE_SOURCE /= BASE_SOURCE.sum()


def perturbed_source(rng: np.random.Generator) -> tuple[float, ...]:
    h2 = float(np.clip(BASE_SOURCE[0] + rng.uniform(-5e-5, 5e-5), 0.99980, 0.99995))
    ratios = BASE_SOURCE[1:] / BASE_SOURCE[1:].sum()
    ratios = ratios * rng.lognormal(mean=0.0, sigma=0.12, size=4)
    ratios /= ratios.sum()
    return tuple(np.r_[h2, (1.0 - h2) * ratios].tolist())


def main() -> None:
    rng = np.random.default_rng(20261009)
    rows = []
    for i in range(32):
        source_y = perturbed_source(rng)
        cap = float(rng.uniform(0.95, 1.05)); aff = float(rng.uniform(0.95, 1.05)); ldf = float(rng.uniform(0.95, 1.05))
        p_low = float(rng.uniform(0.05, 0.20)); eq_cond = float(rng.uniform(0.08, 0.12)); recycle = float(rng.uniform(0.35, 0.45))
        p = SpatialParams(
            n_cells=4, P_high_bar=15.65, P_low_bar=p_low, phase_duration_s=10.0,
            feed_y_dry=tuple(BASE_FEED.tolist()), purge_y_dry=source_y,
            k_in_mol_s_bar=1.0, k_out_mol_s_bar=1.0, k_internal_mol_s_bar=5.0,
            capacity_factor=cap, affinity_factor=aff, ldf_factor=ldf,
            max_step_points=12, solver_method="BDF",
        )
        try:
            result = run_cycle(n_cycles=100, p=p, equalization_duration_s=2.0,
                               equalization_conductance=eq_cond, recycle_fraction=recycle,
                               tank_capacity_mol=100.0, initial_tank_moles=0.0)
            purity = float(result["product_external_y"][0]); recovery = float(result["h2_recovery_external_proxy"])
            row = {
                "sample": i, "source_h2": source_y[0], "source_co2": source_y[1], "source_ch4": source_y[2], "source_co": source_y[3], "source_n2": source_y[4],
                "capacity_factor": cap, "affinity_factor": aff, "ldf_factor": ldf, "P_low_bar": p_low, "equalization_conductance": eq_cond, "recycle_fraction": recycle,
                "h2_product": purity, "h2_recovery_external_proxy": recovery, "css_residual": result["css_residual_final"],
                "step_mass_balance_relative_max": result["step_mass_balance_relative_max"], "cycle_mass_balance_relative_max": result["cycle_mass_balance_relative_max"],
                "equalization_pair_mass_residual_max_mol": result["equalization_pair_mass_residual_max_mol"], "css_gate_1e-4": result["css_gate_1e-4"],
                "purity_match_band": purity >= 0.9998, "recovery_match_band": recovery >= 0.789,
                "joint_anchor_event": purity >= 0.9998 and recovery >= 0.789, "model_status": result["model_status"],
            }
        except Exception as exc:
            row = {"sample": i, "source_h2": source_y[0], "source_co2": source_y[1], "source_ch4": source_y[2], "source_co": source_y[3], "source_n2": source_y[4],
                   "capacity_factor": cap, "affinity_factor": aff, "ldf_factor": ldf, "P_low_bar": p_low, "equalization_conductance": eq_cond, "recycle_fraction": recycle,
                   "h2_product": np.nan, "h2_recovery_external_proxy": np.nan, "css_residual": np.nan, "step_mass_balance_relative_max": np.nan,
                   "cycle_mass_balance_relative_max": np.nan, "equalization_pair_mass_residual_max_mol": np.nan, "css_gate_1e-4": False,
                   "purity_match_band": False, "recovery_match_band": False, "joint_anchor_event": False, "model_status": f"solver_failure:{type(exc).__name__}:{exc}"}
        rows.append(row)
    path = Path(__file__).with_name("psa_two_bed_spatial_tank_n2_independent_source_uncertainty_32.csv")
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    h2 = np.asarray([float(r["h2_product"]) for r in rows]); rec = np.asarray([float(r["h2_recovery_external_proxy"]) for r in rows])
    summary = {
        "schema": "psa-two-bed-spatial-tank-n2-independent-source-uncertainty-32/v1", "sample_count": len(rows), "successful_count": int(np.isfinite(h2).sum()),
        "h2_product_range": [float(np.nanmin(h2)), float(np.nanmax(h2))], "h2_recovery_external_proxy_range": [float(np.nanmin(rec)), float(np.nanmax(rec))],
        "joint_anchor_event_count": int(sum(bool(r["joint_anchor_event"]) for r in rows)), "joint_anchor_event_probability_hat": float(sum(bool(r["joint_anchor_event"]) for r in rows) / len(rows)),
        "css_pass_count": int(sum(bool(r["css_gate_1e-4"]) for r in rows)), "max_step_mass_balance_relative": float(np.nanmax([float(r["step_mass_balance_relative_max"]) for r in rows])),
        "max_cycle_mass_balance_relative": float(np.nanmax([float(r["cycle_mass_balance_relative_max"]) for r in rows])), "max_equalization_pair_mass_residual_mol": float(np.nanmax([float(r["equalization_pair_mass_residual_max_mol"]) for r in rows])),
        "status": "independent_published_source_uncertainty_32_screen_context_H2O_and_plant_valve_validation_open",
    }
    summary_path = Path(__file__).with_name("psa_two_bed_spatial_tank_n2_independent_source_uncertainty_32_summary.json")
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"wrote {path}"); print(f"wrote {summary_path}"); print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
