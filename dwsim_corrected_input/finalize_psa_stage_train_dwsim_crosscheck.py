"""Audit, summarize, plot, and hash the DWSIM PSA polishing cross-check."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


PROJECT = Path(__file__).resolve().parents[2]
DWSIM = PROJECT / "07_DWSIM_Aspen_재현"
RESULTS = DWSIM / "results" / os.environ.get("PSA_DWSIM_RESULTS_SUBDIR", "")
INPUT = RESULTS / "psa_stage_train_dwsim_input.csv"
CROSSCHECK = RESULTS / "psa_stage_train_dwsim_crosscheck.csv"
STREAMS = RESULTS / "psa_stage_train_dwsim_streams.csv"
CASES = RESULTS / "psa_stage_train_cases"
OUT = RESULTS / "psa_stage_train_dwsim_audit"
ODE_AUDIT = (
    PROJECT
    / "10_TEA_LCA_Python"
    / "psa_qae"
    / "results"
    / os.environ.get("PSA_DWSIM_ODE_DIR", "independent_ode_membrane_audit")
    / "PSA_INDEPENDENT_ODE_MEMBRANE_AUDIT.json"
)
ODE_MANIFEST = ODE_AUDIT.with_name("MANIFEST_SHA256.json")
MW_H2_KG_MOL = 2.01588e-3


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def relative(path: Path) -> str:
    return str(path.resolve().relative_to(PROJECT.resolve()))


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    inp = pd.read_csv(INPUT)
    result = pd.read_csv(CROSSCHECK)
    merged = result.merge(
        inp[["case_id", "python_product_H2_mol_s"]], on="case_id", validate="one_to_one"
    )
    merged["dwsim_compression_kWh_kg_H2"] = (
        merged["total_adiabatic_compression_power_W"]
        / (merged["python_product_H2_mol_s"] * MW_H2_KG_MOL)
        / 3.6e6
    )
    merged["python_isothermal_compression_kWh_kg_H2"] = (
        merged["python_isothermal_compression_power_W"]
        / (merged["python_product_H2_mol_s"] * MW_H2_KG_MOL)
        / 3.6e6
    )
    merged.to_csv(OUT / "Table_dwsim_crosscheck_augmented.csv", index=False)

    if len(merged) != 16 or not (merged["calculation_errors"] == 0).all():
        raise AssertionError("DWSIM did not solve all 16 predeclared cases")
    if merged["stage1_balance_max_abs_mol_s"].max() > 1.0e-12:
        raise AssertionError("stage-1 DWSIM component balance failed")
    if merged["stage2_balance_max_abs_mol_s"].max() > 1.0e-12:
        raise AssertionError("stage-2 DWSIM component balance failed")
    if merged["product_reference_max_abs_mol_s"].max() > 1.0e-12:
        raise AssertionError("DWSIM product stream does not reproduce the supplied membrane split")

    verification = {
        "schema": "psa-stage-train-dwsim-crosscheck/v1",
        "status": "passed_16_of_16_horizon_averaged_cases",
        "software": {
            "dwsim_version": "8.7.1.0",
            "property_package": "Peng-Robinson (PR)",
        },
        "process_architecture": {
            "raw_psa_pressure_bar": 8.0,
            "polymer_feed_pressure_bar": 20.0,
            "polymer_permeate_pressure_bar": 1.0,
            "pd_feed_pressure_bar": 20.0,
            "pd_permeate_pressure_bar": 1.0,
            "polymer_area_m2": 0.18919607212953285,
            "pd_area_m2": float(inp["pd_area_m2"].iloc[0]),
            "pd_permeance_retention": float(inp["pd_permeance_retention"].iloc[0]),
            "membrane_integration_method": str(inp["membrane_integration_method"].iloc[0]),
            "first_compression": "one adiabatic stage, 8 to 20 bar, 72% efficiency, cooled to 298.15 K",
            "interstage_compression": "three equal-pressure-ratio adiabatic stages, 1 to 20 bar, 72% efficiency each, intercooling to 298.15 K",
            "membrane_representation": "DWSIM Component Separators receive horizon-averaged component split fractions from the packet-resolved Python membrane model",
        },
        "checks": {
            "case_count": int(len(merged)),
            "calculation_error_count": int(merged["calculation_errors"].sum()),
            "maximum_component_balance_abs_mol_s": float(
                max(
                    merged["stage1_balance_max_abs_mol_s"].max(),
                    merged["stage2_balance_max_abs_mol_s"].max(),
                )
            ),
            "maximum_product_reference_difference_mol_s": float(
                merged["product_reference_max_abs_mol_s"].max()
            ),
            "saved_reopenable_case_count": len(list(CASES.glob("*.dwxmz"))),
        },
        "energy_and_temperature": {
            "adiabatic_compression_power_W_range": [
                float(merged["total_adiabatic_compression_power_W"].min()),
                float(merged["total_adiabatic_compression_power_W"].max()),
            ],
            "python_isothermal_lower_bound_power_W_range": [
                float(merged["python_isothermal_compression_power_W"].min()),
                float(merged["python_isothermal_compression_power_W"].max()),
            ],
            "adiabatic_to_isothermal_power_ratio_range": [
                float(merged["power_ratio_adiabatic_to_isothermal"].min()),
                float(merged["power_ratio_adiabatic_to_isothermal"].max()),
            ],
            "dwsim_specific_compression_kWh_kg_H2_range": [
                float(merged["dwsim_compression_kWh_kg_H2"].min()),
                float(merged["dwsim_compression_kWh_kg_H2"].max()),
            ],
            "total_cooling_duty_W_range": [
                float(merged["total_cooling_duty_W"].min()),
                float(merged["total_cooling_duty_W"].max()),
            ],
            "maximum_first_compressor_discharge_K": float(
                merged["c1_hot_temperature_K"].max()
            ),
            "maximum_interstage_compressor_discharge_K": float(
                merged["c2_max_hot_temperature_K"].max()
            ),
        },
        "claim_boundary": {
            "supported": (
                "The specified two-stage membrane train is thermodynamically and materially consistent in DWSIM for the 16 horizon-averaged cases; "
                "three-stage intercooled recompression limits the modeled discharge temperature and requires about 15.3% more shaft power than the isothermal lower bound."
            ),
            "not_supported": (
                "This check does not independently reproduce membrane transport, cyclic surge/receiver dynamics, compressor maps, pressure drop, or a vendor module. "
                "The component split fractions are supplied by the Python membrane model."
            ),
        },
    }
    (OUT / "PSA_STAGE_TRAIN_DWSIM_CROSSCHECK.json").write_text(
        json.dumps(verification, indent=2), encoding="utf-8"
    )

    x = np.arange(len(merged))
    colors = np.where(merged["validation_kind"].eq("uncertainty_corner"), "#3366cc", "#e67e22")
    fig, axes = plt.subplots(2, 2, figsize=(12.5, 8.5), constrained_layout=True)
    ax = axes[0, 0]
    lo = min(merged["python_isothermal_compression_power_W"].min(), merged["total_adiabatic_compression_power_W"].min()) - 1
    hi = max(merged["python_isothermal_compression_power_W"].max(), merged["total_adiabatic_compression_power_W"].max()) + 1
    ax.plot([lo, hi], [lo, hi], "--", color="0.45", label="equal power")
    ax.scatter(
        merged["python_isothermal_compression_power_W"],
        merged["total_adiabatic_compression_power_W"],
        c=colors,
        edgecolor="white",
        s=58,
    )
    ax.set(xlabel="Python isothermal lower bound (W)", ylabel="DWSIM adiabatic power (W)", title="a  Compression power cross-check")
    ax.set_xlim(lo, hi)
    ax.set_ylim(lo, hi)
    ax.grid(alpha=0.25)

    ax = axes[0, 1]
    ax.plot(x, merged["dwsim_compression_kWh_kg_H2"], "o-", label="DWSIM, 3-stage intercooled")
    ax.plot(x, merged["python_isothermal_compression_kWh_kg_H2"], "s--", label="isothermal lower bound")
    ax.set(xlabel="Predeclared case index", ylabel="Compression energy (kWh kg$^{-1}$ H$_2$)", title="b  Specific compression energy")
    ax.grid(alpha=0.25)
    ax.legend(frameon=False, fontsize=8)

    ax = axes[1, 0]
    ax.plot(x, merged["c1_hot_temperature_K"], "o-", label="8→20 bar compressor")
    ax.plot(x, merged["c2a_hot_temperature_K"], "^-", label="1→2.71 bar")
    ax.plot(x, merged["c2b_hot_temperature_K"], "v-", label="2.71→7.37 bar")
    ax.plot(x, merged["c2c_hot_temperature_K"], "d-", label="7.37→20 bar")
    ax.set(xlabel="Predeclared case index", ylabel="Discharge temperature (K)", title="c  Compressor discharge temperatures")
    ax.grid(alpha=0.25)
    ax.legend(frameon=False, fontsize=7, ncol=2)

    ax = axes[1, 1]
    closure = np.maximum.reduce(
        [
            merged["stage1_balance_max_abs_mol_s"].to_numpy(),
            merged["stage2_balance_max_abs_mol_s"].to_numpy(),
            merged["product_reference_max_abs_mol_s"].to_numpy(),
        ]
    )
    ax.semilogy(x, np.maximum(closure, 1.0e-22), "o", color="#4c956c")
    ax.axhline(1.0e-12, ls="--", color="#c0392b", label="audit tolerance")
    ax.set(xlabel="Predeclared case index", ylabel="Maximum closure error (mol s$^{-1}$)", title="d  Material and stream closure")
    ax.grid(alpha=0.25, which="both")
    ax.legend(frameon=False, fontsize=8)

    fig.suptitle("DWSIM cross-check of the PSA membrane polishing train", fontsize=14)
    for suffix in ("png", "pdf", "svg"):
        fig.savefig(OUT / f"Fig_psa_stage_train_dwsim_crosscheck.{suffix}", dpi=300)
    plt.close(fig)

    e = verification["energy_and_temperature"]
    checks = verification["checks"]
    md = f"""# DWSIM cross-check of the PSA membrane polishing train

