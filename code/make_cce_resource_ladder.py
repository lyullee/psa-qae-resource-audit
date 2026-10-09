"""Create the CCE main-text resource ladder figure and Table 3."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import LogLocator


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RESULTS = ROOT / "10_TEA_LCA_Python" / "results" / "pycharm_publication_enhancement"

LINEAR = RESULTS / "PSA_QAE_CCE_PRIMARY_LINEAR_SURROGATE_ORACLE.json"
LOADER = RESULTS / "PSA_QAE_CCE_PRIMARY_COPULA_STATE_LOADER.json"
PHASE_SCREEN = RESULTS / "PSA_QAE_CCE_PHASE_MAP_FIXED_POINT_SCREEN.json"
PHASE_COMPILE = RESULTS / "PSA_QAE_CCE_PHASE_MAP_AFFINE_BLOCK_COMPILE.json"
PRIMARY_PHASE_LEDGER = RESULTS / "PSA_QAE_CCE_PRIMARY_PHASE_LEDGER.json"
PRIMARY_EVENT_BRIDGE = RESULTS / "PSA_QAE_CCE_PRIMARY_PHASE_EVENT_BRIDGE.json"
PRIMARY_EVENT_SCREEN = RESULTS / "PSA_QAE_CCE_PRIMARY_PHASE_EVENT_FIXED_POINT_SCREEN.json"
PRIMARY_EVENT_COMPILE = RESULTS / "PSA_QAE_CCE_PRIMARY_PHASE_EVENT_BLOCK_COMPILE.json"
PRIMARY_FINAL_EVENT = RESULTS / "PSA_QAE_CCE_PRIMARY_FINAL_EVENT_ARITHMETIC.json"
PRIMARY_POLICY_STREAM_EVENT = RESULTS / "PSA_QAE_CCE_PRIMARY_POLICY_STREAM_EVENT_ORACLE.json"
CSS_INITIALIZER_BRIDGE = RESULTS / "PSA_QAE_CCE_PRIMARY_CSS_INITIALIZER_EVENT_BRIDGE.json"
CSS_INITIALIZER_SCREEN = RESULTS / "PSA_QAE_CCE_PRIMARY_CSS_INITIALIZER_FIXED_POINT_SCREEN.json"
CSS_INITIALIZER_COMPILE = RESULTS / "PSA_QAE_CCE_PRIMARY_CSS_INITIALIZER_BLOCK_COMPILE.json"
SMALL_E2E = RESULTS / "PSA_QAE_CCE_SMALL_END_TO_END_ORACLE.json"
FINITE = RESULTS / "PSA_QAE_CCE_PRIMARY_FINITE_ORACLE_GATE_RESOURCES.json"
IBM_PREFLIGHT = RESULTS / "PSA_QAE_CCE_PRIMARY_FINITE_ORACLE_IBM_PREFLIGHT_ibm_marrakesh.json"
QPU = RESULTS / "QAE_QPU_BREAKTHROUGH_PHASE_MLAE_IBM_db42v34lf4us73c24q50.json"
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

OUT_PNG = RESULTS / "PSA_QAE_CCE_RESOURCE_LADDER_FIGURE.png"
OUT_PDF = RESULTS / "PSA_QAE_CCE_RESOURCE_LADDER_FIGURE.pdf"
OUT_JSON = RESULTS / "PSA_QAE_CCE_RESOURCE_TABLE3.json"
OUT_CSV = RESULTS / "PSA_QAE_CCE_RESOURCE_TABLE3.csv"
OUT_MD = RESULTS / "PSA_QAE_CCE_RESOURCE_TABLE3.md"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    linear = load(LINEAR)
    loader = load(LOADER)
    phase_screen = load(PHASE_SCREEN)
    phase_compile = load(PHASE_COMPILE)
    primary_phase_ledger = load(PRIMARY_PHASE_LEDGER)
    primary_event_bridge = load(PRIMARY_EVENT_BRIDGE)
    primary_event_screen = load(PRIMARY_EVENT_SCREEN)
    primary_event_compile = load(PRIMARY_EVENT_COMPILE)
    primary_final_event = load(PRIMARY_FINAL_EVENT)
    primary_policy_stream_event = load(PRIMARY_POLICY_STREAM_EVENT)
    css_initializer_bridge = load(CSS_INITIALIZER_BRIDGE)
    css_initializer_screen = load(CSS_INITIALIZER_SCREEN)
    css_initializer_compile = load(CSS_INITIALIZER_COMPILE)
    small_e2e = load(SMALL_E2E)
    finite = load(FINITE)
    ibm_preflight = load(IBM_PREFLIGHT)
    qpu = load(QPU)
    all_component_ldf = load(ALL_COMPONENT_LDF)
    product_boundary = load(PRODUCT_BOUNDARY)
    product_boundary_balance = load(PRODUCT_BOUNDARY_BALANCE)
    product_ldf_valve_balance = load(PRODUCT_LDF_VALVE_BALANCE)
    normalized_product_ldf_valve_balance = load(NORMALIZED_PRODUCT_LDF_VALVE_BALANCE)
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

    plt.rcParams.update(
        {
            "font.size": 9.2,
            "axes.titlesize": 10.5,
            "axes.labelsize": 9.5,
            "legend.fontsize": 8.0,
            "xtick.labelsize": 8.4,
            "ytick.labelsize": 8.4,
        }
    )
    fig, axes = plt.subplots(2, 2, figsize=(12.6, 8.4), constrained_layout=True)

    # (a) Decision-label accuracy that sets the response-oracle precision.
    ax = axes[0, 0]
    linear_rows = sorted(linear["rows"], key=lambda row: row["input_bits_per_feature"])
    bits = [row["input_bits_per_feature"] for row in linear_rows]
    disagreement = [row["classification_disagreement"] for row in linear_rows]
    ax.plot(bits, disagreement, "o-", color="#1f77b4", lw=2, label="event-label disagreement")
    threshold = float(linear["fixed_point"]["observed_noiseless_mlae_rmse"])
    ax.axhline(threshold, color="#c00000", ls="--", label="observed MLAE RMSE")
    selected_linear = next(row for row in linear_rows if row["input_bits_per_feature"] == 7)
    ax.scatter([7], [selected_linear["classification_disagreement"]], s=80, facecolors="none", edgecolors="#111111", zorder=5)
    ax.annotate(
        "selected: 7-bit input\n99 qubits; 35,160 CX/call",
        xy=(7, selected_linear["classification_disagreement"]),
        xytext=(4.25, 0.0105),
        arrowprops={"arrowstyle": "->", "lw": 0.9},
        ha="left",
    )
    ax.set(xlabel="bits per active uncertainty coordinate", ylabel="classification disagreement", yscale="log", title="(a) Response-oracle decision accuracy")
    ax.set_xticks(bits)
    ax.grid(alpha=0.25, which="both")
    ax.legend(loc="upper right")

    # (b) Measured low-bit dense loading and the unsynthesized accuracy tier.
    ax = axes[0, 1]
    loader_rows = sorted(loader["compiled_rows"], key=lambda row: row["bits_per_active_feature"])
    x_loader = [row["bits_per_active_feature"] for row in loader_rows]
    cx_loader = [row["transpiled_cx_prepare"] for row in loader_rows]
    bars = ax.bar(x_loader, cx_loader, width=0.55, color="#9467bd", label="compiled dense preparation")
    for bar, row in zip(bars, loader_rows):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() * 1.20,
            f"CX {row['transpiled_cx_prepare']:,}\nlabel error {row['event_label_disagreement']:.3f}",
            ha="center",
            va="bottom",
            fontsize=7.8,
        )
    tier = loader["accuracy_tier"]
    ax.axvline(7, color="#c00000", ls="--", lw=1.2)
    ax.text(
        6.8,
        1.3e3,
        "7-bit tier not synthesized\n63 loader qubits\n$2^{63}$ amplitudes; 64 EiB table",
        ha="right",
        va="bottom",
        color="#8b0000",
        fontsize=8.2,
    )
    ax.set(xlabel="bits per active uncertainty coordinate", ylabel="CX gates for state preparation", yscale="log", title="(b) Dense empirical-copula loader boundary")
    ax.set_xticks([1, 2, 7])
    ax.set_xlim(0.3, 7.5)
    ax.set_ylim(2e2, 1.3e6)
    ax.grid(alpha=0.25, axis="y", which="both")

    # (c) Joint phase-map input/output precision screen, normalized by budgets.
    ax = axes[1, 0]
    for output_bits in phase_screen["sum_bits_cases"]:
        selected = [
            row
            for row in phase_screen["summaries"]
            if row["sum_bits_per_scalar_output"] == output_bits
        ]
        selected.sort(key=lambda row: row["bits_per_input"])
        ratio = [
            max(
                row["p95_state_quantization_relative_l1"] / row["state_budget_10pct_holdout_p95"],
                row["p95_outlet_h2_quantization_abs_error"] / row["outlet_budget_10pct_holdout_p95"],
            )
            for row in selected
        ]
        ax.plot(
            [row["bits_per_input"] for row in selected],
            ratio,
            "o-",
            ms=3.5,
            label=f"{output_bits}-bit accumulator",
        )
    feasible = phase_screen["minimum_register_proxy_configuration_within_both_budgets"]
    feasible_ratio = max(
        feasible["p95_state_quantization_relative_l1"] / feasible["state_budget_10pct_holdout_p95"],
        feasible["p95_outlet_h2_quantization_abs_error"] / feasible["outlet_budget_10pct_holdout_p95"],
    )
    ax.axhline(1.0, color="#c00000", ls="--", label="declared error budget")
    ax.scatter([feasible["bits_per_input"]], [feasible_ratio], s=90, facecolors="none", edgecolors="#111111", zorder=6)
    ax.annotate(
        "selected: 11-bit input / 16-bit output\n170-qubit register proxy",
        xy=(feasible["bits_per_input"], feasible_ratio),
        xytext=(6.0, 0.16),
        arrowprops={"arrowstyle": "->", "lw": 0.9},
        fontsize=8.2,
    )
    ax.set(xlabel="bits per active phase-map input", ylabel="max(p95 error / allocated budget)", yscale="log", title="(c) Calibrated phase-map precision")
    ax.set_xticks(range(2, 17, 2))
    ax.grid(alpha=0.25, which="both")
    ax.legend(ncol=2, loc="upper right")

    # (d) Primitive two-qubit-gate cost of the 72 calibrated affine blocks.
    ax = axes[1, 1]
    phase_rows = phase_compile["phase_summaries"]
    phase_labels = {
        "A_adsorption": "A ads.",
        "B_pressurization": "B press.",
        "A_blowdown": "A blow.",
        "B_adsorption": "B ads.",
        "A_purge": "A purge",
        "B_blowdown": "B blow.",
        "A_pressurization": "A press.",
        "B_purge": "B purge",
    }
    labels = [phase_labels[row["phase"]] for row in phase_rows]
    x = np.arange(len(labels))
    width = 0.36
    ax.bar(x - width / 2, [row["serial_forward_cx"] for row in phase_rows], width, color="#2ca02c", label="forward")
    ax.bar(x + width / 2, [row["serial_clean_compute_uncompute_cx"] for row in phase_rows], width, color="#ff7f0e", label="clean compute-uncompute")
    cycle = phase_compile["full_cycle_affine_block_serial_bound"]
    ax.text(
        0.02,
        0.97,
        f"72 blocks; max 186 qubits\ncycle total: {cycle['serial_forward_cx']:,} forward CX\n{cycle['serial_clean_compute_uncompute_cx']:,} clean CX",
        transform=ax.transAxes,
        va="top",
        ha="left",
        fontsize=8.2,
        bbox={"facecolor": "white", "edgecolor": "0.75", "alpha": 0.9, "pad": 3},
    )
    event_blocks = primary_event_compile["aggregate"]
    final_event = primary_final_event["primitive_gate_compile"]["clean_phase_oracle"]
    policy_oracle = max(
        primary_policy_stream_event["primitive_gate_compile"]["policy_resources"],
        key=lambda row: row["clean_phase_oracle"]["cx"],
    )["clean_phase_oracle"]
    css_blocks = css_initializer_compile["aggregate"]
    ax.text(
        0.98,
        0.97,
        f"primary surrogate tiers\nCSS init.: 20 blocks; {css_blocks['max_logical_qubits_reusing_scalar_workspace']} q; "
        f"{css_blocks['serial_forward_cx'] / 1e6:.2f} M CX\n"
        f"event streams: 12 blocks; {event_blocks['max_logical_qubits_reusing_scalar_workspace']} q; "
        f"{event_blocks['serial_forward_cx'] / 1e6:.2f} M CX\n"
        f"final event: {final_event['logical_qubits']} q; {final_event['cx'] / 1e6:.2f} M clean CX\n"
        f"policy stream→event: {policy_oracle['logical_qubits']} q; {policy_oracle['cx'] / 1e6:.2f} M clean CX",
        transform=ax.transAxes,
        va="top",
        ha="right",
        fontsize=8.0,
        bbox={"facecolor": "#eef7ff", "edgecolor": "#6a8fb3", "alpha": 0.92, "pad": 3},
    )
    ax.set(ylabel="compiled CX gates", title="(d) Calibrated affine variable-term cost", xticks=x, xticklabels=labels, yscale="log")
    ax.yaxis.set_major_locator(LogLocator(base=10, subs=(1.0,)))
    ax.tick_params(axis="x", labelrotation=0)
    ax.grid(alpha=0.25, axis="y", which="both")
    ax.legend(loc="lower right")

    fig.savefig(OUT_PNG, dpi=300)
    fig.savefig(OUT_PDF)
    plt.close(fig)

    finite_oracle = next(
        row
        for row in finite["oracle_comparison"]
        if row["topology"] == "all_to_all_CX"
        and row["implementation"] == "global_phase_equivalent_mark_7_bad"
    )
    finite_schedule = finite["total_frozen_mlae_experiment"]["all_to_all_CX"]
    worst_scalar = max(phase_compile["scalar_blocks"], key=lambda row: row["forward_cx"])
    qpu_max = max(qpu["circuits"], key=lambda row: row["depth"])
    preflight_m8 = next(row for row in ibm_preflight["summaries"] if row["power"] == 8)
    rows = [
        {
            "tier": "finite-table phase oracle",
            "role": "32-row exact event control",
            "logical_qubits": 5,
            "compiled_basis_or_device": "all-to-all u/CX",
            "per_call_or_block_resource": f"{finite_oracle['two_qubit_gates']:,} CX; depth {finite_oracle['depth']:,}",
            "schedule_or_aggregate_resource": f"{int(finite_schedule['median_transpiled_two_qubit_gates']):,} CX for frozen 3,500-query schedule",
            "accuracy_or_observation": "truth table exhaustively verified",
            "boundary": "finite enumeration; no continuous prior or cyclic integrator",
        },
        {
            "tier": "small end-to-end structural oracle",
            "role": "state update/equalization/joint-event/phase/uncompute connection control",
            "logical_qubits": small_e2e["registers"]["total_logical_qubits"],
            "compiled_basis_or_device": "all-to-all u/CX",
            "per_call_or_block_resource": (
                f"{small_e2e['primitive_gate_compile']['clean_phase_oracle']['cx']:,} CX; "
                f"depth {small_e2e['primitive_gate_compile']['clean_phase_oracle']['depth_all_to_all']:,}"
            ),
            "schedule_or_aggregate_resource": "one coherent compute-phase-uncompute control",
            "accuracy_or_observation": "64/64 phase labels; all work qubits clean",
            "boundary": "three-bit structural integer map; not calibrated kinetics, CSS, or primary H2 event",
        },
        {
            "tier": "fixed-point response-event oracle",
            "role": "active recovery response plane",
            "logical_qubits": selected_linear["total_logical_qubits"],
            "compiled_basis_or_device": "all-to-all u/CX",
            "per_call_or_block_resource": f"{selected_linear['transpiled_cx']:,} CX; depth {selected_linear['transpiled_depth']:,}",
            "schedule_or_aggregate_resource": f"{selected_linear['frozen_schedule_cx_lower_bound_excluding_loader']:,} CX for 1,500 phase calls",
            "accuracy_or_observation": f"event disagreement {selected_linear['classification_disagreement']:.6f}",
            "boundary": "correlated loader and cyclic PSA evaluator excluded",
        },
        {
            "tier": "dense empirical-copula loader (1 bit)",
            "role": "low-resolution state-preparation control",
            "logical_qubits": loader_rows[0]["loader_qubits"],
            "compiled_basis_or_device": "all-to-all u/CX",
            "per_call_or_block_resource": f"{loader_rows[0]['transpiled_cx_prepare']:,} CX prepare; depth {loader_rows[0]['transpiled_depth']:,}",
            "schedule_or_aggregate_resource": f"{loader_rows[0]['transpiled_cx_prepare_uncompute']:,} CX prepare-uncompute",
            "accuracy_or_observation": f"event disagreement {loader_rows[0]['event_label_disagreement']:.6f}",
            "boundary": "accuracy insufficient",
        },
        {
            "tier": "dense empirical-copula loader (2 bit)",
            "role": "low-resolution state-preparation control",
            "logical_qubits": loader_rows[1]["loader_qubits"],
            "compiled_basis_or_device": "all-to-all u/CX",
            "per_call_or_block_resource": f"{loader_rows[1]['transpiled_cx_prepare']:,} CX prepare; depth {loader_rows[1]['transpiled_depth']:,}",
            "schedule_or_aggregate_resource": f"{loader_rows[1]['transpiled_cx_prepare_uncompute']:,} CX prepare-uncompute",
            "accuracy_or_observation": f"event disagreement {loader_rows[1]['event_label_disagreement']:.6f}",
            "boundary": "7-bit dense tier would require 63 qubits and a 64-EiB probability table",
        },
        {
            "tier": "calibrated one-cycle affine blocks",
            "role": "8 phases x 9 fitted scalar variable terms",
            "logical_qubits": cycle["max_logical_qubits_reusing_scalar_workspace"],
            "compiled_basis_or_device": "all-to-all u/CX",
            "per_call_or_block_resource": f"worst block {worst_scalar['forward_cx']:,} CX; depth {worst_scalar['forward_depth_all_to_all']:,}",
            "schedule_or_aggregate_resource": f"{cycle['serial_forward_cx']:,} forward CX; {cycle['serial_clean_compute_uncompute_cx']:,} clean CX",
            "accuracy_or_observation": "11-bit input / 16-bit output satisfies both p95 budgets",
            "boundary": "constant/state update, equalization, CSS, event logic, loader and routing excluded",
        },
        {
            "tier": "parameter-only CSS initializer blocks",
            "role": "11 process parameters to 20 aggregate A/B CSS-state outputs",
            "logical_qubits": css_blocks["max_logical_qubits_reusing_scalar_workspace"],
            "compiled_basis_or_device": "all-to-all u/CX",
            "per_call_or_block_resource": (
                f"worst block {max(css_initializer_compile['blocks'], key=lambda row: row['forward_cx'])['forward_cx']:,} CX"
            ),
            "schedule_or_aggregate_resource": (
                f"{css_blocks['serial_forward_cx']:,} forward CX; "
                f"{css_blocks['serial_clean_compute_uncompute_cx']:,} clean CX"
            ),
            "accuracy_or_observation": (
                f"9-bit input / 14-bit output; "
                f"{css_initializer_bridge['summary']['event_matches']}/32 held-out labels without held dynamic state"
            ),
            "boundary": "fitted CSS-state initializer; constant/state update, physical CSS, tank/profile state, loader and routing excluded",
        },
        {
            "tier": "primary phase-stream event blocks",
            "role": "2 adsorption phases x 6 event-active stream outputs",
            "logical_qubits": event_blocks["max_logical_qubits_reusing_scalar_workspace"],
            "compiled_basis_or_device": "all-to-all u/CX",
            "per_call_or_block_resource": (
                f"worst block {max(primary_event_compile['blocks'], key=lambda row: row['forward_cx'])['forward_cx']:,} CX"
            ),
            "schedule_or_aggregate_resource": (
                f"{event_blocks['serial_forward_cx']:,} forward CX; "
                f"{event_blocks['serial_clean_compute_uncompute_cx']:,} clean CX"
            ),
            "accuracy_or_observation": (
                f"12-bit input / 16-bit output; "
                f"{primary_event_bridge['event_summary']['event_matches']}/32 held-out labels"
            ),
            "boundary": "conditional on observed phase starts; a collapsed policy-specific stream-to-event oracle is compiled separately; physical CSS, loader and routing excluded",
        },
        {
            "tier": "primary final joint-event arithmetic",
            "role": "16-bit aggregate feed-H2/product-H2/impurity comparison, joint phase mark, and exact uncompute",
            "logical_qubits": final_event["logical_qubits"],
            "compiled_basis_or_device": "all-to-all u/CX",
            "per_call_or_block_resource": (
                f"{final_event['cx']:,} CX; depth {final_event['depth_all_to_all']:,}"
            ),
            "schedule_or_aggregate_resource": "one clean compute-phase-uncompute event block",
            "accuracy_or_observation": (
                f"{primary_final_event['verification']['integer_event_matches']}/32 labels; "
                f"{primary_final_event['precision_screen']['selected']['bits']}-bit aggregate registers"
            ),
            "boundary": "standalone aggregate-register interface; the policy-specific upstream connection is compiled separately; physical CSS, loading and routing excluded",
        },
        {
            "tier": "primary policy stream-to-event clean oracle",
            "role": "29 encoded phase-state/parameter variables to three aggregate streams, fixed-policy recycle scaling, joint phase mark, and exact uncompute",
            "logical_qubits": policy_oracle["logical_qubits"],
            "compiled_basis_or_device": "all-to-all u/CX",
            "per_call_or_block_resource": f"{policy_oracle['cx']:,} CX; depth {policy_oracle['depth_all_to_all']:,}",
            "schedule_or_aggregate_resource": "one separately compiled clean oracle for each recycle candidate 0.420/0.427/0.430",
            "accuracy_or_observation": (
                f"{primary_policy_stream_event['precision_screen']['selected']['aggregate_bits']}-bit aggregates; "
                f"{primary_policy_stream_event['verification']['candidate_integer_event_matches_vs_float']}/96 candidate labels; "
                f"{primary_policy_stream_event['verification']['ledger_support_event_matches_vs_actual']}/32 ledger-support labels"
            ),
            "boundary": "starts from encoded observed phase-start states and shared parameters; stable physical/reversible CSS, state preparation, routing/noise and external validation excluded",
        },
        {
            "tier": "five-component equilibrium/LDF microsteps",
            "role": "one activated-carbon cell, five separately compiled competitive-Langmuir/LDF updates, one second",
            "logical_qubits": all_component_ldf["sequential_five_component_accounting"]["logical_qubits"],
            "compiled_basis_or_device": "all-to-all u/CX",
            "per_call_or_block_resource": (
                f"individual modules {min(row['compiled_clean_microstep']['cx'] for row in all_component_ldf['components']):,}–"
                f"{max(row['compiled_clean_microstep']['cx'] for row in all_component_ldf['components']):,} CX"
            ),
            "schedule_or_aggregate_resource": (
                f"{all_component_ldf['sequential_five_component_accounting']['cx_additive_module_bound']:,} additive CX "
                "with sequential workspace reuse"
            ),
            "accuracy_or_observation": "25,856 physical cell states; all component precision/overflow/erasure gates pass",
            "boundary": "modular one-cell/one-second accounting; gas transport, pressure, valves, tanks, repeated integration, routing and full phase excluded",
        },
        {
            "tier": "product-boundary valve and recycle-tank modules",
            "role": "encoded product-end pressure/composition to five one-second component fluxes, plus separate fixed-policy product split, tank candidates, and capacity flag",
            "logical_qubits": product_boundary["five_component_tank_accounting"]["logical_qubits"],
            "compiled_basis_or_device": "all-to-all u/CX",
            "per_call_or_block_resource": (
                f"valve {product_boundary['compiled_clean_valve_component_flux']['logical_qubits']} q/"
                f"{product_boundary['compiled_clean_valve_component_flux']['cx']:,} CX; "
                f"scalar split {product_boundary['compiled_clean_scalar_product_split_tank_candidate']['logical_qubits']} q/"
                f"{product_boundary['compiled_clean_scalar_product_split_tank_candidate']['cx']:,} CX; "
                f"capacity {product_boundary['compiled_clean_tank_capacity_flag']['logical_qubits']} q/"
                f"{product_boundary['compiled_clean_tank_capacity_flag']['cx']:,} CX"
            ),
            "schedule_or_aggregate_resource": (
                f"five-component tank accounting {product_boundary['five_component_tank_accounting']['logical_qubits']} q/"
                f"{product_boundary['five_component_tank_accounting']['cx_additive_module_bound']:,} additive CX; "
                "valve-flux module remains separate"
            ),
            "accuracy_or_observation": (
                f"{product_boundary['valve_state_source']['states']:,} valve states and "
                f"{product_boundary['tank_record_source']['product_recycle_records']} product/tank records; "
                "both declared precision gates pass"
            ),
            "boundary": "modular product-boundary arithmetic; local pressure/face modules are a separate tier; adsorption coupling, tank withdrawal, adaptive integration, monolithic valve-to-tank composition, routing and full cycle excluded",
        },
        {
            "tier": "direct product-valve-to-boundary-cell balance",
            "role": "encoded product-end pressure/composition through five valve-flux registers into five conservative next-gas inventories with exact valve-work reversal",
            "logical_qubits": product_boundary_balance["compiled_clean_product_valve_boundary_balance"]["logical_qubits"],
            "compiled_basis_or_device": "all-to-all u/CX",
            "per_call_or_block_resource": (
                f"one five-component clean circuit: "
                f"{product_boundary_balance['compiled_clean_product_valve_boundary_balance']['logical_qubits']:,} q/"
                f"{product_boundary_balance['compiled_clean_product_valve_boundary_balance']['cx']:,} CX; "
                f"depth {product_boundary_balance['compiled_clean_product_valve_boundary_balance']['depth_all_to_all']:,}"
            ),
            "schedule_or_aggregate_resource": "single directly transpiled valve-to-boundary-balance circuit; not an additive module estimate",
            "accuracy_or_observation": (
                f"{product_boundary_balance['physical_state_source']['product_boundary_states']:,} product-end states and "
                f"{product_boundary_balance['physical_state_source']['component_balances']:,} component balances; "
                "all five inventory precision/erasure/overflow gates pass"
            ),
            "boundary": "pressure/composition and nonvalve balance terms remain supplied; reversible normalization, valve scheduling, tank withdrawal, adaptive integration, routing and full cycle remain open",
        },
        {
            "tier": "direct product-cell LDF/valve/boundary-balance paths",
            "role": "shared encoded product pressure/composition through factor-specialized LDF uptake and product-valve flux into one conservative component balance with exact work reversal",
            "logical_qubits": product_ldf_valve_balance["conservative_five_component_upper_bound"]["logical_qubits_peak"],
            "compiled_basis_or_device": "all-to-all u/CX",
            "per_call_or_block_resource": (
                f"component paths {min(row['logical_qubits'] for row in product_ldf_valve_balance['componentwise_compiled_direct_paths']):,}–"
                f"{max(row['logical_qubits'] for row in product_ldf_valve_balance['componentwise_compiled_direct_paths']):,} q/"
                f"{min(row['cx'] for row in product_ldf_valve_balance['componentwise_compiled_direct_paths']):,}–"
                f"{max(row['cx'] for row in product_ldf_valve_balance['componentwise_compiled_direct_paths']):,} CX"
            ),
            "schedule_or_aggregate_resource": (
                f"{product_ldf_valve_balance['conservative_five_component_upper_bound']['logical_qubits_peak']:,} peak q/"
                f"{product_ldf_valve_balance['conservative_five_component_upper_bound']['cx_additive_upper_bound']:,} additive CX; "
                "monolithic five-component transpilation open"
            ),
            "accuracy_or_observation": (
                f"{product_ldf_valve_balance['physical_state_source']['product_boundary_states']:,} states; "
                f"{product_ldf_valve_balance['physical_state_source']['component_balances']:,} balances; "
                f"p95 {min(row['next_p95_scale_normalized_absolute_error'] for row in product_ldf_valve_balance['selected_components']):.3e}–"
                f"{max(row['next_p95_scale_normalized_absolute_error'] for row in product_ldf_valve_balance['selected_components']):.3e}; "
                f"max ≤{max(row['next_max_scale_normalized_absolute_error'] for row in product_ldf_valve_balance['selected_components']):.3e}"
            ),
            "boundary": "shared 20-bit pressure/composition high 18 bits feed the valve; factor-specialized component circuits; product composition normalization, inward-face generation, coherent run parameters, tank withdrawal, integration, routing and full cycle remain open",
        },
        {
            "tier": "gas-inventory-generated product-cell LDF/valve/balance paths",
            "role": "two five-component gas inventories and one current loading through two normalizers, two pressure reconstructions, one inward face, factor-specialized LDF uptake, product-valve withdrawal, and one conservative next-gas balance with exact work reversal",
            "logical_qubits": normalized_product_ldf_valve_balance["conservative_five_component_upper_bound"]["logical_qubits_peak"],
            "compiled_basis_or_device": "all-to-all u/CX",
            "per_call_or_block_resource": (
                f"component paths {min(row['logical_qubits'] for row in normalized_product_ldf_valve_balance['componentwise_compiled_direct_paths']):,}–"
                f"{max(row['logical_qubits'] for row in normalized_product_ldf_valve_balance['componentwise_compiled_direct_paths']):,} q/"
                f"{min(row['cx'] for row in normalized_product_ldf_valve_balance['componentwise_compiled_direct_paths']):,}–"
                f"{max(row['cx'] for row in normalized_product_ldf_valve_balance['componentwise_compiled_direct_paths']):,} CX"
            ),
            "schedule_or_aggregate_resource": (
                f"{normalized_product_ldf_valve_balance['conservative_five_component_upper_bound']['logical_qubits_peak']:,} peak q/"
                f"{normalized_product_ldf_valve_balance['conservative_five_component_upper_bound']['cx_additive_upper_bound']:,} additive CX; "
                "monolithic five-component transpilation open"
            ),
            "accuracy_or_observation": (
                f"{normalized_product_ldf_valve_balance['physical_state_source']['product_end_states']:,} states; "
                f"{normalized_product_ldf_valve_balance['physical_state_source']['component_balances']:,} balances; "
                f"p95 {min(row['next_p95_scale_normalized_absolute_error'] for row in normalized_product_ldf_valve_balance['selected_components']):.3e}–"
                f"{max(row['next_p95_scale_normalized_absolute_error'] for row in normalized_product_ldf_valve_balance['selected_components']):.3e}; "
                f"max ≤{max(row['next_max_scale_normalized_absolute_error'] for row in normalized_product_ldf_valve_balance['selected_components']):.3e}"
            ),
            "boundary": "frozen-support, factor-specialized component paths; the finite-support run/schedule/tank interface is reported separately, while monolithic five-component transpilation, adaptive integration, routing and full cycle remain open",
        },
        {
            "tier": "coherent run/schedule/tank interface",
            "role": "five-qubit run address to eleven fixed-point parameter words, six-stage paired-bed valve decoder, and five-component final-cycle tank subtraction",
            "logical_qubits": coherent_run_schedule_tank["integrated_interface"]["logical_qubits"],
            "compiled_basis_or_device": "all-to-all u/CX",
            "per_call_or_block_resource": (
                f"{coherent_run_schedule_tank['integrated_interface']['cx']:,} CX; "
                f"depth {coherent_run_schedule_tank['integrated_interface']['depth_all_to_all']:,}"
            ),
            "schedule_or_aggregate_resource": "one directly transpiled finite-support run/valve/tank interface; no measurement or reset",
            "accuracy_or_observation": (
                f"{coherent_run_schedule_tank['parameter_encoding']['basis_table_values_checked']} parameter values, "
                f"{coherent_run_schedule_tank['schedule_encoding']['basis_addresses_checked']} schedule addresses, and "
                f"{coherent_run_schedule_tank['tank_encoding']['basis_component_records_checked']} tank component records checked; "
                "zero meaningful erasure/underflow/mismatch"
            ),
            "boundary": "finite 32-run/final-cycle ledger QROM; continuous off-ledger parameter loading, pressure/flow-derived withdrawal, adaptive integration, monolithic five-component phase/cycle, routing and fault tolerance remain open",
        },
        {
            "tier": "coherent run-factor/LDF coefficient interface",
            "role": "loaded capacity, affinity, and LDF-factor words through reversible multiplication to five equilibrium prefactors, five LDF coefficients, and paired-bed adsorption flags",
            "logical_qubits": coherent_run_factor_ldf["compiled_interface"]["logical_qubits"],
            "compiled_basis_or_device": "all-to-all u/CX",
            "per_call_or_block_resource": (
                f"{coherent_run_factor_ldf['compiled_interface']['cx']:,} CX; "
                f"depth {coherent_run_factor_ldf['compiled_interface']['depth_all_to_all']:,}"
            ),
            "schedule_or_aggregate_resource": "one directly transpiled finite-support controller-to-kinetics coefficient circuit; no measurement or reset",
            "accuracy_or_observation": (
                f"{coherent_run_factor_ldf['support']['coefficient_records_checked']} coefficient records and "
                f"{coherent_run_factor_ldf['support']['schedule_flags_checked']} bed/stage flags checked; "
                f"equilibrium max relative error {coherent_run_factor_ldf['precision']['five_component_equilibrium_prefactor_max_relative_error']:.3e}; "
                f"LDF max relative error {coherent_run_factor_ldf['precision']['five_component_ldf_alpha_max_relative_error']:.3e}"
            ),
            "boundary": "finite 32-run coefficient-generation interface; downstream coefficient consumption is reported separately; dynamic pressure/composition denominator and reciprocal, off-ledger tank demand, adaptive integration, monolithic phase/cycle, routing and fault tolerance remain open",
        },
        {
            "tier": "coherent coefficient-to-LDF/loading/balance paths",
            "role": "run-generated equilibrium and LDF coefficients, supplied 20-bit competitive-Langmuir response, adsorption schedule mask, signed loading transfer, and one conservative gas balance for each component",
            "logical_qubits": coherent_coefficient_ldf_balance["conservative_five_component_upper_bound"]["logical_qubits_peak"],
            "compiled_basis_or_device": "all-to-all u/CX",
            "per_call_or_block_resource": (
                f"component paths {min(row['logical_qubits'] for row in coherent_coefficient_ldf_balance['componentwise_compiled_direct_paths']):,}–"
                f"{max(row['logical_qubits'] for row in coherent_coefficient_ldf_balance['componentwise_compiled_direct_paths']):,} q/"
                f"{min(row['cx'] for row in coherent_coefficient_ldf_balance['componentwise_compiled_direct_paths']):,}–"
                f"{max(row['cx'] for row in coherent_coefficient_ldf_balance['componentwise_compiled_direct_paths']):,} CX"
            ),
            "schedule_or_aggregate_resource": (
                f"{coherent_coefficient_ldf_balance['conservative_five_component_upper_bound']['logical_qubits_peak']:,} peak q/"
                f"{coherent_coefficient_ldf_balance['conservative_five_component_upper_bound']['cx_additive_upper_bound']:,} additive CX; "
                f"depth {coherent_coefficient_ldf_balance['conservative_five_component_upper_bound']['depth_all_to_all_additive_upper_bound']:,}; "
                "five separately transpiled paths, no measurement or reset"
            ),
            "accuracy_or_observation": (
                f"{coherent_coefficient_ldf_balance['support']['component_balance_records_checked']:,} component balances; "
                f"q* max ≤{max(row['qstar_max_loading_scale_normalized_absolute_error'] for row in coherent_coefficient_ldf_balance['components']):.3e}; "
                f"LDF-next max ≤{max(row['ldf_next_max_loading_scale_normalized_absolute_error'] for row in coherent_coefficient_ldf_balance['components']):.3e}; "
                f"next-gas max ≤{max(row['next_gas_max_scale_normalized_absolute_error'] for row in coherent_coefficient_ldf_balance['components']):.3e}; zero quantized-transfer erasure"
            ),
            "boundary": "controller-generated coefficients are consumed in schedule-gated component state-update paths with a supplied 20-bit Langmuir response; dynamic affinity denominator/reciprocal generation, gas normalization, face generation, off-ledger tank demand, monolithic five-component phase/cycle, routing and fault tolerance remain open",
        },
        {
            "tier": "coherent dynamic-Langmuir-to-LDF/loading/balance paths",
            "role": "run-generated affinity-dependent Langmuir denominator/reciprocal from supplied 20-bit pressure and five compositions, followed by generated q*, schedule-masked LDF uptake, signed loading transfer, and one conservative gas balance per component",
            "logical_qubits": coherent_dynamic_langmuir_ldf_balance["conservative_five_component_upper_bound"]["logical_qubits_peak"],
            "compiled_basis_or_device": "all-to-all u/CX",
            "per_call_or_block_resource": (
                f"component paths {min(row['logical_qubits'] for row in coherent_dynamic_langmuir_ldf_balance['componentwise_compiled_direct_paths']):,}–"
                f"{max(row['logical_qubits'] for row in coherent_dynamic_langmuir_ldf_balance['componentwise_compiled_direct_paths']):,} q/"
                f"{min(row['cx'] for row in coherent_dynamic_langmuir_ldf_balance['componentwise_compiled_direct_paths']):,}–"
                f"{max(row['cx'] for row in coherent_dynamic_langmuir_ldf_balance['componentwise_compiled_direct_paths']):,} CX"
            ),
            "schedule_or_aggregate_resource": (
                f"{coherent_dynamic_langmuir_ldf_balance['conservative_five_component_upper_bound']['logical_qubits_peak']:,} peak q/"
                f"{coherent_dynamic_langmuir_ldf_balance['conservative_five_component_upper_bound']['cx_additive_upper_bound']:,} additive CX; "
                f"depth {coherent_dynamic_langmuir_ldf_balance['conservative_five_component_upper_bound']['depth_all_to_all_additive_upper_bound']:,}; "
                "five separately transpiled paths, no measurement or reset"
            ),
            "accuracy_or_observation": (
                f"{coherent_dynamic_langmuir_ldf_balance['support']['component_balance_records_checked']:,} component balances; "
                f"denominator p95/max {coherent_dynamic_langmuir_ldf_balance['selected_dynamic_response_design']['denominator_p95_absolute_error']:.3e}/"
                f"{coherent_dynamic_langmuir_ldf_balance['selected_dynamic_response_design']['denominator_max_absolute_error']:.3e}; "
                f"q* max ≤{max(row['qstar_max_loading_scale_normalized_absolute_error'] for row in coherent_dynamic_langmuir_ldf_balance['components']):.3e}; "
                f"next-gas max ≤{max(row['next_gas_max_scale_normalized_absolute_error'] for row in coherent_dynamic_langmuir_ldf_balance['components']):.3e}"
            ),
            "boundary": "pressure and five composition words are supplied; gas normalization, face generation, off-ledger tank demand, monolithic five-component phase/cycle, adaptive integration, routing, hardware feasibility, external H2 validation, and quantum advantage remain open",
        },
        {
            "tier": "coherent gas-inventory-to-dynamic-Langmuir/transport/LDF/balance paths",
            "role": "three raw five-component gas inventories generate two normalized compositions, three pressures, two oriented faces, a controller-coupled dynamic Langmuir response, schedule-masked LDF uptake, signed loading transfer, and one conservative gas balance per component",
            "logical_qubits": coherent_normalized_dynamic_transport_ldf_balance["conservative_five_component_upper_bound"]["logical_qubits_peak"],
            "compiled_basis_or_device": "all-to-all u/CX",
            "per_call_or_block_resource": (
                f"component paths {min(row['logical_qubits'] for row in coherent_normalized_dynamic_transport_ldf_balance['componentwise_compiled_direct_paths']):,}–"
                f"{max(row['logical_qubits'] for row in coherent_normalized_dynamic_transport_ldf_balance['componentwise_compiled_direct_paths']):,} q/"
                f"{min(row['cx'] for row in coherent_normalized_dynamic_transport_ldf_balance['componentwise_compiled_direct_paths']):,}–"
                f"{max(row['cx'] for row in coherent_normalized_dynamic_transport_ldf_balance['componentwise_compiled_direct_paths']):,} CX"
            ),
            "schedule_or_aggregate_resource": (
                f"{coherent_normalized_dynamic_transport_ldf_balance['conservative_five_component_upper_bound']['logical_qubits_peak']:,} peak q/"
                f"{coherent_normalized_dynamic_transport_ldf_balance['conservative_five_component_upper_bound']['cx_additive_upper_bound']:,} additive CX; "
                f"depth {coherent_normalized_dynamic_transport_ldf_balance['conservative_five_component_upper_bound']['depth_all_to_all_additive_upper_bound']:,}; "
                "five separately transpiled paths, no measurement or reset"
            ),
            "accuracy_or_observation": (
                f"{coherent_normalized_dynamic_transport_ldf_balance['support']['normalization_states']:,} normalization states and "
                f"{coherent_normalized_dynamic_transport_ldf_balance['support']['component_balance_records_checked']:,} component balances; "
                f"q* max ≤{max(row['qstar_max_loading_scale_normalized_absolute_error'] for row in coherent_normalized_dynamic_transport_ldf_balance['components']):.3e}; "
                f"next-gas max ≤{max(row['next_gas_max_scale_normalized_absolute_error'] for row in coherent_normalized_dynamic_transport_ldf_balance['components']):.3e}"
            ),
            "boundary": "normalization and orientation are calibrated to the frozen support; negative-flow switching outside that support, continuous off-ledger tank demand, monolithic five-component phase/cycle, adaptive integration, routing, hardware feasibility, external H2 validation, and quantum advantage remain open",
        },
        {
            "tier": "pressure-derived saturated tank-withdrawal interface",
            "role": "five raw endpoint gas inventories generate end pressure and a conservative phase-demand proxy, which is compared with five-component tank inventory before clean saturated withdrawal and componentwise subtraction",
            "logical_qubits": offledger_tank_saturation["compiled_clean_circuit"]["logical_qubits"],
            "compiled_basis_or_device": "all-to-all u/CX",
            "per_call_or_block_resource": (
                f"{offledger_tank_saturation['compiled_clean_circuit']['logical_qubits']:,} q/"
                f"{offledger_tank_saturation['compiled_clean_circuit']['cx']:,} CX; "
                f"depth {offledger_tank_saturation['compiled_clean_circuit']['depth_all_to_all']:,}"
            ),
            "schedule_or_aggregate_resource": "128 final-cycle tank calls verified; the recorded-withdrawal QROM is unnecessary on the saturated support branch",
            "accuracy_or_observation": (
                f"{offledger_tank_saturation['selected_design']['encoded_saturated_records']}/128 encoded saturation labels; "
                f"minimum pressure-bound margin {offledger_tank_saturation['selected_design']['minimum_lower_bound_minus_tank_mol']:.6f} mol; "
                f"p95 aggregate normalized error {offledger_tank_saturation['selected_design']['all_output_p95_scale_normalized_absolute_error']:.3e}; "
                "zero flag mismatch, lower-bound violation, underflow or meaningful erasure"
            ),
            "boundary": "all frozen calls are demand-saturated; unsaturated proportional allocation, phase-end state generation inside a monolithic phase unitary, adaptive integration, routing, external H2 validation, and quantum advantage remain open",
        },
        {
            "tier": "pressure-derived saturated/unsaturated proportional tank-allocation interface",
            "role": "five raw endpoint gas inventories generate demand, compare it with tank total, select full-tank withdrawal on saturation or demand-proportional five-component withdrawal otherwise, subtract the selected withdrawal, and exactly reverse all work",
            "logical_qubits": offledger_tank_proportional["compiled_clean_circuit"]["logical_qubits"],
            "compiled_basis_or_device": "all-to-all u/CX",
            "per_call_or_block_resource": (
                f"{offledger_tank_proportional['compiled_clean_circuit']['logical_qubits']:,} q/"
                f"{offledger_tank_proportional['compiled_clean_circuit']['cx']:,} CX; "
                f"depth {offledger_tank_proportional['compiled_clean_circuit']['depth_all_to_all']:,}"
            ),
            "schedule_or_aggregate_resource": (
                f"{offledger_tank_proportional['support']['observed_frozen_final_cycle_records']} observed saturated calls plus "
                f"{offledger_tank_proportional['support']['counterfactual_arithmetic_records']} bounded unsaturated arithmetic cases; "
                f"{offledger_tank_proportional['selected_design']['reciprocal_segments']} reciprocal segments"
            ),
            "accuracy_or_observation": (
                f"{offledger_tank_proportional['selected_design']['encoded_saturated_records']} saturated/"
                f"{offledger_tank_proportional['selected_design']['encoded_unsaturated_records']} unsaturated labels; "
                f"withdrawal/next p95 {offledger_tank_proportional['selected_design']['withdrawal_and_next_p95_component_scale_normalized_absolute_error']:.3e}, "
                f"max {offledger_tank_proportional['selected_design']['withdrawal_and_next_max_component_scale_normalized_absolute_error']:.3e}; "
                "zero flag mismatch, fraction overflow, underflow, or meaningful erasure"
            ),
            "boundary": "unsaturated coverage is a declared bounded pressure counterfactual over observed tank compositions, not a physical trajectory or plant validation; out-of-domain reciprocal behavior, monolithic five-component phase/cycle generation, adaptive integration, routing, external H2 validation, and quantum advantage remain open",
        },
        {
            "tier": "model-derived physical unsaturated tank-trajectory control",
            "role": "a source-model short-schedule trajectory supplies start/end gas inventories, integrated demand, and five-component tank withdrawals to a clean two-pressure proportional-allocation circuit",
            "logical_qubits": physical_unsaturated_tank["compiled_clean_circuit"]["logical_qubits"],
            "compiled_basis_or_device": "all-to-all u/CX",
            "per_call_or_block_resource": (
                f"{physical_unsaturated_tank['compiled_clean_circuit']['logical_qubits']:,} q/"
                f"{physical_unsaturated_tank['compiled_clean_circuit']['cx']:,} CX; "
                f"depth {physical_unsaturated_tank['compiled_clean_circuit']['depth_all_to_all']:,}"
            ),
            "schedule_or_aggregate_resource": (
                f"{physical_unsaturated_tank['trajectory']['tank_calls']} replayed tank calls over "
                f"{physical_unsaturated_tank['trajectory']['replayed_cycles']} final cycles; "
                f"{physical_unsaturated_tank['trajectory']['non_adsorption_duration_s']:.2f}-s non-adsorption control"
            ),
            "accuracy_or_observation": (
                f"{physical_unsaturated_tank['trajectory']['unsaturated_calls']}/"
                f"{physical_unsaturated_tank['trajectory']['tank_calls']} physical unsaturated and zero-makeup calls; "
                f"trapezoid-demand p95 relative error {physical_unsaturated_tank['pressure_demand_diagnostics']['trapezoid_proxy_p95_relative_error']:.3%}; "
                f"withdrawal/next p95 {physical_unsaturated_tank['selected_design']['withdrawal_and_next_p95_component_scale_normalized_absolute_error']:.3e}, "
                f"max {physical_unsaturated_tank['selected_design']['withdrawal_and_next_max_component_scale_normalized_absolute_error']:.3e}"
            ),
            "boundary": "same sample-0 recycle fraction but a declared 0.02-s rather than frozen 10-s non-adsorption schedule; one model-derived trajectory, not plant calibration, the frozen-policy trajectory, monolithic phase integration, routing, hardware feasibility, external H2 validation, or quantum advantage",
        },
        {
            "tier": "pressure reconstruction and oriented internal-face transport",
            "role": "five gas inventories to pressure, then reconstructed pressure difference and supplied upwind composition to five one-second component transfers",
            "logical_qubits": internal_transport["pressure_to_face_modular_accounting"]["logical_qubits"],
            "compiled_basis_or_device": "all-to-all u/CX",
            "per_call_or_block_resource": (
                f"pressure {internal_transport['compiled_clean_pressure_reconstruction']['logical_qubits']} q/"
                f"{internal_transport['compiled_clean_pressure_reconstruction']['cx']:,} CX; "
                f"face {internal_transport['compiled_clean_oriented_internal_face_transport']['logical_qubits']} q/"
                f"{internal_transport['compiled_clean_oriented_internal_face_transport']['cx']:,} CX"
            ),
            "schedule_or_aggregate_resource": (
                f"two pressure modules plus one face module: "
                f"{internal_transport['pressure_to_face_modular_accounting']['logical_qubits']} q/"
                f"{internal_transport['pressure_to_face_modular_accounting']['cx_additive_module_bound']:,} additive CX"
            ),
            "accuracy_or_observation": (
                f"{internal_transport['physical_state_source']['cell_states']:,} cell states and "
                f"{internal_transport['physical_state_source']['internal_faces']:,} faces; "
                f"active-flow p95 relative error {internal_transport['selected_face']['active_flow_p95_relative_error']:.5f}; "
                "all declared pressure/flow/flux gates pass"
            ),
            "boundary": "locally oriented physical support; composition normalization and negative-flow switching beyond that support are open; direct two-face accumulation is reported in the next tier, while LDF coupling, adaptive integration, routing and full phase/cycle remain open",
        },
        {
            "tier": "direct pressure-to-two-face-to-interior-cell balance",
            "role": "three encoded cell inventories through pressure reconstruction and two five-component internal-face transfers into five conservative centre-cell next-gas inventories with exact transport-work reversal",
            "logical_qubits": internal_face_balance["compiled_clean_internal_face_balance"]["logical_qubits"],
            "compiled_basis_or_device": "all-to-all u/CX",
            "per_call_or_block_resource": (
                f"one five-component clean circuit: "
                f"{internal_face_balance['compiled_clean_internal_face_balance']['logical_qubits']:,} q/"
                f"{internal_face_balance['compiled_clean_internal_face_balance']['cx']:,} CX; "
                f"depth {internal_face_balance['compiled_clean_internal_face_balance']['depth_all_to_all']:,}"
            ),
            "schedule_or_aggregate_resource": "single directly transpiled 3-pressure/2-face/interior-balance circuit; not an additive module estimate",
            "accuracy_or_observation": (
                f"{internal_face_balance['physical_state_source']['interior_cell_states']:,} interior-cell states and "
                f"{internal_face_balance['physical_state_source']['component_balances']:,} component balances; "
                "all five propagated inventory and arithmetic-only precision/erasure/overflow gates pass"
            ),
            "boundary": "two supplied upwind-composition registers and nonface balance inputs remain; normalization, negative-flow switching outside the cached orientation, direct centre-cell LDF/loading coupling, run-specific parameters, tank withdrawal, integration, routing and full cycle remain open",
        },
        {
            "tier": "direct gas-normalization-to-two-face-to-interior-cell balance",
            "role": "three encoded cell inventories through two reversible mole-fraction normalizers, three pressure reconstructions, and two internal faces into five conservative centre-cell next-gas inventories with exact work reversal",
            "logical_qubits": normalized_internal_face_balance["compiled_clean_normalized_internal_face_balance"]["logical_qubits"],
            "compiled_basis_or_device": "all-to-all u/CX",
            "per_call_or_block_resource": (
                f"one five-component clean circuit: "
                f"{normalized_internal_face_balance['compiled_clean_normalized_internal_face_balance']['logical_qubits']:,} q/"
                f"{normalized_internal_face_balance['compiled_clean_normalized_internal_face_balance']['cx']:,} CX; "
                f"depth {normalized_internal_face_balance['compiled_clean_normalized_internal_face_balance']['depth_all_to_all']:,}; "
                f"standalone normalizer {normalized_internal_face_balance['compiled_clean_composition_normalizer']['logical_qubits']:,} q/"
                f"{normalized_internal_face_balance['compiled_clean_composition_normalizer']['cx']:,} CX"
            ),
            "schedule_or_aggregate_resource": "single directly transpiled 2-normalizer/3-pressure/2-face/interior-balance circuit; not an additive module estimate",
            "accuracy_or_observation": (
                f"{normalized_internal_face_balance['physical_state_source']['normalization_cell_states']:,} normalization states and "
                f"{normalized_internal_face_balance['physical_state_source']['component_balances']:,} component balances; "
                f"maximum composition p95 absolute error {max(normalized_internal_face_balance['selected_normalization']['composition_p95_absolute_error'].values()):.3e}; "
                "all normalization, propagated face, and five inventory gates pass"
            ),
            "boundary": "support-adaptive reciprocal thresholds are calibrated to the frozen left/centre-cell domain; nonface balance inputs remain supplied; out-of-support normalization, negative-flow switching, centre-cell LDF/loading coupling, run-specific parameters, tank withdrawal, integration, routing and full cycle remain open",
        },
        {
            "tier": "direct LDF-to-loading-sign-to-cell-balance composition",
            "role": "widened competitive-Langmuir/LDF output joined through loading-sign extraction and solid conversion to conservative next gas",
            "logical_qubits": ldf_sign_balance["sequential_five_component_accounting"]["logical_qubits"],
            "compiled_basis_or_device": "all-to-all u/CX",
            "per_call_or_block_resource": (
                f"clean directly composed modules {min(row['compiled_clean_ldf_sign_cell_balance']['logical_qubits'] for row in ldf_sign_balance['components'])}–"
                f"{max(row['compiled_clean_ldf_sign_cell_balance']['logical_qubits'] for row in ldf_sign_balance['components'])} q/"
                f"{min(row['compiled_clean_ldf_sign_cell_balance']['cx'] for row in ldf_sign_balance['components']):,}–"
                f"{max(row['compiled_clean_ldf_sign_cell_balance']['cx'] for row in ldf_sign_balance['components']):,} CX"
            ),
            "schedule_or_aggregate_resource": (
                f"five-component direct-composition accounting {ldf_sign_balance['sequential_five_component_accounting']['logical_qubits']:,} q/"
                f"{ldf_sign_balance['sequential_five_component_accounting']['cx_additive_module_bound']:,} additive CX; "
                f"loading-sign/balance interface alone {loading_sign_balance['sequential_five_component_accounting']['logical_qubits']:,} q/"
                f"{loading_sign_balance['sequential_five_component_accounting']['cx_additive_module_bound']:,} additive CX"
            ),
            "accuracy_or_observation": (
                f"{ldf_sign_balance['physical_state_source']['ldf_precision_cell_states']:,} LDF precision states and "
                f"{ldf_sign_balance['physical_state_source']['balance_interface_component_samples']:,} component balances; "
                f"loading bits {','.join(str(row['selected']['loading_bits']) for row in loading_sign_balance['components'])}; "
                "all widened LDF and downstream interface gates pass"
            ),
            "boundary": "LDF arithmetic remains constant-specialized; a direct pressure/face/balance circuit is a separate tier, while joint LDF-plus-face composition, normalization, reversible run-specific parameters, boundary withdrawal, adaptive integration, routing and full phase/cycle remain open",
        },
        {
            "tier": "direct normalized-transport/LDF/interior-balance paths",
            "role": "shared gas inventories generate normalized compositions, pressures, two internal faces, and centre-cell LDF uptake before one conservative component balance and exact work reversal",
            "logical_qubits": joint_normalized_transport_ldf_balance["compiled_clean_joint_specialized_circuit"]["logical_qubits_peak"],
            "compiled_basis_or_device": "all-to-all u/CX",
            "per_call_or_block_resource": (
                f"five directly connected component paths "
                f"{min(row['logical_qubits'] for row in joint_normalized_transport_ldf_balance['componentwise_compiled_direct_paths']):,}–"
                f"{max(row['logical_qubits'] for row in joint_normalized_transport_ldf_balance['componentwise_compiled_direct_paths']):,} q/"
                f"{min(row['cx'] for row in joint_normalized_transport_ldf_balance['componentwise_compiled_direct_paths']):,}–"
                f"{max(row['cx'] for row in joint_normalized_transport_ldf_balance['componentwise_compiled_direct_paths']):,} CX"
            ),
            "schedule_or_aggregate_resource": (
                f"common-path-repeating conservative upper bound "
                f"{joint_normalized_transport_ldf_balance['compiled_clean_joint_specialized_circuit']['logical_qubits_peak']:,} peak q/"
                f"{joint_normalized_transport_ldf_balance['compiled_clean_joint_specialized_circuit']['cx_additive_upper_bound']:,} additive CX; "
                "monolithic five-component transpilation not completed"
            ),
            "accuracy_or_observation": (
                f"{joint_normalized_transport_ldf_balance['physical_state_source']['interior_cell_states']:,} interior states and "
                f"{joint_normalized_transport_ldf_balance['physical_state_source']['component_balances']:,} balances; "
                f"selected p95 next-gas errors "
                f"{min(row['next_p95_scale_normalized_absolute_error'] for row in joint_normalized_transport_ldf_balance['selected_components']):.3e}–"
                f"{max(row['next_p95_scale_normalized_absolute_error'] for row in joint_normalized_transport_ldf_balance['selected_components']):.3e}; "
                "all five gates pass"
            ),
            "boundary": "32 factor-quantized parameter-specialized paths on frozen support; one coherent scenario-parameter register, monolithic five-component transpilation, out-of-support switching, boundary/tank withdrawal, integration, routing, and full cycle remain open",
        },
        {
            "tier": "IBM finite-oracle preflight",
            "role": "device-target compilation without submission",
            "logical_qubits": 5,
            "compiled_basis_or_device": "ibm_marrakesh target",
            "per_call_or_block_resource": f"m=8: {int(preflight_m8['two_qubit_median']):,} CZ; depth {int(preflight_m8['depth_median']):,}",
            "schedule_or_aggregate_resource": "no sampler/job/QPU charge",
            "accuracy_or_observation": "three transpiler seeds agree",
            "boundary": "preflight only",
        },
        {
            "tier": "real-QPU three-qubit event",
            "role": "amplification-noise boundary",
            "logical_qubits": 3,
            "compiled_basis_or_device": f"{qpu['backend']}",
            "per_call_or_block_resource": f"max circuit {qpu_max['two_qubit_instructions']} CZ; depth {qpu_max['depth']}",
            "schedule_or_aggregate_resource": f"{qpu['runtime_metrics']['usage']['qpu_charge_time_seconds']} s QPU charge; {qpu['runtime_metrics']['usage']['value']} RU",
            "accuracy_or_observation": f"p-hat {qpu['estimate']['estimate']:.6f}; absolute error {qpu['estimate']['absolute_error']:.6f}",
            "boundary": "one backend and one job; ideal likelihood interval is not noise calibrated",
        },
    ]
    payload = {
        "schema": "psa-qae-cce-resource-table3/v1",
        "status": "main_text_resource_ladder_assembled_open_end_to_end_gates_disclosed",
        "source_files": [
            path.name
            for path in [
                LINEAR,
                LOADER,
                PHASE_SCREEN,
                PHASE_COMPILE,
                PRIMARY_PHASE_LEDGER,
                PRIMARY_EVENT_BRIDGE,
                PRIMARY_EVENT_SCREEN,
                PRIMARY_EVENT_COMPILE,
                PRIMARY_FINAL_EVENT,
                PRIMARY_POLICY_STREAM_EVENT,
                CSS_INITIALIZER_BRIDGE,
                CSS_INITIALIZER_SCREEN,
                CSS_INITIALIZER_COMPILE,
                SMALL_E2E,
                FINITE,
                IBM_PREFLIGHT,
                QPU,
                ALL_COMPONENT_LDF,
                PRODUCT_BOUNDARY,
                PRODUCT_BOUNDARY_BALANCE,
                PRODUCT_LDF_VALVE_BALANCE,
                NORMALIZED_PRODUCT_LDF_VALVE_BALANCE,
                COHERENT_RUN_SCHEDULE_TANK,
                COHERENT_RUN_FACTOR_LDF,
                COHERENT_COEFFICIENT_LDF_BALANCE,
                COHERENT_DYNAMIC_LANGMUIR_LDF_BALANCE,
                OFFLEDGER_TANK_SATURATION,
                OFFLEDGER_TANK_PROPORTIONAL,
                PHYSICAL_UNSATURATED_TANK,
                INTERNAL_TRANSPORT,
                INTERNAL_FACE_BALANCE,
                NORMALIZED_INTERNAL_FACE_BALANCE,
                CELL_BALANCE,
                LOADING_SIGN_BALANCE,
                LDF_SIGN_BALANCE,
                JOINT_NORMALIZED_TRANSPORT_LDF_BALANCE,
            ]
        ],
        "rows": rows,
        "figure": OUT_PNG.name,
        "note": "Resources from different evidence tiers are not additive unless explicitly labelled as a schedule or aggregate. No end-to-end quantum speedup is claimed.",
    }
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with OUT_CSV.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    lines = [
        "# Table 3. Resource ladder from finite controls to calibrated phase maps",
        "",
        "| tier | role | logical qubits | basis/device | per call or block | schedule/aggregate | accuracy/observation | boundary |",
        "|---|---|---:|---|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                str(row[key])
                for key in [
                    "tier",
                    "role",
                    "logical_qubits",
                    "compiled_basis_or_device",
                    "per_call_or_block_resource",
                    "schedule_or_aggregate_resource",
                    "accuracy_or_observation",
                    "boundary",
                ]
            )
            + " |"
        )
    lines += ["", payload["note"], "", f"Main-text figure: {OUT_PNG.name}."]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"status": payload["status"], "rows": len(rows), "figure": OUT_PNG.name}, indent=2))


if __name__ == "__main__":
    main()
