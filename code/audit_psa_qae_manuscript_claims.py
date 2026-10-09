"""Audit the current PSA--QAE manuscript evidence map.

This is a targeted consistency audit, not a scientific peer review and not a
new PSA simulation. It checks that the manuscript-facing Figure 1 sources,
the direct reduced-PSA convergence numbers, the 128-point MLAE stress test,
and the policy-bridge validation artifact agree with one another.
"""

from __future__ import annotations

import json
from pathlib import Path


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _check(checks: list[dict], name: str, condition: bool, detail: str) -> None:
    checks.append({"name": name, "pass": bool(condition), "detail": detail})


def main() -> None:
    here = Path(__file__).resolve().parent
    results = here.parent / "results" / "pycharm_publication_enhancement"
    manuscript_path = results / "PSA_QAE_SCI_MANUSCRIPT_DRAFT_TWOTIER.md"
    figure_script_path = here / "make_two_tier_figure.py"
    convergence_path = here / "psa_qae_policy_physical_mc_qmc_convergence.json"
    mlae_path = results / "QAE_PHYSICAL_POLICY_128_MLAE_NOISE.json"
    tuwien_qpe_path = results / "QAE_TUWIEN_H2_STATEVECTOR_QPE.json"
    tuwien_mlae_path = results / "QAE_TUWIEN_H2_MLAE_NOISE.json"
    tuwien_uncertainty_path = results / "QAE_TUWIEN_H2_UNCERTAINTY_STATEVECTOR_QPE.json"
    tuwien_resource_path = results / "QAE_TUWIEN_H2_RESOURCE_BOUNDARY.json"
    tuwien_structured_loader_path = results / "QAE_TUWIEN_H2_STRUCTURED_LOADER_BOUNDARY.json"
    hybrid_policy_selection_path = results / "QAE_HYBRID_POLICY_SELECTION_PHYSICAL_16X3.json"
    surrogate_continuous_qpe_path = results / "QAE_INDEPENDENT_SOURCE_SURROGATE_CONTINUOUS_QPE.json"
    quadratic_holdout_path = here / "psa_independent_source_quadratic_surrogate_holdout_32_summary.json"
    continuous_policy_selection_path = results / "PSA_QAE_CONTINUOUS_POLICY_SELECTION.json"
    policy_sample_size_path = results / "PSA_QAE_POLICY_SAMPLE_SIZE_DESIGN.json"
    cvar_loss_bridge_path = here / "psa_qae_cvar_loss_bridge.json"
    direct_tail_stability_path = here / "psa_qae_direct_physical_tail_stability.json"
    tail_loss_oracle_path = results / "PSA_QAE_DIRECT_PHYSICAL_TAIL_LOSS_ORACLE.json"
    tail_amplitude_oracle_path = results / "PSA_QAE_DIRECT_PHYSICAL_TAIL_AMPLITUDE_ORACLE.json"
    tail_amplitude_mlae_path = results / "QAE_DIRECT_PHYSICAL_TAIL_AMPLITUDE_MLAE_NOISE.json"
    tail_end_to_end_path = results / "QAE_DIRECT_PHYSICAL_TAIL_END_TO_END_BOUNDARY.json"
    tail_loader_crossover_path = results / "QAE_TAIL_LOADER_RESOURCE_CROSSOVER.json"
    process_parameter_prior_path = results / "QAE_PROCESS_PARAMETER_CONTINUOUS_PRIOR.json"
    process_parameter_resource_path = results / "QAE_PROCESS_PARAMETER_RESOURCE_BOUNDARY.json"
    process_prior_weight_path = results / "QAE_PROCESS_PARAMETER_PRIOR_WEIGHT_SENSITIVITY.json"
    discrepancy_boundary_path = results / "QAE_SURROGATE_MODEL_DISCREPANCY_BOUNDARY.json"
    rare_tail_boundary_path = results / "QAE_SURROGATE_RARE_TAIL_BOUNDARY.json"
    direct_physical_rare_tail_boundary_path = results / "QAE_DIRECT_PHYSICAL_RARE_TAIL_BOUNDARY.json"
    direct_physical_rare_tail_replicates_path = results / "QAE_DIRECT_PHYSICAL_RARE_TAIL_REPLICATES_N32.json"
    direct_physical_rare_tail_mlae_path = results / "QAE_DIRECT_PHYSICAL_RARE_TAIL_MLAE_NOISE.json"
    cross_oracle_model_form_path = results / "QAE_CROSS_ORACLE_RECOVERY_MODEL_FORM_BOUNDARY.json"
    paired_oracle_model_form_path = results / "QAE_PAIRED_ORACLE_RECOVERY_BOUNDARY_K8.json"
    paired_oracle_model_form_k16_path = results / "QAE_PAIRED_ORACLE_RECOVERY_BOUNDARY_K16.json"
    paired_oracle_model_form_k32_path = results / "QAE_PAIRED_ORACLE_RECOVERY_BOUNDARY_K32.json"
    paired_oracle_k_progress_path = results / "QAE_PAIRED_ORACLE_K_PROGRESS_SUMMARY.json"
    literature_gap_path = results / "PSA_QAE_LITERATURE_GAP_2026.md"
    references_path = results / "PSA_QAE_SCI_REFERENCES.bib"
    end_to_end_resource_path = results / "QAE_END_TO_END_RESOURCE_SUMMARY.json"
    strict_css_horizon_path = results / "QAE_STRICT_CSS_HORIZON_SCREEN.json"
    strict_css_mesh_path = results / "QAE_STRICT_CSS_MESH_SCREEN.json"
    submission_gate_path = results / "PSA_QAE_SCI_SUBMISSION_GATE.json"
    high_n_extension_path = results / "PSA_QAE_POLICY_PHYSICAL_HIGH_N_EXTENSION.json"
    n128_replicate_extension_path = results / "PSA_QAE_POLICY_PHYSICAL_128_REPLICATE_EXTENSION.json"
    seed_panel_path = results / "PSA_QAE_DIRECT_PHYSICAL_SEED_PANEL.json"
    structured_loader_path = results / "PSA_QAE_STRUCTURED_EMPIRICAL_LOADER.json"
    reversible_cycle_path = results / "PSA_QAE_REVERSIBLE_FIXED_POINT_CYCLE_CONTROL.json"
    primary_finite_gate_path = results / "PSA_QAE_CCE_PRIMARY_FINITE_ORACLE_GATE_RESOURCES.json"
    primary_finite_ibm_preflight_path = results / "PSA_QAE_CCE_PRIMARY_FINITE_ORACLE_IBM_PREFLIGHT_ibm_marrakesh.json"
    primary_linear_oracle_path = results / "PSA_QAE_CCE_PRIMARY_LINEAR_SURROGATE_ORACLE.json"
    primary_copula_loader_path = results / "PSA_QAE_CCE_PRIMARY_COPULA_STATE_LOADER.json"
    primary_threshold_activity_path = results / "PSA_QAE_CCE_PRIMARY_THRESHOLD_ACTIVITY.json"
    cce_policy_decision_margin_path = results / "PSA_QAE_CCE_POLICY_DECISION_MARGIN.json"
    cce_gate_manifest_path = results / "PSA_QAE_CCE_GATE_COMPILATION_MANIFEST.json"
    cce_external_policy_path = results / "PSA_QAE_CCE_EXTERNAL_LIGHT_PRODUCT_POLICY_VALIDATION.json"
    cce_external_refinement_path = results / "PSA_QAE_CCE_EXTERNAL_POLICY_NUMERICAL_REFINEMENT.json"
    cce_pyapep_path = results / "PSA_QAE_CCE_INDEPENDENT_PYAPEP_H2_RECYCLE_VALIDATION.json"
    cce_h2_resolution_path = results / "PSA_QAE_CCE_INDEPENDENT_H2_POLICY_RESOLUTION_AUDIT.json"
    cce_topsail_yang_path = results / "PSA_QAE_CCE_TOPSAIL_YANG_H2_PUBLIC_MODEL_AUDIT.json"
    cce_prospective_design_path = results / "PSA_QAE_CCE_PROSPECTIVE_POLICY_DESIGN_AUDIT.json"
    cce_phase_map_path = results / "PSA_QAE_CCE_CALIBRATED_ONE_CYCLE_PHASE_MAP.json"
    cce_phase_map_fixed_point_path = results / "PSA_QAE_CCE_PHASE_MAP_FIXED_POINT_SCREEN.json"
    cce_phase_map_compile_path = results / "PSA_QAE_CCE_PHASE_MAP_AFFINE_BLOCK_COMPILE.json"
    cce_small_e2e_path = results / "PSA_QAE_CCE_SMALL_END_TO_END_ORACLE.json"
    cce_primary_phase_ledger_path = results / "PSA_QAE_CCE_PRIMARY_PHASE_LEDGER.json"
    cce_primary_physical_css_path = results / "PSA_QAE_CCE_PRIMARY_PHYSICAL_CSS_HORIZON_AUDIT.json"
    cce_primary_qstar_microkernel_path = results / "PSA_QAE_CCE_PRIMARY_QSTAR_REVERSIBLE_MICROKERNEL.json"
    cce_primary_qstar_ldf_microstep_path = results / "PSA_QAE_CCE_PRIMARY_QSTAR_LDF_REVERSIBLE_MICROSTEP.json"
    cce_primary_all_component_ldf_path = results / "PSA_QAE_CCE_PRIMARY_ALL_COMPONENT_LDF_MICROSTEPS.json"
    cce_primary_product_boundary_path = results / "PSA_QAE_CCE_PRIMARY_PRODUCT_BOUNDARY_MICROSTEPS.json"
    cce_primary_product_boundary_balance_path = results / "PSA_QAE_CCE_PRIMARY_PRODUCT_BOUNDARY_BALANCE_COMPOSITION.json"
    cce_primary_product_ldf_valve_balance_path = results / "PSA_QAE_CCE_PRIMARY_PRODUCT_LDF_VALVE_BALANCE_COMPOSITION.json"
    cce_primary_normalized_product_ldf_valve_balance_path = results / "PSA_QAE_CCE_PRIMARY_NORMALIZED_PRODUCT_LDF_VALVE_BALANCE.json"
    cce_primary_coherent_run_schedule_tank_path = results / "PSA_QAE_CCE_COHERENT_RUN_SCHEDULE_TANK_INTERFACE.json"
    cce_primary_coherent_run_factor_ldf_path = results / "PSA_QAE_CCE_COHERENT_RUN_FACTOR_LDF_INTERFACE.json"
    cce_primary_coherent_coefficient_ldf_balance_path = results / "PSA_QAE_CCE_COHERENT_COEFFICIENT_LDF_BALANCE_INTERFACE.json"
    cce_primary_coherent_dynamic_langmuir_ldf_balance_path = results / "PSA_QAE_CCE_COHERENT_DYNAMIC_LANGMUIR_LDF_BALANCE_INTERFACE.json"
    cce_primary_coherent_normalized_dynamic_transport_ldf_balance_path = results / "PSA_QAE_CCE_COHERENT_NORMALIZED_DYNAMIC_TRANSPORT_LDF_BALANCE.json"
    cce_primary_offledger_tank_saturation_path = results / "PSA_QAE_CCE_OFFLEDGER_TANK_SATURATION_INTERFACE.json"
    cce_primary_offledger_tank_proportional_path = results / "PSA_QAE_CCE_OFFLEDGER_TANK_PROPORTIONAL_INTERFACE.json"
    cce_primary_physical_unsaturated_tank_path = results / "PSA_QAE_CCE_PHYSICAL_UNSATURATED_TANK_TRAJECTORY.json"
    cce_primary_internal_transport_path = results / "PSA_QAE_CCE_PRIMARY_INTERNAL_TRANSPORT_MICROSTEPS.json"
    cce_primary_internal_face_balance_path = results / "PSA_QAE_CCE_PRIMARY_INTERNAL_FACE_BALANCE_COMPOSITION.json"
    cce_primary_normalized_internal_face_balance_path = results / "PSA_QAE_CCE_PRIMARY_COMPOSITION_NORMALIZED_INTERNAL_FACE_BALANCE.json"
    cce_primary_cell_balance_path = results / "PSA_QAE_CCE_PRIMARY_CELL_BALANCE_MICROSTEPS.json"
    cce_primary_loading_sign_balance_path = results / "PSA_QAE_CCE_PRIMARY_LOADING_SIGN_BALANCE_INTERFACE.json"
    cce_primary_ldf_sign_balance_path = results / "PSA_QAE_CCE_PRIMARY_LDF_SIGN_BALANCE_COMPOSITION.json"
    cce_primary_joint_normalized_transport_ldf_balance_path = results / "PSA_QAE_CCE_PRIMARY_JOINT_NORMALIZED_TRANSPORT_LDF_BALANCE.json"
    cce_primary_event_bridge_path = results / "PSA_QAE_CCE_PRIMARY_PHASE_EVENT_BRIDGE.json"
    cce_primary_event_fixed_point_path = results / "PSA_QAE_CCE_PRIMARY_PHASE_EVENT_FIXED_POINT_SCREEN.json"
    cce_primary_event_compile_path = results / "PSA_QAE_CCE_PRIMARY_PHASE_EVENT_BLOCK_COMPILE.json"
    cce_primary_final_event_path = results / "PSA_QAE_CCE_PRIMARY_FINAL_EVENT_ARITHMETIC.json"
    cce_primary_policy_stream_event_path = results / "PSA_QAE_CCE_PRIMARY_POLICY_STREAM_EVENT_ORACLE.json"
    cce_primary_free_running_path = results / "PSA_QAE_CCE_PRIMARY_PHASE_EVENT_FREE_RUNNING.json"
    cce_primary_repeated_path = results / "PSA_QAE_CCE_PRIMARY_PHASE_EVENT_REPEATED_CYCLE_SCREEN.json"
    cce_css_initializer_path = results / "PSA_QAE_CCE_PRIMARY_CSS_INITIALIZER_EVENT_BRIDGE.json"
    cce_css_repeated_path = results / "PSA_QAE_CCE_PRIMARY_CSS_INITIALIZER_REPEATED_CYCLE_SCREEN.json"
    cce_css_stability_path = results / "PSA_QAE_CCE_PRIMARY_CSS_INITIALIZER_SPECTRAL_STABILITY_SCREEN.json"
    cce_css_fixed_path = results / "PSA_QAE_CCE_PRIMARY_CSS_INITIALIZER_FIXED_POINT_SCREEN.json"
    cce_css_compile_path = results / "PSA_QAE_CCE_PRIMARY_CSS_INITIALIZER_BLOCK_COMPILE.json"
    cce_resource_table_path = results / "PSA_QAE_CCE_RESOURCE_TABLE3.json"
    cce_table1_path = results / "PSA_QAE_CCE_TABLE1_FROZEN_PROTOCOL.json"
    cce_table2_path = results / "PSA_QAE_CCE_TABLE2_MATCHED_ESTIMATORS.json"
    cce_table4_path = results / "PSA_QAE_CCE_TABLE4_EVIDENCE_HIERARCHY.json"
    cce_validity_figure_path = results / "PSA_QAE_CCE_VALIDITY_BOUNDARY_FIGURE.json"
    cce_editorial_path = results / "PSA_QAE_CCE_EDITORIAL_PACKAGE.json"
    cce_editorial_md_path = results / "PSA_QAE_CCE_EDITORIAL_PACKAGE.md"
    cce_cover_path = results / "PSA_QAE_CCE_COVER_LETTER_DRAFT.md"
    cce_highlights_path = results / "PSA_QAE_CCE_HIGHLIGHTS.txt"
    cce_checklist_path = results / "PSA_QAE_CCE_SUBMISSION_CHECKLIST.md"
    cce_graphical_abstract_png_path = results / "PSA_QAE_CCE_GRAPHICAL_ABSTRACT.png"
    cce_graphical_abstract_pdf_path = results / "PSA_QAE_CCE_GRAPHICAL_ABSTRACT.pdf"
    phase_ledger_path = results / "PSA_QAE_DIRECT_PHYSICAL_PHASE_LEDGER.json"
    compiled_physical_oracle_path = results / "PSA_QAE_DIRECT_PHYSICAL_COMPILED_ORACLE.json"
    strict_css_16cell_path = results / "QAE_STRICT_CSS_16CELL_SCREEN.json"
    industrial_8bed_bridge_path = results / "PSA_QAE_INDUSTRIAL_8BED_BENCHMARK_BRIDGE.json"
    industrial_target_boundary_path = results / "PSA_QAE_INDUSTRIAL_TARGET_EVENT_BOUNDARY.json"
    reduced_calibration_localization_path = results / "PSA_QAE_REDUCED_CALIBRATION_LOCALIZATION.json"
    hybrid_policy_bootstrap_path = results / "PSA_QAE_HYBRID_POLICY_SELECTION_BOOTSTRAP.json"
    hybrid_policy_threshold_path = results / "PSA_QAE_HYBRID_POLICY_THRESHOLD_SENSITIVITY.json"
    hybrid_policy_direct_noise_path = results / "PSA_QAE_HYBRID_POLICY_DIRECT_NOISE.json"
    submission_manifest_path = results / "PSA_QAE_SCI_SUBMISSION_MANIFEST.json"
    validation_path = here / "psa_qae_two_tier_policy_bridge_validation.json"
    case_spec_path = results / "psa_qae_case_spec.json"
    submission_packet_path = results / "PSA_QAE_SCI_SUBMISSION_PACKET.md"

    convergence = _load(convergence_path)
    mlae = _load(mlae_path)
    tuwien_qpe = _load(tuwien_qpe_path)
    tuwien_mlae = _load(tuwien_mlae_path)
    tuwien_uncertainty = _load(tuwien_uncertainty_path)
    tuwien_resource = _load(tuwien_resource_path)
    tuwien_structured_loader = _load(tuwien_structured_loader_path)
    hybrid_policy_selection = _load(hybrid_policy_selection_path)
    surrogate_continuous_qpe = _load(surrogate_continuous_qpe_path)
    quadratic_holdout = _load(quadratic_holdout_path)
    continuous_policy_selection = _load(continuous_policy_selection_path)
    policy_sample_size = _load(policy_sample_size_path)
    cvar_loss_bridge = _load(cvar_loss_bridge_path)
    direct_tail_stability = _load(direct_tail_stability_path)
    tail_loss_oracle = _load(tail_loss_oracle_path)
    tail_amplitude_oracle = _load(tail_amplitude_oracle_path)
    tail_amplitude_mlae = _load(tail_amplitude_mlae_path)
    tail_end_to_end = _load(tail_end_to_end_path)
    tail_loader_crossover = _load(tail_loader_crossover_path)
    process_parameter_prior = _load(process_parameter_prior_path)
    process_parameter_resource = _load(process_parameter_resource_path)
    process_prior_weight = _load(process_prior_weight_path)
    discrepancy_boundary = _load(discrepancy_boundary_path)
    rare_tail_boundary = _load(rare_tail_boundary_path)
    direct_physical_rare_tail_boundary = _load(direct_physical_rare_tail_boundary_path)
    direct_physical_rare_tail_replicates = _load(direct_physical_rare_tail_replicates_path)
    direct_physical_rare_tail_mlae = _load(direct_physical_rare_tail_mlae_path)
    cross_oracle_model_form = _load(cross_oracle_model_form_path)
    paired_oracle_model_form = _load(paired_oracle_model_form_path)
    paired_oracle_model_form_k16 = _load(paired_oracle_model_form_k16_path)
    paired_oracle_model_form_k32 = _load(paired_oracle_model_form_k32_path)
    paired_oracle_k_progress = _load(paired_oracle_k_progress_path)
    validation = _load(validation_path)
    case_spec = _load(case_spec_path)
    manuscript = manuscript_path.read_text(encoding="utf-8")
    submission_packet = submission_packet_path.read_text(encoding="utf-8")
    literature_gap = literature_gap_path.read_text(encoding="utf-8")
    references = references_path.read_text(encoding="utf-8")
    end_to_end_resource = _load(end_to_end_resource_path)
    strict_css_horizon = _load(strict_css_horizon_path)
    strict_css_mesh = _load(strict_css_mesh_path)
    submission_gate = _load(submission_gate_path)
    high_n_extension = _load(high_n_extension_path)
    n128_replicate_extension = _load(n128_replicate_extension_path)
    seed_panel = _load(seed_panel_path)
    structured_loader = _load(structured_loader_path)
    reversible_cycle = _load(reversible_cycle_path)
    primary_finite_gate = _load(primary_finite_gate_path)
    primary_finite_ibm_preflight = _load(primary_finite_ibm_preflight_path)
    primary_linear_oracle = _load(primary_linear_oracle_path)
    primary_copula_loader = _load(primary_copula_loader_path)
    primary_threshold_activity = _load(primary_threshold_activity_path)
    cce_policy_decision_margin = _load(cce_policy_decision_margin_path)
    cce_gate_manifest = _load(cce_gate_manifest_path)
    cce_external_policy = _load(cce_external_policy_path)
    cce_external_refinement = _load(cce_external_refinement_path)
    cce_pyapep = _load(cce_pyapep_path)
    cce_h2_resolution = _load(cce_h2_resolution_path)
    cce_topsail_yang = _load(cce_topsail_yang_path)
    cce_prospective_design = _load(cce_prospective_design_path)
    cce_phase_map = _load(cce_phase_map_path)
    cce_phase_map_fixed_point = _load(cce_phase_map_fixed_point_path)
    cce_phase_map_compile = _load(cce_phase_map_compile_path)
    cce_small_e2e = _load(cce_small_e2e_path)
    cce_primary_phase_ledger = _load(cce_primary_phase_ledger_path)
    cce_primary_physical_css = _load(cce_primary_physical_css_path)
    cce_primary_qstar_microkernel = _load(cce_primary_qstar_microkernel_path)
    cce_primary_qstar_ldf_microstep = _load(cce_primary_qstar_ldf_microstep_path)
    cce_primary_all_component_ldf = _load(cce_primary_all_component_ldf_path)
    cce_primary_product_boundary = _load(cce_primary_product_boundary_path)
    cce_primary_product_boundary_balance = _load(cce_primary_product_boundary_balance_path)
    cce_primary_product_ldf_valve_balance = _load(cce_primary_product_ldf_valve_balance_path)
    cce_primary_normalized_product_ldf_valve_balance = _load(
        cce_primary_normalized_product_ldf_valve_balance_path
    )
    cce_primary_coherent_run_schedule_tank = _load(
        cce_primary_coherent_run_schedule_tank_path
    )
    cce_primary_coherent_run_factor_ldf = _load(
        cce_primary_coherent_run_factor_ldf_path
    )
    cce_primary_coherent_coefficient_ldf_balance = _load(
        cce_primary_coherent_coefficient_ldf_balance_path
    )
    cce_primary_coherent_dynamic_langmuir_ldf_balance = _load(
        cce_primary_coherent_dynamic_langmuir_ldf_balance_path
    )
    cce_primary_coherent_normalized_dynamic_transport_ldf_balance = _load(
        cce_primary_coherent_normalized_dynamic_transport_ldf_balance_path
    )
    cce_primary_offledger_tank_saturation = _load(
        cce_primary_offledger_tank_saturation_path
    )
    cce_primary_offledger_tank_proportional = _load(
        cce_primary_offledger_tank_proportional_path
    )
    cce_primary_physical_unsaturated_tank = _load(
        cce_primary_physical_unsaturated_tank_path
    )
    cce_primary_internal_transport = _load(cce_primary_internal_transport_path)
    cce_primary_internal_face_balance = _load(cce_primary_internal_face_balance_path)
    cce_primary_normalized_internal_face_balance = _load(cce_primary_normalized_internal_face_balance_path)
    cce_primary_cell_balance = _load(cce_primary_cell_balance_path)
    cce_primary_loading_sign_balance = _load(cce_primary_loading_sign_balance_path)
    cce_primary_ldf_sign_balance = _load(cce_primary_ldf_sign_balance_path)
    cce_primary_joint_normalized_transport_ldf_balance = _load(
        cce_primary_joint_normalized_transport_ldf_balance_path
    )
    cce_primary_event_bridge = _load(cce_primary_event_bridge_path)
    cce_primary_event_fixed_point = _load(cce_primary_event_fixed_point_path)
    cce_primary_event_compile = _load(cce_primary_event_compile_path)
    cce_primary_final_event = _load(cce_primary_final_event_path)
    cce_primary_policy_stream_event = _load(cce_primary_policy_stream_event_path)
    cce_primary_free_running = _load(cce_primary_free_running_path)
    cce_primary_repeated = _load(cce_primary_repeated_path)
    cce_css_initializer = _load(cce_css_initializer_path)
    cce_css_repeated = _load(cce_css_repeated_path)
    cce_css_stability = _load(cce_css_stability_path)
    cce_css_fixed = _load(cce_css_fixed_path)
    cce_css_compile = _load(cce_css_compile_path)
    cce_resource_table = _load(cce_resource_table_path)
    cce_table1 = _load(cce_table1_path)
    cce_table2 = _load(cce_table2_path)
    cce_table4 = _load(cce_table4_path)
    cce_validity_figure = _load(cce_validity_figure_path)
    cce_editorial = _load(cce_editorial_path)
    cce_cover = cce_cover_path.read_text(encoding="utf-8")
    cce_checklist = cce_checklist_path.read_text(encoding="utf-8")
    phase_ledger = _load(phase_ledger_path)
    compiled_physical_oracle = _load(compiled_physical_oracle_path)
    strict_css_16cell = _load(strict_css_16cell_path)
    industrial_8bed_bridge = _load(industrial_8bed_bridge_path)
    industrial_target_boundary = _load(industrial_target_boundary_path)
    reduced_calibration_localization = _load(reduced_calibration_localization_path)
    hybrid_policy_bootstrap = _load(hybrid_policy_bootstrap_path)
    hybrid_policy_threshold = _load(hybrid_policy_threshold_path)
    hybrid_policy_direct_noise = _load(hybrid_policy_direct_noise_path)
    submission_manifest = _load(submission_manifest_path)
    figure_script = figure_script_path.read_text(encoding="utf-8")
    checks: list[dict] = []

    manifest_project = here.parent
    manifest_paths_exist = all(
        (manifest_project / row["path"]).exists()
        for row in submission_manifest.get("files", [])
    )
    _check(
        checks,
        "submission evidence manifest",
        submission_manifest.get("status") == "reviewer_facing_evidence_manifest_hash_locked"
        and int(submission_manifest.get("file_count", 0)) == len(submission_manifest.get("files", []))
        and int(submission_manifest.get("file_count", 0)) >= 20
        and manifest_paths_exist,
        f"files={submission_manifest.get('file_count')}, paths_exist={manifest_paths_exist}",
    )
    _check(
        checks,
        "submission packet claim boundary",
        "Recommended title" in submission_packet
        and "unconditional quantum advantage" in submission_packet
        and "QAE/QMC ratio" in submission_packet
        and "hash-locked evidence manifest" in submission_packet,
        "title, abstract, cover letter, limits, and evidence anchors are present",
    )
    _check(
        checks,
        "CCE editorial package and graphical abstract claim boundary",
        cce_editorial.get("status")
        == "editorial_materials_complete_scientific_submission_gates_open"
        and cce_editorial.get("submission_ready") is False
        and cce_editorial.get("qpu_submission") is False
        and len(cce_editorial.get("highlights", [])) == 5
        and max(cce_editorial.get("highlight_character_counts", [999])) <= 85
        and cce_editorial.get("evidence", {}).get("rqmc_rmse") == 0.002482
        and cce_editorial.get("evidence", {}).get("mlae_rmse") == 0.002892
        and cce_editorial.get("evidence", {}).get("response_oracle_cx_per_call") == 35160
        and cce_editorial.get("evidence", {}).get("primary_phase_event_matches") == 32
        and cce_editorial.get("evidence", {}).get("primary_phase_event_block_logical_qubits") == 272
        and cce_editorial.get("evidence", {}).get("primary_phase_event_block_forward_cx") == 1101233
        and cce_editorial.get("evidence", {}).get("primary_phase_event_block_clean_cx") == 2202466
        and cce_editorial.get("evidence", {}).get("primary_final_event_logical_qubits") == 125
        and cce_editorial.get("evidence", {}).get("primary_final_event_clean_cx") == 182981
        and cce_editorial.get("evidence", {}).get("primary_final_event_labels") == 32
        and cce_editorial.get("evidence", {}).get("policy_stream_event_aggregate_bits") == 19
        and cce_editorial.get("evidence", {}).get("policy_stream_event_candidate_labels") == 96
        and cce_editorial.get("evidence", {}).get("policy_stream_event_ledger_labels") == 32
        and cce_editorial.get("evidence", {}).get("policy_stream_event_logical_qubits") == 510
        and cce_editorial.get("evidence", {}).get("policy_stream_event_clean_cx") == 1286021
        and cce_editorial.get("evidence", {}).get("parameter_only_css_event_matches") == 32
        and cce_editorial.get("evidence", {}).get("parameter_only_css_block_logical_qubits") == 118
        and cce_editorial.get("evidence", {}).get("parameter_only_css_block_forward_cx") == 578702
        and cce_editorial.get("evidence", {}).get("parameter_only_css_block_clean_cx") == 1157404
        and cce_editorial.get("evidence", {}).get("parameter_only_css_50cycle_terminal_matches") == 28
        and cce_editorial.get("evidence", {}).get("parameter_only_css_50cycle_gate_passes") == 2
        and cce_editorial.get("evidence", {}).get("physical_css_joint_horizon") == 68
        and cce_editorial.get("evidence", {}).get("physical_css_fixed_point_bits") == 16
        and cce_editorial.get("evidence", {}).get("physical_css_safe_horizon") == 85
        and cce_editorial.get("evidence", {}).get("physical_single_state_data_qubits") == 1360
        and cce_editorial.get("evidence", {}).get("physical_out_of_place_state_stream_data_qubits") == 2880
        and cce_editorial.get("evidence", {}).get("qstar_microkernel_bits") == 18
        and cce_editorial.get("evidence", {}).get("qstar_microkernel_logical_qubits") == 266
        and cce_editorial.get("evidence", {}).get("qstar_microkernel_forward_cx") == 127112
        and cce_editorial.get("evidence", {}).get("qstar_microkernel_clean_cx") == 254224
        and float(cce_editorial.get("evidence", {}).get("qstar_microkernel_denominator_p95_relative_error", 1.0)) < 1.0e-3
        and float(cce_editorial.get("evidence", {}).get("qstar_microkernel_qstar_p95_relative_error", 1.0)) < 5.0e-2
        and cce_editorial.get("evidence", {}).get("qstar_ldf_address_bits") == 5
        and cce_editorial.get("evidence", {}).get("qstar_ldf_arithmetic_bits") == 24
        and float(cce_editorial.get("evidence", {}).get("qstar_ldf_qstar_p95_relative_error", 1.0)) < 5.0e-2
        and float(cce_editorial.get("evidence", {}).get("qstar_ldf_next_p95_relative_error", 1.0)) < 1.0e-3
        and cce_editorial.get("evidence", {}).get("qstar_ldf_logical_qubits") == 515
        and cce_editorial.get("evidence", {}).get("qstar_ldf_cx") == 1225138
        and cce_editorial.get("evidence", {}).get("qstar_ldf_depth") == 1919788
        and cce_editorial.get("evidence", {}).get("all_component_ldf_logical_qubits") == 675
        and cce_editorial.get("evidence", {}).get("all_component_ldf_additive_cx") == 6547362
        and cce_editorial.get("evidence", {}).get("product_valve_address_bits") == 12
        and cce_editorial.get("evidence", {}).get("product_valve_flow_bits") == 20
        and cce_editorial.get("evidence", {}).get("product_valve_logical_qubits") == 288
        and cce_editorial.get("evidence", {}).get("product_valve_cx") == 800762
        and cce_editorial.get("evidence", {}).get("product_tank_amount_bits") == 24
        and cce_editorial.get("evidence", {}).get("product_tank_fraction_bits") == 14
        and cce_editorial.get("evidence", {}).get("product_tank_logical_qubits") == 677
        and cce_editorial.get("evidence", {}).get("product_tank_additive_cx") == 1043990
        and abs(float(cce_editorial.get("evidence", {}).get("product_tank_minimum_capacity_headroom_mol", 0.0)) - 97.40262911728867) < 1.0e-12
        and cce_editorial.get("evidence", {}).get("product_boundary_balance_logical_qubits") == 842
        and cce_editorial.get("evidence", {}).get("product_boundary_balance_cx") == 2348388
        and cce_editorial.get("evidence", {}).get("product_boundary_balance_depth") == 3285605
        and cce_editorial.get("evidence", {}).get("product_boundary_balance_states") == 6464
        and cce_editorial.get("evidence", {}).get("product_boundary_balance_component_balances") == 32320
        and cce_editorial.get("evidence", {}).get("pressure_reconstruction_logical_qubits") == 152
        and cce_editorial.get("evidence", {}).get("pressure_reconstruction_cx") == 93764
        and cce_editorial.get("evidence", {}).get("internal_face_logical_qubits") == 404
        and cce_editorial.get("evidence", {}).get("internal_face_cx") == 1340390
        and cce_editorial.get("evidence", {}).get("internal_face_balance_logical_qubits") == 1508
        and cce_editorial.get("evidence", {}).get("internal_face_balance_cx") == 8328622
        and cce_editorial.get("evidence", {}).get("internal_face_balance_depth") == 12250291
        and cce_editorial.get("evidence", {}).get("internal_face_balance_states") == 12928
        and cce_editorial.get("evidence", {}).get("internal_face_balance_component_balances") == 64640
        and cce_editorial.get("evidence", {}).get("normalized_internal_face_balance_logical_qubits") == 1651
        and cce_editorial.get("evidence", {}).get("normalized_internal_face_balance_cx") == 14667150
        and cce_editorial.get("evidence", {}).get("normalized_internal_face_balance_depth") == 22143683
        and cce_editorial.get("evidence", {}).get("composition_normalizer_logical_qubits") == 333
        and cce_editorial.get("evidence", {}).get("composition_normalizer_cx") == 1340232
        and cce_editorial.get("evidence", {}).get("composition_normalization_states") == 25856
        and cce_editorial.get("evidence", {}).get("composition_normalization_address_bits") == 8
        and float(cce_editorial.get("evidence", {}).get("composition_normalization_p95_absolute_error_max", 1.0)) < 2.1e-4
        and cce_editorial.get("evidence", {}).get("pressure_face_modular_logical_qubits") == 584
        and cce_editorial.get("evidence", {}).get("pressure_face_modular_additive_cx") == 1527918
        and cce_editorial.get("evidence", {}).get("cell_balance_logical_qubits") == 609
        and cce_editorial.get("evidence", {}).get("cell_balance_additive_cx") == 366802
        and cce_editorial.get("evidence", {}).get("cell_balance_samples") == 64640
        and cce_editorial.get("evidence", {}).get("loading_sign_balance_logical_qubits") == 934
        and cce_editorial.get("evidence", {}).get("loading_sign_balance_additive_cx") == 1411882
        and cce_editorial.get("evidence", {}).get("loading_sign_balance_selected_bits") == [26, 26, 32, 32, 30]
        and cce_editorial.get("evidence", {}).get("loading_sign_balance_structural_pairs") == 64
        and cce_editorial.get("evidence", {}).get("ldf_sign_balance_logical_qubits") == 1317
        and cce_editorial.get("evidence", {}).get("ldf_sign_balance_additive_cx") == 19082852
        and cce_editorial.get("evidence", {}).get("ldf_sign_balance_component_qubit_range") == [861, 929]
        and cce_editorial.get("evidence", {}).get("ldf_sign_balance_component_cx_range") == [3412254, 4991534]
        and cce_editorial.get("evidence", {}).get("joint_transport_ldf_component_qubit_range") == [1944, 2039]
        and cce_editorial.get("evidence", {}).get("joint_transport_ldf_component_cx_range") == [20670468, 35947274]
        and cce_editorial.get("evidence", {}).get("joint_transport_ldf_peak_logical_qubits") == 2039
        and cce_editorial.get("evidence", {}).get("joint_transport_ldf_additive_cx_upper_bound") == 128013726
        and cce_editorial.get("evidence", {}).get("same_control_h2_validation") is False
        and "end-to-end quantum advantage" in cce_editorial.get("claim_boundary", {}).get("unsupported", "")
        and "do not claim quantum advantage" in cce_cover
        and "same physical product-recycle control" in cce_checklist
        and all(
            path.exists()
            for path in [
                cce_editorial_md_path,
                cce_cover_path,
                cce_highlights_path,
                cce_checklist_path,
                cce_graphical_abstract_png_path,
                cce_graphical_abstract_pdf_path,
            ]
        ),
        f"status={cce_editorial.get('status')}, highlights={cce_editorial.get('highlight_character_counts')}, qpu_submission={cce_editorial.get('qpu_submission')}",
    )

    expected_sizes = [16, 32, 64, 128]
    observed_sizes = [int(row["sample_count_per_method"]) for row in convergence["rows"]]
    _check(
        checks,
        "direct convergence sample sizes",
        observed_sizes == expected_sizes,
        f"observed={observed_sizes}",
    )
    _check(
        checks,
        "direct convergence internal gates",
        all(row["all_css_and_mass_balance_pass"] for row in convergence["rows"]),
        f"rows={len(convergence['rows'])}",
    )

    row128 = next(row for row in convergence["rows"] if int(row["sample_count_per_method"]) == 128)
    _check(
        checks,
        "N=128 MC/QMC/IS values",
        abs(float(row128["qmc_probability"]) - 0.65625) < 1e-12
        and abs(float(row128["mc_probability"]) - 0.625) < 1e-12
        and abs(float(row128["is_weighted_probability"]) - 0.7534803450992892) < 1e-12,
        f"qmc={row128['qmc_probability']}, mc={row128['mc_probability']}, is={row128['is_weighted_probability']}",
    )

    stress_rows = [
        row
        for row in mlae["rows"]
        if int(row["shots_per_power"]) == 100 and abs(float(row["bit_flip_probability"]) - 0.05) < 1e-12
    ]
    stress_by_method = {row["method"]: row for row in stress_rows}
    _check(
        checks,
        "128-point 5% MLAE stress values",
        set(stress_by_method) == {"MC", "Sobol_QMC"}
        and abs(float(stress_by_method["MC"]["qae_rmse"]) - 0.0051231289267399584) < 1e-12
        and abs(float(stress_by_method["Sobol_QMC"]["qae_rmse"]) - 0.012343423350108358) < 1e-12,
        f"methods={sorted(stress_by_method)}",
    )

    tuwien_8bit = next(row for row in tuwien_qpe["qpe_rows"] if int(row["phase_bits"]) == 8)
    _check(
        checks,
        "measured H2 table QPE values",
        int(tuwien_qpe["n_states"]) == 13
        and int(tuwien_qpe["good_states"]) == 6
        and abs(float(tuwien_qpe["exact_probability"]) - 0.46153846153846156) < 1e-12
        and abs(float(tuwien_8bit["qae_peak_probability_estimate"]) - 0.4632177182001663) < 1e-12
        and abs(float(tuwien_8bit["qae_expected_rmse_one_qpe_shot"]) - 0.01846792118491932) < 1e-12,
        f"states={tuwien_qpe['n_states']}, good={tuwien_qpe['good_states']}, qpe8={tuwien_8bit['qae_peak_probability_estimate']}",
    )
    tuwien_mlae_rows = {round(float(row["bit_flip_probability"]), 2): row for row in tuwien_mlae["rows"]}
    _check(
        checks,
        "measured H2 table MLAE noise values",
        abs(float(tuwien_mlae["reference_probability"]) - 0.46153846153846156) < 1e-12
        and abs(float(tuwien_mlae_rows[0.0]["qae_rmse"]) - 0.004449186016904416) < 1e-12
        and abs(float(tuwien_mlae_rows[0.05]["qae_rmse"]) - 0.007137908984748696) < 1e-12,
        f"reference={tuwien_mlae['reference_probability']}, rows={len(tuwien_mlae_rows)}",
    )
    tuwien_uncertainty_8bit = next(row for row in tuwien_uncertainty["qpe_rows"] if int(row["phase_bits"]) == 8)
    _check(
        checks,
        "measured H2 recovery uncertainty values",
        abs(float(tuwien_uncertainty["analytic_uncertainty_adjusted_probability"]) - 0.48651701306094) < 1e-12
        and abs(float(tuwien_uncertainty["midpoint_grid_probability"]) - 0.484375) < 1e-12
        and abs(float(tuwien_uncertainty_8bit["qae_peak_probability_estimate"]) - 0.4877293857385438) < 1e-12,
        f"analytic={tuwien_uncertainty['analytic_uncertainty_adjusted_probability']}, grid={tuwien_uncertainty['midpoint_grid_probability']}, qpe8={tuwien_uncertainty_8bit['qae_peak_probability_estimate']}",
    )
    resource_comparisons = tuwien_resource["comparisons"]
    _check(
        checks,
        "measured H2 resource boundary values",
        int(tuwien_resource["rows"][0]["samples_or_queries"]) == 3142
        and int(tuwien_resource["rows"][1]["samples_or_queries"]) == 959427
        and int(tuwien_resource["rows"][2]["samples_or_queries"]) == 128
        and abs(float(resource_comparisons["ideal_qae_to_finite_qmc_sample_ratio"]) - 24.546875) < 1e-12
        and int(resource_comparisons["loader_rotation_bound_total_at_ideal_qae_queries"]) == 798068,
        f"qae={tuwien_resource['rows'][0]['samples_or_queries']}, mc={tuwien_resource['rows'][1]['samples_or_queries']}, qmc={tuwien_resource['rows'][2]['samples_or_queries']}",
    )
    structured_rows = {row["loader"]: row for row in tuwien_structured_loader["rows"]}
    _check(
        checks,
        "measured H2 structured loader boundary values",
        structured_rows["dense_128_state_table"]["rotations_per_prepare_uncompute"] == 254
        and structured_rows["optimistic_factorized_row_times_quantile"]["rotations_per_prepare_uncompute"] == 60
        and structured_rows["naive_row_conditioned_quadrature"]["rotations_per_prepare_uncompute"] == 420
        and abs(float(tuwien_structured_loader["ideal_qae_overhead_tolerance_vs_finite_qmc"]) - 0.04073838319541693) < 1e-12
        and structured_rows["optimistic_factorized_row_times_quantile"]["total_rotation_equivalents_at_3142_qae_queries"] == 188520
        and structured_rows["naive_row_conditioned_quadrature"]["total_rotation_equivalents_at_3142_qae_queries"] == 1319640,
        f"loaders={[(name, row['rotations_per_prepare_uncompute']) for name, row in structured_rows.items()]}",
    )
    hybrid_rows = {round(float(row["policy_recycle_fraction"]), 3): row for row in hybrid_policy_selection["policy_rows"]}
    _check(
        checks,
        "hybrid physical policy selection values",
        hybrid_policy_selection["selected_policy_by_empirical_probability"] == 0.41
        and hybrid_policy_selection["selected_policy_by_95pct_lower_bound"] == 0.41
        and hybrid_rows[0.410]["pass_count"] == 16
        and hybrid_rows[0.427]["pass_count"] == 7
        and hybrid_rows[0.440]["pass_count"] == 0
        and abs(float(hybrid_rows[0.427]["qae_8bit_probability_estimate"]) - 0.43879466240039194) < 1e-12
        and all(bool(row["finite_qmc_sobol_indices_cover_all_states"]) for row in hybrid_rows.values())
        and all(abs(float(row["finite_qmc_probability"]) - float(row["exact_finite_probability"])) < 1e-12 for row in hybrid_rows.values())
        and int(hybrid_rows[0.410]["dense_16_state_loader_total_rotation_equivalents"]) == 94260,
        f"selected={hybrid_policy_selection['selected_policy_by_empirical_probability']}, counts={[hybrid_rows[p]['pass_count'] for p in (0.410, 0.427, 0.440)]}",
    )
    surrogate_qpe8 = next(row for row in surrogate_continuous_qpe["qpe_rows"] if int(row["phase_bits"]) == 8)
    _check(
        checks,
        "independent-source continuous-prior surrogate QPE values",
        int(surrogate_continuous_qpe["physical_oracle_training_count"]) == 32
        and int(surrogate_continuous_qpe["state_count"]) == 128
        and abs(float(surrogate_continuous_qpe["surrogate_reference_probability"]) - 0.4705352783203125) < 1e-12
        and abs(float(surrogate_continuous_qpe["single_128_state_qmc_probability"]) - 0.46875) < 1e-12
        and abs(float(surrogate_qpe8["qae_peak_probability_estimate"]) - 0.4632177182001663) < 1e-12
        and abs(float(surrogate_qpe8["qae_expected_rmse_one_qpe_shot"]) - 0.0436897254315299) < 1e-12
        and int(surrogate_continuous_qpe["first_replicated_qmc_n_at_rmse_epsilon"]) == 32768
        and int(surrogate_continuous_qpe["dense_128_state_loader_total_at_ideal_qae"]) == 798068,
        f"reference={surrogate_continuous_qpe['surrogate_reference_probability']}, qmc128={surrogate_continuous_qpe['single_128_state_qmc_probability']}, qpe8={surrogate_qpe8['qae_peak_probability_estimate']}",
    )
    _check(
        checks,
        "independent-source quadratic surrogate holdout values",
        quadratic_holdout["status"] == "conditional_nonlinear_holdout_not_a_physical_oracle"
        and int(quadratic_holdout["sample_count"]) == 32
        and abs(float(quadratic_holdout["h2_rmse"]) - 2.4107255456177927e-06) < 1e-15
        and abs(float(quadratic_holdout["recovery_rmse"]) - 0.0015434139100057598) < 1e-15
        and abs(float(quadratic_holdout["event_accuracy"]) - 1.0) < 1e-12
        and "PSA_INDEPENDENT_SOURCE_QUADRATIC_SURROGATE_HOLDOUT_32.md" in manuscript,
        f"n={quadratic_holdout['sample_count']}, h2_rmse={quadratic_holdout['h2_rmse']}, recovery_rmse={quadratic_holdout['recovery_rmse']}",
    )
    selection_methods = {row["method"]: row for row in continuous_policy_selection["method_summary"]}
    _check(
        checks,
        "continuous-prior hybrid policy-selection values",
        continuous_policy_selection["status"] == "frozen_primary_case_conditional_surrogate_benchmark_not_physical_validation"
        and int(continuous_policy_selection["physical_training_draws"]) == 32
        and int(continuous_policy_selection["reference_sample_size_per_scramble"]) == 262144
        and int(continuous_policy_selection["reference_scrambles"]) == 8
        and int(continuous_policy_selection["replicates"]) == 200
        and continuous_policy_selection["true_selected_policy"] == 0.42
        and abs(float(continuous_policy_selection["reference_probability_by_policy"]["0.420"]) - 0.9274306297302246) < 1e-12
        and abs(float(continuous_policy_selection["reference_probability_by_policy"]["0.427"]) - 0.4704403877258301) < 1e-12
        and abs(float(continuous_policy_selection["reference_probability_by_policy"]["0.430"]) - 0.283597469329834) < 1e-12
        and float(selection_methods["MC_same_query"]["correct_selection_fraction"]) == 1.0
        and float(selection_methods["Sobol_RQMC"]["correct_selection_fraction"]) == 1.0
        and float(selection_methods["MLAE_0.00"]["correct_selection_fraction"]) == 1.0
        and abs(float(selection_methods["defensive_mixture_IS"]["correct_selection_fraction"]) - 0.995) < 1e-12
        and abs(float(selection_methods["Sobol_RQMC"]["rmse_across_policy_estimates"]) - 0.002482444815142756) < 1e-12
        and abs(float(selection_methods["defensive_mixture_IS"]["rmse_across_policy_estimates"]) - 0.010170348016498102) < 1e-12
        and abs(float(selection_methods["MLAE_0.05"]["rmse_across_policy_estimates"]) - 0.005472817413062547) < 1e-12
        and "PSA_QAE_CONTINUOUS_POLICY_SELECTION.md" in manuscript,
        f"true_selected={continuous_policy_selection['true_selected_policy']}, methods={sorted(selection_methods)}",
    )
    sample_size_summary = {int(row["sample_size"]): row for row in policy_sample_size["summary"]}
    _check(
        checks,
        "physical policy sample-size design values",
        policy_sample_size["status"] == "finite_physical_pilot_resampling_design_not_process_power_guarantee"
        and int(policy_sample_size["source_state_count"]) == 16
        and policy_sample_size["sample_sizes"] == [16, 32, 64, 128, 256]
        and policy_sample_size["normal_approximation_required_n_at_p_0.5"] == {
            "absolute_half_width_0.05": 385,
            "absolute_half_width_0.03": 1068,
            "absolute_half_width_0.02": 2401,
        }
        and abs(float(sample_size_summary[16]["empirical_selection_frequency_0.410"]) - 0.60006) < 1e-12
        and abs(float(sample_size_summary[256]["empirical_selection_frequency_0.410"]) - 0.97454) < 1e-12
        and "PSA_QAE_POLICY_SAMPLE_SIZE_DESIGN.md" in manuscript,
        f"N16/N256 empirical r0.410={sample_size_summary[16]['empirical_selection_frequency_0.410']}/{sample_size_summary[256]['empirical_selection_frequency_0.410']}",
    )
    cvar_rows = [row for row in cvar_loss_bridge["metrics"] if row["epsilon"] == 0.001]
    cvar_by_key = {(row["observable"], row["alpha"]): row for row in cvar_rows}
    _check(
        checks,
        "recovery-loss CVaR bridge values",
        cvar_loss_bridge["status"] == "cvar_like_tail_observable_bridge_without_quantum_speedup_claim"
        and cvar_loss_bridge["n_physical_draws"] == 32
        and abs(float(cvar_loss_bridge["base_metrics"]["recovery_loss_mean"]) - 0.17203850265635054) < 1e-15
        and abs(float(cvar_by_key[("tail_loss_mass", 0.9)]["empirical_mean"]) - 0.029880194901519556) < 1e-15
        and abs(float(cvar_by_key[("tail_loss_mass", 0.95)]["empirical_mean"]) - 0.015259642504985696) < 1e-15
        and abs(float(cvar_by_key[("tail_loss_mass", 0.9)]["mc_to_qae_ratio"]) - 35.440483768300446) < 1e-12
        and abs(float(cvar_by_key[("tail_loss_mass", 0.95)]["mc_to_qae_ratio"]) - 18.372056015276893) < 1e-12
        and "PSA_QAE_CVAR_LOSS_BRIDGE.md" in manuscript,
        f"n={cvar_loss_bridge['n_physical_draws']}, tail90={cvar_by_key[('tail_loss_mass', 0.9)]['empirical_mean']}, tail95={cvar_by_key[('tail_loss_mass', 0.95)]['empirical_mean']}",
    )
    direct_tail_rows = direct_tail_stability["records"]
    direct_tail_seed = direct_tail_stability["n128_seed_delta"]
    direct_sobol_seed90 = next(row for row in direct_tail_seed if row["method"] == "Sobol_QMC" and abs(float(row["alpha"]) - 0.90) < 1e-12)
    direct_sobol_seed95 = next(row for row in direct_tail_seed if row["method"] == "Sobol_QMC" and abs(float(row["alpha"]) - 0.95) < 1e-12)
    _check(
        checks,
        "direct physical recovery-loss tail stability values",
        direct_tail_stability["status"] == "direct_physical_tail_stability_control_not_converged_process_risk_claim"
        and len(direct_tail_rows) == 48
        and direct_tail_stability["source_campaigns"][-1]["sample_size"] == 256
        and abs(float(direct_sobol_seed90["n128_seed0_tail_loss_mass"]) - 0.06459526045252749) < 1e-15
        and abs(float(direct_sobol_seed90["n128_seed300_tail_loss_mass"]) - 0.09208517567195346) < 1e-15
        and abs(float(direct_sobol_seed90["absolute_seed_delta"]) - 0.027489915219425967) < 1e-15
        and abs(float(direct_sobol_seed95["n128_seed0_tail_loss_mass"]) - 0.036758083918381125) < 1e-15
        and abs(float(direct_sobol_seed95["n128_seed300_tail_loss_mass"]) - 0.03660483842642773) < 1e-15
        and all(bool(row["all_css_gate_pass"]) and bool(row["all_mass_balance_gate_pass"]) for row in direct_tail_rows)
        and "PSA_QAE_DIRECT_PHYSICAL_TAIL_STABILITY.md" in manuscript,
        f"rows={len(direct_tail_rows)}, sobol90_delta={direct_sobol_seed90['absolute_seed_delta']}, sobol95={direct_sobol_seed95['n128_seed0_tail_loss_mass']}/{direct_sobol_seed95['n128_seed300_tail_loss_mass']}",
    )
    tail_loss_rows = tail_loss_oracle["tail_rows"]
    _check(
        checks,
        "finite weighted tail-loss oracle values",
        tail_loss_oracle["status"] == "finite_fixed_point_tail_loss_oracle_compiled_and_exhaustively_verified_not_cyclic_or_continuous"
        and tail_loss_oracle["state_count"] == 256
        and tail_loss_oracle["address_qubits"] == 8
        and tail_loss_oracle["output_register"]["bits"] == 14
        and tail_loss_oracle["lookup_compilation"]["mcx_primitives"] == 1768
        and tail_loss_oracle["lookup_compilation"]["x_gates"] == 14078
        and tail_loss_oracle["lookup_compilation"]["abstract_operation_count"] == 15846
        and tail_loss_oracle["lookup_compilation"]["inverse_checks"] == 4194304
        and tail_loss_oracle["gate_summary"]["all_quantized_tail_labels_match"]
        and abs(float(tail_loss_oracle["output_register"]["quantization_max_absolute_error"]) - 3.043035653926829e-05) < 1e-15
        and len(tail_loss_rows) == 2
        and all(int(row["tail_label_mismatch_count"]) == 0 for row in tail_loss_rows)
        and "PSA_QAE_DIRECT_PHYSICAL_TAIL_LOSS_ORACLE.md" in manuscript,
        f"ops={tail_loss_oracle['lookup_compilation']['abstract_operation_count']}, inverse_checks={tail_loss_oracle['lookup_compilation']['inverse_checks']}, max_q_error={tail_loss_oracle['output_register']['quantization_max_absolute_error']}",
    )
    tail_amplitude_rows = tail_amplitude_oracle["tail_rows"]
    _check(
        checks,
        "finite Bernoulliized tail-amplitude oracle values",
        tail_amplitude_oracle["status"] == "finite_bernoulliized_tail_amplitude_oracle_exhaustively_verified_not_continuous_or_hardware"
        and tail_amplitude_oracle["state_count"] == 256
        and tail_amplitude_oracle["loss_register_bits"] == 14
        and tail_amplitude_oracle["random_register_bits"] == 14
        and tail_amplitude_oracle["loss_lookup"]["forward_uncompute_abstract_operations"] == 31692
        and tail_amplitude_oracle["comparator"]["abstract_comparator_primitives_per_alpha"] == 1
        and len(tail_amplitude_rows) == 2
        and all(int(row["comparator_inverse_checks"]) == 8388608 for row in tail_amplitude_rows)
        and all(int(row["tail_label_mismatch_count"]) == 0 for row in tail_amplitude_rows)
        and abs(float(tail_amplitude_rows[0]["amplitude_abs_error_vs_exact_tail_loss"]) - 1.7616415477761382e-07) < 1e-15
        and abs(float(tail_amplitude_rows[1]["amplitude_abs_error_vs_exact_tail_loss"]) - 1.6480288744791238e-07) < 1e-15
        and tail_amplitude_oracle["gate_summary"]["all_amplitude_errors_below_0.001"]
        and "PSA_QAE_DIRECT_PHYSICAL_TAIL_AMPLITUDE_ORACLE.md" in manuscript,
        f"rows={len(tail_amplitude_rows)}, inverse_checks={tail_amplitude_rows[0]['comparator_inverse_checks']}, errors={[row['amplitude_abs_error_vs_exact_tail_loss'] for row in tail_amplitude_rows]}",
    )
    mlae_rows = tail_amplitude_mlae["summary_shots_100"]
    mlae_by_key = {
        (round(float(row["alpha"]), 2), round(float(row["bit_flip_probability"]), 2), row["method"]): row
        for row in mlae_rows
    }
    _check(
        checks,
        "finite tail-amplitude MLAE/noise values",
        tail_amplitude_mlae["status"] == "conditional_MLAE_measurement_stress_on_finite_Bernoulliized_tail_amplitude"
        and len(tail_amplitude_mlae["rows"]) == 48
        and len(mlae_rows) == 12
        and tail_amplitude_mlae["repetitions"] == 200
        and abs(float(mlae_by_key[(0.90, 0.00, "noisy_MLAE_assuming_ideal_model")]["rmse"]) - 0.0011941247500425532) < 1e-12
        and abs(float(mlae_by_key[(0.90, 0.05, "noisy_MLAE_assuming_ideal_model")]["rmse"]) - 0.001908787275772803) < 1e-12
        and abs(float(mlae_by_key[(0.95, 0.00, "noisy_MLAE_assuming_ideal_model")]["rmse"]) - 0.0010321488751486407) < 1e-12
        and abs(float(mlae_by_key[(0.95, 0.05, "noisy_MLAE_assuming_ideal_model")]["rmse"]) - 0.004589428212086812) < 1e-12
        and abs(float(mlae_by_key[(0.95, 0.05, "MC_same_oracle_query_budget")]["rmse"]) - 0.003370898630720983) < 1e-12
        and "QAE_DIRECT_PHYSICAL_TAIL_AMPLITUDE_MLAE_NOISE.md" in manuscript,
        f"rows={len(tail_amplitude_mlae['rows'])}, alpha90_5pct={mlae_by_key[(0.90, 0.05, 'noisy_MLAE_assuming_ideal_model')]['rmse']}, alpha95_5pct={mlae_by_key[(0.95, 0.05, 'noisy_MLAE_assuming_ideal_model')]['rmse']}",
    )
    tail_end_rows = tail_end_to_end["rows"]
    _check(
        checks,
        "finite tail-amplitude end-to-end boundary values",
        tail_end_to_end["status"] == "finite_tail_amplitude_end_to_end_boundary_reverses_ideal_query_advantage"
        and len(tail_end_rows) == 2
        and all(int(row["ideal_qae_queries"]) == 3142 for row in tail_end_rows)
        and all(int(row["lookup_forward_uncompute_plus_comparator_ops_per_qae_query"]) == 31693 for row in tail_end_rows)
        and abs(float(tail_end_rows[0]["mc_95pct_samples"]) - 231508) < 1e-12
        and abs(float(tail_end_rows[1]["mc_95pct_samples"]) - 127038) < 1e-12
        and abs(float(tail_end_rows[0]["normalized_qae_work_to_mc_ratio"]) - 430.1337577967068) < 1e-12
        and abs(float(tail_end_rows[1]["normalized_qae_work_to_mc_ratio"]) - 783.8552716510021) < 1e-12
        and "QAE_DIRECT_PHYSICAL_TAIL_END_TO_END_BOUNDARY.md" in manuscript,
        f"ops_per_query={tail_end_rows[0]['lookup_forward_uncompute_plus_comparator_ops_per_qae_query']}, normalized_ratios={[row['normalized_qae_work_to_mc_ratio'] for row in tail_end_rows]}",
    )
    loader_rows = tail_loader_crossover["rows"]
    _check(
        checks,
        "loader-sensitive tail crossover values",
        tail_loader_crossover["status"] == "conditional_loader_sensitive_tail_resource_crossover_with_qmc_negative_control"
        and len(loader_rows) == 2
        and int(tail_loader_crossover["scenario"]["forward_oracle_units"]) == 1857600
        and int(tail_loader_crossover["scenario"]["controlled_plus_loader_units_per_qae_query"]) == 3715749
        and abs(float(loader_rows[0]["qae_to_mc_resource_ratio"]) - 0.027147781480386164) < 1e-15
        and abs(float(loader_rows[1]["qae_to_mc_resource_ratio"]) - 0.04947282383980573) < 1e-15
        and all(abs(float(row["qae_to_qmc_resource_ratio"]) - 12.275251162033673) < 1e-12 for row in loader_rows)
        and abs(float(loader_rows[0]["finite_table_qae_to_mc_ratio"]) - 430.1337577967068) < 1e-12
        and abs(float(loader_rows[1]["finite_table_qae_to_mc_ratio"]) - 783.8552716510021) < 1e-12
        and "QAE_TAIL_LOADER_RESOURCE_CROSSOVER.md" in manuscript,
        f"qae_mc={[row['qae_to_mc_resource_ratio'] for row in loader_rows]}, qae_qmc={[row['qae_to_qmc_resource_ratio'] for row in loader_rows]}",
    )
    _check(
        checks,
        "continuous operating-parameter prior values",
        process_parameter_prior["status"] == "conditional_trilinear_process_parameter_prior_qmc_control"
        and process_parameter_prior["source_grid_shape"] == [4, 3, 4]
        and int(process_parameter_prior["reference_states"]) == 262144
        and abs(float(process_parameter_prior["reference_probability"]) - 0.6425971984863281) < 1e-12
        and process_parameter_prior["first_qmc_sample_size_at_rmse_epsilon"] == 8192
        and process_parameter_prior["first_mc_sample_size_at_rmse_epsilon"] is None
        and int(process_parameter_prior["mc_95pct_samples_at_epsilon"]) == 882253
        and int(process_parameter_prior["ideal_qae_queries_at_epsilon"]) == 3142
        and process_parameter_prior["conditional_loader_boundary"]["address_qubits"] == 6
        and process_parameter_prior["conditional_loader_boundary"]["multilinear_corner_evaluations_per_query"] == 8
        and "QAE_PROCESS_PARAMETER_CONTINUOUS_PRIOR.md" in manuscript,
        f"p={process_parameter_prior['reference_probability']}, first_qmc={process_parameter_prior['first_qmc_sample_size_at_rmse_epsilon']}, mc_proxy={process_parameter_prior['mc_95pct_samples_at_epsilon']}",
    )
    resource_rows = process_parameter_resource["rows"]
    resource_min = next(row for row in resource_rows if int(row["effective_controlled_process_units_per_qae_query"]) == 8)
    _check(
        checks,
        "continuous operating-parameter resource boundary values",
        process_parameter_resource["status"] == "conditional_process_parameter_loader_resource_boundary_with_qmc_control"
        and int(process_parameter_resource["ideal_qae_queries"]) == 3142
        and int(process_parameter_resource["mc_95pct_evaluations"]) == 882253
        and int(process_parameter_resource["qmc_evaluations_at_rmse_epsilon"]) == 8192
        and abs(float(process_parameter_resource["mc_overhead_tolerance_units_per_qae_query"]) - 280.7934436664545) < 1e-12
        and abs(float(process_parameter_resource["qmc_overhead_tolerance_units_per_qae_query"]) - 2.6072565245066834) < 1e-12
        and abs(float(resource_min["qae_to_mc_ratio"]) - 0.02849069371257451) < 1e-15
        and abs(float(resource_min["qae_to_qmc_ratio"]) - 3.068359375) < 1e-12
        and "QAE_PROCESS_PARAMETER_RESOURCE_BOUNDARY.md" in manuscript,
        f"tolerances=({process_parameter_resource['mc_overhead_tolerance_units_per_qae_query']}, {process_parameter_resource['qmc_overhead_tolerance_units_per_qae_query']}), c8=({resource_min['qae_to_mc_ratio']}, {resource_min['qae_to_qmc_ratio']})",
    )
    weight_rows = {float(row["concentration"]): row for row in process_prior_weight["summary"]}
    _check(
        checks,
        "process-prior weight sensitivity values",
        process_prior_weight["status"] == "conditional_dirichlet_process_prior_weight_sensitivity_not_calibrated"
        and int(process_prior_weight["cell_count"]) == 18
        and abs(float(process_prior_weight["uniform_cell_probability"]) - 0.6427951388888888) < 1e-12
        and abs(float(weight_rows[1.0]["probability_p025"]) - 0.14129454243210754) < 1e-12
        and abs(float(weight_rows[1.0]["probability_p975"]) - 0.9871307893571316) < 1e-12
        and abs(float(weight_rows[1000.0]["probability_p025"]) - 0.6207212678196381) < 1e-12
        and abs(float(weight_rows[1000.0]["probability_p975"]) - 0.6645350055640509) < 1e-12
        and abs(float(weight_rows[1.0]["absolute_shift_from_uniform_p975"]) - 0.5015005964567814) < 1e-12
        and "QAE_PROCESS_PARAMETER_PRIOR_WEIGHT_SENSITIVITY.md" in manuscript,
        f"k1={[weight_rows[1.0]['probability_p025'], weight_rows[1.0]['probability_p975']]}, k1000={[weight_rows[1000.0]['probability_p025'], weight_rows[1000.0]['probability_p975']]}",
    )
    _check(
        checks,
        "surrogate model-discrepancy boundary values",
        int(discrepancy_boundary["state_count"]) == 4096
        and int(discrepancy_boundary["replicates"]) == 512
        and abs(float(discrepancy_boundary["base_surrogate_probability"]) - 0.4716796875) < 1e-12
        and abs(float(discrepancy_boundary["discrepancy_stress_probability_p025"]) - 0.46826171875) < 1e-12
        and abs(float(discrepancy_boundary["discrepancy_stress_probability_p975"]) - 0.47607421875) < 1e-12
        and abs(float(discrepancy_boundary["discrepancy_stress_abs_shift_p975"]) - 0.004638671875) < 1e-12,
        f"base={discrepancy_boundary['base_surrogate_probability']}, interval=[{discrepancy_boundary['discrepancy_stress_probability_p025']}, {discrepancy_boundary['discrepancy_stress_probability_p975']}]",
    )
    rare_rows = {round(float(row["recovery_guard_band"]), 3): row for row in rare_tail_boundary["summary_rows"]}
    _check(
        checks,
        "surrogate rare-tail boundary values",
        rare_tail_boundary["status"] == "rare_tail_surrogate_sensitivity_boundary"
        and rare_rows[0.775]["reference_probability"] == 0.005214691162109375
        and rare_rows[0.780]["reference_probability"] == 0.09171676635742188
        and rare_rows[0.785]["reference_probability"] == 0.3081550598144531
        and rare_rows[0.789]["reference_probability"] == 0.5291938781738281
        and rare_rows[0.775]["first_qmc_n_at_rmse_epsilon"] == 4096
        and abs(float(rare_rows[0.775]["mc_to_ideal_qae_query_ratio"]) - 6.342457033736474) < 1e-12,
        f"p={[rare_rows[t]['reference_probability'] for t in (0.775, 0.780, 0.785, 0.789)]}, qmc_first={rare_rows[0.775]['first_qmc_n_at_rmse_epsilon']}",
    )
    direct_rare_rows = {
        (round(float(row["recovery_guard_band"]), 3), row["method"]): row
        for row in direct_physical_rare_tail_boundary["n128_summary"]
    }
    direct_qpe_rows = {
        (round(float(row["recovery_guard_band"]), 3), row["method"]): row
        for row in direct_physical_rare_tail_boundary["qpe_rows"]
    }
    _check(
        checks,
        "direct physical rare-tail boundary values",
        direct_physical_rare_tail_boundary["status"] == "direct_reduced_physical_rare_tail_sensitivity_boundary"
        and direct_physical_rare_tail_boundary["sample_sizes"] == [16, 32, 64, 128]
        and direct_rare_rows[(0.35, "Sobol_QMC")]["pass_count"] == 6
        and direct_rare_rows[(0.35, "MC")]["pass_count"] == 1
        and abs(float(direct_rare_rows[(0.35, "IS")]["event_probability"]) - 0.0012071710643394185) < 1e-12
        and direct_rare_rows[(0.50, "MC")]["pass_count"] == 36
        and abs(float(direct_qpe_rows[(0.35, "Sobol_QMC")]["qae_8bit_expected_rmse"]) - 0.027810703788454547) < 1e-12
        and abs(float(direct_qpe_rows[(0.35, "MC")]["matched_query_mc_rmse"]) - 0.005513429182282041) < 1e-12
        and all(bool(row["all_css_gate_pass"]) and bool(row["all_mass_balance_gate_pass"]) for row in direct_physical_rare_tail_boundary["records"]),
        f"n128={[(key, row['event_probability']) for key, row in direct_rare_rows.items()]}",
    )
    direct_replicate_rows = {
        (round(float(row["recovery_guard_band"]), 3), row["method"]): row
        for row in direct_physical_rare_tail_replicates["aggregate_rows"]
    }
    _check(
        checks,
        "replicated direct physical rare-tail boundary values",
        direct_physical_rare_tail_replicates["status"] == "direct_reduced_physical_rare_tail_replicated_boundary"
        and int(direct_physical_rare_tail_replicates["source_count"]) == 3
        and int(direct_physical_rare_tail_replicates["sample_size_per_method"]) == 32
        and abs(float(direct_replicate_rows[(0.35, "Sobol_QMC")]["mean_event_probability"]) - 0.010416666666666666) < 1e-12
        and abs(float(direct_replicate_rows[(0.35, "MC")]["mean_event_probability"]) - 0.020833333333333332) < 1e-12
        and abs(float(direct_replicate_rows[(0.40, "IS")]["mean_event_probability"]) - 0.04304193005602055) < 1e-12
        and int(direct_physical_rare_tail_replicates["dense_loader_rotations_per_prepare_uncompute"]) == 62
        and int(direct_physical_rare_tail_replicates["dense_loader_total_rotation_equivalents_at_ideal_qae"]) == 194804
        and bool(direct_physical_rare_tail_replicates["all_gate_checks_pass"]),
        f"K={direct_physical_rare_tail_replicates['source_count']}, guard0.35={[direct_replicate_rows[(0.35, method)]['mean_event_probability'] for method in ('Sobol_QMC', 'MC', 'IS')]}",
    )
    mlae_rows = {
        (round(float(row["recovery_guard_band"]), 3), row["method"], round(float(row["bit_flip_probability"]), 2)): row
        for row in direct_physical_rare_tail_mlae["rows"]
    }
    _check(
        checks,
        "direct physical rare-tail MLAE/noise values",
        direct_physical_rare_tail_mlae["status"] == "conditional_mlae_measurement_stress_on_replicated_direct_physical_tail"
        and len(direct_physical_rare_tail_mlae["rows"]) == 18
        and abs(float(mlae_rows[(0.35, "Sobol_QMC", 0.0)]["qae_rmse"]) - 0.000576) < 5e-7
        and abs(float(mlae_rows[(0.35, "Sobol_QMC", 0.05)]["qae_rmse"]) - 0.001352) < 5e-7
        and abs(float(mlae_rows[(0.40, "Sobol_QMC", 0.05)]["qae_rmse"]) - 0.004651) < 5e-7
        and int(direct_physical_rare_tail_mlae["dense_loader_rotations_per_prepare_uncompute"]) == 62,
        f"rows={len(direct_physical_rare_tail_mlae['rows'])}, guard0.40_5pct={mlae_rows[(0.40, 'Sobol_QMC', 0.05)]['qae_rmse']}",
    )
    cross_delta_rows = [row for row in cross_oracle_model_form["rows"] if row["oracle"] == "absolute_model_form_delta"]
    _check(
        checks,
        "cross-oracle recovery model-form boundary values",
        cross_oracle_model_form["status"] == "cross_oracle_recovery_model_form_boundary_unpaired_stress_control"
        and abs(float(cross_oracle_model_form["max_absolute_model_form_delta"]) - 0.5104166666666666) < 1e-12
        and bool(cross_oracle_model_form["gate_summary"]["reduced_all_gates_pass"])
        and bool(cross_oracle_model_form["gate_summary"]["spatial_all_l1_and_mass_pass"])
        and int(cross_oracle_model_form["gate_summary"]["spatial_strict_max_css_failures"]) == 18
        and len(cross_delta_rows) == 18,
        f"max_delta={cross_oracle_model_form['max_absolute_model_form_delta']}, strict_failures={cross_oracle_model_form['gate_summary']['spatial_strict_max_css_failures']}",
    )
    _check(
        checks,
        "paired-oracle recovery model-form boundary values",
        paired_oracle_model_form["status"] == "paired_uncertainty_state_model_form_boundary_uncalibrated_oracle"
        and int(paired_oracle_model_form["paired_count_per_method"]) == 8
        and abs(float(paired_oracle_model_form["max_absolute_paired_delta"]) - 0.75) < 1e-12
        and len(paired_oracle_model_form["aggregate_rows"]) == 18
        and all(bool(row["process_gate_pass"]) and bool(row["css_or_l1_gate_pass"]) and bool(row["mass_balance_gate_pass"]) for row in paired_oracle_model_form["reduced_rows"] + paired_oracle_model_form["spatial_tank_rows"])
        and any(int(row["spatial_strict_max_css_fail_count"]) > 0 for row in paired_oracle_model_form["aggregate_rows"]),
        f"K={paired_oracle_model_form['paired_count_per_method']}, max_delta={paired_oracle_model_form['max_absolute_paired_delta']}, aggregate_rows={len(paired_oracle_model_form['aggregate_rows'])}",
    )
    paired_k16_rows = {
        (round(float(row["recovery_guard_band"]), 3), row["method"]): row
        for row in paired_oracle_model_form_k16["aggregate_rows"]
    }
    _check(
        checks,
        "paired-oracle K=16 recovery model-form boundary values",
        paired_oracle_model_form_k16["status"] == "paired_uncertainty_state_model_form_boundary_uncalibrated_oracle"
        and int(paired_oracle_model_form_k16["paired_count_per_method"]) == 16
        and abs(float(paired_oracle_model_form_k16["max_absolute_paired_delta"]) - 0.5625) < 1e-12
        and len(paired_oracle_model_form_k16["aggregate_rows"]) == 18
        and abs(float(paired_k16_rows[(0.55, "IS")]["reduced_probability"]) - 0.75) < 1e-12
        and abs(float(paired_k16_rows[(0.55, "IS")]["spatial_tank_probability"]) - 0.25) < 1e-12
        and abs(float(paired_k16_rows[(0.60, "IS")]["reduced_probability"]) - 0.5625) < 1e-12
        and abs(float(paired_k16_rows[(0.60, "IS")]["spatial_tank_probability"]) - 0.0) < 1e-12
        and all(bool(row["process_gate_pass"]) and bool(row["css_or_l1_gate_pass"]) and bool(row["mass_balance_gate_pass"]) for row in paired_oracle_model_form_k16["reduced_rows"] + paired_oracle_model_form_k16["spatial_tank_rows"])
        and any(int(row["spatial_strict_max_css_fail_count"]) > 0 for row in paired_oracle_model_form_k16["aggregate_rows"]),
        f"K={paired_oracle_model_form_k16['paired_count_per_method']}, max_delta={paired_oracle_model_form_k16['max_absolute_paired_delta']}, aggregate_rows={len(paired_oracle_model_form_k16['aggregate_rows'])}",
    )
    paired_k32_rows = {
        (round(float(row["recovery_guard_band"]), 3), row["method"]): row
        for row in paired_oracle_model_form_k32["aggregate_rows"]
    }
    _check(
        checks,
        "paired-oracle K=32 recovery model-form boundary values",
        paired_oracle_model_form_k32["status"] == "paired_uncertainty_state_model_form_boundary_uncalibrated_oracle"
        and int(paired_oracle_model_form_k32["paired_count_per_method"]) == 32
        and abs(float(paired_oracle_model_form_k32["max_absolute_paired_delta"]) - 0.5) < 1e-12
        and len(paired_oracle_model_form_k32["aggregate_rows"]) == 18
        and abs(float(paired_k32_rows[(0.55, "IS")]["reduced_probability"]) - 0.65625) < 1e-12
        and abs(float(paired_k32_rows[(0.55, "IS")]["spatial_tank_probability"]) - 0.28125) < 1e-12
        and abs(float(paired_k32_rows[(0.60, "IS")]["reduced_probability"]) - 0.5) < 1e-12
        and abs(float(paired_k32_rows[(0.60, "IS")]["spatial_tank_probability"]) - 0.0) < 1e-12
        and all(bool(row["process_gate_pass"]) and bool(row["css_or_l1_gate_pass"]) and bool(row["mass_balance_gate_pass"]) for row in paired_oracle_model_form_k32["reduced_rows"] + paired_oracle_model_form_k32["spatial_tank_rows"])
        and any(int(row["spatial_strict_max_css_fail_count"]) > 0 for row in paired_oracle_model_form_k32["aggregate_rows"]),
        f"K={paired_oracle_model_form_k32['paired_count_per_method']}, max_delta={paired_oracle_model_form_k32['max_absolute_paired_delta']}, aggregate_rows={len(paired_oracle_model_form_k32['aggregate_rows'])}",
    )
    _check(
        checks,
        "paired-oracle K-progress summary values",
        paired_oracle_k_progress["status"] == "paired_oracle_k_progress_uncalibrated_model_form_diagnostic"
        and [int(row["paired_count_per_method"]) for row in paired_oracle_k_progress["rows"]] == [8, 16, 32]
        and [round(float(row["max_absolute_paired_delta"]), 4) for row in paired_oracle_k_progress["rows"]] == [0.75, 0.5625, 0.5]
        and all(bool(row["all_process_l1_mass_gates_pass"]) for row in paired_oracle_k_progress["rows"]),
        f"K={[row['paired_count_per_method'] for row in paired_oracle_k_progress['rows']]}, max_deltas={[row['max_absolute_paired_delta'] for row in paired_oracle_k_progress['rows']]}",
    )
    _check(
        checks,
        "bounded literature-gap update",
        "direct industrial PSA + QAE case" in literature_gap
        and "Nieman et al." in literature_gap
        and "Nenno and Caspari" in literature_gap
        and "Yun et al." in literature_gap
        and "Sarno" in literature_gap
        and "He et al." in literature_gap
        and "nieman2024cstramplitude" in references
        and "nenno2024dynamicquantum" in references
        and "yun2026industrialh2psa" in references
        and "sarno2026qaegrad" in references
        and "he2025qareliability" in references
        and "QAE/MLAE resource" in manuscript,
        "direct PSA+QAE gap is scoped and adjacent process-quantum/QAE precedents are recorded",
    )
    resource_rows = {row["scenario"]: row for row in end_to_end_resource["rows"]}
    _check(
        checks,
        "consolidated end-to-end resource boundary values",
        end_to_end_resource["status"] == "conditional_resource_boundary_with_paired_model_form_control"
        and abs(float(resource_rows["breakthrough 3D"]["qae_over_qmc_wall_overhead_tolerance"]) - 2.6072565245066834) < 1e-12
        and abs(float(resource_rows["breakthrough 3D"]["qae_over_qmc_normalized_resource_ratio"]) - 3.1003214518229165) < 1e-12
        and abs(float(resource_rows["spatial/tank 7D"]["qae_over_qmc_wall_overhead_tolerance"]) - 0.16295353278166771) < 1e-12
        and abs(float(resource_rows["spatial/tank 7D"]["qae_over_qmc_normalized_resource_ratio"]) - 12.275251162033673) < 1e-12
        and abs(float(resource_rows["spatial/tank 7D"]["dense_8bit_table_gib"]) - 536870912.0) < 1e-9
        and abs(float(end_to_end_resource["paired_k32_max_model_form_delta"]) - 0.5) < 1e-12,
        f"breakthrough={resource_rows['breakthrough 3D']['qae_over_qmc_wall_overhead_tolerance']}, spatial={resource_rows['spatial/tank 7D']['qae_over_qmc_normalized_resource_ratio']}, paired_delta={end_to_end_resource['paired_k32_max_model_form_delta']}",
    )
    _check(
        checks,
        "strict CSS horizon screen values",
        strict_css_horizon["status"] == "strict_css_horizon_screen_representative_uncalibrated_oracle"
        and strict_css_horizon["horizons"] == [20, 40, 80, 160]
        and len(strict_css_horizon["rows"]) == 12
        and all(bool(row["l1_css_gate_pass"]) and bool(row["mass_balance_gate_pass"]) for row in strict_css_horizon["rows"])
        and all(sum(bool(row["strict_css_gate_pass"]) for row in strict_css_horizon["rows"] if int(row["n_cycles"]) == horizon) == 1 for horizon in (20, 40, 80, 160))
        and max(float(row["css_residual_max"]) for row in strict_css_horizon["rows"] if not bool(row["strict_css_gate_pass"])) > 2.0e-3,
        f"rows={len(strict_css_horizon['rows'])}, strict_pass_by_horizon={[sum(bool(row['strict_css_gate_pass']) for row in strict_css_horizon['rows'] if int(row['n_cycles']) == horizon) for horizon in (20, 40, 80, 160)]}",
    )
    _check(
        checks,
        "strict CSS mesh screen values",
        strict_css_mesh["status"] == "strict_css_mesh_screen_representative_uncalibrated_oracle"
        and strict_css_mesh["cells_compared"] == [4, 8]
        and strict_css_mesh["horizons"] == [40]
        and len(strict_css_mesh["rows"]) == 6
        and all(bool(row["l1_css_gate_pass"]) and bool(row["mass_balance_gate_pass"]) for row in strict_css_mesh["rows"])
        and sum(bool(row["strict_css_gate_pass"]) for row in strict_css_mesh["rows"] if int(row["n_cells"]) == 4) == 1
        and sum(bool(row["strict_css_gate_pass"]) for row in strict_css_mesh["rows"] if int(row["n_cells"]) == 8) == 2
        and abs(float(next(row for row in strict_css_mesh["rows"] if row["method"] == "Sobol_QMC" and int(row["sample_index"]) == 0 and int(row["n_cells"]) == 4)["css_residual_max"]) - 1.630e-2) < 1e-5
        and abs(float(next(row for row in strict_css_mesh["rows"] if row["method"] == "Sobol_QMC" and int(row["sample_index"]) == 0 and int(row["n_cells"]) == 8)["css_residual_max"]) - 1.749e-7) < 1e-9,
        f"rows={len(strict_css_mesh['rows'])}, strict_pass_by_cells={[sum(bool(row['strict_css_gate_pass']) for row in strict_css_mesh['rows'] if int(row['n_cells']) == cells) for cells in (4, 8)]}",
    )
    _check(
        checks,
        "SCI submission scope gate",
        submission_gate["status"] == "resource_aware_methods_paper_conditional_submission_ready"
        and "resource-aware quantum simulation/estimation method" in submission_gate["supportable_claim"]
        and len(submission_gate["minimum_submission_conditions"]) == 5
        and "hardware quantum speedup" in submission_gate["unsupported_claims_until_gates_close"],
        f"status={submission_gate['status']}, conditions={len(submission_gate['minimum_submission_conditions'])}",
    )
    high_n_row = next(row for row in high_n_extension["rows"] if int(row["sample_count_per_method"]) == 256)
    _check(
        checks,
        "direct physical high-N extension values",
        high_n_extension["status"] == "direct_physical_reduced_order_high_n_extension_single_seed_not_formal_convergence"
        and high_n_extension["sample_sizes"] == [16, 32, 64, 128, 256]
        and len(high_n_extension["rows"]) == 5
        and bool(high_n_row["all_css_and_mass_balance_pass"])
        and abs(float(high_n_row["qmc_probability"]) - 0.6640625) < 1e-12
        and abs(float(high_n_row["mc_probability"]) - 0.6796875) < 1e-12
        and abs(float(high_n_row["is_weighted_probability"]) - 0.7326607723888873) < 1e-12
        and abs(float(high_n_row["is_effective_sample_size"]) - 198.2299649045058) < 1e-9,
        f"n256_qmc={high_n_row['qmc_probability']}, n256_mc={high_n_row['mc_probability']}, n256_is={high_n_row['is_weighted_probability']}",
    )
    _check(
        checks,
        "independent-seed N=128 extension values",
        n128_replicate_extension["status"] == "direct_physical_reduced_order_n128_independent_seed_extension_not_formal_convergence"
        and n128_replicate_extension["seed_offsets"] == {"seed0": 0, "seed300": 300}
        and len(n128_replicate_extension["rows"]) == 6
        and abs(float(n128_replicate_extension["paired_summary"]["qmc_mean"]) - 0.66796875) < 1e-12
        and abs(float(n128_replicate_extension["paired_summary"]["qmc_sd"]) - 0.016572815184059706) < 1e-12
        and abs(float(n128_replicate_extension["paired_summary"]["mc_mean"]) - 0.64453125) < 1e-12
        and abs(float(n128_replicate_extension["paired_summary"]["mc_sd"]) - 0.027621358640099514) < 1e-12
        and bool(n128_replicate_extension["paired_summary"]["all_rows_css_and_mass_balance_pass"]),
        f"seeds={n128_replicate_extension['seed_offsets']}, qmc_mean={n128_replicate_extension['paired_summary']['qmc_mean']}, mc_mean={n128_replicate_extension['paired_summary']['mc_mean']}",
    )
    compiled_rows = compiled_physical_oracle["rows"]
    compiled_n16 = {(row["method"]): row for row in compiled_rows if row["campaign"] == "n16_seed0"}
    compiled_n256 = {(row["method"]): row for row in compiled_rows if row["campaign"] == "n256_seed0"}
    _check(
        checks,
        "direct physical compiled-oracle boundary values",
        compiled_physical_oracle["status"] == "direct_physical_reduced_oracle_truth_table_compiled_and_verified_not_cyclic_oracle"
        and len(compiled_rows) == 12
        and all(bool(row["verification_passed"]) and bool(row["all_css_gate_pass"]) and bool(row["all_mass_balance_gate_pass"]) for row in compiled_rows)
        and compiled_n16["Sobol_QMC"]["abstract_operation_count"] == 39
        and compiled_n16["MC"]["abstract_operation_count"] == 57
        and compiled_n256["Sobol_QMC"]["abstract_operation_count"] == 1518
        and compiled_n256["MC"]["abstract_operation_count"] == 1542,
        f"rows={len(compiled_rows)}, n16={[compiled_n16[m]['abstract_operation_count'] for m in ('Sobol_QMC', 'MC')]}, n256={[compiled_n256[m]['abstract_operation_count'] for m in ('Sobol_QMC', 'MC')]}",
    )
    _check(
        checks,
        "structured empirical loader boundary values",
        structured_loader["status"] == "finite_structured_empirical_loader_compiled_and_exhaustively_verified_not_continuous_or_cyclic"
        and structured_loader["source_row_count"] == 20
        and structured_loader["address_qubits"] == 5
        and structured_loader["output_register_width"] == 44
        and structured_loader["state_preparation"]["exact_arbitrary_amplitude_rotation_upper_bound"] == 31
        and structured_loader["state_preparation"]["prepare_uncompute_rotation_upper_bound"] == 62
        and structured_loader["lookup_compilation"]["lookup_mcx_primitives"] == 400
        and structured_loader["lookup_compilation"]["lookup_x_gates"] == 2394
        and structured_loader["lookup_compilation"]["exhaustive_basis_checks"] == 64
        and structured_loader["lookup_compilation"]["verification_passed"]
        and structured_loader["all_source_css_and_mass_balance_pass"],
        f"rows={structured_loader['source_row_count']}, lookup={structured_loader['lookup_compilation']['lookup_abstract_operations']}, checks={structured_loader['lookup_compilation']['exhaustive_basis_checks']}",
    )
    _check(
        checks,
        "reversible fixed-point cycle control values",
        reversible_cycle["status"] == "reversible_fixed_point_cyclic_surrogate_compiled_and_exhaustively_verified_not_calibrated"
        and reversible_cycle["phase_count"] == 6
        and reversible_cycle["cycle_basis_states_checked"] == 65536
        and reversible_cycle["cycle_inverse_verified"]
        and reversible_cycle["controlled_cycle_forward_uncompute_event_units"] == 55,
        f"phases={reversible_cycle['phase_count']}, checks={reversible_cycle['cycle_basis_states_checked']}, units={reversible_cycle['controlled_cycle_forward_uncompute_event_units']}",
    )
    primary_gate_oracles = {
        (row["topology"], row["implementation"]): row
        for row in primary_finite_gate["oracle_comparison"]
    }
    primary_gate_totals = primary_finite_gate["total_frozen_mlae_experiment"]
    _check(
        checks,
        "primary finite event oracle primitive-gate values",
        primary_finite_gate["status"]
        == "finite_primary_event_table_synthesized_to_primitive_gates_not_continuous_psa_oracle"
        and primary_finite_gate["source_rows"] == 32
        and primary_finite_gate["address_qubits"] == 5
        and primary_finite_gate["event"]["good_rows"] == 25
        and primary_finite_gate["event"]["bad_rows"] == 7
        and abs(float(primary_finite_gate["event"]["finite_probability"]) - 0.78125) < 1e-12
        and primary_finite_gate["compiler"]["good_phase_basis_checks"] == 32
        and primary_finite_gate["compiler"]["complement_phase_basis_checks"] == 32
        and primary_gate_oracles[("all_to_all_CX", "naive_mark_25_good")]["two_qubit_gates"] == 900
        and primary_gate_oracles[("all_to_all_CX", "global_phase_equivalent_mark_7_bad")]["two_qubit_gates"] == 252
        and primary_gate_oracles[("linear_ECR", "naive_mark_25_good")]["two_qubit_gates"] == 1839
        and primary_gate_oracles[("linear_ECR", "global_phase_equivalent_mark_7_bad")]["two_qubit_gates"] == 507
        and primary_gate_totals["all_to_all_CX"]["logical_oracle_queries"] == 3500
        and abs(float(primary_gate_totals["all_to_all_CX"]["median_transpiled_two_qubit_gates"]) - 432000.0) < 1e-9
        and abs(float(primary_gate_totals["linear_ECR"]["median_transpiled_two_qubit_gates"]) - 883600.0) < 1e-9,
        f"p={primary_finite_gate['event']['finite_probability']}, CX={primary_gate_totals['all_to_all_CX']['median_transpiled_two_qubit_gates']}, ECR={primary_gate_totals['linear_ECR']['median_transpiled_two_qubit_gates']}",
    )
    ibm_preflight_by_power = {
        int(row["power"]): row for row in primary_finite_ibm_preflight["summaries"]
    }
    ibm_preflight_total_twoq = 100 * sum(
        float(row["two_qubit_median"])
        for row in primary_finite_ibm_preflight["summaries"]
    )
    _check(
        checks,
        "primary finite event oracle IBM backend preflight values",
        primary_finite_ibm_preflight["status"]
        == "open_plan_backend_compilation_completed_no_job_submitted"
        and primary_finite_ibm_preflight["backend"] == "ibm_marrakesh"
        and primary_finite_ibm_preflight["verified_plan"] == "open"
        and primary_finite_ibm_preflight["phase_minterms"] == 7
        and primary_finite_ibm_preflight["submission"]["sampler_created"] is False
        and primary_finite_ibm_preflight["submission"]["job_submitted"] is False
        and primary_finite_ibm_preflight["submission"]["job_id"] is None
        and primary_finite_ibm_preflight["submission"]["qpu_quota_consumed"] is False
        and ibm_preflight_by_power[8]["depth_median"] == 11437.0
        and ibm_preflight_by_power[8]["two_qubit_median"] == 4157.0
        and abs(ibm_preflight_total_twoq - 778800.0) < 1e-9,
        f"backend={primary_finite_ibm_preflight['backend']}, m8_depth={ibm_preflight_by_power[8]['depth_median']}, m8_2q={ibm_preflight_by_power[8]['two_qubit_median']}, total_2q={ibm_preflight_total_twoq}, submitted={primary_finite_ibm_preflight['submission']['job_submitted']}",
    )
    primary_linear_rows = {
        int(row["input_bits_per_feature"]): row
        for row in primary_linear_oracle["rows"]
    }
    _check(
        checks,
        "primary structured fixed-point linear oracle values",
        primary_linear_oracle["status"]
        == "structured_fixed_point_linear_response_oracle_compiled_loader_and_cyclic_psa_open"
        and primary_linear_oracle["policy"] == 0.427
        and primary_linear_oracle["event"]["purity_constraint_inactive_on_bounded_support"]
        and abs(float(primary_linear_oracle["event"]["bounded_support_purity_range"][0]) - 0.9998353223063741) < 1e-12
        and primary_linear_oracle["fixed_point"]["first_case_below_observed_noiseless_mlae_rmse"] == 7
        and primary_linear_rows[7]["active_features"] == 9
        and primary_linear_rows[7]["total_logical_qubits"] == 99
        and abs(float(primary_linear_rows[7]["classification_disagreement"]) - 0.002044677734375) < 1e-12
        and primary_linear_rows[7]["transpiled_depth"] == 59012
        and primary_linear_rows[7]["transpiled_cx"] == 35160
        and primary_linear_rows[7]["frozen_schedule_cx_lower_bound_excluding_loader"] == 52740000,
        f"purity_lb={primary_linear_oracle['event']['bounded_support_purity_range'][0]}, bits={primary_linear_oracle['fixed_point']['first_case_below_observed_noiseless_mlae_rmse']}, qubits={primary_linear_rows[7]['total_logical_qubits']}, CX={primary_linear_rows[7]['transpiled_cx']}",
    )
    primary_loader_rows = {
        int(row["bits_per_active_feature"]): row
        for row in primary_copula_loader["compiled_rows"]
    }
    primary_loader_accuracy = primary_copula_loader["accuracy_tier"]
    _check(
        checks,
        "primary empirical-copula dense-loader boundary values",
        primary_copula_loader["status"]
        == "exact_low_bit_empirical_copula_loader_compiled_accuracy_tier_dense_loader_intractable"
        and len(primary_copula_loader["active_features"]) == 9
        and primary_loader_rows[1]["loader_qubits"] == 9
        and primary_loader_rows[1]["transpiled_cx_prepare"] == 502
        and abs(float(primary_loader_rows[1]["event_label_disagreement"]) - 0.1546173095703125) < 1e-12
        and abs(float(primary_loader_rows[1]["statevector_fidelity_check"]) - 1.0) < 1e-12
        and primary_loader_rows[2]["loader_qubits"] == 18
        and primary_loader_rows[2]["transpiled_cx_prepare"] == 262125
        and abs(float(primary_loader_rows[2]["event_label_disagreement"]) - 0.09804534912109375) < 1e-12
        and primary_loader_accuracy["bits_per_active_feature"] == 7
        and primary_loader_accuracy["loader_qubits"] == 63
        and primary_loader_accuracy["dense_basis_states"] == 9223372036854775808
        and primary_loader_accuracy["dense_probability_table_eib"] == 64.0,
        f"CX_1bit={primary_loader_rows[1]['transpiled_cx_prepare']}, CX_2bit={primary_loader_rows[2]['transpiled_cx_prepare']}, qubits_7bit={primary_loader_accuracy['loader_qubits']}, table_EiB={primary_loader_accuracy['dense_probability_table_eib']}",
    )
    frozen_threshold = primary_threshold_activity["frozen_primary_row"]
    _check(
        checks,
        "primary joint-constraint activity sensitivity values",
        primary_threshold_activity["status"]
        == "frozen_threshold_activity_audit_not_primary_threshold_retuning"
        and primary_threshold_activity["reference_sample_size_per_scramble"] == 262144
        and primary_threshold_activity["scrambles"] == 4
        and frozen_threshold["p427_purity_marginal"] == 1.0
        and frozen_threshold["both_constraints_active_at_0427"] is False
        and frozen_threshold["selected_policy"] == "0.420"
        and frozen_threshold["selection_stable_across_scrambles"]
        and len(primary_threshold_activity["active_joint_rows_selecting_0420"]) == 8,
        f"frozen_purity={frozen_threshold['p427_purity_marginal']}, frozen_joint={frozen_threshold['p427_joint_mean']}, active_joint_rows={len(primary_threshold_activity['active_joint_rows_selecting_0420'])}",
    )
    _check(
        checks,
        "CCE frozen policy engineering and decision-margin values",
        cce_policy_decision_margin["status"]
        == "surrogate_level_engineering_allocation_and_decision_margin_not_economic_optimum"
        and cce_policy_decision_margin["selected_policy"] == 0.42
        and len(cce_policy_decision_margin["rows"]) == 3
        and abs(float(cce_policy_decision_margin["nearest_failed_probability_shortfall"]) - 0.029559612274169922) < 1e-12
        and abs(float(cce_policy_decision_margin["nearest_failed_shortfall_over_rqmc_rmse"]) - 11.907459974078037) < 1e-12
        and abs(float(cce_policy_decision_margin["nearest_failed_shortfall_over_residual_stress_half_width"]) - 7.5672607421875) < 1e-12,
        f"selected={cce_policy_decision_margin['selected_policy']}, nearest_failed={cce_policy_decision_margin['nearest_failed_policy']}, shortfall_RQMC={cce_policy_decision_margin['nearest_failed_shortfall_over_rqmc_rmse']}",
    )
    _check(
        checks,
        "CCE gate-compilation reproducibility manifest",
        cce_gate_manifest["status"] == "pass"
        and cce_gate_manifest["qpu_submission"] is False
        and cce_gate_manifest["qpu_quota_consumed"] is False
        and len(cce_gate_manifest["artifacts"]) == 37
        and all(cce_gate_manifest["validations"].values()),
        f"status={cce_gate_manifest['status']}, artifacts={len(cce_gate_manifest['artifacts'])}, validations={sum(cce_gate_manifest['validations'].values())}/{len(cce_gate_manifest['validations'])}",
    )
    _check(
        checks,
        "CCE independent public-model policy control values",
        cce_external_policy["status"]
        == "partial_external_chemistry_analog_direction_control_not_H2_selection_validation"
        and cce_external_policy["source"]["doi"] == "10.17632/564nt6pcgb.1"
        and len(cce_external_policy["rows"]) == 12
        and cce_external_policy["purity_endpoint_direction_match_count"] == 4
        and cce_external_policy["recovery_endpoint_direction_match_count"] == 3
        and cce_external_policy["event_labels_identical_within_each_scenario"]
        and cce_external_policy["event_probability_over_four_scenarios_by_policy"]
        == {"0.420": 0.5, "0.427": 0.5, "0.430": 0.5}
        and cce_external_policy["external_largest_feasible_policy"] == 0.43,
        f"rows={len(cce_external_policy['rows'])}, purity_match={cce_external_policy['purity_endpoint_direction_match_count']}/4, recovery_match={cce_external_policy['recovery_endpoint_direction_match_count']}/4, external_selection={cce_external_policy['external_largest_feasible_policy']}",
    )
    refinement_by_scenario = {
        row["scenario"]: row for row in cce_external_refinement["summaries"]
    }
    _check(
        checks,
        "CCE external policy numerical-resolution boundary",
        cce_external_refinement["status"]
        == "external_policy_direction_below_solver_metric_resolution_not_independent_selection_validation"
        and cce_external_refinement["points_per_phase"] == 4800
        and len(cce_external_refinement["rows"]) == 4
        and refinement_by_scenario["t9_vac_long_slow"]["purity_direction_preserved"]
        and refinement_by_scenario["t9_vac_long_slow"]["recovery_direction_preserved"]
        and refinement_by_scenario["t14_kCO2_low"]["purity_direction_preserved"]
        and refinement_by_scenario["t14_kCO2_low"]["recovery_direction_preserved"]
        and abs(float(refinement_by_scenario["t9_vac_long_slow"]["abs_policy_recovery_effect_over_abs_quadrature_shift"]) - 0.017181401848101224) < 1e-12
        and abs(float(refinement_by_scenario["t14_kCO2_low"]["abs_policy_recovery_effect_over_abs_quadrature_shift"]) - 0.0032613252087200194) < 1e-12,
        f"baseline_ratio={refinement_by_scenario['t9_vac_long_slow']['abs_policy_recovery_effect_over_abs_quadrature_shift']}, low_k_ratio={refinement_by_scenario['t14_kCO2_low']['abs_policy_recovery_effect_over_abs_quadrature_shift']}",
    )
    pyapep_long = cce_pyapep["long_horizon_control"]["row"]
    pyapep_gates = cce_pyapep["gates"]
    _check(
        checks,
        "CCE corrected independent pyAPEP H2 topology-boundary values",
        cce_pyapep["schema"] == "cce-independent-pyapep-h2-topology-correction-audit/v1"
        and cce_pyapep["solver"]["version"] == "0.1.8"
        and len(cce_pyapep["short_policy_screen"]["rows"]) == 3
        and cce_pyapep["short_policy_screen"]["recovery_direction_0p420_gt_0p427_gt_0p430"]
        and abs(float(pyapep_long["h2_product"]) - 0.9916662549110212) < 1e-12
        and abs(float(pyapep_long["h2_recovery_external_boundary"]) - 0.04416561223073386) < 1e-12
        and abs(float(pyapep_long["tank_supply_fraction_total"]) - 0.03163854226773907) < 1e-12
        and abs(float(pyapep_long["css_residual_final"]) - 0.001253780834234175) < 1e-15
        and pyapep_gates["counts_as_same_policy_css_validation"] is False
        and pyapep_gates["counts_as_external_h2_selection_validation"] is False,
        f"short_rows={len(cce_pyapep['short_policy_screen']['rows'])}, long_purity={pyapep_long['h2_product']}, long_recovery={pyapep_long['h2_recovery_external_boundary']}, tank={pyapep_long['tank_supply_fraction_total']}, css={pyapep_long['css_residual_final']}",
    )
    h2_best = cce_h2_resolution["best_available_pair"]
    _check(
        checks,
        "CCE independent H2 frozen-policy spacing resolution values",
        cce_h2_resolution["status"]
        == "independent_h2_policy_resolution_gate_failed_semantics_and_error"
        and cce_h2_resolution["source"]["runs"] == 13
        and cce_h2_resolution["gate"]["all_pairs_fail_5x_resolution"]
        and not cce_h2_resolution["gate"]["same_control_semantics"]
        and not cce_h2_resolution["gate"]["continuous_frozen_purity_event_identifiable"]
        and abs(float(h2_best["effect_to_group_cv_rmse"]) - 0.13318038104451815) < 1e-12
        and abs(float(h2_best["rmse_reduction_factor_needed"]) - 37.54306723547106) < 1e-10,
        f"runs={cce_h2_resolution['source']['runs']}, best_effect_RMSE={h2_best['effect_to_group_cv_rmse']}, reduction={h2_best['rmse_reduction_factor_needed']}",
    )
    _check(
        checks,
        "CCE public toPSAil/Yang H2 model and experiment boundary",
        cce_topsail_yang["status"]
        == "independent_same_chemistry_model_and_experimental_anchor_policy_mapping_open"
        and len(cce_topsail_yang["public_workbook_cases"]) == 4
        and all(cce_topsail_yang["topology_checks"].values())
        and cce_topsail_yang["event_comparison"]["yang_purity_passes_frozen_threshold"]
        and not cce_topsail_yang["event_comparison"]["yang_recovery_passes_frozen_threshold"]
        and not cce_topsail_yang["event_comparison"]["yang_joint_event_under_frozen_thresholds"]
        and not cce_topsail_yang["gate"]["same_control_semantics"]
        and not cce_topsail_yang["gate"]["counts_as_external_0420_selection_validation"]
        and cce_topsail_yang["qpu_submission"] is False,
        f"cases={len(cce_topsail_yang['public_workbook_cases'])}, joint_event={cce_topsail_yang['event_comparison']['yang_joint_event_under_frozen_thresholds']}, same_control={cce_topsail_yang['gate']['same_control_semantics']}",
    )
    prospective_curve = cce_prospective_design["conditional_surrogate_curve"]
    prospective_resolution = cce_prospective_design["independent_h2_resolution_design"]
    _check(
        checks,
        "CCE prospective decision-active policy design requirements",
        cce_prospective_design["status"]
        == "prospective_design_requirements_quantified_primary_protocol_unchanged"
        and cce_prospective_design["primary_protocol_unchanged"]
        and abs(float(prospective_curve["p50_crossing_recycle"]) - 0.4265883590354689) < 1e-12
        and abs(float(prospective_resolution["observed_support_effect_to_rmse"]) - 1.2958178156718303) < 1e-12
        and abs(float(prospective_resolution["max_recovery_rmse_for_full_support_to_pass_5x_pct_point"]) - 1.517180480512733) < 1e-12
        and not prospective_resolution["five_rmse_spacing_fits_inside_training_support"],
        f"crossing={prospective_curve['p50_crossing_recycle']}, support_effect_RMSE={prospective_resolution['observed_support_effect_to_rmse']}, required_RMSE={prospective_resolution['max_recovery_rmse_for_full_support_to_pass_5x_pct_point']}",
    )
    phase_bridge_cycle = cce_phase_map["cycle_summary"]
    _check(
        checks,
        "CCE calibrated one-cycle phase-map bridge values",
        cce_phase_map["status"]
        == "nested_leave_one_run_out_phase_map_bridge_quantified_not_reversible_cyclic_oracle"
        and cce_phase_map["source_rows"] == 20
        and cce_phase_map["phase_records"] == 160
        and cce_phase_map["state_dimension_per_bed"] == 8
        and abs(float(phase_bridge_cycle["median_joint_state_relative_l1"]) - 0.0014891907281789464) < 1e-12
        and abs(float(phase_bridge_cycle["p95_joint_state_relative_l1"]) - 0.003174356417535877) < 1e-12
        and abs(float(phase_bridge_cycle["median_pressure_abs_error_a_bar"]) - 0.007341152987833333) < 1e-12
        and abs(float(phase_bridge_cycle["median_pressure_abs_error_b_bar"]) - 0.007412661689089717) < 1e-12
        and phase_bridge_cycle["equalization_direction_match_fraction"] == 1.0
        and phase_bridge_cycle["total_negative_state_values_clipped"] == 0,
        f"median_L1={phase_bridge_cycle['median_joint_state_relative_l1']}, p95_L1={phase_bridge_cycle['p95_joint_state_relative_l1']}, pressure_A={phase_bridge_cycle['median_pressure_abs_error_a_bar']}, pressure_B={phase_bridge_cycle['median_pressure_abs_error_b_bar']}",
    )
    fixed_selected = cce_phase_map_fixed_point[
        "minimum_register_proxy_configuration_within_both_budgets"
    ]
    _check(
        checks,
        "CCE calibrated phase-map fixed-point screen values",
        cce_phase_map_fixed_point["status"]
        == "calibrated_phase_map_fixed_point_screen_not_reversible_cycle_compilation"
        and fixed_selected["bits_per_input"] == 11
        and fixed_selected["sum_bits_per_scalar_output"] == 16
        and fixed_selected["max_active_inputs"] == 14
        and fixed_selected["sequential_register_proxy_qubits"] == 170
        and abs(float(fixed_selected["p95_state_quantization_relative_l1"]) - 9.997833499654743e-05) < 1e-15
        and abs(float(fixed_selected["p95_outlet_h2_quantization_abs_error"]) - 2.2017342313790367e-05) < 1e-15,
        f"input_bits={fixed_selected['bits_per_input']}, output_bits={fixed_selected['sum_bits_per_scalar_output']}, proxy_qubits={fixed_selected['sequential_register_proxy_qubits']}",
    )
    affine_cycle = cce_phase_map_compile["full_cycle_affine_block_serial_bound"]
    _check(
        checks,
        "CCE calibrated phase-map affine primitive-gate values",
        cce_phase_map_compile["status"]
        == "calibrated_affine_variable_terms_compiled_cycle_oracle_still_open"
        and affine_cycle["scalar_blocks"] == 72
        and affine_cycle["max_logical_qubits_reusing_scalar_workspace"] == 186
        and affine_cycle["serial_forward_depth"] == 8257830
        and affine_cycle["serial_forward_cx"] == 4183986
        and affine_cycle["serial_clean_compute_uncompute_cx"] == 8367972,
        f"blocks={affine_cycle['scalar_blocks']}, qubits={affine_cycle['max_logical_qubits_reusing_scalar_workspace']}, forward_CX={affine_cycle['serial_forward_cx']}, clean_CX={affine_cycle['serial_clean_compute_uncompute_cx']}",
    )
    small_oracle = cce_small_e2e["primitive_gate_compile"]["clean_phase_oracle"]
    small_verify = cce_small_e2e["verification"]
    _check(
        checks,
        "CCE small coherent end-to-end connection control values",
        cce_small_e2e["status"]
        == "small_structural_end_to_end_oracle_compiled_and_coherently_verified_not_calibrated_cycle"
        and cce_small_e2e["registers"]["total_logical_qubits"] == 15
        and small_oracle["depth_all_to_all"] == 405
        and small_oracle["cx"] == 304
        and small_verify["basis_states_checked_in_one_coherent_superposition"] == 64
        and small_verify["all_work_and_event_qubits_clean_after_uncompute"]
        and small_verify["all_event_phase_labels_match"]
        and float(small_verify["phase_oracle_max_abs_amplitude_error"]) < 1e-12,
        f"qubits={cce_small_e2e['registers']['total_logical_qubits']}, depth={small_oracle['depth_all_to_all']}, CX={small_oracle['cx']}, error={small_verify['phase_oracle_max_abs_amplitude_error']}",
    )
    primary_ledger_event = cce_primary_phase_ledger["event"]
    primary_ledger_verify = cce_primary_phase_ledger["verification"]
    _check(
        checks,
        "CCE primary final-cycle phase ledger event replay values",
        cce_primary_phase_ledger["status"]
        == "frozen_primary_spatial_tank_final_cycle_phase_ledger_replayed_event_observable_not_reversible"
        and cce_primary_phase_ledger["sample_count"] == 32
        and primary_ledger_event["joint_event_count"] == 25
        and primary_ledger_verify["css_pass_count"] == 32
        and primary_ledger_verify["all_phase_counts_complete"]
        and primary_ledger_verify["all_event_outputs_replay_source_csv"]
        and float(primary_ledger_verify["max_replay_purity_abs_error"]) < 3e-15
        and float(primary_ledger_verify["max_replay_recovery_abs_error"]) < 1.4e-10
        and float(primary_ledger_verify["max_equalization_pair_mass_residual_mol"]) < 1.5e-14
        and cce_primary_phase_ledger["qpu_submission"] is False
        and "plant validation" in cce_primary_phase_ledger["claim_boundary"]["unsupported"],
        f"runs={cce_primary_phase_ledger['sample_count']}, event={primary_ledger_event['joint_event_count']}/32, purity_replay={primary_ledger_verify['max_replay_purity_abs_error']}, recovery_replay={primary_ledger_verify['max_replay_recovery_abs_error']}",
    )
    physical_horizon = cce_primary_physical_css["physical_horizon"]
    physical_precision = cce_primary_physical_css["fixed_point_screen"]["selected"]
    physical_registers = cce_primary_physical_css["reversible_register_accounting"]
    _check(
        checks,
        "CCE primary physical tank/spatial CSS horizon and register accounting",
        cce_primary_physical_css["status"]
        == "physical_tank_spatial_css_horizon_and_register_accounting_quantified_transport_unitary_open"
        and cce_primary_physical_css["source"]["runs"] == 32
        and cce_primary_physical_css["source"]["total_cycle_boundary_state_scalars"] == 85
        and physical_horizon["strict_css_final_pass_count"] == 32
        and physical_horizon["l1_css_final_pass_count"] == 32
        and physical_horizon["max_joint_strict_css_event_horizon"] == 68
        and physical_precision["bits_per_scalar"] == 16
        and physical_precision["safe_fixed_horizon"] == 85
        and physical_precision["final_event_label_match_count"] == 32
        and physical_registers["single_physical_state_data_qubits"] == 1360
        and physical_registers["out_of_place_current_plus_next_state_data_qubits"] == 2720
        and physical_registers["out_of_place_current_next_state_plus_raw_event_stream_data_qubits"] == 2880
        and "not a universal circuit lower bound" in physical_registers["interpretation"]
        and cce_primary_physical_css["qpu_submission"] is False,
        f"physical_horizon={physical_horizon['max_joint_strict_css_event_horizon']}, bits={physical_precision['bits_per_scalar']}, safe_horizon={physical_precision['safe_fixed_horizon']}, out_of_place_qubits={physical_registers['out_of_place_current_next_state_plus_raw_event_stream_data_qubits']}",
    )
    qstar_selected = cce_primary_qstar_microkernel["selected"]
    _check(
        checks,
        "CCE competitive-Langmuir reversible microkernel values",
        cce_primary_qstar_microkernel["status"]
        == "competitive_langmuir_numerator_denominator_preparation_compiled_reciprocal_ode_open"
        and cce_primary_qstar_microkernel["physical_state_source"]["cell_states_evaluated"] == 25856
        and cce_primary_qstar_microkernel["equation"]["normalized_integer_affinity_weights"] == [3, 255, 134, 60, 144]
        and qstar_selected["bits_per_pressure_and_composition"] == 18
        and qstar_selected["logical_qubits"] == 266
        and qstar_selected["forward_depth_all_to_all"] == 186885
        and qstar_selected["forward_cx"] == 127112
        and qstar_selected["clean_compute_uncompute_cx"] == 254224
        and float(qstar_selected["denominator_p95_relative_error"]) < 1.0e-3
        and float(qstar_selected["co2_qstar_p95_relative_error"]) < 5.0e-2
        and qstar_selected["nonzero_co2_numerator_zeroed_fraction"] == 0.0
        and cce_primary_qstar_microkernel["qpu_submission"] is False,
        f"states={cce_primary_qstar_microkernel['physical_state_source']['cell_states_evaluated']}, bits={qstar_selected['bits_per_pressure_and_composition']}, qubits={qstar_selected['logical_qubits']}, forward_CX={qstar_selected['forward_cx']}, qstar_p95={qstar_selected['co2_qstar_p95_relative_error']}",
    )
    qstar_ldf_selected = cce_primary_qstar_ldf_microstep["selected"]
    qstar_ldf_resources = cce_primary_qstar_ldf_microstep["compiled_clean_microstep"]
    _check(
        checks,
        "CCE competitive-Langmuir reciprocal and CO2 LDF clean microstep values",
        cce_primary_qstar_ldf_microstep["status"]
        == "competitive_langmuir_reciprocal_and_co2_ldf_microstep_compiled_full_phase_cycle_open"
        and cce_primary_qstar_ldf_microstep["physical_state_source"]["cell_states_evaluated"] == 25856
        and qstar_ldf_selected["denominator_address_bits"] == 5
        and qstar_ldf_selected["arithmetic_bits"] == 24
        and qstar_ldf_selected["reciprocal_segments"] == 32
        and float(qstar_ldf_selected["qstar_p95_relative_error"]) < 5.0e-2
        and float(qstar_ldf_selected["ldf_next_p95_relative_error"]) < 1.0e-3
        and qstar_ldf_selected["nonzero_qstar_erased_fraction"] == 0.0
        and qstar_ldf_resources["logical_qubits"] == 515
        and qstar_ldf_resources["depth_all_to_all"] == 1919788
        and qstar_ldf_resources["cx"] == 1225138
        and qstar_ldf_resources["measurement"] == 0
        and qstar_ldf_resources["reset"] == 0
        and cce_primary_qstar_ldf_microstep["qpu_submission"] is False,
        f"states={cce_primary_qstar_ldf_microstep['physical_state_source']['cell_states_evaluated']}, address_bits={qstar_ldf_selected['denominator_address_bits']}, arithmetic_bits={qstar_ldf_selected['arithmetic_bits']}, qubits={qstar_ldf_resources['logical_qubits']}, CX={qstar_ldf_resources['cx']}",
    )
    all_component_rows = {
        row["component"]: row for row in cce_primary_all_component_ldf["components"]
    }
    all_component_sequential = cce_primary_all_component_ldf[
        "sequential_five_component_accounting"
    ]
    _check(
        checks,
        "CCE all-component competitive-Langmuir/LDF clean microstep values",
        cce_primary_all_component_ldf["status"]
        == "all_five_competitive_langmuir_ldf_microsteps_compiled_transport_valve_tank_cycle_open"
        and cce_primary_all_component_ldf["physical_state_source"]["cell_states_evaluated"] == 25856
        and set(all_component_rows) == {"H2", "CO2", "CH4", "CO", "N2"}
        and all(
            row["selected"]["passes_all_component_precision_gate"]
            and row["selected"]["loading_input_overflow_fraction"] == 0.0
            and row["selected"]["nonzero_qstar_erased_fraction"] == 0.0
            and row["compiled_clean_microstep"]["measurement"] == 0
            and row["compiled_clean_microstep"]["reset"] == 0
            for row in all_component_rows.values()
        )
        and all_component_rows["H2"]["selected"]["arithmetic_bits"] == 20
        and all_component_rows["H2"]["selected"]["denominator_address_bits"] == 8
        and all_component_rows["CO2"]["selected"]["arithmetic_bits"] == 24
        and all_component_rows["CO2"]["selected"]["denominator_address_bits"] == 5
        and all_component_sequential["logical_qubits"] == 675
        and all_component_sequential["cx_additive_module_bound"] == 6547362
        and cce_primary_all_component_ldf["qpu_submission"] is False,
        f"components={len(all_component_rows)}, qubits={all_component_sequential['logical_qubits']}, additive_CX={all_component_sequential['cx_additive_module_bound']}",
    )
    product_valve_selected = cce_primary_product_boundary["selected_valve"]
    product_valve_resources = cce_primary_product_boundary["compiled_clean_valve_component_flux"]
    product_tank_selected = cce_primary_product_boundary["selected_tank"]
    product_tank_accounting = cce_primary_product_boundary["five_component_tank_accounting"]
    _check(
        checks,
        "CCE product-boundary valve flux and recycle-tank clean module values",
        cce_primary_product_boundary["status"]
        == "product_valve_flux_and_recycle_tank_capacity_modules_compiled_internal_transport_pressure_cycle_open"
        and cce_primary_product_boundary["valve_state_source"]["states"] == 6464
        and cce_primary_product_boundary["valve_state_source"]["active_states"] == 3232
        and product_valve_selected["valve_address_bits"] == 12
        and product_valve_selected["flow_bits"] == 20
        and product_valve_selected["passes_declared_precision_gate"]
        and product_valve_selected["active_label_mismatch_fraction"] == 0.0
        and max(row["nonzero_flux_erased_fraction"] for row in product_valve_selected["component_metrics"]) == 0.0
        and product_valve_resources["logical_qubits"] == 288
        and product_valve_resources["depth_all_to_all"] == 1379148
        and product_valve_resources["cx"] == 800762
        and product_valve_resources["measurement"] == 0
        and product_valve_resources["reset"] == 0
        and cce_primary_product_boundary["tank_record_source"]["product_recycle_records"] == 64
        and product_tank_selected["amount_bits"] == 24
        and product_tank_selected["fraction_bits"] == 14
        and product_tank_selected["passes_declared_precision_gate"]
        and product_tank_selected["nonzero_recycle_erased_fraction"] == 0.0
        and product_tank_selected["capacity_flag_mismatch_fraction"] == 0.0
        and product_tank_accounting["logical_qubits"] == 677
        and product_tank_accounting["cx_additive_module_bound"] == 1043990
        and cce_primary_product_boundary["qpu_submission"] is False,
        f"valve={product_valve_resources['logical_qubits']}q/{product_valve_resources['cx']}CX, tank={product_tank_accounting['logical_qubits']}q/{product_tank_accounting['cx_additive_module_bound']}CX",
    )
    product_boundary_balance_components = {
        row["component"]: row
        for row in cce_primary_product_boundary_balance["components"]
    }
    product_boundary_balance_resources = cce_primary_product_boundary_balance[
        "compiled_clean_product_valve_boundary_balance"
    ]
    product_boundary_balance_layout = cce_primary_product_boundary_balance[
        "direct_composition_layout"
    ]
    _check(
        checks,
        "CCE direct product-valve to boundary-cell balance composition values",
        cce_primary_product_boundary_balance["status"]
        == "five_component_product_valve_to_boundary_balance_directly_composed_normalization_phase_open"
        and cce_primary_product_boundary_balance["physical_state_source"]["product_boundary_states"] == 6464
        and cce_primary_product_boundary_balance["physical_state_source"]["component_balances"] == 32320
        and cce_primary_product_boundary_balance["physical_state_source"]["active_valve_states"] == 3232
        and set(product_boundary_balance_components) == {"H2", "CO2", "CH4", "CO", "N2"}
        and all(
            row["selected"]["input_bits_per_nonvalve_term"] == 16
            and row["selected"]["valve_flux_input_bits"] == 20
            and row["selected"]["next_output_bits"] == 20
            and row["selected"]["passes_product_boundary_balance_precision_gate"]
            and row["selected"]["maximum_nonzero_nonvalve_term_erased_fraction"] == 0.0
            and row["selected"]["nonzero_valve_flux_erased_by_valve_fraction"] == 0.0
            and row["selected"]["nonzero_valve_flux_erased_by_balance_conversion_fraction"] == 0.0
            and row["selected"]["negative_sum_underflow_fraction"] == 0.0
            and row["selected"]["next_output_overflow_fraction"] == 0.0
            for row in product_boundary_balance_components.values()
        )
        and product_boundary_balance_layout["retained_input_output_qubits"] == 528
        and product_boundary_balance_layout["cleared_workspace_qubits"] == 314
        and product_boundary_balance_resources["logical_qubits"] == 842
        and product_boundary_balance_resources["depth_all_to_all"] == 3285605
        and product_boundary_balance_resources["cx"] == 2348388
        and product_boundary_balance_resources["measurement"] == 0
        and product_boundary_balance_resources["reset"] == 0
        and cce_primary_product_boundary_balance["qpu_submission"] is False,
        f"states={cce_primary_product_boundary_balance['physical_state_source']['product_boundary_states']}, balances={cce_primary_product_boundary_balance['physical_state_source']['component_balances']}, resources={product_boundary_balance_resources['logical_qubits']}q/{product_boundary_balance_resources['cx']}CX",
    )
    pressure_selected = cce_primary_internal_transport["selected_pressure"]
    face_selected = cce_primary_internal_transport["selected_face"]
    pressure_resources = cce_primary_internal_transport["compiled_clean_pressure_reconstruction"]
    face_resources = cce_primary_internal_transport["compiled_clean_oriented_internal_face_transport"]
    transport_accounting = cce_primary_internal_transport["pressure_to_face_modular_accounting"]
    _check(
        checks,
        "CCE pressure reconstruction and oriented internal-face transport values",
        cce_primary_internal_transport["status"]
        == "pressure_reconstruction_and_oriented_internal_face_transport_compiled_composition_normalization_phase_cycle_open"
        and cce_primary_internal_transport["physical_state_source"]["cell_states"] == 25856
        and cce_primary_internal_transport["physical_state_source"]["internal_faces"] == 19392
        and pressure_selected["gas_bits_per_component"] == 18
        and pressure_selected["pressure_output_bits"] == 20
        and pressure_selected["passes_pressure_precision_gate"]
        and pressure_selected["maximum_component_nonzero_erased_fraction"] == 0.0
        and pressure_selected["physical_pressure_output_overflow_fraction"] == 0.0
        and face_selected["flow_effective_bits"] == 24
        and face_selected["flow_register_bits"] == 28
        and face_selected["composition_bits_per_component"] == 20
        and face_selected["passes_oriented_face_precision_gate"]
        and face_selected["negative_exact_face_count"] == 0
        and face_selected["reconstructed_pressure_difference_underflow_fraction"] == 0.0
        and face_selected["active_label_mismatch_fraction"] == 0.0
        and max(row["nonzero_flux_erased_fraction"] for row in face_selected["component_metrics"]) == 0.0
        and pressure_resources["logical_qubits"] == 152
        and pressure_resources["depth_all_to_all"] == 158331
        and pressure_resources["cx"] == 93764
        and pressure_resources["measurement"] == 0
        and pressure_resources["reset"] == 0
        and face_resources["logical_qubits"] == 404
        and face_resources["depth_all_to_all"] == 2237277
        and face_resources["cx"] == 1340390
        and face_resources["measurement"] == 0
        and face_resources["reset"] == 0
        and transport_accounting["logical_qubits"] == 584
        and transport_accounting["cx_additive_module_bound"] == 1527918
        and cce_primary_internal_transport["qpu_submission"] is False,
        f"pressure={pressure_resources['logical_qubits']}q/{pressure_resources['cx']}CX, face={face_resources['logical_qubits']}q/{face_resources['cx']}CX, modular={transport_accounting['logical_qubits']}q/{transport_accounting['cx_additive_module_bound']}CX",
    )
    internal_face_balance_components = {
        row["component"]: row
        for row in cce_primary_internal_face_balance["components"]
    }
    internal_face_balance_resources = cce_primary_internal_face_balance[
        "compiled_clean_internal_face_balance"
    ]
    internal_face_balance_layout = cce_primary_internal_face_balance[
        "direct_composition_layout"
    ]
    _check(
        checks,
        "CCE direct pressure-to-two-face-to-interior-cell balance values",
        cce_primary_internal_face_balance["status"]
        == "three_pressure_two_internal_face_five_component_balance_directly_composed_normalization_ldf_phase_open"
        and cce_primary_internal_face_balance["physical_state_source"]["interior_cell_states"] == 12928
        and cce_primary_internal_face_balance["physical_state_source"]["component_balances"] == 64640
        and set(internal_face_balance_components) == {"H2", "CO2", "CH4", "CO", "N2"}
        and all(
            row["selected"]["input_bits_per_nonface_term"] == 16
            and row["selected"]["face_flux_input_bits"] == 28
            and row["selected"]["next_output_bits"] == 20
            and row["selected"]["balance_scale_headroom_factor"] == 1.001
            and row["selected"]["passes_internal_face_balance_precision_gate"]
            and row["selected"]["maximum_nonzero_nonface_term_erased_fraction"] == 0.0
            and row["selected"]["nonzero_direct_face_flux_erased_fraction"] == 0.0
            and row["selected"]["positive_sum_overflow_fraction"] == 0.0
            and row["selected"]["negative_sum_underflow_fraction"] == 0.0
            and row["selected"]["next_output_overflow_fraction"] == 0.0
            for row in internal_face_balance_components.values()
        )
        and cce_primary_internal_face_balance["face_diagnostics_on_interior_cell_pairs"]["pressure_difference_underflow_fraction"] == 0.0
        and cce_primary_internal_face_balance["face_diagnostics_on_interior_cell_pairs"]["nonzero_face_flux_erased_fraction"] == 0.0
        and internal_face_balance_layout["retained_input_output_qubits"] == 810
        and internal_face_balance_layout["cleared_workspace_qubits"] == 698
        and internal_face_balance_resources["logical_qubits"] == 1508
        and internal_face_balance_resources["depth_all_to_all"] == 12250291
        and internal_face_balance_resources["cx"] == 8328622
        and internal_face_balance_resources["measurement"] == 0
        and internal_face_balance_resources["reset"] == 0
        and cce_primary_internal_face_balance["qpu_submission"] is False,
        f"states={cce_primary_internal_face_balance['physical_state_source']['interior_cell_states']}, balances={cce_primary_internal_face_balance['physical_state_source']['component_balances']}, resources={internal_face_balance_resources['logical_qubits']}q/{internal_face_balance_resources['cx']}CX",
    )
    normalized_selected = cce_primary_normalized_internal_face_balance[
        "selected_normalization"
    ]
    normalized_balances = {
        row["component"]: row
        for row in cce_primary_normalized_internal_face_balance[
            "selected_balance_rows"
        ]
    }
    normalized_face_diagnostics = cce_primary_normalized_internal_face_balance[
        "propagated_face_diagnostics"
    ]
    normalizer_resources = cce_primary_normalized_internal_face_balance[
        "compiled_clean_composition_normalizer"
    ]
    normalized_direct_resources = cce_primary_normalized_internal_face_balance[
        "compiled_clean_normalized_internal_face_balance"
    ]
    normalized_direct_layout = cce_primary_normalized_internal_face_balance[
        "direct_composition_layout"
    ]
    _check(
        checks,
        "CCE direct gas-normalization-to-two-face-to-interior-cell balance values",
        cce_primary_normalized_internal_face_balance["status"]
        == "gas_inventory_normalization_pressure_two_internal_face_five_component_balance_directly_composed_ldf_phase_open"
        and cce_primary_normalized_internal_face_balance["physical_state_source"][
            "normalization_cell_states"
        ]
        == 25856
        and cce_primary_normalized_internal_face_balance["physical_state_source"][
            "interior_cell_states"
        ]
        == 12928
        and cce_primary_normalized_internal_face_balance["physical_state_source"][
            "component_balances"
        ]
        == 64640
        and normalized_selected["amount_bits"] == 22
        and normalized_selected["reciprocal_bits"] == 22
        and normalized_selected["address_bits"] == 8
        and normalized_selected["reciprocal_segments"] == 256
        and normalized_selected["passes_composition_precision_gate"]
        and normalized_selected["passes_end_to_end_precision_gate"]
        and normalized_selected["maximum_nonzero_composition_erased_fraction"]
        == 0.0
        and normalized_selected["composition_output_overflow_fraction"] == 0.0
        and max(normalized_selected["composition_p95_absolute_error"].values())
        < 2.1e-4
        and max(normalized_selected["composition_max_absolute_error"].values())
        < 3.2e-4
        and normalized_face_diagnostics["passes_propagated_face_precision_gate"]
        and normalized_face_diagnostics["pressure_difference_underflow_fraction"]
        == 0.0
        and normalized_face_diagnostics["nonzero_face_flux_erased_fraction"]
        == 0.0
        and set(normalized_balances) == {"H2", "CO2", "CH4", "CO", "N2"}
        and all(
            row["input_bits_per_nonface_term"] == 16
            and row["face_flux_input_bits"] == 28
            and row["next_output_bits"] == 20
            and row["passes_internal_face_balance_precision_gate"]
            for row in normalized_balances.values()
        )
        and normalizer_resources["logical_qubits"] == 333
        and normalizer_resources["depth_all_to_all"] == 2153892
        and normalizer_resources["cx"] == 1340232
        and normalizer_resources["measurement"] == 0
        and normalizer_resources["reset"] == 0
        and normalized_direct_layout["retained_input_output_qubits"] == 610
        and normalized_direct_layout["cleared_workspace_qubits"] == 1041
        and normalized_direct_resources["logical_qubits"] == 1651
        and normalized_direct_resources["depth_all_to_all"] == 22143683
        and normalized_direct_resources["cx"] == 14667150
        and normalized_direct_resources["measurement"] == 0
        and normalized_direct_resources["reset"] == 0
        and cce_primary_normalized_internal_face_balance["qpu_submission"] is False,
        f"normalization_states={cce_primary_normalized_internal_face_balance['physical_state_source']['normalization_cell_states']}, normalizer={normalizer_resources['logical_qubits']}q/{normalizer_resources['cx']}CX, direct={normalized_direct_resources['logical_qubits']}q/{normalized_direct_resources['cx']}CX",
    )
    cell_components = {
        row["component"]: row for row in cce_primary_cell_balance["components"]
    }
    cell_accounting = cce_primary_cell_balance["sequential_five_component_accounting"]
    expected_cell_resources = {
        "H2": (16, 20, 204, 65228, 70584),
        "CO2": (16, 20, 199, 86506, 74100),
        "CH4": (16, 20, 199, 86638, 72642),
        "CO": (16, 20, 198, 82644, 68676),
        "N2": (16, 22, 209, 97719, 80800),
    }
    _check(
        checks,
        "CCE five-component interior-cell gas-balance accumulator values",
        cce_primary_cell_balance["status"]
        == "five_component_interior_cell_balance_accumulators_compiled_sign_extraction_phase_cycle_open"
        and cce_primary_cell_balance["physical_state_source"]["interior_cell_samples"] == 12928
        and cce_primary_cell_balance["physical_state_source"]["component_balance_samples"] == 64640
        and cce_primary_cell_balance["physical_state_source"]["negative_exact_next_count"] == 0
        and set(cell_components) == set(expected_cell_resources)
        and all(
            row["selected"]["input_bits_per_term"] == expected_cell_resources[name][0]
            and row["selected"]["next_output_bits"] == expected_cell_resources[name][1]
            and row["selected"]["passes_cell_balance_precision_gate"]
            and row["selected"]["maximum_nonzero_term_erased_fraction"] == 0.0
            and row["selected"]["positive_sum_overflow_fraction"] == 0.0
            and row["selected"]["negative_sum_underflow_fraction"] == 0.0
            and row["selected"]["next_output_overflow_fraction"] == 0.0
            and row["compiled_clean_balance"]["logical_qubits"] == expected_cell_resources[name][2]
            and row["compiled_clean_balance"]["depth_all_to_all"] == expected_cell_resources[name][3]
            and row["compiled_clean_balance"]["cx"] == expected_cell_resources[name][4]
            and row["compiled_clean_balance"]["measurement"] == 0
            and row["compiled_clean_balance"]["reset"] == 0
            for name, row in cell_components.items()
        )
        and cell_accounting["logical_qubits"] == 609
        and cell_accounting["retained_term_and_next_gas_qubits"] == 502
        and cell_accounting["shared_workspace_qubits"] == 107
        and cell_accounting["cx_additive_module_bound"] == 366802
        and cell_accounting["depth_all_to_all_additive_module_bound"] == 418735
        and cce_primary_cell_balance["qpu_submission"] is False,
        f"samples={cce_primary_cell_balance['physical_state_source']['component_balance_samples']}, components={len(cell_components)}, sequential={cell_accounting['logical_qubits']}q/{cell_accounting['cx_additive_module_bound']}CX",
    )
    loading_sign_components = {
        row["component"]: row
        for row in cce_primary_loading_sign_balance["components"]
    }
    loading_sign_expected = {
        "H2": (20, 26, 211, 34534, 383, 104828, 139600),
        "CO2": (24, 26, 227, 97950, 394, 322549, 269948),
        "CH4": (20, 32, 261, 128580, 428, 424031, 329738),
        "CO": (20, 32, 265, 137534, 431, 452936, 343680),
        "N2": (20, 30, 253, 124088, 430, 409563, 328916),
    }
    loading_sign_accounting = cce_primary_loading_sign_balance[
        "sequential_five_component_accounting"
    ]
    _check(
        checks,
        "CCE loading-sign extraction and directly composed cell-balance values",
        cce_primary_loading_sign_balance["status"]
        == "five_component_loading_sign_solid_conversion_cell_balance_compiled_upstream_ldf_face_phase_open"
        and cce_primary_loading_sign_balance["physical_state_source"]["interior_cell_samples"] == 12928
        and cce_primary_loading_sign_balance["physical_state_source"]["component_balance_samples"] == 64640
        and cce_primary_loading_sign_balance["small_width_structural_check"]["basis_pairs"] == 64
        and cce_primary_loading_sign_balance["small_width_structural_check"]["mismatches"] == 0
        and cce_primary_loading_sign_balance["small_width_structural_check"]["dirty_workspace_pairs"] == 0
        and cce_primary_loading_sign_balance["small_width_structural_check"]["passes"]
        and set(loading_sign_components) == set(loading_sign_expected)
        and all(
            row["previous_standalone_ldf_loading_bits"] == loading_sign_expected[name][0]
            and row["selected"]["loading_bits"] == loading_sign_expected[name][1]
            and row["selected"]["passes_loading_sign_balance_interface_gate"]
            and row["selected"]["branch_mismatch_fraction"] == 0.0
            and row["selected"]["nonzero_change_erased_fraction"] == 0.0
            and row["selected"]["zero_change_false_activation_fraction"] == 0.0
            and row["selected"]["adsorption_term_overflow_fraction"] == 0.0
            and row["selected"]["desorption_term_overflow_fraction"] == 0.0
            and row["selected"]["negative_sum_underflow_fraction"] == 0.0
            and row["selected"]["next_output_overflow_fraction"] == 0.0
            and row["compiled_clean_loading_to_terms"]["logical_qubits"] == loading_sign_expected[name][2]
            and row["compiled_clean_loading_to_terms"]["cx"] == loading_sign_expected[name][3]
            and row["compiled_integrated_loading_sign_cell_balance"]["logical_qubits"] == loading_sign_expected[name][4]
            and row["compiled_integrated_loading_sign_cell_balance"]["depth_all_to_all"] == loading_sign_expected[name][5]
            and row["compiled_integrated_loading_sign_cell_balance"]["cx"] == loading_sign_expected[name][6]
            and row["compiled_integrated_loading_sign_cell_balance"]["measurement"] == 0
            and row["compiled_integrated_loading_sign_cell_balance"]["reset"] == 0
            for name, row in loading_sign_components.items()
        )
        and loading_sign_accounting["logical_qubits"] == 934
        and loading_sign_accounting["retained_input_output_qubits"] == 634
        and loading_sign_accounting["shared_workspace_qubits"] == 300
        and loading_sign_accounting["cx_additive_module_bound"] == 1411882
        and loading_sign_accounting["depth_all_to_all_additive_module_bound"] == 1713907
        and cce_primary_loading_sign_balance["qpu_submission"] is False,
        f"bits={[loading_sign_components[name]['selected']['loading_bits'] for name in ('H2','CO2','CH4','CO','N2')]}, sequential={loading_sign_accounting['logical_qubits']}q/{loading_sign_accounting['cx_additive_module_bound']}CX",
    )
    ldf_sign_components = {
        row["component"]: row for row in cce_primary_ldf_sign_balance["components"]
    }
    ldf_sign_expected = {
        "H2": (20, 26, 8, 530, 3427063, 2107572, 861, 7871973, 4991534, 636790),
        "CO2": (24, 26, 5, 527, 1966877, 1252758, 869, 4949239, 3412254, 636790),
        "CH4": (20, 32, 4, 562, 2011830, 1279980, 926, 5128934, 3579478, 689780),
        "CO": (20, 32, 4, 562, 2011830, 1279980, 929, 5128934, 3593420, 689780),
        "N2": (20, 30, 4, 550, 1989222, 1252708, 920, 5030941, 3506166, 671834),
    }
    ldf_sign_accounting = cce_primary_ldf_sign_balance[
        "sequential_five_component_accounting"
    ]
    _check(
        checks,
        "CCE direct widened-LDF to loading-sign and cell-balance composition values",
        cce_primary_ldf_sign_balance["status"]
        == "five_component_register_compatible_ldf_sign_balance_composed_face_normalization_phase_open"
        and cce_primary_ldf_sign_balance["physical_state_source"]["ldf_precision_cell_states"] == 25856
        and cce_primary_ldf_sign_balance["physical_state_source"]["balance_interface_component_samples"] == 64640
        and set(ldf_sign_components) == set(ldf_sign_expected)
        and all(
            row["previous_standalone_loading_bits"] == ldf_sign_expected[name][0]
            and row["register_compatible_loading_bits"] == ldf_sign_expected[name][1]
            and row["denominator_address_bits"] == ldf_sign_expected[name][2]
            and row["widened_ldf_precision"]["passes_all_component_precision_gate"]
            and row["widened_ldf_precision"]["nonzero_qstar_erased_fraction"] == 0.0
            and row["widened_ldf_precision"]["loading_input_overflow_fraction"] == 0.0
            and row["compiled_widened_clean_ldf_microstep"]["logical_qubits"] == ldf_sign_expected[name][3]
            and row["compiled_widened_clean_ldf_microstep"]["depth_all_to_all"] == ldf_sign_expected[name][4]
            and row["compiled_widened_clean_ldf_microstep"]["cx"] == ldf_sign_expected[name][5]
            and row["compiled_clean_ldf_sign_cell_balance"]["logical_qubits"] == ldf_sign_expected[name][6]
            and row["compiled_clean_ldf_sign_cell_balance"]["depth_all_to_all"] == ldf_sign_expected[name][7]
            and row["compiled_clean_ldf_sign_cell_balance"]["cx"] == ldf_sign_expected[name][8]
            and row["direct_minus_additive_cx"] == ldf_sign_expected[name][9]
            and row["compiled_clean_ldf_sign_cell_balance"]["measurement"] == 0
            and row["compiled_clean_ldf_sign_cell_balance"]["reset"] == 0
            for name, row in ldf_sign_components.items()
        )
        and ldf_sign_accounting["logical_qubits"] == 1317
        and ldf_sign_accounting["shared_process_pressure_composition_input_qubits"] == 108
        and ldf_sign_accounting["retained_input_output_qubits"] == 596
        and ldf_sign_accounting["shared_workspace_qubits"] == 721
        and ldf_sign_accounting["cx_additive_module_bound"] == 19082852
        and ldf_sign_accounting["depth_all_to_all_additive_module_bound"] == 28110021
        and cce_primary_ldf_sign_balance["qpu_submission"] is False,
        f"bits={[ldf_sign_components[name]['register_compatible_loading_bits'] for name in ('H2','CO2','CH4','CO','N2')]}, sequential={ldf_sign_accounting['logical_qubits']}q/{ldf_sign_accounting['cx_additive_module_bound']}CX",
    )
    joint_components = {
        row["component"]: row
        for row in cce_primary_joint_normalized_transport_ldf_balance[
            "selected_components"
        ]
    }
    joint_resources = {
        row["component"]: row
        for row in cce_primary_joint_normalized_transport_ldf_balance[
            "componentwise_compiled_direct_paths"
        ]
    }
    joint_expected = {
        "H2": (9, 26, 11, 1944, 59186552, 35947274),
        "CO2": (8, 26, 9, 1960, 35145371, 22128076),
        "CH4": (9, 38, 10, 2033, 46501180, 28558642),
        "CO": (7, 36, 8, 2039, 32668327, 20709266),
        "N2": (6, 36, 8, 2033, 32612294, 20670468),
    }
    joint_upper = cce_primary_joint_normalized_transport_ldf_balance[
        "compiled_clean_joint_specialized_circuit"
    ]
    _check(
        checks,
        "CCE direct normalized transport LDF component paths and upper bound",
        cce_primary_joint_normalized_transport_ldf_balance["status"]
        == "parameter_specialized_componentwise_direct_paths_compiled_additive_upper_bound_monolithic_open"
        and cce_primary_joint_normalized_transport_ldf_balance[
            "joint_ldf_input_bits_per_pressure_and_composition"
        ]
        == 20
        and set(joint_components) == set(joint_expected)
        and set(joint_resources) == set(joint_expected)
        and all(
            joint_components[name]["factor_bits"] == expected[0]
            and joint_components[name]["loading_bits"] == expected[1]
            and joint_components[name]["address_bits"] == expected[2]
            and joint_components[name]["affinity_bits"] == 8
            and joint_components[name]["coefficient_bits"] == 8
            and joint_components[name]["passes_joint_balance_gate"]
            and joint_components[name]["nonzero_transfer_erased_fraction"] == 0.0
            and joint_resources[name]["logical_qubits"] == expected[3]
            and joint_resources[name]["depth_all_to_all"] == expected[4]
            and joint_resources[name]["cx"] == expected[5]
            and joint_resources[name]["measurement"] == 0
            and joint_resources[name]["reset"] == 0
            for name, expected in joint_expected.items()
        )
        and joint_upper["logical_qubits_peak"] == 2039
        and joint_upper["depth_all_to_all_additive_upper_bound"] == 206113724
        and joint_upper["cx_additive_upper_bound"] == 128013726
        and joint_upper["monolithic_five_component_transpile"] is False
        and cce_primary_joint_normalized_transport_ldf_balance["qpu_submission"]
        is False,
        f"paths={len(joint_resources)}, peak={joint_upper['logical_qubits_peak']}q, upper={joint_upper['cx_additive_upper_bound']}CX",
    )
    product_ldf_components = {
        row["component"]: row
        for row in cce_primary_product_ldf_valve_balance["selected_components"]
    }
    product_ldf_resources = {
        row["component"]: row
        for row in cce_primary_product_ldf_valve_balance["componentwise_compiled_direct_paths"]
    }
    product_ldf_expected = {
        "H2": (26, 11, 8, 1074, 39624718, 23836418),
        "CO2": (26, 9, 10, 1072, 15670199, 10060060),
        "CH4": (38, 10, 8, 1188, 26823018, 16433266),
        "CO": (38, 9, 8, 1195, 17641524, 11248412),
        "N2": (36, 11, 8, 1174, 45153788, 26810396),
    }
    product_ldf_upper = cce_primary_product_ldf_valve_balance[
        "conservative_five_component_upper_bound"
    ]
    _check(
        checks,
        "CCE direct product-cell LDF valve boundary-balance paths and upper bound",
        cce_primary_product_ldf_valve_balance["status"]
        == "parameter_specialized_componentwise_product_ldf_valve_balance_compiled_monolithic_open"
        and cce_primary_product_ldf_valve_balance["qpu_submission"] is False
        and cce_primary_product_ldf_valve_balance["physical_state_source"]["product_boundary_states"] == 6464
        and cce_primary_product_ldf_valve_balance["physical_state_source"]["component_balances"] == 32320
        and cce_primary_product_ldf_valve_balance["joint_ldf_input_bits_per_pressure_and_composition"] == 20
        and set(product_ldf_components) == set(product_ldf_expected)
        and set(product_ldf_resources) == set(product_ldf_expected)
        and all(
            product_ldf_components[name]["loading_bits"] == expected[0]
            and product_ldf_components[name]["address_bits"] == expected[1]
            and product_ldf_components[name]["coefficient_bits"] == expected[2]
            and product_ldf_components[name]["passes_product_ldf_valve_balance_gate"]
            and product_ldf_components[name]["nonzero_transfer_erased_fraction"] == 0.0
            and product_ldf_components[name]["adsorption_term_overflow_fraction"] == 0.0
            and product_ldf_components[name]["desorption_term_overflow_fraction"] == 0.0
            and product_ldf_components[name]["negative_sum_underflow_fraction"] == 0.0
            and product_ldf_components[name]["next_output_overflow_fraction"] == 0.0
            and product_ldf_resources[name]["logical_qubits"] == expected[3]
            and product_ldf_resources[name]["depth_all_to_all"] == expected[4]
            and product_ldf_resources[name]["cx"] == expected[5]
            and product_ldf_resources[name]["measurement"] == 0
            and product_ldf_resources[name]["reset"] == 0
            for name, expected in product_ldf_expected.items()
        )
        and product_ldf_upper["logical_qubits_peak"] == 1195
        and product_ldf_upper["depth_all_to_all_additive_upper_bound"] == 144913247
        and product_ldf_upper["cx_additive_upper_bound"] == 88388552
        and product_ldf_upper["monolithic_five_component_transpile"] is False,
        f"paths={len(product_ldf_resources)}, peak={product_ldf_upper['logical_qubits_peak']}q, upper={product_ldf_upper['cx_additive_upper_bound']}CX",
    )
    normalized_product_components = {
        row["component"]: row
        for row in cce_primary_normalized_product_ldf_valve_balance[
            "selected_components"
        ]
    }
    normalized_product_resources = {
        row["component"]: row
        for row in cce_primary_normalized_product_ldf_valve_balance[
            "componentwise_compiled_direct_paths"
        ]
    }
    normalized_product_upper = cce_primary_normalized_product_ldf_valve_balance[
        "conservative_five_component_upper_bound"
    ]
    _check(
        checks,
        "CCE gas-inventory-generated product-cell LDF valve balance paths",
        cce_primary_normalized_product_ldf_valve_balance["status"]
        == "two_gas_inventory_componentwise_product_paths_compiled_monolithic_open"
        and cce_primary_normalized_product_ldf_valve_balance["qpu_submission"] is False
        and cce_primary_normalized_product_ldf_valve_balance["physical_state_source"]["product_end_states"] == 6464
        and cce_primary_normalized_product_ldf_valve_balance["physical_state_source"]["component_balances"] == 32320
        and cce_primary_normalized_product_ldf_valve_balance["normalizer_selection"]
        == {"amount_bits": 22, "reciprocal_bits": 22, "address_bits": 8}
        and set(normalized_product_components) == set(product_ldf_expected)
        and set(normalized_product_resources) == set(product_ldf_expected)
        and all(
            normalized_product_components[name]["passes_normalized_product_balance_gate"]
            and normalized_product_components[name]["next_p95_scale_normalized_absolute_error"] <= 2.5e-4
            and normalized_product_components[name]["next_max_scale_normalized_absolute_error"] <= 5.0e-4
            and normalized_product_components[name]["nonzero_transfer_erased_fraction"] == 0.0
            and normalized_product_components[name]["negative_sum_underflow_fraction"] == 0.0
            and normalized_product_components[name]["next_output_overflow_fraction"] == 0.0
            and normalized_product_resources[name]["measurement"] == 0
            and normalized_product_resources[name]["reset"] == 0
            for name in product_ldf_expected
        )
        and normalized_product_upper["logical_qubits_peak"]
        == max(row["logical_qubits"] for row in normalized_product_resources.values())
        and normalized_product_upper["depth_all_to_all_additive_upper_bound"]
        == sum(row["depth_all_to_all"] for row in normalized_product_resources.values())
        and normalized_product_upper["cx_additive_upper_bound"]
        == sum(row["cx"] for row in normalized_product_resources.values())
        and normalized_product_upper["monolithic_five_component_transpile"] is False,
        f"paths={len(normalized_product_resources)}, peak={normalized_product_upper['logical_qubits_peak']}q, upper={normalized_product_upper['cx_additive_upper_bound']}CX",
    )
    coherent_interface = cce_primary_coherent_run_schedule_tank["integrated_interface"]
    coherent_parameter = cce_primary_coherent_run_schedule_tank["parameter_encoding"]
    coherent_schedule = cce_primary_coherent_run_schedule_tank["schedule_encoding"]
    coherent_tank = cce_primary_coherent_run_schedule_tank["tank_encoding"]
    _check(
        checks,
        "CCE coherent finite-support run schedule tank interface",
        cce_primary_coherent_run_schedule_tank["status"]
        == "finite_support_coherent_run_parameter_valve_schedule_and_tank_withdrawal_interface_compiled_adaptive_cycle_open"
        and cce_primary_coherent_run_schedule_tank["qpu_submission"] is False
        and cce_primary_coherent_run_schedule_tank["support"]["runs"] == 32
        and cce_primary_coherent_run_schedule_tank["support"]["schedule_stages"] == 6
        and cce_primary_coherent_run_schedule_tank["support"]["tank_calls_per_final_cycle"] == 4
        and coherent_parameter["basis_table_values_checked"] == 352
        and coherent_parameter["bits_each"] == 12
        and coherent_parameter["aggregate"]["max_span_normalized_absolute_error"] <= 1.25e-4
        and coherent_schedule["basis_addresses_checked"] == 8
        and coherent_schedule["unused_codes_decode_valid_false"] is True
        and coherent_tank["selected"]["bits"] == 18
        and coherent_tank["selected"]["passes_declared_precision_gate"] is True
        and coherent_tank["selected"]["meaningful_nonzero_withdrawal_erased_count"] == 0
        and coherent_tank["selected"]["modular_underflow_count"] == 0
        and coherent_tank["selected"]["next_tank_precision_mismatch_count"] == 0
        and coherent_tank["basis_component_records_checked"] == 640
        and coherent_interface["logical_qubits"] == 440
        and coherent_interface["depth_all_to_all"] == 324495
        and coherent_interface["cx"] == 166189
        and coherent_interface["u"] == 194419
        and coherent_interface["measurement"] == 0
        and coherent_interface["reset"] == 0,
        f"parameter_values={coherent_parameter['basis_table_values_checked']}, schedule_addresses={coherent_schedule['basis_addresses_checked']}, tank_records={coherent_tank['basis_component_records_checked']}, integrated={coherent_interface['logical_qubits']}q/{coherent_interface['cx']}CX",
    )
    coherent_factor_ldf_resources = cce_primary_coherent_run_factor_ldf["compiled_interface"]
    coherent_factor_ldf_precision = cce_primary_coherent_run_factor_ldf["precision"]
    _check(
        checks,
        "CCE coherent run-factor to five-component LDF coefficient interface",
        cce_primary_coherent_run_factor_ldf["status"]
        == "finite_support_coherent_run_factors_directly_wired_to_five_component_ldf_coefficients_full_state_update_open"
        and cce_primary_coherent_run_factor_ldf["qpu_submission"] is False
        and cce_primary_coherent_run_factor_ldf["support"]["runs"] == 32
        and cce_primary_coherent_run_factor_ldf["support"]["coefficient_records_checked"] == 320
        and cce_primary_coherent_run_factor_ldf["support"]["schedule_flags_checked"] == 16
        and coherent_factor_ldf_precision["coefficient_scale_bits"] == 20
        and coherent_factor_ldf_precision["passes_declared_precision_gate"] is True
        and coherent_factor_ldf_precision["five_component_equilibrium_prefactor_max_relative_error"] <= 5.0e-5
        and coherent_factor_ldf_precision["five_component_ldf_alpha_max_relative_error"] <= 4.4e-5
        and coherent_factor_ldf_resources["logical_qubits"] == 495
        and coherent_factor_ldf_resources["depth_all_to_all"] == 526434
        and coherent_factor_ldf_resources["cx"] == 353441
        and coherent_factor_ldf_resources["u"] == 436305
        and coherent_factor_ldf_resources["measurement"] == 0
        and coherent_factor_ldf_resources["reset"] == 0,
        f"coefficients={cce_primary_coherent_run_factor_ldf['support']['coefficient_records_checked']}, flags={cce_primary_coherent_run_factor_ldf['support']['schedule_flags_checked']}, resources={coherent_factor_ldf_resources['logical_qubits']}q/{coherent_factor_ldf_resources['cx']}CX",
    )
    coherent_consumer_components = {
        row["component"]: row
        for row in cce_primary_coherent_coefficient_ldf_balance["components"]
    }
    coherent_consumer_resources = {
        row["component"]: row
        for row in cce_primary_coherent_coefficient_ldf_balance[
            "componentwise_compiled_direct_paths"
        ]
    }
    coherent_consumer_expected = {
        "H2": (1297, 1612437, 1855912),
        "CO2": (1298, 1681455, 1883094),
        "CH4": (1486, 3143800, 2807252),
        "CO": (1477, 2937203, 2690244),
        "N2": (1472, 3012190, 2674550),
    }
    coherent_consumer_upper = cce_primary_coherent_coefficient_ldf_balance[
        "conservative_five_component_upper_bound"
    ]
    _check(
        checks,
        "CCE coherent coefficient-consuming five-component LDF/loading/balance paths",
        cce_primary_coherent_coefficient_ldf_balance["status"]
        == "coherent_run_coefficients_consumed_in_five_schedule_gated_component_ldf_loading_balance_paths_dynamic_denominator_open"
        and cce_primary_coherent_coefficient_ldf_balance["qpu_submission"] is False
        and cce_primary_coherent_coefficient_ldf_balance["support"]["runs"] == 32
        and cce_primary_coherent_coefficient_ldf_balance["support"]["component_balance_records_checked"] == 64640
        and set(coherent_consumer_components) == set(coherent_consumer_expected)
        and all(row["passes_declared_precision_gate"] for row in coherent_consumer_components.values())
        and all(row["nonzero_quantized_transfer_erased_fraction"] == 0.0 for row in coherent_consumer_components.values())
        and max(row["qstar_max_loading_scale_normalized_absolute_error"] for row in coherent_consumer_components.values()) <= 4.4e-5
        and max(row["ldf_next_max_loading_scale_normalized_absolute_error"] for row in coherent_consumer_components.values()) <= 3.2e-5
        and max(row["next_gas_max_scale_normalized_absolute_error"] for row in coherent_consumer_components.values()) <= 4.0e-4
        and all(
            (
                coherent_consumer_resources[component]["logical_qubits"],
                coherent_consumer_resources[component]["depth_all_to_all"],
                coherent_consumer_resources[component]["cx"],
            )
            == expected
            for component, expected in coherent_consumer_expected.items()
        )
        and all(row["measurement"] == 0 and row["reset"] == 0 for row in coherent_consumer_resources.values())
        and coherent_consumer_upper["logical_qubits_peak"] == 1486
        and coherent_consumer_upper["depth_all_to_all_additive_upper_bound"] == 12387085
        and coherent_consumer_upper["cx_additive_upper_bound"] == 11911052
        and coherent_consumer_upper["monolithic_five_component_transpile"] is False,
        f"balances={cce_primary_coherent_coefficient_ldf_balance['support']['component_balance_records_checked']}, peak={coherent_consumer_upper['logical_qubits_peak']}q, additive_CX={coherent_consumer_upper['cx_additive_upper_bound']}",
    )
    coherent_dynamic_components = {
        row["component"]: row
        for row in cce_primary_coherent_dynamic_langmuir_ldf_balance["components"]
    }
    coherent_dynamic_resources = {
        row["component"]: row
        for row in cce_primary_coherent_dynamic_langmuir_ldf_balance[
            "componentwise_compiled_direct_paths"
        ]
    }
    coherent_dynamic_expected = {
        "H2": (1771, 67700348, 41440216),
        "CO2": (1772, 67700348, 41467398),
        "CH4": (1960, 67700348, 42391556),
        "CO": (1951, 67700348, 42274548),
        "N2": (1946, 67700348, 42258854),
    }
    coherent_dynamic_design = cce_primary_coherent_dynamic_langmuir_ldf_balance[
        "selected_dynamic_response_design"
    ]
    coherent_dynamic_upper = cce_primary_coherent_dynamic_langmuir_ldf_balance[
        "conservative_five_component_upper_bound"
    ]
    _check(
        checks,
        "CCE coherent dynamic Langmuir five-component LDF/loading/balance paths",
        cce_primary_coherent_dynamic_langmuir_ldf_balance["status"]
        == "dynamic_run_affinity_langmuir_response_consumed_in_five_compiled_component_paths"
        and cce_primary_coherent_dynamic_langmuir_ldf_balance["qpu_submission"] is False
        and cce_primary_coherent_dynamic_langmuir_ldf_balance["support"]["runs"] == 32
        and cce_primary_coherent_dynamic_langmuir_ldf_balance["support"]["component_balance_records_checked"] == 64640
        and coherent_dynamic_design["affinity_bits"] == 8
        and coherent_dynamic_design["denominator_address_bits"] == 12
        and coherent_dynamic_design["reciprocal_segments"] == 4096
        and coherent_dynamic_design["denominator_max_absolute_error"] <= 3.6e-4
        and set(coherent_dynamic_components) == set(coherent_dynamic_expected)
        and all(row["passes_declared_precision_gate"] for row in coherent_dynamic_components.values())
        and max(row["qstar_max_loading_scale_normalized_absolute_error"] for row in coherent_dynamic_components.values()) <= 2.9e-4
        and max(row["ldf_next_max_loading_scale_normalized_absolute_error"] for row in coherent_dynamic_components.values()) <= 2.0e-4
        and max(row["next_gas_max_scale_normalized_absolute_error"] for row in coherent_dynamic_components.values()) <= 4.0e-4
        and all(
            (
                coherent_dynamic_resources[component]["logical_qubits"],
                coherent_dynamic_resources[component]["depth_all_to_all"],
                coherent_dynamic_resources[component]["cx"],
            )
            == expected
            for component, expected in coherent_dynamic_expected.items()
        )
        and all(row["measurement"] == 0 and row["reset"] == 0 for row in coherent_dynamic_resources.values())
        and coherent_dynamic_upper["logical_qubits_peak"] == 1960
        and coherent_dynamic_upper["depth_all_to_all_additive_upper_bound"] == 338501740
        and coherent_dynamic_upper["cx_additive_upper_bound"] == 209832572
        and coherent_dynamic_upper["monolithic_five_component_transpile"] is False,
        f"balances={cce_primary_coherent_dynamic_langmuir_ldf_balance['support']['component_balance_records_checked']}, peak={coherent_dynamic_upper['logical_qubits_peak']}q, additive_CX={coherent_dynamic_upper['cx_additive_upper_bound']}",
    )
    coherent_normalized_dynamic_components = {
        row["component"]: row
        for row in cce_primary_coherent_normalized_dynamic_transport_ldf_balance[
            "components"
        ]
    }
    coherent_normalized_dynamic_resources = {
        row["component"]: row
        for row in cce_primary_coherent_normalized_dynamic_transport_ldf_balance[
            "componentwise_compiled_direct_paths"
        ]
    }
    coherent_normalized_dynamic_expected = {
        "H2": (2696, 89147751, 55337688),
        "CO2": (2697, 89147751, 55364870),
        "CH4": (2885, 89147751, 56289028),
        "CO": (2876, 89147751, 56172020),
        "N2": (2871, 89147751, 56156326),
    }
    coherent_normalized_dynamic_upper = (
        cce_primary_coherent_normalized_dynamic_transport_ldf_balance[
            "conservative_five_component_upper_bound"
        ]
    )
    _check(
        checks,
        "CCE coherent gas-inventory dynamic Langmuir transport LDF balance paths",
        cce_primary_coherent_normalized_dynamic_transport_ldf_balance["status"]
        == "gas_inventory_to_dynamic_langmuir_ldf_balance_five_component_paths_compiled"
        and cce_primary_coherent_normalized_dynamic_transport_ldf_balance[
            "qpu_submission"
        ]
        is False
        and cce_primary_coherent_normalized_dynamic_transport_ldf_balance["support"][
            "runs"
        ]
        == 32
        and cce_primary_coherent_normalized_dynamic_transport_ldf_balance["support"][
            "normalization_states"
        ]
        == 25856
        and cce_primary_coherent_normalized_dynamic_transport_ldf_balance["support"][
            "component_balance_records_checked"
        ]
        == 64640
        and set(coherent_normalized_dynamic_components)
        == set(coherent_normalized_dynamic_expected)
        and all(
            row["passes_declared_precision_gate"]
            for row in coherent_normalized_dynamic_components.values()
        )
        and max(
            row["next_gas_max_scale_normalized_absolute_error"]
            for row in coherent_normalized_dynamic_components.values()
        )
        <= 4.0e-4
        and all(
            (
                coherent_normalized_dynamic_resources[component]["logical_qubits"],
                coherent_normalized_dynamic_resources[component]["depth_all_to_all"],
                coherent_normalized_dynamic_resources[component]["cx"],
            )
            == expected
            for component, expected in coherent_normalized_dynamic_expected.items()
        )
        and all(
            row["measurement"] == 0 and row["reset"] == 0
            for row in coherent_normalized_dynamic_resources.values()
        )
        and coherent_normalized_dynamic_upper["logical_qubits_peak"] == 2885
        and coherent_normalized_dynamic_upper[
            "depth_all_to_all_additive_upper_bound"
        ]
        == 445738755
        and coherent_normalized_dynamic_upper["cx_additive_upper_bound"]
        == 279319932
        and coherent_normalized_dynamic_upper["monolithic_five_component_transpile"]
        is False,
        f"balances={cce_primary_coherent_normalized_dynamic_transport_ldf_balance['support']['component_balance_records_checked']}, peak={coherent_normalized_dynamic_upper['logical_qubits_peak']}q, additive_CX={coherent_normalized_dynamic_upper['cx_additive_upper_bound']}",
    )
    offledger_tank_selected = cce_primary_offledger_tank_saturation["selected_design"]
    offledger_tank_resources = cce_primary_offledger_tank_saturation[
        "compiled_clean_circuit"
    ]
    _check(
        checks,
        "CCE pressure-derived saturated tank-withdrawal interface",
        cce_primary_offledger_tank_saturation["status"]
        == "frozen_support_pressure_derived_saturated_tank_withdrawal_compiled"
        and cce_primary_offledger_tank_saturation["support"]["records"] == 128
        and offledger_tank_selected["common_bits"] == 20
        and offledger_tank_selected["exact_demand_saturated_records"] == 128
        and offledger_tank_selected[
            "end_pressure_lower_bound_saturated_records"
        ]
        == 128
        and offledger_tank_selected["encoded_saturated_records"] == 128
        and offledger_tank_selected["saturation_flag_mismatch_count"] == 0
        and offledger_tank_selected["lower_bound_violation_count"] == 0
        and offledger_tank_selected["modular_next_tank_underflow_count"] == 0
        and offledger_tank_selected["meaningful_withdrawal_erased_count"] == 0
        and offledger_tank_selected[
            "all_output_p95_scale_normalized_absolute_error"
        ]
        <= 2.1e-6
        and offledger_tank_selected["passes_declared_support_gate"] is True
        and offledger_tank_resources["logical_qubits"] == 557
        and offledger_tank_resources["depth_all_to_all"] == 327212
        and offledger_tank_resources["cx"] == 195276
        and offledger_tank_resources["measurement"] == 0
        and offledger_tank_resources["reset"] == 0
        and cce_primary_offledger_tank_saturation["qpu_submission"] is False,
        f"records={cce_primary_offledger_tank_saturation['support']['records']}, labels={offledger_tank_selected['encoded_saturated_records']}/128, margin={offledger_tank_selected['minimum_lower_bound_minus_tank_mol']:.6f} mol, resources={offledger_tank_resources['logical_qubits']}q/{offledger_tank_resources['cx']}CX",
    )
    offledger_proportional_selected = cce_primary_offledger_tank_proportional[
        "selected_design"
    ]
    offledger_proportional_resources = cce_primary_offledger_tank_proportional[
        "compiled_clean_circuit"
    ]
    _check(
        checks,
        "CCE pressure-derived saturated and bounded-unsaturated proportional tank allocation",
        cce_primary_offledger_tank_proportional["status"]
        == "pressure_derived_saturated_and_bounded_unsaturated_proportional_tank_allocation_compiled"
        and cce_primary_offledger_tank_proportional["support"]["observed_frozen_final_cycle_records"] == 128
        and cce_primary_offledger_tank_proportional["support"]["observed_saturated_records"] == 128
        and cce_primary_offledger_tank_proportional["support"]["counterfactual_arithmetic_records"] == 224
        and cce_primary_offledger_tank_proportional["support"]["counterfactual_unsaturated_records"] == 224
        and offledger_proportional_selected["common_bits"] == 18
        and offledger_proportional_selected["address_bits"] == 5
        and offledger_proportional_selected["reciprocal_bits"] == 16
        and offledger_proportional_selected["encoded_saturated_records"] == 128
        and offledger_proportional_selected["encoded_unsaturated_records"] == 224
        and offledger_proportional_selected["saturation_flag_mismatch_count"] == 0
        and offledger_proportional_selected["unsaturated_fraction_overflow_count"] == 0
        and offledger_proportional_selected["modular_next_tank_underflow_count"] == 0
        and offledger_proportional_selected["meaningful_withdrawal_erased_count"] == 0
        and offledger_proportional_selected["withdrawal_and_next_p95_component_scale_normalized_absolute_error"] <= 1.7e-4
        and offledger_proportional_selected["withdrawal_and_next_max_component_scale_normalized_absolute_error"] <= 3.9e-4
        and offledger_proportional_selected["passes_declared_domain_gate"] is True
        and offledger_proportional_resources["logical_qubits"] == 647
        and offledger_proportional_resources["depth_all_to_all"] == 1127046
        and offledger_proportional_resources["cx"] == 705194
        and offledger_proportional_resources["measurement"] == 0
        and offledger_proportional_resources["reset"] == 0
        and cce_primary_offledger_tank_proportional["qpu_submission"] is False,
        f"observed={cce_primary_offledger_tank_proportional['support']['observed_saturated_records']}, counterfactual={cce_primary_offledger_tank_proportional['support']['counterfactual_unsaturated_records']}, labels={offledger_proportional_selected['encoded_saturated_records']}/{offledger_proportional_selected['encoded_unsaturated_records']}, resources={offledger_proportional_resources['logical_qubits']}q/{offledger_proportional_resources['cx']}CX",
    )
    physical_unsaturated_selected = cce_primary_physical_unsaturated_tank[
        "selected_design"
    ]
    physical_unsaturated_resources = cce_primary_physical_unsaturated_tank[
        "compiled_clean_circuit"
    ]
    physical_unsaturated_trajectory = cce_primary_physical_unsaturated_tank[
        "trajectory"
    ]
    _check(
        checks,
        "CCE model-derived physical unsaturated tank trajectory control",
        cce_primary_physical_unsaturated_tank["status"]
        == "same_recycle_short_schedule_two_pressure_unsaturated_allocation_compiled"
        and physical_unsaturated_trajectory["tank_calls"] == 128
        and physical_unsaturated_trajectory["unsaturated_calls"] == 128
        and physical_unsaturated_trajectory["saturated_calls"] == 0
        and physical_unsaturated_trajectory["zero_makeup_calls"] == 128
        and physical_unsaturated_trajectory["maximum_replay_absolute_state_error"] == 0
        and physical_unsaturated_trajectory["final_css_residual_max"] < 1.0e-6
        and cce_primary_physical_unsaturated_tank["pressure_demand_diagnostics"]["trapezoid_proxy_p95_relative_error"] <= 8.6e-3
        and physical_unsaturated_selected["common_bits"] == 18
        and physical_unsaturated_selected["address_bits"] == 3
        and physical_unsaturated_selected["reciprocal_bits"] == 16
        and physical_unsaturated_selected["passes_declared_domain_gate"] is True
        and physical_unsaturated_selected["saturation_flag_mismatch_count"] == 0
        and physical_unsaturated_selected["withdrawal_and_next_p95_component_scale_normalized_absolute_error"] <= 8.4e-6
        and physical_unsaturated_selected["withdrawal_and_next_max_component_scale_normalized_absolute_error"] <= 9.3e-6
        and physical_unsaturated_resources["logical_qubits"] == 845
        and physical_unsaturated_resources["depth_all_to_all"] == 1634701
        and physical_unsaturated_resources["cx"] == 1078054
        and physical_unsaturated_resources["measurement"] == 0
        and physical_unsaturated_resources["reset"] == 0
        and cce_primary_physical_unsaturated_tank["qpu_submission"] is False,
        f"calls={physical_unsaturated_trajectory['unsaturated_calls']}/128, css={physical_unsaturated_trajectory['final_css_residual_max']:.3e}, trapezoid_p95={cce_primary_physical_unsaturated_tank['pressure_demand_diagnostics']['trapezoid_proxy_p95_relative_error']:.3%}, resources={physical_unsaturated_resources['logical_qubits']}q/{physical_unsaturated_resources['cx']}CX",
    )
    primary_event = cce_primary_event_bridge["event_summary"]
    _check(
        checks,
        "CCE nested-held-out primary phase-stream event bridge values",
        cce_primary_event_bridge["status"]
        == "nested_holdout_primary_phase_stream_event_bridge_conditional_on_observed_phase_starts"
        and cce_primary_event_bridge["sample_count"] == 32
        and primary_event["held_out_runs"] == 32
        and primary_event["event_matches"] == 32
        and primary_event["false_positive_count"] == 0
        and primary_event["false_negative_count"] == 0
        and abs(float(primary_event["purity_mae"]) - 3.789824838673628e-08) < 1e-16
        and abs(float(primary_event["recovery_mae"]) - 7.271581715980954e-05) < 1e-12
        and cce_primary_event_bridge["qpu_submission"] is False
        and "free-running CSS" in cce_primary_event_bridge["claim_boundary"]["unsupported"],
        f"labels={primary_event['event_matches']}/32, purity_MAE={primary_event['purity_mae']}, recovery_MAE={primary_event['recovery_mae']}",
    )
    primary_fixed = cce_primary_event_fixed_point["minimum_configuration_within_budgets_and_all_labels"]
    primary_compile = cce_primary_event_compile["aggregate"]
    _check(
        checks,
        "CCE primary event-active fixed-point and primitive-gate values",
        cce_primary_event_fixed_point["status"]
        == "primary_phase_event_fixed_point_precision_screen_event_arithmetic_and_css_open"
        and primary_fixed["bits_per_input"] == 12
        and primary_fixed["sum_bits_per_scalar_output"] == 16
        and primary_fixed["event_matches_vs_actual"] == 32
        and primary_fixed["within_both_budgets"]
        and primary_fixed["all_event_labels_match"]
        and cce_primary_event_compile["status"]
        == "event_active_primary_phase_stream_affine_blocks_compiled_event_arithmetic_css_and_loader_open"
        and primary_compile["scalar_blocks"] == 12
        and primary_compile["max_logical_qubits_reusing_scalar_workspace"] == 272
        and primary_compile["serial_forward_cx"] == 1101233
        and primary_compile["serial_clean_compute_uncompute_cx"] == 2202466
        and cce_primary_event_fixed_point["qpu_submission"] is False
        and cce_primary_event_compile["qpu_submission"] is False
        and "joint-event comparison" in cce_primary_event_compile["claim_boundary"]["unsupported"],
        f"fixed={primary_fixed['bits_per_input']}/{primary_fixed['sum_bits_per_scalar_output']} bits, blocks={primary_compile['scalar_blocks']}, qubits={primary_compile['max_logical_qubits_reusing_scalar_workspace']}, forward_CX={primary_compile['serial_forward_cx']}, clean_CX={primary_compile['serial_clean_compute_uncompute_cx']}",
    )
    final_precision = cce_primary_final_event["precision_screen"]["selected"]
    final_coefficient = cce_primary_final_event["coefficient_screen"]["selected"]
    final_verify = cce_primary_final_event["verification"]
    final_compile = cce_primary_final_event["primitive_gate_compile"]["clean_phase_oracle"]
    _check(
        checks,
        "CCE primary final joint-event arithmetic values",
        cce_primary_final_event["status"]
        == "primary_quantized_joint_event_arithmetic_compiled_clean_phase_oracle_stream_aggregation_and_css_open"
        and final_precision["bits"] == 16
        and final_precision["within_both_budgets_and_labels"]
        and final_coefficient["coefficient_bits"] == 8
        and final_coefficient["coefficient_error_within_margin_gate"]
        and final_verify["integer_event_matches"] == 32
        and final_verify["false_positives"] == 0
        and final_verify["false_negatives"] == 0
        and final_compile["logical_qubits"] == 125
        and final_compile["cx"] == 182981
        and final_compile["depth_all_to_all"] == 355454
        and cce_primary_final_event["qpu_submission"] is False,
        f"bits={final_precision['bits']}, coefficient_bits={final_coefficient['coefficient_bits']}, labels={final_verify['integer_event_matches']}/32, qubits={final_compile['logical_qubits']}, clean_CX={final_compile['cx']}",
    )
    policy_precision = cce_primary_policy_stream_event["precision_screen"]["selected"]
    policy_verify = cce_primary_policy_stream_event["verification"]
    policy_resources = cce_primary_policy_stream_event["primitive_gate_compile"]["policy_resources"]
    _check(
        checks,
        "CCE primary policy stream-to-event clean oracle values",
        cce_primary_policy_stream_event["status"]
        == "candidate_policy_collapsed_stream_aggregation_and_joint_event_compiled_physical_css_open"
        and policy_precision["aggregate_bits"] == 19
        and policy_precision["within_both_budgets_and_labels"]
        and abs(float(policy_precision["p95_purity_abs_error"]) - 1.1324226889541933e-08) < 1e-18
        and abs(float(policy_precision["p95_recovery_abs_error"]) - 1.108876928965219e-05) < 1e-15
        and policy_verify["candidate_integer_event_matches_vs_float"] == 96
        and policy_verify["ledger_support_event_matches_vs_actual"] == 32
        and policy_verify["candidate_input_clip_count"] == 0
        and max(row["clean_phase_oracle"]["logical_qubits"] for row in policy_resources) == 510
        and max(row["clean_phase_oracle"]["cx"] for row in policy_resources) == 1286021
        and max(row["clean_phase_oracle"]["depth_all_to_all"] for row in policy_resources) == 2481760
        and cce_primary_policy_stream_event["qpu_submission"] is False,
        f"aggregate_bits={policy_precision['aggregate_bits']}, candidate_labels={policy_verify['candidate_integer_event_matches_vs_float']}/96, ledger_labels={policy_verify['ledger_support_event_matches_vs_actual']}/32, max_qubits={max(row['clean_phase_oracle']['logical_qubits'] for row in policy_resources)}, max_clean_CX={max(row['clean_phase_oracle']['cx'] for row in policy_resources)}",
    )
    free_event = cce_primary_free_running["event_summary"]
    _check(
        checks,
        "CCE primary one-cycle free-running aggregate event values",
        cce_primary_free_running["status"]
        == "nested_holdout_primary_one_cycle_free_running_aggregate_state_bridge_repeated_css_open"
        and free_event["event_matches"] == 32
        and free_event["false_positive_count"] == 0
        and free_event["false_negative_count"] == 0
        and abs(float(free_event["recovery_mae"]) - 6.428084378119758e-05) < 1e-12
        and free_event["total_clipped_state_entries"] == 0
        and free_event["total_clipped_stream_entries"] == 0
        and cce_primary_free_running["qpu_submission"] is False,
        f"labels={free_event['event_matches']}/32, recovery_MAE={free_event['recovery_mae']}, p95_closure={free_event['p95_final_cycle_closure_relative_l1']}",
    )
    repeated = cce_primary_repeated["summary"]
    _check(
        checks,
        "CCE observed-start repeated-cycle instability values",
        cce_primary_repeated["status"]
        == "nested_holdout_primary_aggregate_map_repeated_cycle_stability_screen_tank_and_reversible_css_open"
        and repeated["cycles_per_run"] == 50
        and repeated["terminal_event_matches"] == 21
        and repeated["tail_css_gate_1e_4_count"] == 1
        and repeated["total_clipped_state_entries"] == 1014
        and repeated["total_clipped_stream_entries"] == 982
        and cce_primary_repeated["qpu_submission"] is False,
        f"terminal={repeated['terminal_event_matches']}/32, css={repeated['tail_css_gate_1e_4_count']}/32, state_clips={repeated['total_clipped_state_entries']}",
    )
    css_summary = cce_css_initializer["summary"]
    css_repeated = cce_css_repeated["summary"]
    _check(
        checks,
        "CCE parameter-only CSS initializer and repeated-cycle values",
        cce_css_initializer["status"]
        == "nested_holdout_parameter_to_css_initializer_one_cycle_event_bridge_no_held_dynamic_state"
        and cce_css_initializer["held_run_dynamic_states_supplied"] == 0
        and css_summary["event_matches"] == 32
        and abs(float(css_summary["recovery_mae"]) - 0.0003221441157125124) < 1e-12
        and css_summary["total_initial_clipped_state_entries"] == 0
        and cce_css_repeated["status"]
        == "nested_holdout_parameter_only_css_initializer_repeated_aggregate_cycle_screen_tank_and_reversible_css_open"
        and css_repeated["terminal_event_matches"] == 28
        and css_repeated["tail_css_gate_1e_4_count"] == 2
        and cce_css_initializer["qpu_submission"] is False
        and cce_css_repeated["qpu_submission"] is False,
        f"one_cycle={css_summary['event_matches']}/32, recovery_MAE={css_summary['recovery_mae']}, terminal={css_repeated['terminal_event_matches']}/32, css={css_repeated['tail_css_gate_1e_4_count']}/32",
    )
    css_stability = cce_css_stability["summary"]
    _check(
        checks,
        "CCE parameter-only aggregate spectral-stability values",
        cce_css_stability["status"]
        == "nested_holdout_spectral_stabilization_pass_reduced_surrogate_only_physical_reversible_css_open"
        and cce_css_stability["held_run_dynamic_states_supplied"] == 0
        and cce_css_stability["held_run_event_labels_used_for_stabilization"] is False
        and css_stability["raw_spectral_radius_min"] > 1.0
        and abs(float(css_stability["target_spectral_radius"]) - 0.9) < 1e-12
        and css_stability["terminal_event_matches"] == 32
        and css_stability["tail_css_gate_1e_4_count"] == 32
        and css_stability["baseline_terminal_event_matches"] == 28
        and css_stability["baseline_tail_css_gate_1e_4_count"] == 2
        and css_stability["total_clipped_state_entries"] == 0
        and css_stability["total_clipped_stream_entries"] == 0
        and cce_css_stability["qpu_submission"] is False,
        f"rho={css_stability['raw_spectral_radius_min']}/{css_stability['raw_spectral_radius_max']}, weight={css_stability['anchor_weight_min']}/{css_stability['anchor_weight_max']}, labels={css_stability['terminal_event_matches']}/32, css={css_stability['tail_css_gate_1e_4_count']}/32",
    )
    css_fixed = cce_css_fixed["minimum_configuration_within_all_budgets_and_labels"]
    css_compile = cce_css_compile["aggregate"]
    _check(
        checks,
        "CCE parameter-only CSS initializer fixed-point and primitive-gate values",
        cce_css_fixed["status"]
        == "parameter_only_css_initializer_fixed_point_screen_reversible_state_update_and_physical_css_open"
        and css_fixed["bits_per_input"] == 9
        and css_fixed["sum_bits_per_scalar_output"] == 14
        and css_fixed["event_matches_vs_actual"] == 32
        and css_fixed["within_all_budgets"]
        and cce_css_compile["status"]
        == "parameter_only_css_initializer_affine_blocks_compiled_state_update_physical_css_and_loader_open"
        and css_compile["scalar_blocks"] == 20
        and css_compile["max_logical_qubits_reusing_scalar_workspace"] == 118
        and css_compile["serial_forward_cx"] == 578702
        and css_compile["serial_clean_compute_uncompute_cx"] == 1157404
        and cce_css_fixed["qpu_submission"] is False
        and cce_css_compile["qpu_submission"] is False,
        f"fixed={css_fixed['bits_per_input']}/{css_fixed['sum_bits_per_scalar_output']} bits, blocks={css_compile['scalar_blocks']}, qubits={css_compile['max_logical_qubits_reusing_scalar_workspace']}, forward_CX={css_compile['serial_forward_cx']}",
    )
    resource_rows = {row["tier"]: row for row in cce_resource_table["rows"]}
    _check(
        checks,
        "CCE main-text resource ladder table values",
        cce_resource_table["status"]
        == "main_text_resource_ladder_assembled_open_end_to_end_gates_disclosed"
        and len(resource_rows) == 30
        and resource_rows["small end-to-end structural oracle"]["logical_qubits"] == 15
        and "304 CX" in resource_rows["small end-to-end structural oracle"]["per_call_or_block_resource"]
        and resource_rows["fixed-point response-event oracle"]["logical_qubits"] == 99
        and "52,740,000 CX" in resource_rows["fixed-point response-event oracle"]["schedule_or_aggregate_resource"]
        and resource_rows["calibrated one-cycle affine blocks"]["logical_qubits"] == 186
        and "8,367,972 clean CX" in resource_rows["calibrated one-cycle affine blocks"]["schedule_or_aggregate_resource"]
        and resource_rows["primary phase-stream event blocks"]["logical_qubits"] == 272
        and "1,101,233 forward CX" in resource_rows["primary phase-stream event blocks"]["schedule_or_aggregate_resource"]
        and "2,202,466 clean CX" in resource_rows["primary phase-stream event blocks"]["schedule_or_aggregate_resource"]
        and resource_rows["primary final joint-event arithmetic"]["logical_qubits"] == 125
        and "182,981 CX" in resource_rows["primary final joint-event arithmetic"]["per_call_or_block_resource"]
        and "32/32 labels" in resource_rows["primary final joint-event arithmetic"]["accuracy_or_observation"]
        and resource_rows["primary policy stream-to-event clean oracle"]["logical_qubits"] == 510
        and "1,286,021 CX" in resource_rows["primary policy stream-to-event clean oracle"]["per_call_or_block_resource"]
        and "96/96 candidate labels" in resource_rows["primary policy stream-to-event clean oracle"]["accuracy_or_observation"]
        and "32/32 ledger-support labels" in resource_rows["primary policy stream-to-event clean oracle"]["accuracy_or_observation"]
        and resource_rows["five-component equilibrium/LDF microsteps"]["logical_qubits"] == 675
        and "6,547,362 additive CX" in resource_rows["five-component equilibrium/LDF microsteps"]["schedule_or_aggregate_resource"]
        and "transport" in resource_rows["five-component equilibrium/LDF microsteps"]["boundary"]
        and resource_rows["product-boundary valve and recycle-tank modules"]["logical_qubits"] == 677
        and "valve 288 q/800,762 CX" in resource_rows["product-boundary valve and recycle-tank modules"]["per_call_or_block_resource"]
        and "five-component tank accounting 677 q/1,043,990 additive CX" in resource_rows["product-boundary valve and recycle-tank modules"]["schedule_or_aggregate_resource"]
        and "local pressure/face modules" in resource_rows["product-boundary valve and recycle-tank modules"]["boundary"]
        and resource_rows["direct product-valve-to-boundary-cell balance"]["logical_qubits"] == 842
        and "842 q/2,348,388 CX" in resource_rows["direct product-valve-to-boundary-cell balance"]["per_call_or_block_resource"]
        and "depth 3,285,605" in resource_rows["direct product-valve-to-boundary-cell balance"]["per_call_or_block_resource"]
        and "32,320 component balances" in resource_rows["direct product-valve-to-boundary-cell balance"]["accuracy_or_observation"]
        and "normalization" in resource_rows["direct product-valve-to-boundary-cell balance"]["boundary"]
        and resource_rows["direct product-cell LDF/valve/boundary-balance paths"]["logical_qubits"] == 1195
        and "1,072–1,195 q/10,060,060–26,810,396 CX" in resource_rows["direct product-cell LDF/valve/boundary-balance paths"]["per_call_or_block_resource"]
        and "88,388,552 additive CX" in resource_rows["direct product-cell LDF/valve/boundary-balance paths"]["schedule_or_aggregate_resource"]
        and "32,320 balances" in resource_rows["direct product-cell LDF/valve/boundary-balance paths"]["accuracy_or_observation"]
        and "product composition normalization" in resource_rows["direct product-cell LDF/valve/boundary-balance paths"]["boundary"]
        and resource_rows["gas-inventory-generated product-cell LDF/valve/balance paths"]["logical_qubits"] == normalized_product_upper["logical_qubits_peak"]
        and f"{min(row['logical_qubits'] for row in normalized_product_resources.values()):,}–{max(row['logical_qubits'] for row in normalized_product_resources.values()):,} q/{min(row['cx'] for row in normalized_product_resources.values()):,}–{max(row['cx'] for row in normalized_product_resources.values()):,} CX" in resource_rows["gas-inventory-generated product-cell LDF/valve/balance paths"]["per_call_or_block_resource"]
        and f"{normalized_product_upper['cx_additive_upper_bound']:,} additive CX" in resource_rows["gas-inventory-generated product-cell LDF/valve/balance paths"]["schedule_or_aggregate_resource"]
        and "32,320 balances" in resource_rows["gas-inventory-generated product-cell LDF/valve/balance paths"]["accuracy_or_observation"]
        and "finite-support run/schedule/tank interface" in resource_rows["gas-inventory-generated product-cell LDF/valve/balance paths"]["boundary"]
        and resource_rows["coherent run/schedule/tank interface"]["logical_qubits"] == 440
        and "166,189 CX" in resource_rows["coherent run/schedule/tank interface"]["per_call_or_block_resource"]
        and "352 parameter values" in resource_rows["coherent run/schedule/tank interface"]["accuracy_or_observation"]
        and "zero meaningful erasure/underflow/mismatch" in resource_rows["coherent run/schedule/tank interface"]["accuracy_or_observation"]
        and "continuous off-ledger" in resource_rows["coherent run/schedule/tank interface"]["boundary"]
        and resource_rows["coherent run-factor/LDF coefficient interface"]["logical_qubits"] == 495
        and "353,441 CX" in resource_rows["coherent run-factor/LDF coefficient interface"]["per_call_or_block_resource"]
        and "320 coefficient records" in resource_rows["coherent run-factor/LDF coefficient interface"]["accuracy_or_observation"]
        and "16 bed/stage flags" in resource_rows["coherent run-factor/LDF coefficient interface"]["accuracy_or_observation"]
        and "reported separately" in resource_rows["coherent run-factor/LDF coefficient interface"]["boundary"]
        and resource_rows["coherent coefficient-to-LDF/loading/balance paths"]["logical_qubits"] == 1486
        and "1,297–1,486 q/1,855,912–2,807,252 CX" in resource_rows["coherent coefficient-to-LDF/loading/balance paths"]["per_call_or_block_resource"]
        and "11,911,052 additive CX" in resource_rows["coherent coefficient-to-LDF/loading/balance paths"]["schedule_or_aggregate_resource"]
        and "64,640 component balances" in resource_rows["coherent coefficient-to-LDF/loading/balance paths"]["accuracy_or_observation"]
        and "zero quantized-transfer erasure" in resource_rows["coherent coefficient-to-LDF/loading/balance paths"]["accuracy_or_observation"]
        and "dynamic affinity denominator/reciprocal" in resource_rows["coherent coefficient-to-LDF/loading/balance paths"]["boundary"]
        and resource_rows["coherent dynamic-Langmuir-to-LDF/loading/balance paths"]["logical_qubits"] == 1960
        and "1,771–1,960 q/41,440,216–42,391,556 CX" in resource_rows["coherent dynamic-Langmuir-to-LDF/loading/balance paths"]["per_call_or_block_resource"]
        and "209,832,572 additive CX" in resource_rows["coherent dynamic-Langmuir-to-LDF/loading/balance paths"]["schedule_or_aggregate_resource"]
        and "64,640 component balances" in resource_rows["coherent dynamic-Langmuir-to-LDF/loading/balance paths"]["accuracy_or_observation"]
        and "pressure and five composition words are supplied" in resource_rows["coherent dynamic-Langmuir-to-LDF/loading/balance paths"]["boundary"]
        and resource_rows["coherent gas-inventory-to-dynamic-Langmuir/transport/LDF/balance paths"]["logical_qubits"] == 2885
        and "2,696–2,885 q/55,337,688–56,289,028 CX" in resource_rows["coherent gas-inventory-to-dynamic-Langmuir/transport/LDF/balance paths"]["per_call_or_block_resource"]
        and "279,319,932 additive CX" in resource_rows["coherent gas-inventory-to-dynamic-Langmuir/transport/LDF/balance paths"]["schedule_or_aggregate_resource"]
        and "25,856 normalization states" in resource_rows["coherent gas-inventory-to-dynamic-Langmuir/transport/LDF/balance paths"]["accuracy_or_observation"]
        and "negative-flow switching" in resource_rows["coherent gas-inventory-to-dynamic-Langmuir/transport/LDF/balance paths"]["boundary"]
        and resource_rows["pressure-derived saturated tank-withdrawal interface"]["logical_qubits"] == 557
        and "557 q/195,276 CX" in resource_rows["pressure-derived saturated tank-withdrawal interface"]["per_call_or_block_resource"]
        and "depth 327,212" in resource_rows["pressure-derived saturated tank-withdrawal interface"]["per_call_or_block_resource"]
        and "128 final-cycle tank calls" in resource_rows["pressure-derived saturated tank-withdrawal interface"]["schedule_or_aggregate_resource"]
        and "128/128 encoded saturation labels" in resource_rows["pressure-derived saturated tank-withdrawal interface"]["accuracy_or_observation"]
        and "1.624404 mol" in resource_rows["pressure-derived saturated tank-withdrawal interface"]["accuracy_or_observation"]
        and "2.033e-06" in resource_rows["pressure-derived saturated tank-withdrawal interface"]["accuracy_or_observation"]
        and "unsaturated proportional allocation" in resource_rows["pressure-derived saturated tank-withdrawal interface"]["boundary"]
        and resource_rows["pressure-derived saturated/unsaturated proportional tank-allocation interface"]["logical_qubits"] == 647
        and "647 q/705,194 CX" in resource_rows["pressure-derived saturated/unsaturated proportional tank-allocation interface"]["per_call_or_block_resource"]
        and "depth 1,127,046" in resource_rows["pressure-derived saturated/unsaturated proportional tank-allocation interface"]["per_call_or_block_resource"]
        and "128 observed saturated calls" in resource_rows["pressure-derived saturated/unsaturated proportional tank-allocation interface"]["schedule_or_aggregate_resource"]
        and "224 bounded unsaturated arithmetic cases" in resource_rows["pressure-derived saturated/unsaturated proportional tank-allocation interface"]["schedule_or_aggregate_resource"]
        and "128 saturated/224 unsaturated labels" in resource_rows["pressure-derived saturated/unsaturated proportional tank-allocation interface"]["accuracy_or_observation"]
        and "1.687e-04" in resource_rows["pressure-derived saturated/unsaturated proportional tank-allocation interface"]["accuracy_or_observation"]
        and "3.872e-04" in resource_rows["pressure-derived saturated/unsaturated proportional tank-allocation interface"]["accuracy_or_observation"]
        and "counterfactual" in resource_rows["pressure-derived saturated/unsaturated proportional tank-allocation interface"]["boundary"]
        and resource_rows["model-derived physical unsaturated tank-trajectory control"]["logical_qubits"] == 845
        and "845 q/1,078,054 CX" in resource_rows["model-derived physical unsaturated tank-trajectory control"]["per_call_or_block_resource"]
        and "depth 1,634,701" in resource_rows["model-derived physical unsaturated tank-trajectory control"]["per_call_or_block_resource"]
        and "128/128 physical unsaturated" in resource_rows["model-derived physical unsaturated tank-trajectory control"]["accuracy_or_observation"]
        and "0.853%" in resource_rows["model-derived physical unsaturated tank-trajectory control"]["accuracy_or_observation"]
        and "0.02-s" in resource_rows["model-derived physical unsaturated tank-trajectory control"]["boundary"]
        and resource_rows["pressure reconstruction and oriented internal-face transport"]["logical_qubits"] == 584
        and "pressure 152 q/93,764 CX" in resource_rows["pressure reconstruction and oriented internal-face transport"]["per_call_or_block_resource"]
        and "face 404 q/1,340,390 CX" in resource_rows["pressure reconstruction and oriented internal-face transport"]["per_call_or_block_resource"]
        and "584 q/1,527,918 additive CX" in resource_rows["pressure reconstruction and oriented internal-face transport"]["schedule_or_aggregate_resource"]
        and resource_rows["direct pressure-to-two-face-to-interior-cell balance"]["logical_qubits"] == 1508
        and "1,508 q/8,328,622 CX" in resource_rows["direct pressure-to-two-face-to-interior-cell balance"]["per_call_or_block_resource"]
        and "depth 12,250,291" in resource_rows["direct pressure-to-two-face-to-interior-cell balance"]["per_call_or_block_resource"]
        and "64,640 component balances" in resource_rows["direct pressure-to-two-face-to-interior-cell balance"]["accuracy_or_observation"]
        and "normalization" in resource_rows["direct pressure-to-two-face-to-interior-cell balance"]["boundary"]
        and resource_rows["direct gas-normalization-to-two-face-to-interior-cell balance"]["logical_qubits"] == 1651
        and "1,651 q/14,667,150 CX" in resource_rows["direct gas-normalization-to-two-face-to-interior-cell balance"]["per_call_or_block_resource"]
        and "depth 22,143,683" in resource_rows["direct gas-normalization-to-two-face-to-interior-cell balance"]["per_call_or_block_resource"]
        and "standalone normalizer 333 q/1,340,232 CX" in resource_rows["direct gas-normalization-to-two-face-to-interior-cell balance"]["per_call_or_block_resource"]
        and "25,856 normalization states" in resource_rows["direct gas-normalization-to-two-face-to-interior-cell balance"]["accuracy_or_observation"]
        and "support-adaptive" in resource_rows["direct gas-normalization-to-two-face-to-interior-cell balance"]["boundary"]
        and resource_rows["direct LDF-to-loading-sign-to-cell-balance composition"]["logical_qubits"] == 1317
        and "clean directly composed modules 861–929 q/3,412,254–4,991,534 CX" in resource_rows["direct LDF-to-loading-sign-to-cell-balance composition"]["per_call_or_block_resource"]
        and "1,317 q/19,082,852 additive CX" in resource_rows["direct LDF-to-loading-sign-to-cell-balance composition"]["schedule_or_aggregate_resource"]
        and "934 q/1,411,882 additive CX" in resource_rows["direct LDF-to-loading-sign-to-cell-balance composition"]["schedule_or_aggregate_resource"]
        and "loading bits 26,26,32,32,30" in resource_rows["direct LDF-to-loading-sign-to-cell-balance composition"]["accuracy_or_observation"]
        and "constant-specialized" in resource_rows["direct LDF-to-loading-sign-to-cell-balance composition"]["boundary"]
        and resource_rows["direct normalized-transport/LDF/interior-balance paths"]["logical_qubits"] == 2039
        and "1,944–2,039 q/20,670,468–35,947,274 CX" in resource_rows["direct normalized-transport/LDF/interior-balance paths"]["per_call_or_block_resource"]
        and "128,013,726 additive CX" in resource_rows["direct normalized-transport/LDF/interior-balance paths"]["schedule_or_aggregate_resource"]
        and "all five gates pass" in resource_rows["direct normalized-transport/LDF/interior-balance paths"]["accuracy_or_observation"]
        and "monolithic five-component transpilation" in resource_rows["direct normalized-transport/LDF/interior-balance paths"]["boundary"]
        and resource_rows["parameter-only CSS initializer blocks"]["logical_qubits"] == 118
        and "578,702 forward CX" in resource_rows["parameter-only CSS initializer blocks"]["schedule_or_aggregate_resource"]
        and "1,157,404 clean CX" in resource_rows["parameter-only CSS initializer blocks"]["schedule_or_aggregate_resource"]
        and resource_rows["real-QPU three-qubit event"]["logical_qubits"] == 3
        and "0.058060" in resource_rows["real-QPU three-qubit event"]["accuracy_or_observation"],
        f"rows={len(resource_rows)}, response_qubits={resource_rows['fixed-point response-event oracle']['logical_qubits']}, affine_qubits={resource_rows['calibrated one-cycle affine blocks']['logical_qubits']}, css_init_qubits={resource_rows['parameter-only CSS initializer blocks']['logical_qubits']}, event_stream_qubits={resource_rows['primary phase-stream event blocks']['logical_qubits']}, final_event_qubits={resource_rows['primary final joint-event arithmetic']['logical_qubits']}, integrated_policy_qubits={resource_rows['primary policy stream-to-event clean oracle']['logical_qubits']}, all_component_ldf_qubits={resource_rows['five-component equilibrium/LDF microsteps']['logical_qubits']}, transport_qubits={resource_rows['pressure reconstruction and oriented internal-face transport']['logical_qubits']}, direct_internal_face_balance_qubits={resource_rows['direct pressure-to-two-face-to-interior-cell balance']['logical_qubits']}, normalized_internal_face_balance_qubits={resource_rows['direct gas-normalization-to-two-face-to-interior-cell balance']['logical_qubits']}, direct_ldf_sign_balance_qubits={resource_rows['direct LDF-to-loading-sign-to-cell-balance composition']['logical_qubits']}, product_boundary_qubits={resource_rows['product-boundary valve and recycle-tank modules']['logical_qubits']}, product_boundary_balance_qubits={resource_rows['direct product-valve-to-boundary-cell balance']['logical_qubits']}",
    )
    table1_rows = {row["item"]: row for row in cce_table1["rows"]}
    table2_rows = {row["method"]: row for row in cce_table2["rows"]}
    table4_rows = {row["evidence tier"]: row for row in cce_table4["rows"]}
    _check(
        checks,
        "CCE main-text Tables 1 2 and 4 values",
        cce_table1["status"] == "frozen_primary_protocol_tabulated"
        and len(table1_rows) == 12
        and table1_rows["candidate policies"]["frozen specification"] == "0.420/0.427/0.430"
        and cce_table2["status"] == "matched_primary_estimators_tabulated"
        and len(table2_rows) == 4
        and table2_rows["scrambled Sobol RQMC"]["rmse"] == "0.002482"
        and table2_rows["noiseless MLAE"]["rmse"] == "0.002892"
        and cce_table4["status"] == "evidence_tiers_tabulated_without_cross_system_pooling"
        and len(table4_rows) == 31
        and "not plant validation" in table4_rows["primary spatial/tank response model"]["explicit boundary"]
        and "physical joint horizon 68 cycles" in table4_rows["primary physical CSS horizon and register accounting"]["key result"]
        and "2,880 qubits" in table4_rows["primary physical CSS horizon and register accounting"]["key result"]
        and "not a universal lower bound" in table4_rows["primary physical CSS horizon and register accounting"]["explicit boundary"]
        and "490–515 qubits" in table4_rows["five-component competitive-Langmuir/LDF microsteps"]["key result"]
        and "675 qubits/6,547,362 additive CX" in table4_rows["five-component competitive-Langmuir/LDF microsteps"]["key result"]
        and "gas transport" in table4_rows["five-component competitive-Langmuir/LDF microsteps"]["explicit boundary"]
        and "monolithic composition" in table4_rows["five-component competitive-Langmuir/LDF microsteps"]["explicit boundary"]
        and "1,944–2,039 qubits" in table4_rows["direct normalized-transport/LDF/interior-balance paths"]["key result"]
        and "128,013,726 CX" in table4_rows["direct normalized-transport/LDF/interior-balance paths"]["key result"]
        and "monolithic five-component transpilation" in table4_rows["direct normalized-transport/LDF/interior-balance paths"]["explicit boundary"]
        and "valve 288 qubits/800,762 CX" in table4_rows["product-boundary valve and recycle-tank modules"]["key result"]
        and "five-component tank accounting 677 qubits/1,043,990 additive CX" in table4_rows["product-boundary valve and recycle-tank modules"]["key result"]
        and "97.40 mol" in table4_rows["product-boundary valve and recycle-tank modules"]["key result"]
        and "separate evidence tiers" in table4_rows["product-boundary valve and recycle-tank modules"]["explicit boundary"]
        and "842 qubits/2,348,388 CX" in table4_rows["direct product-valve-to-boundary-cell balance"]["key result"]
        and "depth 3,285,605" in table4_rows["direct product-valve-to-boundary-cell balance"]["key result"]
        and "normalization" in table4_rows["direct product-valve-to-boundary-cell balance"]["explicit boundary"]
        and "1,072–1,195 qubits" in table4_rows["direct product-cell LDF/valve/boundary-balance paths"]["key result"]
        and "10,060,060–26,810,396 CX" in table4_rows["direct product-cell LDF/valve/boundary-balance paths"]["key result"]
        and "88,388,552 additive CX" in table4_rows["direct product-cell LDF/valve/boundary-balance paths"]["key result"]
        and "product composition normalization" in table4_rows["direct product-cell LDF/valve/boundary-balance paths"]["explicit boundary"]
        and f"{min(row['logical_qubits'] for row in normalized_product_resources.values()):,}–{max(row['logical_qubits'] for row in normalized_product_resources.values()):,} qubits" in table4_rows["gas-inventory-generated product-cell LDF/valve/balance paths"]["key result"]
        and f"{min(row['cx'] for row in normalized_product_resources.values()):,}–{max(row['cx'] for row in normalized_product_resources.values()):,} CX" in table4_rows["gas-inventory-generated product-cell LDF/valve/balance paths"]["key result"]
        and f"{normalized_product_upper['cx_additive_upper_bound']:,} additive CX" in table4_rows["gas-inventory-generated product-cell LDF/valve/balance paths"]["key result"]
        and "finite-support run/schedule/tank interface" in table4_rows["gas-inventory-generated product-cell LDF/valve/balance paths"]["explicit boundary"]
        and "440 qubits/166,189 CX" in table4_rows["coherent run/schedule/tank interface"]["key result"]
        and "depth 324,495" in table4_rows["coherent run/schedule/tank interface"]["key result"]
        and "zero meaningful tank erasure" in table4_rows["coherent run/schedule/tank interface"]["key result"]
        and "continuous off-ledger evaluator" in table4_rows["coherent run/schedule/tank interface"]["explicit boundary"]
        and "495 qubits/353,441 CX" in table4_rows["coherent run-factor/LDF coefficient interface"]["key result"]
        and "depth 526,434" in table4_rows["coherent run-factor/LDF coefficient interface"]["key result"]
        and "4.987e-05" in table4_rows["coherent run-factor/LDF coefficient interface"]["key result"]
        and "4.356e-05" in table4_rows["coherent run-factor/LDF coefficient interface"]["key result"]
        and "reported separately" in table4_rows["coherent run-factor/LDF coefficient interface"]["explicit boundary"]
        and "1,297–1,486 qubits" in table4_rows["coherent coefficient-to-LDF/loading/balance paths"]["key result"]
        and "1,855,912–2,807,252 CX" in table4_rows["coherent coefficient-to-LDF/loading/balance paths"]["key result"]
        and "11,911,052 additive CX" in table4_rows["coherent coefficient-to-LDF/loading/balance paths"]["key result"]
        and "64,640 component-balance records" in table4_rows["coherent coefficient-to-LDF/loading/balance paths"]["system and size"]
        and "dynamic affinity-dependent denominator/reciprocal" in table4_rows["coherent coefficient-to-LDF/loading/balance paths"]["explicit boundary"]
        and "1,771–1,960 qubits" in table4_rows["coherent dynamic-Langmuir-to-LDF/loading/balance paths"]["key result"]
        and "41,440,216–42,391,556 CX" in table4_rows["coherent dynamic-Langmuir-to-LDF/loading/balance paths"]["key result"]
        and "209,832,572 additive CX" in table4_rows["coherent dynamic-Langmuir-to-LDF/loading/balance paths"]["key result"]
        and "64,640 component-balance records" in table4_rows["coherent dynamic-Langmuir-to-LDF/loading/balance paths"]["system and size"]
        and "20-bit pressure and five composition words are supplied" in table4_rows["coherent dynamic-Langmuir-to-LDF/loading/balance paths"]["explicit boundary"]
        and "2,696–2,885 qubits" in table4_rows["coherent gas-inventory-to-dynamic-Langmuir/transport/LDF/balance paths"]["key result"]
        and "55,337,688–56,289,028 CX" in table4_rows["coherent gas-inventory-to-dynamic-Langmuir/transport/LDF/balance paths"]["key result"]
        and "279,319,932 additive CX" in table4_rows["coherent gas-inventory-to-dynamic-Langmuir/transport/LDF/balance paths"]["key result"]
        and "25,856 normalization states" in table4_rows["coherent gas-inventory-to-dynamic-Langmuir/transport/LDF/balance paths"]["system and size"]
        and "without supplied pressure, composition, or face-flux words" in table4_rows["coherent gas-inventory-to-dynamic-Langmuir/transport/LDF/balance paths"]["supported role"]
        and "557 qubits/195,276 CX/depth 327,212" in table4_rows["pressure-derived saturated tank-withdrawal interface"]["key result"]
        and "128/128 saturation labels" in table4_rows["pressure-derived saturated tank-withdrawal interface"]["key result"]
        and "1.624404 mol" in table4_rows["pressure-derived saturated tank-withdrawal interface"]["key result"]
        and "2.033e-06" in table4_rows["pressure-derived saturated tank-withdrawal interface"]["key result"]
        and "replaces the recorded-withdrawal lookup" in table4_rows["pressure-derived saturated tank-withdrawal interface"]["supported role"]
        and "unsaturated proportional allocation" in table4_rows["pressure-derived saturated tank-withdrawal interface"]["explicit boundary"]
        and "647 qubits/705,194 CX/depth 1,127,046" in table4_rows["pressure-derived saturated/unsaturated proportional tank-allocation interface"]["key result"]
        and "128 saturated/224 unsaturated labels" in table4_rows["pressure-derived saturated/unsaturated proportional tank-allocation interface"]["key result"]
        and "1.687e-04" in table4_rows["pressure-derived saturated/unsaturated proportional tank-allocation interface"]["key result"]
        and "3.872e-04" in table4_rows["pressure-derived saturated/unsaturated proportional tank-allocation interface"]["key result"]
        and "closes the missing five-component proportional-allocation arithmetic branch" in table4_rows["pressure-derived saturated/unsaturated proportional tank-allocation interface"]["supported role"]
        and "counterfactuals" in table4_rows["pressure-derived saturated/unsaturated proportional tank-allocation interface"]["explicit boundary"]
        and "845 qubits/1,078,054 CX/depth 1,634,701" in table4_rows["model-derived physical unsaturated tank-trajectory control"]["key result"]
        and "128/128 unsaturated and zero-makeup calls" in table4_rows["model-derived physical unsaturated tank-trajectory control"]["key result"]
        and "0.853%" in table4_rows["model-derived physical unsaturated tank-trajectory control"]["key result"]
        and "short-schedule" in table4_rows["model-derived physical unsaturated tank-trajectory control"]["explicit boundary"]
        and "pressure 152 qubits/93,764 CX" in table4_rows["pressure reconstruction and oriented internal-face transport"]["key result"]
        and "face 404 qubits/1,340,390 CX" in table4_rows["pressure reconstruction and oriented internal-face transport"]["key result"]
        and "584 qubits/1,527,918 additive CX" in table4_rows["pressure reconstruction and oriented internal-face transport"]["key result"]
        and "composition normalization" in table4_rows["pressure reconstruction and oriented internal-face transport"]["explicit boundary"]
        and "1,508 qubits/8,328,622 CX" in table4_rows["direct pressure-to-two-face-to-interior-cell balance"]["key result"]
        and "depth 12,250,291" in table4_rows["direct pressure-to-two-face-to-interior-cell balance"]["key result"]
        and "normalization" in table4_rows["direct pressure-to-two-face-to-interior-cell balance"]["explicit boundary"]
        and "1,651 qubits/14,667,150 CX" in table4_rows["direct gas-normalization-to-two-face-to-interior-cell balance"]["key result"]
        and "depth 22,143,683" in table4_rows["direct gas-normalization-to-two-face-to-interior-cell balance"]["key result"]
        and "standalone normalizer 333 qubits/1,340,232 CX" in table4_rows["direct gas-normalization-to-two-face-to-interior-cell balance"]["key result"]
        and "2.071e-04" in table4_rows["direct gas-normalization-to-two-face-to-interior-cell balance"]["key result"]
        and "support-adaptive" in table4_rows["direct gas-normalization-to-two-face-to-interior-cell balance"]["explicit boundary"]
        and "loading bits 26/26/32/32/30" in table4_rows["direct LDF-to-loading-sign-to-cell-balance composition"]["key result"]
        and "861–929 qubits" in table4_rows["direct LDF-to-loading-sign-to-cell-balance composition"]["key result"]
        and "3,412,254–4,991,534 CX" in table4_rows["direct LDF-to-loading-sign-to-cell-balance composition"]["key result"]
        and "1,317 qubits/19,082,852 additive CX" in table4_rows["direct LDF-to-loading-sign-to-cell-balance composition"]["key result"]
        and "934 qubits/1,411,882 additive CX" in table4_rows["direct LDF-to-loading-sign-to-cell-balance composition"]["key result"]
        and "constant-specialized" in table4_rows["direct LDF-to-loading-sign-to-cell-balance composition"]["explicit boundary"]
        and "event labels 32/32" in table4_rows["primary phase-stream event bridge"]["key result"]
        and "final event 125 qubits/182,981 clean CX" in table4_rows["primary phase-stream event bridge"]["key result"]
        and "observed phase-start states" in table4_rows["primary phase-stream event bridge"]["independence"]
        and "integrated policy-specific arithmetic is reported separately" in table4_rows["primary phase-stream event bridge"]["explicit boundary"]
        and "candidate labels 96/96" in table4_rows["primary policy stream-to-event clean oracle"]["key result"]
        and "ledger-support labels 32/32" in table4_rows["primary policy stream-to-event clean oracle"]["key result"]
        and "510 qubits/1,286,021 CX" in table4_rows["primary policy stream-to-event clean oracle"]["key result"]
        and "stable physical/reversible CSS" in table4_rows["primary policy stream-to-event clean oracle"]["explicit boundary"]
        and "no held dynamic state supplied" in table4_rows["parameter-only CSS initializer and cycle screen"]["independence"]
        and "one-cycle labels 32/32" in table4_rows["parameter-only CSS initializer and cycle screen"]["key result"]
        and "50-cycle terminal labels 28/32" in table4_rows["parameter-only CSS initializer and cycle screen"]["key result"]
        and "unanchored/stabilized 50-cycle CSS gates 2/32 and 32/32" in table4_rows["parameter-only CSS initializer and cycle screen"]["explicit boundary"]
        and "purge/feed is not product recycle" in table4_rows["TU Wien H2/CH4 literature data"]["explicit boundary"]
        and "0.133" in table4_rows["TU Wien H2/CH4 literature data"]["key result"]
        and "does not reproduce 0.420" in table4_rows["public dynamic CO2/N2 model"]["explicit boundary"]
        and "purity, recovery, tank, and CSS gates fail" in table4_rows["independent pyAPEP H2 recycle code path"]["explicit boundary"]
        and "0.99167" in table4_rows["independent pyAPEP H2 recycle code path"]["key result"]
        and "75.87%" in table4_rows["public toPSAil/Yang H2 model and experiment"]["key result"]
        and "no 0.420 validation" in table4_rows["public toPSAil/Yang H2 model and experiment"]["explicit boundary"],
        f"table1={len(table1_rows)}, table2={len(table2_rows)}, table4={len(table4_rows)}",
    )
    validity_panels = cce_validity_figure["panels"]
    _check(
        checks,
        "CCE main-text validity boundary figure values",
        cce_validity_figure["status"]
        == "main_text_validity_boundary_assembled_external_h2_selection_gate_open"
        and abs(float(validity_panels["a"]["stress_p025"]) - 0.46826171875) < 1e-12
        and abs(float(validity_panels["a"]["stress_p975"]) - 0.47607421875) < 1e-12
        and validity_panels["c"]["purity_direction_match_count"] == 4
        and abs(float(validity_panels["d"]["scenario_ratios"]["t9_vac_long_slow"]) - 0.017181401848101224) < 1e-12
        and abs(float(validity_panels["d"]["scenario_ratios"]["t14_kCO2_low"]) - 0.0032613252087200194) < 1e-12,
        f"stress=[{validity_panels['a']['stress_p025']},{validity_panels['a']['stress_p975']}], ratios={validity_panels['d']['scenario_ratios']}",
    )
    _check(
        checks,
        "direct physical phase ledger values",
        phase_ledger["status"] == "direct_reduced_physical_phase_ledger_one_cycle_calibration_interface"
        and phase_ledger["source_row_count"] == 20
        and phase_ledger["phase_call_count"] == 160
        and phase_ledger["equalization_call_count"] == 40
        and abs(float(phase_ledger["max_phase_mass_balance_relative"]) - 1.9325151473222348e-05) < 1e-12
        and abs(float(phase_ledger["max_equalization_mass_residual_mol"]) - 2.842170943040401e-14) < 1e-15
        and phase_ledger["equalization_cap_active_calls"] == 0
        and phase_ledger["all_phase_mass_balance_below_1e_3"]
        and phase_ledger["all_equalization_mass_residual_zero_to_tolerance"],
        f"phase_calls={phase_ledger['phase_call_count']}, eq_calls={phase_ledger['equalization_call_count']}, max_phase={phase_ledger['max_phase_mass_balance_relative']}",
    )
    _check(
        checks,
        "direct physical seed panel values",
        seed_panel["status"] == "direct_physical_reduced_oracle_seed_panel_not_formal_asymptotic_convergence"
        and seed_panel["record_count"] == 16
        and len(seed_panel["source_summaries"]) == 8
        and seed_panel["all_rows_css_and_mass_balance_pass"],
        f"summaries={len(seed_panel['source_summaries'])}, records={seed_panel['record_count']}",
    )
    _check(
        checks,
        "strict CSS 16-cell refinement values",
        strict_css_16cell["status"] == "strict_css_16cell_screen_representative_uncalibrated_oracle"
        and strict_css_16cell["cells_compared"] == [4, 8, 16]
        and strict_css_16cell["horizons"] == [40]
        and len(strict_css_16cell["rows"]) == 3
        and sum(bool(row["strict_css_gate_pass"]) for row in strict_css_16cell["rows"]) == 1
        and all(bool(row["l1_css_gate_pass"]) and bool(row["mass_balance_gate_pass"]) for row in strict_css_16cell["rows"])
        and abs(float(strict_css_16cell["rows"][0]["css_residual_max"]) - 0.0002444965484279619) < 1e-12
        and abs(float(strict_css_16cell["rows"][1]["css_residual_max"]) - 6.89732299052892e-08) < 1e-15
        and abs(float(strict_css_16cell["rows"][2]["css_residual_max"]) - 0.00010780374133037797) < 1e-12,
        f"rows={len(strict_css_16cell['rows'])}, strict_pass={sum(bool(row['strict_css_gate_pass']) for row in strict_css_16cell['rows'])}/3",
    )
    _check(
        checks,
        "industrial 8-bed benchmark bridge values",
        industrial_8bed_bridge["status"] == "direct_reduced_oracle_methodological_bridge_not_calibrated_to_industrial_target"
        and abs(float(industrial_8bed_bridge["threshold_gaps_vs_reported_optimized"]["purity"]) - 0.0199) < 1e-12
        and abs(float(industrial_8bed_bridge["threshold_gaps_vs_reported_optimized"]["recovery"]) - 0.1659) < 1e-12
        and abs(float(industrial_8bed_bridge["rows"][1]["h2_purity"]) - 0.9999) < 1e-12
        and abs(float(industrial_8bed_bridge["rows"][1]["h2_recovery"]) - 0.6659) < 1e-12,
        f"purity_gap={industrial_8bed_bridge['threshold_gaps_vs_reported_optimized']['purity']}, recovery_gap={industrial_8bed_bridge['threshold_gaps_vs_reported_optimized']['recovery']}",
    )
    _check(
        checks,
        "industrial target event negative-control boundary",
        industrial_target_boundary["status"] == "industrial_target_event_negative_control_reduced_oracle_not_calibrated"
        and industrial_target_boundary["total_direct_rows"] == 1376
        and industrial_target_boundary["all_industrial_event_counts_zero"]
        and industrial_target_boundary["all_rows_css_and_mass_balance_pass"]
        and abs(float(industrial_target_boundary["max_h2_product_observed"]) - 0.9847089043902868) < 1e-12
        and abs(float(industrial_target_boundary["purity_gap_to_industrial_target"]) - 0.015191095609713212) < 1e-12,
        f"rows={industrial_target_boundary['total_direct_rows']}, industrial_pass={sum(row['industrial_event_count'] for row in industrial_target_boundary['rows'])}, max_h2={industrial_target_boundary['max_h2_product_observed']}",
    )
    _check(
        checks,
        "reduced calibration-localization grid values",
        reduced_calibration_localization["status"] == "reduced_psa_calibration_localization_not_fitted_to_industrial_target"
        and len(reduced_calibration_localization["rows"]) == 48
        and reduced_calibration_localization["valid_row_count"] == 47
        and abs(float(reduced_calibration_localization["best_normalized_target_gap"]["normalized_target_gap"]) - 1.5673045123062592) < 1e-12
        and abs(float(reduced_calibration_localization["best_normalized_target_gap"]["h2_product"]) - 0.9853987008859662) < 1e-12
        and abs(float(reduced_calibration_localization["best_normalized_target_gap"]["h2_recovery_proxy"]) - 0.6064385272341184) < 1e-12
        and abs(float(reduced_calibration_localization["maximum_purity_row"]["h2_product"]) - 0.9863315961600854) < 1e-12,
        f"rows={len(reduced_calibration_localization['rows'])}, valid={reduced_calibration_localization['valid_row_count']}, best_gap={reduced_calibration_localization['best_normalized_target_gap']['normalized_target_gap']}",
    )
    _check(
        checks,
        "hybrid policy-selection bootstrap values",
        hybrid_policy_bootstrap["status"] == "finite_physical_policy_selection_bootstrap_stability_control"
        and hybrid_policy_bootstrap["bootstrap_replicates"] == 10000
        and hybrid_policy_bootstrap["sample_count_per_policy"] == 16
        and hybrid_policy_bootstrap["empirical_selection_counts"] == {"0.410": 6040, "0.427": 3960, "0.440": 0, "none": 0}
        and hybrid_policy_bootstrap["confidence_selection_counts"] == {"0.410": 9976, "0.427": 24, "0.440": 0, "none": 0}
        and hybrid_policy_bootstrap["observed_empirical_selection"] == 0.41
        and hybrid_policy_bootstrap["observed_confidence_selection"] == 0.41,
        f"replicates={hybrid_policy_bootstrap['bootstrap_replicates']}, empirical={hybrid_policy_bootstrap['empirical_selection_counts']}, confidence={hybrid_policy_bootstrap['confidence_selection_counts']}",
    )
    threshold_anchor = next(
        row
        for row in hybrid_policy_threshold["grid_summary"]
        if row["purity_threshold"] == 0.9998 and row["recovery_threshold"] == 0.789
    )
    threshold_industrial = next(
        row
        for row in hybrid_policy_threshold["grid_summary"]
        if row["purity_threshold"] == 0.9999 and row["recovery_threshold"] == 0.6659
    )
    threshold_relaxed = next(
        row
        for row in hybrid_policy_threshold["grid_summary"]
        if row["purity_threshold"] == 0.9998 and row["recovery_threshold"] == 0.75
    )
    threshold_strict = next(
        row
        for row in hybrid_policy_threshold["grid_summary"]
        if row["purity_threshold"] == 0.99987 and row["recovery_threshold"] == 0.789
    )
    _check(
        checks,
        "hybrid policy event-threshold sensitivity values",
        hybrid_policy_threshold["status"] == "finite_physical_policy_threshold_sensitivity_not_threshold_calibrated"
        and len(hybrid_policy_threshold["rows"]) == 48
        and threshold_anchor["empirical_selected_policy"] == 0.41
        and threshold_anchor["confidence_selected_policy"] == 0.41
        and threshold_relaxed["empirical_selected_policy"] == 0.44
        and threshold_strict["empirical_selected_policy"] is None
        and threshold_industrial["empirical_selected_policy"] is None
        and all(row["internal_gate_pass_count"] == 16 for row in hybrid_policy_threshold["rows"]),
        f"rows={len(hybrid_policy_threshold['rows'])}, anchor={threshold_anchor['empirical_selected_policy']}, relaxed={threshold_relaxed['empirical_selected_policy']}, strict={threshold_strict['empirical_selected_policy']}, industrial={threshold_industrial['empirical_selected_policy']}",
    )
    direct_noise_100 = [
        row
        for row in hybrid_policy_direct_noise["rows"]
        if int(row["shots_per_power"]) == 100
    ]
    direct_noise_by_key = {
        (round(float(row["bit_flip_probability"]), 2), row["method"]): row
        for row in direct_noise_100
    }
    _check(
        checks,
        "direct physical hybrid-policy noise values",
        hybrid_policy_direct_noise["status"] == "direct_physical_policy_non_degenerate_mlae_noise_control"
        and hybrid_policy_direct_noise["physical_pass_count"] == 7
        and hybrid_policy_direct_noise["physical_label_count"] == 16
        and len(hybrid_policy_direct_noise["rows"]) == 24
        and abs(float(direct_noise_by_key[(0.0, "noisy_MLAE_assuming_ideal_model")]["rmse"]) - 0.0033061193263401755) < 1e-12
        and abs(float(direct_noise_by_key[(0.01, "noisy_MLAE_assuming_ideal_model")]["rmse"]) - 0.0026535094686094495) < 1e-12
        and abs(float(direct_noise_by_key[(0.05, "noisy_MLAE_assuming_ideal_model")]["rmse"]) - 0.007675008143318159) < 1e-12
        and abs(float(direct_noise_by_key[(0.0, "MC_same_oracle_query_budget")]["rmse"]) - 0.008554912659533403) < 1e-12,
        f"rows={len(hybrid_policy_direct_noise['rows'])}, p={hybrid_policy_direct_noise['exact_probability']}, noise_levels={hybrid_policy_direct_noise['noise_levels']}",
    )

    expected_sources = [
        "10_TEA_LCA_Python/psa_qae/psa_qae_breakthrough_risk_bridge.json",
        "10_TEA_LCA_Python/psa_qae/psa_qae_policy_physical_mc_qmc_convergence.json",
        "10_TEA_LCA_Python/psa_qae/qae_psa_oracle_cost_crossover.json",
        "10_TEA_LCA_Python/results/pycharm_publication_enhancement/QAE_PHYSICAL_POLICY_128_MLAE_NOISE.json",
    ]
    figure_sources = case_spec["internal_two_tier_figure"]["data_sources"]
    _check(
        checks,
        "Figure 1 data-source manifest",
        figure_sources == expected_sources,
        f"sources={figure_sources}",
    )
    _check(
        checks,
        "Figure 1 script source alignment",
        "psa_qae_policy_physical_mc_qmc_convergence.json" in figure_script
        and "QAE_PHYSICAL_POLICY_128_MLAE_NOISE.json" in figure_script
        and "psa_qae_policy_spatial_tank_event_mid_replicate_convergence.json" not in figure_script
        and "qae_breakthrough_event_mlae_benchmark.json" not in figure_script,
        "current direct reduced-PSA inputs are used",
    )
    validation_checks = {check["name"]: check for check in validation["checks"]}
    physical_validation = validation_checks.get("physical policy convergence gates", {})
    _check(
        checks,
        "validation artifact",
        validation["status"] == "pass"
        and "sample_sizes=[16, 32, 64, 128]" in physical_validation.get("detail", ""),
        f"status={validation['status']}, detail={physical_validation.get('detail', '')}",
    )

    required_artifacts = [
        results / "PSA_QAE_CCE_WORKFLOW_FIGURE.png",
        results / "PSA_QAE_CCE_WORKFLOW_FIGURE.pdf",
        results / "PSA_QAE_TWO_TIER_FIGURE.png",
        results / "PSA_QAE_TWO_TIER_FIGURE.pdf",
        convergence_path,
        mlae_path,
        tuwien_qpe_path,
        results / "QAE_TUWIEN_H2_STATEVECTOR_QPE_FIGURE.png",
        tuwien_mlae_path,
        results / "QAE_TUWIEN_H2_MLAE_NOISE_FIGURE.png",
        tuwien_uncertainty_path,
        results / "QAE_TUWIEN_H2_UNCERTAINTY_STATEVECTOR_QPE_FIGURE.png",
        tuwien_resource_path,
        results / "QAE_TUWIEN_H2_RESOURCE_BOUNDARY_FIGURE.png",
        tuwien_structured_loader_path,
        results / "QAE_TUWIEN_H2_STRUCTURED_LOADER_BOUNDARY_FIGURE.png",
        hybrid_policy_selection_path,
        results / "QAE_HYBRID_POLICY_SELECTION_PHYSICAL_16X3_FIGURE.png",
        surrogate_continuous_qpe_path,
        results / "QAE_INDEPENDENT_SOURCE_SURROGATE_CONTINUOUS_QPE_FIGURE.png",
        quadratic_holdout_path,
        here / "psa_independent_source_quadratic_surrogate_holdout_32.csv",
        here / "PSA_INDEPENDENT_SOURCE_QUADRATIC_SURROGATE_HOLDOUT_32.md",
        continuous_policy_selection_path,
        results / "PSA_QAE_CONTINUOUS_POLICY_SELECTION.csv",
        results / "PSA_QAE_CONTINUOUS_POLICY_SELECTION.md",
        results / "PSA_QAE_CONTINUOUS_POLICY_SELECTION_FIGURE.png",
        policy_sample_size_path,
        results / "PSA_QAE_POLICY_SAMPLE_SIZE_DESIGN.csv",
        results / "PSA_QAE_POLICY_SAMPLE_SIZE_DESIGN.md",
        results / "PSA_QAE_POLICY_SAMPLE_SIZE_DESIGN_FIGURE.png",
        cvar_loss_bridge_path,
        here / "psa_qae_cvar_loss_bridge.csv",
        here / "PSA_QAE_CVAR_LOSS_BRIDGE.md",
        here / "PSA_QAE_CVAR_LOSS_BRIDGE_FIGURE.png",
        here / "PSA_QAE_CVAR_LOSS_BRIDGE_FIGURE.pdf",
        direct_tail_stability_path,
        here / "psa_qae_direct_physical_tail_stability.csv",
        here / "PSA_QAE_DIRECT_PHYSICAL_TAIL_STABILITY.md",
        here / "PSA_QAE_DIRECT_PHYSICAL_TAIL_STABILITY_FIGURE.png",
        here / "PSA_QAE_DIRECT_PHYSICAL_TAIL_STABILITY_FIGURE.pdf",
        tail_loss_oracle_path,
        results / "PSA_QAE_DIRECT_PHYSICAL_TAIL_LOSS_ORACLE.csv",
        results / "PSA_QAE_DIRECT_PHYSICAL_TAIL_LOSS_ORACLE.md",
        results / "PSA_QAE_DIRECT_PHYSICAL_TAIL_LOSS_ORACLE_FIGURE.png",
        results / "PSA_QAE_DIRECT_PHYSICAL_TAIL_LOSS_ORACLE_FIGURE.pdf",
        tail_amplitude_oracle_path,
        results / "PSA_QAE_DIRECT_PHYSICAL_TAIL_AMPLITUDE_ORACLE.csv",
        results / "PSA_QAE_DIRECT_PHYSICAL_TAIL_AMPLITUDE_ORACLE.md",
        results / "PSA_QAE_DIRECT_PHYSICAL_TAIL_AMPLITUDE_ORACLE_FIGURE.png",
        results / "PSA_QAE_DIRECT_PHYSICAL_TAIL_AMPLITUDE_ORACLE_FIGURE.pdf",
        tail_amplitude_mlae_path,
        results / "QAE_DIRECT_PHYSICAL_TAIL_AMPLITUDE_MLAE_NOISE.csv",
        results / "QAE_DIRECT_PHYSICAL_TAIL_AMPLITUDE_MLAE_NOISE.md",
        results / "QAE_DIRECT_PHYSICAL_TAIL_AMPLITUDE_MLAE_NOISE_FIGURE.png",
        results / "QAE_DIRECT_PHYSICAL_TAIL_AMPLITUDE_MLAE_NOISE_FIGURE.pdf",
        tail_end_to_end_path,
        results / "QAE_DIRECT_PHYSICAL_TAIL_END_TO_END_BOUNDARY.csv",
        results / "QAE_DIRECT_PHYSICAL_TAIL_END_TO_END_BOUNDARY.md",
        results / "QAE_DIRECT_PHYSICAL_TAIL_END_TO_END_BOUNDARY_FIGURE.png",
        results / "QAE_DIRECT_PHYSICAL_TAIL_END_TO_END_BOUNDARY_FIGURE.pdf",
        tail_loader_crossover_path,
        results / "QAE_TAIL_LOADER_RESOURCE_CROSSOVER.csv",
        results / "QAE_TAIL_LOADER_RESOURCE_CROSSOVER.md",
        results / "QAE_TAIL_LOADER_RESOURCE_CROSSOVER_FIGURE.png",
        results / "QAE_TAIL_LOADER_RESOURCE_CROSSOVER_FIGURE.pdf",
        process_parameter_prior_path,
        results / "QAE_PROCESS_PARAMETER_CONTINUOUS_PRIOR.csv",
        results / "QAE_PROCESS_PARAMETER_CONTINUOUS_PRIOR.md",
        results / "QAE_PROCESS_PARAMETER_CONTINUOUS_PRIOR_FIGURE.png",
        results / "QAE_PROCESS_PARAMETER_CONTINUOUS_PRIOR_FIGURE.pdf",
        process_parameter_resource_path,
        results / "QAE_PROCESS_PARAMETER_RESOURCE_BOUNDARY.csv",
        results / "QAE_PROCESS_PARAMETER_RESOURCE_BOUNDARY.md",
        results / "QAE_PROCESS_PARAMETER_RESOURCE_BOUNDARY_FIGURE.png",
        results / "QAE_PROCESS_PARAMETER_RESOURCE_BOUNDARY_FIGURE.pdf",
        process_prior_weight_path,
        results / "QAE_PROCESS_PARAMETER_PRIOR_WEIGHT_SENSITIVITY.csv",
        results / "QAE_PROCESS_PARAMETER_PRIOR_WEIGHT_SENSITIVITY.md",
        results / "QAE_PROCESS_PARAMETER_PRIOR_WEIGHT_SENSITIVITY_FIGURE.png",
        results / "QAE_PROCESS_PARAMETER_PRIOR_WEIGHT_SENSITIVITY_FIGURE.pdf",
        discrepancy_boundary_path,
        results / "QAE_SURROGATE_MODEL_DISCREPANCY_BOUNDARY_FIGURE.png",
        rare_tail_boundary_path,
        results / "QAE_SURROGATE_RARE_TAIL_BOUNDARY_FIGURE.png",
        direct_physical_rare_tail_boundary_path,
        results / "QAE_DIRECT_PHYSICAL_RARE_TAIL_BOUNDARY_FIGURE.png",
        direct_physical_rare_tail_replicates_path,
        results / "QAE_DIRECT_PHYSICAL_RARE_TAIL_REPLICATES_N32_FIGURE.png",
        direct_physical_rare_tail_mlae_path,
        results / "QAE_DIRECT_PHYSICAL_RARE_TAIL_MLAE_NOISE_FIGURE.png",
        cross_oracle_model_form_path,
        results / "QAE_CROSS_ORACLE_RECOVERY_MODEL_FORM_BOUNDARY_FIGURE.png",
        paired_oracle_model_form_path,
        results / "QAE_PAIRED_ORACLE_RECOVERY_BOUNDARY_K8_FIGURE.png",
        paired_oracle_model_form_k16_path,
        results / "QAE_PAIRED_ORACLE_RECOVERY_BOUNDARY_K16_FIGURE.png",
        paired_oracle_model_form_k32_path,
        results / "QAE_PAIRED_ORACLE_RECOVERY_BOUNDARY_K32_FIGURE.png",
        paired_oracle_k_progress_path,
        results / "QAE_PAIRED_ORACLE_K_PROGRESS_SUMMARY_FIGURE.png",
        literature_gap_path,
        references_path,
        end_to_end_resource_path,
        results / "QAE_END_TO_END_RESOURCE_SUMMARY_FIGURE.png",
        strict_css_horizon_path,
        results / "QAE_STRICT_CSS_HORIZON_SCREEN_FIGURE.png",
        strict_css_mesh_path,
        results / "QAE_STRICT_CSS_MESH_SCREEN_FIGURE.png",
        results / "PSA_QAE_SCI_SUBMISSION_GATE.md",
        results / "PSA_QAE_SCI_SUBMISSION_GATE.json",
        results / "PSA_QAE_SCI_JOURNAL_TARGETS_2026.md",
        here / "PSA_CLASSICAL_2026_8BED_BASELINE.md",
        here / "psa_classical_2026_8bed_baseline.json",
        high_n_extension_path,
        results / "PSA_QAE_POLICY_PHYSICAL_HIGH_N_EXTENSION_FIGURE.png",
        n128_replicate_extension_path,
        results / "PSA_QAE_POLICY_PHYSICAL_128_REPLICATE_EXTENSION_FIGURE.png",
        seed_panel_path,
        results / "PSA_QAE_DIRECT_PHYSICAL_SEED_PANEL.csv",
        results / "PSA_QAE_DIRECT_PHYSICAL_SEED_PANEL.md",
        structured_loader_path,
        results / "PSA_QAE_STRUCTURED_EMPIRICAL_LOADER.csv",
        results / "PSA_QAE_STRUCTURED_EMPIRICAL_LOADER.md",
        results / "PSA_QAE_STRUCTURED_EMPIRICAL_LOADER_FIGURE.png",
        reversible_cycle_path,
        results / "PSA_QAE_REVERSIBLE_FIXED_POINT_CYCLE_CONTROL.csv",
        results / "PSA_QAE_REVERSIBLE_FIXED_POINT_CYCLE_CONTROL.md",
        results / "PSA_QAE_REVERSIBLE_FIXED_POINT_CYCLE_CONTROL_FIGURE.png",
        primary_finite_gate_path,
        results / "PSA_QAE_CCE_PRIMARY_FINITE_ORACLE_GATE_RESOURCES.csv",
        results / "PSA_QAE_CCE_PRIMARY_FINITE_ORACLE_GATE_RESOURCES.md",
        results / "PSA_QAE_CCE_PRIMARY_FINITE_ORACLE_GATE_RESOURCES_FIGURE.png",
        primary_finite_ibm_preflight_path,
        results / "PSA_QAE_CCE_PRIMARY_FINITE_ORACLE_IBM_PREFLIGHT_ibm_marrakesh.csv",
        results / "PSA_QAE_CCE_PRIMARY_FINITE_ORACLE_IBM_PREFLIGHT_ibm_marrakesh.md",
        primary_linear_oracle_path,
        results / "PSA_QAE_CCE_PRIMARY_LINEAR_SURROGATE_ORACLE.csv",
        results / "PSA_QAE_CCE_PRIMARY_LINEAR_SURROGATE_ORACLE.md",
        results / "PSA_QAE_CCE_PRIMARY_LINEAR_SURROGATE_ORACLE_FIGURE.png",
        primary_copula_loader_path,
        results / "PSA_QAE_CCE_PRIMARY_COPULA_STATE_LOADER.csv",
        results / "PSA_QAE_CCE_PRIMARY_COPULA_STATE_LOADER.md",
        results / "PSA_QAE_CCE_PRIMARY_COPULA_STATE_LOADER_FIGURE.png",
        primary_threshold_activity_path,
        results / "PSA_QAE_CCE_PRIMARY_THRESHOLD_ACTIVITY.csv",
        results / "PSA_QAE_CCE_PRIMARY_THRESHOLD_ACTIVITY.md",
        results / "PSA_QAE_CCE_PRIMARY_THRESHOLD_ACTIVITY_FIGURE.png",
        cce_gate_manifest_path,
        results / "PSA_QAE_CCE_GATE_COMPILATION_MANIFEST.md",
        cce_external_policy_path,
        results / "PSA_QAE_CCE_EXTERNAL_LIGHT_PRODUCT_POLICY_VALIDATION.csv",
        results / "PSA_QAE_CCE_EXTERNAL_LIGHT_PRODUCT_POLICY_VALIDATION.md",
        results / "PSA_QAE_CCE_EXTERNAL_LIGHT_PRODUCT_POLICY_VALIDATION_FIGURE.png",
        cce_external_refinement_path,
        results / "PSA_QAE_CCE_EXTERNAL_POLICY_NUMERICAL_REFINEMENT.csv",
        results / "PSA_QAE_CCE_EXTERNAL_POLICY_NUMERICAL_REFINEMENT.md",
        cce_h2_resolution_path,
        results / "PSA_QAE_CCE_INDEPENDENT_H2_POLICY_RESOLUTION_AUDIT.csv",
        results / "PSA_QAE_CCE_INDEPENDENT_H2_POLICY_RESOLUTION_AUDIT.md",
        results / "PSA_QAE_CCE_INDEPENDENT_H2_POLICY_RESOLUTION_AUDIT_FIGURE.png",
        results / "PSA_QAE_CCE_INDEPENDENT_H2_POLICY_RESOLUTION_AUDIT_FIGURE.pdf",
        cce_prospective_design_path,
        results / "PSA_QAE_CCE_PROSPECTIVE_POLICY_DESIGN_AUDIT.csv",
        results / "PSA_QAE_CCE_PROSPECTIVE_POLICY_DESIGN_AUDIT.md",
        results / "PSA_QAE_CCE_PROSPECTIVE_POLICY_DESIGN_AUDIT_FIGURE.png",
        results / "PSA_QAE_CCE_PROSPECTIVE_POLICY_DESIGN_AUDIT_FIGURE.pdf",
        cce_phase_map_path,
        results / "PSA_QAE_CCE_CALIBRATED_ONE_CYCLE_PHASE_MAP.csv",
        results / "PSA_QAE_CCE_CALIBRATED_ONE_CYCLE_PHASE_MAP.md",
        results / "PSA_QAE_CCE_CALIBRATED_ONE_CYCLE_PHASE_MAP_FIGURE.png",
        cce_phase_map_fixed_point_path,
        results / "PSA_QAE_CCE_PHASE_MAP_FIXED_POINT_SCREEN.csv",
        results / "PSA_QAE_CCE_PHASE_MAP_FIXED_POINT_SCREEN.md",
        results / "PSA_QAE_CCE_PHASE_MAP_FIXED_POINT_SCREEN_FIGURE.png",
        results / "PSA_QAE_CCE_PHASE_MAP_FIXED_POINT_SCREEN_FIGURE.pdf",
        cce_phase_map_compile_path,
        results / "PSA_QAE_CCE_PHASE_MAP_AFFINE_BLOCK_COMPILE.csv",
        results / "PSA_QAE_CCE_PHASE_MAP_AFFINE_BLOCK_COMPILE.md",
        results / "PSA_QAE_CCE_PHASE_MAP_AFFINE_BLOCK_COMPILE_FIGURE.png",
        results / "PSA_QAE_CCE_PHASE_MAP_AFFINE_BLOCK_COMPILE_FIGURE.pdf",
        cce_small_e2e_path,
        results / "PSA_QAE_CCE_SMALL_END_TO_END_ORACLE.csv",
        results / "PSA_QAE_CCE_SMALL_END_TO_END_ORACLE.md",
        results / "PSA_QAE_CCE_SMALL_END_TO_END_ORACLE_FIGURE.png",
        results / "PSA_QAE_CCE_SMALL_END_TO_END_ORACLE_FIGURE.pdf",
        cce_primary_phase_ledger_path,
        results / "PSA_QAE_CCE_PRIMARY_PHASE_LEDGER.csv",
        results / "PSA_QAE_CCE_PRIMARY_PHASE_LEDGER.md",
        results / "PSA_QAE_CCE_PRIMARY_PHASE_LEDGER_FIGURE.png",
        results / "PSA_QAE_CCE_PRIMARY_PHASE_LEDGER_FIGURE.pdf",
        cce_primary_physical_css_path,
        results / "PSA_QAE_CCE_PRIMARY_PHYSICAL_CSS_HORIZON_AUDIT.csv",
        results / "PSA_QAE_CCE_PRIMARY_PHYSICAL_CSS_HORIZON_AUDIT.md",
        results / "PSA_QAE_CCE_PRIMARY_PHYSICAL_CSS_HORIZON_AUDIT_FIGURE.png",
        results / "PSA_QAE_CCE_PRIMARY_PHYSICAL_CSS_HORIZON_AUDIT_FIGURE.pdf",
        cce_primary_qstar_microkernel_path,
        results / "PSA_QAE_CCE_PRIMARY_QSTAR_REVERSIBLE_MICROKERNEL.csv",
        results / "PSA_QAE_CCE_PRIMARY_QSTAR_REVERSIBLE_MICROKERNEL.md",
        results / "PSA_QAE_CCE_PRIMARY_QSTAR_REVERSIBLE_MICROKERNEL_FIGURE.png",
        results / "PSA_QAE_CCE_PRIMARY_QSTAR_REVERSIBLE_MICROKERNEL_FIGURE.pdf",
        cce_primary_qstar_ldf_microstep_path,
        results / "PSA_QAE_CCE_PRIMARY_QSTAR_LDF_REVERSIBLE_MICROSTEP.csv",
        results / "PSA_QAE_CCE_PRIMARY_QSTAR_LDF_REVERSIBLE_MICROSTEP.md",
        results / "PSA_QAE_CCE_PRIMARY_QSTAR_LDF_REVERSIBLE_MICROSTEP_FIGURE.png",
        results / "PSA_QAE_CCE_PRIMARY_QSTAR_LDF_REVERSIBLE_MICROSTEP_FIGURE.pdf",
        cce_primary_all_component_ldf_path,
        results / "PSA_QAE_CCE_PRIMARY_ALL_COMPONENT_LDF_MICROSTEPS.csv",
        results / "PSA_QAE_CCE_PRIMARY_ALL_COMPONENT_LDF_MICROSTEPS.md",
        cce_primary_product_boundary_path,
        results / "PSA_QAE_CCE_PRIMARY_PRODUCT_BOUNDARY_MICROSTEPS.csv",
        results / "PSA_QAE_CCE_PRIMARY_PRODUCT_BOUNDARY_MICROSTEPS.md",
        cce_primary_product_boundary_balance_path,
        results / "PSA_QAE_CCE_PRIMARY_PRODUCT_BOUNDARY_BALANCE_COMPOSITION.csv",
        results / "PSA_QAE_CCE_PRIMARY_PRODUCT_BOUNDARY_BALANCE_COMPOSITION.md",
        cce_primary_product_ldf_valve_balance_path,
        results / "PSA_QAE_CCE_PRIMARY_PRODUCT_LDF_VALVE_BALANCE_COMPOSITION.csv",
        results / "PSA_QAE_CCE_PRIMARY_PRODUCT_LDF_VALVE_BALANCE_COMPOSITION.md",
        cce_primary_normalized_product_ldf_valve_balance_path,
        results / "PSA_QAE_CCE_PRIMARY_NORMALIZED_PRODUCT_LDF_VALVE_BALANCE.csv",
        results / "PSA_QAE_CCE_PRIMARY_NORMALIZED_PRODUCT_LDF_VALVE_BALANCE.md",
        cce_primary_coherent_run_schedule_tank_path,
        results / "PSA_QAE_CCE_COHERENT_RUN_SCHEDULE_TANK_INTERFACE.csv",
        results / "PSA_QAE_CCE_COHERENT_RUN_SCHEDULE_TANK_INTERFACE.md",
        cce_primary_coherent_run_factor_ldf_path,
        results / "PSA_QAE_CCE_COHERENT_RUN_FACTOR_LDF_INTERFACE.csv",
        results / "PSA_QAE_CCE_COHERENT_RUN_FACTOR_LDF_INTERFACE.md",
        cce_primary_coherent_coefficient_ldf_balance_path,
        results / "PSA_QAE_CCE_COHERENT_COEFFICIENT_LDF_BALANCE_INTERFACE.csv",
        results / "PSA_QAE_CCE_COHERENT_COEFFICIENT_LDF_BALANCE_INTERFACE.md",
        cce_primary_coherent_dynamic_langmuir_ldf_balance_path,
        results / "PSA_QAE_CCE_COHERENT_DYNAMIC_LANGMUIR_LDF_BALANCE_INTERFACE.csv",
        results / "PSA_QAE_CCE_COHERENT_DYNAMIC_LANGMUIR_LDF_BALANCE_INTERFACE.md",
        cce_primary_coherent_normalized_dynamic_transport_ldf_balance_path,
        results / "PSA_QAE_CCE_COHERENT_NORMALIZED_DYNAMIC_TRANSPORT_LDF_BALANCE.csv",
        results / "PSA_QAE_CCE_COHERENT_NORMALIZED_DYNAMIC_TRANSPORT_LDF_BALANCE.md",
        cce_primary_offledger_tank_saturation_path,
        results / "PSA_QAE_CCE_OFFLEDGER_TANK_SATURATION_INTERFACE.csv",
        results / "PSA_QAE_CCE_OFFLEDGER_TANK_SATURATION_INTERFACE.md",
        cce_primary_offledger_tank_proportional_path,
        results / "PSA_QAE_CCE_OFFLEDGER_TANK_PROPORTIONAL_INTERFACE.csv",
        results / "PSA_QAE_CCE_OFFLEDGER_TANK_PROPORTIONAL_INTERFACE.md",
        cce_primary_physical_unsaturated_tank_path,
        results / "PSA_QAE_CCE_PHYSICAL_UNSATURATED_TANK_TRAJECTORY.csv",
        results / "PSA_QAE_CCE_PHYSICAL_UNSATURATED_TANK_TRAJECTORY.md",
        results / "PSA_QAE_CCE_PHYSICAL_UNSATURATED_TANK_TRAJECTORY_FIGURE.png",
        results / "PSA_QAE_CCE_PHYSICAL_UNSATURATED_TANK_TRAJECTORY_FIGURE.pdf",
        cce_primary_internal_transport_path,
        results / "PSA_QAE_CCE_PRIMARY_INTERNAL_TRANSPORT_MICROSTEPS.csv",
        results / "PSA_QAE_CCE_PRIMARY_INTERNAL_TRANSPORT_MICROSTEPS.md",
        cce_primary_internal_face_balance_path,
        results / "PSA_QAE_CCE_PRIMARY_INTERNAL_FACE_BALANCE_COMPOSITION.csv",
        results / "PSA_QAE_CCE_PRIMARY_INTERNAL_FACE_BALANCE_COMPOSITION.md",
        cce_primary_normalized_internal_face_balance_path,
        results / "PSA_QAE_CCE_PRIMARY_COMPOSITION_NORMALIZED_INTERNAL_FACE_BALANCE.csv",
        results / "PSA_QAE_CCE_PRIMARY_COMPOSITION_NORMALIZED_INTERNAL_FACE_BALANCE.md",
        cce_primary_cell_balance_path,
        results / "PSA_QAE_CCE_PRIMARY_CELL_BALANCE_MICROSTEPS.csv",
        results / "PSA_QAE_CCE_PRIMARY_CELL_BALANCE_MICROSTEPS.md",
        cce_primary_loading_sign_balance_path,
        results / "PSA_QAE_CCE_PRIMARY_LOADING_SIGN_BALANCE_INTERFACE.csv",
        results / "PSA_QAE_CCE_PRIMARY_LOADING_SIGN_BALANCE_INTERFACE.md",
        cce_primary_ldf_sign_balance_path,
        results / "PSA_QAE_CCE_PRIMARY_LDF_SIGN_BALANCE_COMPOSITION.csv",
        results / "PSA_QAE_CCE_PRIMARY_LDF_SIGN_BALANCE_COMPOSITION.md",
        cce_primary_joint_normalized_transport_ldf_balance_path,
        results / "PSA_QAE_CCE_PRIMARY_JOINT_NORMALIZED_TRANSPORT_LDF_BALANCE.csv",
        results / "PSA_QAE_CCE_PRIMARY_JOINT_NORMALIZED_TRANSPORT_LDF_BALANCE.md",
        cce_primary_event_bridge_path,
        results / "PSA_QAE_CCE_PRIMARY_PHASE_EVENT_BRIDGE.csv",
        results / "PSA_QAE_CCE_PRIMARY_PHASE_EVENT_BRIDGE.md",
        results / "PSA_QAE_CCE_PRIMARY_PHASE_EVENT_BRIDGE_FIGURE.png",
        results / "PSA_QAE_CCE_PRIMARY_PHASE_EVENT_BRIDGE_FIGURE.pdf",
        cce_primary_event_fixed_point_path,
        results / "PSA_QAE_CCE_PRIMARY_PHASE_EVENT_FIXED_POINT_SCREEN.csv",
        results / "PSA_QAE_CCE_PRIMARY_PHASE_EVENT_FIXED_POINT_SCREEN.md",
        results / "PSA_QAE_CCE_PRIMARY_PHASE_EVENT_FIXED_POINT_SCREEN_FIGURE.png",
        results / "PSA_QAE_CCE_PRIMARY_PHASE_EVENT_FIXED_POINT_SCREEN_FIGURE.pdf",
        cce_primary_event_compile_path,
        results / "PSA_QAE_CCE_PRIMARY_PHASE_EVENT_BLOCK_COMPILE.csv",
        results / "PSA_QAE_CCE_PRIMARY_PHASE_EVENT_BLOCK_COMPILE.md",
        results / "PSA_QAE_CCE_PRIMARY_PHASE_EVENT_BLOCK_COMPILE_FIGURE.png",
        results / "PSA_QAE_CCE_PRIMARY_PHASE_EVENT_BLOCK_COMPILE_FIGURE.pdf",
        cce_primary_final_event_path,
        results / "PSA_QAE_CCE_PRIMARY_FINAL_EVENT_ARITHMETIC.csv",
        results / "PSA_QAE_CCE_PRIMARY_FINAL_EVENT_ARITHMETIC.md",
        results / "PSA_QAE_CCE_PRIMARY_FINAL_EVENT_ARITHMETIC_FIGURE.png",
        results / "PSA_QAE_CCE_PRIMARY_FINAL_EVENT_ARITHMETIC_FIGURE.pdf",
        cce_primary_policy_stream_event_path,
        results / "PSA_QAE_CCE_PRIMARY_POLICY_STREAM_EVENT_ORACLE.csv",
        results / "PSA_QAE_CCE_PRIMARY_POLICY_STREAM_EVENT_ORACLE.md",
        results / "PSA_QAE_CCE_PRIMARY_POLICY_STREAM_EVENT_ORACLE_FIGURE.png",
        results / "PSA_QAE_CCE_PRIMARY_POLICY_STREAM_EVENT_ORACLE_FIGURE.pdf",
        cce_primary_free_running_path,
        results / "PSA_QAE_CCE_PRIMARY_PHASE_EVENT_FREE_RUNNING.csv",
        results / "PSA_QAE_CCE_PRIMARY_PHASE_EVENT_FREE_RUNNING.md",
        results / "PSA_QAE_CCE_PRIMARY_PHASE_EVENT_FREE_RUNNING_FIGURE.png",
        results / "PSA_QAE_CCE_PRIMARY_PHASE_EVENT_FREE_RUNNING_FIGURE.pdf",
        cce_primary_repeated_path,
        results / "PSA_QAE_CCE_PRIMARY_PHASE_EVENT_REPEATED_CYCLE_SCREEN.csv",
        results / "PSA_QAE_CCE_PRIMARY_PHASE_EVENT_REPEATED_CYCLE_SCREEN.md",
        results / "PSA_QAE_CCE_PRIMARY_PHASE_EVENT_REPEATED_CYCLE_SCREEN_FIGURE.png",
        results / "PSA_QAE_CCE_PRIMARY_PHASE_EVENT_REPEATED_CYCLE_SCREEN_FIGURE.pdf",
        cce_css_initializer_path,
        results / "PSA_QAE_CCE_PRIMARY_CSS_INITIALIZER_EVENT_BRIDGE.csv",
        results / "PSA_QAE_CCE_PRIMARY_CSS_INITIALIZER_EVENT_BRIDGE.md",
        results / "PSA_QAE_CCE_PRIMARY_CSS_INITIALIZER_EVENT_BRIDGE_FIGURE.png",
        results / "PSA_QAE_CCE_PRIMARY_CSS_INITIALIZER_EVENT_BRIDGE_FIGURE.pdf",
        cce_css_repeated_path,
        results / "PSA_QAE_CCE_PRIMARY_CSS_INITIALIZER_REPEATED_CYCLE_SCREEN.csv",
        results / "PSA_QAE_CCE_PRIMARY_CSS_INITIALIZER_REPEATED_CYCLE_SCREEN.md",
        results / "PSA_QAE_CCE_PRIMARY_CSS_INITIALIZER_REPEATED_CYCLE_SCREEN_FIGURE.png",
        results / "PSA_QAE_CCE_PRIMARY_CSS_INITIALIZER_REPEATED_CYCLE_SCREEN_FIGURE.pdf",
        cce_css_stability_path,
        results / "PSA_QAE_CCE_PRIMARY_CSS_INITIALIZER_SPECTRAL_STABILITY_SCREEN.csv",
        results / "PSA_QAE_CCE_PRIMARY_CSS_INITIALIZER_SPECTRAL_STABILITY_SCREEN.md",
        results / "PSA_QAE_CCE_PRIMARY_CSS_INITIALIZER_SPECTRAL_STABILITY_SCREEN_FIGURE.png",
        results / "PSA_QAE_CCE_PRIMARY_CSS_INITIALIZER_SPECTRAL_STABILITY_SCREEN_FIGURE.pdf",
        cce_css_fixed_path,
        results / "PSA_QAE_CCE_PRIMARY_CSS_INITIALIZER_FIXED_POINT_SCREEN.csv",
        results / "PSA_QAE_CCE_PRIMARY_CSS_INITIALIZER_FIXED_POINT_SCREEN.md",
        results / "PSA_QAE_CCE_PRIMARY_CSS_INITIALIZER_FIXED_POINT_SCREEN_FIGURE.png",
        results / "PSA_QAE_CCE_PRIMARY_CSS_INITIALIZER_FIXED_POINT_SCREEN_FIGURE.pdf",
        cce_css_compile_path,
        results / "PSA_QAE_CCE_PRIMARY_CSS_INITIALIZER_BLOCK_COMPILE.csv",
        results / "PSA_QAE_CCE_PRIMARY_CSS_INITIALIZER_BLOCK_COMPILE.md",
        results / "PSA_QAE_CCE_PRIMARY_CSS_INITIALIZER_BLOCK_COMPILE_FIGURE.png",
        results / "PSA_QAE_CCE_PRIMARY_CSS_INITIALIZER_BLOCK_COMPILE_FIGURE.pdf",
        cce_resource_table_path,
        results / "PSA_QAE_CCE_RESOURCE_TABLE3.csv",
        results / "PSA_QAE_CCE_RESOURCE_TABLE3.md",
        results / "PSA_QAE_CCE_RESOURCE_LADDER_FIGURE.png",
        results / "PSA_QAE_CCE_RESOURCE_LADDER_FIGURE.pdf",
        cce_table1_path,
        results / "PSA_QAE_CCE_TABLE1_FROZEN_PROTOCOL.csv",
        results / "PSA_QAE_CCE_TABLE1_FROZEN_PROTOCOL.md",
        cce_table2_path,
        results / "PSA_QAE_CCE_TABLE2_MATCHED_ESTIMATORS.csv",
        results / "PSA_QAE_CCE_TABLE2_MATCHED_ESTIMATORS.md",
        cce_table4_path,
        results / "PSA_QAE_CCE_TABLE4_EVIDENCE_HIERARCHY.csv",
        results / "PSA_QAE_CCE_TABLE4_EVIDENCE_HIERARCHY.md",
        cce_validity_figure_path,
        results / "PSA_QAE_CCE_VALIDITY_BOUNDARY_FIGURE.png",
        results / "PSA_QAE_CCE_VALIDITY_BOUNDARY_FIGURE.pdf",
        results / "PSA_QAE_CCE_MAIN_FIGURE_CAPTIONS.md",
        phase_ledger_path,
        results / "PSA_QAE_DIRECT_PHYSICAL_PHASE_LEDGER.csv",
        results / "PSA_QAE_DIRECT_PHYSICAL_PHASE_LEDGER.md",
        results / "PSA_QAE_DIRECT_PHYSICAL_PHASE_LEDGER_FIGURE.png",
        compiled_physical_oracle_path,
        results / "PSA_QAE_DIRECT_PHYSICAL_COMPILED_ORACLE.csv",
        results / "PSA_QAE_DIRECT_PHYSICAL_COMPILED_ORACLE.md",
        results / "PSA_QAE_DIRECT_PHYSICAL_COMPILED_ORACLE_FIGURE.png",
        strict_css_16cell_path,
        results / "QAE_STRICT_CSS_16CELL_SCREEN.csv",
        results / "QAE_STRICT_CSS_16CELL_SCREEN.md",
        results / "QAE_STRICT_CSS_16CELL_SCREEN_FIGURE.png",
        industrial_8bed_bridge_path,
        results / "PSA_QAE_INDUSTRIAL_8BED_BENCHMARK_BRIDGE.csv",
        results / "PSA_QAE_INDUSTRIAL_8BED_BENCHMARK_BRIDGE.md",
        results / "PSA_QAE_INDUSTRIAL_8BED_BENCHMARK_BRIDGE_FIGURE.png",
        industrial_target_boundary_path,
        results / "PSA_QAE_INDUSTRIAL_TARGET_EVENT_BOUNDARY.csv",
        results / "PSA_QAE_INDUSTRIAL_TARGET_EVENT_BOUNDARY.md",
        results / "PSA_QAE_INDUSTRIAL_TARGET_EVENT_BOUNDARY_FIGURE.png",
        reduced_calibration_localization_path,
        results / "PSA_QAE_REDUCED_CALIBRATION_LOCALIZATION.csv",
        results / "PSA_QAE_REDUCED_CALIBRATION_LOCALIZATION.md",
        results / "PSA_QAE_REDUCED_CALIBRATION_LOCALIZATION_FIGURE.png",
        hybrid_policy_bootstrap_path,
        results / "PSA_QAE_HYBRID_POLICY_SELECTION_BOOTSTRAP.csv",
        results / "PSA_QAE_HYBRID_POLICY_SELECTION_BOOTSTRAP.md",
        results / "PSA_QAE_HYBRID_POLICY_SELECTION_BOOTSTRAP_FIGURE.png",
        hybrid_policy_threshold_path,
        results / "PSA_QAE_HYBRID_POLICY_THRESHOLD_SENSITIVITY.csv",
        results / "PSA_QAE_HYBRID_POLICY_THRESHOLD_SENSITIVITY.md",
        results / "PSA_QAE_HYBRID_POLICY_THRESHOLD_SENSITIVITY_FIGURE.png",
        hybrid_policy_direct_noise_path,
        results / "PSA_QAE_HYBRID_POLICY_DIRECT_NOISE.csv",
        results / "PSA_QAE_HYBRID_POLICY_DIRECT_NOISE.md",
        results / "PSA_QAE_HYBRID_POLICY_DIRECT_NOISE_FIGURE.png",
        submission_manifest_path,
        results / "PSA_QAE_SCI_SUBMISSION_MANIFEST.md",
        submission_packet_path,
    ]
    _check(
        checks,
        "reviewer-facing artifact files",
        all(path.exists() for path in required_artifacts),
        f"files={len(required_artifacts)}",
    )

    required_claim_strings = [
        "N=16/32/64/128",
        "0.65625",
        "0.625",
        "0.75348",
        "0.01234",
        "0.00837",
        "Direct reduced-PSA",
        "0.461538",
        "0.463218",
        "0.01847",
        "0.03122",
        "QAE_TUWIEN_H2_STATEVECTOR_QPE.md",
        "0.00445",
        "0.00405",
        "0.00714",
        "0.00799",
        "QAE_TUWIEN_H2_MLAE_NOISE.md",
        "0.486517",
        "0.484375",
        "0.487729",
        "QAE_TUWIEN_H2_UNCERTAINTY_STATEVECTOR_QPE.md",
        "QAE_TUWIEN_H2_RESOURCE_BOUNDARY.md",
        "959,427",
        "N=128",
        "24.55×",
        "798,068",
        "QAE_TUWIEN_H2_STRUCTURED_LOADER_BOUNDARY.md",
        "188,520",
        "1,319,640",
        "1.47×10^3",
        "QAE_HYBRID_POLICY_SELECTION_PHYSICAL_16X3.md",
        "94,260",
        "0.438795",
        "QAE_INDEPENDENT_SOURCE_SURROGATE_CONTINUOUS_QPE.md",
        "0.470535",
        "0.04369",
        "32,768",
        "PSA_INDEPENDENT_SOURCE_QUADRATIC_SURROGATE_HOLDOUT_32.md",
        "2.41×10−6",
        "1.54×10−3",
        "PSA_QAE_CONTINUOUS_POLICY_SELECTION.md",
        "0.927509/0.470535/0.284023",
        "0.002508",
        "PSA_QAE_POLICY_SAMPLE_SIZE_DESIGN.md",
        "385/1,068/2,401",
        "0.975/0.025",
        "PSA_QAE_CVAR_LOSS_BRIDGE.md",
        "0.02988",
        "0.01526",
        "111,354",
        "57,725",
        "133.7x",
        "PSA_QAE_DIRECT_PHYSICAL_TAIL_STABILITY.md",
        "0.06460",
        "0.09209",
        "0.02749",
        "0.03676/0.03660",
        "0.064415/0.034242",
        "231,507/127,037",
        "73.7×/40.4×",
        "PSA_QAE_DIRECT_PHYSICAL_TAIL_LOSS_ORACLE.md",
        "1,768",
        "14,078",
        "4,194,304",
        "3.043×10−5",
        "PSA_QAE_DIRECT_PHYSICAL_TAIL_AMPLITUDE_ORACLE.md",
        "8,388,608",
        "1.762×10−7",
        "1.648×10−7",
        "QAE_DIRECT_PHYSICAL_TAIL_AMPLITUDE_MLAE_NOISE.md",
        "0.001194/0.001161/0.001909",
        "0.001032/0.001977/0.004589",
        "QAE_DIRECT_PHYSICAL_TAIL_END_TO_END_BOUNDARY.md",
        "31,693",
        "430.1×/783.9×",
        "231,508/127,038",
        "QAE_TAIL_LOADER_RESOURCE_CROSSOVER.md",
        "0.027×/0.049×",
        "12.275×",
        "QAE_PROCESS_PARAMETER_CONTINUOUS_PRIOR.md",
        "0.642597",
        "882,253",
        "8,192",
        "280.8×",
        "QAE_PROCESS_PARAMETER_RESOURCE_BOUNDARY.md",
        "280.79",
        "2.607",
        "0.0285×",
        "3.068×",
        "QAE_PROCESS_PARAMETER_PRIOR_WEIGHT_SENSITIVITY.md",
        "0.141295",
        "0.987131",
        "0.620721",
        "0.664535",
        "0.501501",
        "QAE_SURROGATE_MODEL_DISCREPANCY_BOUNDARY.md",
        "0.003906",
        "QAE_SURROGATE_RARE_TAIL_BOUNDARY.md",
        "0.005215",
        "19,928",
        "4,096",
        "QAE_DIRECT_PHYSICAL_RARE_TAIL_BOUNDARY.md",
        "0.046875",
        "0.001207",
        "171,628",
        "0.02781",
        "0.01324",
        "QAE_DIRECT_PHYSICAL_RARE_TAIL_REPLICATES_N32.md",
        "0.010417",
        "0.020833",
        "0.043042",
        "194,804",
        "QAE_DIRECT_PHYSICAL_RARE_TAIL_MLAE_NOISE.md",
        "0.000576",
        "0.004651",
        "QAE_CROSS_ORACLE_RECOVERY_MODEL_FORM_BOUNDARY.md",
        "0.510417",
        "510x",
        "QAE_PAIRED_ORACLE_RECOVERY_BOUNDARY_K8.md",
        "0.750",
        "750x",
        "QAE_PAIRED_ORACLE_RECOVERY_BOUNDARY_K16.md",
        "0.5625",
        "562.5x",
        "QAE_PAIRED_ORACLE_RECOVERY_BOUNDARY_K32.md",
        "0.5000",
        "500x",
        "QAE_PAIRED_ORACLE_K_PROGRESS_SUMMARY.md",
        "QAE_END_TO_END_RESOURCE_SUMMARY.md",
        "2.607x",
        "3.100x",
        "0.163x",
        "12.275x",
        "536,870,912 GiB",
        "QAE_STRICT_CSS_HORIZON_SCREEN.md",
        "1/3",
        "2e-3–2.4e-2",
        "QAE_STRICT_CSS_MESH_SCREEN.md",
        "2/3",
        "1.63e-2",
        "1.75e-7",
        "1.04e-4",
        "PSA_QAE_SCI_SUBMISSION_GATE.md",
        "resource-aware quantum simulation/estimation method",
        "PSA_QAE_POLICY_PHYSICAL_HIGH_N_EXTENSION.md",
        "0.6641",
        "0.6797",
        "0.7327",
        "198.2",
        "PSA_QAE_SCI_JOURNAL_TARGETS_2026.md",
        "PSA_QAE_POLICY_PHYSICAL_128_REPLICATE_EXTENSION.md",
        "0.66797",
        "0.64453",
        "0.01657",
        "0.02762",
        "PSA_QAE_DIRECT_PHYSICAL_SEED_PANEL.md",
        "seed-100 and seed-200",
        "PSA_QAE_STRUCTURED_EMPIRICAL_LOADER.md",
        "400",
        "2,394",
        "31` rotations per",
        "PSA_QAE_REVERSIBLE_FIXED_POINT_CYCLE_CONTROL.md",
        "65,536",
        "55",
        "PSA_QAE_DIRECT_PHYSICAL_PHASE_LEDGER.md",
        "160",
        "40",
        "1.933e-5",
        "2.842e-14",
        "PSA_QAE_POLICY_PHYSICAL_128_REPLICATE_EXTENSION.md",
        "PSA_QAE_DIRECT_PHYSICAL_COMPILED_ORACLE.md",
        "39/57",
        "1,518/1,542",
        "finite physical-oracle label-table",
        "QAE_STRICT_CSS_16CELL_SCREEN.md",
        "1/3",
        "2.445e-4",
        "6.897e-8",
        "1.078e-4",
        "PSA_QAE_INDUSTRIAL_8BED_BENCHMARK_BRIDGE.md",
        "0.0199",
        "0.1659",
        "Yun et al.",
        "99.99/66.59%/6.23 kWh kmol⁻¹",
        "1,376",
        "0.984709",
        "0.015191",
        "PSA_QAE_INDUSTRIAL_TARGET_EVENT_BOUNDARY.md",
        "PSA_QAE_REDUCED_CALIBRATION_LOCALIZATION.md",
        "1.5673",
        "0.985399",
        "0.606439",
        "0.986332",
        "47/48",
        "PSA_QAE_HYBRID_POLICY_SELECTION_BOOTSTRAP.md",
        "60.4%",
        "39.6%",
        "99.76%",
        "0.24%",
        "PSA_QAE_HYBRID_POLICY_THRESHOLD_SENSITIVITY.md",
        "0.99987",
        "relaxing recovery",
        "industrial purity boundary",
        "PSA_QAE_HYBRID_POLICY_DIRECT_NOISE.md",
        "0.003306",
        "0.002654",
        "0.007675",
        "0.008555",
        "same-query MC",
    ]
    missing_claim_strings = [value for value in required_claim_strings if value not in manuscript]
    _check(
        checks,
        "manuscript claim anchors",
        not missing_claim_strings,
        f"missing={missing_claim_strings}",
    )

    status = "pass" if all(check["pass"] for check in checks) else "fail"
    result = {
        "schema": "psa-qae-sci-manuscript-claims-audit/v1",
        "status": status,
        "scope": "Targeted consistency audit; not plant validation, peer review, or quantum advantage evidence.",
        "checks": checks,
        "sources": [
            convergence_path.name,
            mlae_path.name,
            tuwien_qpe_path.name,
            tuwien_mlae_path.name,
            tuwien_uncertainty_path.name,
            tuwien_resource_path.name,
            tuwien_structured_loader_path.name,
            hybrid_policy_selection_path.name,
            surrogate_continuous_qpe_path.name,
            quadratic_holdout_path.name,
            continuous_policy_selection_path.name,
            policy_sample_size_path.name,
            cvar_loss_bridge_path.name,
            direct_tail_stability_path.name,
            tail_loss_oracle_path.name,
            tail_amplitude_oracle_path.name,
            tail_amplitude_mlae_path.name,
            tail_end_to_end_path.name,
            tail_loader_crossover_path.name,
            process_parameter_prior_path.name,
            process_parameter_resource_path.name,
            process_prior_weight_path.name,
            discrepancy_boundary_path.name,
            rare_tail_boundary_path.name,
            direct_physical_rare_tail_boundary_path.name,
            direct_physical_rare_tail_replicates_path.name,
            direct_physical_rare_tail_mlae_path.name,
            cross_oracle_model_form_path.name,
            paired_oracle_model_form_path.name,
            paired_oracle_model_form_k16_path.name,
            paired_oracle_model_form_k32_path.name,
            paired_oracle_k_progress_path.name,
            validation_path.name,
            case_spec_path.name,
            manuscript_path.name,
            n128_replicate_extension_path.name,
            primary_finite_gate_path.name,
            primary_finite_ibm_preflight_path.name,
            primary_linear_oracle_path.name,
            primary_copula_loader_path.name,
            primary_threshold_activity_path.name,
            cce_gate_manifest_path.name,
            cce_external_policy_path.name,
            cce_external_refinement_path.name,
            cce_h2_resolution_path.name,
            cce_prospective_design_path.name,
            cce_phase_map_path.name,
            cce_phase_map_fixed_point_path.name,
            cce_phase_map_compile_path.name,
            cce_small_e2e_path.name,
            cce_primary_phase_ledger_path.name,
            cce_primary_physical_css_path.name,
            cce_primary_qstar_microkernel_path.name,
            cce_primary_qstar_ldf_microstep_path.name,
            cce_primary_all_component_ldf_path.name,
            cce_primary_product_boundary_path.name,
            cce_primary_product_boundary_balance_path.name,
            cce_primary_internal_transport_path.name,
            cce_primary_internal_face_balance_path.name,
            cce_primary_cell_balance_path.name,
            cce_primary_loading_sign_balance_path.name,
            cce_primary_ldf_sign_balance_path.name,
            cce_primary_event_bridge_path.name,
            cce_primary_event_fixed_point_path.name,
            cce_primary_event_compile_path.name,
            cce_primary_final_event_path.name,
            cce_primary_policy_stream_event_path.name,
            cce_primary_free_running_path.name,
            cce_primary_repeated_path.name,
            cce_css_initializer_path.name,
            cce_css_repeated_path.name,
            cce_css_stability_path.name,
            cce_css_fixed_path.name,
            cce_css_compile_path.name,
            cce_resource_table_path.name,
            cce_table1_path.name,
            cce_table2_path.name,
            cce_table4_path.name,
            cce_validity_figure_path.name,
            cce_editorial_path.name,
            cce_editorial_md_path.name,
            cce_cover_path.name,
            cce_highlights_path.name,
            cce_checklist_path.name,
            cce_graphical_abstract_png_path.name,
            cce_graphical_abstract_pdf_path.name,
            compiled_physical_oracle_path.name,
            strict_css_16cell_path.name,
            industrial_8bed_bridge_path.name,
            industrial_target_boundary_path.name,
            reduced_calibration_localization_path.name,
            hybrid_policy_bootstrap_path.name,
            hybrid_policy_threshold_path.name,
            hybrid_policy_direct_noise_path.name,
            submission_manifest_path.name,
            submission_packet_path.name,
        ],
    }
    json_path = results / "PSA_QAE_SCI_CLAIMS_AUDIT.json"
    json_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# PSA--QAE SCI manuscript claims audit",
        "",
        "This is a targeted artifact-consistency audit. It does not establish plant validation, hardware execution, or quantum advantage.",
        "",
        "| check | result | detail |",
        "|---|---|---|",
    ]
    lines.extend(
        f"| {check['name']} | {'PASS' if check['pass'] else 'FAIL'} | {check['detail']} |"
        for check in checks
    )
    lines.extend(
        [
            "",
            f"Overall status: **{status.upper()}**.",
            "",
            "The remaining publication gates are process calibration, independent physical replicates, and compiled state-preparation/controlled-oracle resource accounting.",
        ]
    )
    md_path = results / "PSA_QAE_SCI_CLAIMS_AUDIT.md"
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {json_path}")
    print(f"wrote {md_path}")
    if status != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()


