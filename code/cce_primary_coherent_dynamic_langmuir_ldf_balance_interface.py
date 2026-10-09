"""Generate the competitive-Langmuir response inside the coherent PSA path.

This audit closes the supplied-response boundary of the coherent coefficient
consumer.  A clean reversible module consumes the controller's retained
12-bit run-specific affinity-factor word together with a 20-bit pressure and
five 20-bit composition words.  It constructs

    D = 1 + P f_b sum_j(b_j y_j),   rho_i = P y_i / D,

loads a reciprocal from a global finite-support QROM, emits a 20-bit rho_i,
and reverses every denominator, reciprocal, and multiplication workspace.
The generated rho_i is consumed directly by the existing controller-to-q*,
LDF-loading, loading-sign, and conservative component-balance path.  No QPU
job is submitted.
"""

from __future__ import annotations

import argparse
import csv
import gc
import json
from pathlib import Path

import numpy as np
from qiskit import QuantumCircuit, QuantumRegister, transpile
from qiskit.circuit.library import MultiplierGate, WeightedAdder

from cce_primary_coherent_coefficient_ldf_balance_interface import (
    RESPONSE_BITS,
    RESPONSE_LEVELS,
    build_component_circuit,
    component_precision_rows,
    controller_bundle,
    resource_record,
)
from cce_primary_coherent_run_factor_ldf_interface import (
    COEFFICIENT_SCALE_BITS,
    integer_weights_for_affine,
    weighted_code,
)
from cce_primary_coherent_run_schedule_tank_interface import (
    COMPONENTS,
    PARAMETER_BITS,
    RESULTS,
    parameter_tables,
)
from cce_primary_joint_normalized_transport_ldf_balance import (
    RECORDS_PER_RUN,
    load_context,
)
from cce_primary_loading_sign_balance_interface import register_indices
from cce_primary_qstar_ldf_reversible_microstep import (
    append_address_extractor,
    append_reciprocal_qrom,
)


OUT_JSON = RESULTS / "PSA_QAE_CCE_COHERENT_DYNAMIC_LANGMUIR_LDF_BALANCE_INTERFACE.json"
OUT_CSV = RESULTS / "PSA_QAE_CCE_COHERENT_DYNAMIC_LANGMUIR_LDF_BALANCE_INTERFACE.csv"
OUT_MD = RESULTS / "PSA_QAE_CCE_COHERENT_DYNAMIC_LANGMUIR_LDF_BALANCE_INTERFACE.md"
CHECKPOINT_JSON = RESULTS / "PSA_QAE_CCE_COHERENT_DYNAMIC_LANGMUIR_LDF_BALANCE_INTERFACE.checkpoint.json"
PRIOR_JOINT_JSON = RESULTS / "PSA_QAE_CCE_PRIMARY_JOINT_NORMALIZED_TRANSPORT_LDF_BALANCE.json"

AFFINITY_BIT_CANDIDATES = (8, 9, 10, 11, 12)
ADDRESS_BIT_CANDIDATES = (9, 10, 11, 12)
TRANSPILER_SEED = 20261010


def affinity_parameter_row(bundle: dict) -> dict:
    _, rows, _ = parameter_tables(bundle["runs"])
    return next(row for row in rows if row["parameter"] == "affinity_factor")


