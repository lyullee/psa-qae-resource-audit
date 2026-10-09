"""Build CCE-facing editorial material without submitting work or using a QPU."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
from PIL import Image


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RESULTS = ROOT / "10_TEA_LCA_Python" / "results" / "pycharm_publication_enhancement"

MANUSCRIPT = RESULTS / "PSA_QAE_CCE_CORE_MANUSCRIPT_DRAFT.md"
TABLE2 = RESULTS / "PSA_QAE_CCE_TABLE2_MATCHED_ESTIMATORS.json"
RESOURCE_TABLE = RESULTS / "PSA_QAE_CCE_RESOURCE_TABLE3.json"
PROSPECTIVE = RESULTS / "PSA_QAE_CCE_PROSPECTIVE_POLICY_DESIGN_AUDIT.json"
QPU = RESULTS / "QAE_QPU_BREAKTHROUGH_PHASE_MLAE_IBM_db42v34lf4us73c24q50.json"
QPU_CAMPAIGN = RESULTS / "PSA_QAE_QPU_REPLICATION_CAMPAIGN_ANALYSIS.json"
CSS_INITIALIZER = RESULTS / "PSA_QAE_CCE_PRIMARY_CSS_INITIALIZER_EVENT_BRIDGE.json"
CSS_REPEATED = RESULTS / "PSA_QAE_CCE_PRIMARY_CSS_INITIALIZER_REPEATED_CYCLE_SCREEN.json"
CSS_STABILITY = RESULTS / "PSA_QAE_CCE_PRIMARY_CSS_INITIALIZER_SPECTRAL_STABILITY_SCREEN.json"
CSS_COMPILE = RESULTS / "PSA_QAE_CCE_PRIMARY_CSS_INITIALIZER_BLOCK_COMPILE.json"
FINAL_EVENT = RESULTS / "PSA_QAE_CCE_PRIMARY_FINAL_EVENT_ARITHMETIC.json"
POLICY_STREAM_EVENT = RESULTS / "PSA_QAE_CCE_PRIMARY_POLICY_STREAM_EVENT_ORACLE.json"
PHYSICAL_CSS = RESULTS / "PSA_QAE_CCE_PRIMARY_PHYSICAL_CSS_HORIZON_AUDIT.json"
QSTAR_MICROKERNEL = RESULTS / "PSA_QAE_CCE_PRIMARY_QSTAR_REVERSIBLE_MICROKERNEL.json"
QSTAR_LDF_MICROSTEP = RESULTS / "PSA_QAE_CCE_PRIMARY_QSTAR_LDF_REVERSIBLE_MICROSTEP.json"
ALL_COMPONENT_LDF = RESULTS / "PSA_QAE_CCE_PRIMARY_ALL_COMPONENT_LDF_MICROSTEPS.json"
PRODUCT_BOUNDARY = RESULTS / "PSA_QAE_CCE_PRIMARY_PRODUCT_BOUNDARY_MICROSTEPS.json"
PRODUCT_BOUNDARY_BALANCE = RESULTS / "PSA_QAE_CCE_PRIMARY_PRODUCT_BOUNDARY_BALANCE_COMPOSITION.json"
PRODUCT_LDF_VALVE_BALANCE = RESULTS / "PSA_QAE_CCE_PRIMARY_PRODUCT_LDF_VALVE_BALANCE_COMPOSITION.json"
NORMALIZED_PRODUCT_LDF_VALVE_BALANCE = RESULTS / "PSA_QAE_CCE_PRIMARY_NORMALIZED_PRODUCT_LDF_VALVE_BALANCE.json"
COHERENT_RUN_SCHEDULE_TANK = RESULTS / "PSA_QAE_CCE_COHERENT_RUN_SCHEDULE_TANK_INTERFACE.json"
COHERENT_RUN_FACTOR_LDF = RESULTS / "PSA_QAE_CCE_COHERENT_RUN_FACTOR_LDF_INTERFACE.json"
COHERENT_COEFFICIENT_LDF_BALANCE = RESULTS / "PSA_QAE_CCE_COHERENT_COEFFICIENT_LDF_BALANCE_INTERFACE.json"
COHERENT_DYNAMIC_LANGMUIR_LDF_BALANCE = RESULTS / "PSA_QAE_CCE_COHERENT_DYNAMIC_LANGMUIR_LDF_BALANCE_INTERFACE.json"
COHERENT_NORMALIZED_DYNAMIC_TRANSPORT_LDF_BALANCE = RESULTS / "PSA_QAE_CCE_COHERENT_NORMALIZED_DYNAMIC_TRANSPORT_LDF_BALANCE.json"
OFFLEDGER_TANK_SATURATION = RESULTS / "PSA_QAE_CCE_OFFLEDGER_TANK_SATURATION_INTERFACE.json"
OFFLEDGER_TANK_PROPORTIONAL = RESULTS / "PSA_QAE_CCE_OFFLEDGER_TANK_PROPORTIONAL_INTERFACE.json"
PHYSICAL_UNSATURATED_TANK = RESULTS / "PSA_QAE_CCE_PHYSICAL_UNSATURATED_TANK_TRAJECTORY.json"
INTERNAL_TRANSPORT = RESULTS / "PSA_QAE_CCE_PRIMARY_INTERNAL_TRANSPORT_MICROSTEPS.json"
INTERNAL_FACE_BALANCE = RESULTS / "PSA_QAE_CCE_PRIMARY_INTERNAL_FACE_BALANCE_COMPOSITION.json"
NORMALIZED_INTERNAL_FACE_BALANCE = RESULTS / "PSA_QAE_CCE_PRIMARY_COMPOSITION_NORMALIZED_INTERNAL_FACE_BALANCE.json"
CELL_BALANCE = RESULTS / "PSA_QAE_CCE_PRIMARY_CELL_BALANCE_MICROSTEPS.json"
LOADING_SIGN_BALANCE = RESULTS / "PSA_QAE_CCE_PRIMARY_LOADING_SIGN_BALANCE_INTERFACE.json"
LDF_SIGN_BALANCE = RESULTS / "PSA_QAE_CCE_PRIMARY_LDF_SIGN_BALANCE_COMPOSITION.json"
JOINT_NORMALIZED_TRANSPORT_LDF_BALANCE = RESULTS / "PSA_QAE_CCE_PRIMARY_JOINT_NORMALIZED_TRANSPORT_LDF_BALANCE.json"

OUT_JSON = RESULTS / "PSA_QAE_CCE_EDITORIAL_PACKAGE.json"
OUT_MD = RESULTS / "PSA_QAE_CCE_EDITORIAL_PACKAGE.md"
OUT_COVER = RESULTS / "PSA_QAE_CCE_COVER_LETTER_DRAFT.md"
OUT_HIGHLIGHTS = RESULTS / "PSA_QAE_CCE_HIGHLIGHTS.txt"
OUT_CHECKLIST = RESULTS / "PSA_QAE_CCE_SUBMISSION_CHECKLIST.md"
OUT_PNG = RESULTS / "PSA_QAE_CCE_GRAPHICAL_ABSTRACT.png"
OUT_PDF = RESULTS / "PSA_QAE_CCE_GRAPHICAL_ABSTRACT.pdf"

MAIN_FIGURE_BASES = [
    "PSA_QAE_CCE_WORKFLOW_FIGURE",
    "PSA_QAE_CONTINUOUS_POLICY_SELECTION_FIGURE",
    "PSA_QAE_CCE_PRIMARY_RESOURCE_BOUNDARY_FIGURE",
    "PSA_QAE_CCE_RESOURCE_LADDER_FIGURE",
    "PSA_QAE_QPU_REPLICATION_CAMPAIGN_ANALYSIS_FIGURE",
    "PSA_QAE_CCE_VALIDITY_BOUNDARY_FIGURE",
]

TITLE = (
    "Resource-aware quantum amplitude estimation for chance-constrained pressure "
    "swing adsorption: classical baselines, compiled oracle costs, and a hardware boundary"
)

HIGHLIGHTS = [
    "PSA chance constraints are compared using MC, RQMC, IS, and noiseless MLAE.",
    "RQMC gives lower RMSE than MLAE for the frozen surrogate benchmark.",
    "A response oracle needs 99 logical qubits and 35,160 CX per call.",
    "Policy stream-to-event oracles preserve all candidate and ledger labels.",
    "Nine IBM jobs quantify backend and transpiler-seed hardware variability.",
]


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def add_box(ax, xy, width, height, face, edge, title, lines):
    x, y = xy
    box = FancyBboxPatch(
        (x, y),
        width,
        height,
        boxstyle="round,pad=0.018,rounding_size=0.025",
        linewidth=1.6,
        edgecolor=edge,
        facecolor=face,
    )
    ax.add_patch(box)
    ax.text(x + 0.03, y + height - 0.06, title, fontsize=13, fontweight="bold", color=edge, va="top")
    ax.text(x + 0.03, y + height - 0.14, "\n".join(lines), fontsize=10.2, color="#18212b", va="top", linespacing=1.5)


def make_graphical_abstract(payload: dict) -> None:
    fig, ax = plt.subplots(figsize=(14.4, 6.0))
    fig.patch.set_facecolor("white")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    ax.text(
        0.5,
        0.955,
        "Where quantum amplitude estimation meets a PSA decision",
        ha="center",
        va="top",
        fontsize=20,
        fontweight="bold",
        color="#102a43",
    )
    ax.text(
        0.5,
        0.895,
        "Matched estimands expose estimator performance, reversible-computing cost, and validation limits",
        ha="center",
        va="top",
        fontsize=11.5,
        color="#486581",
    )

    add_box(
        ax,
        (0.03, 0.29),
        0.265,
        0.49,
        "#eaf4fb",
        "#1677a5",
        "1  Frozen PSA decision",
        [
            "Recycle policies: 0.420 / 0.427 / 0.430",
            "Joint event: H2 purity + recovery",
            "Correlated process uncertainty",
            "Chance target: p >= 0.50",
        ],
    )
    add_box(
        ax,
        (0.365, 0.29),
        0.27,
        0.49,
        "#f2effb",
        "#6b4bb6",
        "2  Matched probability estimators",
        [
            "200 replications per method",
            "MC       RMSE 0.00679",
            "RQMC   RMSE 0.00248  | best",
            "IS         RMSE 0.01017",
            "MLAE   RMSE 0.00289  | ideal",
        ],
    )
    add_box(
        ax,
        (0.705, 0.29),
        0.265,
        0.49,
        "#fff4e6",
        "#b35c00",
        "3  Measured implementation boundary",
        [
            "Response oracle: 99 q / 35,160 CX",
            "Parameter-only CSS: 32/32 events",
            "5-component LDF modules: 675 q / 6.55 M CX",
            "Valve→boundary: 842 q / 2.35 M CX | tank: 677 q",
            "Gas→y→2 faces→cell: 1,651 q / 14.67 M CX",
            "Direct LDF→cell balance: 1,317 q / 19.08 M CX",
            "Policy stream→event: 510 q / 1.29 M CX",
            "Raw agg. CSS: 2/32 | physical: 68→85 cycles",
            "Out-of-place state/streams: 2,880 q",
            "Dense 7-bit loader: 2^63 amplitudes",
            f"IBM 3x3: mean {payload['evidence']['qpu_campaign_estimate_mean']:.5f} vs 0.625",
        ],
    )

    for start, end in [((0.298, 0.535), (0.36, 0.535)), ((0.638, 0.535), (0.70, 0.535))]:
        ax.add_patch(
            FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=18, linewidth=2.0, color="#627d98")
        )

    conclusion = (
        "Current result: no end-to-end quantum advantage\n"
        "State accumulation/full phase logic, structured loading, and H2 validation remain decisive"
    )
    ax.add_patch(
        FancyBboxPatch(
            (0.12, 0.055),
            0.76,
            0.15,
            boxstyle="round,pad=0.018,rounding_size=0.025",
            linewidth=1.8,
            edgecolor="#2f855a",
            facecolor="#e6fffa",
        )
    )
    ax.text(0.5, 0.13, conclusion, ha="center", va="center", fontsize=11.1, fontweight="bold", color="#22543d", linespacing=1.4)
    ax.text(0.98, 0.02, "Resource-aware PSA–QAE study", ha="right", va="bottom", fontsize=8.5, color="#829ab1")

    fig.savefig(OUT_PNG, dpi=300, bbox_inches="tight", facecolor="white")
    fig.savefig(OUT_PDF, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def main() -> None:
    manuscript_text = MANUSCRIPT.read_text(encoding="utf-8")
    manuscript_title = manuscript_text.splitlines()[0].removeprefix("# ").strip()
    if manuscript_title != TITLE:
        raise ValueError(f"Title mismatch: {manuscript_title!r}")
    abstract_match = re.search(r"## Abstract\s+(.*?)\s+## Keywords", manuscript_text, flags=re.S)
    keywords_match = re.search(r"## Keywords\s+(.*?)\s+## 1\. Introduction", manuscript_text, flags=re.S)
    abstract_words = len(abstract_match.group(1).split()) if abstract_match else 0
    keywords = [item.strip() for item in keywords_match.group(1).split(";")] if keywords_match else []
    if not 1 <= len(keywords) <= 7:
        raise ValueError(f"CCE keyword count must be 1--7; observed {len(keywords)}")
    if abstract_words > 250:
        raise ValueError(f"CCE abstract must not exceed 250 words; observed {abstract_words}")
    if any(len(item) > 85 for item in HIGHLIGHTS):
        raise ValueError({item: len(item) for item in HIGHLIGHTS if len(item) > 85})

    table2 = load(TABLE2)
    resources = load(RESOURCE_TABLE)
    prospective = load(PROSPECTIVE)
    qpu = load(QPU)
    qpu_campaign = load(QPU_CAMPAIGN)
    if qpu_campaign.get("status") != "complete_9_of_9":
        raise RuntimeError("editorial packaging requires the complete 9/9 QPU campaign")
    css_initializer = load(CSS_INITIALIZER)
    css_repeated = load(CSS_REPEATED)
    css_stability = load(CSS_STABILITY)
    css_compile = load(CSS_COMPILE)
    final_event = load(FINAL_EVENT)
    policy_stream_event = load(POLICY_STREAM_EVENT)
    physical_css = load(PHYSICAL_CSS)
    qstar_microkernel = load(QSTAR_MICROKERNEL)
    qstar_selected = qstar_microkernel["selected"]
    qstar_ldf_microstep = load(QSTAR_LDF_MICROSTEP)
    qstar_ldf_selected = qstar_ldf_microstep["selected"]
    qstar_ldf_resources = qstar_ldf_microstep["compiled_clean_microstep"]
    all_component_ldf = load(ALL_COMPONENT_LDF)
    all_component_ldf_sequential = all_component_ldf["sequential_five_component_accounting"]
    product_boundary = load(PRODUCT_BOUNDARY)
    product_boundary_balance = load(PRODUCT_BOUNDARY_BALANCE)
    product_ldf_valve_balance = load(PRODUCT_LDF_VALVE_BALANCE)
    normalized_product_ldf_valve_balance = load(
        NORMALIZED_PRODUCT_LDF_VALVE_BALANCE
    )
    coherent_run_schedule_tank = load(COHERENT_RUN_SCHEDULE_TANK)
    coherent_run_factor_ldf = load(COHERENT_RUN_FACTOR_LDF)
    coherent_coefficient_ldf_balance = load(COHERENT_COEFFICIENT_LDF_BALANCE)
    coherent_dynamic_langmuir_ldf_balance = load(COHERENT_DYNAMIC_LANGMUIR_LDF_BALANCE)
    coherent_normalized_dynamic_transport_ldf_balance = load(COHERENT_NORMALIZED_DYNAMIC_TRANSPORT_LDF_BALANCE)
    offledger_tank_saturation = load(OFFLEDGER_TANK_SATURATION)
    offledger_tank_proportional = load(OFFLEDGER_TANK_PROPORTIONAL)
    physical_unsaturated_tank = load(PHYSICAL_UNSATURATED_TANK)
    internal_transport = load(INTERNAL_TRANSPORT)
    internal_face_balance = load(INTERNAL_FACE_BALANCE)
    normalized_internal_face_balance = load(NORMALIZED_INTERNAL_FACE_BALANCE)
    cell_balance = load(CELL_BALANCE)
    loading_sign_balance = load(LOADING_SIGN_BALANCE)
    ldf_sign_balance = load(LDF_SIGN_BALANCE)
    joint_normalized_transport_ldf_balance = load(
        JOINT_NORMALIZED_TRANSPORT_LDF_BALANCE
    )
    estimators = {row["method"]: row for row in table2["rows"]}
    resource_rows = {row["tier"]: row for row in resources["rows"]}

    evidence = {
        "rqmc_rmse": float(estimators["scrambled Sobol RQMC"]["rmse"]),
        "mlae_rmse": float(estimators["noiseless MLAE"]["rmse"]),
        "response_oracle_logical_qubits": resource_rows["fixed-point response-event oracle"]["logical_qubits"],
        "response_oracle_cx_per_call": 35160,
        "response_oracle_schedule_cx": 52740000,
        "calibrated_phase_map_logical_qubits": resource_rows["calibrated one-cycle affine blocks"]["logical_qubits"],
        "calibrated_phase_map_forward_cx": 4183986,
        "primary_phase_event_matches": 32,
        "primary_phase_event_total": 32,
        "primary_phase_event_block_logical_qubits": resource_rows["primary phase-stream event blocks"]["logical_qubits"],
        "primary_phase_event_block_forward_cx": 1101233,
        "primary_phase_event_block_clean_cx": 2202466,
        "primary_final_event_logical_qubits": final_event["primitive_gate_compile"]["clean_phase_oracle"]["logical_qubits"],
        "primary_final_event_clean_cx": final_event["primitive_gate_compile"]["clean_phase_oracle"]["cx"],
        "primary_final_event_labels": final_event["verification"]["integer_event_matches"],
        "policy_stream_event_aggregate_bits": policy_stream_event["precision_screen"]["selected"]["aggregate_bits"],
        "policy_stream_event_candidate_labels": policy_stream_event["verification"]["candidate_integer_event_matches_vs_float"],
        "policy_stream_event_ledger_labels": policy_stream_event["verification"]["ledger_support_event_matches_vs_actual"],
        "policy_stream_event_logical_qubits": max(row["clean_phase_oracle"]["logical_qubits"] for row in policy_stream_event["primitive_gate_compile"]["policy_resources"]),
        "policy_stream_event_clean_cx": max(row["clean_phase_oracle"]["cx"] for row in policy_stream_event["primitive_gate_compile"]["policy_resources"]),
        "parameter_only_css_event_matches": css_initializer["summary"]["event_matches"],
        "parameter_only_css_recovery_mae": css_initializer["summary"]["recovery_mae"],
        "parameter_only_css_block_logical_qubits": css_compile["aggregate"]["max_logical_qubits_reusing_scalar_workspace"],
        "parameter_only_css_block_forward_cx": css_compile["aggregate"]["serial_forward_cx"],
        "parameter_only_css_block_clean_cx": css_compile["aggregate"]["serial_clean_compute_uncompute_cx"],
        "parameter_only_css_50cycle_terminal_matches": css_repeated["summary"]["terminal_event_matches"],
        "parameter_only_css_50cycle_gate_passes": css_repeated["summary"]["tail_css_gate_1e_4_count"],
        "parameter_only_css_raw_spectral_radius_range": [css_stability["summary"]["raw_spectral_radius_min"], css_stability["summary"]["raw_spectral_radius_max"]],
        "parameter_only_css_anchor_weight_range": [css_stability["summary"]["anchor_weight_min"], css_stability["summary"]["anchor_weight_max"]],
        "parameter_only_css_stabilized_terminal_matches": css_stability["summary"]["terminal_event_matches"],
        "parameter_only_css_stabilized_50cycle_gate_passes": css_stability["summary"]["tail_css_gate_1e_4_count"],
        "physical_css_joint_horizon": physical_css["physical_horizon"]["max_joint_strict_css_event_horizon"],
        "physical_css_fixed_point_bits": physical_css["fixed_point_screen"]["selected"]["bits_per_scalar"],
        "physical_css_safe_horizon": physical_css["fixed_point_screen"]["selected"]["safe_fixed_horizon"],
        "physical_single_state_data_qubits": physical_css["reversible_register_accounting"]["single_physical_state_data_qubits"],
        "physical_out_of_place_state_stream_data_qubits": physical_css["reversible_register_accounting"]["out_of_place_current_next_state_plus_raw_event_stream_data_qubits"],
        "qstar_microkernel_bits": qstar_selected["bits_per_pressure_and_composition"],
        "qstar_microkernel_logical_qubits": qstar_selected["logical_qubits"],
        "qstar_microkernel_forward_cx": qstar_selected["forward_cx"],
        "qstar_microkernel_clean_cx": qstar_selected["clean_compute_uncompute_cx"],
        "qstar_microkernel_denominator_p95_relative_error": qstar_selected["denominator_p95_relative_error"],
        "qstar_microkernel_qstar_p95_relative_error": qstar_selected["co2_qstar_p95_relative_error"],
        "qstar_ldf_address_bits": qstar_ldf_selected["denominator_address_bits"],
        "qstar_ldf_arithmetic_bits": qstar_ldf_selected["arithmetic_bits"],
        "qstar_ldf_qstar_p95_relative_error": qstar_ldf_selected["qstar_p95_relative_error"],
        "qstar_ldf_next_p95_relative_error": qstar_ldf_selected["ldf_next_p95_relative_error"],
        "qstar_ldf_logical_qubits": qstar_ldf_resources["logical_qubits"],
        "qstar_ldf_cx": qstar_ldf_resources["cx"],
        "qstar_ldf_depth": qstar_ldf_resources["depth_all_to_all"],
        "all_component_ldf_logical_qubits": all_component_ldf_sequential["logical_qubits"],
        "all_component_ldf_additive_cx": all_component_ldf_sequential["cx_additive_module_bound"],
        "product_valve_address_bits": product_boundary["selected_valve"]["valve_address_bits"],
        "product_valve_flow_bits": product_boundary["selected_valve"]["flow_bits"],
        "product_valve_logical_qubits": product_boundary["compiled_clean_valve_component_flux"]["logical_qubits"],
        "product_valve_cx": product_boundary["compiled_clean_valve_component_flux"]["cx"],
        "product_tank_amount_bits": product_boundary["selected_tank"]["amount_bits"],
        "product_tank_fraction_bits": product_boundary["selected_tank"]["fraction_bits"],
        "product_tank_logical_qubits": product_boundary["five_component_tank_accounting"]["logical_qubits"],
        "product_tank_additive_cx": product_boundary["five_component_tank_accounting"]["cx_additive_module_bound"],
        "product_tank_minimum_capacity_headroom_mol": product_boundary["selected_tank"]["minimum_capacity_headroom_mol"],
        "product_boundary_balance_logical_qubits": product_boundary_balance["compiled_clean_product_valve_boundary_balance"]["logical_qubits"],
        "product_boundary_balance_cx": product_boundary_balance["compiled_clean_product_valve_boundary_balance"]["cx"],
        "product_boundary_balance_depth": product_boundary_balance["compiled_clean_product_valve_boundary_balance"]["depth_all_to_all"],
        "product_boundary_balance_states": product_boundary_balance["physical_state_source"]["product_boundary_states"],
        "product_boundary_balance_component_balances": product_boundary_balance["physical_state_source"]["component_balances"],
        "product_ldf_valve_component_qubit_range": [min(row["logical_qubits"] for row in product_ldf_valve_balance["componentwise_compiled_direct_paths"]), max(row["logical_qubits"] for row in product_ldf_valve_balance["componentwise_compiled_direct_paths"])],
        "product_ldf_valve_component_cx_range": [min(row["cx"] for row in product_ldf_valve_balance["componentwise_compiled_direct_paths"]), max(row["cx"] for row in product_ldf_valve_balance["componentwise_compiled_direct_paths"])],
        "product_ldf_valve_peak_logical_qubits": product_ldf_valve_balance["conservative_five_component_upper_bound"]["logical_qubits_peak"],
        "product_ldf_valve_additive_cx_upper_bound": product_ldf_valve_balance["conservative_five_component_upper_bound"]["cx_additive_upper_bound"],
        "normalized_product_component_qubit_range": [min(row["logical_qubits"] for row in normalized_product_ldf_valve_balance["componentwise_compiled_direct_paths"]), max(row["logical_qubits"] for row in normalized_product_ldf_valve_balance["componentwise_compiled_direct_paths"])],
        "normalized_product_component_depth_range": [min(row["depth_all_to_all"] for row in normalized_product_ldf_valve_balance["componentwise_compiled_direct_paths"]), max(row["depth_all_to_all"] for row in normalized_product_ldf_valve_balance["componentwise_compiled_direct_paths"])],
        "normalized_product_component_cx_range": [min(row["cx"] for row in normalized_product_ldf_valve_balance["componentwise_compiled_direct_paths"]), max(row["cx"] for row in normalized_product_ldf_valve_balance["componentwise_compiled_direct_paths"])],
        "normalized_product_peak_logical_qubits": normalized_product_ldf_valve_balance["conservative_five_component_upper_bound"]["logical_qubits_peak"],
        "normalized_product_additive_depth_upper_bound": normalized_product_ldf_valve_balance["conservative_five_component_upper_bound"]["depth_all_to_all_additive_upper_bound"],
        "normalized_product_additive_cx_upper_bound": normalized_product_ldf_valve_balance["conservative_five_component_upper_bound"]["cx_additive_upper_bound"],
        "normalized_product_next_p95_range": [min(row["next_p95_scale_normalized_absolute_error"] for row in normalized_product_ldf_valve_balance["selected_components"]), max(row["next_p95_scale_normalized_absolute_error"] for row in normalized_product_ldf_valve_balance["selected_components"])],
        "normalized_product_next_max_error": max(row["next_max_scale_normalized_absolute_error"] for row in normalized_product_ldf_valve_balance["selected_components"]),
        "coherent_interface_logical_qubits": coherent_run_schedule_tank["integrated_interface"]["logical_qubits"],
        "coherent_interface_depth": coherent_run_schedule_tank["integrated_interface"]["depth_all_to_all"],
        "coherent_interface_cx": coherent_run_schedule_tank["integrated_interface"]["cx"],
        "coherent_interface_parameter_checks": coherent_run_schedule_tank["parameter_encoding"]["basis_table_values_checked"],
        "coherent_interface_schedule_checks": coherent_run_schedule_tank["schedule_encoding"]["basis_addresses_checked"],
        "coherent_interface_tank_checks": coherent_run_schedule_tank["tank_encoding"]["basis_component_records_checked"],
        "coherent_interface_parameter_p95": coherent_run_schedule_tank["parameter_encoding"]["aggregate"]["p95_span_normalized_absolute_error"],
        "coherent_interface_tank_p95": coherent_run_schedule_tank["tank_encoding"]["selected"]["p95_scale_normalized_absolute_error"],
        "coherent_factor_ldf_logical_qubits": coherent_run_factor_ldf["compiled_interface"]["logical_qubits"],
        "coherent_factor_ldf_depth": coherent_run_factor_ldf["compiled_interface"]["depth_all_to_all"],
        "coherent_factor_ldf_cx": coherent_run_factor_ldf["compiled_interface"]["cx"],
        "coherent_factor_ldf_coefficient_records": coherent_run_factor_ldf["support"]["coefficient_records_checked"],
        "coherent_factor_ldf_schedule_flags": coherent_run_factor_ldf["support"]["schedule_flags_checked"],
        "coherent_factor_ldf_equilibrium_p95": coherent_run_factor_ldf["precision"]["five_component_equilibrium_prefactor_p95_relative_error"],
        "coherent_factor_ldf_equilibrium_max": coherent_run_factor_ldf["precision"]["five_component_equilibrium_prefactor_max_relative_error"],
        "coherent_factor_ldf_alpha_p95": coherent_run_factor_ldf["precision"]["five_component_ldf_alpha_p95_relative_error"],
        "coherent_factor_ldf_alpha_max": coherent_run_factor_ldf["precision"]["five_component_ldf_alpha_max_relative_error"],
        "coherent_coefficient_consumer_component_qubit_range": [min(row["logical_qubits"] for row in coherent_coefficient_ldf_balance["componentwise_compiled_direct_paths"]), max(row["logical_qubits"] for row in coherent_coefficient_ldf_balance["componentwise_compiled_direct_paths"])],
        "coherent_coefficient_consumer_component_cx_range": [min(row["cx"] for row in coherent_coefficient_ldf_balance["componentwise_compiled_direct_paths"]), max(row["cx"] for row in coherent_coefficient_ldf_balance["componentwise_compiled_direct_paths"])],
        "coherent_coefficient_consumer_peak_logical_qubits": coherent_coefficient_ldf_balance["conservative_five_component_upper_bound"]["logical_qubits_peak"],
        "coherent_coefficient_consumer_additive_depth_upper_bound": coherent_coefficient_ldf_balance["conservative_five_component_upper_bound"]["depth_all_to_all_additive_upper_bound"],
        "coherent_coefficient_consumer_additive_cx_upper_bound": coherent_coefficient_ldf_balance["conservative_five_component_upper_bound"]["cx_additive_upper_bound"],
        "coherent_coefficient_consumer_component_balance_records": coherent_coefficient_ldf_balance["support"]["component_balance_records_checked"],
        "coherent_coefficient_consumer_qstar_max_error": max(row["qstar_max_loading_scale_normalized_absolute_error"] for row in coherent_coefficient_ldf_balance["components"]),
        "coherent_coefficient_consumer_ldf_next_max_error": max(row["ldf_next_max_loading_scale_normalized_absolute_error"] for row in coherent_coefficient_ldf_balance["components"]),
        "coherent_coefficient_consumer_next_gas_max_error": max(row["next_gas_max_scale_normalized_absolute_error"] for row in coherent_coefficient_ldf_balance["components"]),
        "coherent_coefficient_consumer_max_transfer_erasure_fraction": max(row["nonzero_quantized_transfer_erased_fraction"] for row in coherent_coefficient_ldf_balance["components"]),
        "coherent_dynamic_langmuir_affinity_bits": coherent_dynamic_langmuir_ldf_balance["selected_dynamic_response_design"]["affinity_bits"],
        "coherent_dynamic_langmuir_address_bits": coherent_dynamic_langmuir_ldf_balance["selected_dynamic_response_design"]["denominator_address_bits"],
        "coherent_dynamic_langmuir_reciprocal_segments": coherent_dynamic_langmuir_ldf_balance["selected_dynamic_response_design"]["reciprocal_segments"],
        "coherent_dynamic_langmuir_denominator_p95_error": coherent_dynamic_langmuir_ldf_balance["selected_dynamic_response_design"]["denominator_p95_absolute_error"],
        "coherent_dynamic_langmuir_denominator_max_error": coherent_dynamic_langmuir_ldf_balance["selected_dynamic_response_design"]["denominator_max_absolute_error"],
        "coherent_dynamic_langmuir_component_qubit_range": [min(row["logical_qubits"] for row in coherent_dynamic_langmuir_ldf_balance["componentwise_compiled_direct_paths"]), max(row["logical_qubits"] for row in coherent_dynamic_langmuir_ldf_balance["componentwise_compiled_direct_paths"])],
        "coherent_dynamic_langmuir_component_cx_range": [min(row["cx"] for row in coherent_dynamic_langmuir_ldf_balance["componentwise_compiled_direct_paths"]), max(row["cx"] for row in coherent_dynamic_langmuir_ldf_balance["componentwise_compiled_direct_paths"])],
        "coherent_dynamic_langmuir_peak_logical_qubits": coherent_dynamic_langmuir_ldf_balance["conservative_five_component_upper_bound"]["logical_qubits_peak"],
        "coherent_dynamic_langmuir_additive_depth_upper_bound": coherent_dynamic_langmuir_ldf_balance["conservative_five_component_upper_bound"]["depth_all_to_all_additive_upper_bound"],
        "coherent_dynamic_langmuir_additive_cx_upper_bound": coherent_dynamic_langmuir_ldf_balance["conservative_five_component_upper_bound"]["cx_additive_upper_bound"],
        "coherent_dynamic_langmuir_component_balance_records": coherent_dynamic_langmuir_ldf_balance["support"]["component_balance_records_checked"],
        "coherent_dynamic_langmuir_qstar_max_error": max(row["qstar_max_loading_scale_normalized_absolute_error"] for row in coherent_dynamic_langmuir_ldf_balance["components"]),
        "coherent_dynamic_langmuir_ldf_next_max_error": max(row["ldf_next_max_loading_scale_normalized_absolute_error"] for row in coherent_dynamic_langmuir_ldf_balance["components"]),
        "coherent_dynamic_langmuir_next_gas_max_error": max(row["next_gas_max_scale_normalized_absolute_error"] for row in coherent_dynamic_langmuir_ldf_balance["components"]),
        "coherent_normalized_dynamic_normalization_states": coherent_normalized_dynamic_transport_ldf_balance["support"]["normalization_states"],
        "coherent_normalized_dynamic_component_balance_records": coherent_normalized_dynamic_transport_ldf_balance["support"]["component_balance_records_checked"],
        "coherent_normalized_dynamic_component_qubit_range": [min(row["logical_qubits"] for row in coherent_normalized_dynamic_transport_ldf_balance["componentwise_compiled_direct_paths"]), max(row["logical_qubits"] for row in coherent_normalized_dynamic_transport_ldf_balance["componentwise_compiled_direct_paths"])],
        "coherent_normalized_dynamic_component_cx_range": [min(row["cx"] for row in coherent_normalized_dynamic_transport_ldf_balance["componentwise_compiled_direct_paths"]), max(row["cx"] for row in coherent_normalized_dynamic_transport_ldf_balance["componentwise_compiled_direct_paths"])],
        "coherent_normalized_dynamic_peak_logical_qubits": coherent_normalized_dynamic_transport_ldf_balance["conservative_five_component_upper_bound"]["logical_qubits_peak"],
        "coherent_normalized_dynamic_additive_depth_upper_bound": coherent_normalized_dynamic_transport_ldf_balance["conservative_five_component_upper_bound"]["depth_all_to_all_additive_upper_bound"],
        "coherent_normalized_dynamic_additive_cx_upper_bound": coherent_normalized_dynamic_transport_ldf_balance["conservative_five_component_upper_bound"]["cx_additive_upper_bound"],
        "coherent_normalized_dynamic_next_gas_max_error": max(row["next_gas_max_scale_normalized_absolute_error"] for row in coherent_normalized_dynamic_transport_ldf_balance["components"]),
        "offledger_tank_records": offledger_tank_saturation["support"]["records"],
        "offledger_tank_common_bits": offledger_tank_saturation["selected_design"]["common_bits"],
        "offledger_tank_saturation_labels": offledger_tank_saturation["selected_design"]["encoded_saturated_records"],
        "offledger_tank_minimum_margin_mol": offledger_tank_saturation["selected_design"]["minimum_lower_bound_minus_tank_mol"],
        "offledger_tank_p95_error": offledger_tank_saturation["selected_design"]["all_output_p95_scale_normalized_absolute_error"],
        "offledger_tank_logical_qubits": offledger_tank_saturation["compiled_clean_circuit"]["logical_qubits"],
        "offledger_tank_depth": offledger_tank_saturation["compiled_clean_circuit"]["depth_all_to_all"],
        "offledger_tank_cx": offledger_tank_saturation["compiled_clean_circuit"]["cx"],
        "offledger_proportional_observed_saturated": offledger_tank_proportional["support"]["observed_saturated_records"],
        "offledger_proportional_counterfactual_unsaturated": offledger_tank_proportional["support"]["counterfactual_unsaturated_records"],
        "offledger_proportional_common_bits": offledger_tank_proportional["selected_design"]["common_bits"],
        "offledger_proportional_address_bits": offledger_tank_proportional["selected_design"]["address_bits"],
        "offledger_proportional_reciprocal_bits": offledger_tank_proportional["selected_design"]["reciprocal_bits"],
        "offledger_proportional_p95_error": offledger_tank_proportional["selected_design"]["withdrawal_and_next_p95_component_scale_normalized_absolute_error"],
        "offledger_proportional_max_error": offledger_tank_proportional["selected_design"]["withdrawal_and_next_max_component_scale_normalized_absolute_error"],
        "offledger_proportional_logical_qubits": offledger_tank_proportional["compiled_clean_circuit"]["logical_qubits"],
        "offledger_proportional_depth": offledger_tank_proportional["compiled_clean_circuit"]["depth_all_to_all"],
        "offledger_proportional_cx": offledger_tank_proportional["compiled_clean_circuit"]["cx"],
        "physical_unsaturated_calls": physical_unsaturated_tank["trajectory"]["unsaturated_calls"],
        "physical_unsaturated_zero_makeup_calls": physical_unsaturated_tank["trajectory"]["zero_makeup_calls"],
        "physical_unsaturated_css": physical_unsaturated_tank["trajectory"]["final_css_residual_max"],
        "physical_unsaturated_schedule_s": physical_unsaturated_tank["trajectory"]["non_adsorption_duration_s"],
        "physical_unsaturated_trapezoid_p95_relative_error": physical_unsaturated_tank["pressure_demand_diagnostics"]["trapezoid_proxy_p95_relative_error"],
        "physical_unsaturated_withdrawal_p95_error": physical_unsaturated_tank["selected_design"]["withdrawal_and_next_p95_component_scale_normalized_absolute_error"],
        "physical_unsaturated_logical_qubits": physical_unsaturated_tank["compiled_clean_circuit"]["logical_qubits"],
        "physical_unsaturated_depth": physical_unsaturated_tank["compiled_clean_circuit"]["depth_all_to_all"],
        "physical_unsaturated_cx": physical_unsaturated_tank["compiled_clean_circuit"]["cx"],
        "pressure_reconstruction_logical_qubits": internal_transport["compiled_clean_pressure_reconstruction"]["logical_qubits"],
        "pressure_reconstruction_cx": internal_transport["compiled_clean_pressure_reconstruction"]["cx"],
        "internal_face_logical_qubits": internal_transport["compiled_clean_oriented_internal_face_transport"]["logical_qubits"],
        "internal_face_cx": internal_transport["compiled_clean_oriented_internal_face_transport"]["cx"],
        "pressure_face_modular_logical_qubits": internal_transport["pressure_to_face_modular_accounting"]["logical_qubits"],
        "pressure_face_modular_additive_cx": internal_transport["pressure_to_face_modular_accounting"]["cx_additive_module_bound"],
        "internal_face_balance_logical_qubits": internal_face_balance["compiled_clean_internal_face_balance"]["logical_qubits"],
        "internal_face_balance_cx": internal_face_balance["compiled_clean_internal_face_balance"]["cx"],
        "internal_face_balance_depth": internal_face_balance["compiled_clean_internal_face_balance"]["depth_all_to_all"],
        "internal_face_balance_states": internal_face_balance["physical_state_source"]["interior_cell_states"],
        "internal_face_balance_component_balances": internal_face_balance["physical_state_source"]["component_balances"],
        "normalized_internal_face_balance_logical_qubits": normalized_internal_face_balance["compiled_clean_normalized_internal_face_balance"]["logical_qubits"],
        "normalized_internal_face_balance_cx": normalized_internal_face_balance["compiled_clean_normalized_internal_face_balance"]["cx"],
        "normalized_internal_face_balance_depth": normalized_internal_face_balance["compiled_clean_normalized_internal_face_balance"]["depth_all_to_all"],
        "composition_normalizer_logical_qubits": normalized_internal_face_balance["compiled_clean_composition_normalizer"]["logical_qubits"],
        "composition_normalizer_cx": normalized_internal_face_balance["compiled_clean_composition_normalizer"]["cx"],
        "composition_normalization_states": normalized_internal_face_balance["physical_state_source"]["normalization_cell_states"],
        "composition_normalization_address_bits": normalized_internal_face_balance["selected_normalization"]["address_bits"],
        "composition_normalization_p95_absolute_error_max": max(normalized_internal_face_balance["selected_normalization"]["composition_p95_absolute_error"].values()),
        "cell_balance_logical_qubits": cell_balance["sequential_five_component_accounting"]["logical_qubits"],
        "cell_balance_additive_cx": cell_balance["sequential_five_component_accounting"]["cx_additive_module_bound"],
        "cell_balance_samples": cell_balance["physical_state_source"]["component_balance_samples"],
        "loading_sign_balance_logical_qubits": loading_sign_balance["sequential_five_component_accounting"]["logical_qubits"],
        "loading_sign_balance_additive_cx": loading_sign_balance["sequential_five_component_accounting"]["cx_additive_module_bound"],
        "loading_sign_balance_selected_bits": [row["selected"]["loading_bits"] for row in loading_sign_balance["components"]],
        "loading_sign_balance_structural_pairs": loading_sign_balance["small_width_structural_check"]["basis_pairs"],
        "ldf_sign_balance_logical_qubits": ldf_sign_balance["sequential_five_component_accounting"]["logical_qubits"],
        "ldf_sign_balance_additive_cx": ldf_sign_balance["sequential_five_component_accounting"]["cx_additive_module_bound"],
        "ldf_sign_balance_component_qubit_range": [min(row["compiled_clean_ldf_sign_cell_balance"]["logical_qubits"] for row in ldf_sign_balance["components"]), max(row["compiled_clean_ldf_sign_cell_balance"]["logical_qubits"] for row in ldf_sign_balance["components"])],
        "ldf_sign_balance_component_cx_range": [min(row["compiled_clean_ldf_sign_cell_balance"]["cx"] for row in ldf_sign_balance["components"]), max(row["compiled_clean_ldf_sign_cell_balance"]["cx"] for row in ldf_sign_balance["components"])],
        "joint_transport_ldf_component_qubit_range": [min(row["logical_qubits"] for row in joint_normalized_transport_ldf_balance["componentwise_compiled_direct_paths"]), max(row["logical_qubits"] for row in joint_normalized_transport_ldf_balance["componentwise_compiled_direct_paths"])],
        "joint_transport_ldf_component_cx_range": [min(row["cx"] for row in joint_normalized_transport_ldf_balance["componentwise_compiled_direct_paths"]), max(row["cx"] for row in joint_normalized_transport_ldf_balance["componentwise_compiled_direct_paths"])],
        "joint_transport_ldf_peak_logical_qubits": joint_normalized_transport_ldf_balance["compiled_clean_joint_specialized_circuit"]["logical_qubits_peak"],
        "joint_transport_ldf_additive_cx_upper_bound": joint_normalized_transport_ldf_balance["compiled_clean_joint_specialized_circuit"]["cx_additive_upper_bound"],
        "dense_loader_amplitudes": "2^63",
        "qpu_backend": qpu["backend"],
        "qpu_exact_probability": qpu["exact_probability"],
        "qpu_estimate": qpu["estimate"]["estimate"],
        "qpu_absolute_error": qpu["estimate"]["absolute_error"],
        "qpu_campaign_jobs": qpu_campaign["summary"]["completed_cells"],
        "qpu_campaign_estimate_mean": qpu_campaign["summary"]["estimate_mean"],
        "qpu_campaign_mean_absolute_error": qpu_campaign["summary"]["mean_absolute_error"],
        "qpu_campaign_between_job_sd": qpu_campaign["summary"]["between_job_sd"],
        "qpu_campaign_total_charge_seconds": qpu_campaign["summary"]["total_qpu_charge_seconds_recorded"],
        "qpu_campaign_crossed_bootstrap": qpu_campaign["summary"]["crossed_design_bootstrap"],
        "same_control_h2_validation": False,
        "max_h2_recovery_rmse_full_support_pct_point": prospective["independent_h2_resolution_design"]["max_recovery_rmse_for_full_support_to_pass_5x_pct_point"],
        "max_h2_recovery_rmse_primary_span_pct_point": prospective["independent_h2_resolution_design"]["max_recovery_rmse_for_primary_0p010_span_to_pass_5x_pct_point"],
    }
    payload = {
        "schema": "psa-qae-cce-editorial-package/v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "editorial_materials_complete_scientific_submission_gates_open",
        "target_journal": "Computers & Chemical Engineering",
        "title": TITLE,
        "highlights": HIGHLIGHTS,
        "highlight_character_counts": [len(item) for item in HIGHLIGHTS],
        "evidence": evidence,
        "claim_boundary": {
            "supported": "resource-aware comparison and measured implementation boundary for a frozen surrogate-conditioned PSA chance constraint",
            "unsupported": "end-to-end quantum advantage, plant-validated H2 policy selection, or industrial deployment readiness",
        },
        "submission_ready": False,
        "qpu_submission": False,
        "scientific_priority": [
            "same-control H2 product-recycle campaign with synchronized policy, pressure, flow, continuous composition, and product/recycle split",
            "generate a physically integrated unsaturated tank trajectory inside a complete five-component adsorption phase and quantify adaptive integration workspace",
        ],
        "outputs": [OUT_MD.name, OUT_COVER.name, OUT_HIGHLIGHTS.name, OUT_CHECKLIST.name, OUT_PNG.name, OUT_PDF.name],
    }
    make_graphical_abstract(payload)
    graphical_abstract_pixels = Image.open(OUT_PNG).size
    if graphical_abstract_pixels[0] < 1328 or graphical_abstract_pixels[1] < 531:
        raise ValueError(f"Graphical abstract below CCE minimum: {graphical_abstract_pixels}")
    vector_figure_pdfs = [RESULTS / f"{base}.pdf" for base in MAIN_FIGURE_BASES]
    missing_vector_figures = [path.name for path in vector_figure_pdfs if not path.exists()]
    if missing_vector_figures:
        raise FileNotFoundError(f"Missing vector main figures: {missing_vector_figures}")
    payload["submission_format_checks"] = {
        "abstract_words": abstract_words,
        "abstract_limit": 250,
        "keyword_count": len(keywords),
        "keyword_limit": [1, 7],
        "highlight_count": len(HIGHLIGHTS),
        "highlight_character_counts": [len(item) for item in HIGHLIGHTS],
        "highlight_limit_each": 85,
        "graphical_abstract_pixels": list(graphical_abstract_pixels),
        "graphical_abstract_minimum_pixels": [1328, 531],
        "main_figure_vector_pdf_count": len(vector_figure_pdfs),
        "main_table3_rows": 8,
        "supplementary_table_s1_rows": 31,
        "main_table4_rows": 8,
        "supplementary_table_s2_rows": 32,
        "word_rendered_pages": {
            "manuscript": 30,
            "title_page": 1,
            "supplementary_information": 7,
        },
        "reference_style": "author-year citations; alphabetized reference list in submission DOCX",
    }
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OUT_HIGHLIGHTS.write_text("\n".join(f"• {item}" for item in HIGHLIGHTS) + "\n", encoding="utf-8")

    editorial = f"""# CCE editorial package

