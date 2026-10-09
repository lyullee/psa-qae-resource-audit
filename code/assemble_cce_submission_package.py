"""Assemble a local CCE submission/SI manifest without submitting external work."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RESULTS = ROOT / "10_TEA_LCA_Python" / "results" / "pycharm_publication_enhancement"
OUT_JSON = RESULTS / "PSA_QAE_CCE_SUBMISSION_PACKAGE_MANIFEST.json"
OUT_MD = RESULTS / "PSA_QAE_CCE_SUBMISSION_PACKAGE_MANIFEST.md"
OUT_SI = RESULTS / "PSA_QAE_CCE_SUPPLEMENTARY_INFORMATION_DRAFT.md"


MAIN_FILES = [
    "PSA_QAE_CCE_CORE_MANUSCRIPT_DRAFT.md",
    "PSA_QAE_CCE_SUBMISSION_MANUSCRIPT.docx",
    "PSA_QAE_CCE_TITLE_PAGE.docx",
    "PSA_QAE_CCE_SUPPLEMENTARY_INFORMATION.docx",
    "PSA_QAE_CCE_COVER_LETTER_DRAFT.md",
    "PSA_QAE_CCE_HIGHLIGHTS.txt",
    "PSA_QAE_CCE_GRAPHICAL_ABSTRACT.png",
    "PSA_QAE_CCE_GRAPHICAL_ABSTRACT.pdf",
    "PSA_QAE_SCI_REFERENCES.bib",
    "PSA_QAE_CCE_MAIN_FIGURE_CAPTIONS.md",
    "PSA_QAE_CCE_WORKFLOW_FIGURE.png",
    "PSA_QAE_CCE_WORKFLOW_FIGURE.pdf",
    "PSA_QAE_CONTINUOUS_POLICY_SELECTION_FIGURE.png",
    "PSA_QAE_CONTINUOUS_POLICY_SELECTION_FIGURE.pdf",
    "PSA_QAE_CCE_PRIMARY_RESOURCE_BOUNDARY_FIGURE.png",
    "PSA_QAE_CCE_PRIMARY_RESOURCE_BOUNDARY_FIGURE.pdf",
    "PSA_QAE_CCE_RESOURCE_LADDER_FIGURE.png",
    "PSA_QAE_CCE_RESOURCE_LADDER_FIGURE.pdf",
    "FIG_QPU_MLAE_HARDWARE_BOUNDARY.png",
    "FIG_QPU_MLAE_HARDWARE_BOUNDARY.pdf",
    "PSA_QAE_QPU_REPLICATION_CAMPAIGN_ANALYSIS_FIGURE.png",
    "PSA_QAE_QPU_REPLICATION_CAMPAIGN_ANALYSIS_FIGURE.pdf",
    "PSA_QAE_CCE_VALIDITY_BOUNDARY_FIGURE.png",
    "PSA_QAE_CCE_VALIDITY_BOUNDARY_FIGURE.pdf",
    "PSA_QAE_CCE_TABLE1_FROZEN_PROTOCOL.json",
    "PSA_QAE_CCE_TABLE1_FROZEN_PROTOCOL.csv",
    "PSA_QAE_CCE_TABLE1_FROZEN_PROTOCOL.md",
    "PSA_QAE_CCE_TABLE2_MATCHED_ESTIMATORS.json",
    "PSA_QAE_CCE_TABLE2_MATCHED_ESTIMATORS.csv",
    "PSA_QAE_CCE_TABLE2_MATCHED_ESTIMATORS.md",
    "PSA_QAE_CCE_RESOURCE_TABLE3.json",
    "PSA_QAE_CCE_RESOURCE_TABLE3.csv",
    "PSA_QAE_CCE_RESOURCE_TABLE3.md",
    "PSA_QAE_CCE_TABLE4_EVIDENCE_HIERARCHY.json",
    "PSA_QAE_CCE_TABLE4_EVIDENCE_HIERARCHY.csv",
    "PSA_QAE_CCE_TABLE4_EVIDENCE_HIERARCHY.md",
]

SI_FILES = [
    "PSA_QAE_CCE_PRIMARY_CASE_PROTOCOL.json",
    "PSA_QAE_CONTINUOUS_POLICY_SELECTION.json",
    "PSA_QAE_CCE_PRIMARY_RESOURCE_BOUNDARY.json",
    "PSA_QAE_CCE_PRIMARY_THRESHOLD_ACTIVITY.json",
    "PSA_QAE_CCE_POLICY_DECISION_MARGIN.json",
    "PSA_QAE_CCE_POLICY_DECISION_MARGIN.csv",
    "PSA_QAE_CCE_POLICY_DECISION_MARGIN.md",
    "PSA_QAE_CCE_PROSPECTIVE_POLICY_DESIGN_AUDIT.json",
    "PSA_QAE_CCE_PROSPECTIVE_POLICY_DESIGN_AUDIT.csv",
    "PSA_QAE_CCE_PROSPECTIVE_POLICY_DESIGN_AUDIT.md",
    "PSA_QAE_CCE_PROSPECTIVE_POLICY_DESIGN_AUDIT_FIGURE.png",
    "PSA_QAE_CCE_PROSPECTIVE_POLICY_DESIGN_AUDIT_FIGURE.pdf",
    "PSA_QAE_CCE_PRIMARY_FINITE_ORACLE_GATE_RESOURCES.json",
    "PSA_QAE_CCE_PRIMARY_FINITE_ORACLE_IBM_PREFLIGHT_ibm_marrakesh.json",
    "PSA_QAE_CCE_PRIMARY_LINEAR_SURROGATE_ORACLE.json",
    "PSA_QAE_CCE_PRIMARY_COPULA_STATE_LOADER.json",
    "PSA_QAE_CCE_CALIBRATED_ONE_CYCLE_PHASE_MAP.json",
    "PSA_QAE_CCE_PHASE_MAP_FIXED_POINT_SCREEN.json",
    "PSA_QAE_CCE_PHASE_MAP_AFFINE_BLOCK_COMPILE.json",
    "PSA_QAE_CCE_SMALL_END_TO_END_ORACLE.json",
    "PSA_QAE_CCE_SMALL_END_TO_END_ORACLE.csv",
    "PSA_QAE_CCE_SMALL_END_TO_END_ORACLE.md",
    "PSA_QAE_CCE_SMALL_END_TO_END_ORACLE_FIGURE.png",
    "PSA_QAE_CCE_SMALL_END_TO_END_ORACLE_FIGURE.pdf",
    "PSA_QAE_CCE_PRIMARY_PHASE_LEDGER.json",
    "PSA_QAE_CCE_PRIMARY_PHASE_LEDGER.csv",
    "PSA_QAE_CCE_PRIMARY_PHASE_LEDGER.md",
    "PSA_QAE_CCE_PRIMARY_PHASE_LEDGER_FIGURE.png",
    "PSA_QAE_CCE_PRIMARY_PHASE_LEDGER_FIGURE.pdf",
    "PSA_QAE_CCE_PRIMARY_PHYSICAL_CSS_HORIZON_AUDIT.json",
    "PSA_QAE_CCE_PRIMARY_PHYSICAL_CSS_HORIZON_AUDIT.csv",
    "PSA_QAE_CCE_PRIMARY_PHYSICAL_CSS_HORIZON_AUDIT.md",
    "PSA_QAE_CCE_PRIMARY_PHYSICAL_CSS_HORIZON_AUDIT_FIGURE.png",
    "PSA_QAE_CCE_PRIMARY_PHYSICAL_CSS_HORIZON_AUDIT_FIGURE.pdf",
    "PSA_QAE_CCE_PRIMARY_QSTAR_REVERSIBLE_MICROKERNEL.json",
    "PSA_QAE_CCE_PRIMARY_QSTAR_REVERSIBLE_MICROKERNEL.csv",
    "PSA_QAE_CCE_PRIMARY_QSTAR_REVERSIBLE_MICROKERNEL.md",
    "PSA_QAE_CCE_PRIMARY_QSTAR_REVERSIBLE_MICROKERNEL_FIGURE.png",
    "PSA_QAE_CCE_PRIMARY_QSTAR_REVERSIBLE_MICROKERNEL_FIGURE.pdf",
    "PSA_QAE_CCE_PRIMARY_QSTAR_LDF_REVERSIBLE_MICROSTEP.json",
    "PSA_QAE_CCE_PRIMARY_QSTAR_LDF_REVERSIBLE_MICROSTEP.csv",
    "PSA_QAE_CCE_PRIMARY_QSTAR_LDF_REVERSIBLE_MICROSTEP.md",
    "PSA_QAE_CCE_PRIMARY_QSTAR_LDF_REVERSIBLE_MICROSTEP_FIGURE.png",
    "PSA_QAE_CCE_PRIMARY_QSTAR_LDF_REVERSIBLE_MICROSTEP_FIGURE.pdf",
    "PSA_QAE_CCE_PRIMARY_ALL_COMPONENT_LDF_MICROSTEPS.json",
    "PSA_QAE_CCE_PRIMARY_ALL_COMPONENT_LDF_MICROSTEPS.csv",
    "PSA_QAE_CCE_PRIMARY_ALL_COMPONENT_LDF_MICROSTEPS.md",
    "PSA_QAE_CCE_PRIMARY_PRODUCT_BOUNDARY_MICROSTEPS.json",
    "PSA_QAE_CCE_PRIMARY_PRODUCT_BOUNDARY_MICROSTEPS.csv",
    "PSA_QAE_CCE_PRIMARY_PRODUCT_BOUNDARY_MICROSTEPS.md",
    "PSA_QAE_CCE_PRIMARY_PRODUCT_BOUNDARY_BALANCE_COMPOSITION.json",
    "PSA_QAE_CCE_PRIMARY_PRODUCT_BOUNDARY_BALANCE_COMPOSITION.csv",
    "PSA_QAE_CCE_PRIMARY_PRODUCT_BOUNDARY_BALANCE_COMPOSITION.md",
    "PSA_QAE_CCE_PRIMARY_PRODUCT_LDF_VALVE_BALANCE_COMPOSITION.json",
    "PSA_QAE_CCE_PRIMARY_PRODUCT_LDF_VALVE_BALANCE_COMPOSITION.csv",
    "PSA_QAE_CCE_PRIMARY_PRODUCT_LDF_VALVE_BALANCE_COMPOSITION.md",
    "PSA_QAE_CCE_PRIMARY_NORMALIZED_PRODUCT_LDF_VALVE_BALANCE.json",
    "PSA_QAE_CCE_PRIMARY_NORMALIZED_PRODUCT_LDF_VALVE_BALANCE.csv",
    "PSA_QAE_CCE_PRIMARY_NORMALIZED_PRODUCT_LDF_VALVE_BALANCE.md",
    "PSA_QAE_CCE_COHERENT_RUN_SCHEDULE_TANK_INTERFACE.json",
    "PSA_QAE_CCE_COHERENT_RUN_SCHEDULE_TANK_INTERFACE.csv",
    "PSA_QAE_CCE_COHERENT_RUN_SCHEDULE_TANK_INTERFACE.md",
    "PSA_QAE_CCE_COHERENT_RUN_FACTOR_LDF_INTERFACE.json",
    "PSA_QAE_CCE_COHERENT_RUN_FACTOR_LDF_INTERFACE.csv",
    "PSA_QAE_CCE_COHERENT_RUN_FACTOR_LDF_INTERFACE.md",
    "PSA_QAE_CCE_COHERENT_COEFFICIENT_LDF_BALANCE_INTERFACE.json",
    "PSA_QAE_CCE_COHERENT_COEFFICIENT_LDF_BALANCE_INTERFACE.csv",
    "PSA_QAE_CCE_COHERENT_COEFFICIENT_LDF_BALANCE_INTERFACE.md",
    "PSA_QAE_CCE_COHERENT_DYNAMIC_LANGMUIR_LDF_BALANCE_INTERFACE.json",
    "PSA_QAE_CCE_COHERENT_DYNAMIC_LANGMUIR_LDF_BALANCE_INTERFACE.csv",
    "PSA_QAE_CCE_COHERENT_DYNAMIC_LANGMUIR_LDF_BALANCE_INTERFACE.md",
    "PSA_QAE_CCE_COHERENT_NORMALIZED_DYNAMIC_TRANSPORT_LDF_BALANCE.json",
    "PSA_QAE_CCE_COHERENT_NORMALIZED_DYNAMIC_TRANSPORT_LDF_BALANCE.csv",
    "PSA_QAE_CCE_COHERENT_NORMALIZED_DYNAMIC_TRANSPORT_LDF_BALANCE.md",
    "PSA_QAE_CCE_OFFLEDGER_TANK_SATURATION_INTERFACE.json",
    "PSA_QAE_CCE_OFFLEDGER_TANK_SATURATION_INTERFACE.csv",
    "PSA_QAE_CCE_OFFLEDGER_TANK_SATURATION_INTERFACE.md",
    "PSA_QAE_CCE_OFFLEDGER_TANK_PROPORTIONAL_INTERFACE.json",
    "PSA_QAE_CCE_OFFLEDGER_TANK_PROPORTIONAL_INTERFACE.csv",
    "PSA_QAE_CCE_OFFLEDGER_TANK_PROPORTIONAL_INTERFACE.md",
    "PSA_QAE_CCE_PHYSICAL_UNSATURATED_TANK_TRAJECTORY.json",
    "PSA_QAE_CCE_PHYSICAL_UNSATURATED_TANK_TRAJECTORY.csv",
    "PSA_QAE_CCE_PHYSICAL_UNSATURATED_TANK_TRAJECTORY.md",
    "PSA_QAE_CCE_PHYSICAL_UNSATURATED_TANK_TRAJECTORY_FIGURE.png",
    "PSA_QAE_CCE_PHYSICAL_UNSATURATED_TANK_TRAJECTORY_FIGURE.pdf",
    "PSA_QAE_CCE_PRIMARY_INTERNAL_FACE_BALANCE_COMPOSITION.json",
    "PSA_QAE_CCE_PRIMARY_INTERNAL_FACE_BALANCE_COMPOSITION.csv",
    "PSA_QAE_CCE_PRIMARY_INTERNAL_FACE_BALANCE_COMPOSITION.md",
    "PSA_QAE_CCE_PRIMARY_COMPOSITION_NORMALIZED_INTERNAL_FACE_BALANCE.json",
    "PSA_QAE_CCE_PRIMARY_COMPOSITION_NORMALIZED_INTERNAL_FACE_BALANCE.csv",
    "PSA_QAE_CCE_PRIMARY_COMPOSITION_NORMALIZED_INTERNAL_FACE_BALANCE.md",
    "PSA_QAE_CCE_PRIMARY_INTERNAL_TRANSPORT_MICROSTEPS.json",
    "PSA_QAE_CCE_PRIMARY_INTERNAL_TRANSPORT_MICROSTEPS.csv",
    "PSA_QAE_CCE_PRIMARY_INTERNAL_TRANSPORT_MICROSTEPS.md",
    "PSA_QAE_CCE_PRIMARY_CELL_BALANCE_MICROSTEPS.json",
    "PSA_QAE_CCE_PRIMARY_CELL_BALANCE_MICROSTEPS.csv",
    "PSA_QAE_CCE_PRIMARY_CELL_BALANCE_MICROSTEPS.md",
    "PSA_QAE_CCE_PRIMARY_LOADING_SIGN_BALANCE_INTERFACE.json",
    "PSA_QAE_CCE_PRIMARY_LOADING_SIGN_BALANCE_INTERFACE.csv",
    "PSA_QAE_CCE_PRIMARY_LOADING_SIGN_BALANCE_INTERFACE.md",
    "PSA_QAE_CCE_PRIMARY_LDF_SIGN_BALANCE_COMPOSITION.json",
    "PSA_QAE_CCE_PRIMARY_LDF_SIGN_BALANCE_COMPOSITION.csv",
    "PSA_QAE_CCE_PRIMARY_LDF_SIGN_BALANCE_COMPOSITION.md",
    "PSA_QAE_CCE_PRIMARY_JOINT_NORMALIZED_TRANSPORT_LDF_BALANCE.json",
    "PSA_QAE_CCE_PRIMARY_JOINT_NORMALIZED_TRANSPORT_LDF_BALANCE.csv",
    "PSA_QAE_CCE_PRIMARY_JOINT_NORMALIZED_TRANSPORT_LDF_BALANCE.md",
    "PSA_QAE_CCE_PRIMARY_PHASE_EVENT_BRIDGE.json",
    "PSA_QAE_CCE_PRIMARY_PHASE_EVENT_BRIDGE.csv",
    "PSA_QAE_CCE_PRIMARY_PHASE_EVENT_BRIDGE.md",
    "PSA_QAE_CCE_PRIMARY_PHASE_EVENT_BRIDGE_FIGURE.png",
    "PSA_QAE_CCE_PRIMARY_PHASE_EVENT_BRIDGE_FIGURE.pdf",
    "PSA_QAE_CCE_PRIMARY_PHASE_EVENT_FIXED_POINT_SCREEN.json",
    "PSA_QAE_CCE_PRIMARY_PHASE_EVENT_FIXED_POINT_SCREEN.csv",
    "PSA_QAE_CCE_PRIMARY_PHASE_EVENT_FIXED_POINT_SCREEN.md",
    "PSA_QAE_CCE_PRIMARY_PHASE_EVENT_FIXED_POINT_SCREEN_FIGURE.png",
    "PSA_QAE_CCE_PRIMARY_PHASE_EVENT_FIXED_POINT_SCREEN_FIGURE.pdf",
    "PSA_QAE_CCE_PRIMARY_PHASE_EVENT_BLOCK_COMPILE.json",
    "PSA_QAE_CCE_PRIMARY_PHASE_EVENT_BLOCK_COMPILE.csv",
    "PSA_QAE_CCE_PRIMARY_PHASE_EVENT_BLOCK_COMPILE.md",
    "PSA_QAE_CCE_PRIMARY_PHASE_EVENT_BLOCK_COMPILE_FIGURE.png",
    "PSA_QAE_CCE_PRIMARY_PHASE_EVENT_BLOCK_COMPILE_FIGURE.pdf",
    "PSA_QAE_CCE_PRIMARY_FINAL_EVENT_ARITHMETIC.json",
    "PSA_QAE_CCE_PRIMARY_FINAL_EVENT_ARITHMETIC.csv",
    "PSA_QAE_CCE_PRIMARY_FINAL_EVENT_ARITHMETIC.md",
    "PSA_QAE_CCE_PRIMARY_FINAL_EVENT_ARITHMETIC_FIGURE.png",
    "PSA_QAE_CCE_PRIMARY_FINAL_EVENT_ARITHMETIC_FIGURE.pdf",
    "PSA_QAE_CCE_PRIMARY_POLICY_STREAM_EVENT_ORACLE.json",
    "PSA_QAE_CCE_PRIMARY_POLICY_STREAM_EVENT_ORACLE.csv",
    "PSA_QAE_CCE_PRIMARY_POLICY_STREAM_EVENT_ORACLE.md",
    "PSA_QAE_CCE_PRIMARY_POLICY_STREAM_EVENT_ORACLE_FIGURE.png",
    "PSA_QAE_CCE_PRIMARY_POLICY_STREAM_EVENT_ORACLE_FIGURE.pdf",
    "PSA_QAE_CCE_PRIMARY_PHASE_EVENT_FREE_RUNNING.json",
    "PSA_QAE_CCE_PRIMARY_PHASE_EVENT_FREE_RUNNING.csv",
    "PSA_QAE_CCE_PRIMARY_PHASE_EVENT_FREE_RUNNING.md",
    "PSA_QAE_CCE_PRIMARY_PHASE_EVENT_FREE_RUNNING_FIGURE.png",
    "PSA_QAE_CCE_PRIMARY_PHASE_EVENT_FREE_RUNNING_FIGURE.pdf",
    "PSA_QAE_CCE_PRIMARY_PHASE_EVENT_REPEATED_CYCLE_SCREEN.json",
    "PSA_QAE_CCE_PRIMARY_PHASE_EVENT_REPEATED_CYCLE_SCREEN.csv",
    "PSA_QAE_CCE_PRIMARY_PHASE_EVENT_REPEATED_CYCLE_SCREEN.md",
    "PSA_QAE_CCE_PRIMARY_PHASE_EVENT_REPEATED_CYCLE_SCREEN_FIGURE.png",
    "PSA_QAE_CCE_PRIMARY_PHASE_EVENT_REPEATED_CYCLE_SCREEN_FIGURE.pdf",
    "PSA_QAE_CCE_PRIMARY_CSS_INITIALIZER_EVENT_BRIDGE.json",
    "PSA_QAE_CCE_PRIMARY_CSS_INITIALIZER_EVENT_BRIDGE.csv",
    "PSA_QAE_CCE_PRIMARY_CSS_INITIALIZER_EVENT_BRIDGE.md",
    "PSA_QAE_CCE_PRIMARY_CSS_INITIALIZER_EVENT_BRIDGE_FIGURE.png",
    "PSA_QAE_CCE_PRIMARY_CSS_INITIALIZER_EVENT_BRIDGE_FIGURE.pdf",
    "PSA_QAE_CCE_PRIMARY_CSS_INITIALIZER_REPEATED_CYCLE_SCREEN.json",
    "PSA_QAE_CCE_PRIMARY_CSS_INITIALIZER_REPEATED_CYCLE_SCREEN.csv",
    "PSA_QAE_CCE_PRIMARY_CSS_INITIALIZER_REPEATED_CYCLE_SCREEN.md",
    "PSA_QAE_CCE_PRIMARY_CSS_INITIALIZER_REPEATED_CYCLE_SCREEN_FIGURE.png",
    "PSA_QAE_CCE_PRIMARY_CSS_INITIALIZER_REPEATED_CYCLE_SCREEN_FIGURE.pdf",
    "PSA_QAE_CCE_PRIMARY_CSS_INITIALIZER_SPECTRAL_STABILITY_SCREEN.json",
    "PSA_QAE_CCE_PRIMARY_CSS_INITIALIZER_SPECTRAL_STABILITY_SCREEN.csv",
    "PSA_QAE_CCE_PRIMARY_CSS_INITIALIZER_SPECTRAL_STABILITY_SCREEN.md",
    "PSA_QAE_CCE_PRIMARY_CSS_INITIALIZER_SPECTRAL_STABILITY_SCREEN_FIGURE.png",
    "PSA_QAE_CCE_PRIMARY_CSS_INITIALIZER_SPECTRAL_STABILITY_SCREEN_FIGURE.pdf",
    "PSA_QAE_CCE_PRIMARY_CSS_INITIALIZER_FIXED_POINT_SCREEN.json",
    "PSA_QAE_CCE_PRIMARY_CSS_INITIALIZER_FIXED_POINT_SCREEN.csv",
    "PSA_QAE_CCE_PRIMARY_CSS_INITIALIZER_FIXED_POINT_SCREEN.md",
    "PSA_QAE_CCE_PRIMARY_CSS_INITIALIZER_FIXED_POINT_SCREEN_FIGURE.png",
    "PSA_QAE_CCE_PRIMARY_CSS_INITIALIZER_FIXED_POINT_SCREEN_FIGURE.pdf",
    "PSA_QAE_CCE_PRIMARY_CSS_INITIALIZER_BLOCK_COMPILE.json",
    "PSA_QAE_CCE_PRIMARY_CSS_INITIALIZER_BLOCK_COMPILE.csv",
    "PSA_QAE_CCE_PRIMARY_CSS_INITIALIZER_BLOCK_COMPILE.md",
    "PSA_QAE_CCE_PRIMARY_CSS_INITIALIZER_BLOCK_COMPILE_FIGURE.png",
    "PSA_QAE_CCE_PRIMARY_CSS_INITIALIZER_BLOCK_COMPILE_FIGURE.pdf",
    "PSA_QAE_DIRECT_PHYSICAL_PHASE_LEDGER.json",
    "PSA_QAE_EMPIRICAL_VALVE_TANK_PRODUCT_CALIBRATION.json",
    "PSA_QAE_CCE_EXTERNAL_LIGHT_PRODUCT_POLICY_VALIDATION.json",
    "PSA_QAE_CCE_INDEPENDENT_H2_EQUALIZATION_CONTROL.json",
    "PSA_QAE_CCE_INDEPENDENT_H2_EQUALIZATION_CONTROL.csv",
    "PSA_QAE_CCE_INDEPENDENT_H2_EQUALIZATION_CONTROL.md",
    "PSA_QAE_CCE_INDEPENDENT_H2_EQUALIZATION_CONTROL_FIGURE.png",
    "PSA_QAE_CCE_INDEPENDENT_H2_EQUALIZATION_CONTROL_FIGURE.pdf",
    "PSA_QAE_CCE_INDEPENDENT_PYAPEP_H2_RECYCLE_VALIDATION.json",
    "PSA_QAE_CCE_INDEPENDENT_PYAPEP_H2_RECYCLE_VALIDATION.csv",
    "PSA_QAE_CCE_INDEPENDENT_PYAPEP_H2_RECYCLE_VALIDATION.md",
    "PSA_QAE_CCE_INDEPENDENT_PYAPEP_H2_RECYCLE_VALIDATION_FIGURE.png",
    "PSA_QAE_CCE_INDEPENDENT_PYAPEP_H2_RECYCLE_VALIDATION_FIGURE.pdf",
    "PSA_QAE_CCE_INDEPENDENT_PYAPEP_H2_RECYCLE_VALIDATION_SUPERSEDED_V1.json",
    "PSA_QAE_CCE_INDEPENDENT_PYAPEP_H2_RECYCLE_LONG_HORIZON_RAW.json",
    "PSA_QAE_CCE_INDEPENDENT_PYAPEP_H2_RECYCLE_DIRECTION_QUICK_V3.json",
    "PSA_QAE_CCE_INDEPENDENT_H2_POLICY_RESOLUTION_AUDIT.json",
    "PSA_QAE_CCE_INDEPENDENT_H2_POLICY_RESOLUTION_AUDIT.csv",
    "PSA_QAE_CCE_INDEPENDENT_H2_POLICY_RESOLUTION_AUDIT.md",
    "PSA_QAE_CCE_INDEPENDENT_H2_POLICY_RESOLUTION_AUDIT_FIGURE.png",
    "PSA_QAE_CCE_INDEPENDENT_H2_POLICY_RESOLUTION_AUDIT_FIGURE.pdf",
    "PSA_QAE_CCE_TOPSAIL_YANG_H2_PUBLIC_MODEL_AUDIT.json",
    "PSA_QAE_CCE_TOPSAIL_YANG_H2_PUBLIC_MODEL_AUDIT.csv",
    "PSA_QAE_CCE_TOPSAIL_YANG_H2_PUBLIC_MODEL_AUDIT.md",
    "PSA_QAE_CCE_TOPSAIL_YANG_H2_PUBLIC_MODEL_AUDIT_FIGURE.png",
    "PSA_QAE_CCE_TOPSAIL_YANG_H2_PUBLIC_MODEL_AUDIT_FIGURE.pdf",
    "PSA_QAE_CCE_PUBLIC_H2_SYNCHRONIZED_DATA_AUDIT.json",
    "PSA_QAE_CCE_PUBLIC_H2_SYNCHRONIZED_DATA_AUDIT.csv",
    "PSA_QAE_CCE_PUBLIC_H2_SYNCHRONIZED_DATA_AUDIT.md",
    "PSA_QAE_CCE_NOVELTY_SEARCH_AUDIT.json",
    "PSA_QAE_CCE_NOVELTY_SEARCH_AUDIT.md",
    "PSA_QAE_CCE_EXTERNAL_POLICY_NUMERICAL_REFINEMENT.json",
    "QAE_SURROGATE_MODEL_DISCREPANCY_BOUNDARY.json",
    "QAE_QPU_BREAKTHROUGH_PHASE_MLAE_IBM_db42v34lf4us73c24q50.json",
    "PSA_QAE_QPU_REPLICATION_CAMPAIGN_PLAN.json",
    "PSA_QAE_CCE_VALIDITY_BOUNDARY_FIGURE.json",
    "PSA_QAE_SCI_CLAIMS_AUDIT.json",
    "PSA_QAE_CCE_MANUSCRIPT_DRAFT_AUDIT.json",
    "PSA_QAE_CCE_GATE_COMPILATION_MANIFEST.json",
]

REPRO_FILES = [
    "PSA_QAE_CCE_AUTHOR_METADATA.json",
    "PSA_QAE_CCE_AUTHOR_METADATA.md",
    "PSA_QAE_CCE_EDITORIAL_PACKAGE.json",
    "PSA_QAE_CCE_EDITORIAL_PACKAGE.md",
    "PSA_QAE_CCE_SUBMISSION_CHECKLIST.md",
    "PSA_QAE_CCE_REQUIREMENTS_SCIENTIFIC.txt",
    "PSA_QAE_CCE_REQUIREMENTS_QISKIT.txt",
    "PSA_QAE_CCE_FIGURE_TABLE_PLAN_2026-10-09.md",
    "PSA_QAE_CCE_SUBMISSION_READINESS_2026-10-09.md",
    "PSA_QAE_CCE_FINAL_GAP_PLAN_2026-10-09.md",
]

CODE_FILES = [
    "build_cce_submission_docx.py",
    "build_cce_title_page_docx.py",
    "build_cce_supplementary_docx.py",
    "prepare_cce_public_repository.py",
    "qpu_breakthrough_mlae.py",
    "qpu_breakthrough_phase_mlae.py",
    "plan_qpu_replication_campaign.py",
    "analyze_qpu_replication_campaign.py",
    "collect_qpu_replication_campaign.py",
    "run_cce_primary_package.py",
    "run_cce_gate_compilation_package.py",
    "cce_calibrated_one_cycle_phase_map.py",
    "cce_policy_decision_margin.py",
    "cce_prospective_policy_design_audit.py",
    "cce_independent_h2_equalization_control.py",
    "cce_independent_pyapep_h2_recycle_validation.py",
    "cce_independent_pyapep_h2_topology_correction_audit.py",
    "cce_independent_h2_policy_resolution_audit.py",
    "cce_topsail_yang_h2_public_model_audit.py",
    "cce_public_h2_synchronized_data_audit.py",
    "cce_primary_physical_css_horizon_audit.py",
    "cce_primary_qstar_reversible_microkernel.py",
    "cce_primary_qstar_ldf_reversible_microstep.py",
    "cce_primary_all_component_ldf_reversible_microsteps.py",
    "cce_primary_product_boundary_reversible_microsteps.py",
    "cce_primary_internal_transport_reversible_microsteps.py",
    "cce_primary_cell_balance_reversible_microsteps.py",
    "cce_primary_loading_sign_balance_interface.py",
    "cce_primary_ldf_sign_balance_composition.py",
    "cce_primary_product_boundary_balance_composition.py",
    "cce_primary_product_ldf_valve_balance_composition.py",
    "cce_primary_normalized_product_ldf_valve_balance.py",
    "cce_primary_coherent_run_schedule_tank_interface.py",
    "cce_primary_coherent_run_factor_ldf_interface.py",
    "cce_primary_coherent_coefficient_ldf_balance_interface.py",
    "cce_primary_coherent_dynamic_langmuir_ldf_balance_interface.py",
    "cce_primary_coherent_normalized_dynamic_transport_ldf_balance.py",
    "cce_primary_offledger_tank_saturation_interface.py",
    "cce_primary_offledger_tank_proportional_interface.py",
    "cce_primary_physical_unsaturated_tank_trajectory.py",
    "cce_primary_internal_face_balance_composition.py",
    "cce_primary_composition_normalized_internal_face_balance.py",
    "cce_primary_joint_normalized_transport_ldf_balance.py",
    "cce_primary_physical_css_horizon_cache.npz",
    "psa_two_bed_spatial_tank_n2.py",
    "psa_two_bed_spatial_network_n2.py",
    "psa_spatial_network_probe_n2.py",
    "psa_two_bed_spatial_tank_n2_independent_source_uncertainty_32.py",
    "psa_two_bed_spatial_tank_n2_independent_source_uncertainty_32.csv",
    "cce_phase_map_fixed_point_screen.py",
    "compile_cce_phase_map_affine_blocks.py",
    "compile_cce_small_end_to_end_oracle.py",
    "extract_cce_primary_phase_ledger.py",
    "cce_primary_phase_event_bridge.py",
    "cce_primary_phase_event_fixed_point_screen.py",
    "compile_cce_primary_phase_event_blocks.py",
    "compile_cce_primary_final_event_arithmetic.py",
    "compile_cce_primary_policy_stream_event_oracle.py",
    "cce_primary_phase_event_free_running.py",
    "cce_primary_phase_event_repeated_cycle_screen.py",
    "cce_primary_css_initializer_event_bridge.py",
    "cce_primary_css_initializer_repeated_cycle_screen.py",
    "cce_primary_css_initializer_spectral_stability_screen.py",
    "cce_primary_css_initializer_fixed_point_screen.py",
    "compile_cce_primary_css_initializer_blocks.py",
    "make_cce_workflow_figure.py",
    "make_cce_resource_ladder.py",
    "make_cce_main_tables.py",
    "make_cce_validity_boundary_figure.py",
    "make_cce_submission_editorial_package.py",
    "assemble_cce_submission_package.py",
    "verify_cce_submission_package.py",
    "audit_psa_qae_manuscript_claims.py",
    "audit_cce_manuscript_draft.py",
    "audit_psa_qae_novelty_search.py",
]


def checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def resolve(group: str, name: str) -> Path:
    return HERE / name if group == "code" else RESULTS / name


def main() -> None:
    qpu_campaign = json.loads(
        (
            RESULTS
            / "PSA_QAE_QPU_REPLICATION_CAMPAIGN_ANALYSIS.json"
        ).read_text(encoding="utf-8")
    )
    if qpu_campaign.get("status") != "complete_9_of_9":
        raise RuntimeError("submission assembly requires the complete 9/9 QPU campaign")
    normalized_product = json.loads(
        (
            RESULTS
            / "PSA_QAE_CCE_PRIMARY_NORMALIZED_PRODUCT_LDF_VALVE_BALANCE.json"
        ).read_text(encoding="utf-8")
    )
    normalized_product_resources = normalized_product[
        "componentwise_compiled_direct_paths"
    ]
    normalized_product_upper = normalized_product[
        "conservative_five_component_upper_bound"
    ]
    coherent_interface = json.loads(
        (
            RESULTS
            / "PSA_QAE_CCE_COHERENT_RUN_SCHEDULE_TANK_INTERFACE.json"
        ).read_text(encoding="utf-8")
    )
    coherent_factor_ldf = json.loads(
        (
            RESULTS
            / "PSA_QAE_CCE_COHERENT_RUN_FACTOR_LDF_INTERFACE.json"
        ).read_text(encoding="utf-8")
    )
    coherent_coefficient_ldf_balance = json.loads(
        (
            RESULTS
            / "PSA_QAE_CCE_COHERENT_COEFFICIENT_LDF_BALANCE_INTERFACE.json"
        ).read_text(encoding="utf-8")
    )
    coherent_dynamic_langmuir_ldf_balance = json.loads(
        (
            RESULTS
            / "PSA_QAE_CCE_COHERENT_DYNAMIC_LANGMUIR_LDF_BALANCE_INTERFACE.json"
        ).read_text(encoding="utf-8")
    )
    coherent_normalized_dynamic_transport_ldf_balance = json.loads(
        (
            RESULTS
            / "PSA_QAE_CCE_COHERENT_NORMALIZED_DYNAMIC_TRANSPORT_LDF_BALANCE.json"
        ).read_text(encoding="utf-8")
    )
    offledger_tank_saturation = json.loads(
        (
            RESULTS
            / "PSA_QAE_CCE_OFFLEDGER_TANK_SATURATION_INTERFACE.json"
        ).read_text(encoding="utf-8")
    )
    offledger_tank_proportional = json.loads(
        (
            RESULTS
            / "PSA_QAE_CCE_OFFLEDGER_TANK_PROPORTIONAL_INTERFACE.json"
        ).read_text(encoding="utf-8")
    )
    physical_unsaturated_tank = json.loads(
        (
            RESULTS
            / "PSA_QAE_CCE_PHYSICAL_UNSATURATED_TANK_TRAJECTORY.json"
        ).read_text(encoding="utf-8")
    )
    qpu_support_files = [
        "PSA_QAE_QPU_REPLICATION_CAMPAIGN_PLAN.csv",
        "PSA_QAE_QPU_REPLICATION_CAMPAIGN_PLAN.md",
        "PSA_QAE_QPU_REPLICATION_CAMPAIGN_STATUS.json",
        "PSA_QAE_QPU_REPLICATION_CAMPAIGN_ANALYSIS.json",
        "PSA_QAE_QPU_REPLICATION_CAMPAIGN_ANALYSIS.csv",
        "PSA_QAE_QPU_REPLICATION_CAMPAIGN_ANALYSIS.md",
    ]
    for row in qpu_campaign["rows"]:
        stem = Path(str(row["source_file"])).stem
        qpu_support_files.extend(f"{stem}.{suffix}" for suffix in ("json", "csv", "md"))
    groups = {
        "main_text": MAIN_FILES,
        "supporting_information": list(dict.fromkeys(SI_FILES + qpu_support_files)),
        "reproducibility": REPRO_FILES,
        "code": CODE_FILES,
    }
    missing = []
    artifacts = []
    for group, names in groups.items():
        for name in names:
            path = resolve(group, name)
            if not path.exists():
                missing.append({"group": group, "path": str(path.relative_to(ROOT))})
                continue
            artifacts.append(
                {
                    "group": group,
                    "path": str(path.relative_to(ROOT)).replace("\\", "/"),
                    "bytes": path.stat().st_size,
                    "sha256": checksum(path),
                }
            )
    if missing:
        raise FileNotFoundError(json.dumps(missing, indent=2))

    si_lines = [
        "# Supplementary Information draft",
        "",
        "## S1. Frozen decision protocol and numerical reference",
        "",
        "The outer recycle candidates, joint event, target probability, conditional prior, estimator budgets, endpoints, and prohibited claims are frozen in `PSA_QAE_CCE_PRIMARY_CASE_PROTOCOL.json`. High-N scrambled-Sobol references are numerical references for the fitted conditional model and are not plant truth.",
        "",
        "## S2. Matched estimator records and decision diagnostics",
        "",
        "Complete 200-replication MC, RQMC, IS, and MLAE records, reference-scramble diagnostics, classification error, policy selection, timing labels, importance-sampling ESS, threshold activity, and the product-split/decision-margin audit accompany `PSA_QAE_CONTINUOUS_POLICY_SELECTION.json`, `PSA_QAE_CCE_PRIMARY_THRESHOLD_ACTIVITY.json`, and `PSA_QAE_CCE_POLICY_DECISION_MARGIN.json`. A separate prospective-design audit keeps the frozen candidates unchanged while mapping the p=0.50 crossing and the H2 validation precision required across the observed recycle support.",
        "",
        "## S3. Process evidence and one-cycle calibration bridge",
        "",
        "The reduced-H2 phase/equalization ledger, component inventories, mass-balance gates, nested leave-one-run-out phase maps, and one-cycle predictions are stored in `PSA_QAE_DIRECT_PHYSICAL_PHASE_LEDGER.json` and `PSA_QAE_CCE_CALIBRATED_ONE_CYCLE_PHASE_MAP.json`. The separate 32-run primary spatial/tank final-cycle ledger in `PSA_QAE_CCE_PRIMARY_PHASE_LEDGER.json` exposes eight phases, two equalizations, tank withdrawal, and product/recycle splits; its streams replay all source purity/recovery event outputs, with 25/32 joint events and 32/32 CSS-passing runs. The full 100-cycle boundary cache retains 85 physical scalars per boundary. All 32 rows settle, with latest joint physical horizon 68; a 16-bit precision screen gives a conservative 85-cycle horizon. One state uses 1,360 data qubits, while an explicit clean out-of-place current/next layout with ten raw event-stream scalars uses 2,880 before transport workspace. The competitive-Langmuir path screens 25,856 cached cell states and compiles separate clean one-second reciprocal/LDF updates for H2, CO2, CH4, CO, and N2. Individual circuits use 490–515 qubits and 1,118,920–1,965,308 CX; modular sequential accounting retains all current/next loadings at 675 qubits and 6,547,362 additive CX. Product-boundary compilation covers 6,464 valve states and 64 final-cycle product/tank records: the clean five-component valve/flux block uses 288 qubits and 800,762 CX, while fixed-0.420 five-component tank accounting uses 677 qubits and 1,043,990 additive CX. The valve fluxes are also consumed directly in 32,320 product-cell component balances and uncomputed in one 842-qubit, 2,348,388-CX clean circuit. A factor-specialized product-cell follow-on generates the adsorption/desorption terms from the shared product pressure/composition registers and combines them with the valve flux in the same conservative boundary balance. Its component paths use 1,072–1,195 qubits and 10,060,060–26,810,396 CX; the repeated-common-path upper bound is 1,195 peak qubits and 88,388,552 additive CX. Gas-inventory pressure reconstruction uses 152 qubits and 93,764 CX, and an oriented internal-face five-component transfer uses 404 qubits and 1,340,390 CX; modular two-pressure-plus-one-face accounting uses 584 qubits and 1,527,918 additive CX. The supplied-composition three-pressure/two-face/five-balance baseline uses 1,508 qubits and 8,328,622 CX. A support-adaptive 22-bit common-amount/22-bit reciprocal normalizer removes both independent composition inputs; two normalizers, three pressures, two faces, and five balances compile directly to 1,651 qubits, depth 22,143,683, and 14,667,150 CX over 25,856 normalization states and 64,640 balances. Supplied-sign cell-balance accounting uses 609 qubits and 366,802 additive CX. A direct current/next-loading interface extracts sign, converts loading change through solid mass, and composes the balance at 26/26/32/32/30 bits for H2/CO2/CH4/CO/N2; interface accounting uses 934 qubits and 1,411,882 additive CX. Recompiled widened LDF microsteps are then mapped directly into that interface and exactly reversed. The clean component circuits use 861–929 qubits and 3,412,254–4,991,534 CX; five-component sequential accounting uses 1,317 qubits and 19,082,852 additive CX. Five further parameter-specialized paths connect full 20-bit normalized pressure/composition and both generated internal faces to LDF uptake and the same conservative component balance; they use 1,944–2,039 qubits and 20,670,468–35,947,274 CX each, with a conservative common-path-repeating upper bound of 2,039 peak qubits and 128,013,726 additive CX. A monolithic five-component transpilation, coherent run-parameter register, product-composition normalization and inward-face generation at the product cell, tank withdrawal, adaptive integration, routing, and full phase integration remain open. A parameter-only nested-held-out initializer retains 32/32 one-cycle labels, while raw aggregate 50-cycle repetition retains only 2/32 CSS passes. These evidence tiers remain distinct.",
        "",
        "## S4. Fixed-point response and calibrated phase-map circuits",
        "",
        "This section reports the response-event precision scan, finite truth-table controls, calibrated affine blocks, and coherent module-connection controls. The primary stream bridge compiles 12 adsorption-stream blocks to 272 logical qubits and 2,202,466 clean CX. The modular final event uses 125 qubits and 182,981 clean CX. The integrated policy construction retains 96/96 candidate-policy and 32/32 ledger-support labels at 510 qubits and 1,286,021 clean CX. The parameter-only initializer compiles to 118 qubits and 578,702 forward CX. The competitive-Langmuir construction is extended through clean one-second LDF updates for H2, CO2, CH4, CO, and N2. The five component circuits compile individually to 490–515 qubits and 1,118,920–1,965,308 CX; modular sequential accounting with retained current/next loadings uses 675 qubits and 6,547,362 additive CX. The product-end valve/flux circuit uses 288 qubits and 800,762 CX; it is directly composed with five product-cell balances at 842 qubits, depth 3,285,605, and 2,348,388 CX. Factor-specialized product-cell LDF/valve/balance paths use 1,072–1,195 qubits and 10,060,060–26,810,396 CX per component, with a 1,195-peak-qubit/88,388,552-additive-CX conservative upper bound. Separate five-component product-split/tank-capacity accounting uses 677 qubits and 1,043,990 additive CX. Pressure reconstruction uses 152 qubits and 93,764 CX, and oriented internal-face transfer uses 404 qubits and 1,340,390 CX; modular two-pressure-plus-one-face accounting uses 584 qubits and 1,527,918 additive CX. The supplied-composition direct baseline uses 1,508 qubits and 8,328,622 CX. Generating both upwind compositions from gas inventories and composing the full path uses 1,651 qubits, depth 22,143,683, and 14,667,150 CX; the standalone normalizer uses 333 qubits and 1,340,232 CX. Supplied-sign cell balance uses 609 qubits and 366,802 additive CX. Reversible sign extraction and solid-mass conversion are directly composed with that balance at 934 qubits and 1,411,882 additive CX across five components. Widened LDF outputs are directly composed with this interface at 861–929 qubits and 3,412,254–4,991,534 CX per component; five-component accounting is 1,317 qubits and 19,082,852 additive CX. Reversible run-specific parameters, product composition normalization and inward-face generation, monolithic five-component transpilation, tank withdrawal, adaptive integration, state loading, and routing remain open.",
        "",
        "## S5. Correlated state-preparation boundary",
        "",
        "One- and two-bit dense empirical-copula loaders are compiled exactly. The seven-bit accuracy tier is a storage/address-space extrapolation, not a synthesized loader. No general lower bound against structured reversible Gaussian/quantile loading is claimed.",
        "",
        "## S6. QPU execution and preflight",
        "",
        f"The completed three-backend by three-seed IBM campaign contains nine Open-plan jobs and {qpu_campaign['summary']['total_qpu_charge_seconds_recorded']:.0f} s of recorded QPU charge. Its mean event estimate is {qpu_campaign['summary']['estimate_mean']:.6f}, the mean absolute error from p=0.625 is {qpu_campaign['summary']['mean_absolute_error']:.6f}, and the between-job standard deviation is {qpu_campaign['summary']['between_job_sd']:.6f}. The crossed-design bootstrap interval [{qpu_campaign['summary']['crossed_design_bootstrap']['low_2_5_percent']:.6f}, {qpu_campaign['summary']['crossed_design_bootstrap']['high_97_5_percent']:.6f}] describes only the sampled backend/seed design. Raw counts, physical layouts, depths, two-qubit instructions, calibration timestamps, and charges are archived for every job. Ideal-model likelihood intervals are not interpreted as noise-calibrated hardware confidence intervals.",
        "",
        "## S7. External and model-form validity controls",
        "",
        "TU Wien H2/CH4 tables provide H2 separation calibration; Thelen VA-10 provides a matched same-chemistry equalization-pressure/recovery direction control; the Otway log provides cross-chemistry hydraulic plausibility; and the public CO2/N2 solver supplies an executable policy-direction control. Applying only the frozen numeric candidate spacings to the Voigt H2 recovery coefficient gives a maximum effect/group-held-out-RMSE ratio of 0.1332 and would require a 37.5-fold RMSE reduction to pass the declared five-times gate; purge/feed is also not product recycle and continuous purity is not identifiable. An audit of the pyAPEP 0.1.8 wrapper supersedes its earlier feed-end pressurisation and adsorption-feed-only recovery calculation. The corrected product-end wrapper includes external high-purity makeup in the recovery denominator and reports tank self-sufficiency. Its three-policy 15-cycle screen is pre-CSS; a separate 450-cycle 0.420 control reaches purity 0.991666, external-boundary recovery 0.044166, tank supply fraction 0.03164, and CSS residual 1.2538e-3, so it fails purity, recovery, tank, and CSS gates and is retained only as a topology-feasibility stress test. The public toPSAil/Yang branch adds an experimentally anchored H2/CO 70/30 two-bed six-step zeolite-5A model with product tank, equalization, purge, valve/pressure/recovery calibration, and published 13/42/36/31-cycle CSS controls. Yang's 99.99% purity passes the frozen purity threshold, but its 75.87% recovery fails the frozen event; purge/feed remains distinct from product-gas recycle and the repository exposes no cycle-result MAT files. These controls are distinct evidence tiers and do not validate the local H2 recycle selection.",
        "A structured public-data audit covers ten H2 experiments, pilots, industrial precedents, models, and the cross-chemistry Otway historian. Zero of ten sources jointly provide H2 chemistry, a public synchronized valve/pressure/feed-flow/product-flow/product-composition file, the frozen product-gas-recycle policy, and the frozen purity/recovery event. The Schell H2/CO2 laboratory database is retained as a cyclic experimental anchor, while the Cranfield record exposes only a disclaimer file in the scoped public access. `PSA_QAE_CCE_PUBLIC_H2_SYNCHRONIZED_DATA_AUDIT.json` records the channel-by-channel admissible role and exclusion reason for every source.",
        "",
        "## S8. Reproducibility and file integrity",
        "",
        "Two environment freezes, deterministic local runners, random seeds, transpiler settings, claim audits, and this SHA-256 manifest are included. Reproduction runners do not submit QPU work. The IBM API credential is excluded.",
        "",
        "## S9. Bounded literature-search protocol",
        "",
        "The novelty screen was refreshed on 9 October 2026 with four exact and related queries: `\"pressure swing adsorption\" \"quantum amplitude estimation\"`; `\"pressure swing adsorption\" quantum computing optimization`; `\"quantum amplitude estimation\" adsorption process`; and `\"quantum amplitude estimation\" chemical process optimization`. Crossref and OpenAlex were queried through their public APIs, and candidate records were checked at publisher, DOI, repository, or preprint pages. Records were assigned to QAE/risk methods, process-quantum precedents, or classical PSA optimization and simulation. Quantum molecular-sieving papers were excluded because they concern material selectivity rather than gate-based probability estimation. The machine-readable audit retrieved 299 query-result records and 220 unique DOI/title records, with zero records satisfying the explicit PSA-plus-QAE/MLAE metadata rule. The result supports only the phrasing “no direct case was identified in this scoped search”; it does not establish an exhaustive systematic-review or priority claim. Full queries, metadata, classification rule, and claim boundary are archived in `PSA_QAE_CCE_NOVELTY_SEARCH_AUDIT.json`.",
        "",
        "## Open evidence gates",
        "",
        "- Calibrated same-policy H2 recycle/event validation; the corrected pyAPEP path is a non-CSS topology-feasibility stress test, the Thelen pair is a narrower equalization-direction control, and the toPSAil/Yang branch is a same-chemistry model/experiment anchor with different policy semantics.",
        "- A completed reversible nonlinear tank/spatial cycle map feeding the policy stream-to-event oracle. The source model settles, its 85-cycle target is quantified, and direct five-component LDF-to-loading-sign-to-cell-balance, gas-normalization-to-two-face-to-interior-cell, parameter-specialized normalized-transport/LDF/interior-balance, supplied-composition product-cell LDF/valve/boundary-balance, gas-inventory-generated product-cell normalization/inward-face/LDF/valve/balance paths, coherent control, pressure-derived saturated/unsaturated tank allocation, and one short-schedule source-model physical unsaturated control are compiled; frozen-schedule physical unsaturated coverage, a monolithic five-component phase/cycle, adaptive phase integration, and remaining workspace are open.",
        "- A scalable structured correlated loader if an end-to-end speedup claim is pursued.",
    ]
    product_open_old = (
        "a monolithic five-component transpilation, coherent run-parameter register, "
        "product-composition normalization and inward-face generation at the product "
        "cell, tank withdrawal, adaptive integration, routing, and full phase "
        "integration remain open"
    )
    product_open_new = (
        "direct wiring of the finite-support run/schedule/tank controller into the "
        "component paths, frozen-schedule physical unsaturated coverage, a monolithic five-component "
        "transpilation, adaptive integration, routing, and full phase integration remain open"
    )
    short_open_old = (
        "Reversible run-specific parameters, product composition normalization and "
        "inward-face generation, monolithic five-component transpilation, tank "
        "withdrawal, adaptive integration, state loading, and routing remain open."
    )
    short_open_new = (
        "A finite-support run/schedule/tank controller and a direct run-factor-to-five-component-LDF-coefficient interface are compiled separately. Direct "
        "coefficient consumption inside the state-update paths, frozen-schedule physical unsaturated coverage, monolithic "
        "five-component transpilation, adaptive integration, state loading, and routing remain open."
    )
    si_lines = [
        line.replace(product_open_old, product_open_new).replace(
            short_open_old, short_open_new
        ).replace(
            "coherent run-specific parameters, product composition normalization and inward-face generation, tank withdrawal",
            "coherent run-specific parameters, valve scheduling, tank withdrawal",
        ).replace(
            "A monolithic five-component transpilation, coherent run-parameter register, product-composition normalization and inward-face generation at the product cell, tank withdrawal",
            "Direct wiring of the finite-support run/schedule/tank controller into the component paths, frozen-schedule physical unsaturated coverage, and a monolithic five-component transpilation",
        ).replace(
            "a monolithic five-component transpilation, coherent run-specific parameters, valve scheduling, tank withdrawal, adaptive phase integration, and remaining workspace are open",
            "direct consumption of coherent coefficient registers inside a monolithic five-component state update, frozen-schedule physical unsaturated coverage, adaptive phase integration, and remaining workspace are open",
        )
        for line in si_lines
    ]
    normalized_product_paragraph = (
        "A further product-cell composition closes the previously supplied product "
        "composition and inward-face inputs. Two encoded five-component gas inventories "
        "generate both normalized compositions, both pressures, one oriented inward "
        "face, factor-specialized LDF transfer, product-valve withdrawal, loading-sign "
        "conversion, and one conservative next-gas balance before exact reversal. The "
        f"five component paths use {min(row['logical_qubits'] for row in normalized_product_resources):,}–"
        f"{max(row['logical_qubits'] for row in normalized_product_resources):,} qubits, "
        f"depths {min(row['depth_all_to_all'] for row in normalized_product_resources):,}–"
        f"{max(row['depth_all_to_all'] for row in normalized_product_resources):,}, and "
        f"{min(row['cx'] for row in normalized_product_resources):,}–"
        f"{max(row['cx'] for row in normalized_product_resources):,} CX. The conservative "
        f"upper bound is {normalized_product_upper['logical_qubits_peak']:,} peak qubits, "
        f"depth {normalized_product_upper['depth_all_to_all_additive_upper_bound']:,}, "
        f"and {normalized_product_upper['cx_additive_upper_bound']:,} additive CX. All "
        "32,320 frozen-support balances pass the declared precision, erasure, underflow, "
        "and overflow gates."
    )
    coherent_interface_paragraph = (
        "A coherent finite-support controller checks "
        f"{coherent_interface['parameter_encoding']['basis_table_values_checked']} run/parameter table entries, "
        f"all {coherent_interface['schedule_encoding']['basis_addresses_checked']} stage addresses, and "
        f"{coherent_interface['tank_encoding']['basis_component_records_checked']} run/slot/component tank records. "
        f"The directly transpiled interface uses {coherent_interface['integrated_interface']['logical_qubits']:,} logical qubits, "
        f"depth {coherent_interface['integrated_interface']['depth_all_to_all']:,}, "
        f"{coherent_interface['integrated_interface']['cx']:,} CX, and "
        f"{coherent_interface['integrated_interface']['u']:,} u gates with no measurement or reset. "
        "It is a ledger-support controller rather than a continuous off-ledger parameter, valve, or tank-demand evaluator."
    )
    coherent_factor_ldf_paragraph = (
        "A second coherent circuit consumes the loaded capacity, affinity, and LDF-factor words in reversible arithmetic. "
        "It generates five equilibrium prefactors, five LDF-alpha coefficients, and two paired-bed adsorption flags. "
        f"The audit checks {coherent_factor_ldf['support']['coefficient_records_checked']} coefficient records and "
        f"{coherent_factor_ldf['support']['schedule_flags_checked']} bed/stage flags; maximum relative errors are "
        f"{coherent_factor_ldf['precision']['five_component_equilibrium_prefactor_max_relative_error']:.3e} for equilibrium prefactors and "
        f"{coherent_factor_ldf['precision']['five_component_ldf_alpha_max_relative_error']:.3e} for LDF alpha. "
        f"The directly transpiled interface uses {coherent_factor_ldf['compiled_interface']['logical_qubits']:,} logical qubits, "
        f"depth {coherent_factor_ldf['compiled_interface']['depth_all_to_all']:,}, and "
        f"{coherent_factor_ldf['compiled_interface']['cx']:,} CX with no measurement or reset. "
        "Their direct consumption in component state-update paths is reported in the following tier."
    )
    coherent_coefficient_ldf_balance_resources = coherent_coefficient_ldf_balance[
        "componentwise_compiled_direct_paths"
    ]
    coherent_coefficient_ldf_balance_upper = coherent_coefficient_ldf_balance[
        "conservative_five_component_upper_bound"
    ]
    coherent_coefficient_ldf_balance_paragraph = (
        "The controller-generated equilibrium and LDF-alpha coefficients are then consumed in five separately compiled, schedule-gated component paths. "
        "Each path combines a supplied 20-bit competitive-Langmuir response with q* generation, sign-preserving LDF loading update, solid conversion, and one conservative gas balance. "
        f"Across {coherent_coefficient_ldf_balance['support']['component_balance_records_checked']:,} component-balance records, the maximum q*, LDF-next, and next-gas scale-normalized errors are "
        f"{max(row['qstar_max_loading_scale_normalized_absolute_error'] for row in coherent_coefficient_ldf_balance['components']):.3e}, "
        f"{max(row['ldf_next_max_loading_scale_normalized_absolute_error'] for row in coherent_coefficient_ldf_balance['components']):.3e}, and "
        f"{max(row['next_gas_max_scale_normalized_absolute_error'] for row in coherent_coefficient_ldf_balance['components']):.3e}, with zero quantized-transfer erasure. "
        f"The paths use {min(row['logical_qubits'] for row in coherent_coefficient_ldf_balance_resources):,}–{max(row['logical_qubits'] for row in coherent_coefficient_ldf_balance_resources):,} logical qubits and "
        f"{min(row['cx'] for row in coherent_coefficient_ldf_balance_resources):,}–{max(row['cx'] for row in coherent_coefficient_ldf_balance_resources):,} CX; the repeated-controller upper bound is "
        f"{coherent_coefficient_ldf_balance_upper['logical_qubits_peak']:,} peak qubits, depth {coherent_coefficient_ldf_balance_upper['depth_all_to_all_additive_upper_bound']:,}, and {coherent_coefficient_ldf_balance_upper['cx_additive_upper_bound']:,} additive CX. "
        "Dynamic affinity-denominator/reciprocal generation from pressure/composition remains open."
    )
    coherent_dynamic_langmuir_resources = coherent_dynamic_langmuir_ldf_balance[
        "componentwise_compiled_direct_paths"
    ]
    coherent_dynamic_langmuir_upper = coherent_dynamic_langmuir_ldf_balance[
        "conservative_five_component_upper_bound"
    ]
    coherent_dynamic_langmuir_design = coherent_dynamic_langmuir_ldf_balance[
        "selected_dynamic_response_design"
    ]
    coherent_dynamic_langmuir_paragraph = (
        "The next controller-coupled tier removes the supplied competitive-Langmuir response. "
        "Its retained 12-bit run-affinity word and supplied 20-bit pressure/five-component composition generate the affinity-dependent denominator, a global reciprocal lookup, and the component response before direct q*/LDF/loading/balance consumption. "
        f"The selected {coherent_dynamic_langmuir_design['affinity_bits']}-bit affinity/{coherent_dynamic_langmuir_design['denominator_address_bits']}-bit address design uses {coherent_dynamic_langmuir_design['reciprocal_segments']:,} reciprocal segments; denominator p95/max absolute errors are {coherent_dynamic_langmuir_design['denominator_p95_absolute_error']:.3e}/{coherent_dynamic_langmuir_design['denominator_max_absolute_error']:.3e}. "
        f"Across {coherent_dynamic_langmuir_ldf_balance['support']['component_balance_records_checked']:,} component balances, the five directly transpiled paths use {min(row['logical_qubits'] for row in coherent_dynamic_langmuir_resources):,}–{max(row['logical_qubits'] for row in coherent_dynamic_langmuir_resources):,} logical qubits and {min(row['cx'] for row in coherent_dynamic_langmuir_resources):,}–{max(row['cx'] for row in coherent_dynamic_langmuir_resources):,} CX; the repeated-controller upper bound is {coherent_dynamic_langmuir_upper['logical_qubits_peak']:,} peak qubits and {coherent_dynamic_langmuir_upper['cx_additive_upper_bound']:,} additive CX. "
        "Gas normalization, face generation, and tank-demand logic are reported separately; monolithic five-component phase/cycle integration remains open."
    )
    coherent_normalized_dynamic_resources = coherent_normalized_dynamic_transport_ldf_balance[
        "componentwise_compiled_direct_paths"
    ]
    coherent_normalized_dynamic_upper = coherent_normalized_dynamic_transport_ldf_balance[
        "conservative_five_component_upper_bound"
    ]
    coherent_normalized_dynamic_paragraph = (
        "The highest controller-coupled local tier removes the supplied pressure, composition, and face-flux words. "
        "Three raw five-component gas inventories generate two normalized compositions, three pressures, and two oriented faces before the centre state enters the dynamic Langmuir, q*, LDF, loading-sign, and conservative-balance path. "
        f"Across {coherent_normalized_dynamic_transport_ldf_balance['support']['normalization_states']:,} normalization states and {coherent_normalized_dynamic_transport_ldf_balance['support']['component_balance_records_checked']:,} component balances, the five directly transpiled paths use {min(row['logical_qubits'] for row in coherent_normalized_dynamic_resources):,}–{max(row['logical_qubits'] for row in coherent_normalized_dynamic_resources):,} logical qubits and {min(row['cx'] for row in coherent_normalized_dynamic_resources):,}–{max(row['cx'] for row in coherent_normalized_dynamic_resources):,} CX. "
        f"The repeated-path upper bound is {coherent_normalized_dynamic_upper['logical_qubits_peak']:,} peak qubits, depth {coherent_normalized_dynamic_upper['depth_all_to_all_additive_upper_bound']:,}, and {coherent_normalized_dynamic_upper['cx_additive_upper_bound']:,} additive CX. "
        "Separate pressure-derived saturated and proportional tank branches are reported next; monolithic five-component phase/cycle integration, adaptive integration, routing, external H2 validation, and quantum advantage remain open."
    )
    offledger_tank_resources = offledger_tank_saturation["compiled_clean_circuit"]
    offledger_tank_selected = offledger_tank_saturation["selected_design"]
    offledger_proportional_resources = offledger_tank_proportional[
        "compiled_clean_circuit"
    ]
    offledger_proportional_selected = offledger_tank_proportional[
        "selected_design"
    ]
    physical_unsaturated_resources = physical_unsaturated_tank[
        "compiled_clean_circuit"
    ]
    physical_unsaturated_selected = physical_unsaturated_tank["selected_design"]
    offledger_tank_paragraph = (
        "The pressure-derived tank follow-on removes the recorded-withdrawal QROM on the frozen saturated branch. "
        "Five raw endpoint gas inventories generate source-end pressure and an end-pressure demand lower bound, which is compared reversibly with the five-component tank inventory before saturated withdrawal, componentwise subtraction, and exact workspace reversal. "
        f"All {offledger_tank_saturation['support']['records']} final-cycle calls retain the saturation label with minimum lower-bound margin {offledger_tank_selected['minimum_lower_bound_minus_tank_mol']:.6f} mol and p95 aggregate normalized error {offledger_tank_selected['all_output_p95_scale_normalized_absolute_error']:.3e}. "
        f"The saturated-only clean circuit uses {offledger_tank_resources['logical_qubits']:,} logical qubits, depth {offledger_tank_resources['depth_all_to_all']:,}, and {offledger_tank_resources['cx']:,} CX. "
        "A second circuit adds support-adaptive reciprocal lookup and reversible multiplication to select the saturated branch or proportional unsaturated allocation. "
        f"It preserves {offledger_tank_proportional['support']['observed_saturated_records']} observed saturated and {offledger_tank_proportional['support']['counterfactual_unsaturated_records']} bounded-counterfactual unsaturated labels with p95/max component-scale normalized errors {offledger_proportional_selected['withdrawal_and_next_p95_component_scale_normalized_absolute_error']:.3e}/{offledger_proportional_selected['withdrawal_and_next_max_component_scale_normalized_absolute_error']:.3e}. "
        f"The combined clean circuit uses {offledger_proportional_resources['logical_qubits']:,} logical qubits, depth {offledger_proportional_resources['depth_all_to_all']:,}, and {offledger_proportional_resources['cx']:,} CX. "
        "The 224 counterfactual cases are bounded arithmetic tests over observed tank compositions. "
        f"A separate source-model control keeps the sample-0 recycle fraction, shortens non-adsorption from 10 s to {physical_unsaturated_tank['trajectory']['non_adsorption_duration_s']:.2f} s, reaches CSS {physical_unsaturated_tank['trajectory']['final_css_residual_max']:.3e}, and yields {physical_unsaturated_tank['trajectory']['unsaturated_calls']}/{physical_unsaturated_tank['trajectory']['tank_calls']} unsaturated zero-makeup calls. "
        f"A start/end-pressure trapezoidal-demand circuit reduces p95 demand error to {physical_unsaturated_tank['pressure_demand_diagnostics']['trapezoid_proxy_p95_relative_error']:.3%}, retains withdrawal/next-tank p95 error {physical_unsaturated_selected['withdrawal_and_next_p95_component_scale_normalized_absolute_error']:.3e}, and compiles to {physical_unsaturated_resources['logical_qubits']:,} logical qubits, depth {physical_unsaturated_resources['depth_all_to_all']:,}, and {physical_unsaturated_resources['cx']:,} CX. "
        "This is a short-schedule model control rather than the frozen 10-s policy or plant validation; phase-end state generation inside a monolithic phase remains open."
    )
    generated_si_prefixes = (
        "A further product-cell composition closes",
        "A coherent finite-support controller checks",
        "A second coherent circuit consumes",
        "The controller-generated equilibrium and LDF-alpha coefficients are then consumed",
        "The next controller-coupled tier removes the supplied competitive-Langmuir response",
        "The highest controller-coupled local tier removes the supplied pressure",
        "The pressure-derived tank follow-on removes the recorded-withdrawal QROM",
    )
    existing_generated = [
        index
        for index, line in enumerate(si_lines)
        if any(line.startswith(prefix) for prefix in generated_si_prefixes)
    ]
    if existing_generated:
        existing_s4 = si_lines.index(
            "## S4. Fixed-point response and calibrated phase-map circuits"
        )
        del si_lines[min(existing_generated):existing_s4]
    s4_index = si_lines.index("## S4. Fixed-point response and calibrated phase-map circuits")
    si_lines[s4_index:s4_index] = [normalized_product_paragraph, "", coherent_interface_paragraph, "", coherent_factor_ldf_paragraph, "", coherent_coefficient_ldf_balance_paragraph, "", coherent_dynamic_langmuir_paragraph, "", coherent_normalized_dynamic_paragraph, "", offledger_tank_paragraph, ""]
    OUT_SI.write_text("\n".join(si_lines) + "\n", encoding="utf-8")
    si_artifact = {
        "group": "supporting_information",
        "path": str(OUT_SI.relative_to(ROOT)).replace("\\", "/"),
        "bytes": OUT_SI.stat().st_size,
        "sha256": checksum(OUT_SI),
    }
    artifacts.append(si_artifact)

    payload = {
        "schema": "psa-qae-cce-submission-package-manifest/v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "local_submission_packet_assembled_external_evidence_gates_open",
        "submission_ready": False,
        "qpu_submission": False,
        "artifact_count": len(artifacts),
        "groups": {group: sum(row["group"] == group for row in artifacts) for group in set(row["group"] for row in artifacts)},
        "artifacts": artifacts,
        "open_gates": [
            "calibrated same-policy H2 recycle/event validation (corrected pyAPEP topology stress test and same-chemistry equalization control completed)",
            "completed reversible nonlinear tank/spatial cycle map feeding the compiled policy stream-to-event oracle; physical horizon/register accounting, direct five-component LDF-to-loading-sign-to-cell-balance, gas-inventory-generated product-cell paths, a finite-support coherent run/schedule/tank interface, pressure-derived saturated and bounded-counterfactual proportional tank-allocation branches, one short-schedule source-model physical unsaturated control, and five raw-gas-inventory-to-normalization/pressure/two-face/dynamic-Langmuir/LDF/loading/balance paths are quantified, while frozen-schedule physical unsaturated coverage, monolithic five-component phase integration, adaptive integration, and remaining workspace remain open",
            "permanent public archive DOI and journal-formatted final files",
        ],
        "note": "This manifest proves local packet completeness and file integrity only; it does not establish plant validation, hardware advantage, journal acceptance, or closure of external evidence gates.",
    }
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# CCE submission package manifest",
        "",
        f"Status: **{payload['status']}**",
        "",
        f"Submission ready: **{payload['submission_ready']}**",
        "",
        f"Artifacts: **{payload['artifact_count']}**. QPU submission during assembly: **{payload['qpu_submission']}**.",
        "",
        "| group | path | bytes | SHA-256 |",
        "|---|---|---:|---|",
    ]
    for row in artifacts:
        lines.append(f"| {row['group']} | {row['path']} | {row['bytes']:,} | `{row['sha256']}` |")
    lines += ["", "## Open gates", ""] + [f"- {gate}" for gate in payload["open_gates"]] + ["", payload["note"]]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"status": payload["status"], "artifacts": len(artifacts), "submission_ready": False, "qpu_submission": False}, indent=2))


if __name__ == "__main__":
    main()