def response_design(context, bundle: dict, affinity_bits: int, address_bits: int) -> dict:
    levels = RESPONSE_LEVELS
    affinity_levels = (1 << int(affinity_bits)) - 1
    address_levels = (1 << int(address_bits)) - 1
    pressure_scale = float(context.normalized["selected_pressure"]["pressure_scale_bar"])
    base_affinity = np.asarray(context.base_constants["affinity"], dtype=float)
    affinity_scale = float(np.max(base_affinity))
    affinity_integer = np.rint(
        base_affinity / affinity_scale * affinity_levels
    ).astype(int)
    affinity_weights = [
        int(affinity_integer[component]) * (1 << bit)
        for component in range(len(COMPONENTS))
        for bit in range(RESPONSE_BITS)
    ]
    affinity_adder = WeightedAdder(len(affinity_weights), affinity_weights)

    parameter_row = affinity_parameter_row(bundle)
    factor_weights = integer_weights_for_affine(
        float(parameter_row["support_min"]),
        float(parameter_row["support_span"]),
    )
    factor_adder = WeightedAdder(len(factor_weights), factor_weights)
    factor_codes_by_run = np.asarray(
        [
            weighted_code(int(code), factor_weights, constant=True)
            for code in bundle["tables"]["affinity_factor"]
        ],
        dtype=object,
    )
    state_samples = np.repeat(np.asarray(context.samples, dtype=int), RECORDS_PER_RUN)
    factor_code = np.asarray(
        [int(factor_codes_by_run[int(sample)]) for sample in state_samples],
        dtype=object,
    )

    pressure_code = np.asarray(context.pressure20[:, 1], dtype=object)
    composition_code = np.asarray(context.composition20[:, 1, :], dtype=object)
    affinity_sum_code = np.zeros(len(pressure_code), dtype=object)
    for component in range(len(COMPONENTS)):
        affinity_sum_code += (
            composition_code[:, component] * int(affinity_integer[component])
        )
    scaled_affinity_sum_code = np.asarray(
        [
            (
                int(affinity_sum_code[index]) * int(factor_code[index])
                + (1 << (COEFFICIENT_SCALE_BITS - 1))
            )
            >> COEFFICIENT_SCALE_BITS
            for index in range(len(pressure_code))
        ],
        dtype=object,
    )
    denominator_scale = (
        levels * levels * affinity_levels / (pressure_scale * affinity_scale)
    )
    denominator_one_code = int(round(denominator_scale))
    denominator_code = np.asarray(
        [
            denominator_one_code
            + int(pressure_code[index]) * int(scaled_affinity_sum_code[index])
            for index in range(len(pressure_code))
        ],
        dtype=object,
    )

    exact_pressure = np.asarray(context.terms["pressure_triplet"][:, 1], dtype=float)
    exact_composition = np.asarray(
        context.terms["composition_pair"][:, 1, :], dtype=float
    )
    exact_factor = np.repeat(context.factors[:, 1], RECORDS_PER_RUN)
    exact_denominator = 1.0 + exact_pressure * np.sum(
        exact_composition * base_affinity[None, :] * exact_factor[:, None], axis=1
    )
    implemented_denominator = (
        np.asarray(denominator_code, dtype=float) / denominator_scale
    )
    denominator_min = 1.0
    denominator_max = float(
        max(np.max(exact_denominator), np.max(implemented_denominator))
        * (1.0 + 1.0e-12)
    )
    thresholds = [
        int(
            round(
                (
                    denominator_min
                    + (index - 0.5)
                    * (denominator_max - denominator_min)
                    / address_levels
                )
                * denominator_scale
            )
        )
        for index in range(1, address_levels + 1)
    ]
    address = np.searchsorted(
        np.asarray(thresholds, dtype=object), denominator_code, side="right"
    )
    reciprocal_table = [
        min(
            levels,
            int(
                round(
                    levels
                    / (
                        denominator_min
                        + (denominator_max - denominator_min)
                        * code
                        / address_levels
                    )
                )
            ),
        )
        for code in range(address_levels + 1)
    ]
    reciprocal_code = np.asarray(
        [reciprocal_table[int(code)] for code in address], dtype=object
    )
    response_codes: list[np.ndarray] = []
    for component in range(len(COMPONENTS)):
        numerator = pressure_code * composition_code[:, component]
        response_codes.append(
            np.asarray(
                [
                    (
                        int(numerator[index]) * int(reciprocal_code[index])
                        + (1 << (2 * RESPONSE_BITS - 1))
                    )
                    >> (2 * RESPONSE_BITS)
                    for index in range(len(numerator))
                ],
                dtype=object,
            )
        )
    if any(
        np.any(np.asarray(code, dtype=float) > levels) for code in response_codes
    ):
        raise AssertionError("dynamic response overflow")

    factor_implemented = np.asarray(factor_code, dtype=float) / (
        1 << COEFFICIENT_SCALE_BITS
    )
    factor_exact = exact_factor
    denominator_error = np.abs(implemented_denominator - exact_denominator)
    return {
        "affinity_bits": int(affinity_bits),
        "denominator_address_bits": int(address_bits),
        "reciprocal_segments": 1 << int(address_bits),
        "affinity_integer": [int(value) for value in affinity_integer],
        "affinity_weights": affinity_weights,
        "affinity_sum_bits": int(affinity_adder.num_sum_qubits),
        "affinity_adder_ancillas": int(affinity_adder.num_ancillas),
        "factor_weights": [int(value) for value in factor_weights],
        "factor_sum_bits": int(factor_adder.num_sum_qubits),
        "factor_adder_ancillas": int(factor_adder.num_ancillas),
        "denominator_scale": float(denominator_scale),
        "denominator_one_code": int(denominator_one_code),
        "denominator_range": [denominator_min, denominator_max],
        "denominator_threshold_codes": thresholds,
        "reciprocal_table": reciprocal_table,
        "factor_p95_absolute_error": float(
            np.quantile(np.abs(factor_implemented - factor_exact), 0.95)
        ),
        "factor_max_absolute_error": float(
            np.max(np.abs(factor_implemented - factor_exact))
        ),
        "denominator_p95_absolute_error": float(
            np.quantile(denominator_error, 0.95)
        ),
        "denominator_max_absolute_error": float(np.max(denominator_error)),
        "denominator_address_min": int(np.min(address)),
        "denominator_address_max": int(np.max(address)),
        "denominator_address_saturation_fraction": float(
            np.mean(address == address_levels)
        ),
        "response_codes": response_codes,
    }