Target journal: **Computers & Chemical Engineering**

## Final working title

{TITLE}

## One-sentence editorial pitch

This study tests quantum amplitude estimation against strong classical estimators on the same frozen PSA chance constraint, compiles the process-facing quantum costs, and identifies the empirical conditions that must change before an end-to-end advantage claim becomes credible.

## Why the paper fits CCE

- The research question is a chemical-process decision problem: chance-constrained PSA policy screening under correlated uncertainty.
- The comparison is decision-consistent: MC, scrambled Sobol RQMC, defensive-mixture IS, and noiseless MLAE estimate the same event under frozen budgets.
- The paper reports executable resource accounting rather than asymptotic query complexity alone.
- Negative results are operational: RQMC wins the current benchmark, and loader/process-oracle costs define where the quantum route fails.
- Independent H2 and public-simulator controls are separated by evidence tier and are not pooled as plant validation.

## Main evidence for the editor

- RQMC RMSE is **{evidence['rqmc_rmse']:.6f}**, below noiseless MLAE at **{evidence['mlae_rmse']:.6f}**.
- The fixed-point response oracle requires **99 logical qubits** and **35,160 CX per phase call**; the frozen schedule alone reaches **52.74 million CX**, excluding the correlated loader.
- The calibrated one-cycle affine blocks require up to **186 logical qubits** and **4,183,986 forward CX** before reversible equalization, repeated CSS, event logic, and routing.
- The primary final-cycle phase ledger replays every frozen process event, and nested held-out phase-stream maps recover **32/32 event labels** when conditioned on observed phase-start states. A modular 16-bit final event block retains **32/32 labels** at **125 logical qubits** and **182,981 clean CX**. The integrated policy-specific construction collapses both adsorption maps into 19-bit aggregate registers, applies recycle scaling, marks the joint event, and uncomputes exactly; it retains **96/96 candidate-policy** and **32/32 ledger-support labels** and reaches **510 logical qubits** and **1,286,021 clean CX**.
- A stricter parameter-only CSS initializer supplies no held dynamic state and retains **32/32 one-cycle labels** with recovery MAE **3.22e-4**. Its 20 affine blocks require **118 logical qubits**, **578,702 forward CX**, and **1,157,404 clean CX**. Unanchored 50-cycle repetition retains 28/32 terminal labels and only 2/32 CSS passes. Exact fitted Jacobians have spectral radii 1.040–1.254; a label-free radius-0.9 anchor restores 32/32 aggregate CSS passes, but this explicit model correction does not establish physical CSS.
- Direct 100-cycle reruns of all 32 tank/spatial cases give a latest joint physical horizon of **68 cycles**. A 16-bit screen gives a conservative **85-cycle** target. One state uses **1,360 data qubits**; a clean out-of-place current/next layout with ten raw event streams uses **2,880** before nonlinear transport workspace. This is architecture-specific accounting, not a universal lower bound.
- The physical competitive-Langmuir path is extended through clean one-second LDF updates for **H2, CO2, CH4, CO, and N2** over **25,856 cell states**. The component circuits compile individually to 490–515 logical qubits and 1,118,920–1,965,308 CX. Sequential workspace-reuse accounting with all current/next loadings retained requires **675 logical qubits** and **6,547,362 additive CX**.
- A clean product-end valve module maps encoded pressure and five compositions to component fluxes at **288 logical qubits** and **800,762 CX**. Separate fixed-0.420 product split, tank-candidate, and capacity modules give a five-component accounting point of **677 logical qubits** and **1,043,990 additive CX**, with **97.40 mol** minimum capacity headroom.
- The valve output is now consumed directly by five conservative product-cell balances and then uncomputed. The single clean circuit covers **6,464 product-end states** and **32,320 component balances**, using **842 logical qubits**, depth **3,285,605**, and **2,348,388 CX**; all declared inventory error, erasure, overflow, and underflow gates pass.
- The product-cell follow-on removes supplied adsorption/desorption inputs. The same 20-bit pressure/composition registers drive factor-specialized LDF uptake and, through their high 18 bits, the valve. The five component paths use **1,072–1,195 logical qubits** and **10,060,060–26,810,396 CX**; the conservative repeated-common-path upper bound is **1,195 peak qubits/88,388,552 additive CX**. All 32,320 balance checks pass without transfer erasure, underflow, or overflow.
- The extended product-cell path also removes the supplied composition and inward-face inputs. Two five-component gas inventories generate both normalized compositions, both pressures, one inward face, LDF transfer, valve withdrawal, and one conservative next-gas balance before exact uncomputation. The factor-specialized component paths use **{evidence['normalized_product_component_qubit_range'][0]:,}–{evidence['normalized_product_component_qubit_range'][1]:,} logical qubits**, depths **{evidence['normalized_product_component_depth_range'][0]:,}–{evidence['normalized_product_component_depth_range'][1]:,}**, and **{evidence['normalized_product_component_cx_range'][0]:,}–{evidence['normalized_product_component_cx_range'][1]:,} CX**; the conservative upper bound is **{evidence['normalized_product_peak_logical_qubits']:,} peak qubits/{evidence['normalized_product_additive_cx_upper_bound']:,} additive CX**. All 32,320 checks pass, with p95 next-gas errors **{evidence['normalized_product_next_p95_range'][0]:.3e}–{evidence['normalized_product_next_p95_range'][1]:.3e}** and maximum error no larger than **{evidence['normalized_product_next_max_error']:.3e}**.
- A finite-support controller now loads the 32 run-specific parameter words, decodes all six paired-bed valve stages, and performs the recorded five-component tank withdrawals. The integrated circuit checks **{evidence['coherent_interface_parameter_checks']} parameter values**, **{evidence['coherent_interface_schedule_checks']} schedule addresses**, and **{evidence['coherent_interface_tank_checks']} tank records** and uses **{evidence['coherent_interface_logical_qubits']} logical qubits**, depth **{evidence['coherent_interface_depth']:,}**, and **{evidence['coherent_interface_cx']:,} CX**. Parameter and tank p95 normalized errors are **{evidence['coherent_interface_parameter_p95']:.3e}** and **{evidence['coherent_interface_tank_p95']:.3e}**, with zero meaningful tank erasure, underflow, or next-state mismatch.
- The run-loaded capacity, affinity, and LDF factors are now consumed by reversible arithmetic that emits five component equilibrium prefactors, five component LDF-alpha coefficients, and paired-bed adsorption flags. The circuit verifies **{evidence['coherent_factor_ldf_coefficient_records']} coefficient records** and **{evidence['coherent_factor_ldf_schedule_flags']} schedule flags** at **{evidence['coherent_factor_ldf_logical_qubits']} logical qubits**, depth **{evidence['coherent_factor_ldf_depth']:,}**, and **{evidence['coherent_factor_ldf_cx']:,} CX**. Equilibrium-prefactor and LDF-alpha p95/max relative errors are **{evidence['coherent_factor_ldf_equilibrium_p95']:.3e}/{evidence['coherent_factor_ldf_equilibrium_max']:.3e}** and **{evidence['coherent_factor_ldf_alpha_p95']:.3e}/{evidence['coherent_factor_ldf_alpha_max']:.3e}**.
- Those generated coefficients are consumed directly in five separately compiled, schedule-gated q*/LDF/loading-sign/gas-balance paths using a supplied 20-bit competitive-Langmuir response. Across **{evidence['coherent_coefficient_consumer_component_balance_records']:,} component balances**, maximum q*, LDF-next, and next-gas scale-normalized errors are **{evidence['coherent_coefficient_consumer_qstar_max_error']:.3e}**, **{evidence['coherent_coefficient_consumer_ldf_next_max_error']:.3e}**, and **{evidence['coherent_coefficient_consumer_next_gas_max_error']:.3e}**, with zero quantized-transfer erasure. The paths use **{evidence['coherent_coefficient_consumer_component_qubit_range'][0]:,}–{evidence['coherent_coefficient_consumer_component_qubit_range'][1]:,} logical qubits** and **{evidence['coherent_coefficient_consumer_component_cx_range'][0]:,}–{evidence['coherent_coefficient_consumer_component_cx_range'][1]:,} CX**.
- A controller-coupled intermediate tier constructs the run-affinity-dependent Langmuir denominator and reciprocal from supplied 20-bit pressure and five 20-bit compositions, generates the response, and consumes it in the same q*/LDF/loading/balance path. The selected **{evidence['coherent_dynamic_langmuir_affinity_bits']}-bit affinity/{evidence['coherent_dynamic_langmuir_address_bits']}-bit address** design uses **{evidence['coherent_dynamic_langmuir_reciprocal_segments']:,} reciprocal segments**; denominator p95/max errors are **{evidence['coherent_dynamic_langmuir_denominator_p95_error']:.3e}/{evidence['coherent_dynamic_langmuir_denominator_max_error']:.3e}**. Five directly transpiled paths use **{evidence['coherent_dynamic_langmuir_component_qubit_range'][0]:,}–{evidence['coherent_dynamic_langmuir_component_qubit_range'][1]:,} qubits** and **{evidence['coherent_dynamic_langmuir_component_cx_range'][0]:,}–{evidence['coherent_dynamic_langmuir_component_cx_range'][1]:,} CX**.
- The highest component tier removes those supplied pressure, composition, and face-flux words. Three raw five-component gas inventories generate two normalized compositions, three pressures, and two oriented faces before direct controller-coupled dynamic-Langmuir/q*/LDF/loading/balance consumption. Across **{evidence['coherent_normalized_dynamic_normalization_states']:,} normalization states** and **{evidence['coherent_normalized_dynamic_component_balance_records']:,} component balances**, the five paths use **{evidence['coherent_normalized_dynamic_component_qubit_range'][0]:,}–{evidence['coherent_normalized_dynamic_component_qubit_range'][1]:,} qubits** and **{evidence['coherent_normalized_dynamic_component_cx_range'][0]:,}–{evidence['coherent_normalized_dynamic_component_cx_range'][1]:,} CX**. The repeated-path upper bound is **{evidence['coherent_normalized_dynamic_peak_logical_qubits']:,} peak qubits/{evidence['coherent_normalized_dynamic_additive_cx_upper_bound']:,} additive CX**, and maximum next-gas error is **{evidence['coherent_normalized_dynamic_next_gas_max_error']:.3e}**.
- The tank follow-on first replaces the recorded-withdrawal QROM on all **{evidence['offledger_tank_records']}** frozen calls. Raw endpoint gas generates pressure and a demand lower bound, which is compared with five-component tank inventory before saturated withdrawal and exact uncomputation. That **{evidence['offledger_tank_logical_qubits']}-qubit** circuit retains **{evidence['offledger_tank_saturation_labels']}/128** observed saturation labels. A second clean circuit adds support-adaptive reciprocal lookup and reversible multiplication to select either full-tank withdrawal or proportional unsaturated allocation. Its **{evidence['offledger_proportional_common_bits']}-bit common/{evidence['offledger_proportional_address_bits']}-bit address/{evidence['offledger_proportional_reciprocal_bits']}-bit reciprocal** design preserves **{evidence['offledger_proportional_observed_saturated']} observed saturated** and **{evidence['offledger_proportional_counterfactual_unsaturated']} bounded-counterfactual unsaturated** labels with p95/max component-scale errors **{evidence['offledger_proportional_p95_error']:.3e}/{evidence['offledger_proportional_max_error']:.3e}**. A source-model short-schedule control then generates **{evidence['physical_unsaturated_calls']}/128** physical unsaturated, zero-makeup calls. Its start/end-pressure trapezoid gives **{evidence['physical_unsaturated_trapezoid_p95_relative_error']:.3%}** p95 demand error and the clean circuit uses **{evidence['physical_unsaturated_logical_qubits']} qubits**, depth **{evidence['physical_unsaturated_depth']:,}**, and **{evidence['physical_unsaturated_cx']:,} CX**. This control keeps the recycle fraction but shortens non-adsorption from 10 s to **{evidence['physical_unsaturated_schedule_s']:.2f} s**; frozen-schedule physical unsaturated trajectories and monolithic phase integration remain open.
- Five gas inventories are reversibly mapped to pressure at **152 logical qubits** and **93,764 CX**. The supplied-composition three-pressure/two-face/five-balance baseline uses **1,508 logical qubits** and **8,328,622 CX**. A support-adaptive normalizer generates both five-component upwind compositions directly from the retained gas inventories over **25,856 normalization states**. The clean normalized transport-balance circuit uses **1,651 logical qubits**, depth **22,143,683**, and **14,667,150 CX**; its standalone normalizer uses **333 qubits/1,340,232 CX**, and the maximum component p95 composition error is **2.071e-4**.
- Current/next loading registers are connected through reversible sign extraction and solid-mass conversion to the interior-cell gas balance. The precision screen widens H2/CO2/CH4/CO/N2 loading interfaces from **20/24/20/20/20** to **26/26/32/32/30 bits**. The interface alone uses **383–431 logical qubits** and **139,600–343,680 CX**, or **934 qubits/1,411,882 additive CX** across five components.
- Recompiling the five LDF microsteps at those wider interfaces permits direct clean LDF→sign→solid-conversion→cell-balance composition. Component circuits use **861–929 logical qubits** and **3,412,254–4,991,534 CX**; sequential workspace-reuse accounting is **1,317 logical qubits** and **19,082,852 additive CX**.
- Five parameter-specialized paths connect the full 20-bit normalized pressure/composition outputs and both internal faces to LDF uptake and the same component balance. They use **1,944–2,039 logical qubits** and **20,670,468–35,947,274 CX** each; the common-path-repeating upper bound is **2,039 peak qubits/128,013,726 additive CX**. All five frozen-support precision gates pass. The higher controller-coupled tier generates normalization, pressure, both faces, the dynamic response, and each component update; the tank tier removes the recorded withdrawal lookup on the saturated branch. Monolithic five-component phase integration remains open.
- A dense seven-bit representation addresses **2^63 amplitudes**, making generic dense preparation infeasible.
- The complete nine-job IBM campaign spans three processors and three fixed transpiler seeds. Its mean estimate is **{evidence['qpu_campaign_estimate_mean']:.6f}**, mean absolute error is **{evidence['qpu_campaign_mean_absolute_error']:.6f}**, between-job SD is **{evidence['qpu_campaign_between_job_sd']:.6f}**, and recorded QPU charge is **{evidence['qpu_campaign_total_charge_seconds']:.0f} s**. This remains a three-qubit hardware boundary, not an end-to-end PSA execution.
- The independent H2 audit fails the five-times resolution gate. A future full-support campaign needs group-held-out recovery RMSE no larger than **{evidence['max_h2_recovery_rmse_full_support_pct_point']:.3f} percentage points**; the frozen 0.010 policy span needs about **{evidence['max_h2_recovery_rmse_primary_span_pct_point']:.3f} percentage points**.