## Result

All **16/16** predeclared uncertainty and hold-out cases solved in DWSIM 8.7.1 with the Peng–Robinson property package. The largest component material-balance residual was **{checks['maximum_component_balance_abs_mol_s']:.3e} mol/s**, and the largest difference between the DWSIM product stream and the supplied packet-model split was **{checks['maximum_product_reference_difference_mol_s']:.3e} mol/s**.

The process uses a **0.1892-m² polymer stage**, a **{verification['process_architecture']['pd_area_m2']:.3f}-m² Pd stage at 80% permeance retention**, one 8→20 bar compressor before the polymer stage, and three equal-pressure-ratio, intercooled compressor stages between the 1 bar polymer permeate and the 20 bar Pd feed. The maximum first-stage discharge temperature was **{e['maximum_first_compressor_discharge_K']:.2f} K**; the maximum recompression-stage discharge temperature was **{e['maximum_interstage_compressor_discharge_K']:.2f} K**.

The DWSIM adiabatic shaft-power range was **{e['adiabatic_compression_power_W_range'][0]:.3f}–{e['adiabatic_compression_power_W_range'][1]:.3f} W**, equal to **{e['dwsim_specific_compression_kWh_kg_H2_range'][0]:.3f}–{e['dwsim_specific_compression_kWh_kg_H2_range'][1]:.3f} kWh/kg H2**. This is **{100*(e['adiabatic_to_isothermal_power_ratio_range'][0]-1):.2f}–{100*(e['adiabatic_to_isothermal_power_ratio_range'][1]-1):.2f}%** above the earlier isothermal lower bound. The total intercooling duty was **{e['total_cooling_duty_W_range'][0]:.3f}–{e['total_cooling_duty_W_range'][1]:.3f} W**.

