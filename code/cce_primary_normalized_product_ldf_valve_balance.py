"""Generate product composition, pressure, inward face, LDF, valve, and balance.

This frozen-support audit starts each factor-specialized component path from two
encoded five-component gas inventories and one current product-cell loading.
It normalizes both compositions, reconstructs both pressures, generates the
oriented inward face, evaluates the product-cell competitive-Langmuir/LDF and
outlet valve modules, accumulates one conservative product balance, copies the
next gas code, and exactly reverses every temporary module.  Compilation is
componentwise and no QPU work is submitted.
"""

from __future__ import annotations

import argparse
import csv
import gc
import json
from pathlib import Path

import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit.circuit.library import ModularAdderGate, WeightedAdder

from cce_primary_composition_normalized_internal_face_balance import (
    build_composition_normalizer,
    encoded_gas,
    normalization_design,
)
from cce_primary_internal_face_balance_composition import module_register_map
from cce_primary_internal_transport_reversible_microsteps import (
    build_face_circuit,
    build_pressure_circuit,
)
from cce_primary_joint_normalized_transport_ldf_balance import (
    JOINT_LDF_INPUT_BITS,
    direct_gas_weights,
    load_context,
    quantize_factors,
    specialized_constants,
)
from cce_primary_loading_sign_balance_interface import (
    build_loading_to_terms,
    conversion_weights,
    register_indices,
    weighted_code,
)
from cce_primary_product_boundary_balance_composition import (
    CACHE,
    PRODUCT_JSON,
    RESULTS,
    SOURCE,
    boundary_terms,
    source_rows,
)
from cce_primary_product_boundary_reversible_microsteps import (
    COMPOSITION_BITS,
    PRESSURE_BITS,
    TRANSPILER_SEED,
    build_valve_flux_circuit,
)
from cce_primary_product_ldf_valve_balance_composition import (
    JOINT_JSON,
    PRODUCT_BALANCE_JSON,
    RECORDS_PER_RUN,
    product_integer_inputs,
    product_loading_records,
    run_design,
    shared_pressure_valve_flux_codes,
)
from cce_primary_qstar_ldf_reversible_microstep import (
    build_clean_microstep,
    build_preparation,
)
from psa_spatial_network_probe_n2 import (
    COMPONENTS,
    SpatialParams,
    cell_pressure,
    cell_y,
)


NORMALIZED_JSON = (
    RESULTS / "PSA_QAE_CCE_PRIMARY_COMPOSITION_NORMALIZED_INTERNAL_FACE_BALANCE.json"
)
PRIOR_PRODUCT_JSON = (
    RESULTS / "PSA_QAE_CCE_PRIMARY_PRODUCT_LDF_VALVE_BALANCE_COMPOSITION.json"
)
OUT_JSON = RESULTS / "PSA_QAE_CCE_PRIMARY_NORMALIZED_PRODUCT_LDF_VALVE_BALANCE.json"
OUT_CSV = RESULTS / "PSA_QAE_CCE_PRIMARY_NORMALIZED_PRODUCT_LDF_VALVE_BALANCE.csv"
OUT_MD = RESULTS / "PSA_QAE_CCE_PRIMARY_NORMALIZED_PRODUCT_LDF_VALVE_BALANCE.md"

NORMALIZER_AMOUNT_BITS = 22
NORMALIZER_RECIPROCAL_BITS = 22
NORMALIZER_ADDRESS_BITS = 8
P95_NEXT_SCALE_NORMALIZED_GATE = 2.5e-4
MAX_NEXT_SCALE_NORMALIZED_GATE = 5.0e-4
ROUND_OFF_ZERO_MOL = 1.0e-15


def product_gas_support() -> dict[str, np.ndarray]:
    """Return upstream/product gas pairs in product-boundary record order."""

    cache = np.load(CACHE)
    samples = np.asarray(cache["samples"], dtype=int)
    boundaries = np.asarray(cache["boundaries"], dtype=float)
    if boundaries.shape != (32, 101, 85):
        raise AssertionError(boundaries.shape)
    rows = source_rows()
    gas_pairs: list[np.ndarray] = []
    pressures: list[np.ndarray] = []
    compositions: list[np.ndarray] = []
    run_indices: list[int] = []
    for run_index, sample in enumerate(samples):
        row = rows[int(sample)]
        params = SpatialParams(
            n_cells=4,
            P_high_bar=15.65,
            P_low_bar=float(row["P_low_bar"]),
            phase_duration_s=10.0,
            k_in_mol_s_bar=1.0,
            k_out_mol_s_bar=0.3,
            k_internal_mol_s_bar=5.0,
            capacity_factor=float(row["capacity_factor"]),
            affinity_factor=float(row["affinity_factor"]),
            ldf_factor=float(row["ldf_factor"]),
            max_step_points=12,
            solver_method="BDF",
        )
        for boundary in boundaries[run_index]:
            for offset in (0, 40):
                gas = boundary[offset : offset + 20].reshape(5, 4)
                gas_pair = gas[:, -2:].T
                gas_pairs.append(gas_pair)
                pressures.append(cell_pressure(gas, params)[-2:])
                compositions.append(cell_y(gas)[:, -2:].T)
                run_indices.append(run_index)
    result = {
        "gas_pair": np.asarray(gas_pairs, dtype=float),
        "exact_pressure_pair": np.asarray(pressures, dtype=float),
        "exact_composition_pair": np.asarray(compositions, dtype=float),
        "run_index": np.asarray(run_indices, dtype=int),
        "samples": samples,
    }
    if len(result["gas_pair"]) != len(samples) * RECORDS_PER_RUN:
        raise AssertionError(len(result["gas_pair"]))
    return result