def serializable_design(design: dict) -> dict:
    return {key: value for key, value in design.items() if key != "response_codes"}


def build_dynamic_response_module(
    design: dict, component_index: int
) -> tuple[QuantumCircuit, dict]:
    affinity_adder = WeightedAdder(
        len(design["affinity_weights"]), design["affinity_weights"]
    )
    factor_adder = WeightedAdder(
        len(design["factor_weights"]), design["factor_weights"]
    )
    affinity_sum_bits = int(affinity_adder.num_sum_qubits)
    factor_sum_bits = int(factor_adder.num_sum_qubits)
    state_bits = max(affinity_sum_bits, factor_sum_bits, RESPONSE_BITS)
    wide_bits = 2 * state_bits
    address_bits = int(design["denominator_address_bits"])
    shared_work_bits = max(
        wide_bits,
        affinity_adder.num_ancillas,
        factor_adder.num_ancillas,
        address_bits - 2,
    )
    pad_bits = max(
        state_bits - factor_sum_bits,
        state_bits - RESPONSE_BITS,
        RESPONSE_BITS,
    )

    affinity_parameter = QuantumRegister(PARAMETER_BITS, "affinity_parameter")
    pressure = QuantumRegister(RESPONSE_BITS, "pressure")
    composition = QuantumRegister(
        len(COMPONENTS) * RESPONSE_BITS, "composition"
    )
    constant_one = QuantumRegister(1, "constant_one")
    factor_sum = QuantumRegister(factor_sum_bits, "affinity_factor_fixed")
    affinity_sum = QuantumRegister(affinity_sum_bits, "base_affinity_sum")
    scaled_affinity_sum = QuantumRegister(
        affinity_sum_bits, "run_affinity_sum"
    )
    wide_product = QuantumRegister(wide_bits, "denominator_product")
    address = QuantumRegister(address_bits, "denominator_address")
    reciprocal = QuantumRegister(RESPONSE_BITS, "reciprocal")
    numerator = QuantumRegister(2 * RESPONSE_BITS, "numerator")
    response_product = QuantumRegister(3 * RESPONSE_BITS, "response_product")
    response = QuantumRegister(RESPONSE_BITS, "response")
    pad = QuantumRegister(pad_bits, "multiplier_pad")
    shared_work = QuantumRegister(shared_work_bits, "shared_work")
    circuit = QuantumCircuit(
        affinity_parameter,
        pressure,
        composition,
        constant_one,
        factor_sum,
        affinity_sum,
        scaled_affinity_sum,
        wide_product,
        address,
        reciprocal,
        numerator,
        response_product,
        response,
        pad,
        shared_work,
        name=f"dynamic_langmuir_{COMPONENTS[component_index].lower()}",
    )

    circuit.x(constant_one[0])
    factor_qargs = (
        list(constant_one)
        + list(affinity_parameter)
        + list(factor_sum)
        + list(shared_work)[: factor_adder.num_ancillas]
    )
    circuit.append(factor_adder, factor_qargs)
    affinity_qargs = (
        list(composition)
        + list(affinity_sum)
        + list(shared_work)[: affinity_adder.num_ancillas]
    )
    circuit.append(affinity_adder, affinity_qargs)

    factor_operand = list(factor_sum) + list(pad)[: state_bits - factor_sum_bits]
    affinity_operand = list(affinity_sum) + list(shared_work)[
        : state_bits - affinity_sum_bits
    ]
    scaled_multiplier = MultiplierGate(state_bits, wide_bits)
    scaled_qargs = affinity_operand + factor_operand + list(wide_product)
    circuit.x(wide_product[COEFFICIENT_SCALE_BITS - 1])
    circuit.append(scaled_multiplier, scaled_qargs)
    scaled_sources = list(wide_product)[
        COEFFICIENT_SCALE_BITS : COEFFICIENT_SCALE_BITS + affinity_sum_bits
    ]
    for source, target in zip(scaled_sources, list(scaled_affinity_sum)):
        circuit.cx(source, target)
    circuit.append(scaled_multiplier.inverse(), scaled_qargs)
    circuit.x(wide_product[COEFFICIENT_SCALE_BITS - 1])

    pressure_operand = list(pressure) + list(pad)[: state_bits - RESPONSE_BITS]
    scaled_operand = list(scaled_affinity_sum) + list(shared_work)[
        : state_bits - affinity_sum_bits
    ]
    denominator_multiplier = MultiplierGate(state_bits, wide_bits)
    denominator_qargs = pressure_operand + scaled_operand + list(wide_product)
    denominator_one_code = int(design["denominator_one_code"])
    for bit in range(wide_bits):
        if (denominator_one_code >> bit) & 1:
            circuit.x(wide_product[bit])
    circuit.append(denominator_multiplier, denominator_qargs)

    append_address_extractor(
        circuit,
        list(wide_product),
        list(address),
        shared_work[0],
        list(shared_work)[1:],
        design["denominator_threshold_codes"],
    )
    append_reciprocal_qrom(
        circuit,
        list(address),
        list(reciprocal),
        list(shared_work),
        design["reciprocal_table"],
    )

    component_word = list(composition)[
        component_index * RESPONSE_BITS : (component_index + 1) * RESPONSE_BITS
    ]
    numerator_multiplier = MultiplierGate(RESPONSE_BITS, 2 * RESPONSE_BITS)
    numerator_qargs = list(pressure) + component_word + list(numerator)
    circuit.append(numerator_multiplier, numerator_qargs)
    reciprocal_operand = list(reciprocal) + list(pad)[:RESPONSE_BITS]
    response_multiplier = MultiplierGate(
        2 * RESPONSE_BITS, 3 * RESPONSE_BITS
    )
    response_qargs = list(numerator) + reciprocal_operand + list(response_product)
    circuit.x(response_product[2 * RESPONSE_BITS - 1])
    circuit.append(response_multiplier, response_qargs)
    high_response = list(response_product)[
        2 * RESPONSE_BITS : 3 * RESPONSE_BITS
    ]
    for source, target in zip(high_response, list(response)):
        circuit.cx(source, target)
    circuit.append(response_multiplier.inverse(), response_qargs)
    circuit.x(response_product[2 * RESPONSE_BITS - 1])
    circuit.append(numerator_multiplier.inverse(), numerator_qargs)

    append_reciprocal_qrom(
        circuit,
        list(address),
        list(reciprocal),
        list(shared_work),
        design["reciprocal_table"],
        inverse=True,
    )
    append_address_extractor(
        circuit,
        list(wide_product),
        list(address),
        shared_work[0],
        list(shared_work)[1:],
        design["denominator_threshold_codes"],
        inverse=True,
    )
    circuit.append(denominator_multiplier.inverse(), denominator_qargs)
    for bit in reversed(range(wide_bits)):
        if (denominator_one_code >> bit) & 1:
            circuit.x(wide_product[bit])

    circuit.x(wide_product[COEFFICIENT_SCALE_BITS - 1])
    circuit.append(scaled_multiplier, scaled_qargs)
    for source, target in reversed(
        list(zip(scaled_sources, list(scaled_affinity_sum)))
    ):
        circuit.cx(source, target)
    circuit.append(scaled_multiplier.inverse(), scaled_qargs)
    circuit.x(wide_product[COEFFICIENT_SCALE_BITS - 1])
    circuit.append(affinity_adder.inverse(), affinity_qargs)
    circuit.append(factor_adder.inverse(), factor_qargs)
    circuit.x(constant_one[0])

    retained = set(
        list(affinity_parameter)
        + list(pressure)
        + list(composition)
        + list(response)
    )
    layout = {
        "component": COMPONENTS[component_index],
        "affinity_parameter": register_indices(circuit, "affinity_parameter"),
        "pressure": register_indices(circuit, "pressure"),
        "composition": register_indices(circuit, "composition"),
        "response": register_indices(circuit, "response"),
        "logical_qubits": circuit.num_qubits,
        "retained_input_output_qubits": len(retained),
        "cleared_workspace_qubits": circuit.num_qubits - len(retained),
        "affinity_sum_bits": affinity_sum_bits,
        "factor_sum_bits": factor_sum_bits,
        "denominator_register_bits": wide_bits,
        "denominator_address_bits": address_bits,
        "reciprocal_bits": RESPONSE_BITS,
    }
    return circuit, layout


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--screen-only", action="store_true")
    parser.add_argument("--componentwise-compile", action="store_true")
    args = parser.parse_args()
    if args.screen_only and args.componentwise_compile:
        parser.error("--screen-only and --componentwise-compile are mutually exclusive")

    context = load_context()
    bundle = controller_bundle()
    selected_components = json.loads(PRIOR_JOINT_JSON.read_text(encoding="utf-8"))[
        "selected_components"
    ]
    screens: list[dict] = []
    chosen_design = None
    chosen_rows = None
    for address_bits in ADDRESS_BIT_CANDIDATES:
        for affinity_bits in AFFINITY_BIT_CANDIDATES:
            design = response_design(context, bundle, affinity_bits, address_bits)
            rows = component_precision_rows(
                context,
                bundle,
                selected_components,
                response_codes_by_component=design["response_codes"],
            )
            screen = {
                "affinity_bits": affinity_bits,
                "denominator_address_bits": address_bits,
                "reciprocal_segments": 1 << address_bits,
                "affinity_sum_bits": design["affinity_sum_bits"],
                "denominator_p95_absolute_error": design[
                    "denominator_p95_absolute_error"
                ],
                "denominator_max_absolute_error": design[
                    "denominator_max_absolute_error"
                ],
                "maximum_response_p95_scale_normalized_absolute_error": max(
                    row["response_p95_scale_normalized_absolute_error"] for row in rows
                ),
                "maximum_response_max_scale_normalized_absolute_error": max(
                    row["response_max_scale_normalized_absolute_error"] for row in rows
                ),
                "maximum_qstar_p95_loading_scale_normalized_absolute_error": max(
                    row["qstar_p95_loading_scale_normalized_absolute_error"]
                    for row in rows
                ),
                "maximum_qstar_max_loading_scale_normalized_absolute_error": max(
                    row["qstar_max_loading_scale_normalized_absolute_error"]
                    for row in rows
                ),
                "maximum_ldf_next_p95_loading_scale_normalized_absolute_error": max(
                    row["ldf_next_p95_loading_scale_normalized_absolute_error"]
                    for row in rows
                ),
                "maximum_ldf_next_max_loading_scale_normalized_absolute_error": max(
                    row["ldf_next_max_loading_scale_normalized_absolute_error"]
                    for row in rows
                ),
                "all_components_pass": bool(
                    all(row["passes_declared_precision_gate"] for row in rows)
                ),
            }
            screens.append(screen)
            if chosen_design is None and screen["all_components_pass"]:
                chosen_design = design
                chosen_rows = rows
    if chosen_design is None or chosen_rows is None:
        raise AssertionError(screens)

    compiled_rows: list[dict] = []
    response_layouts: list[dict] = []
    consumer_layouts: list[dict] = []
    if not args.screen_only:
        if args.componentwise_compile:
            prior_checkpoint = None
            if CHECKPOINT_JSON.exists():
                prior_checkpoint = json.loads(
                    CHECKPOINT_JSON.read_text(encoding="utf-8")
                )
            elif OUT_JSON.exists():
                prior_checkpoint = json.loads(OUT_JSON.read_text(encoding="utf-8"))
            if prior_checkpoint is not None:
                prior_design = prior_checkpoint.get(
                    "selected_dynamic_response_design", {}
                )
                if (
                    int(prior_design.get("affinity_bits", -1))
                    == int(chosen_design["affinity_bits"])
                    and int(prior_design.get("denominator_address_bits", -1))
                    == int(chosen_design["denominator_address_bits"])
                ):
                    compiled_rows = list(
                        prior_checkpoint.get(
                            "componentwise_compiled_direct_paths", []
                        )
                    )
                    response_layouts = list(
                        prior_checkpoint.get("dynamic_response_layouts", [])
                    )
                    consumer_layouts = list(
                        prior_checkpoint.get("componentwise_layouts", [])
                    )
            completed = {row["component"] for row in compiled_rows}
            indices = [
                index
                for index, component in enumerate(COMPONENTS)
                if component not in completed
            ]
        else:
            indices = [0]
        for component_index in indices:
            response_module, response_layout = build_dynamic_response_module(
                chosen_design, component_index
            )
            circuit, consumer_layout = build_component_circuit(
                context,
                bundle,
                selected_components,
                component_index,
                response_module=response_module,
                response_module_layout=response_layout,
            )
            compiled = transpile(
                circuit,
                basis_gates=["u", "cx"],
                optimization_level=1,
                seed_transpiler=TRANSPILER_SEED,
            )
            resources = resource_record(compiled, COMPONENTS[component_index])
            if resources["measurement"] or resources["reset"]:
                raise AssertionError(resources)
            compiled_rows.append(resources)
            response_layouts.append(response_layout)
            consumer_layouts.append(consumer_layout)
            CHECKPOINT_JSON.write_text(
                json.dumps(
                    {
                        "selected_dynamic_response_design": serializable_design(
                            chosen_design
                        ),
                        "componentwise_compiled_direct_paths": compiled_rows,
                        "dynamic_response_layouts": response_layouts,
                        "componentwise_layouts": consumer_layouts,
                    },
                    ensure_ascii=False,
                    indent=2,
                    default=lambda value: value.item()
                    if isinstance(value, np.generic)
                    else str(value),
                )
                + "\n",
                encoding="utf-8",
            )
            del response_module, circuit, compiled
            gc.collect()

    upper_bound = None
    if compiled_rows:
        upper_bound = {
            "logical_qubits_peak": max(row["logical_qubits"] for row in compiled_rows),
            "depth_all_to_all_additive_upper_bound": sum(
                row["depth_all_to_all"] for row in compiled_rows
            ),
            "cx_additive_upper_bound": sum(row["cx"] for row in compiled_rows),
            "u_additive_upper_bound": sum(row["u"] for row in compiled_rows),
            "common_controller_repeated_per_component": True,
            "monolithic_five_component_transpile": False,
        }

    payload = {
        "schema": "psa-qae-cce-coherent-dynamic-langmuir-ldf-balance-interface/v1",
        "status": (
            "dynamic_run_affinity_langmuir_response_consumed_in_five_compiled_component_paths"
            if len(compiled_rows) == len(COMPONENTS)
            else "dynamic_run_affinity_langmuir_precision_pass_componentwise_compile_pending"
        ),
        "qpu_submission": False,
        "support": {
            "runs": 32,
            "physical_records_per_component": int(len(context.current_loading)),
            "component_balance_records_checked": int(
                len(context.current_loading) * len(COMPONENTS)
            ),
            "components": list(COMPONENTS),
        },
        "selected_dynamic_response_design": serializable_design(chosen_design),
        "precision_screen": screens,
        "components": chosen_rows,
        "dynamic_response_layouts": response_layouts,
        "componentwise_layouts": consumer_layouts,
        "componentwise_compiled_direct_paths": compiled_rows,
        "conservative_five_component_upper_bound": upper_bound,
        "cleanliness_by_construction": {
            "retained": [
                "run, stage and bed addresses",
                "20-bit pressure and five 20-bit composition inputs",
                "current loading, current gas and two face-flux inputs",
                "next loading and next gas outputs",
            ],
            "cleared": [
                "run-affinity fixed-point decode",
                "affinity sum, denominator address and reciprocal",
                "numerator and response products",
                "all controller, qstar, LDF, loading-transfer and balance workspace",
            ],
        },
        "claim_boundary": {
            "supported": "direct all-to-all u/CX composition from coherent run/stage control and supplied 20-bit pressure/compositions through a dynamically generated run-affinity Langmuir denominator/reciprocal, generated response, qstar, schedule-gated LDF loading update, loading-sign conversion and one conservative component gas balance",
            "unsupported": "gas normalization from raw component amounts, face generation, off-ledger tank demand, a monolithic five-component transpilation, adaptive phase/cycle integration, routed hardware feasibility, external H2 validation, or quantum advantage",
        },
    }
    RESULTS.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            default=lambda value: value.item()
            if isinstance(value, np.generic)
            else str(value),
        )
        + "\n",
        encoding="utf-8",
    )
    with OUT_CSV.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(chosen_rows[0]))
        writer.writeheader()
        writer.writerows(chosen_rows)

    lines = [
        "# Coherent dynamic-Langmuir-to-LDF/loading/balance interface",
        "",
        f"Status: **{payload['status']}**",
        "",
        "The controller's retained 12-bit run-affinity word and supplied 20-bit pressure/five-component composition now generate the competitive-Langmuir denominator and reciprocal inside each clean component path. The generated response is consumed directly by the run-specific equilibrium coefficient, LDF loading update, loading-sign conversion and conservative gas balance.",
        "",
        f"Selected design: **{chosen_design['affinity_bits']} affinity bits**, **{chosen_design['denominator_address_bits']} denominator-address bits** ({chosen_design['reciprocal_segments']:,} reciprocal segments).",
        "",
        "| component | response p95/max | q* p95/max | LDF-next p95/max | next-gas p95/max | pass |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for row in chosen_rows:
        lines.append(
            f"| {row['component']} | "
            f"{row['response_p95_scale_normalized_absolute_error']:.3e}/"
            f"{row['response_max_scale_normalized_absolute_error']:.3e} | "
            f"{row['qstar_p95_loading_scale_normalized_absolute_error']:.3e}/"
            f"{row['qstar_max_loading_scale_normalized_absolute_error']:.3e} | "
            f"{row['ldf_next_p95_loading_scale_normalized_absolute_error']:.3e}/"
            f"{row['ldf_next_max_loading_scale_normalized_absolute_error']:.3e} | "
            f"{row['next_gas_p95_scale_normalized_absolute_error']:.3e}/"
            f"{row['next_gas_max_scale_normalized_absolute_error']:.3e} | "
            f"{row['passes_declared_precision_gate']} |"
        )
    if compiled_rows:
        lines += [
            "",
            "| compiled component path | logical qubits | depth | CX |",
            "|---|---:|---:|---:|",
        ]
        for row in compiled_rows:
            lines.append(
                f"| {row['component']} | {row['logical_qubits']:,} | "
                f"{row['depth_all_to_all']:,} | {row['cx']:,} |"
            )
    lines += [
        "",
        "Gas normalization, face generation, off-ledger tank demand, monolithic five-component phase/cycle integration, routing, hardware feasibility, external H2 validation and quantum advantage remain open.",
        "",
        "No QPU job was submitted.",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    if len(compiled_rows) == len(COMPONENTS) and CHECKPOINT_JSON.exists():
        CHECKPOINT_JSON.unlink()
    print(
        json.dumps(
            {
                "status": payload["status"],
                "selected_affinity_bits": chosen_design["affinity_bits"],
                "selected_address_bits": chosen_design["denominator_address_bits"],
                "compiled_paths": len(compiled_rows),
                "qpu_submission": False,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
