"""Consume coherent run coefficients in a schedule-gated LDF/balance path.

The finite-support controller already maps a five-qubit run address to the
capacity, affinity, and LDF factors and then generates five equilibrium
prefactors and five LDF-alpha coefficients.  This audit composes that exact
controller with five componentwise state-update circuits.  Each circuit
consumes a 20-bit competitive-Langmuir response

    rho_i = P*y_i / (1 + P*sum_j(b_j*y_j))

and the run-generated equilibrium prefactor to produce q_i_star.  A bed/stage
decoder masks the run-generated LDF-alpha coefficient outside adsorption.
The resulting loading update is connected to reversible loading-sign/solid-
mass conversion and one conservative component gas balance.  All controller,
coefficient, product, loading-transfer, and balance workspaces are reversed;
run/stage/bed, physical inputs, q_next, and next-gas outputs remain.

The 20-bit rho input, current gas, and two face-flux terms are supplied at this
tier.  Dynamic affinity-denominator construction from pressure/composition,
gas normalization and face generation, off-ledger tank demand, monolithic
five-component compilation, phase integration, routing, and hardware
feasibility remain open.  No QPU work is submitted.
"""

from __future__ import annotations

import argparse
import csv
import gc
import json
from pathlib import Path

import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit.circuit.library import ModularAdderGate, MultiplierGate, WeightedAdder

from cce_primary_coherent_run_factor_ldf_interface import (
    COEFFICIENT_SCALE,
    COEFFICIENT_SCALE_BITS,
    component_weights,
    integer_weights_for_affine,
    integer_weights_for_affine_product,
    product_weighted_code,
    weighted_code,
    build_circuit as build_controller_circuit,
)
from cce_primary_coherent_run_schedule_tank_interface import (
    COMPONENTS,
    LEDGER,
    PARAMETERS,
    PARAMETER_BITS,
    RESULTS,
    SCHEDULE,
    make_schedule_rows,
    parameter_tables,
)
from cce_primary_internal_face_balance_composition import (
    MAX_NEXT_SCALE_NORMALIZED_GATE,
    P95_NEXT_SCALE_NORMALIZED_GATE,
)
from cce_primary_joint_normalized_transport_ldf_balance import (
    RECORDS_PER_RUN,
    load_context,
    transfer_selected,
)
from cce_primary_loading_sign_balance_interface import (
    build_sign_split_compute,
    build_loading_to_terms,
    register_indices,
)
from cce_primary_qstar_ldf_reversible_microstep import physical_constants
from psa_spatial_network_probe_n2 import LDF


OUT_JSON = RESULTS / "PSA_QAE_CCE_COHERENT_COEFFICIENT_LDF_BALANCE_INTERFACE.json"
OUT_CSV = RESULTS / "PSA_QAE_CCE_COHERENT_COEFFICIENT_LDF_BALANCE_INTERFACE.csv"
OUT_MD = RESULTS / "PSA_QAE_CCE_COHERENT_COEFFICIENT_LDF_BALANCE_INTERFACE.md"
PRIOR_JOINT_JSON = RESULTS / "PSA_QAE_CCE_PRIMARY_JOINT_NORMALIZED_TRANSPORT_LDF_BALANCE.json"

RESPONSE_BITS = 20
RESPONSE_LEVELS = (1 << RESPONSE_BITS) - 1
TRANSPILER_SEED = 20261010
QSTAR_P95_LOADING_SCALE_GATE = 5.0e-4
QSTAR_MAX_LOADING_SCALE_GATE = 7.5e-4
LDF_P95_LOADING_SCALE_GATE = 2.5e-4
LDF_MAX_LOADING_SCALE_GATE = 5.0e-4