def generated_process_codes(
    support: dict[str, np.ndarray],
    selected_pressure: dict,
    selected_face: dict,
) -> tuple[dict, dict]:
    """Evaluate the exact integer interface used by the composed circuit."""

    flat_gas = support["gas_pair"].reshape(-1, len(COMPONENTS))
    flat_exact_composition = support["exact_composition_pair"].reshape(
        -1, len(COMPONENTS)
    )
    normalization, composition_flat = normalization_design(
        flat_gas,
        flat_exact_composition,
        selected_pressure,
        NORMALIZER_AMOUNT_BITS,
        NORMALIZER_RECIPROCAL_BITS,
        NORMALIZER_ADDRESS_BITS,
        keep_circuit_constants=True,
    )
    state_count = len(support["gas_pair"])
    composition_codes = composition_flat.reshape(state_count, 2, len(COMPONENTS))
    gas_flat_codes, _, _ = encoded_gas(flat_gas, selected_pressure)
    gas_codes = gas_flat_codes.reshape(state_count, 2, len(COMPONENTS))
    gas_bits = int(selected_pressure["gas_bits_per_component"])
    pressure_codes = np.zeros((state_count, 2), dtype=np.int64)
    pressure_weights = [int(value) for value in selected_pressure["pressure_weights"]]
    for component in range(len(COMPONENTS)):
        for bit in range(gas_bits):
            pressure_codes += (
                ((gas_codes[:, :, component] >> bit) & 1)
                * pressure_weights[component * gas_bits + bit]
            )
    pressure_levels = (1 << int(selected_pressure["pressure_output_bits"])) - 1
    pressure_scale = float(selected_pressure["pressure_scale_bar"])
    pressure_approx = pressure_codes.astype(float) / pressure_levels * pressure_scale
    pressure_difference = pressure_codes[:, 0] - pressure_codes[:, 1]
    if np.any(pressure_difference < 0):
        raise AssertionError("product inward pressure difference underflows")
    flow_codes = np.zeros(state_count, dtype=np.int64)
    for bit, weight in enumerate(selected_face["flow_weights"]):
        flow_codes += ((pressure_difference >> bit) & 1) * int(weight)
    flux_codes = (
        flow_codes[:, None] * composition_codes[:, 0, :]
    ) >> int(selected_face["composition_bits_per_component"])
    flow_levels = (1 << int(selected_face["flow_effective_bits"])) - 1
    flow_scale = float(selected_face["flow_scale_mol_s"])
    flux_approx = flux_codes.astype(float) / flow_levels * flow_scale
    composition_levels = (
        1 << int(normalization["composition_output_bits_per_component"])
    ) - 1
    composition_approx = composition_codes.astype(float) / composition_levels
    exact_pressure = support["exact_pressure_pair"]
    exact_composition = support["exact_composition_pair"]
    diagnostics = {
        "normalization": normalization,
        "pressure_p95_scale_normalized_absolute_error": float(
            np.quantile(np.abs(pressure_approx - exact_pressure) / pressure_scale, 0.95)
        ),
        "pressure_max_scale_normalized_absolute_error": float(
            np.max(np.abs(pressure_approx - exact_pressure) / pressure_scale)
        ),
        "inward_face_component_p95_flow_scale_normalized_absolute_error": {
            component: float(
                np.quantile(
                    np.abs(flux_approx[:, index] - boundary_terms()["left_influx"][:, index])
                    / flow_scale,
                    0.95,
                )
            )
            for index, component in enumerate(COMPONENTS)
        },
        "inward_face_component_max_flow_scale_normalized_absolute_error": {
            component: float(
                np.max(
                    np.abs(flux_approx[:, index] - boundary_terms()["left_influx"][:, index])
                    / flow_scale
                )
            )
            for index, component in enumerate(COMPONENTS)
        },
        "pressure_difference_underflow_fraction": float(
            np.mean(pressure_difference < 0)
        ),
        "nonzero_inward_flux_erased_fraction": float(
            np.mean((boundary_terms()["left_influx"] > 0.0) & (flux_codes == 0))
        ),
        "composition_sum_p95_absolute_error": float(
            np.quantile(np.abs(np.sum(composition_approx, axis=2) - 1.0), 0.95)
        ),
    }
    return {
        "gas_codes": gas_codes,
        "composition_codes": composition_codes,
        "pressure_codes": pressure_codes,
        "pressure_approx": pressure_approx,
        "composition_approx": composition_approx,
        "flow_codes": flow_codes,
        "flux_codes": flux_codes.astype(np.int64),
        "flux_approx": flux_approx,
    }, diagnostics