## Claim boundary

**Supported:** resource-aware estimator comparison and implementation boundary for a frozen, surrogate-conditioned PSA chance constraint.

**Not supported:** end-to-end quantum advantage, external confirmation of recycle 0.420, industrial H2 validation, or deployment readiness.

## Editorial risk and response

The main desk-review risk is that the quantum calculation can be read as a small illustrative kernel disconnected from the PSA model. The manuscript addresses this with an exact final-cycle stream ledger, a parameter-only initializer, compiled stream/event logic, a 510-qubit policy oracle, direct tank/spatial trajectories, clean five-component LDF microsteps, gas-inventory-generated interior and product-cell paths, pressure-derived 557-qubit saturated and 647-qubit bounded proportional-allocation interfaces, an 845-qubit source-model physical unsaturated control, a 440-qubit coherent finite-support controller, a 495-qubit controller-to-coefficient interface, and 2,696–2,885-qubit paths that connect raw three-cell inventories and coherent control through normalization, pressure, two faces, dynamic Langmuir response, LDF/loading conversion, and conservative balance. The aggregate surrogate's raw instability is reported separately from the source model's 68-cycle physical horizon and 85-cycle precision target. The remaining local implementation gap is the frozen-schedule physical unsaturated branch, adaptive integration, and a complete monolithic reversible phase/cycle map.

