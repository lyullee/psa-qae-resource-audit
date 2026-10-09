"""Compose product-cell LDF uptake and valve withdrawal in one clean balance.

The existing product-boundary circuit computes the nonlinear outlet law and
uses the resulting five component-flux registers in conservative product-cell
balances, but adsorption/desorption remained supplied inputs.  This audit
replaces those two inputs with a factor-specialized competitive-Langmuir/LDF
microstep.  For each component it shares the same encoded product pressure and
five-component composition between the LDF and valve modules, maps the generated
current/next loading registers through sign splitting and solid-mass conversion,
uses the generated adsorption/desorption and outlet-flux registers in the same
one-second balance, copies next gas, and exactly reverses all work.

The frozen precision audit covers all 32 runs, 101 cached cycle boundaries, and
both beds.  Resource compilation is componentwise so that the common five-flux
valve path is intentionally repeated in the conservative additive upper bound.
Composition normalization from gas inventories, generation of the inward face,
a coherent run-parameter register, valve scheduling, tank withdrawal, adaptive
phase integration, routing, and a complete cycle remain outside this circuit.
No QPU work is submitted.
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

from cce_primary_joint_normalized_transport_ldf_balance import (
    JOINT_LDF_INPUT_BITS,
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
    encode_term,
    source_rows,
)
from cce_primary_product_boundary_reversible_microsteps import (
    COMPOSITION_BITS,
    PRESSURE_BITS,
    TRANSPILER_SEED,
    build_valve_flux_circuit,
)
from cce_primary_qstar_ldf_reversible_microstep import (
    LDF,
    build_clean_microstep,
    build_preparation,
    reciprocal_table,
)
from psa_spatial_network_probe_n2 import (
    COMPONENTS,
    SpatialParams,
    cell_pressure,
    cell_y,
    profile_cell_volumes,
    profile_parameter_arrays,
    qstar,
)


HERE = Path(__file__).resolve().parent
PRODUCT_BALANCE_JSON = (
    RESULTS / "PSA_QAE_CCE_PRIMARY_PRODUCT_BOUNDARY_BALANCE_COMPOSITION.json"
)
JOINT_JSON = RESULTS / "PSA_QAE_CCE_PRIMARY_JOINT_NORMALIZED_TRANSPORT_LDF_BALANCE.json"
OUT_JSON = RESULTS / "PSA_QAE_CCE_PRIMARY_PRODUCT_LDF_VALVE_BALANCE_COMPOSITION.json"
OUT_CSV = RESULTS / "PSA_QAE_CCE_PRIMARY_PRODUCT_LDF_VALVE_BALANCE_COMPOSITION.csv"
OUT_MD = RESULTS / "PSA_QAE_CCE_PRIMARY_PRODUCT_LDF_VALVE_BALANCE_COMPOSITION.md"

RECORDS_PER_RUN = 202
P95_NEXT_SCALE_NORMALIZED_GATE = 2.5e-4
MAX_NEXT_SCALE_NORMALIZED_GATE = 5.0e-4
ROUND_OFF_ZERO_MOL = 1.0e-15
MAX_LOADING_BITS = 42
MAX_ADDRESS_BITS = 12
MAX_COEFFICIENT_BITS = 13


def product_loading_records() -> dict[str, np.ndarray]:
    """Return product-cell loading pairs in product-boundary balance order."""

    cache = np.load(CACHE)
    samples = np.asarray(cache["samples"], dtype=int)
    boundaries = np.asarray(cache["boundaries"], dtype=float)
    if boundaries.shape != (32, 101, 85):
        raise AssertionError(boundaries.shape)
    rows = source_rows()
    current: list[np.ndarray] = []
    following: list[np.ndarray] = []
    solid_mass: list[float] = []
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
        _, solid = profile_cell_volumes(params)
        *_, kinetic = profile_parameter_arrays(params)
        for boundary in boundaries[run_index]:
            for offset in (0, 40):
                gas = boundary[offset : offset + 20].reshape(5, 4)
                loading = boundary[offset + 20 : offset + 40].reshape(5, 4)
                pressure = cell_pressure(gas, params)
                composition = cell_y(gas)
                loading_next = loading + params.ldf_factor * kinetic * (
                    qstar(pressure, composition, params) - loading
                )
                current.append(loading[:, -1])
                following.append(loading_next[:, -1])
                solid_mass.append(float(solid[-1]))
                run_indices.append(run_index)
    result = {
        "current_loading": np.asarray(current, dtype=float),
        "exact_next_loading": np.asarray(following, dtype=float),
        "solid_mass": np.asarray(solid_mass, dtype=float),
        "run_index": np.asarray(run_indices, dtype=int),
        "samples": samples,
    }
    if len(result["current_loading"]) != len(samples) * RECORDS_PER_RUN:
        raise AssertionError(len(result["current_loading"]))
    if float(np.ptp(result["solid_mass"])) > 1.0e-12:
        raise AssertionError("product-cell solid mass is not constant")
    return result


def product_integer_inputs(
    context,
    constants: dict,
    pressure: np.ndarray,
    composition: np.ndarray,
    component_index: int,
) -> dict:
    levels = (1 << JOINT_LDF_INPUT_BITS) - 1
    coefficient_levels = (
        1 << int(constants.get("affinity_coefficient_bits", 8))
    ) - 1
    pressure_scale = float(context.normalized["selected_pressure"]["pressure_scale_bar"])
    pressure_code = np.rint(pressure / pressure_scale * levels).astype(np.int64)
    composition_code = np.rint(composition * levels).astype(np.int64)
    affinity = np.asarray(constants["affinity"], dtype=float)
    affinity_integer = np.asarray(constants["affinity_integer"], dtype=int)
    affinity_sum = np.zeros(len(pressure_code), dtype=np.int64)
    for component in range(len(COMPONENTS)):
        affinity_sum += composition_code[:, component] * int(
            affinity_integer[component]
        )
    denominator_scale = levels * levels * coefficient_levels / (
        pressure_scale * float(np.max(affinity))
    )
    denominator_one_code = int(round(denominator_scale))
    denominator_code = denominator_one_code + pressure_code * affinity_sum
    numerator_code = (
        pressure_code.astype(object)
        * composition_code[:, component_index].astype(object)
    )
    return {
        "levels": levels,
        "pressure_max": pressure_scale,
        "pressure_code": pressure_code,
        "composition_code": composition_code,
        "affinity_sum_code": affinity_sum,
        "denominator_scale": float(denominator_scale),
        "denominator_one_code": denominator_one_code,
        "denominator_code": denominator_code,
        "numerator_code": numerator_code,
    }


def shared_pressure_valve_flux_codes(
    context,
    selected_valve: dict,
    terms: dict[str, np.ndarray],
) -> np.ndarray:
    """Evaluate valve codes from the high bits of the shared 20-bit pressure."""

    if JOINT_LDF_INPUT_BITS < PRESSURE_BITS:
        raise AssertionError((JOINT_LDF_INPUT_BITS, PRESSURE_BITS))
    pressure_scale = float(
        context.normalized["selected_pressure"]["pressure_scale_bar"]
    )
    if abs(pressure_scale - float(selected_valve["pressure_scale_bar"])) > 1.0e-12:
        raise AssertionError("LDF and valve pressure scales differ")
    joint_levels = (1 << JOINT_LDF_INPUT_BITS) - 1
    pressure_code_joint = np.rint(
        terms["pressure"] / pressure_scale * joint_levels
    ).astype(np.int64)
    pressure_code_valve = pressure_code_joint >> (
        JOINT_LDF_INPUT_BITS - PRESSURE_BITS
    )
    address = pressure_code_valve >> (
        PRESSURE_BITS - int(selected_valve["valve_address_bits"])
    )
    table = np.asarray(selected_valve["flow_table_codes"], dtype=np.int64)
    flow_code = table[address]
    joint_composition_levels = (1 << JOINT_LDF_INPUT_BITS) - 1
    composition_code = np.rint(
        terms["composition"] * joint_composition_levels
    ).astype(np.int64) >> (JOINT_LDF_INPUT_BITS - COMPOSITION_BITS)
    return (flow_code[:, None] * composition_code) >> COMPOSITION_BITS


def run_design(
    context,
    terms: dict[str, np.ndarray],
    loading: dict[str, np.ndarray],
    component_index: int,
    run_index: int,
    factor_bits: int,
    address_bits: int,
    coefficient_bits: int,
    affinity_bits: int,
    loading_bits: int,
    loading_scale: float,
) -> tuple[dict, np.ndarray, dict, dict, dict]:
    """Build one product-support factor-specialized LDF design."""

    run_slice = slice(
        run_index * RECORDS_PER_RUN, (run_index + 1) * RECORDS_PER_RUN
    )
    quantized = quantize_factors(context.factors, factor_bits)[run_index]
    capacity, affinity_factor, ldf_factor = [float(value) for value in quantized]
    exact_capacity, exact_affinity, exact_ldf = [
        float(value) for value in context.factors[run_index]
    ]
    constants = specialized_constants(
        context,
        capacity,
        affinity_factor,
        affinity_coefficient_bits=affinity_bits,
    )
    pressure = np.asarray(terms["pressure"][run_slice], dtype=float)
    composition = np.asarray(terms["composition"][run_slice], dtype=float)
    encoded = product_integer_inputs(
        context, constants, pressure, composition, component_index
    )
    arithmetic_levels = (1 << loading_bits) - 1
    base_affinity = np.asarray(context.base_constants["affinity"], dtype=float)
    base_qcap = np.asarray(context.base_constants["qcap"], dtype=float)
    exact_denominator = 1.0 + pressure * np.sum(
        composition * (base_affinity * exact_affinity)[None, :], axis=1
    )
    denominator_physical = (
        np.asarray(encoded["denominator_code"], dtype=float)
        / float(encoded["denominator_scale"])
    )
    denominator_min = 1.0
    denominator_max = float(
        max(np.max(exact_denominator), np.max(denominator_physical))
    )
    address_levels = (1 << address_bits) - 1
    thresholds = [
        int(
            round(
                (
                    denominator_min
                    + (index - 0.5)
                    * (denominator_max - denominator_min)
                    / address_levels
                )
                * float(encoded["denominator_scale"])
            )
        )
        for index in range(1, address_levels + 1)
    ]
    address = np.searchsorted(
        np.asarray(thresholds, dtype=np.int64),
        np.asarray(encoded["denominator_code"], dtype=np.int64),
        side="right",
    )
    natural_scale = float(
        constants["qcap"][component_index]
        * constants["affinity"][component_index]
        * float(encoded["pressure_max"])
    )
    selected = {
        "component": COMPONENTS[component_index],
        "component_index": component_index,
        "arithmetic_bits": int(loading_bits),
        "denominator_address_bits": int(address_bits),
        "reciprocal_segments": 1 << address_bits,
        "ldf_coefficient_bits": int(coefficient_bits),
        "affinity_coefficient_bits": int(affinity_bits),
        "ldf_alpha_exact": float(LDF[component_index] * ldf_factor),
        "ldf_alpha_integer": int(
            round(float(LDF[component_index] * ldf_factor) * (1 << coefficient_bits))
        ),
        "natural_qstar_scale_mol_per_kg": natural_scale,
        "loading_scale_mol_per_kg": float(loading_scale),
        "reciprocal_scale_ratio": natural_scale / loading_scale,
        "denominator_range": [denominator_min, denominator_max],
        "denominator_threshold_codes": thresholds,
    }
    selected["ldf_alpha_implemented"] = selected["ldf_alpha_integer"] / (
        1 << coefficient_bits
    )
    table = reciprocal_table(selected)
    reciprocal_code = np.asarray([table[int(code)] for code in address], dtype=object)
    qstar_raw = np.asarray(
        [
            (
                int(encoded["numerator_code"][row])
                * int(reciprocal_code[row])
            )
            >> (2 * JOINT_LDF_INPUT_BITS)
            for row in range(RECORDS_PER_RUN)
        ],
        dtype=object,
    )
    qstar_overflow = np.asarray(
        [int(value) > arithmetic_levels for value in qstar_raw], dtype=bool
    )
    qstar_code = np.asarray(
        [int(value) & arithmetic_levels for value in qstar_raw], dtype=object
    )
    current_loading = loading["current_loading"][run_slice, component_index]
    current_code = np.rint(
        current_loading / loading_scale * arithmetic_levels
    ).astype(object)
    alpha = int(selected["ldf_alpha_integer"])
    retained = (1 << coefficient_bits) - alpha
    rounding = 1 << (coefficient_bits - 1)
    next_code = np.asarray(
        [
            (
                retained * int(current_code[row])
                + alpha * int(qstar_code[row])
                + rounding
            )
            >> coefficient_bits
            for row in range(RECORDS_PER_RUN)
        ],
        dtype=object,
    )
    exact_qstar = (
        base_qcap[component_index]
        * exact_capacity
        * base_affinity[component_index]
        * exact_affinity
        * pressure
        * composition[:, component_index]
        / exact_denominator
    )
    exact_next = current_loading + float(LDF[component_index] * exact_ldf) * (
        exact_qstar - current_loading
    )
    qstar_approx = (
        np.asarray(qstar_code, dtype=float) / arithmetic_levels * loading_scale
    )
    next_approx = (
        np.asarray(next_code, dtype=float) / arithmetic_levels * loading_scale
    )
    difference = np.asarray(next_code - current_code, dtype=np.int64)
    exact_difference = (
        loading["exact_next_loading"][run_slice, component_index]
        - current_loading
    )
    diagnostics = {
        "run_index": int(run_index),
        "sample": int(context.samples[run_index]),
        "factor_bits": int(factor_bits),
        "address_bits": int(address_bits),
        "coefficient_bits": int(coefficient_bits),
        "affinity_bits": int(affinity_bits),
        "exact_factors": context.factors[run_index].tolist(),
        "quantized_factors": quantized.tolist(),
        "qstar_p95_loading_scale_error": float(
            np.quantile(np.abs(qstar_approx - exact_qstar) / loading_scale, 0.95)
        ),
        "qstar_max_loading_scale_error": float(
            np.max(np.abs(qstar_approx - exact_qstar) / loading_scale)
        ),
        "ldf_next_p95_loading_scale_error": float(
            np.quantile(np.abs(next_approx - exact_next) / loading_scale, 0.95)
        ),
        "ldf_next_max_loading_scale_error": float(
            np.max(np.abs(next_approx - exact_next) / loading_scale)
        ),
        "qstar_output_overflow_fraction": float(np.mean(qstar_overflow)),
        "loading_input_overflow_fraction": float(
            np.mean(np.asarray(current_code, dtype=object) > arithmetic_levels)
        ),
        "signed_change_branch_mismatch_fraction": float(
            np.mean(np.sign(difference) != np.sign(exact_difference))
        ),
        "encoded_denominator_one_code": int(encoded["denominator_one_code"]),
        "encoded_denominator_scale": float(encoded["denominator_scale"]),
    }
    selected |= {
        "qstar_p95_loading_scale_normalized_absolute_error": diagnostics[
            "qstar_p95_loading_scale_error"
        ],
        "qstar_max_loading_scale_normalized_absolute_error": diagnostics[
            "qstar_max_loading_scale_error"
        ],
        "ldf_next_p95_loading_scale_normalized_absolute_error": diagnostics[
            "ldf_next_p95_loading_scale_error"
        ],
        "ldf_next_max_loading_scale_normalized_absolute_error": diagnostics[
            "ldf_next_max_loading_scale_error"
        ],
        "nonzero_qstar_erased_fraction": float(
            np.mean((exact_qstar > 0.0) & (np.asarray(qstar_code, dtype=float) == 0.0))
        ),
        "loading_input_overflow_fraction": diagnostics[
            "loading_input_overflow_fraction"
        ],
    }
    return selected, difference, diagnostics, constants, encoded


def evaluate_component(
    context,
    terms: dict[str, np.ndarray],
    loading: dict[str, np.ndarray],
    product_row: dict,
    joint_row: dict,
    component_index: int,
    loading_bits: int,
    address_bits: int,
) -> dict:
    component = COMPONENTS[component_index]
    loading_scale = max(
        float(joint_row["loading_scale_mol_per_kg"]),
        1.001
        * float(
            max(
                np.max(loading["current_loading"][:, component_index]),
                np.max(loading["exact_next_loading"][:, component_index]),
            )
        ),
    )
    run_designs: list[dict] = []
    run_diagnostics: list[dict] = []
    differences: list[np.ndarray] = []
    for run_index in range(len(context.samples)):
        design, difference, diagnostic, _, _ = run_design(
            context,
            terms,
            loading,
            component_index,
            run_index,
            int(joint_row["factor_bits"]),
            int(address_bits),
            int(joint_row["coefficient_bits"]),
            int(joint_row["affinity_bits"]),
            int(loading_bits),
            float(loading_scale),
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
    solid_mass = float(loading["solid_mass"][0])
    loading_levels = (1 << loading_bits) - 1
    approximate_adsorption_mol = (
        adsorption_magnitude.astype(float)
        / loading_levels
        * loading_scale
        * solid_mass
    )
    approximate_desorption_mol = (
        desorption_magnitude.astype(float)
        / loading_levels
        * loading_scale
        * solid_mass
    )
    adsorption_scale = 1.001 * max(
        float(product_row["term_scales_mol"]["adsorption"]),
        float(np.max(approximate_adsorption_mol)),
    )
    desorption_scale = 1.001 * max(
        float(product_row["term_scales_mol"]["desorption"]),
        float(np.max(approximate_desorption_mol)),
    )
    adsorption_weights = conversion_weights(
        loading_bits,
        loading_scale,
        solid_mass,
        term_bits,
        adsorption_scale,
    )
    desorption_weights = conversion_weights(
        loading_bits,
        loading_scale,
        solid_mass,
        term_bits,
        desorption_scale,
    )
    adsorption_code = weighted_code(adsorption_magnitude, adsorption_weights)
    desorption_code = weighted_code(desorption_magnitude, desorption_weights)
    input_bits = int(product_row["input_bits_per_nonvalve_term"])
    output_bits = int(product_row["next_output_bits"])
    output_levels = (1 << output_bits) - 1
    balance_scale = float(product_row["balance_scale_mol"])
    adsorption_balance_weights = [
        int(
            round(
                adsorption_scale
                / term_levels
                * (1 << bit)
                / balance_scale
                * output_levels
            )
        )
        for bit in range(term_bits)
    ]
    desorption_balance_weights = [
        int(
            round(
                desorption_scale
                / term_levels
                * (1 << bit)
                / balance_scale
                * output_levels
            )
        )
        for bit in range(term_bits)
    ]
    current_code, _ = encode_term(
        terms["current_gas"][:, component_index],
        float(product_row["term_scales_mol"]["current_gas"]),
        input_bits,
        output_bits,
        balance_scale,
    )
    left_code, _ = encode_term(
        terms["left_influx"][:, component_index],
        float(product_row["term_scales_mol"]["left_influx"]),
        input_bits,
        output_bits,
        balance_scale,
    )
    desorption_balance = weighted_code(
        desorption_code,
        desorption_balance_weights,
    )
    adsorption_balance = weighted_code(
        adsorption_code,
        adsorption_balance_weights,
    )
    product = json.loads(PRODUCT_JSON.read_text(encoding="utf-8"))
    selected_valve = product["selected_valve"]
    flux_codes = shared_pressure_valve_flux_codes(
        context, selected_valve, terms
    )
    valve_bits = int(selected_valve["flow_bits"])
    outlet_balance = weighted_code(
        flux_codes[:, component_index],
        [int(value) for value in product_row["direct_outlet_flux_weights"]],
    )
    positive = current_code + left_code + desorption_balance
    negative = outlet_balance + adsorption_balance
    next_code = positive - negative
    next_approx = next_code / output_levels * balance_scale
    exact_next = terms["next_gas"][:, component_index]
    normalized_error = np.abs(next_approx - exact_next) / float(
        product_row["next_gas_scale_mol"]
    )
    branch_mismatch = np.sign(signed_difference) != np.sign(exact_change)
    nonzero = exact_change != 0.0
    result = {
        "component": component,
        "component_index": component_index,
        "factor_bits": int(joint_row["factor_bits"]),
        "address_bits": int(address_bits),
        "coefficient_bits": int(joint_row["coefficient_bits"]),
        "affinity_bits": int(joint_row["affinity_bits"]),
        "loading_bits": int(loading_bits),
        "loading_scale_mol_per_kg": float(loading_scale),
        "term_bits": term_bits,
        "valve_flux_bits": valve_bits,
        "next_bits": output_bits,
        "cell_solid_mass_kg": solid_mass,
        "adsorption_term_scale_mol": adsorption_scale,
        "desorption_term_scale_mol": desorption_scale,
        "adsorption_conversion_weights": adsorption_weights,
        "desorption_conversion_weights": desorption_weights,
        "adsorption_balance_weights": adsorption_balance_weights,
        "desorption_balance_weights": desorption_balance_weights,
        "next_p95_scale_normalized_absolute_error": float(
            np.quantile(normalized_error, 0.95)
        ),
        "next_max_scale_normalized_absolute_error": float(np.max(normalized_error)),
        "signed_change_branch_mismatch_fraction": float(np.mean(branch_mismatch)),
        "nonzero_transfer_erased_fraction": float(
            np.mean(nonzero & (signed_difference == 0))
        ),
        "adsorption_term_overflow_fraction": float(
            np.mean(adsorption_code > term_levels)
        ),
        "desorption_term_overflow_fraction": float(
            np.mean(desorption_code > term_levels)
        ),
        "negative_sum_underflow_fraction": float(np.mean(negative > positive)),
        "next_output_overflow_fraction": float(np.mean(next_code > output_levels)),
        "minimum_exact_next_gas_mol": float(np.min(exact_next)),
        "qstar_p95_loading_scale_error_max_over_runs": max(
            row["qstar_p95_loading_scale_error"] for row in run_diagnostics
        ),
        "ldf_next_p95_loading_scale_error_max_over_runs": max(
            row["ldf_next_p95_loading_scale_error"] for row in run_diagnostics
        ),
        "qstar_output_overflow_fraction_max_over_runs": max(
            row["qstar_output_overflow_fraction"] for row in run_diagnostics
        ),
        "loading_input_overflow_fraction_max_over_runs": max(
            row["loading_input_overflow_fraction"] for row in run_diagnostics
        ),
        "run_diagnostics": run_diagnostics,
        "run_designs": run_designs,
    }
    result["passes_product_ldf_valve_balance_gate"] = bool(
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


def screen_components(
    context,
    terms: dict[str, np.ndarray],
    loading: dict[str, np.ndarray],
    product_rows: list[dict],
    joint_rows: list[dict],
) -> tuple[list[dict], list[dict]]:
    selected: list[dict] = []
    screen: list[dict] = []
    for component_index, component in enumerate(COMPONENTS):
        base_loading = int(joint_rows[component_index]["loading_bits"])
        if base_loading % 2:
            loading_candidates = [base_loading] + list(
                range(base_loading + 1, MAX_LOADING_BITS + 1, 2)
            )
        else:
            loading_candidates = list(
                range(base_loading, MAX_LOADING_BITS + 1, 2)
            )
        address_candidates = list(
            range(int(joint_rows[component_index]["address_bits"]), MAX_ADDRESS_BITS + 1)
        )
        coefficient_candidates = list(
            range(
                int(joint_rows[component_index]["coefficient_bits"]),
                MAX_COEFFICIENT_BITS + 1,
            )
        )
        choice = None
        for coefficient_bits in coefficient_candidates:
            candidate_joint_row = dict(joint_rows[component_index])
            candidate_joint_row["coefficient_bits"] = coefficient_bits
            for address_bits in address_candidates:
                for loading_bits in loading_candidates:
                    result = evaluate_component(
                        context,
                        terms,
                        loading,
                        product_rows[component_index],
                        candidate_joint_row,
                        component_index,
                        loading_bits,
                        address_bits,
                    )
                    screen.append(
                        {
                            key: value
                            for key, value in result.items()
                            if key not in {"run_diagnostics", "run_designs"}
                        }
                    )
                    if result["passes_product_ldf_valve_balance_gate"]:
                        choice = result
                        break
                if choice is not None:
                    break
            if choice is not None:
                break
        if choice is None:
            raise AssertionError(f"no product LDF/valve precision tier passes for {component}")
        selected.append(choice)
        print(
            json.dumps(
                {
                    "component": component,
                    "loading_bits": choice["loading_bits"],
                    "address_bits": choice["address_bits"],
                    "next_p95": choice[
                        "next_p95_scale_normalized_absolute_error"
                    ],
                    "next_max": choice[
                        "next_max_scale_normalized_absolute_error"
                    ],
                    "passes": True,
                }
            ),
            flush=True,
        )
    return selected, screen


def map_register(
    destination: list[int],
    source_indices: list[int],
    target_indices: list[int],
    name: str,
) -> None:
    if len(source_indices) != len(target_indices):
        raise AssertionError((name, len(source_indices), len(target_indices)))
    for source, target in zip(source_indices, target_indices):
        if destination[source] not in {-1, target}:
            raise AssertionError((name, source, destination[source], target))
        destination[source] = target


def build_component_circuit(
    context,
    terms: dict[str, np.ndarray],
    loading: dict[str, np.ndarray],
    selected_valve: dict,
    product_row: dict,
    component_row: dict,
    compile_run_index: int,
) -> tuple[QuantumCircuit, dict]:
    component_index = int(component_row["component_index"])
    component = COMPONENTS[component_index]
    slug = component.lower()
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
    encoded = product_integer_inputs(
        context,
        constants,
        terms["pressure"][run_slice],
        terms["composition"][run_slice],
        component_index,
    )
    design = component_row["run_designs"][compile_run_index]
    ldf, _ = build_clean_microstep(
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
    valve, _ = build_valve_flux_circuit(selected_valve)
    transfer_spec = {
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
    transfer, _ = build_loading_to_terms(transfer_spec)

    next_index = ldf.num_qubits

    def allocate(size: int) -> list[int]:
        nonlocal next_index
        result = list(range(next_index, next_index + size))
        next_index += size
        return result

    ldf_pressure = [int(index) for index in preparation_layout["pressure"]]
    ldf_composition = [int(index) for index in preparation_layout["composition"]]
    if len(ldf_pressure) != JOINT_LDF_INPUT_BITS:
        raise AssertionError(len(ldf_pressure))
    if len(ldf_composition) != len(COMPONENTS) * JOINT_LDF_INPUT_BITS:
        raise AssertionError(len(ldf_composition))
    valve_composition_sources = [
        index
        for component_index in range(len(COMPONENTS))
        for index in ldf_composition[
            component_index * JOINT_LDF_INPUT_BITS
            + (JOINT_LDF_INPUT_BITS - COMPOSITION_BITS) :
            (component_index + 1) * JOINT_LDF_INPUT_BITS
        ]
    ]

    valve_map = [-1] * valve.num_qubits
    map_register(
        valve_map,
        register_indices(valve, "pressure"),
        ldf_pressure[JOINT_LDF_INPUT_BITS - PRESSURE_BITS :],
        "shared pressure",
    )
    map_register(
        valve_map,
        register_indices(valve, "composition"),
        valve_composition_sources,
        "shared composition",
    )
    for index in range(valve.num_qubits):
        if valve_map[index] < 0:
            valve_map[index] = allocate(1)[0]

    ldf_current = register_indices(ldf, f"q_{slug}")
    ldf_next = register_indices(ldf, f"q_{slug}_next")
    transfer_map = [-1] * transfer.num_qubits
    map_register(
        transfer_map,
        register_indices(transfer, "q_current"),
        ldf_current,
        "q_current",
    )
    map_register(
        transfer_map,
        register_indices(transfer, "q_next"),
        ldf_next,
        "q_next",
    )
    for index in range(transfer.num_qubits):
        if transfer_map[index] < 0:
            transfer_map[index] = allocate(1)[0]

    current_gas = allocate(int(product_row["input_bits_per_nonvalve_term"]))
    left_influx = allocate(int(product_row["input_bits_per_nonvalve_term"]))
    next_gas = allocate(int(product_row["next_output_bits"]))
    desorption_term = [
        transfer_map[index]
        for index in register_indices(transfer, "desorption_term")
    ]
    adsorption_term = [
        transfer_map[index]
        for index in register_indices(transfer, "adsorption_term")
    ]
    valve_flux_all = [
        valve_map[index] for index in register_indices(valve, "component_flux")
    ]
    valve_bits = int(product_row["valve_flux_input_bits"])
    component_flux = valve_flux_all[
        component_index * valve_bits : (component_index + 1) * valve_bits
    ]
    positive_weights = (
        [int(value) for value in product_row["term_weights"]["current_gas"]]
        + [int(value) for value in product_row["term_weights"]["left_influx"]]
        + [int(value) for value in component_row["desorption_balance_weights"]]
    )
    negative_weights = (
        [int(value) for value in product_row["direct_outlet_flux_weights"]]
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

    circuit = QuantumCircuit(next_index, name=f"clean_product_{slug}_ldf_valve_balance")
    ldf_map = list(range(ldf.num_qubits))
    circuit.compose(ldf, qubits=ldf_map, inplace=True)
    circuit.compose(valve, qubits=valve_map, inplace=True)
    circuit.compose(transfer, qubits=transfer_map, inplace=True)
    positive_qargs = (
        current_gas
        + left_influx
        + desorption_term
        + positive_sum
        + positive_work
    )
    negative_qargs = (
        component_flux + adsorption_term + negative_sum + negative_work
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

    retained = sorted(
        set(
            ldf_pressure
            + ldf_composition
            + ldf_current
            + current_gas
            + left_influx
            + next_gas
        )
    )
    if set(ldf_next) & set(retained):
        raise AssertionError("temporary next loading retained")
    if set(component_flux) & set(retained):
        raise AssertionError("temporary valve flux retained")
    return circuit, {
        "shared_pressure_input": ldf_pressure,
        "shared_composition_inputs": ldf_composition,
        "current_loading_input": ldf_current,
        "current_gas_input": current_gas,
        "left_influx_input": left_influx,
        "next_gas_output": next_gas,
        "temporary_next_loading": ldf_next,
        "temporary_valve_component_flux": component_flux,
        "retained_input_output_qubits": len(retained),
        "cleared_workspace_qubits": circuit.num_qubits - len(retained),
        "directly_composed_modules": [
            "factor-specialized competitive-Langmuir reciprocal and LDF update",
            "shared-pressure/shared-composition product valve",
            "loading sign and solid-mass conversion",
            "current gas plus inward face minus valve and adsorption balance",
            "exact reverse of conversion, valve, and LDF work",
        ],
        "quantized_factors": quantized.tolist(),
    }


def resource_record(compiled: QuantumCircuit) -> dict:
    return {
        "logical_qubits": int(compiled.num_qubits),
        "depth_all_to_all": int(compiled.depth()),
        "cx": int(compiled.count_ops().get("cx", 0)),
        "u": int(compiled.count_ops().get("u", 0)),
        "measurement": int(compiled.count_ops().get("measure", 0)),
        "reset": int(compiled.count_ops().get("reset", 0)),
        "basis_gates": ["u", "cx"],
        "optimization_level": 1,
        "transpiler_seed": TRANSPILER_SEED,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--componentwise-compile",
        action="store_true",
        help="transpile five one-component direct paths sequentially",
    )
    args = parser.parse_args()
    context = load_context()
    terms = boundary_terms()
    loading = product_loading_records()
    if len(terms["pressure"]) != len(loading["current_loading"]):
        raise AssertionError("product term/loading ordering differs")
    product = json.loads(PRODUCT_JSON.read_text(encoding="utf-8"))
    product_balance = json.loads(PRODUCT_BALANCE_JSON.read_text(encoding="utf-8"))
    joint = json.loads(JOINT_JSON.read_text(encoding="utf-8"))
    selected_valve = product["selected_valve"]
    product_rows = [row["selected"] for row in product_balance["components"]]
    joint_rows = joint["selected_components"]
    selected_components, screen_rows = screen_components(
        context, terms, loading, product_rows, joint_rows
    )
    compile_run_index = max(
        range(len(context.samples)),
        key=lambda run: max(
            row["run_diagnostics"][run]["ldf_next_p95_loading_scale_error"]
            for row in selected_components
        ),
    )
    compile_score = max(
        row["run_diagnostics"][compile_run_index][
            "ldf_next_p95_loading_scale_error"
        ]
        for row in selected_components
    )

    compiled_rows: list[dict] = []
    layouts: list[dict] = []
    if args.componentwise_compile:
        for component_index, component in enumerate(COMPONENTS):
            circuit, layout = build_component_circuit(
                context,
                terms,
                loading,
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
            resources = resource_record(compiled) | {"component": component}
            if resources["measurement"] or resources["reset"]:
                raise AssertionError(resources)
            compiled_rows.append(resources)
            layouts.append({"component": component} | layout)
            print(json.dumps(resources), flush=True)
            del compiled, circuit
            gc.collect()
    upper = None
    if compiled_rows:
        upper = {
            "accounting": "five directly connected one-component product LDF/valve/balance paths executed sequentially; the shared pressure/composition valve path is repeated in every component and the sum is a conservative upper bound, not a monolithic five-component transpilation",
            "logical_qubits_peak": max(row["logical_qubits"] for row in compiled_rows),
            "depth_all_to_all_additive_upper_bound": sum(
                row["depth_all_to_all"] for row in compiled_rows
            ),
            "cx_additive_upper_bound": sum(row["cx"] for row in compiled_rows),
            "u_additive_upper_bound": sum(row["u"] for row in compiled_rows),
            "monolithic_five_component_transpile": False,
        }

    serializable_components: list[dict] = []
    flat_rows: list[dict] = []
    for row in selected_components:
        serializable = {
            key: value for key, value in row.items() if key != "run_designs"
        }
        serializable["compiled_run_design"] = row["run_designs"][compile_run_index]
        serializable_components.append(serializable)
        flat_rows.append(
            {
                "component": row["component"],
                "factor_bits": row["factor_bits"],
                "address_bits": row["address_bits"],
                "coefficient_bits": row["coefficient_bits"],
                "affinity_bits": row["affinity_bits"],
                "loading_bits": row["loading_bits"],
                "next_p95_scale_error": row[
                    "next_p95_scale_normalized_absolute_error"
                ],
                "next_max_scale_error": row[
                    "next_max_scale_normalized_absolute_error"
                ],
                "nonzero_transfer_erased_fraction": row[
                    "nonzero_transfer_erased_fraction"
                ],
                "negative_sum_underflow_fraction": row[
                    "negative_sum_underflow_fraction"
                ],
                "passes": row["passes_product_ldf_valve_balance_gate"],
            }
        )
    payload = {
        "schema": "psa-qae-cce-primary-product-ldf-valve-balance-composition/v1",
        "status": (
            "parameter_specialized_componentwise_product_ldf_valve_balance_compiled_monolithic_open"
            if compiled_rows
            else "precision_pass_componentwise_compile_pending"
        ),
        "qpu_submission": False,
        "physical_state_source": {
            "runs": 32,
            "cycles_per_run": 100,
            "beds": 2,
            "product_boundary_states": int(len(terms["pressure"])),
            "component_balances": int(len(terms["pressure"]) * len(COMPONENTS)),
            "active_valve_states": int(
                np.sum(np.sum(terms["outlet_flux"], axis=1) > 0.0)
            ),
        },
        "precision_gate": {
            "next_p95_scale_normalized_absolute_error_max": P95_NEXT_SCALE_NORMALIZED_GATE,
            "next_max_scale_normalized_absolute_error_max": MAX_NEXT_SCALE_NORMALIZED_GATE,
            "nonzero_transfer_erasure_required": 0.0,
            "underflow_overflow_required": 0.0,
        },
        "joint_ldf_input_bits_per_pressure_and_composition": JOINT_LDF_INPUT_BITS,
        "selected_components": serializable_components,
        "screen_rows": screen_rows,
        "compile_run_selection": {
            "criterion": "maximum selected componentwise product-support p95 LDF loading-scale error",
            "run_index": int(compile_run_index),
            "sample": int(context.samples[compile_run_index]),
            "score": float(compile_score),
        },
        "componentwise_direct_layouts": layouts,
        "componentwise_compiled_direct_paths": compiled_rows,
        "conservative_five_component_upper_bound": upper,
        "accuracy_boundary": "all cached product-cell states are audited with run-factor-quantized LDF arithmetic and the same valve flux codes consumed by the reversible balance; compiled circuits are one-component parameter-specialized paths",
        "claim_boundary": {
            "supported": "frozen-support precision audit for 32 factor-specialized product-cell paths and direct all-to-all u/CX compilation of one-component LDF-to-loading-sign-to-solid-conversion plus product-valve-to-boundary-balance paths when componentwise compilation is enabled",
            "unsupported": "composition normalization from product-cell gas inventory, generation of the inward face, a coherent superposition-capable run-parameter register, monolithic five-component transpilation, valve scheduling, tank withdrawal, adaptive integration, routing, hardware feasibility, or quantum advantage",
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
        "# Direct product-cell LDF, valve, and boundary balance",
        "",
        f"The frozen audit covers **{len(terms['pressure']):,} product-end states**, **{len(terms['pressure']) * len(COMPONENTS):,} component balances**, and 32 parameter-specialized source rows. The valve is active in **{payload['physical_state_source']['active_valve_states']:,} states**. No QPU job was submitted.",
        "",
        "| Component | factor bits | address bits | loading bits | next-gas p95 | next-gas max | transfer erasure | underflow |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in flat_rows:
        lines.append(
            f"| {row['component']} | {row['factor_bits']} | {row['address_bits']} | {row['loading_bits']} | {row['next_p95_scale_error']:.3e} | {row['next_max_scale_error']:.3e} | {row['nonzero_transfer_erased_fraction']:.3e} | {row['negative_sum_underflow_fraction']:.3e} |"
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
        "Each component circuit shares one encoded pressure/composition input between its competitive-Langmuir/LDF and product-valve modules, maps the generated loading change through sign and solid-mass conversion, consumes the generated adsorption/desorption and outlet flux in one conservative balance, copies next gas, and exactly reverses all work. Composition normalization, inward-face generation, coherent run parameters, five-component monolithic composition, valve scheduling, tank withdrawal, adaptive integration, routing, and a complete phase/cycle remain open.",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": payload["status"],
                "components": len(selected_components),
                "states": len(terms["pressure"]),
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