def controller_bundle() -> dict:
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    runs = sorted(ledger["runs"], key=lambda row: int(row["sample"]))
    if len(runs) != 32 or [int(row["sample"]) for row in runs] != list(range(32)):
        raise AssertionError("expected contiguous 32-run support")
    tables, parameter_rows, parameter_precision = parameter_tables(runs)
    schedule_table, schedule_rows = make_schedule_rows()
    by_name = {row["parameter"]: row for row in parameter_rows}
    capacity_row = by_name["capacity_factor"]
    affinity_row = by_name["affinity_factor"]
    ldf_row = by_name["ldf_factor"]
    factor_weights = integer_weights_for_affine_product(
        float(capacity_row["support_min"]),
        float(capacity_row["support_span"]),
        float(affinity_row["support_min"]),
        float(affinity_row["support_span"]),
    )
    ldf_factor_weights = integer_weights_for_affine(
        float(ldf_row["support_min"]), float(ldf_row["support_span"])
    )
    factor_product_adder = WeightedAdder(len(factor_weights), factor_weights)
    ldf_factor_adder = WeightedAdder(len(ldf_factor_weights), ldf_factor_weights)
    constants = physical_constants()
    equilibrium_base = np.asarray(constants["qcap"], dtype=float) * np.asarray(
        constants["affinity"], dtype=float
    )
    alpha_base = np.asarray(LDF, dtype=float)
    equilibrium_weights = component_weights(
        factor_product_adder.num_sum_qubits, equilibrium_base
    )
    alpha_weights = component_weights(ldf_factor_adder.num_sum_qubits, alpha_base)
    equilibrium_adders = [WeightedAdder(len(row), row) for row in equilibrium_weights]
    alpha_adders = [WeightedAdder(len(row), row) for row in alpha_weights]
    controller, layout = build_controller_circuit(
        tables,
        schedule_table,
        factor_product_adder,
        ldf_factor_adder,
        equilibrium_adders,
        alpha_adders,
    )

    equilibrium_codes = np.zeros((len(runs), len(COMPONENTS)), dtype=object)
    alpha_codes = np.zeros((len(runs), len(COMPONENTS)), dtype=object)
    for run_index in range(len(runs)):
        factor_code = product_weighted_code(
            int(tables["capacity_factor"][run_index]),
            int(tables["affinity_factor"][run_index]),
            factor_weights,
        )
        ldf_factor_code = weighted_code(
            int(tables["ldf_factor"][run_index]),
            ldf_factor_weights,
            constant=True,
        )
        for component_index in range(len(COMPONENTS)):
            equilibrium_codes[run_index, component_index] = weighted_code(
                factor_code, equilibrium_weights[component_index]
            )
            alpha_codes[run_index, component_index] = weighted_code(
                ldf_factor_code, alpha_weights[component_index]
            )
    return {
        "controller": controller,
        "layout": layout,
        "runs": runs,
        "tables": tables,
        "parameter_precision": parameter_precision,
        "schedule_rows": schedule_rows,
        "equilibrium_codes": equilibrium_codes,
        "alpha_codes": alpha_codes,
        "equilibrium_base": equilibrium_base,
        "alpha_base": alpha_base,
    }


def qstar_rescale_weights(
    coefficient_bits: int,
    loading_bits: int,
    response_scale: float,
    loading_scale: float,
) -> list[int]:
    loading_levels = (1 << loading_bits) - 1
    factor = (
        float(response_scale)
        * loading_levels
        / (COEFFICIENT_SCALE * RESPONSE_LEVELS * float(loading_scale))
    )
    return [
        int(round((1 << bit) * factor))
        for bit in range(coefficient_bits + RESPONSE_BITS)
    ]


def weighted_values(values: np.ndarray, weights: list[int]) -> np.ndarray:
    return np.asarray(
        [
            sum(
                int(weight)
                for bit, weight in enumerate(weights)
                if (int(value) >> bit) & 1
            )
            for value in values
        ],
        dtype=object,
    )