The second risk is insufficient process validation. The manuscript reports the public H2 and simulator checks as negative or directional controls and gives a quantitative specification for the next same-control H2 campaign. No cross-system dataset is presented as industrial validation.

## Graphical abstract

`{OUT_PNG.name}` and `{OUT_PDF.name}` summarize the left-to-right logic: frozen PSA decision, matched estimators, and measured implementation boundary.
"""
    OUT_MD.write_text(editorial, encoding="utf-8")

    cover = f"""# Cover letter draft — Computers & Chemical Engineering

[Date]

Dear Editor,

Please consider our manuscript, “{TITLE},” for publication as a research article in *Computers & Chemical Engineering*.

The manuscript asks a process-systems question that asymptotic quantum-computing analyses usually leave unresolved: does amplitude estimation improve an actual PSA chance-constrained policy decision after strong classical estimators, state preparation, reversible process evaluation, and hardware error are counted on the same basis? We freeze three product-recycle policies and one joint hydrogen purity/recovery event, then compare Monte Carlo, scrambled Sobol randomized quasi-Monte Carlo, defensive-mixture importance sampling, and noiseless maximum-likelihood amplitude estimation over 200 matched replications.

The result is deliberately resource-aware. Scrambled Sobol RQMC attains RMSE 0.002482, below noiseless MLAE at 0.002892. A compiled response-event oracle requires 99 logical qubits and 35,160 CX per call. A parameter-only initializer and one-cycle composition recover 32/32 event labels without held dynamic states; its 20 affine blocks reach 118 logical qubits and 578,702 forward CX. A policy-specific stream-to-event oracle retains 96/96 candidate-policy and 32/32 ledger-support labels at up to 510 logical qubits and 1,286,021 CX. Raw aggregate 50-cycle repetition passes CSS in only 2/32 runs, whereas all 32 source tank/spatial models settle with a latest joint horizon of 68 cycles. A 16-bit audit gives an 85-cycle target and 2,880-qubit clean out-of-place state/stream accounting point before nonlinear transport workspace. Five controller-coupled paths now generate normalized compositions, three pressures, two faces, the run-affinity Langmuir denominator/reciprocal, and q*/LDF/loading/balance updates directly from raw three-cell inventories. They compile to {evidence['coherent_normalized_dynamic_component_qubit_range'][0]:,}–{evidence['coherent_normalized_dynamic_component_qubit_range'][1]:,} qubits and {evidence['coherent_normalized_dynamic_component_cx_range'][0]:,}–{evidence['coherent_normalized_dynamic_component_cx_range'][1]:,} CX each. A 557-qubit pressure-derived circuit removes the withdrawal lookup on all 128 frozen saturated tank calls. A 647-qubit extension selects that branch or proportional allocation and preserves 128 observed saturated plus 224 bounded-counterfactual unsaturated labels; the added cases test arithmetic rather than physical trajectories. A nine-job IBM campaign over three processors and three fixed transpiler seeds gives mean estimate {evidence['qpu_campaign_estimate_mean']:.6f}, mean absolute error {evidence['qpu_campaign_mean_absolute_error']:.6f}, and between-job SD {evidence['qpu_campaign_between_job_sd']:.6f} for exact 0.625; it serves as a hardware-noise boundary.

