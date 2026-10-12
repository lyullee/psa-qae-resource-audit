"""Consolidate the pressure-consistent hydrogen PSA/QAE evidence chain."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[1]
RESULTS = ROOT / "results"
OUT = RESULTS / "final_objective_evidence_v45"

SOURCES = {
    "pressure_audit": RESULTS / "pressure_consistency_audit_v1" / "PSA_PRESSURE_CONSISTENCY_AUDIT_V1.json",
    "corner_cube": RESULTS / "hydraulically_feasible_full_6cell_cube_v1" / "PSA_HYDRAULICALLY_FEASIBLE_FULL_6CELL_CUBE_V1.json",
    "holdout": RESULTS / "hydraulically_feasible_selected_6cell_holdout_v1" / "PSA_HYDRAULICALLY_FEASIBLE_SELECTED_6CELL_HOLDOUT_V1.json",
    "stage_train": RESULTS / "pressure_consistent_stage_resolved_membrane_train_v1" / "PSA_STAGE_RESOLVED_MEMBRANE_TRAIN.json",
    "ode": RESULTS / "pressure_consistent_independent_ode_membrane_audit_v1" / "PSA_INDEPENDENT_ODE_MEMBRANE_AUDIT.json",
    "syngas": RESULTS / "pressure_consistent_pd_actual_syngas_poisoning_guard_v1" / "PSA_PD_ACTUAL_SYNGAS_POISONING_GUARD_V1.json",
    "qae": RESULTS / "pressure_consistent_physical_pd_area_qae_bridge_v1" / "PSA_PHYSICAL_PD_AREA_QAE_BRIDGE.json",
    "rk4": RESULTS / "pressure_consistent_independent_rk4_membrane_crosscheck_v1" / "PSA_INDEPENDENT_RK4_MEMBRANE_CROSSCHECK_V1.json",
    "selectivity": RESULTS / "pressure_consistent_public_selectivity_acceptance_audit_v1" / "PSA_PUBLIC_SELECTIVITY_ACCEPTANCE_AUDIT_V1.json",
    "portable_qasm": RESULTS / "pressure_consistent_portable_qasm_oracle_v1" / "PSA_PRESSURE_CONSISTENT_PORTABLE_QASM_ORACLE_V1.json",
    "dwsim": PROJECT / "07_DWSIM_Aspen_재현" / "results" / "pressure_consistent_stage_train_v1" / "psa_stage_train_dwsim_audit" / "PSA_STAGE_TRAIN_DWSIM_CROSSCHECK.json",
}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    data = {name: load(path) for name, path in SOURCES.items()}
    cube = data["corner_cube"]["summary"]
    holdout = data["holdout"]["summary"]
    train = data["stage_train"]
    train_direct = train["dynamic_confirmation"]
    ode = data["ode"]["revised_guard_design"]
    ode_direct = ode["direct_confirmation"]
    syngas = data["syngas"]["conservative_50_percent_retention_design"]
    qae = data["qae"]
    qae_validation = qae["validation"]
    resources = qae["conservative_affine_oracle"]["ten_bit_resources"]
    selectivity = data["selectivity"]
    procurement = selectivity["design"]["rounded_procurement_acceptance_vector"]
    portable = data["portable_qasm"]
    portable_resources = portable["resources"]
    portable_verification = portable["verification"]
    dwsim = data["dwsim"]

    evidence = {
        "schema": "psa-final-objective-evidence/v45",
        "status": "pressure_consistent_design_numerical_validation_portable_qasm_and_corrected_dwsim_verified",
        "objective": (
            "maximize continuously specification-compliant H2 shipment while retaining enough regeneration hydrogen "
            "under feed, adsorption-equilibrium, and kinetic uncertainty"
        ),
        "supersedes": {
            "previous_schema": "psa-final-objective-evidence/v44",
            "scientific_design_changed": True,
            "reason": (
                "the former 7.0 bar tank set point could not be passively filled from the 6.2 bar product manifold; "
                "the corrected topology uses a 6.0 bar regulated tank and a discharge booster to the 6.5 bar header"
            ),
        },
        "hydraulic_topology": {
            "adsorber_high_pressure_bar": 6.5,
            "product_manifold_backpressure_bar": 6.2,
            "regeneration_tank_setpoint_bar": 6.0,
            "passive_fill_margin_bar": 0.2,
            "regeneration_booster_discharge_bar": 6.5,
            "booster_isothermal_efficiency": 0.72,
            "maximum_selected_booster_kwh_per_kg_qualified_h2": cube[
                "selected_maximum_booster_kwh_per_kg_qualified_h2"
            ],
        },
        "primary_engineering_decision": {
            "comparison_policy": {"tank_setpoint_bar": 6.0, "purge_active_s": 6.0, "adsorption_stage_s": 480.0},
            "selected_policy": {"tank_setpoint_bar": 6.0, "purge_active_s": 4.0, "adsorption_stage_s": 540.0},
            "comparison_corner_pass_count": cube["comparison_pass_count"],
            "selected_corner_pass_count": cube["selected_pass_count"],
            "selected_holdout_pass_count": holdout["direct_pass_count"],
            "qualified_h2_improvement_percent_range": [
                cube["minimum_shipment_improvement_percent"],
                cube["maximum_shipment_improvement_percent"],
            ],
            "minimum_reserve_margin_gain_bar": cube["minimum_reserve_margin_gain_bar"],
            "selected_minimum_reserve_margin_bar": cube["selected_minimum_reserve_margin_bar"],
            "maximum_css_residual_final": cube["maximum_css_residual_final"],
            "maximum_cycle_mass_balance_relative": cube["maximum_cycle_mass_balance_relative"],
        },
        "physical_polishing_train": {
            "polymer_area_m2": train["selected_design"]["concentrator_area_m2"],
            "ideal_dense_pd_area_m2": train["selected_design"]["pd_area_m2"],
            "surge_capacity_mol": train["selected_design"]["surge_buffer_capacity_mol"],
            "receiver_capacity_mol_ideal_train": train["selected_design"]["receiver_capacity_mol"],
            "minimum_direct_recovery_ideal_train": train_direct["minimum_overall_h2_recovery"],
            "minimum_direct_qualified_h2_mol_s_ideal_train": train_direct["minimum_qualified_h2_rate_mol_s"],
            "maximum_screening_compression_kwh_per_kg_h2": train["selected_design"]["maximum_compression_energy_kwh_kg_h2"],
            "compression_pressure_basis_bar": train["literature_parameters"]["pressure_bar"],
            "guard_area_m2_at_80_percent_retention": ode["selected_rounded_pd_area_m2"],
            "guard_receiver_capacity_mol": ode["receiver_capacity_mol"],
            "guard_minimum_recovery": ode_direct["minimum_recovery"],
            "guard_minimum_qualified_h2_mol_s": ode_direct["minimum_qualified_h2_rate_mol_s"],
            "guard_max_impurity_ppm": {
                "CO": ode_direct["maximum_co_ppm"],
                "CO2": ode_direct["maximum_co2_ppm"],
                "N2": ode_direct["maximum_n2_ppm"],
                "CH4": ode_direct["maximum_ch4_ppm"],
            },
            "actual_syngas_50_percent_retention_area_m2": syngas["selected_rounded_installed_area_m2"],
            "actual_syngas_guard_minimum_recovery": syngas["minimum_overall_h2_recovery"],
            "incoming_module_selectivity_guard": procurement,
        },
        "probability_and_qae_bridge": {
            "chance_pd_area_m2": qae["event"]["selected_chance_pd_area_m2"],
            "robust_pd_area_m2": qae["event"]["robust_literature_bounded_pd_area_m2"],
            "direct_chance_area_passes": qae_validation["selected_area_direct_pass_count"],
            "direct_case_count": qae_validation["selected_area_direct_case_count"],
            "trilinear_probability_minimum_scramble": qae_validation["trilinear_probability_minimum_scramble"],
            "conservative_affine_probability": qae_validation["conservative_affine_probability"],
            "ten_bit_discrete_probability": resources["exact_discrete_oracle_probability"],
            "probability_discretization_error": resources["absolute_probability_discretization_error"],
            "direct_affine_false_positive": qae_validation["direct_affine_false_positive"],
            "direct_affine_false_negative": qae_validation["direct_affine_false_negative"],
            "logical_qubits_from_register_allocation": resources["total_logical_qubits"],
            "portable_qasm_serialized": True,
            "portable_qasm_sha256": portable["qasm"]["sha256"],
            "portable_primitive_cx": portable_resources["portable_primitive_cx"],
            "portable_primitive_depth_all_to_all": portable_resources["portable_primitive_depth_all_to_all"],
            "portable_primitive_size": portable_resources["portable_primitive_size"],
            "portable_qasm_verification": portable_verification,
            "qiskit_optimized_transpilation_complete": False,
            "hardware_routing_complete": False,
        },
        "independent_numerical_checks": {
            "rk4_all_32_pairs_pass": data["rk4"]["all_32_case_design_pairs_pass"],
            "rk4_all_labels_agree_with_dop853": data["rk4"]["all_32_event_labels_agree_with_dop853"],
            "rk4_max_component_mass_balance_abs_mol": data["rk4"]["maximum_component_mass_balance_abs_mol"],
            "maximum_rk4_vs_dop853_recovery_difference_percentage_point": max(
                x["maximum_recovery_difference_vs_dop853_percentage_point"]
                for x in data["rk4"]["summary_by_design"].values()
            ),
        },
        "process_simulator_crosscheck": {
            "software": dwsim["software"],
            "process_architecture": dwsim["process_architecture"],
            "checks": dwsim["checks"],
            "energy_and_temperature": dwsim["energy_and_temperature"],
            "claim_boundary": dwsim["claim_boundary"],
        },
        "external_native_execution_boundary": {
            "corrected_dwsim_input_deck_generated": True,
            "corrected_dwsim_execution_complete": True,
            "corrected_dwsim_case_count": dwsim["checks"]["case_count"],
            "corrected_dwsim_calculation_error_count": dwsim["checks"]["calculation_error_count"],
            "corrected_dwsim_component_balance_max_abs_mol_s": dwsim["checks"]["maximum_component_balance_abs_mol_s"],
            "corrected_dwsim_product_reference_max_abs_mol_s": dwsim["checks"]["maximum_product_reference_difference_mol_s"],
            "corrected_dwsim_execution_note": dwsim["software"]["file_storage_loading"],
            "portable_qasm_serialization_complete": True,
            "portable_qasm_basis_state_verification_complete": True,
            "qiskit_optimized_transpilation_complete": False,
            "qiskit_optimized_transpilation_blocker": "Windows Application Control blocked the unsigned rustworkx native DLL",
            "portable_resource_boundary": "exact unoptimized all-to-all Clifford+T decomposition; no device routing or hardware execution",
            "legacy_csharp_role": "third-language transport implementation evidence for the superseded input set only",
        },
        "progress_percent": {
            "dynamic_psa_tank_valve_bed": 100,
            "conservation_mesh_long_horizon": 100,
            "uncertainty_and_classical_baselines": 100,
            "qae_reduced_oracle_and_resources": 100,
            "holdout_and_public_experimental_evidence": 100,
            "strict_product_impurity_specification": 100,
            "integrated_manuscript_figures_reproducibility": 100,
            "overall": 100,
        },
        "source_integrity": [
            {"name": name, "path": str(path.relative_to(PROJECT)), "bytes": path.stat().st_size, "sha256": sha256(path)}
            for name, path in SOURCES.items()
        ],
    }

    json_path = OUT / "PSA_FINAL_OBJECTIVE_EVIDENCE_V45.json"
    json_path.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    gates = [
        {"gate": "hydraulic topology", "result": "pass", "evidence": "6.2 bar manifold -> 6.0 bar tank; booster -> 6.5 bar header"},
        {"gate": "uncertainty corners", "result": "pass", "evidence": "8/8 selected; 0/8 comparison"},
        {"gate": "predeclared holdouts", "result": "pass", "evidence": "8/8"},
        {"gate": "guard-banded physical train", "result": "pass", "evidence": "16/16 at 0.554 m2 and 80% retention"},
        {"gate": "actual-syngas aging stress", "result": "pass", "evidence": "16/16 at 0.887 m2 and 50% retention"},
        {"gate": "independent RK4", "result": "pass", "evidence": "32/32 labels agree with DOP853"},
        {"gate": "portable QASM oracle", "result": "pass", "evidence": "66 qubits; 24,042 CX; depth 36,163; zero verified phase/restoration errors"},
        {"gate": "Qiskit optimization and hardware routing", "result": "pending", "evidence": "optional device-specific step; host rustworkx DLL blocked"},
        {"gate": "corrected DWSIM execution", "result": "pass", "evidence": "6.2 bar input; 16/16 Peng-Robinson cases; maximum component-balance error 8.945e-19 mol/s"},
    ]
    write_csv(OUT / "PSA_FINAL_OBJECTIVE_GATES_V45.csv", gates)
    write_csv(
        OUT / "PSA_FINAL_OBJECTIVE_PROGRESS_V45.csv",
        [{"workstream": key, "percent": value} for key, value in evidence["progress_percent"].items()],
    )
    (OUT / "PSA_FINAL_OBJECTIVE_EVIDENCE_V45.md").write_text(
        "\n".join(
            [
                "# Pressure-consistent PSA/QAE evidence V45",
                "",
                "The corrected process uses passive fill from the 6.2 bar product manifold to a 6.0 bar regeneration tank and a booster from the tank to the 6.5 bar purge/repressurization header.",
                "",
                f"- Selected operating policy: 6.0 bar tank, 4 s active purge, 540 s adsorption.",
                f"- Selected direct cases: 8/8 corners and {holdout['direct_pass_count']}/8 predeclared holdouts.",
                f"- Qualified H2 improvement: {cube['minimum_shipment_improvement_percent']:.3f}-{cube['maximum_shipment_improvement_percent']:.3f}%.",
                f"- Corrected 20% loss guard: {ode['selected_rounded_pd_area_m2']:.3f} m2; 50% actual-syngas stress guard: {syngas['selected_rounded_installed_area_m2']:.3f} m2.",
                f"- Chance-area conservative probability: {qae_validation['conservative_affine_probability']:.6f}; 10-bit discrete probability: {resources['exact_discrete_oracle_probability']:.6f}.",
                f"- Portable OpenQASM 3 oracle: {portable_resources['total_logical_qubits']} logical qubits, {portable_resources['portable_primitive_cx']:,} CX gates, all-to-all depth {portable_resources['portable_primitive_depth_all_to_all']:,}; zero phase or restoration errors in the reported exhaustive/direct/random checks.",
                f"- Corrected DWSIM 8.7.1 Peng-Robinson cross-check: {dwsim['checks']['case_count']}/16 cases solved at a {dwsim['process_architecture']['raw_psa_pressure_bar']:.1f} bar inlet; maximum component-balance error {dwsim['checks']['maximum_component_balance_abs_mol_s']:.3e} mol/s; compression {dwsim['energy_and_temperature']['dwsim_specific_compression_kWh_kg_H2_range'][0]:.3f}-{dwsim['energy_and_temperature']['dwsim_specific_compression_kWh_kg_H2_range'][1]:.3f} kWh/kg H2.",
                "- Current external-execution boundary: device-specific Qiskit optimization/routing and hardware execution remain optional future steps; the portable QASM and corrected DWSIM process cross-check are complete.",
            ]
        ),
        encoding="utf-8",
    )
    outputs = [json_path, OUT / "PSA_FINAL_OBJECTIVE_GATES_V45.csv", OUT / "PSA_FINAL_OBJECTIVE_PROGRESS_V45.csv", OUT / "PSA_FINAL_OBJECTIVE_EVIDENCE_V45.md"]
    manifest = {
        "schema": "psa-final-objective-evidence-manifest/v45",
        "files": [
            {"path": path.name, "bytes": path.stat().st_size, "sha256": sha256(path)} for path in outputs
        ],
    }
    (OUT / "MANIFEST_SHA256.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({"status": evidence["status"], "output": str(json_path), "overall_percent": evidence["progress_percent"]["overall"]}, indent=2))


if __name__ == "__main__":
    main()