def component_precision_rows(
    context,
    bundle: dict,
    selected: list[dict],
    response_codes_by_component: list[np.ndarray] | None = None,
) -> list[dict]:
    constants = context.base_constants
    affinity = np.asarray(constants["affinity"], dtype=float)
    qcap = np.asarray(constants["qcap"], dtype=float)
    pressure = np.asarray(context.terms["pressure_triplet"][:, 1], dtype=float)
    composition = np.asarray(context.terms["composition_pair"][:, 1, :], dtype=float)
    state_samples = np.repeat(np.asarray(context.samples, dtype=int), RECORDS_PER_RUN)
    capacity_factor = np.repeat(context.factors[:, 0], RECORDS_PER_RUN)
    affinity_factor = np.repeat(context.factors[:, 1], RECORDS_PER_RUN)
    ldf_factor = np.repeat(context.factors[:, 2], RECORDS_PER_RUN)
    denominator = 1.0 + pressure * np.sum(
        composition * affinity[None, :] * affinity_factor[:, None], axis=1
    )
    response_scale = float(context.normalized["selected_pressure"]["pressure_scale_bar"])
    rows: list[dict] = []
    for component_index, component in enumerate(COMPONENTS):
        selected_row = selected[component_index]
        loading_bits = int(selected_row["loading_bits"])
        loading_levels = (1 << loading_bits) - 1
        loading_scale = float(selected_row["loading_scale_mol_per_kg"])
        response_exact = pressure * composition[:, component_index] / denominator
        if response_codes_by_component is None:
            response_code = np.rint(
                response_exact / response_scale * RESPONSE_LEVELS
            ).astype(object)
        else:
            response_code = np.asarray(
                response_codes_by_component[component_index], dtype=object
            )
            if response_code.shape != response_exact.shape:
                raise AssertionError(
                    (component, response_code.shape, response_exact.shape)
                )
        if np.any(np.asarray(response_code, dtype=float) > RESPONSE_LEVELS):
            raise AssertionError((component, "response overflow"))
        response_approx = (
            np.asarray(response_code, dtype=float) / RESPONSE_LEVELS * response_scale
        )
        equilibrium_code = np.asarray(
            [
                int(bundle["equilibrium_codes"][sample, component_index])
                for sample in state_samples
            ],
            dtype=object,
        )
        alpha_code = np.asarray(
            [
                int(bundle["alpha_codes"][sample, component_index])
                for sample in state_samples
            ],
            dtype=object,
        )
        product_code = response_code * equilibrium_code
        weights = qstar_rescale_weights(
            int(bundle["layout"]["equilibrium_prefactor_bits_per_component"]),
            loading_bits,
            response_scale,
            loading_scale,
        )
        qstar_code = weighted_values(product_code, weights)
        qstar_approx = (
            np.asarray(qstar_code, dtype=float) / loading_levels * loading_scale
        )
        qstar_exact = (
            qcap[component_index]
            * capacity_factor
            * affinity[component_index]
            * affinity_factor
            * response_exact
        )
        current_code = np.rint(
            context.current_loading[:, component_index]
            / loading_scale
            * loading_levels
        ).astype(object)
        qstar_minus_current = qstar_code - current_code
        qstar_adsorption = np.maximum(qstar_minus_current, 0)
        qstar_desorption = np.maximum(-qstar_minus_current, 0)
        round_up = (1 << COEFFICIENT_SCALE_BITS) - 1
        alpha_adsorption = np.asarray(
            [
                (
                    int(alpha_code[index]) * int(qstar_adsorption[index])
                    + round_up
                )
                >> COEFFICIENT_SCALE_BITS
                for index in range(len(qstar_code))
            ],
            dtype=object,
        )
        alpha_desorption = np.asarray(
            [
                (
                    int(alpha_code[index]) * int(qstar_desorption[index])
                    + round_up
                )
                >> COEFFICIENT_SCALE_BITS
                for index in range(len(qstar_code))
            ],
            dtype=object,
        )
        next_loading_code = current_code + alpha_adsorption - alpha_desorption
        next_loading_approx = (
            np.asarray(next_loading_code, dtype=float)
            / loading_levels
            * loading_scale
        )
        next_loading_exact = context.current_loading[:, component_index] + (
            np.asarray(LDF, dtype=float)[component_index]
            * ldf_factor
            * (qstar_exact - context.current_loading[:, component_index])
        )
        response_error = np.abs(response_approx - response_exact) / response_scale
        qstar_error = np.abs(qstar_approx - qstar_exact) / loading_scale
        next_loading_error = (
            np.abs(next_loading_approx - next_loading_exact) / loading_scale
        )

        signed_change = next_loading_code - current_code
        exact_change = next_loading_exact - context.current_loading[:, component_index]
        adsorption_magnitude = np.maximum(signed_change, 0)
        desorption_magnitude = np.maximum(-signed_change, 0)
        adsorption_code = weighted_values(
            adsorption_magnitude,
            [int(value) for value in selected_row["adsorption_conversion_weights"]],
        )
        desorption_code = weighted_values(
            desorption_magnitude,
            [int(value) for value in selected_row["desorption_conversion_weights"]],
        )
        balance = context.normalized["selected_balance_rows"][component_index]
        positive = (
            weighted_values(
                context.gas_codes[:, 1, component_index],
                [int(value) for value in selected_row["gas_weights"]],
            )
            + weighted_values(
                context.face_flux_codes[:, 0, component_index],
                [int(value) for value in balance["direct_face_flux_weights"]],
            )
            + weighted_values(
                desorption_code,
                [int(value) for value in selected_row["desorption_balance_weights"]],
            )
        )
        negative = (
            weighted_values(
                context.face_flux_codes[:, 1, component_index],
                [int(value) for value in balance["direct_face_flux_weights"]],
            )
            + weighted_values(
                adsorption_code,
                [int(value) for value in selected_row["adsorption_balance_weights"]],
            )
        )
        next_gas_code = positive - negative
        next_gas_levels = (1 << int(balance["next_output_bits"])) - 1
        balance_scale = float(balance["balance_scale_mol"])
        next_gas_approx = (
            np.asarray(next_gas_code, dtype=float)
            / next_gas_levels
            * balance_scale
        )
        next_gas_error = (
            np.abs(next_gas_approx - context.terms["next_gas"][:, component_index])
            / balance_scale
        )
        exact_branch = np.sign(exact_change)
        implemented_branch = np.sign(np.asarray(signed_change, dtype=float))
        row = {
            "component": component,
            "component_index": component_index,
            "response_bits": RESPONSE_BITS,
            "equilibrium_coefficient_bits": int(
                bundle["layout"]["equilibrium_prefactor_bits_per_component"]
            ),
            "alpha_coefficient_bits": int(
                bundle["layout"]["ldf_alpha_bits_per_component"]
            ),
            "loading_bits": loading_bits,
            "response_scale_bar": response_scale,
            "loading_scale_mol_per_kg": loading_scale,
            "qstar_rescale_nonzero_weights": int(sum(value != 0 for value in weights)),
            "response_p95_scale_normalized_absolute_error": float(
                np.quantile(response_error, 0.95)
            ),
            "response_max_scale_normalized_absolute_error": float(
                np.max(response_error)
            ),
            "qstar_p95_loading_scale_normalized_absolute_error": float(
                np.quantile(qstar_error, 0.95)
            ),
            "qstar_max_loading_scale_normalized_absolute_error": float(
                np.max(qstar_error)
            ),
            "ldf_next_p95_loading_scale_normalized_absolute_error": float(
                np.quantile(next_loading_error, 0.95)
            ),
            "ldf_next_max_loading_scale_normalized_absolute_error": float(
                np.max(next_loading_error)
            ),
            "next_gas_p95_scale_normalized_absolute_error": float(
                np.quantile(next_gas_error, 0.95)
            ),
            "next_gas_max_scale_normalized_absolute_error": float(
                np.max(next_gas_error)
            ),
            "nonzero_response_erased_fraction": float(
                np.mean((response_exact > 0.0) & (np.asarray(response_code, dtype=float) == 0.0))
            ),
            "qstar_output_overflow_fraction": float(
                np.mean(np.asarray(qstar_code, dtype=float) > loading_levels)
            ),
            "next_loading_underflow_fraction": float(
                np.mean(np.asarray(next_loading_code, dtype=float) < 0.0)
            ),
            "next_loading_overflow_fraction": float(
                np.mean(np.asarray(next_loading_code, dtype=float) > loading_levels)
            ),
            "signed_change_branch_mismatch_fraction": float(
                np.mean(exact_branch != implemented_branch)
            ),
            "nonzero_quantized_transfer_erased_fraction": float(
                np.mean(
                    (np.asarray(qstar_minus_current, dtype=float) != 0.0)
                    & (np.asarray(signed_change, dtype=float) == 0.0)
                )
            ),
            "next_gas_underflow_fraction": float(
                np.mean(np.asarray(next_gas_code, dtype=float) < 0.0)
            ),
            "next_gas_overflow_fraction": float(
                np.mean(np.asarray(next_gas_code, dtype=float) > next_gas_levels)
            ),
            "physical_records_checked": int(len(response_exact)),
        }
        row["passes_declared_precision_gate"] = bool(
            row["qstar_p95_loading_scale_normalized_absolute_error"]
            <= QSTAR_P95_LOADING_SCALE_GATE
            and row["qstar_max_loading_scale_normalized_absolute_error"]
            <= QSTAR_MAX_LOADING_SCALE_GATE
            and row["ldf_next_p95_loading_scale_normalized_absolute_error"]
            <= LDF_P95_LOADING_SCALE_GATE
            and row["ldf_next_max_loading_scale_normalized_absolute_error"]
            <= LDF_MAX_LOADING_SCALE_GATE
            and row["next_gas_p95_scale_normalized_absolute_error"]
            <= P95_NEXT_SCALE_NORMALIZED_GATE
            and row["next_gas_max_scale_normalized_absolute_error"]
            <= MAX_NEXT_SCALE_NORMALIZED_GATE
            and row["nonzero_response_erased_fraction"] == 0.0
            and row["qstar_output_overflow_fraction"] == 0.0
            and row["next_loading_underflow_fraction"] == 0.0
            and row["next_loading_overflow_fraction"] == 0.0
            and row["nonzero_quantized_transfer_erased_fraction"] == 0.0
            and row["next_gas_underflow_fraction"] == 0.0
            and row["next_gas_overflow_fraction"] == 0.0
        )
        rows.append(row)
    return rows