The paper's contribution is the separation of estimator error, decision value, process-model validity, state-loading cost, reversible-oracle cost, and QPU behavior within one chemical-engineering workflow. Independent H2 literature data and two public simulator paths do not validate the selected policy; we report these results as negative or directional controls and quantify the accuracy required of a future same-control H2 campaign. This boundary is central to the manuscript: we do not claim quantum advantage, industrial H2 validation, or deployment readiness.

We believe the paper fits the journal because it connects uncertainty-aware process optimization, cyclic adsorption modeling, numerical benchmarking, and emerging computational hardware through a reproducible decision framework. The submission includes the main manuscript, supporting information, code and data manifests, highlights, and a graphical abstract.

[Confirm before submission: This manuscript is original, is not under consideration elsewhere, and all authors approve its submission.]

[Confirm before submission: conflict-of-interest statement.]

[Confirm before submission: funding statement. The manuscript already contains the Elsevier-format generative-AI declaration; all authors must approve it with the final text.]

Sincerely,

Ugwiyeon Lee\nKorea Gas Safety Corporation\n1390 Wonjung-ro, Maengdong-myeon, Eumseong-gun, Chungcheongbuk-do 27738, Republic of Korea\nlyullee@kgs.or.kr\n[Telephone, if required]
"""
    OUT_COVER.write_text(cover, encoding="utf-8")

    checklist = f"""# CCE submission checklist