def evaluate_component(
    context,
    exact_terms: dict[str, np.ndarray],
    generated: dict,
    loading: dict[str, np.ndarray],
    selected_pressure: dict,
    selected_face: dict,
    selected_valve: dict,
    product_row: dict,
    prior_row: dict,
    component_index: int,
) -> dict:
    """Audit one generated product path against the exact cached next gas."""

    component = COMPONENTS[component_index]
    generated_terms = {
        "pressure": generated["pressure_approx"][:, 1],
        "composition": generated["composition_approx"][:, 1, :],
    }
    loading_bits = int(prior_row["loading_bits"])
    address_bits = int(prior_row["address_bits"])
    coefficient_bits = int(prior_row["coefficient_bits"])
    affinity_bits = int(prior_row["affinity_bits"])
    factor_bits = int(prior_row["factor_bits"])
    loading_scale = float(prior_row["loading_scale_mol_per_kg"])
    run_designs: list[dict] = []
    run_diagnostics: list[dict] = []
    differences: list[np.ndarray] = []
    for run_index in range(len(context.samples)):
        design, difference, diagnostic, _, _ = run_design(
            context,
            generated_terms,
            loading,
            component_index,
            run_index,
            factor_bits,
            address_bits,
            coefficient_bits,
            affinity_bits,
            loading_bits,
            loading_scale,
        )
        run_designs.append(design)
        run_diagnostics.append(diagnostic)
        differences.append(difference)
    signed_difference = np.concatenate(differences)
    exact_change = (
        loading["exact_next_loading"][:, component_index]
        - loading["current_loading"][:, component_index]
    ) * loading["solid_mass"]
    exact_change[np.abs(exact_change) < ROUND_OFF_ZERO_MOL] = 0.0
    adsorption_magnitude = np.maximum(signed_difference, 0)
    desorption_magnitude = np.maximum(-signed_difference, 0)
    term_bits = int(product_row["input_bits_per_nonvalve_term"])
    term_levels = (1 << term_bits) - 1
    loading_levels = (1 << loading_bits) - 1
    solid_mass = float(loading["solid_mass"][0])
    approximate_adsorption = (
        adsorption_magnitude.astype(float)
        / loading_levels
        * loading_scale
        * solid_mass
    )
    approximate_desorption = (
        desorption_magnitude.astype(float)
        / loading_levels
        * loading_scale
        * solid_mass
    )
    adsorption_scale = 1.001 * max(
        float(product_row["term_scales_mol"]["adsorption"]),
        float(np.max(approximate_adsorption)),
    )
    desorption_scale = 1.001 * max(
        float(product_row["term_scales_mol"]["desorption"]),
        float(np.max(approximate_desorption)),
    )
    adsorption_conversion = conversion_weights(
        loading_bits, loading_scale, solid_mass, term_bits, adsorption_scale
    )
    desorption_conversion = conversion_weights(
        loading_bits, loading_scale, solid_mass, term_bits, desorption_scale
    )
    adsorption_code = weighted_code(adsorption_magnitude, adsorption_conversion)
    desorption_code = weighted_code(desorption_magnitude, desorption_conversion)
    output_bits = int(product_row["next_output_bits"])
    output_levels = (1 << output_bits) - 1
    balance_scale = float(product_row["balance_scale_mol"])

    def balance_weights(bits: int, scale: float, levels: int | None = None) -> list[int]:
        denominator = (1 << bits) - 1 if levels is None else int(levels)
        return [
            int(
                round(
                    (1 << bit)
                    / denominator
                    * scale
                    / balance_scale
                    * output_levels
                )
            )
            for bit in range(bits)
        ]

    adsorption_balance_weights = balance_weights(term_bits, adsorption_scale)
    desorption_balance_weights = balance_weights(term_bits, desorption_scale)
    gas_weights = direct_gas_weights(context, component_index, product_row)
    face_bits = int(selected_face["flow_register_bits"])
    face_levels = (1 << int(selected_face["flow_effective_bits"])) - 1
    face_weights = balance_weights(
        face_bits, float(selected_face["flow_scale_mol_s"]), face_levels
    )
    valve_weights = [int(value) for value in product_row["direct_outlet_flux_weights"]]
    current_balance = weighted_code(
        generated["gas_codes"][:, 1, component_index], gas_weights
    )
    inward_balance = weighted_code(
        generated["flux_codes"][:, component_index], face_weights
    )
    desorption_balance = weighted_code(desorption_code, desorption_balance_weights)
    adsorption_balance = weighted_code(adsorption_code, adsorption_balance_weights)
    valve_codes = shared_pressure_valve_flux_codes(
        context, selected_valve, generated_terms
    )
    valve_balance = weighted_code(valve_codes[:, component_index], valve_weights)
    positive = current_balance + inward_balance + desorption_balance
    negative = valve_balance + adsorption_balance
    next_code = positive - negative
    next_approx = next_code.astype(float) / output_levels * balance_scale
    exact_next = exact_terms["next_gas"][:, component_index]
    normalized_error = np.abs(next_approx - exact_next) / float(
        product_row["next_gas_scale_mol"]
    )
    branch_mismatch = np.sign(signed_difference) != np.sign(exact_change)
    nonzero = exact_change != 0.0
    result = {
        "component": component,
        "component_index": component_index,
        "factor_bits": factor_bits,
        "address_bits": address_bits,
        "coefficient_bits": coefficient_bits,
        "affinity_bits": affinity_bits,
        "loading_bits": loading_bits,
        "loading_scale_mol_per_kg": loading_scale,
        "term_bits": term_bits,
        "next_bits": output_bits,
        "cell_solid_mass_kg": solid_mass,
        "adsorption_term_scale_mol": adsorption_scale,
        "desorption_term_scale_mol": desorption_scale,
        "adsorption_conversion_weights": adsorption_conversion,
        "desorption_conversion_weights": desorption_conversion,
        "adsorption_balance_weights": adsorption_balance_weights,
        "desorption_balance_weights": desorption_balance_weights,
        "direct_product_gas_weights": gas_weights,
        "direct_inward_face_flux_weights": face_weights,
        "direct_valve_flux_weights": valve_weights,
        "next_p95_scale_normalized_absolute_error": float(
            np.quantile(normalized_error, 0.95)
        ),
        "next_max_scale_normalized_absolute_error": float(np.max(normalized_error)),
        "signed_change_branch_mismatch_fraction": float(np.mean(branch_mismatch)),
        "nonzero_transfer_erased_fraction": float(
            np.mean(nonzero & (signed_difference == 0))
        ),
        "adsorption_term_overflow_fraction": float(np.mean(adsorption_code > term_levels)),
        "desorption_term_overflow_fraction": float(np.mean(desorption_code > term_levels)),
        "negative_sum_underflow_fraction": float(np.mean(negative > positive)),
        "next_output_overflow_fraction": float(np.mean(next_code > output_levels)),
        "minimum_exact_next_gas_mol": float(np.min(exact_next)),
        "qstar_output_overflow_fraction_max_over_runs": max(
            row["qstar_output_overflow_fraction"] for row in run_diagnostics
        ),
        "loading_input_overflow_fraction_max_over_runs": max(
            row["loading_input_overflow_fraction"] for row in run_diagnostics
        ),
        "run_diagnostics": run_diagnostics,
        "run_designs": run_designs,
    }
    result["passes_normalized_product_balance_gate"] = bool(
        result["next_p95_scale_normalized_absolute_error"]
        <= P95_NEXT_SCALE_NORMALIZED_GATE
        and result["next_max_scale_normalized_absolute_error"]
        <= MAX_NEXT_SCALE_NORMALIZED_GATE
        and result["nonzero_transfer_erased_fraction"] == 0.0
        and result["adsorption_term_overflow_fraction"] == 0.0
        and result["desorption_term_overflow_fraction"] == 0.0
        and result["negative_sum_underflow_fraction"] == 0.0
        and result["next_output_overflow_fraction"] == 0.0
        and result["qstar_output_overflow_fraction_max_over_runs"] == 0.0
        and result["loading_input_overflow_fraction_max_over_runs"] == 0.0
        and result["minimum_exact_next_gas_mol"] > 0.0
    )
    return result