def build_component_circuit(
    context,
    bundle: dict,
    selected: list[dict],
    component_index: int,
    response_module: QuantumCircuit | None = None,
    response_module_layout: dict | None = None,
) -> tuple[QuantumCircuit, dict]:
    if (response_module is None) != (response_module_layout is None):
        raise ValueError("response_module and response_module_layout must be paired")
    controller = bundle["controller"]
    controller_layout = bundle["layout"]
    component = COMPONENTS[component_index]
    selected_row = selected[component_index]
    loading_bits = int(selected_row["loading_bits"])
    coefficient_bits = int(
        controller_layout["equilibrium_prefactor_bits_per_component"]
    )
    alpha_bits = int(controller_layout["ldf_alpha_bits_per_component"])
    response_scale = float(context.normalized["selected_pressure"]["pressure_scale_bar"])
    loading_scale = float(selected_row["loading_scale_mol_per_kg"])
    qstar_weights = qstar_rescale_weights(
        coefficient_bits, loading_bits, response_scale, loading_scale
    )
    qstar_adder = WeightedAdder(len(qstar_weights), qstar_weights)
    coefficient_multiplier = MultiplierGate(
        coefficient_bits, coefficient_bits + RESPONSE_BITS
    )
    alpha_multiplier = MultiplierGate(
        loading_bits, loading_bits + alpha_bits
    )
    loading_adder = ModularAdderGate(loading_bits)
    sign_split, sign_layout = build_sign_split_compute(loading_bits)
    alpha_product_bits = loading_bits + alpha_bits
    product_rounding_adder = ModularAdderGate(alpha_product_bits)

    transfer_spec = transfer_selected(
        selected_row, context.sign["components"][component_index]
    )
    transfer, _ = build_loading_to_terms(transfer_spec)
    balance = context.normalized["selected_balance_rows"][component_index]
    positive_weights = (
        [int(value) for value in selected_row["gas_weights"]]
        + [int(value) for value in balance["direct_face_flux_weights"]]
        + [int(value) for value in selected_row["desorption_balance_weights"]]
    )
    negative_weights = (
        [int(value) for value in balance["direct_face_flux_weights"]]
        + [int(value) for value in selected_row["adsorption_balance_weights"]]
    )
    positive_adder = WeightedAdder(len(positive_weights), positive_weights)
    negative_adder = WeightedAdder(len(negative_weights), negative_weights)
    common_bits = max(
        positive_adder.num_sum_qubits,
        negative_adder.num_sum_qubits,
        int(balance["next_output_bits"]),
    )

    next_index = controller.num_qubits

    def allocate(size: int) -> list[int]:
        nonlocal next_index
        result = list(range(next_index, next_index + int(size)))
        next_index += int(size)
        return result

    bed = allocate(1)
    pressure = allocate(RESPONSE_BITS) if response_module is not None else []
    composition = (
        allocate(len(COMPONENTS) * RESPONSE_BITS)
        if response_module is not None
        else []
    )
    response = allocate(RESPONSE_BITS)
    response_module_other_sources: list[int] = []
    response_module_other: list[int] = []
    if response_module is not None and response_module_layout is not None:
        response_module_fixed = set(
            response_module_layout["affinity_parameter"]
            + response_module_layout["pressure"]
            + response_module_layout["composition"]
            + response_module_layout["response"]
        )
        response_module_other_sources = [
            index
            for index in range(response_module.num_qubits)
            if index not in response_module_fixed
        ]
        response_module_other = allocate(len(response_module_other_sources))
    response_pad = allocate(coefficient_bits - RESPONSE_BITS)
    current_loading = allocate(loading_bits)
    qstar = allocate(loading_bits)
    next_loading = allocate(loading_bits)
    active = allocate(1)
    active_alpha = allocate(alpha_bits)
    alpha_pad = allocate(loading_bits - alpha_bits)
    coefficient_product = allocate(coefficient_bits + RESPONSE_BITS)
    qstar_sum = allocate(qstar_adder.num_sum_qubits)
    qstar_work = allocate(qstar_adder.num_ancillas)
    alpha_product = allocate(alpha_product_bits)
    rounding_constant = allocate(alpha_product_bits)
    sign_fixed = set(sign_layout["q_current"]) | set(sign_layout["q_next"])
    sign_other_sources = [
        index for index in range(sign_split.num_qubits) if index not in sign_fixed
    ]
    sign_other = allocate(len(sign_other_sources))

    transfer_fixed = set(register_indices(transfer, "q_current")) | set(
        register_indices(transfer, "q_next")
    )
    transfer_other_sources = [
        index for index in range(transfer.num_qubits) if index not in transfer_fixed
    ]
    transfer_other = allocate(len(transfer_other_sources))
    gas_bits = int(context.normalized["selected_pressure"]["gas_bits_per_component"])
    face_bits = int(context.normalized["selected_face"]["flow_register_bits"])
    current_gas = allocate(gas_bits)
    left_flux = allocate(face_bits)
    right_flux = allocate(face_bits)
    next_gas = allocate(int(balance["next_output_bits"]))
    positive_sum = allocate(positive_adder.num_sum_qubits)
    negative_sum = allocate(negative_adder.num_sum_qubits)
    positive_work = allocate(positive_adder.num_ancillas)
    negative_work = allocate(negative_adder.num_ancillas)
    negative_pad = allocate(common_bits - negative_adder.num_sum_qubits)
    balance_register = allocate(common_bits)

    circuit = QuantumCircuit(
        next_index,
        name=f"coherent_{component.lower()}_coefficient_ldf_loading_balance",
    )
    controller_map = list(range(controller.num_qubits))
    circuit.compose(controller, qubits=controller_map, inplace=True)
    stage = register_indices(controller, "stage")
    adsorption = register_indices(controller, "adsorption_active")
    equilibrium_all = register_indices(controller, "equilibrium_prefactor")
    alpha_all = register_indices(controller, "ldf_alpha")
    equilibrium = equilibrium_all[
        component_index * coefficient_bits : (component_index + 1) * coefficient_bits
    ]
    alpha = alpha_all[
        component_index * alpha_bits : (component_index + 1) * alpha_bits
    ]

    response_module_map: list[int] | None = None
    if response_module is not None and response_module_layout is not None:
        parameter = register_indices(controller, "parameter")
        affinity_start = PARAMETERS.index("affinity_factor") * PARAMETER_BITS
        affinity_parameter = parameter[
            affinity_start : affinity_start + PARAMETER_BITS
        ]
        response_module_map = [-1] * response_module.num_qubits
        for source, target in zip(
            response_module_layout["affinity_parameter"], affinity_parameter
        ):
            response_module_map[source] = target
        for source, target in zip(response_module_layout["pressure"], pressure):
            response_module_map[source] = target
        for source, target in zip(response_module_layout["composition"], composition):
            response_module_map[source] = target
        for source, target in zip(response_module_layout["response"], response):
            response_module_map[source] = target
        for source, target in zip(
            response_module_other_sources, response_module_other
        ):
            response_module_map[source] = target
        if any(index < 0 for index in response_module_map) or len(
            set(response_module_map)
        ) != len(response_module_map):
            raise AssertionError("invalid dynamic-response module map")
        circuit.compose(response_module, qubits=response_module_map, inplace=True)

    # Select the adsorption flag for the addressed bed.
    circuit.x(bed[0])
    circuit.ccx(adsorption[0], bed[0], active[0])
    circuit.x(bed[0])
    circuit.ccx(adsorption[1], bed[0], active[0])
    for source, target in zip(alpha, active_alpha):
        circuit.ccx(active[0], source, target)

    # Clean qstar oracle: equilibrium coefficient * 20-bit Langmuir response.
    coefficient_qargs = (
        equilibrium + response + response_pad + coefficient_product
    )
    qstar_qargs = (
        coefficient_product
        + qstar_sum[: qstar_adder.num_sum_qubits]
        + qstar_work[: qstar_adder.num_ancillas]
    )

    def append_qstar_oracle() -> None:
        circuit.append(coefficient_multiplier, coefficient_qargs)
        circuit.append(qstar_adder, qstar_qargs)
        for source, target in zip(qstar_sum, qstar):
            circuit.cx(source, target)
        circuit.append(qstar_adder.inverse(), qstar_qargs)
        circuit.append(coefficient_multiplier.inverse(), coefficient_qargs)

    append_qstar_oracle()

    # q_next = q_current + ceil(alpha*max(qstar-q_current, 0))
    #                    - ceil(alpha*max(q_current-qstar, 0)).
    # The sign split avoids cancellation between two separately truncated
    # products. Adding 2^20-1 before high-word extraction implements exact
    # ceiling division and preserves every nonzero quantized transfer.
    for source, target in zip(current_loading, next_loading):
        circuit.cx(source, target)
    sign_map = [-1] * sign_split.num_qubits
    for source, target in zip(sign_layout["q_current"], current_loading):
        sign_map[source] = target
    for source, target in zip(sign_layout["q_next"], qstar):
        sign_map[source] = target
    for source, target in zip(sign_other_sources, sign_other):
        sign_map[source] = target
    if any(index < 0 for index in sign_map) or len(set(sign_map)) != len(sign_map):
        raise AssertionError("invalid qstar-current sign-split map")
    circuit.compose(sign_split, qubits=sign_map, inplace=True)
    qstar_adsorption = [
        sign_map[index] for index in sign_layout["adsorption_magnitude"]
    ]
    qstar_desorption = [
        sign_map[index] for index in sign_layout["desorption_magnitude"]
    ]
    alpha_operand = active_alpha + alpha_pad
    alpha_high = alpha_product[
        COEFFICIENT_SCALE_BITS : COEFFICIENT_SCALE_BITS + loading_bits
    ]
    adsorption_alpha_qargs = alpha_operand + qstar_adsorption + alpha_product
    desorption_alpha_qargs = alpha_operand + qstar_desorption + alpha_product
    for qubit in rounding_constant[:COEFFICIENT_SCALE_BITS]:
        circuit.x(qubit)
    circuit.append(alpha_multiplier, adsorption_alpha_qargs)
    circuit.append(product_rounding_adder, rounding_constant + alpha_product)
    circuit.append(loading_adder, alpha_high + next_loading)
    circuit.append(
        product_rounding_adder.inverse(), rounding_constant + alpha_product
    )
    circuit.append(alpha_multiplier.inverse(), adsorption_alpha_qargs)
    circuit.append(alpha_multiplier, desorption_alpha_qargs)
    circuit.append(product_rounding_adder, rounding_constant + alpha_product)
    circuit.append(loading_adder.inverse(), alpha_high + next_loading)
    circuit.append(
        product_rounding_adder.inverse(), rounding_constant + alpha_product
    )
    circuit.append(alpha_multiplier.inverse(), desorption_alpha_qargs)
    for qubit in reversed(rounding_constant[:COEFFICIENT_SCALE_BITS]):
        circuit.x(qubit)
    circuit.compose(sign_split.inverse(), qubits=sign_map, inplace=True)

    transfer_map = [-1] * transfer.num_qubits
    for source, target in zip(
        register_indices(transfer, "q_current"), current_loading
    ):
        transfer_map[source] = target
    for source, target in zip(register_indices(transfer, "q_next"), next_loading):
        transfer_map[source] = target
    for source, target in zip(transfer_other_sources, transfer_other):
        transfer_map[source] = target
    if any(index < 0 for index in transfer_map) or len(set(transfer_map)) != len(
        transfer_map
    ):
        raise AssertionError("invalid loading-transfer map")
    circuit.compose(transfer, qubits=transfer_map, inplace=True)
    adsorption_term = [
        transfer_map[index] for index in register_indices(transfer, "adsorption_term")
    ]
    desorption_term = [
        transfer_map[index] for index in register_indices(transfer, "desorption_term")
    ]
    positive_state = current_gas + left_flux + desorption_term
    negative_state = right_flux + adsorption_term
    positive_qargs = positive_state + positive_sum + positive_work
    negative_qargs = negative_state + negative_sum + negative_work
    circuit.append(positive_adder, positive_qargs)
    circuit.append(negative_adder, negative_qargs)
    for source, target in zip(positive_sum, balance_register):
        circuit.cx(source, target)
    negative_operand = negative_sum + negative_pad
    balance_subtractor = ModularAdderGate(common_bits)
    circuit.append(balance_subtractor.inverse(), negative_operand + balance_register)
    for source, target in zip(balance_register, next_gas):
        circuit.cx(source, target)
    circuit.append(balance_subtractor, negative_operand + balance_register)
    for source, target in reversed(list(zip(positive_sum, balance_register))):
        circuit.cx(source, target)
    circuit.append(negative_adder.inverse(), negative_qargs)
    circuit.append(positive_adder.inverse(), positive_qargs)
    circuit.compose(transfer.inverse(), qubits=transfer_map, inplace=True)

    append_qstar_oracle()
    if response_module is not None and response_module_map is not None:
        circuit.compose(
            response_module.inverse(), qubits=response_module_map, inplace=True
        )
    for source, target in reversed(list(zip(alpha, active_alpha))):
        circuit.ccx(active[0], source, target)
    circuit.ccx(adsorption[1], bed[0], active[0])
    circuit.x(bed[0])
    circuit.ccx(adsorption[0], bed[0], active[0])
    circuit.x(bed[0])
    circuit.compose(controller.inverse(), qubits=controller_map, inplace=True)

    run = register_indices(controller, "run")
    retained = set(
        run
        + stage
        + bed
        + pressure
        + composition
        + ([] if response_module is not None else response)
        + current_loading
        + current_gas
        + left_flux
        + right_flux
        + next_loading
        + next_gas
    )
    layout = {
        "component": component,
        "run_address": run,
        "stage_address": stage,
        "bed_address": bed,
        "pressure_input": pressure,
        "composition_input": composition,
        "competitive_langmuir_response_input": (
            [] if response_module is not None else response
        ),
        "competitive_langmuir_response_generated": (
            response if response_module is not None else []
        ),
        "current_loading_input": current_loading,
        "next_loading_output": next_loading,
        "current_gas_input": current_gas,
        "left_flux_input": left_flux,
        "right_flux_input": right_flux,
        "next_gas_output": next_gas,
        "equilibrium_coefficient_bits": coefficient_bits,
        "alpha_coefficient_bits": alpha_bits,
        "qstar_rescale_sum_bits": qstar_adder.num_sum_qubits,
        "retained_input_output_qubits": len(retained),
        "cleared_workspace_qubits": circuit.num_qubits - len(retained),
        "controller_logical_qubits": controller.num_qubits,
        "directly_composed_modules": [
            "32-run parameter and six-stage paired-bed controller",
            "run-factor to five-component equilibrium/LDF coefficient arithmetic",
            "bed-selected adsorption mask",
            (
                "dynamic pressure/composition/run-affinity denominator and reciprocal"
                if response_module is not None
                else "supplied 20-bit competitive-Langmuir response"
            ),
            "20-bit Langmuir-response times run-specific equilibrium prefactor",
            "run-specific LDF loading update",
            "loading-sign and solid-mass conversion",
            "one conservative component gas balance",
            "exact reverse of balance, transfer, qstar, coefficient and controller workspaces",
        ],
    }
    return circuit, layout