## Scientifically complete in the local package

- [x] Frozen policy candidates, joint event, chance target, estimator budgets, and failure rules.
- [x] Matched 200-replication MC/RQMC/IS/MLAE comparison.
- [x] Decision-margin analysis showing limited value from estimator precision below RQMC.
- [x] Primitive-gate resource ladder for finite, response, calibrated-map, and hardware tiers.
- [x] Exact 32-run primary final-cycle phase ledger and nested held-out phase-stream reconstruction of 32/32 event labels, conditional on observed phase-start states.
- [x] Twelve primary event-active stream blocks compiled at 12-bit inputs/16-bit outputs: 272 logical qubits, 1,101,233 forward CX, and 2,202,466 clean CX.
- [x] Final aggregate-stream purity/recovery arithmetic compiled at 16 bits: 32/32 labels, 125 logical qubits, and 182,981 clean CX with exact circuit uncomputation.
- [x] Integrated policy-specific stream-to-event oracle compiled at 19 aggregate bits: 96/96 candidate-policy labels, 32/32 ledger-support labels, 510 logical qubits, and at most 1,286,021 clean CX.
- [x] Parameter-only nested-held-out CSS initializer: 32/32 one-cycle event labels with no held dynamic state; 20 blocks compiled to 118 logical qubits and 578,702 forward CX.
- [x] Fifty-cycle stability boundary reported: raw map 28/32 terminal labels and 2/32 CSS passes; label-free spectral anchoring 32/32 labels and CSS passes, explicitly limited to a reduced-surrogate correction.
- [x] Direct 32-run tank/spatial CSS horizon: latest joint physical horizon 68 cycles; 16-bit screen gives 85 cycles and 1,360/2,720/2,880-qubit architecture-specific register accounting.
- [x] Competitive-Langmuir numerator/denominator microkernel compiled over 25,856 physical cell states: 18 bits, 266 logical qubits, 127,112 forward CX, and 254,224 clean compute-uncompute-equivalent CX.
- [x] Clean competitive-Langmuir reciprocal/CO2-LDF follow-on compiled: five-bit denominator address, 24-bit arithmetic, 515 logical qubits, 1,225,138 CX, and p95 LDF-next error 7.26e-4.
- [x] Clean H2/CO2/CH4/CO/N2 one-cell LDF microsteps compiled separately: 490–515 logical qubits and 1,118,920–1,965,308 CX each; sequential workspace-reuse accounting is 675 logical qubits and 6,547,362 additive CX.
- [x] Product-end valve/component-flux module compiled at 288 logical qubits and 800,762 CX; separate five-component fixed-policy product-split/tank-capacity accounting is 677 logical qubits and 1,043,990 additive CX.
- [x] Gas-inventory pressure reconstruction compiled at 152 logical qubits and 93,764 CX; oriented internal-face five-component transport compiled at 404 logical qubits and 1,340,390 CX, with 584-qubit/1,527,918-additive-CX modular accounting.
- [x] Three pressure reconstructions and two internal faces directly composed with five centre-cell balances: 1,508 logical qubits, depth 12,250,291, and 8,328,622 CX over 12,928 states/64,640 component balances.
- [x] Both upwind compositions generated reversibly from gas inventories and directly composed with the same transport/balance path: 1,651 logical qubits, depth 22,143,683, and 14,667,150 CX; standalone normalizer 333 qubits/1,340,232 CX; 25,856 normalization states with zero erasure/overflow.
- [x] Five sign-split interior-cell component balances compiled at 198–209 logical qubits and 68,676–80,800 CX each; workspace-reuse accounting is 609 logical qubits and 366,802 additive CX over 64,640 cached balances with zero underflow.
- [x] Current/next loading sign extraction and solid-mass conversion directly composed with cell balance: 26/26/32/32/30-bit interfaces, 383–431 qubits and 139,600–343,680 CX per component, and 934 qubits/1,411,882 additive CX with workspace reuse.
- [x] Widened LDF current/next registers directly composed with sign extraction, solid conversion, and next-gas balance: 861–929 qubits and 3,412,254–4,991,534 CX per component; five-component accounting is 1,317 qubits/19,082,852 additive CX.
- [x] Full 20-bit normalized pressure/composition and both generated internal faces directly connected to parameter-specialized LDF uptake and the same component balance: 1,944–2,039 qubits and 20,670,468–35,947,274 CX per path; 2,039-peak-qubit/128,013,726-additive-CX conservative upper bound; monolithic five-component transpilation explicitly open.
- [x] Shared product pressure/composition directly connected to factor-specialized LDF uptake, product-valve flux, and one boundary balance: 1,072–1,195 qubits and 10,060,060–26,810,396 CX per component; 1,195-peak-qubit/88,388,552-additive-CX conservative upper bound; product normalization, inward-face generation, controller wiring, and monolithic compilation explicitly open.
- [x] Two product-end gas inventories directly connected through two composition normalizers, two pressure reconstructions, one inward face, factor-specialized LDF uptake, product-valve flux, loading conversion, and one boundary balance: {evidence['normalized_product_component_qubit_range'][0]:,}–{evidence['normalized_product_component_qubit_range'][1]:,} qubits and {evidence['normalized_product_component_cx_range'][0]:,}–{evidence['normalized_product_component_cx_range'][1]:,} CX per component; {evidence['normalized_product_peak_logical_qubits']:,}-peak-qubit/{evidence['normalized_product_additive_cx_upper_bound']:,}-additive-CX conservative upper bound; consumption of controller-generated coefficients and monolithic compilation explicitly open.
- [x] Coherent finite-support run/schedule/tank controller: {evidence['coherent_interface_parameter_checks']} run-parameter values, {evidence['coherent_interface_schedule_checks']} schedule addresses, and {evidence['coherent_interface_tank_checks']} tank records checked; {evidence['coherent_interface_logical_qubits']} qubits, depth {evidence['coherent_interface_depth']:,}, and {evidence['coherent_interface_cx']:,} CX with zero meaningful tank erasure, underflow, or mismatch.
- [x] Coherent run factors directly converted to five component equilibrium and LDF-alpha coefficients plus paired-bed adsorption flags: {evidence['coherent_factor_ldf_coefficient_records']} coefficient records and {evidence['coherent_factor_ldf_schedule_flags']} flags checked; {evidence['coherent_factor_ldf_logical_qubits']} qubits, depth {evidence['coherent_factor_ldf_depth']:,}, and {evidence['coherent_factor_ldf_cx']:,} CX; all declared relative-error gates pass.
- [x] Intermediate coefficient-consumer audit with a supplied 20-bit Langmuir response: {evidence['coherent_coefficient_consumer_component_balance_records']:,} component balances; {evidence['coherent_coefficient_consumer_component_qubit_range'][0]:,}–{evidence['coherent_coefficient_consumer_component_qubit_range'][1]:,} qubits and {evidence['coherent_coefficient_consumer_component_cx_range'][0]:,}–{evidence['coherent_coefficient_consumer_component_cx_range'][1]:,} CX per path; zero quantized-transfer erasure.
- [x] Run-affinity-dependent Langmuir denominator/reciprocal generated from supplied 20-bit pressure and five compositions and consumed in the same five schedule-gated paths: {evidence['coherent_dynamic_langmuir_component_balance_records']:,} component balances; {evidence['coherent_dynamic_langmuir_component_qubit_range'][0]:,}–{evidence['coherent_dynamic_langmuir_component_qubit_range'][1]:,} qubits and {evidence['coherent_dynamic_langmuir_component_cx_range'][0]:,}–{evidence['coherent_dynamic_langmuir_component_cx_range'][1]:,} CX per path; denominator p95/max {evidence['coherent_dynamic_langmuir_denominator_p95_error']:.3e}/{evidence['coherent_dynamic_langmuir_denominator_max_error']:.3e}.
- [x] Three raw five-component gas inventories directly connected through two normalizers, three pressure reconstructions, two oriented faces, coherent control, dynamic Langmuir response, q*/LDF/loading conversion, and one conservative component balance: {evidence['coherent_normalized_dynamic_component_qubit_range'][0]:,}–{evidence['coherent_normalized_dynamic_component_qubit_range'][1]:,} qubits and {evidence['coherent_normalized_dynamic_component_cx_range'][0]:,}–{evidence['coherent_normalized_dynamic_component_cx_range'][1]:,} CX per path; {evidence['coherent_normalized_dynamic_peak_logical_qubits']:,}-peak-qubit/{evidence['coherent_normalized_dynamic_additive_cx_upper_bound']:,}-additive-CX conservative upper bound.
- [x] Correlated dense-loader infeasibility control and explicit structured-loader caveat.
- [x] Nine-job IBM hardware campaign across three backends and three fixed transpiler seeds, with job IDs, counts, layouts, calibration times, charges, crossed variability analysis, and claim boundary.
- [x] Independent H2/public-simulator controls reported without cross-system pooling.
- [x] Prospective H2 campaign precision target.
- [x] Main manuscript, six main figures, four main tables, SI draft, environment freezes, hashes, highlights, cover-letter draft, and graphical abstract.
- [x] Condense Tables 3 and 4 to eight claim-critical rows each in the main text and reproduce the complete 31/32-tier audit tables as Supplementary Tables S1/S2.
- [x] Compile the pressure-derived saturated/unsaturated tank-allocation tier: 647 qubits, depth 1,127,046, and 705,194 CX; preserve 128 observed saturated and 224 bounded-counterfactual unsaturated labels with p95/max component-scale errors 1.687e-4/3.872e-4.