## Meaning

The cross-check confirms that the pressure levels, stream states, compressor duties, cooling duties, and material closure are internally consistent in a general process simulator for the horizon-averaged cases. It also changes the engineering conclusion: 1→20 bar recompression should be represented as a multistage, intercooled system, and the isothermal calculation should be reported only as a lower bound.

## Claim boundary

DWSIM does not independently calculate the polymer or Pd transport laws here. Each Component Separator receives the component split fractions from the packet-resolved Python membrane model. The calculation also does not replace the dynamic surge/receiver model, compressor maps, pressure-drop calculations, or measurements from a real membrane module.

## Reproduction

1. Run `make_psa_stage_train_dwsim_deck.py` to rebuild the 16-case input deck.
2. Run `run_psa_stage_train_dwsim_crosscheck.ps1` with Windows PowerShell 5.1 and the included DWSIM 8.7.1 portable directory.
3. Run `finalize_psa_stage_train_dwsim_crosscheck.py` to audit the outputs and regenerate this report and figure.
"""
    (OUT / "PSA_STAGE_TRAIN_DWSIM_CROSSCHECK.md").write_text(md, encoding="utf-8")

    source_paths = [
        INPUT,
        CROSSCHECK,
        STREAMS,
        DWSIM / "tools" / "make_psa_stage_train_dwsim_deck.py",
        DWSIM / "tools" / "DwsimPsaStageTrainCrosscheck.cs",
        DWSIM / "tools" / "run_psa_stage_train_dwsim_crosscheck.ps1",
        DWSIM / "tools" / "finalize_psa_stage_train_dwsim_crosscheck.py",
        DWSIM / "H2_REF_DWSIM_v871_PRSV2_PSA1565bar_sensitivity.dwxmz",
        ODE_AUDIT,
        ODE_MANIFEST,
    ]
    source_paths.extend(sorted(CASES.glob("*.dwxmz")))
    source_paths.extend(sorted((PROJECT / "10_TEA_LCA_Python" / "psa_qae" / "results" / "stage_resolved_membrane_train" / "states").glob("*_traces.npz")))
    output_paths = [
        OUT / "Table_dwsim_crosscheck_augmented.csv",
        OUT / "PSA_STAGE_TRAIN_DWSIM_CROSSCHECK.json",
        OUT / "PSA_STAGE_TRAIN_DWSIM_CROSSCHECK.md",
        OUT / "Fig_psa_stage_train_dwsim_crosscheck.png",
        OUT / "Fig_psa_stage_train_dwsim_crosscheck.pdf",
        OUT / "Fig_psa_stage_train_dwsim_crosscheck.svg",
    ]
    manifest = {
        "schema": "psa-stage-train-dwsim-crosscheck-manifest/v1",
        "sources": [
            {"path": relative(path), "sha256": sha256(path), "bytes": path.stat().st_size}
            for path in source_paths
        ],
        "outputs": [
            {"path": relative(path), "sha256": sha256(path), "bytes": path.stat().st_size}
            for path in output_paths
        ],
    }
    (OUT / "MANIFEST_SHA256.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(verification, indent=2))


if __name__ == "__main__":
    main()
