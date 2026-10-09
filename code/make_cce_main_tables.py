"""Assemble CCE Tables 1, 2, and 4 from authoritative project artifacts."""

from __future__ import annotations

import csv
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RESULTS = ROOT / "10_TEA_LCA_Python" / "results" / "pycharm_publication_enhancement"

PROTOCOL = RESULTS / "PSA_QAE_CCE_PRIMARY_CASE_PROTOCOL.json"
ESTIMATORS = RESULTS / "PSA_QAE_CONTINUOUS_POLICY_SELECTION.json"
PHASE_MAP = RESULTS / "PSA_QAE_CCE_CALIBRATED_ONE_CYCLE_PHASE_MAP.json"
PHASE_LEDGER = RESULTS / "PSA_QAE_DIRECT_PHYSICAL_PHASE_LEDGER.json"
PRIMARY_PHASE_LEDGER = RESULTS / "PSA_QAE_CCE_PRIMARY_PHASE_LEDGER.json"
PRIMARY_PHYSICAL_CSS = RESULTS / "PSA_QAE_CCE_PRIMARY_PHYSICAL_CSS_HORIZON_AUDIT.json"
PRIMARY_QSTAR_MICROKERNEL = RESULTS / "PSA_QAE_CCE_PRIMARY_QSTAR_REVERSIBLE_MICROKERNEL.json"
PRIMARY_QSTAR_LDF_MICROSTEP = RESULTS / "PSA_QAE_CCE_PRIMARY_QSTAR_LDF_REVERSIBLE_MICROSTEP.json"
PRIMARY_ALL_COMPONENT_LDF = RESULTS / "PSA_QAE_CCE_PRIMARY_ALL_COMPONENT_LDF_MICROSTEPS.json"
PRIMARY_PRODUCT_BOUNDARY = RESULTS / "PSA_QAE_CCE_PRIMARY_PRODUCT_BOUNDARY_MICROSTEPS.json"
PRIMARY_PRODUCT_BOUNDARY_BALANCE = RESULTS / "PSA_QAE_CCE_PRIMARY_PRODUCT_BOUNDARY_BALANCE_COMPOSITION.json"
PRIMARY_PRODUCT_LDF_VALVE_BALANCE = RESULTS / "PSA_QAE_CCE_PRIMARY_PRODUCT_LDF_VALVE_BALANCE_COMPOSITION.json"
PRIMARY_NORMALIZED_PRODUCT_LDF_VALVE_BALANCE = RESULTS / "PSA_QAE_CCE_PRIMARY_NORMALIZED_PRODUCT_LDF_VALVE_BALANCE.json"
PRIMARY_COHERENT_RUN_SCHEDULE_TANK = RESULTS / "PSA_QAE_CCE_COHERENT_RUN_SCHEDULE_TANK_INTERFACE.json"
PRIMARY_COHERENT_RUN_FACTOR_LDF = RESULTS / "PSA_QAE_CCE_COHERENT_RUN_FACTOR_LDF_INTERFACE.json"
PRIMARY_COHERENT_COEFFICIENT_LDF_BALANCE = RESULTS / "PSA_QAE_CCE_COHERENT_COEFFICIENT_LDF_BALANCE_INTERFACE.json"
PRIMARY_COHERENT_DYNAMIC_LANGMUIR_LDF_BALANCE = RESULTS / "PSA_QAE_CCE_COHERENT_DYNAMIC_LANGMUIR_LDF_BALANCE_INTERFACE.json"
PRIMARY_COHERENT_NORMALIZED_DYNAMIC_TRANSPORT_LDF_BALANCE = RESULTS / "PSA_QAE_CCE_COHERENT_NORMALIZED_DYNAMIC_TRANSPORT_LDF_BALANCE.json"
PRIMARY_OFFLEDGER_TANK_SATURATION = RESULTS / "PSA_QAE_CCE_OFFLEDGER_TANK_SATURATION_INTERFACE.json"
PRIMARY_OFFLEDGER_TANK_PROPORTIONAL = RESULTS / "PSA_QAE_CCE_OFFLEDGER_TANK_PROPORTIONAL_INTERFACE.json"
PRIMARY_PHYSICAL_UNSATURATED_TANK = RESULTS / "PSA_QAE_CCE_PHYSICAL_UNSATURATED_TANK_TRAJECTORY.json"
PRIMARY_INTERNAL_TRANSPORT = RESULTS / "PSA_QAE_CCE_PRIMARY_INTERNAL_TRANSPORT_MICROSTEPS.json"
PRIMARY_INTERNAL_FACE_BALANCE = RESULTS / "PSA_QAE_CCE_PRIMARY_INTERNAL_FACE_BALANCE_COMPOSITION.json"
PRIMARY_NORMALIZED_INTERNAL_FACE_BALANCE = RESULTS / "PSA_QAE_CCE_PRIMARY_COMPOSITION_NORMALIZED_INTERNAL_FACE_BALANCE.json"
PRIMARY_CELL_BALANCE = RESULTS / "PSA_QAE_CCE_PRIMARY_CELL_BALANCE_MICROSTEPS.json"
PRIMARY_LOADING_SIGN_BALANCE = RESULTS / "PSA_QAE_CCE_PRIMARY_LOADING_SIGN_BALANCE_INTERFACE.json"
PRIMARY_LDF_SIGN_BALANCE = RESULTS / "PSA_QAE_CCE_PRIMARY_LDF_SIGN_BALANCE_COMPOSITION.json"
PRIMARY_JOINT_NORMALIZED_TRANSPORT_LDF_BALANCE = RESULTS / "PSA_QAE_CCE_PRIMARY_JOINT_NORMALIZED_TRANSPORT_LDF_BALANCE.json"
PRIMARY_EVENT_BRIDGE = RESULTS / "PSA_QAE_CCE_PRIMARY_PHASE_EVENT_BRIDGE.json"
PRIMARY_FINAL_EVENT = RESULTS / "PSA_QAE_CCE_PRIMARY_FINAL_EVENT_ARITHMETIC.json"
PRIMARY_POLICY_STREAM_EVENT = RESULTS / "PSA_QAE_CCE_PRIMARY_POLICY_STREAM_EVENT_ORACLE.json"
CSS_INITIALIZER_BRIDGE = RESULTS / "PSA_QAE_CCE_PRIMARY_CSS_INITIALIZER_EVENT_BRIDGE.json"
CSS_INITIALIZER_REPEATED = RESULTS / "PSA_QAE_CCE_PRIMARY_CSS_INITIALIZER_REPEATED_CYCLE_SCREEN.json"
CSS_INITIALIZER_STABILITY = RESULTS / "PSA_QAE_CCE_PRIMARY_CSS_INITIALIZER_SPECTRAL_STABILITY_SCREEN.json"
EMPIRICAL = RESULTS / "PSA_QAE_EMPIRICAL_VALVE_TANK_PRODUCT_CALIBRATION.json"
EXTERNAL = RESULTS / "PSA_QAE_CCE_EXTERNAL_LIGHT_PRODUCT_POLICY_VALIDATION.json"
THELEN = RESULTS / "PSA_QAE_CCE_INDEPENDENT_H2_EQUALIZATION_CONTROL.json"
PYAPEP = RESULTS / "PSA_QAE_CCE_INDEPENDENT_PYAPEP_H2_RECYCLE_VALIDATION.json"
H2_RESOLUTION = RESULTS / "PSA_QAE_CCE_INDEPENDENT_H2_POLICY_RESOLUTION_AUDIT.json"
TOPSAIL_YANG = RESULTS / "PSA_QAE_CCE_TOPSAIL_YANG_H2_PUBLIC_MODEL_AUDIT.json"
QPU = RESULTS / "QAE_QPU_BREAKTHROUGH_PHASE_MLAE_IBM_db42v34lf4us73c24q50.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_table(stem: str, schema: str, status: str, sources: list[Path], rows: list[dict], title: str) -> None:
    json_path = RESULTS / f"{stem}.json"
    csv_path = RESULTS / f"{stem}.csv"
    md_path = RESULTS / f"{stem}.md"
    payload = {
        "schema": schema,
        "status": status,
        "source_files": [path.name for path in sources],
        "rows": rows,
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with csv_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    headers = list(rows[0])
    lines = [f"# {title}", "", "| " + " | ".join(headers) + " |", "|" + "|".join("---:" if header.endswith(("rmse", "mae", "bias", "fraction", "seconds", "evaluations")) else "---" for header in headers) + "|"]
    for row in rows:
        values = [str(row[header]).replace("|", "/") for header in headers]
        lines.append("| " + " | ".join(values) + " |")
    lines += ["", f"Sources: {', '.join(payload['source_files'])}."]
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    protocol = load(PROTOCOL)
    estimators = load(ESTIMATORS)
    phase_map = load(PHASE_MAP)
    phase_ledger = load(PHASE_LEDGER)
    primary_phase_ledger = load(PRIMARY_PHASE_LEDGER)
    primary_physical_css = load(PRIMARY_PHYSICAL_CSS)
    primary_qstar_microkernel = load(PRIMARY_QSTAR_MICROKERNEL)
    primary_qstar_ldf_microstep = load(PRIMARY_QSTAR_LDF_MICROSTEP)
    primary_all_component_ldf = load(PRIMARY_ALL_COMPONENT_LDF)
    primary_product_boundary = load(PRIMARY_PRODUCT_BOUNDARY)
    primary_product_boundary_balance = load(PRIMARY_PRODUCT_BOUNDARY_BALANCE)
    primary_product_ldf_valve_balance = load(PRIMARY_PRODUCT_LDF_VALVE_BALANCE)
    primary_normalized_product_ldf_valve_balance = load(
        PRIMARY_NORMALIZED_PRODUCT_LDF_VALVE_BALANCE
    )
    primary_coherent_run_schedule_tank = load(PRIMARY_COHERENT_RUN_SCHEDULE_TANK)
    primary_coherent_run_factor_ldf = load(PRIMARY_COHERENT_RUN_FACTOR_LDF)
    primary_coherent_coefficient_ldf_balance = load(PRIMARY_COHERENT_COEFFICIENT_LDF_BALANCE)
    primary_coherent_dynamic_langmuir_ldf_balance = load(PRIMARY_COHERENT_DYNAMIC_LANGMUIR_LDF_BALANCE)
    primary_coherent_normalized_dynamic_transport_ldf_balance = load(PRIMARY_COHERENT_NORMALIZED_DYNAMIC_TRANSPORT_LDF_BALANCE)
    primary_offledger_tank_saturation = load(PRIMARY_OFFLEDGER_TANK_SATURATION)
    primary_offledger_tank_proportional = load(PRIMARY_OFFLEDGER_TANK_PROPORTIONAL)
    primary_physical_unsaturated_tank = load(PRIMARY_PHYSICAL_UNSATURATED_TANK)
    primary_internal_transport = load(PRIMARY_INTERNAL_TRANSPORT)
    primary_internal_face_balance = load(PRIMARY_INTERNAL_FACE_BALANCE)
    primary_normalized_internal_face_balance = load(PRIMARY_NORMALIZED_INTERNAL_FACE_BALANCE)
    primary_cell_balance = load(PRIMARY_CELL_BALANCE)
    primary_loading_sign_balance = load(PRIMARY_LOADING_SIGN_BALANCE)
    primary_ldf_sign_balance = load(PRIMARY_LDF_SIGN_BALANCE)
    primary_joint_normalized_transport_ldf_balance = load(
        PRIMARY_JOINT_NORMALIZED_TRANSPORT_LDF_BALANCE
    )
    primary_event_bridge = load(PRIMARY_EVENT_BRIDGE)
    primary_final_event = load(PRIMARY_FINAL_EVENT)
    primary_policy_stream_event = load(PRIMARY_POLICY_STREAM_EVENT)
    css_initializer_bridge = load(CSS_INITIALIZER_BRIDGE)
    css_initializer_repeated = load(CSS_INITIALIZER_REPEATED)
    css_initializer_stability = load(CSS_INITIALIZER_STABILITY)
    empirical = load(EMPIRICAL)
    external = load(EXTERNAL)
    thelen = load(THELEN)
    pyapep = load(PYAPEP)
    h2_resolution = load(H2_RESOLUTION)
    topsail_yang = load(TOPSAIL_YANG)
    qpu = load(QPU)

    outer = protocol["outer_decision"]
    prior = protocol["uncertainty_prior"]
    table1 = [
        {"item": "outer decision variable", "frozen specification": outer["variable"], "role": "finite classical policy layer"},
        {"item": "candidate policies", "frozen specification": "/".join(f"{value:.3f}" for value in outer["candidate_values"]), "role": "no adaptive policy insertion after results"},
        {"item": "policy rule", "frozen specification": f"largest recycle candidate with estimated event probability >= {protocol['chance_constraint_target']:.2f}", "role": "largest feasible candidate"},
        {"item": "inner event", "frozen specification": f"H2 product >= {protocol['inner_estimand']['purity_threshold']:.4f} AND external recovery proxy >= {protocol['inner_estimand']['recovery_threshold']:.3f}", "role": "shared by all estimators"},
        {"item": "chance target", "frozen specification": f"{protocol['chance_constraint_target']:.2f}", "role": "policy-feasibility threshold"},
        {"item": "conditional prior", "frozen specification": f"{prior['model']}; {prior['physical_design_rows']} fitted process rows; {len(prior['features'])} coordinates", "role": "conditional computational experiment, not a plant population"},
        {"item": "MC budget", "frozen specification": f"{protocol['estimators']['MC']['samples']:,} samples", "role": "crude Monte Carlo baseline"},
        {"item": "RQMC budget", "frozen specification": f"{protocol['estimators']['RQMC']['samples']:,} points; {protocol['estimators']['RQMC']['sequence']}", "role": "strong smooth-integrand classical baseline"},
        {"item": "IS budget", "frozen specification": f"{protocol['estimators']['IS']['samples']:,} samples; defensive three-component mixture", "role": "rare-event-oriented classical control"},
        {"item": "MLAE budget", "frozen specification": f"{protocol['estimators']['MLAE']['queries']:,} queries; powers {protocol['estimators']['MLAE']['powers']}; {protocol['estimators']['MLAE']['shots_per_power']} shots/power", "role": "noiseless primary amplitude-estimation comparator"},
        {"item": "allowed claim", "frozen specification": protocol["allowed_claim"], "role": "manuscript claim boundary"},
        {"item": "prohibited claims", "frozen specification": "; ".join(protocol["prohibited_claims"]), "role": "prevents industrial or speedup overstatement"},
    ]
    write_table(
        "PSA_QAE_CCE_TABLE1_FROZEN_PROTOCOL",
        "psa-qae-cce-table1-frozen-protocol/v1",
        "frozen_primary_protocol_tabulated",
        [PROTOCOL],
        table1,
        "Table 1. Frozen PSA chance-constrained decision protocol",
    )

    labels = {
        "MC_same_query": "MC",
        "Sobol_RQMC": "scrambled Sobol RQMC",
        "defensive_mixture_IS": "defensive-mixture IS",
        "MLAE_0.00": "noiseless MLAE",
    }
    summary = {row["method"]: row for row in estimators["method_summary"]}
    table2 = []
    for key in labels:
        row = summary[key]
        table2.append(
            {
                "method": labels[key],
                "evaluations": int(row["oracle_calls_or_samples"]),
                "rmse": f"{row['rmse_across_policy_estimates']:.6f}",
                "mae": f"{row['mae_across_policy_estimates']:.6f}",
                "bias": f"{row['bias_across_policy_estimates']:+.6f}",
                "classification error fraction": f"{row['probability_classification_error_fraction']:.6f}",
                "correct policy fraction": f"{row['correct_selection_fraction']:.3f}",
                "correct-policy Wilson 95%": f"[{row['correct_selection_wilson95'][0]:.3f}, {row['correct_selection_wilson95'][1]:.3f}]",
                "median local seconds": f"{row['median_wall_time_seconds_for_three_policies']:.6f}",
                "interpretation": (
                    "best observed RMSE and preferred present method"
                    if key == "Sobol_RQMC"
                    else "improves on crude MC but remains behind RQMC"
                    if key == "MLAE_0.00"
                    else "proposal is inefficient for this broad non-rare event"
                    if key == "defensive_mixture_IS"
                    else "reference classical sampling baseline"
                ),
            }
        )
    write_table(
        "PSA_QAE_CCE_TABLE2_MATCHED_ESTIMATORS",
        "psa-qae-cce-table2-matched-estimators/v1",
        "matched_primary_estimators_tabulated",
        [ESTIMATORS, PROTOCOL],
        table2,
        "Table 2. Matched estimator and policy-selection performance",
    )

    cycle = phase_map["cycle_summary"]
    empirical_sources = empirical["sources"]
    table4 = [
        {
            "evidence tier": "primary spatial/tank response model",
            "system and size": f"H2 PSA; {prior['physical_design_rows']} CSS-converged design rows",
            "independence": "primary fitted data",
            "supported role": "common prior/event for policy and estimator comparison",
            "key result": "reference p=0.92743/0.47044/0.28360; selected policy 0.420",
            "explicit boundary": "conditional affine response and empirical copula; not plant validation",
        },
        {
            "evidence tier": "primary physical CSS horizon and register accounting",
            "system and size": "32 frozen two-bed spatial/tank rows; 100 cycles; 85 boundary-state scalars",
            "independence": "direct rerun of the source physical model; no surrogate state transition",
            "supported role": "tail-stable physical CSS horizon, fixed-point precision target, and explicit out-of-place data-register scale",
            "key result": (
                f"physical joint horizon {primary_physical_css['physical_horizon']['max_joint_strict_css_event_horizon']} cycles; "
                f"selected {primary_physical_css['fixed_point_screen']['selected']['bits_per_scalar']} bits; "
                f"safe horizon {primary_physical_css['fixed_point_screen']['selected']['safe_fixed_horizon']} cycles; "
                f"out-of-place state/raw-stream accounting "
                f"{primary_physical_css['reversible_register_accounting']['out_of_place_current_next_state_plus_raw_event_stream_data_qubits']:,} qubits"
            ),
            "explicit boundary": "architectural data-register accounting, not a universal lower bound; nonlinear reversible transport and workspace are not compiled",
        },
        {
            "evidence tier": "five-component competitive-Langmuir/LDF microsteps",
            "system and size": "25,856 cached cell states; separately compiled H2, CO2, CH4, CO, and N2 one-cell/one-second updates",
            "independence": "direct physical-state precision audit and clean Qiskit compute-copy-uncompute compilation",
            "supported role": "actual nonlinear equilibrium/kinetic microsteps and precision/resource boundary",
            "key result": (
                f"individual circuits 490–515 qubits and 1,118,920–1,965,308 CX; "
                f"sequential workspace-reuse accounting "
                f"{primary_all_component_ldf['sequential_five_component_accounting']['logical_qubits']} qubits/"
                f"{primary_all_component_ldf['sequential_five_component_accounting']['cx_additive_module_bound']:,} additive CX"
            ),
            "explicit boundary": "one AC cell and one-second explicit updates compiled as separate modules; gas transport, pressure evolution, valve/tank logic, adaptive integration, monolithic composition, full phase/cycle, routing, and hardware remain open",
        },
        {
            "evidence tier": "product-boundary valve and recycle-tank modules",
            "system and size": "6,464 cached product-end valve states and 64 final-cycle product/recycle/tank records",
            "independence": "direct physical-ledger precision audit and clean Qiskit compute-copy-uncompute compilation",
            "supported role": "actual outlet-valve/component-flux arithmetic and separate fixed-0.420 product-split/tank-capacity bookkeeping",
            "key result": (
                f"valve {primary_product_boundary['compiled_clean_valve_component_flux']['logical_qubits']} qubits/"
                f"{primary_product_boundary['compiled_clean_valve_component_flux']['cx']:,} CX; "
                f"five-component tank accounting {primary_product_boundary['five_component_tank_accounting']['logical_qubits']} qubits/"
                f"{primary_product_boundary['five_component_tank_accounting']['cx_additive_module_bound']:,} additive CX; "
                f"minimum capacity headroom {primary_product_boundary['selected_tank']['minimum_capacity_headroom_mol']:.2f} mol"
            ),
            "explicit boundary": "valve-flux and integrated product/tank records are separate evidence tiers; pressure/face transport is reported separately; adsorption coupling, tank withdrawal, adaptive integration, monolithic composition, full phase/cycle, routing, loading, and fault tolerance excluded",
        },
        {
            "evidence tier": "direct product-valve-to-boundary-cell balance",
            "system and size": "6,464 cached product-end states; 32,320 five-component boundary-balance evaluations",
            "independence": "frozen physical-cache precision propagation and one clean Qiskit direct composition",
            "supported role": "register-level connection from encoded product pressure/composition through valve component fluxes to conservative product-cell next gas",
            "key result": (
                f"{primary_product_boundary_balance['compiled_clean_product_valve_boundary_balance']['logical_qubits']:,} qubits/"
                f"{primary_product_boundary_balance['compiled_clean_product_valve_boundary_balance']['cx']:,} CX; "
                f"depth {primary_product_boundary_balance['compiled_clean_product_valve_boundary_balance']['depth_all_to_all']:,}; "
                "all five component precision gates pass"
            ),
            "explicit boundary": "pressure/composition and nonvalve terms remain supplied; normalization, valve scheduling, tank withdrawal, adaptive integration, full phase/cycle, routing, and fault tolerance excluded",
        },
        {
            "evidence tier": "direct product-cell LDF/valve/boundary-balance paths",
            "system and size": "6,464 cached product-end states; 32,320 component balances across 32 factor-specialized source rows",
            "independence": "frozen-cache precision propagation and direct clean Qiskit componentwise compilation",
            "supported role": "shared-register connection from product pressure/composition through LDF loading transfer and valve flux to conservative product-cell next gas",
            "key result": (
                f"component paths {min(row['logical_qubits'] for row in primary_product_ldf_valve_balance['componentwise_compiled_direct_paths']):,}–"
                f"{max(row['logical_qubits'] for row in primary_product_ldf_valve_balance['componentwise_compiled_direct_paths']):,} qubits and "
                f"{min(row['cx'] for row in primary_product_ldf_valve_balance['componentwise_compiled_direct_paths']):,}–"
                f"{max(row['cx'] for row in primary_product_ldf_valve_balance['componentwise_compiled_direct_paths']):,} CX; "
                f"conservative upper {primary_product_ldf_valve_balance['conservative_five_component_upper_bound']['logical_qubits_peak']:,} peak qubits/"
                f"{primary_product_ldf_valve_balance['conservative_five_component_upper_bound']['cx_additive_upper_bound']:,} additive CX"
            ),
            "explicit boundary": "shared 20-bit pressure/composition high 18 bits feed the valve; product composition normalization, inward-face generation, coherent run parameters, monolithic five-component transpilation, valve scheduling, tank withdrawal, adaptive integration, routing, and fault tolerance excluded",
        },
        {
            "evidence tier": "gas-inventory-generated product-cell LDF/valve/balance paths",
            "system and size": "6,464 cached product-end states; 32,320 component balances; two encoded gas inventories per state",
            "independence": "frozen physical-cache precision propagation and five clean factor-specialized componentwise Qiskit compilations",
            "supported role": "register-level product path from gas inventories through composition normalization, pressure reconstruction, inward-face generation, LDF uptake, valve withdrawal, loading conversion, and one conservative next-gas balance",
            "key result": (
                f"{min(row['logical_qubits'] for row in primary_normalized_product_ldf_valve_balance['componentwise_compiled_direct_paths']):,}–"
                f"{max(row['logical_qubits'] for row in primary_normalized_product_ldf_valve_balance['componentwise_compiled_direct_paths']):,} qubits/"
                f"{min(row['cx'] for row in primary_normalized_product_ldf_valve_balance['componentwise_compiled_direct_paths']):,}–"
                f"{max(row['cx'] for row in primary_normalized_product_ldf_valve_balance['componentwise_compiled_direct_paths']):,} CX; "
                f"{primary_normalized_product_ldf_valve_balance['conservative_five_component_upper_bound']['logical_qubits_peak']:,} peak qubits/"
                f"{primary_normalized_product_ldf_valve_balance['conservative_five_component_upper_bound']['cx_additive_upper_bound']:,} additive CX"
            ),
            "explicit boundary": "frozen-support factor-specialized component paths; the finite-support run/schedule/tank interface is a separate tier; monolithic five-component transpilation, adaptive integration, routing, and fault tolerance excluded",
        },
        {
            "evidence tier": "coherent run/schedule/tank interface",
            "system and size": "32 frozen run addresses; 11 run parameters; six paired-bed schedule stages; four final-cycle tank calls; five components",
            "independence": "direct encoding of the primary ledger support and clean Qiskit lookup/subtraction compilation",
            "supported role": "coherent finite-support run-parameter loading, local valve-mask scheduling, and recorded componentwise tank withdrawal",
            "key result": (
                f"{primary_coherent_run_schedule_tank['integrated_interface']['logical_qubits']:,} qubits/"
                f"{primary_coherent_run_schedule_tank['integrated_interface']['cx']:,} CX; "
                f"depth {primary_coherent_run_schedule_tank['integrated_interface']['depth_all_to_all']:,}; "
                f"parameter p95/max normalized errors "
                f"{primary_coherent_run_schedule_tank['parameter_encoding']['aggregate']['p95_span_normalized_absolute_error']:.3e}/"
                f"{primary_coherent_run_schedule_tank['parameter_encoding']['aggregate']['max_span_normalized_absolute_error']:.3e}; "
                "zero meaningful tank erasure, underflow, or next-state mismatch"
            ),
            "explicit boundary": "finite 32-run/final-cycle ledger QROM rather than a continuous off-ledger evaluator; state-dependent pressure/flow withdrawal, adaptive integration, monolithic five-component phase/cycle, routing, and fault tolerance remain open",
        },
        {
            "evidence tier": "coherent run-factor/LDF coefficient interface",
            "system and size": "32 frozen run addresses; 11 loaded run parameters; five equilibrium prefactors; five LDF coefficients; six paired-bed schedule stages",
            "independence": "direct reversible use of loaded capacity, affinity, and LDF-factor words with clean Qiskit multiplication and weighted arithmetic",
            "supported role": "controller-to-kinetics coefficient connection plus paired-bed adsorption-stage flags",
            "key result": (
                f"{primary_coherent_run_factor_ldf['compiled_interface']['logical_qubits']:,} qubits/"
                f"{primary_coherent_run_factor_ldf['compiled_interface']['cx']:,} CX; "
                f"depth {primary_coherent_run_factor_ldf['compiled_interface']['depth_all_to_all']:,}; "
                f"equilibrium p95/max relative errors "
                f"{primary_coherent_run_factor_ldf['precision']['five_component_equilibrium_prefactor_p95_relative_error']:.3e}/"
                f"{primary_coherent_run_factor_ldf['precision']['five_component_equilibrium_prefactor_max_relative_error']:.3e}; "
                f"LDF p95/max "
                f"{primary_coherent_run_factor_ldf['precision']['five_component_ldf_alpha_p95_relative_error']:.3e}/"
                f"{primary_coherent_run_factor_ldf['precision']['five_component_ldf_alpha_max_relative_error']:.3e}"
            ),
            "explicit boundary": "this tier generates coefficient registers only; downstream schedule-gated loading/balance consumption is reported separately, while dynamic pressure/composition denominator/reciprocal construction, off-ledger tank demand, adaptive integration, monolithic phase/cycle, routing, and fault tolerance remain open",
        },
        {
            "evidence tier": "coherent coefficient-to-LDF/loading/balance paths",
            "system and size": "32 run addresses; six paired-bed stages; five separately compiled component paths; 64,640 component-balance records",
            "independence": "direct reversible composition of the finite-support controller, generated coefficient registers, supplied 20-bit Langmuir response, sign-preserving LDF update, solid conversion, and conservative component balance",
            "supported role": "direct consumption of controller-generated equilibrium/LDF coefficients in schedule-gated component state updates",
            "key result": (
                f"{min(row['logical_qubits'] for row in primary_coherent_coefficient_ldf_balance['componentwise_compiled_direct_paths']):,}–"
                f"{max(row['logical_qubits'] for row in primary_coherent_coefficient_ldf_balance['componentwise_compiled_direct_paths']):,} qubits/"
                f"{min(row['cx'] for row in primary_coherent_coefficient_ldf_balance['componentwise_compiled_direct_paths']):,}–"
                f"{max(row['cx'] for row in primary_coherent_coefficient_ldf_balance['componentwise_compiled_direct_paths']):,} CX; "
                f"five-path upper bound {primary_coherent_coefficient_ldf_balance['conservative_five_component_upper_bound']['logical_qubits_peak']:,} peak qubits/"
                f"{primary_coherent_coefficient_ldf_balance['conservative_five_component_upper_bound']['cx_additive_upper_bound']:,} additive CX/depth "
                f"{primary_coherent_coefficient_ldf_balance['conservative_five_component_upper_bound']['depth_all_to_all_additive_upper_bound']:,}; "
                f"q* max ≤{max(row['qstar_max_loading_scale_normalized_absolute_error'] for row in primary_coherent_coefficient_ldf_balance['components']):.3e}; "
                f"next-gas max ≤{max(row['next_gas_max_scale_normalized_absolute_error'] for row in primary_coherent_coefficient_ldf_balance['components']):.3e}; zero quantized-transfer erasure"
            ),
            "explicit boundary": "the 20-bit competitive-Langmuir response is supplied; dynamic affinity-dependent denominator/reciprocal construction, gas normalization, face generation, off-ledger tank demand, monolithic five-component phase/cycle, adaptive integration, routing, hardware feasibility, external H2 validation, and quantum advantage remain open",
        },
        {
            "evidence tier": "coherent dynamic-Langmuir-to-LDF/loading/balance paths",
            "system and size": "32 run addresses; six paired-bed stages; five separately compiled component paths; 64,640 component-balance records",
            "independence": "direct reversible composition of the finite-support controller, supplied 20-bit pressure/five-component composition, dynamically generated affinity-dependent denominator/reciprocal, generated response, q*, sign-preserving LDF update, solid conversion, and conservative component balance",
            "supported role": "controller-coupled competitive-Langmuir response generation and direct consumption in schedule-gated component state updates",
            "key result": (
                f"{min(row['logical_qubits'] for row in primary_coherent_dynamic_langmuir_ldf_balance['componentwise_compiled_direct_paths']):,}–"
                f"{max(row['logical_qubits'] for row in primary_coherent_dynamic_langmuir_ldf_balance['componentwise_compiled_direct_paths']):,} qubits/"
                f"{min(row['cx'] for row in primary_coherent_dynamic_langmuir_ldf_balance['componentwise_compiled_direct_paths']):,}–"
                f"{max(row['cx'] for row in primary_coherent_dynamic_langmuir_ldf_balance['componentwise_compiled_direct_paths']):,} CX; "
                f"five-path upper bound {primary_coherent_dynamic_langmuir_ldf_balance['conservative_five_component_upper_bound']['logical_qubits_peak']:,} peak qubits/"
                f"{primary_coherent_dynamic_langmuir_ldf_balance['conservative_five_component_upper_bound']['cx_additive_upper_bound']:,} additive CX/depth "
                f"{primary_coherent_dynamic_langmuir_ldf_balance['conservative_five_component_upper_bound']['depth_all_to_all_additive_upper_bound']:,}; "
                f"denominator p95/max {primary_coherent_dynamic_langmuir_ldf_balance['selected_dynamic_response_design']['denominator_p95_absolute_error']:.3e}/"
                f"{primary_coherent_dynamic_langmuir_ldf_balance['selected_dynamic_response_design']['denominator_max_absolute_error']:.3e}; "
                f"q* max ≤{max(row['qstar_max_loading_scale_normalized_absolute_error'] for row in primary_coherent_dynamic_langmuir_ldf_balance['components']):.3e}"
            ),
            "explicit boundary": "20-bit pressure and five composition words are supplied; gas normalization, face generation, off-ledger tank demand, monolithic five-component phase/cycle, adaptive integration, routing, hardware feasibility, external H2 validation, and quantum advantage remain open",
        },
        {
            "evidence tier": "coherent gas-inventory-to-dynamic-Langmuir/transport/LDF/balance paths",
            "system and size": "32 run addresses; six paired-bed stages; three five-component gas inventories; five separately compiled component paths; 25,856 normalization states; 64,640 component-balance records",
            "independence": "direct reversible composition from encoded gas inventories and finite-support control through normalization, pressure reconstruction, two oriented faces, dynamic affinity-dependent denominator/reciprocal, q*, sign-preserving LDF update, solid conversion, and conservative component balance",
            "supported role": "controller-coupled gas-inventory-to-state-update path without supplied pressure, composition, or face-flux words",
            "key result": (
                f"{min(row['logical_qubits'] for row in primary_coherent_normalized_dynamic_transport_ldf_balance['componentwise_compiled_direct_paths']):,}–"
                f"{max(row['logical_qubits'] for row in primary_coherent_normalized_dynamic_transport_ldf_balance['componentwise_compiled_direct_paths']):,} qubits/"
                f"{min(row['cx'] for row in primary_coherent_normalized_dynamic_transport_ldf_balance['componentwise_compiled_direct_paths']):,}–"
                f"{max(row['cx'] for row in primary_coherent_normalized_dynamic_transport_ldf_balance['componentwise_compiled_direct_paths']):,} CX; "
                f"five-path upper bound {primary_coherent_normalized_dynamic_transport_ldf_balance['conservative_five_component_upper_bound']['logical_qubits_peak']:,} peak qubits/"
                f"{primary_coherent_normalized_dynamic_transport_ldf_balance['conservative_five_component_upper_bound']['cx_additive_upper_bound']:,} additive CX/depth "
                f"{primary_coherent_normalized_dynamic_transport_ldf_balance['conservative_five_component_upper_bound']['depth_all_to_all_additive_upper_bound']:,}; "
                f"next-gas max ≤{max(row['next_gas_max_scale_normalized_absolute_error'] for row in primary_coherent_normalized_dynamic_transport_ldf_balance['components']):.3e}"
            ),
            "explicit boundary": "support-adaptive normalization and oriented flow are calibrated to the frozen domain; negative-flow switching outside support, continuous off-ledger tank demand, monolithic five-component phase/cycle, adaptive integration, routing, hardware feasibility, external H2 validation, and quantum advantage remain open",
        },
        {
            "evidence tier": "pressure-derived saturated tank-withdrawal interface",
            "system and size": "32 runs; four tank-sourced calls per final cycle; 128 endpoint-pressure/tank records; five gas and five tank component inventories per record",
            "independence": "cycle-100 replay from the cached 85-scalar physical boundary, raw endpoint-gas pressure reconstruction, reversible demand/tank comparison, and clean Qiskit compute-copy-uncompute compilation",
            "supported role": "replaces the recorded-withdrawal lookup on the frozen demand-saturated branch with pressure-derived saturation logic and componentwise tank subtraction",
            "key result": (
                f"{primary_offledger_tank_saturation['compiled_clean_circuit']['logical_qubits']:,} qubits/"
                f"{primary_offledger_tank_saturation['compiled_clean_circuit']['cx']:,} CX/depth "
                f"{primary_offledger_tank_saturation['compiled_clean_circuit']['depth_all_to_all']:,}; "
                f"128/128 saturation labels; minimum lower-bound margin "
                f"{primary_offledger_tank_saturation['selected_design']['minimum_lower_bound_minus_tank_mol']:.6f} mol; "
                f"p95 aggregate normalized error {primary_offledger_tank_saturation['selected_design']['all_output_p95_scale_normalized_absolute_error']:.3e}"
            ),
            "explicit boundary": "every frozen call is saturated; unsaturated proportional allocation, trajectory-wide proof outside support, phase-end endpoint-gas generation inside a monolithic phase unitary, adaptive integration, routing, external H2 validation, and quantum advantage remain open",
        },
        {
            "evidence tier": "pressure-derived saturated/unsaturated proportional tank-allocation interface",
            "system and size": "128 observed frozen final-cycle calls plus 224 bounded pressure-counterfactual arithmetic cases over 32 nonzero observed tank compositions and seven demand fractions",
            "independence": "observed saturated branch plus explicitly labelled counterfactual unsaturated arithmetic-domain coverage; direct pressure reconstruction, demand/tank comparison, support-adaptive reciprocal, reversible multipliers, branch selection, subtraction, and clean uncomputation",
            "supported role": "closes the missing five-component proportional-allocation arithmetic branch while preserving the empirical boundary between observed and counterfactual cases",
            "key result": (
                f"{primary_offledger_tank_proportional['compiled_clean_circuit']['logical_qubits']:,} qubits/"
                f"{primary_offledger_tank_proportional['compiled_clean_circuit']['cx']:,} CX/depth "
                f"{primary_offledger_tank_proportional['compiled_clean_circuit']['depth_all_to_all']:,}; "
                f"{primary_offledger_tank_proportional['selected_design']['encoded_saturated_records']} saturated/"
                f"{primary_offledger_tank_proportional['selected_design']['encoded_unsaturated_records']} unsaturated labels; "
                f"withdrawal/next p95 {primary_offledger_tank_proportional['selected_design']['withdrawal_and_next_p95_component_scale_normalized_absolute_error']:.3e}, "
                f"max {primary_offledger_tank_proportional['selected_design']['withdrawal_and_next_max_component_scale_normalized_absolute_error']:.3e}"
            ),
            "explicit boundary": "the unsaturated cases are bounded pressure counterfactuals over observed tank compositions, not physically generated phase trajectories or plant validation; out-of-domain reciprocal behavior, monolithic five-component phase/cycle generation, adaptive integration, routing, external H2 validation, and quantum advantage remain open",
        },
        {
            "evidence tier": "model-derived physical unsaturated tank-trajectory control",
            "system and size": (
                f"sample 0 at recycle {primary_physical_unsaturated_tank['trajectory']['recycle_fraction']:.6f}; "
                f"{primary_physical_unsaturated_tank['trajectory']['cycles']} cycles; "
                f"{primary_physical_unsaturated_tank['trajectory']['tank_calls']} replayed tank calls"
            ),
            "independence": "direct source spatial/tank ODE integration under a declared 0.02-s non-adsorption schedule, exact phase replay, and clean start/end-pressure trapezoidal-demand circuit compilation",
            "supported role": "replaces bounded arithmetic-only unsaturated cases with one physically generated tank-sufficient trajectory and quantifies the extra two-pressure reversible cost",
            "key result": (
                f"{primary_physical_unsaturated_tank['compiled_clean_circuit']['logical_qubits']:,} qubits/"
                f"{primary_physical_unsaturated_tank['compiled_clean_circuit']['cx']:,} CX/depth "
                f"{primary_physical_unsaturated_tank['compiled_clean_circuit']['depth_all_to_all']:,}; "
                f"{primary_physical_unsaturated_tank['trajectory']['unsaturated_calls']}/"
                f"{primary_physical_unsaturated_tank['trajectory']['tank_calls']} unsaturated and zero-makeup calls; "
                f"CSS {primary_physical_unsaturated_tank['trajectory']['final_css_residual_max']:.3e}; "
                f"trapezoid-demand p95 relative error {primary_physical_unsaturated_tank['pressure_demand_diagnostics']['trapezoid_proxy_p95_relative_error']:.3%}; "
                f"withdrawal/next p95 {primary_physical_unsaturated_tank['selected_design']['withdrawal_and_next_p95_component_scale_normalized_absolute_error']:.3e}"
            ),
            "explicit boundary": "same recycle fraction but a short-schedule model counterfactual, not the frozen 10-s policy, the other 31 uncertainty rows, plant calibration, industrial H2 validation, monolithic phase integration, routing, hardware feasibility, or quantum advantage",
        },
        {
            "evidence tier": "pressure reconstruction and oriented internal-face transport",
            "system and size": "25,856 cached cell states and 19,392 locally oriented internal faces",
            "independence": "direct source-state precision audit and clean Qiskit compute-copy-uncompute compilation",
            "supported role": "gas-inventory pressure reconstruction and pressure-driven five-component transfer across one internal face",
            "key result": (
                f"pressure {primary_internal_transport['compiled_clean_pressure_reconstruction']['logical_qubits']} qubits/"
                f"{primary_internal_transport['compiled_clean_pressure_reconstruction']['cx']:,} CX; "
                f"face {primary_internal_transport['compiled_clean_oriented_internal_face_transport']['logical_qubits']} qubits/"
                f"{primary_internal_transport['compiled_clean_oriented_internal_face_transport']['cx']:,} CX; "
                f"modular 2-pressure+1-face accounting {primary_internal_transport['pressure_to_face_modular_accounting']['logical_qubits']} qubits/"
                f"{primary_internal_transport['pressure_to_face_modular_accounting']['cx_additive_module_bound']:,} additive CX"
            ),
            "explicit boundary": "orientation is restricted to the cached nonnegative local coordinate; direct two-face accumulation is reported in a separate tier, while reversible composition normalization, LDF coupling, adaptive integration, routing, and a complete phase/cycle remain open",
        },
        {
            "evidence tier": "direct pressure-to-two-face-to-interior-cell balance",
            "system and size": "12,928 cached interior-cell states and 64,640 five-component balance evaluations",
            "independence": "frozen physical-cache error propagation and one clean Qiskit direct composition",
            "supported role": "register-level connection from three cells' gas inventories through reconstructed pressures and two internal faces to conservative centre-cell next gas",
            "key result": (
                f"{primary_internal_face_balance['compiled_clean_internal_face_balance']['logical_qubits']:,} qubits/"
                f"{primary_internal_face_balance['compiled_clean_internal_face_balance']['cx']:,} CX; "
                f"depth {primary_internal_face_balance['compiled_clean_internal_face_balance']['depth_all_to_all']:,}; "
                "all five propagated inventory and arithmetic-only precision gates pass"
            ),
            "explicit boundary": "two upwind compositions and nonface terms remain supplied; normalization, negative-flow switching outside cached orientation, direct centre-cell LDF/loading coupling, run-specific parameters, tank withdrawal, integration, routing, and fault tolerance excluded",
        },
        {
            "evidence tier": "direct gas-normalization-to-two-face-to-interior-cell balance",
            "system and size": "25,856 cached left/centre normalization states; 12,928 interior-cell states; 64,640 five-component balance evaluations",
            "independence": "frozen physical-cache precision propagation and one clean Qiskit direct composition",
            "supported role": "register-level connection from encoded component inventories through generated mole fractions, reconstructed pressures, two internal faces, and conservative centre-cell next gas",
            "key result": (
                f"{primary_normalized_internal_face_balance['compiled_clean_normalized_internal_face_balance']['logical_qubits']:,} qubits/"
                f"{primary_normalized_internal_face_balance['compiled_clean_normalized_internal_face_balance']['cx']:,} CX; "
                f"depth {primary_normalized_internal_face_balance['compiled_clean_normalized_internal_face_balance']['depth_all_to_all']:,}; "
                f"standalone normalizer {primary_normalized_internal_face_balance['compiled_clean_composition_normalizer']['logical_qubits']:,} qubits/"
                f"{primary_normalized_internal_face_balance['compiled_clean_composition_normalizer']['cx']:,} CX; "
                f"maximum composition p95 absolute error {max(primary_normalized_internal_face_balance['selected_normalization']['composition_p95_absolute_error'].values()):.3e}"
            ),
            "explicit boundary": "support-adaptive reciprocal segmentation is calibrated to the frozen left/centre-cell domain; nonface terms remain supplied; out-of-support normalization, negative-flow switching, centre-cell LDF/loading coupling, run-specific parameters, tank withdrawal, integration, routing, and fault tolerance excluded",
        },
        {
            "evidence tier": "direct LDF-to-loading-sign-to-cell-balance composition",
            "system and size": "25,856 cached LDF precision states and 64,640 interior-cell component balances",
            "independence": "separate physical-cache precision gates, exhaustive three-bit sign control, and direct clean Qiskit register composition",
            "supported role": "widened one-second LDF output, loading sign/solid conversion, conservative next-gas accumulation, and exact reverse",
            "key result": (
                f"loading bits 26/26/32/32/30; directly composed circuits 861–929 qubits and 3,412,254–4,991,534 CX; "
                f"five-component accounting {primary_ldf_sign_balance['sequential_five_component_accounting']['logical_qubits']:,} qubits/"
                f"{primary_ldf_sign_balance['sequential_five_component_accounting']['cx_additive_module_bound']:,} additive CX; "
                f"interface alone {primary_loading_sign_balance['sequential_five_component_accounting']['logical_qubits']:,} qubits/"
                f"{primary_loading_sign_balance['sequential_five_component_accounting']['cx_additive_module_bound']:,} additive CX"
            ),
            "explicit boundary": "LDF arithmetic is constant-specialized; direct pressure/face/balance composition is a separate tier, while joint LDF-plus-face composition, reversible normalization and run-specific parameters, boundary cells, adaptive integration, routing, and complete phase/cycle remain open",
        },
        {
            "evidence tier": "direct normalized-transport/LDF/interior-balance paths",
            "system and size": "25,856 normalization states; 12,928 interior-cell states; 64,640 component balances; 32 factor-specialized rows",
            "independence": "frozen-cache precision propagation and five separately transpiled direct register compositions",
            "supported role": "shared encoded gas inventories through normalization, pressure, two internal faces, competitive-Langmuir/LDF uptake, sign/solid conversion, conservative next gas, and exact work reversal",
            "key result": (
                f"20-bit LDF pressure/composition inputs; selected loading bits "
                f"{'/'.join(str(row['loading_bits']) for row in primary_joint_normalized_transport_ldf_balance['selected_components'])}; "
                f"component paths {min(row['logical_qubits'] for row in primary_joint_normalized_transport_ldf_balance['componentwise_compiled_direct_paths']):,}–"
                f"{max(row['logical_qubits'] for row in primary_joint_normalized_transport_ldf_balance['componentwise_compiled_direct_paths']):,} qubits and "
                f"{min(row['cx'] for row in primary_joint_normalized_transport_ldf_balance['componentwise_compiled_direct_paths']):,}–"
                f"{max(row['cx'] for row in primary_joint_normalized_transport_ldf_balance['componentwise_compiled_direct_paths']):,} CX; "
                f"common-path-repeating upper bound "
                f"{primary_joint_normalized_transport_ldf_balance['compiled_clean_joint_specialized_circuit']['cx_additive_upper_bound']:,} CX"
            ),
            "explicit boundary": "parameter-specialized on frozen support; monolithic five-component transpilation and a coherent run-parameter register remain open, as do negative-flow switching outside support, boundary/tank withdrawal, integration, routing, and fault tolerance",
        },
        {
            "evidence tier": "primary phase-stream event bridge",
            "system and size": f"same 32 spatial/tank runs; {primary_phase_ledger['trace_per_run']['bed_phases']} phases and {primary_phase_ledger['trace_per_run']['equalizations']} equalizations per final cycle",
            "independence": "outer run held out; conditioned on its observed phase-start states",
            "supported role": "process-stream observability and event-active reversible resource interface",
            "key result": (
                f"event labels {primary_event_bridge['event_summary']['event_matches']}/32; "
                f"purity/recovery MAE {primary_event_bridge['event_summary']['purity_mae']:.2e}/"
                f"{primary_event_bridge['event_summary']['recovery_mae']:.2e}; "
                f"final event {primary_final_event['primitive_gate_compile']['clean_phase_oracle']['logical_qubits']} qubits/"
                f"{primary_final_event['primitive_gate_compile']['clean_phase_oracle']['cx']:,} clean CX"
            ),
            "explicit boundary": "conditional on observed phase starts; the integrated policy-specific arithmetic is reported separately; free-running physical CSS, loading, and external validation remain open",
        },
        {
            "evidence tier": "primary policy stream-to-event clean oracle",
            "system and size": "same calibrated adsorption maps; 32 phase-state points x 3 fixed recycle candidates",
            "independence": "arithmetic validation against full-fit maps and original 32-run ledger support; not external data",
            "supported role": "reversible connection from encoded phase starts and shared parameters through stream aggregation, recycle scaling, event phase mark, and exact uncomputation",
            "key result": (
                f"{primary_policy_stream_event['precision_screen']['selected']['aggregate_bits']}-bit aggregates; "
                f"candidate labels {primary_policy_stream_event['verification']['candidate_integer_event_matches_vs_float']}/96; "
                f"ledger-support labels {primary_policy_stream_event['verification']['ledger_support_event_matches_vs_actual']}/32; "
                f"max clean oracle {max(row['clean_phase_oracle']['logical_qubits'] for row in primary_policy_stream_event['primitive_gate_compile']['policy_resources'])} qubits/"
                f"{max(row['clean_phase_oracle']['cx'] for row in primary_policy_stream_event['primitive_gate_compile']['policy_resources']):,} CX"
            ),
            "explicit boundary": "phase starts remain supplied rather than generated by stable physical/reversible CSS; loading, routing/noise, external validation, and advantage remain open",
        },
        {
            "evidence tier": "parameter-only CSS initializer and cycle screen",
            "system and size": "same 32 spatial/tank runs; 11 parameters to 20 aggregate CSS-state coordinates",
            "independence": "outer run held out; no held dynamic state supplied",
            "supported role": "surrogate-conditioned CSS initialization and one-cycle event connection",
            "key result": (
                f"one-cycle labels {css_initializer_bridge['summary']['event_matches']}/32; "
                f"recovery MAE {css_initializer_bridge['summary']['recovery_mae']:.2e}; "
                f"unanchored 50-cycle terminal labels {css_initializer_repeated['summary']['terminal_event_matches']}/32; "
                f"spectrally stabilized terminal labels {css_initializer_stability['summary']['terminal_event_matches']}/32"
            ),
            "explicit boundary": (
                f"unanchored/stabilized 50-cycle CSS gates "
                f"{css_initializer_repeated['summary']['tail_css_gate_1e_4_count']}/32 and "
                f"{css_initializer_stability['summary']['tail_css_gate_1e_4_count']}/32; stabilization is an explicit aggregate-model correction, so tank/profile and physical CSS remain open"
            ),
        },
        {
            "evidence tier": "reduced-H2 phase ledger and calibrated maps",
            "system and size": f"{phase_ledger['source_row_count']} runs; {phase_ledger['phase_call_count']} phases; {phase_ledger['equalization_call_count']} equalizations",
            "independence": "separate reduced-model tier; held out by run",
            "supported role": "one-cycle state-transition bridge and primitive-gate resource layer",
            "key result": f"cycle median/p95 L1={cycle['median_joint_state_relative_l1']:.5f}/{cycle['p95_joint_state_relative_l1']:.5f}; 186-qubit affine block",
            "explicit boundary": "equalization remains classical; repeated CSS and primary event are not reversible",
        },
        {
            "evidence tier": "TU Wien H2/CH4 literature data",
            "system and size": f"H2/CH4 PSA; {empirical['tuwien']['recovery_summary']['n_runs']} recovery runs",
            "independence": "external published table-level data",
            "supported role": "valve sensitivity, tank geometry, breakthrough, product/recovery calibration",
            "key result": (
                f"group-held-out recovery RMSE {empirical['headline']['recovery_group_holdout_rmse_pct_point']:.2f} percentage points; "
                f"widest frozen-spacing effect/RMSE {h2_resolution['best_available_pair']['effect_to_group_cv_rmse']:.3f}"
            ),
            "explicit boundary": "purge/feed is not product recycle; continuous purity and frozen selection are not identifiable",
        },
        {
            "evidence tier": "Otway one-second log",
            "system and size": f"CO2 PSA; {empirical['otway']['row_count']:,} rows; {len(empirical['otway']['complete_cycles'])} complete cycles",
            "independence": "external cross-chemistry log",
            "supported role": "valve/pressure/flow synchronization and held-out hydraulic plausibility",
            "key result": f"mean holdout MAE reduction vs persistence {empirical['headline']['otway_mean_holdout_mae_reduction_vs_persistence']:.3f}",
            "explicit boundary": "does not validate H2 separation chemistry, purity, or recycle policy",
        },
        {
            "evidence tier": "public dynamic CO2/N2 model",
            "system and size": f"two-bed PSA; {len(external['scenarios'])} scenarios x 3 policies",
            "independence": "external executable chemistry analog",
            "supported role": "policy-direction and numerical-resolution control",
            "key result": f"purity direction {external['purity_endpoint_direction_match_count']}/{len(external['scenarios'])}; recovery direction {external['recovery_endpoint_direction_match_count']}/{len(external['scenarios'])}",
            "explicit boundary": "policy signal below quadrature shift; external selection 0.430 does not reproduce 0.420",
        },
        {
            "evidence tier": "Thelen VA-10 matched H2 pair",
            "system and size": "automated four-column H2 PSA; 2 matched operating points; 2 recovery methods",
            "independence": "external public same-chemistry experiment",
            "supported role": "equalization-pressure/recovery direction control",
            "key result": (
                f"4.50->4.75 bara: recovery delta "
                f"{thelen['paired_effects_bp2_minus_bp1']['h2_recovery_direct_bellows_meter_pct_point']:.2f}/"
                f"{thelen['paired_effects_bp2_minus_bp1']['h2_recovery_pulse_transmitter_pct_point']:.2f} percentage points"
            ),
            "explicit boundary": "different control from recycle; both purities below 99.98%; no same-event or 0.420-selection validation",
        },
        {
            "evidence tier": "independent pyAPEP H2 recycle code path",
            "system and size": "uniform 5A H2 PSA; 3 x 15-cycle policy screen plus one 450-cycle control",
            "independence": "external open-source column solver; project wrapper",
            "supported role": "corrected product-end topology and material-boundary stress test",
            "key result": (
                f"450-cycle purity/recovery/tank supply "
                f"{pyapep['long_horizon_control']['row']['h2_product']:.5f}/"
                f"{pyapep['long_horizon_control']['row']['h2_recovery_external_boundary']:.5f}/"
                f"{pyapep['long_horizon_control']['row']['tank_supply_fraction_total']:.5f}; "
                f"CSS {pyapep['long_horizon_control']['row']['css_residual_final']:.4g}"
            ),
            "explicit boundary": "no corrected CSS-converged policy set; purity, recovery, tank, and CSS gates fail; no 0.420 validation",
        },
        {
            "evidence tier": "public toPSAil/Yang H2 model and experiment",
            "system and size": "H2/CO 70/30; zeolite 5A; two beds; six steps; 25-CSTR public model",
            "independence": "external experiment plus external open-source dynamic model inputs and published CSS/calibration results",
            "supported role": "same-chemistry cyclic-topology, valve/pressure/recovery calibration, and high-purity experimental anchor",
            "key result": (
                f"experiment purity/recovery {100 * topsail_yang['yang_experiment']['product_h2_purity']:.2f}%/"
                f"{100 * topsail_yang['yang_experiment']['h2_recovery']:.2f}%; "
                f"frozen event={str(topsail_yang['event_comparison']['yang_joint_event_under_frozen_thresholds']).lower()}; "
                "published CSS 13/42/36/31 cycles"
            ),
            "explicit boundary": "purge/feed and product-tank purge are not the frozen product-gas recycle coordinate; no distributed cycle-result MAT files; no 0.420 validation",
        },
        {
            "evidence tier": "real-QPU finite event",
            "system and size": f"three active logical qubits on {qpu['backend']}; one job",
            "independence": "separate eight-state hardware kernel",
            "supported role": "executable amplification-depth noise boundary",
            "key result": f"exact p={qpu['exact_probability']:.3f}; p-hat={qpu['estimate']['estimate']:.6f}; error={qpu['estimate']['absolute_error']:.6f}",
            "explicit boundary": "not the continuous prior or cyclic PSA model; no hardware-general interval",
        },
    ]
    write_table(
        "PSA_QAE_CCE_TABLE4_EVIDENCE_HIERARCHY",
        "psa-qae-cce-table4-evidence-hierarchy/v1",
        "evidence_tiers_tabulated_without_cross_system_pooling",
        [PROTOCOL, PRIMARY_PHASE_LEDGER, PRIMARY_PHYSICAL_CSS, PRIMARY_QSTAR_MICROKERNEL, PRIMARY_QSTAR_LDF_MICROSTEP, PRIMARY_ALL_COMPONENT_LDF, PRIMARY_PRODUCT_BOUNDARY, PRIMARY_PRODUCT_BOUNDARY_BALANCE, PRIMARY_PRODUCT_LDF_VALVE_BALANCE, PRIMARY_NORMALIZED_PRODUCT_LDF_VALVE_BALANCE, PRIMARY_COHERENT_RUN_SCHEDULE_TANK, PRIMARY_COHERENT_RUN_FACTOR_LDF, PRIMARY_COHERENT_COEFFICIENT_LDF_BALANCE, PRIMARY_COHERENT_DYNAMIC_LANGMUIR_LDF_BALANCE, PRIMARY_OFFLEDGER_TANK_SATURATION, PRIMARY_OFFLEDGER_TANK_PROPORTIONAL, PRIMARY_PHYSICAL_UNSATURATED_TANK, PRIMARY_INTERNAL_TRANSPORT, PRIMARY_INTERNAL_FACE_BALANCE, PRIMARY_NORMALIZED_INTERNAL_FACE_BALANCE, PRIMARY_CELL_BALANCE, PRIMARY_LOADING_SIGN_BALANCE, PRIMARY_LDF_SIGN_BALANCE, PRIMARY_JOINT_NORMALIZED_TRANSPORT_LDF_BALANCE, PRIMARY_EVENT_BRIDGE, PRIMARY_FINAL_EVENT, PRIMARY_POLICY_STREAM_EVENT, CSS_INITIALIZER_BRIDGE, CSS_INITIALIZER_REPEATED, CSS_INITIALIZER_STABILITY, PHASE_MAP, PHASE_LEDGER, EMPIRICAL, EXTERNAL, THELEN, PYAPEP, H2_RESOLUTION, TOPSAIL_YANG, QPU],
        table4,
        "Table 4. Evidence hierarchy and claim boundary",
    )
    print(json.dumps({"status": "cce_main_tables_1_2_4_assembled", "table1_rows": len(table1), "table2_rows": len(table2), "table4_rows": len(table4)}, indent=2))


if __name__ == "__main__":
    main()