## Scientific gates that most affect CCE acceptance

- [ ] **Highest priority:** same physical product-recycle control in H2, with synchronized pressure, valve state, feed/product/recycle flow, continuous product composition, cycle index, and product/recycle split.
- [ ] Use held-out groups or runs; target recovery RMSE <=1.517 percentage points across the observed recycle support, or about <=0.156 percentage points if retaining only the 0.420–0.430 span.
- [x] Repeat the frozen QPU kernel on three backends and three fixed transpiler seeds; report the complete crossed nine-job hardware boundary and descriptive variation without claiming a universal device effect.
- [ ] Generate a physically integrated unsaturated tank trajectory, connect the completed normalized dynamic component paths into at least one complete adsorption phase, and compare it with the 85-cycle physical target.
- [ ] If an end-to-end advantage claim is pursued, implement and compile a scalable structured correlated loader. This is unnecessary for the present boundary-paper claim.

## Author and journal administration

- [x] Record final author order, Korea Gas Safety Corporation affiliation, Ugwiyeon Lee as corresponding author, emails, and validated ORCID check digits.
- [x] Draft the CRediT statement: Ugwiyeon Lee holds the research and manuscript roles; Seong-Yun Bae, Hakrae Kim, and Jungsu Lee hold Writing – review & editing.
- [ ] Obtain explicit approval of the final manuscript, order, and CRediT statement from every author.
- [x] Insert a Methods description and pre-reference declaration of OpenAI Codex use that follows Elsevier's June 2026 generative-AI policy; retain author confirmation as a final approval gate.
- [ ] Confirm funding, acknowledgements, and conflict of interest statements.
- [x] Convert the manuscript, author title page, and SI into separate DOCX files and verify their Word-rendered pages (30-page review manuscript, 1-page title page, and 7-page SI at the current revision).
- [x] Apply the current CCE reference, table, and artwork requirements: author-year citations, alphabetized references, editable tables without shading or vertical rules, and separate vector-PDF versions of all six main figures.
- [x] Verify the graphical abstract against the current guide: 3,706 x 1,446 px PNG plus vector PDF, exceeding the 1,328 x 531 px minimum.
- [ ] Create a permanent public code/data archive and insert its DOI.
- [ ] Confirm the originality/not-under-review statements in the cover letter.
- [ ] Perform final English, symbol, unit, figure-number, and cross-reference checks.

## Submission decision

The package is structurally complete but `submission_ready=false`. A resource-boundary methods paper can be submitted after author/journal administration if the remaining scientific gates are disclosed. The multi-backend repeated-QPU gate is now complete; the strongest CCE version still closes the same-control H2 validation gate. End-to-end quantum advantage remains outside the supported claim.
"""
    OUT_CHECKLIST.write_text(checklist, encoding="utf-8")
    print(json.dumps({"status": payload["status"], "outputs": len(payload["outputs"]) + 1, "qpu_submission": False}, indent=2))


if __name__ == "__main__":
    main()