def resource_record(compiled: QuantumCircuit, component: str) -> dict:
    counts = compiled.count_ops()
    return {
        "component": component,
        "logical_qubits": int(compiled.num_qubits),
        "depth_all_to_all": int(compiled.depth()),
        "cx": int(counts.get("cx", 0)),
        "u": int(counts.get("u", 0)),
        "measurement": int(counts.get("measure", 0)),
        "reset": int(counts.get("reset", 0)),
        "basis_gates": ["u", "cx"],
        "optimization_level": 1,
        "transpiler_seed": TRANSPILER_SEED,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--screen-only", action="store_true")
    parser.add_argument("--componentwise-compile", action="store_true")
    args = parser.parse_args()
    if args.screen_only and args.componentwise_compile:
        parser.error("--screen-only and --componentwise-compile are mutually exclusive")

    context = load_context()
    bundle = controller_bundle()
    prior = json.loads(PRIOR_JOINT_JSON.read_text(encoding="utf-8"))
    selected = prior["selected_components"]
    rows = component_precision_rows(context, bundle, selected)
    if not all(row["passes_declared_precision_gate"] for row in rows):
        raise AssertionError(rows)

    compiled_rows: list[dict] = []
    layouts: list[dict] = []
    if not args.screen_only:
        indices = list(range(len(COMPONENTS))) if args.componentwise_compile else [0]
        for component_index in indices:
            circuit, layout = build_component_circuit(
                context, bundle, selected, component_index
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
            layouts.append(layout)
            del circuit, compiled
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
        "schema": "psa-qae-cce-coherent-coefficient-ldf-balance-interface/v1",
        "status": (
            "coherent_run_coefficients_consumed_in_five_schedule_gated_component_ldf_loading_balance_paths_dynamic_denominator_open"
            if len(compiled_rows) == len(COMPONENTS)
            else "coherent_run_coefficient_consumer_screen_pass_componentwise_compile_pending"
        ),
        "qpu_submission": False,
        "support": {
            "runs": 32,
            "physical_records_per_component": int(len(context.current_loading)),
            "component_balance_records_checked": int(
                len(context.current_loading) * len(COMPONENTS)
            ),
            "schedule_addresses_checked": 8,
            "bed_stage_flags_checked": 16,
            "components": list(COMPONENTS),
        },
        "interface": {
            "response": "20-bit supplied rho_i=P*y_i/(1+P*sum_j(b_j*y_j))",
            "coefficient_scale_bits": COEFFICIENT_SCALE_BITS,
            "schedule_behavior": "the addressed bed's run-specific LDF-alpha coefficient is masked to zero outside adsorption",
            "output": "run- and schedule-dependent q_next plus one conservative next-gas component balance",
        },
        "precision_gates": {
            "qstar_p95_loading_scale_normalized_absolute_error_max": QSTAR_P95_LOADING_SCALE_GATE,
            "qstar_max_loading_scale_normalized_absolute_error_max": QSTAR_MAX_LOADING_SCALE_GATE,
            "ldf_next_p95_loading_scale_normalized_absolute_error_max": LDF_P95_LOADING_SCALE_GATE,
            "ldf_next_max_loading_scale_normalized_absolute_error_max": LDF_MAX_LOADING_SCALE_GATE,
            "next_gas_p95_scale_normalized_absolute_error_max": P95_NEXT_SCALE_NORMALIZED_GATE,
            "next_gas_max_scale_normalized_absolute_error_max": MAX_NEXT_SCALE_NORMALIZED_GATE,
            "erasure_underflow_overflow_required": 0.0,
        },
        "components": rows,
        "componentwise_layouts": layouts,
        "componentwise_compiled_direct_paths": compiled_rows,
        "conservative_five_component_upper_bound": upper_bound,
        "cleanliness_by_construction": {
            "retained": [
                "run, stage and bed addresses",
                "20-bit competitive-Langmuir response input",
                "current loading, current gas and two face-flux inputs",
                "next loading and next gas outputs",
            ],
            "cleared": [
                "eleven parameter words and decoded schedule",
                "capacity-affinity and LDF factors",
                "all five equilibrium and LDF-alpha coefficient registers",
                "qstar products and scaling workspace",
                "adsorption-mask and alpha products",
                "loading-sign, solid-conversion and balance workspace",
            ],
        },
        "claim_boundary": {
            "supported": "direct all-to-all u/CX composition from coherent run/stage control through generated equilibrium/LDF coefficients, supplied 20-bit Langmuir response, schedule-gated LDF loading update, loading-sign/solid conversion and one component gas balance, compiled separately for all five components",
            "unsupported": "dynamic construction of the affinity-dependent denominator and reciprocal from pressure/composition inside the same circuit, gas normalization, face generation, off-ledger tank demand, a monolithic five-component transpilation, adaptive phase/cycle integration, routing, hardware feasibility, external H2 validation, or quantum advantage",
        },
    }
    RESULTS.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    with OUT_CSV.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    lines = [
        "# Coherent coefficient-to-LDF/loading/balance interface",
        "",
        f"Status: **{payload['status']}**",
        "",
        "The five-qubit run address and three-qubit schedule address generate the run-specific equilibrium/LDF coefficients. A bed selector masks LDF uptake outside adsorption. Each component path consumes a supplied 20-bit Langmuir response, produces q*, updates loading, converts the loading change to a signed gas term, accumulates one conservative gas balance, and reverses all controller and arithmetic workspace.",
        "",
        "| component | response bits | loading bits | q* p95/max | LDF-next p95/max | next-gas p95/max | pass |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row['component']} | {row['response_bits']} | {row['loading_bits']} | "
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
        if upper_bound is not None:
            lines += [
                "",
                f"The componentwise repeated-controller upper bound is **{upper_bound['logical_qubits_peak']:,} peak logical qubits**, depth **{upper_bound['depth_all_to_all_additive_upper_bound']:,}**, and **{upper_bound['cx_additive_upper_bound']:,} additive CX**. It is not a monolithic five-component transpilation.",
            ]
    lines += [
        "",
        "The competitive-Langmuir response is supplied. Dynamic affinity-denominator/reciprocal construction, gas normalization, face generation, off-ledger tank demand, and phase/cycle integration remain open.",
        "",
        "No QPU job was submitted.",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": payload["status"],
                "components": len(rows),
                "compiled_paths": len(compiled_rows),
                "qpu_submission": False,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