def build_component_circuit(
    context,
    generated: dict,
    loading: dict[str, np.ndarray],
    normalization: dict,
    selected_pressure: dict,
    selected_face: dict,
    selected_valve: dict,
    product_row: dict,
    component_row: dict,
    compile_run_index: int,
) -> tuple[QuantumCircuit, dict]:
    """Build one direct two-gas-inventory to next-product-gas path."""

    component_index = int(component_row["component_index"])
    component = COMPONENTS[component_index]
    slug = component.lower()
    normalizer, normalizer_layout = build_composition_normalizer(
        normalization, selected_pressure
    )
    pressure_module, pressure_layout = build_pressure_circuit(selected_pressure)
    face_module, face_layout = build_face_circuit(selected_face)
    valve, valve_layout = build_valve_flux_circuit(selected_valve)
    run_slice = slice(
        compile_run_index * RECORDS_PER_RUN,
        (compile_run_index + 1) * RECORDS_PER_RUN,
    )
    quantized = quantize_factors(
        context.factors, int(component_row["factor_bits"])
    )[compile_run_index]
    constants = specialized_constants(
        context,
        float(quantized[0]),
        float(quantized[1]),
        affinity_coefficient_bits=int(component_row["affinity_bits"]),
    )
    generated_terms = {
        "pressure": generated["pressure_approx"][:, 1],
        "composition": generated["composition_approx"][:, 1, :],
    }
    encoded = product_integer_inputs(
        context,
        constants,
        generated_terms["pressure"][run_slice],
        generated_terms["composition"][run_slice],
        component_index,
    )
    design = component_row["run_designs"][compile_run_index]
    ldf, ldf_layout = build_clean_microstep(
        constants,
        encoded,
        design,
        component_index,
        ldf_coefficient_bits=int(component_row["coefficient_bits"]),
        input_bits=JOINT_LDF_INPUT_BITS,
    )
    preparation, preparation_layout = build_preparation(
        constants,
        encoded,
        component_index,
        input_bits=JOINT_LDF_INPUT_BITS,
    )
    if preparation.num_qubits > ldf.num_qubits:
        raise AssertionError("preparation exceeds LDF module")
    del preparation
    transfer, transfer_layout = build_loading_to_terms(
        {
            "component": component,
            "loading_bits": int(component_row["loading_bits"]),
            "cell_balance_term_bits": int(component_row["term_bits"]),
            "adsorption_conversion_weights": component_row[
                "adsorption_conversion_weights"
            ],
            "desorption_conversion_weights": component_row[
                "desorption_conversion_weights"
            ],
        }
    )

    next_index = 0

    def allocate(size: int) -> list[int]:
        nonlocal next_index
        indices = list(range(next_index, next_index + size))
        next_index += size
        return indices

    gas_bits_total = len(register_indices(normalizer, "gas_components"))
    composition_bits_total = len(register_indices(normalizer, "composition"))
    pressure_bits = len(register_indices(pressure_module, "pressure"))
    face_flux_bits_total = len(register_indices(face_module, "component_flux"))
    face_bits = face_flux_bits_total // len(COMPONENTS)
    gas = [allocate(gas_bits_total) for _ in range(2)]
    compositions = [allocate(composition_bits_total) for _ in range(2)]
    normalizer_shared = {
        register.name: allocate(len(register))
        for register in normalizer.qregs
        if register.name not in {"gas_components", "composition"}
    }
    pressures = [allocate(pressure_bits) for _ in range(2)]
    pressure_shared = {
        register.name: allocate(len(register))
        for register in pressure_module.qregs
        if register.name not in {"gas_components", "pressure"}
    }
    face_flux = allocate(face_flux_bits_total)
    face_shared = {
        register.name: allocate(len(register))
        for register in face_module.qregs
        if register.name
        not in {"pressure_left", "pressure_right", "composition_left", "component_flux"}
    }
    current_loading = allocate(int(component_row["loading_bits"]))

    normalizer_maps = [
        module_register_map(
            normalizer,
            {"gas_components": gas[cell], "composition": compositions[cell]},
            normalizer_shared,
        )
        for cell in range(2)
    ]
    pressure_maps = [
        module_register_map(
            pressure_module,
            {"gas_components": gas[cell], "pressure": pressures[cell]},
            pressure_shared,
        )
        for cell in range(2)
    ]
    face_map = module_register_map(
        face_module,
        {
            "pressure_left": pressures[0],
            "pressure_right": pressures[1],
            "composition_left": compositions[0],
            "component_flux": face_flux,
        },
        face_shared,
    )

    ldf_map = [-1] * ldf.num_qubits
    pressure_target = pressures[1][pressure_bits - JOINT_LDF_INPUT_BITS :]
    composition_per_component = composition_bits_total // len(COMPONENTS)
    composition_target = [
        index
        for index_component in range(len(COMPONENTS))
        for index in compositions[1][
            index_component * composition_per_component
            + (composition_per_component - JOINT_LDF_INPUT_BITS) :
            (index_component + 1) * composition_per_component
        ]
    ]
    for source, target in zip(preparation_layout["pressure"], pressure_target):
        ldf_map[source] = target
    for source, target in zip(preparation_layout["composition"], composition_target):
        ldf_map[source] = target
    ldf_current = register_indices(ldf, f"q_{slug}")
    ldf_next = register_indices(ldf, f"q_{slug}_next")
    for source, target in zip(ldf_current, current_loading):
        ldf_map[source] = target
    for index in range(ldf.num_qubits):
        if ldf_map[index] < 0:
            ldf_map[index] = allocate(1)[0]
    if len(set(ldf_map)) != len(ldf_map):
        raise AssertionError("invalid LDF mapping")

    valve_map = [-1] * valve.num_qubits
    valve_pressure_target = pressures[1][pressure_bits - PRESSURE_BITS :]
    valve_composition_target = [
        index
        for index_component in range(len(COMPONENTS))
        for index in compositions[1][
            index_component * composition_per_component
            + (composition_per_component - COMPOSITION_BITS) :
            (index_component + 1) * composition_per_component
        ]
    ]
    for source, target in zip(register_indices(valve, "pressure"), valve_pressure_target):
        valve_map[source] = target
    for source, target in zip(
        register_indices(valve, "composition"), valve_composition_target
    ):
        valve_map[source] = target
    for index in range(valve.num_qubits):
        if valve_map[index] < 0:
            valve_map[index] = allocate(1)[0]
    if len(set(valve_map)) != len(valve_map):
        raise AssertionError("invalid valve mapping")

    transfer_map = [-1] * transfer.num_qubits
    for source, target in zip(register_indices(transfer, "q_current"), current_loading):
        transfer_map[source] = target
    ldf_next_target = [ldf_map[index] for index in ldf_next]
    for source, target in zip(register_indices(transfer, "q_next"), ldf_next_target):
        transfer_map[source] = target
    for index in range(transfer.num_qubits):
        if transfer_map[index] < 0:
            transfer_map[index] = allocate(1)[0]
    if len(set(transfer_map)) != len(transfer_map):
        raise AssertionError("invalid transfer mapping")

    gas_bits = int(selected_pressure["gas_bits_per_component"])
    product_gas_component = gas[1][
        component_index * gas_bits : (component_index + 1) * gas_bits
    ]
    component_face = face_flux[
        component_index * face_bits : (component_index + 1) * face_bits
    ]
    valve_flux_all = [
        valve_map[index] for index in register_indices(valve, "component_flux")
    ]
    valve_bits = int(selected_valve["flow_bits"])
    component_valve = valve_flux_all[
        component_index * valve_bits : (component_index + 1) * valve_bits
    ]
    transfer_terms = {
        name: [transfer_map[index] for index in register_indices(transfer, name)]
        for name in ("desorption_term", "adsorption_term")
    }
    positive_weights = (
        [int(value) for value in component_row["direct_product_gas_weights"]]
        + [int(value) for value in component_row["direct_inward_face_flux_weights"]]
        + [int(value) for value in component_row["desorption_balance_weights"]]
    )
    negative_weights = (
        [int(value) for value in component_row["direct_valve_flux_weights"]]
        + [int(value) for value in component_row["adsorption_balance_weights"]]
    )
    positive_adder = WeightedAdder(len(positive_weights), positive_weights)
    negative_adder = WeightedAdder(len(negative_weights), negative_weights)
    positive_sum = allocate(positive_adder.num_sum_qubits)
    negative_sum = allocate(negative_adder.num_sum_qubits)
    positive_work = allocate(positive_adder.num_ancillas)
    negative_work = allocate(negative_adder.num_ancillas)
    common_bits = max(
        positive_adder.num_sum_qubits,
        negative_adder.num_sum_qubits,
        int(product_row["next_output_bits"]),
    )
    negative_pad = allocate(common_bits - negative_adder.num_sum_qubits)
    balance = allocate(common_bits)
    next_gas = allocate(int(product_row["next_output_bits"]))

    circuit = QuantumCircuit(
        next_index, name=f"clean_normalized_product_{slug}_balance"
    )
    for mapping in normalizer_maps:
        circuit.compose(normalizer, qubits=mapping, inplace=True)
    for mapping in pressure_maps:
        circuit.compose(pressure_module, qubits=mapping, inplace=True)
    circuit.compose(face_module, qubits=face_map, inplace=True)
    circuit.compose(ldf, qubits=ldf_map, inplace=True)
    circuit.compose(valve, qubits=valve_map, inplace=True)
    circuit.compose(transfer, qubits=transfer_map, inplace=True)
    positive_qargs = (
        product_gas_component
        + component_face
        + transfer_terms["desorption_term"]
        + positive_sum
        + positive_work
    )
    negative_qargs = (
        component_valve
        + transfer_terms["adsorption_term"]
        + negative_sum
        + negative_work
    )
    circuit.append(positive_adder, positive_qargs)
    circuit.append(negative_adder, negative_qargs)
    for source, target in zip(positive_sum, balance):
        circuit.cx(source, target)
    negative_operand = negative_sum + negative_pad
    subtractor = ModularAdderGate(common_bits)
    circuit.append(subtractor.inverse(), negative_operand + balance)
    for source, target in zip(balance, next_gas):
        circuit.cx(source, target)
    circuit.append(subtractor, negative_operand + balance)
    for source, target in reversed(list(zip(positive_sum, balance))):
        circuit.cx(source, target)
    circuit.append(negative_adder.inverse(), negative_qargs)
    circuit.append(positive_adder.inverse(), positive_qargs)
    circuit.compose(transfer.inverse(), qubits=transfer_map, inplace=True)
    circuit.compose(valve.inverse(), qubits=valve_map, inplace=True)
    circuit.compose(ldf.inverse(), qubits=ldf_map, inplace=True)
    circuit.compose(face_module.inverse(), qubits=face_map, inplace=True)
    for mapping in reversed(pressure_maps):
        circuit.compose(pressure_module.inverse(), qubits=mapping, inplace=True)
    for mapping in reversed(normalizer_maps):
        circuit.compose(normalizer.inverse(), qubits=mapping, inplace=True)

    retained = sorted(
        set(gas[0] + gas[1] + current_loading + next_gas)
    )
    if set(compositions[0] + compositions[1]) & set(retained):
        raise AssertionError("temporary composition retained")
    if set(face_flux) & set(retained):
        raise AssertionError("temporary face retained")
    return circuit, {
        "component": component,
        "compile_run_index": int(compile_run_index),
        "compile_sample": int(context.samples[compile_run_index]),
        "two_gas_inventory_inputs": gas,
        "current_loading_input": current_loading,
        "next_gas_output": next_gas,
        "temporary_compositions": compositions,
        "temporary_pressures": pressures,
        "temporary_inward_component_fluxes": face_flux,
        "temporary_next_loading": ldf_next_target,
        "temporary_valve_component_flux": component_valve,
        "retained_input_output_qubits": len(retained),
        "cleared_workspace_qubits": circuit.num_qubits - len(retained),
        "normalizer_layout": normalizer_layout,
        "pressure_layout": pressure_layout,
        "face_layout": face_layout,
        "ldf_layout": ldf_layout,
        "valve_layout": valve_layout,
        "transfer_layout": transfer_layout,
        "quantized_factors": quantized.tolist(),
        "directly_composed_modules": [
            "two support-adaptive gas-composition normalizers",
            "two five-component gas-to-pressure reconstructions",
            "one oriented five-component inward-face generator",
            "one factor-specialized competitive-Langmuir/LDF microstep",
            "one product-valve five-component flux generator",
            "one loading-sign and solid-mass conversion interface",
            "one conservative product-cell component balance",
            "exact reverse of every temporary module",
        ],
    }


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
    parser.add_argument(
        "--componentwise-compile",
        action="store_true",
        help="transpile the five factor-specialized component paths sequentially",
    )
    parser.add_argument(
        "--component-cache-dir",
        type=Path,
        help="merge five previously compiled <component>.json resource/layout caches",
    )
    args = parser.parse_args()
    context = load_context()
    normalized = json.loads(NORMALIZED_JSON.read_text(encoding="utf-8"))
    product = json.loads(PRODUCT_JSON.read_text(encoding="utf-8"))
    product_balance = json.loads(PRODUCT_BALANCE_JSON.read_text(encoding="utf-8"))
    prior = json.loads(PRIOR_PRODUCT_JSON.read_text(encoding="utf-8"))
    support = product_gas_support()
    exact_terms = boundary_terms()
    loading = product_loading_records()
    selected_pressure = normalized["selected_pressure"]
    selected_face = normalized["selected_face"]
    selected_valve = product["selected_valve"]
    product_rows = [row["selected"] for row in product_balance["components"]]
    generated, generated_diagnostics = generated_process_codes(
        support, selected_pressure, selected_face
    )
    if not generated_diagnostics["normalization"]["passes_composition_precision_gate"]:
        raise AssertionError("product-support normalization precision gate failed")
    selected_components: list[dict] = []
    for component_index, component in enumerate(COMPONENTS):
        row = evaluate_component(
            context,
            exact_terms,
            generated,
            loading,
            selected_pressure,
            selected_face,
            selected_valve,
            product_rows[component_index],
            prior["selected_components"][component_index],
            component_index,
        )
        if not row["passes_normalized_product_balance_gate"]:
            raise AssertionError((component, row))
        selected_components.append(row)
        print(
            json.dumps(
                {
                    "component": component,
                    "next_p95": row["next_p95_scale_normalized_absolute_error"],
                    "next_max": row["next_max_scale_normalized_absolute_error"],
                    "passes": True,
                }
            ),
            flush=True,
        )
    compile_run_index = max(
        range(len(context.samples)),
        key=lambda run: max(
            row["run_diagnostics"][run]["ldf_next_p95_loading_scale_error"]
            for row in selected_components
        ),
    )
    compile_score = max(
        row["run_diagnostics"][compile_run_index]["ldf_next_p95_loading_scale_error"]
        for row in selected_components
    )
    compiled_rows: list[dict] = []
    layouts: list[dict] = []
    if args.component_cache_dir:
        for component in COMPONENTS:
            cached = json.loads(
                (args.component_cache_dir / f"{component}.json").read_text(
                    encoding="utf-8"
                )
            )
            resources = cached["resources"]
            if resources["component"] != component:
                raise AssertionError((component, resources))
            if resources["measurement"] or resources["reset"]:
                raise AssertionError(resources)
            compiled_rows.append(resources)
            layouts.append(cached["layout"])
            print(json.dumps(resources), flush=True)
    elif args.componentwise_compile:
        for component_index, component in enumerate(COMPONENTS):
            circuit, layout = build_component_circuit(
                context,
                generated,
                loading,
                generated_diagnostics["normalization"],
                selected_pressure,
                selected_face,
                selected_valve,
                product_rows[component_index],
                selected_components[component_index],
                compile_run_index,
            )
            compiled = transpile(
                circuit,
                basis_gates=["u", "cx"],
                optimization_level=1,
                seed_transpiler=TRANSPILER_SEED,
            )
            resources = resource_record(compiled, component)
            if resources["measurement"] or resources["reset"]:
                raise AssertionError(resources)
            compiled_rows.append(resources)
            layouts.append(layout)
            print(json.dumps(resources), flush=True)
            del compiled, circuit
            gc.collect()
    upper = None
    if compiled_rows:
        upper = {
            "accounting": "five one-component gas-inventory-to-product-balance paths executed sequentially; common composition, pressure, face, and valve modules are repeated, so sums are conservative upper bounds rather than a monolithic five-component transpilation",
            "logical_qubits_peak": max(row["logical_qubits"] for row in compiled_rows),
            "depth_all_to_all_additive_upper_bound": sum(
                row["depth_all_to_all"] for row in compiled_rows
            ),
            "cx_additive_upper_bound": sum(row["cx"] for row in compiled_rows),
            "u_additive_upper_bound": sum(row["u"] for row in compiled_rows),
            "monolithic_five_component_transpile": False,
        }
    serializable_components = []
    flat_rows = []
    for row in selected_components:
        serializable = {key: value for key, value in row.items() if key != "run_designs"}
        serializable["compiled_run_design"] = row["run_designs"][compile_run_index]
        serializable_components.append(serializable)
        flat_rows.append(
            {
                "component": row["component"],
                "factor_bits": row["factor_bits"],
                "address_bits": row["address_bits"],
                "loading_bits": row["loading_bits"],
                "next_p95_scale_error": row[
                    "next_p95_scale_normalized_absolute_error"
                ],
                "next_max_scale_error": row[
                    "next_max_scale_normalized_absolute_error"
                ],
                "transfer_erasure": row["nonzero_transfer_erased_fraction"],
                "underflow": row["negative_sum_underflow_fraction"],
                "overflow": row["next_output_overflow_fraction"],
                "passes": row["passes_normalized_product_balance_gate"],
            }
        )
    payload = {
        "schema": "psa-qae-cce-primary-normalized-product-ldf-valve-balance/v1",
        "status": (
            "two_gas_inventory_componentwise_product_paths_compiled_monolithic_open"
            if compiled_rows
            else "precision_pass_componentwise_compile_pending"
        ),
        "qpu_submission": False,
        "physical_state_source": {
            "runs": 32,
            "cycles_per_run": 100,
            "beds": 2,
            "product_end_states": int(len(exact_terms["next_gas"])),
            "component_balances": int(len(exact_terms["next_gas"]) * len(COMPONENTS)),
            "input_gas_inventories_per_state": 2,
        },
        "normalizer_selection": {
            "amount_bits": NORMALIZER_AMOUNT_BITS,
            "reciprocal_bits": NORMALIZER_RECIPROCAL_BITS,
            "address_bits": NORMALIZER_ADDRESS_BITS,
        },
        "generated_process_diagnostics": generated_diagnostics,
        "precision_gate": {
            "next_p95_scale_normalized_absolute_error_max": P95_NEXT_SCALE_NORMALIZED_GATE,
            "next_max_scale_normalized_absolute_error_max": MAX_NEXT_SCALE_NORMALIZED_GATE,
            "nonzero_transfer_erasure_required": 0.0,
            "underflow_overflow_required": 0.0,
        },
        "selected_components": serializable_components,
        "compile_run_selection": {
            "criterion": "maximum selected componentwise generated-input product-support p95 LDF loading-scale error",
            "run_index": int(compile_run_index),
            "sample": int(context.samples[compile_run_index]),
            "score": float(compile_score),
        },
        "componentwise_direct_layouts": layouts,
        "componentwise_compiled_direct_paths": compiled_rows,
        "conservative_five_component_upper_bound": upper,
        "accuracy_boundary": "all cached product-end states use two encoded gas inventories to generate both normalized compositions and pressures, one inward face, the product LDF and valve, and one conservative component balance; circuits remain factor-specialized and compiled componentwise",
        "claim_boundary": {
            "supported": "frozen-support precision audit and direct all-to-all u/CX compilation of factor-specialized one-component paths from two five-component gas inventories and one current loading through normalized compositions, reconstructed pressures, generated inward face, competitive-Langmuir/LDF, product valve, loading conversion, and one conservative product-cell balance",
            "unsupported": "coherent run-parameter loading, monolithic five-component transpilation, valve scheduling, tank withdrawal, adaptive phase integration, complete phase/cycle control and routing, hardware feasibility, or quantum advantage",
        },
    }
    OUT_JSON.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    with OUT_CSV.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(flat_rows[0]))
        writer.writeheader()
        writer.writerows(flat_rows)
    lines = [
        "# Gas-inventory-generated product-cell LDF, valve, and balance",
        "",
        f"The frozen audit covers **{len(exact_terms['next_gas']):,} product-end states** and **{len(exact_terms['next_gas']) * len(COMPONENTS):,} component balances**. Each path starts from two encoded five-component gas inventories and one current loading; both compositions and pressures, the inward face, product LDF transfer, and valve withdrawal are generated inside the reversible path. No QPU job was submitted.",
        "",
        "| Component | factor bits | address bits | loading bits | next-gas p95 | next-gas max | erasure | underflow |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in flat_rows:
        lines.append(
            f"| {row['component']} | {row['factor_bits']} | {row['address_bits']} | {row['loading_bits']} | {row['next_p95_scale_error']:.3e} | {row['next_max_scale_error']:.3e} | {row['transfer_erasure']:.3e} | {row['underflow']:.3e} |"
        )
    if compiled_rows:
        lines += [
            "",
            "| Component | logical qubits | depth | CX | u |",
            "|---|---:|---:|---:|---:|",
        ]
        for row in compiled_rows:
            lines.append(
                f"| {row['component']} | {row['logical_qubits']:,} | {row['depth_all_to_all']:,} | {row['cx']:,} | {row['u']:,} |"
            )
        lines += [
            "",
            f"The conservative common-path-repeating upper bound is **{upper['logical_qubits_peak']:,} peak logical qubits**, all-to-all depth **{upper['depth_all_to_all_additive_upper_bound']:,}**, and **{upper['cx_additive_upper_bound']:,} additive CX**.",
        ]
    lines += [
        "",
        "This closes the previous product-path gap in which product composition and inward-face flux were supplied. Coherent run parameters, a monolithic five-component transpilation, valve scheduling, tank withdrawal, adaptive integration, full phase/cycle control, routing, hardware feasibility, and quantum advantage remain open.",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": payload["status"],
                "states": len(exact_terms["next_gas"]),
                "compiled_paths": len(compiled_rows),
                "upper_bound": upper,
                "qpu_submission": False,
            },
            indent=2,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
