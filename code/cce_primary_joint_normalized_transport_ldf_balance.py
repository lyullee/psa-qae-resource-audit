"""Join normalized internal-face transport and LDF uptake in one cell balance.

This audit closes the remaining register-level interface between the two clean
interior-cell paths.  Three encoded gas inventories generate two upwind
compositions, three pressures, and two five-component face transfers.  The
centre pressure/composition also drive five component LDF microsteps.  Each
temporary loading change is sign split, converted through the cell solid mass,
and consumed together with the two face transfers in the same conservative
next-gas balance.  All work is then reversed.

The 32 source rows carry different capacity, affinity, and LDF factors.  A
single default-parameter circuit is therefore an explicit negative control.
The passing panel is a set of 32 parameter-specialized circuits after a frozen
factor-precision screen.  It is not a coherent run-parameter register.  That
distinction is retained in the status and manuscript claim boundary.  No QPU
work is submitted.
"""

from __future__ import annotations

import argparse
import csv
import gc
import json
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit.circuit.library import ModularAdderGate, WeightedAdder

from cce_primary_composition_normalized_internal_face_balance import (
    OUT_JSON as NORMALIZED_JSON,
    build_composition_normalizer,
    encoded_gas,
    normalization_design,
    normalized_face_flux_codes,
)
from cce_primary_internal_face_balance_composition import (
    MAX_NEXT_SCALE_NORMALIZED_GATE,
    P95_NEXT_SCALE_NORMALIZED_GATE,
    interior_terms,
    module_register_map,
    resource_record,
)
from cce_primary_internal_transport_reversible_microsteps import (
    build_face_circuit,
    build_pressure_circuit,
)
from cce_primary_ldf_sign_balance_composition import (
    SIGN_JSON,
    passes_component_ldf_gate,
)
from cce_primary_loading_sign_balance_interface import (
    build_loading_to_terms,
    conversion_weights,
    physical_loading_pairs,
    register_indices,
    weighted_code,
)
from cce_primary_qstar_ldf_reversible_microstep import (
    AFFINITY_COEFFICIENT_BITS,
    INPUT_BITS as BASE_LDF_INPUT_BITS,
    LDF_COEFFICIENT_BITS,
    build_clean_microstep,
    build_preparation,
    physical_constants,
    reciprocal_table,
)
from psa_spatial_network_probe_n2 import COMPONENTS, LDF


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RESULTS = ROOT / "10_TEA_LCA_Python" / "results" / "pycharm_publication_enhancement"
CACHE = HERE / "cce_primary_physical_css_horizon_cache.npz"
SOURCE = HERE / "psa_two_bed_spatial_tank_n2_independent_source_uncertainty_32.csv"
LDF_COMPOSITION_JSON = RESULTS / "PSA_QAE_CCE_PRIMARY_LDF_SIGN_BALANCE_COMPOSITION.json"
OUT_JSON = RESULTS / "PSA_QAE_CCE_PRIMARY_JOINT_NORMALIZED_TRANSPORT_LDF_BALANCE.json"
OUT_CSV = RESULTS / "PSA_QAE_CCE_PRIMARY_JOINT_NORMALIZED_TRANSPORT_LDF_BALANCE.csv"
OUT_MD = RESULTS / "PSA_QAE_CCE_PRIMARY_JOINT_NORMALIZED_TRANSPORT_LDF_BALANCE.md"

FACTOR_LOW = 0.95
FACTOR_HIGH = 1.05
JOINT_LDF_INPUT_BITS = 20
FACTOR_BITS = tuple(range(4, 13))
COEFFICIENT_BITS = (8, 10, 12, 14)
AFFINITY_BITS = (8, 10, 12, 14)
MAX_ADDRESS_BITS = 13
LOADING_BIT_INCREMENTS = (0, 2, 4, 6, 8)
TERM_SCALE_HEADROOM = 1.001
TRANSPILER_SEED = 20261009
RECORDS_PER_RUN = 101 * 2 * 2


@dataclass
class Context:
    normalized: dict
    prior_ldf: dict
    sign: dict
    terms: dict[str, np.ndarray]
    current_loading: np.ndarray
    exact_next_loading: np.ndarray
    solid_mass: np.ndarray
    samples: np.ndarray
    factors: np.ndarray
    gas_codes: np.ndarray
    pressure20: np.ndarray
    pressure18: np.ndarray
    composition20: np.ndarray
    composition18: np.ndarray
    face_flux_codes: np.ndarray
    normalization_selected: dict
    base_constants: dict
    loading_scales: list[float]


def source_rows() -> dict[int, dict[str, str]]:
    with SOURCE.open(newline="", encoding="utf-8-sig") as handle:
        return {int(row["sample"]): row for row in csv.DictReader(handle)}


def quantize_factors(factors: np.ndarray, bits: int) -> np.ndarray:
    levels = (1 << bits) - 1
    code = np.rint((factors - FACTOR_LOW) / (FACTOR_HIGH - FACTOR_LOW) * levels)
    code = np.clip(code, 0, levels)
    return FACTOR_LOW + code / levels * (FACTOR_HIGH - FACTOR_LOW)


def load_context() -> Context:
    normalized = json.loads(NORMALIZED_JSON.read_text(encoding="utf-8"))
    prior_ldf = json.loads(LDF_COMPOSITION_JSON.read_text(encoding="utf-8"))
    sign = json.loads(SIGN_JSON.read_text(encoding="utf-8"))
    terms = interior_terms()
    current_loading, exact_next_loading, solid_mass = physical_loading_pairs()
    state_count = len(current_loading)
    if state_count != 32 * RECORDS_PER_RUN:
        raise AssertionError(state_count)

    cache = np.load(CACHE)
    samples = np.asarray(cache["samples"], dtype=int)
    rows = source_rows()
    factors = np.asarray(
        [
            [
                float(rows[int(sample)]["capacity_factor"]),
                float(rows[int(sample)]["affinity_factor"]),
                float(rows[int(sample)]["ldf_factor"]),
            ]
            for sample in samples
        ],
        dtype=float,
    )

    selected_pressure = normalized["selected_pressure"]
    selected_face = normalized["selected_face"]
    selected_norm = normalized["selected_normalization"]
    support = terms["gas_triplet"][:, :2, :].reshape(-1, len(COMPONENTS))
    exact_composition = terms["composition_pair"].reshape(-1, len(COMPONENTS))
    norm_selected, composition_flat = normalization_design(
        support,
        exact_composition,
        selected_pressure,
        int(selected_norm["amount_bits"]),
        int(selected_norm["reciprocal_bits"]),
        int(selected_norm["address_bits"]),
        keep_circuit_constants=True,
    )
    composition20 = composition_flat.reshape(state_count, 2, len(COMPONENTS))
    face_flux_codes, face_diagnostics = normalized_face_flux_codes(
        terms,
        selected_pressure,
        selected_face,
        composition_flat,
    )
    if not face_diagnostics["passes_propagated_face_precision_gate"]:
        raise AssertionError(face_diagnostics)

    gas_flat, _, _ = encoded_gas(
        terms["gas_triplet"].reshape(-1, len(COMPONENTS)),
        selected_pressure,
    )
    gas_codes = gas_flat.reshape(state_count, 3, len(COMPONENTS))
    pressure20 = np.zeros((state_count, 3), dtype=np.int64)
    weights = [int(value) for value in selected_pressure["pressure_weights"]]
    gas_bits = int(selected_pressure["gas_bits_per_component"])
    for component in range(len(COMPONENTS)):
        for bit in range(gas_bits):
            pressure20 += (
                (gas_codes[:, :, component] >> bit) & 1
            ) * weights[component * gas_bits + bit]

    pressure_bits = int(selected_pressure["pressure_output_bits"])
    if JOINT_LDF_INPUT_BITS < BASE_LDF_INPUT_BITS:
        raise AssertionError((JOINT_LDF_INPUT_BITS, BASE_LDF_INPUT_BITS))
    if pressure_bits < JOINT_LDF_INPUT_BITS:
        raise AssertionError((pressure_bits, JOINT_LDF_INPUT_BITS))
    shift = pressure_bits - JOINT_LDF_INPUT_BITS
    pressure18 = pressure20[:, 1] >> shift
    composition18 = composition20[:, 1, :] >> shift

    base_constants = physical_constants()
    pressure_scale = float(selected_pressure["pressure_scale_bar"])
    loading_scales: list[float] = []
    for component_index in range(len(COMPONENTS)):
        declared_box_natural = float(
            base_constants["qcap"][component_index]
            * base_constants["affinity"][component_index]
            * pressure_scale
            * FACTOR_HIGH
            * FACTOR_HIGH
        )
        loading_scales.append(
            max(
                declared_box_natural,
                float(np.max(current_loading[:, component_index])) * 1.001,
            )
        )

    return Context(
        normalized=normalized,
        prior_ldf=prior_ldf,
        sign=sign,
        terms=terms,
        current_loading=current_loading,
        exact_next_loading=exact_next_loading,
        solid_mass=solid_mass,
        samples=samples,
        factors=factors,
        gas_codes=gas_codes,
        pressure20=pressure20,
        pressure18=pressure18,
        composition20=composition20,
        composition18=composition18,
        face_flux_codes=face_flux_codes,
        normalization_selected=norm_selected,
        base_constants=base_constants,
        loading_scales=loading_scales,
    )


def specialized_constants(
    context: Context,
    capacity: float,
    affinity: float,
    affinity_coefficient_bits: int = AFFINITY_COEFFICIENT_BITS,
) -> dict:
    scaled_affinity = (
        np.asarray(context.base_constants["affinity"], dtype=float) * affinity
    )
    coefficient_levels = (1 << affinity_coefficient_bits) - 1
    return {
        "params": context.base_constants["params"],
        "affinity": scaled_affinity,
        "qcap": np.asarray(context.base_constants["qcap"], dtype=float) * capacity,
        # The scalar factor cancels under normalization, while the retained
        # coefficient resolution remains an explicit end-to-end screen axis.
        "affinity_integer": np.rint(
            scaled_affinity / np.max(scaled_affinity) * coefficient_levels
        ).astype(int),
        "affinity_coefficient_bits": int(affinity_coefficient_bits),
    }


def integer_interface_inputs(
    context: Context,
    run_slice: slice,
    constants: dict,
    component_index: int,
) -> dict:
    levels = (1 << JOINT_LDF_INPUT_BITS) - 1
    coefficient_levels = (
        1 << int(constants.get("affinity_coefficient_bits", AFFINITY_COEFFICIENT_BITS))
    ) - 1
    pressure_scale = float(context.normalized["selected_pressure"]["pressure_scale_bar"])
    affinity = np.asarray(constants["affinity"], dtype=float)
    affinity_integer = np.asarray(constants["affinity_integer"], dtype=int)
    pressure_code = np.asarray(context.pressure18[run_slice], dtype=np.int64)
    composition_code = np.asarray(context.composition18[run_slice], dtype=np.int64)
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
    numerator_code = pressure_code.astype(object) * composition_code[:, component_index].astype(object)
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


def run_ldf_design(
    context: Context,
    component_index: int,
    run_index: int,
    factor_bits: int,
    address_bits: int,
    coefficient_bits: int,
    affinity_bits: int,
    loading_bits_override: int | None = None,
) -> tuple[dict, np.ndarray, dict]:
    run_slice = slice(
        run_index * RECORDS_PER_RUN, (run_index + 1) * RECORDS_PER_RUN
    )
    quantized = quantize_factors(context.factors, factor_bits)[run_index]
    capacity, affinity_factor, ldf_factor = [float(value) for value in quantized]
    exact_capacity, exact_affinity, exact_ldf = [
        float(value) for value in context.factors[run_index]
    ]
    constants = specialized_constants(
        context, capacity, affinity_factor, affinity_coefficient_bits=affinity_bits
    )
    encoded = integer_interface_inputs(context, run_slice, constants, component_index)

    prior = context.prior_ldf["components"][component_index][
        "widened_ldf_precision"
    ]
    arithmetic_bits = (
        int(prior["arithmetic_bits"])
        if loading_bits_override is None
        else int(loading_bits_override)
    )
    arithmetic_levels = (1 << arithmetic_bits) - 1
    loading_scale = float(context.loading_scales[component_index])
    exact_pressure = context.terms["pressure_triplet"][run_slice, 1]
    exact_composition = context.terms["composition_pair"][run_slice, 1, :]
    base_affinity = np.asarray(context.base_constants["affinity"], dtype=float)
    base_qcap = np.asarray(context.base_constants["qcap"], dtype=float)
    exact_denominator = 1.0 + exact_pressure * np.sum(
        exact_composition * (base_affinity * exact_affinity)[None, :], axis=1
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
    reciprocal_ratio = natural_scale / loading_scale
    selected = {
        "component": COMPONENTS[component_index],
        "component_index": component_index,
        "arithmetic_bits": arithmetic_bits,
        "denominator_address_bits": address_bits,
        "reciprocal_segments": 1 << address_bits,
        "ldf_coefficient_bits": coefficient_bits,
        "affinity_coefficient_bits": affinity_bits,
        "ldf_alpha_exact": float(LDF[component_index] * ldf_factor),
        "ldf_alpha_integer": int(
            round(
                float(LDF[component_index] * ldf_factor)
                * (1 << coefficient_bits)
            )
        ),
        "ldf_alpha_implemented": 0.0,
        "natural_qstar_scale_mol_per_kg": natural_scale,
        "loading_scale_mol_per_kg": loading_scale,
        "reciprocal_scale_ratio": reciprocal_ratio,
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
    current_code = np.rint(
        context.current_loading[run_slice, component_index]
        / loading_scale
        * arithmetic_levels
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
        * exact_pressure
        * exact_composition[:, component_index]
        / exact_denominator
    )
    exact_next = context.current_loading[run_slice, component_index] + float(
        LDF[component_index] * exact_ldf
    ) * (exact_qstar - context.current_loading[run_slice, component_index])
    qstar_approx = (
        np.asarray(qstar_code, dtype=float) / arithmetic_levels * loading_scale
    )
    next_approx = (
        np.asarray(next_code, dtype=float) / arithmetic_levels * loading_scale
    )
    qstar_error = np.abs(qstar_approx - exact_qstar) / loading_scale
    next_error = np.abs(next_approx - exact_next) / loading_scale
    difference = np.asarray(next_code - current_code, dtype=np.int64)
    exact_difference = (
        context.exact_next_loading[run_slice, component_index]
        - context.current_loading[run_slice, component_index]
    )
    diagnostics = {
        "run_index": run_index,
        "sample": int(context.samples[run_index]),
        "factor_bits": factor_bits,
        "address_bits": address_bits,
        "coefficient_bits": coefficient_bits,
        "affinity_bits": affinity_bits,
        "exact_factors": context.factors[run_index].tolist(),
        "quantized_factors": quantized.tolist(),
        "qstar_p95_loading_scale_error": float(np.quantile(qstar_error, 0.95)),
        "qstar_max_loading_scale_error": float(np.max(qstar_error)),
        "ldf_next_p95_loading_scale_error": float(np.quantile(next_error, 0.95)),
        "ldf_next_max_loading_scale_error": float(np.max(next_error)),
        "qstar_output_overflow_fraction": float(np.mean(qstar_overflow)),
        "loading_input_overflow_fraction": float(
            np.mean(np.asarray(current_code, dtype=object) > arithmetic_levels)
        ),
        "signed_change_branch_mismatch_fraction": float(
            np.mean(np.sign(difference) != np.sign(exact_difference))
        ),
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
        "qstar_p95_relative_error": float(
            np.quantile(
                np.abs(qstar_approx - exact_qstar)
                / np.maximum(np.abs(exact_qstar), 1.0e-15),
                0.95,
            )
        ),
        "qstar_max_relative_error": float(
            np.max(
                np.abs(qstar_approx - exact_qstar)
                / np.maximum(np.abs(exact_qstar), 1.0e-15)
            )
        ),
        "ldf_next_p95_relative_error": float(
            np.quantile(
                np.abs(next_approx - exact_next)
                / np.maximum(np.abs(exact_next), 1.0e-15),
                0.95,
            )
        ),
        "ldf_next_max_relative_error": float(
            np.max(
                np.abs(next_approx - exact_next)
                / np.maximum(np.abs(exact_next), 1.0e-15)
            )
        ),
        "nonzero_qstar_erased_fraction": float(
            np.mean((exact_qstar > 0.0) & (np.asarray(qstar_code, dtype=float) == 0.0))
        ),
        "loading_input_overflow_fraction": diagnostics[
            "loading_input_overflow_fraction"
        ],
    }
    selected["passes_declared_precision_gate"] = bool(
        selected["qstar_p95_relative_error"] <= 0.05
        and selected["ldf_next_p95_relative_error"] <= 0.001
        and selected["nonzero_qstar_erased_fraction"] == 0.0
        and selected["loading_input_overflow_fraction"] == 0.0
    )
    return selected, difference, diagnostics | {
        "encoded_denominator_one_code": int(encoded["denominator_one_code"]),
        "encoded_denominator_scale": float(encoded["denominator_scale"]),
    }


def direct_gas_weights(context: Context, component_index: int, balance_row: dict) -> list[int]:
    gas_bits = int(context.normalized["selected_pressure"]["gas_bits_per_component"])
    gas_levels = (1 << gas_bits) - 1
    output_levels = (1 << int(balance_row["next_output_bits"])) - 1
    gas_scale = float(
        context.normalized["selected_pressure"]["gas_component_scales_mol"][
            component_index
        ]
    )
    balance_scale = float(balance_row["balance_scale_mol"])
    return [
        int(
            round(
                (1 << bit)
                * gas_scale
                / gas_levels
                / balance_scale
                * output_levels
            )
        )
        for bit in range(gas_bits)
    ]


def term_balance_weights(
    term_bits: int,
    term_scale: float,
    output_bits: int,
    balance_scale: float,
) -> list[int]:
    term_levels = (1 << term_bits) - 1
    output_levels = (1 << output_bits) - 1
    if term_scale <= 0.0:
        return [0] * term_bits
    return [
        int(
            round(
                (1 << bit)
                * term_scale
                / term_levels
                / balance_scale
                * output_levels
            )
        )
        for bit in range(term_bits)
    ]


def evaluate_component(
    context: Context,
    component_index: int,
    factor_bits: int,
    address_bits: int,
    coefficient_bits: int = LDF_COEFFICIENT_BITS,
    affinity_bits: int = AFFINITY_COEFFICIENT_BITS,
    term_bits_override: int | None = None,
    loading_bits_override: int | None = None,
    keep_designs: bool = False,
) -> dict:
    state_count = len(context.current_loading)
    difference = np.zeros(state_count, dtype=np.int64)
    run_diagnostics: list[dict] = []
    designs: list[dict] = []
    for run_index in range(len(context.samples)):
        design, run_difference, diagnostics = run_ldf_design(
            context,
            component_index,
            run_index,
            factor_bits,
            address_bits,
            coefficient_bits,
            affinity_bits,
            loading_bits_override=loading_bits_override,
        )
        run_slice = slice(
            run_index * RECORDS_PER_RUN, (run_index + 1) * RECORDS_PER_RUN
        )
        difference[run_slice] = run_difference
        run_diagnostics.append(diagnostics)
        if keep_designs:
            designs.append(design)

    component = COMPONENTS[component_index]
    prior = context.prior_ldf["components"][component_index][
        "widened_ldf_precision"
    ]
    loading_bits = (
        int(prior["arithmetic_bits"])
        if loading_bits_override is None
        else int(loading_bits_override)
    )
    loading_levels = (1 << loading_bits) - 1
    loading_scale = float(context.loading_scales[component_index])
    approximate_transfer = (
        context.solid_mass * difference / loading_levels * loading_scale
    )
    adsorption_physical = np.maximum(approximate_transfer, 0.0)
    desorption_physical = np.maximum(-approximate_transfer, 0.0)
    exact_adsorption = context.terms["adsorption"][:, component_index]
    exact_desorption = context.terms["desorption"][:, component_index]
    adsorption_scale = max(
        float(np.max(exact_adsorption)), float(np.max(adsorption_physical))
    ) * TERM_SCALE_HEADROOM
    desorption_max = max(
        float(np.max(exact_desorption)), float(np.max(desorption_physical))
    )
    desorption_scale = desorption_max * TERM_SCALE_HEADROOM

    balance_row = dict(
        context.normalized["selected_balance_rows"][component_index]
    )
    term_bits = (
        int(balance_row["input_bits_per_nonface_term"])
        if term_bits_override is None
        else int(term_bits_override)
    )
    term_levels = (1 << term_bits) - 1
    adsorption_conversion = conversion_weights(
        loading_bits,
        loading_scale,
        float(context.solid_mass[0]),
        term_bits,
        adsorption_scale,
    )
    desorption_conversion = conversion_weights(
        loading_bits,
        loading_scale,
        float(context.solid_mass[0]),
        term_bits,
        desorption_scale,
    )
    adsorption_code = weighted_code(
        np.maximum(difference, 0), adsorption_conversion
    )
    desorption_code = weighted_code(
        np.maximum(-difference, 0), desorption_conversion
    )

    output_bits = int(balance_row["next_output_bits"])
    output_levels = (1 << output_bits) - 1
    balance_scale = float(balance_row["balance_scale_mol"])
    gas_weights = direct_gas_weights(context, component_index, balance_row)
    face_weights = [int(value) for value in balance_row["direct_face_flux_weights"]]
    adsorption_balance = term_balance_weights(
        term_bits, adsorption_scale, output_bits, balance_scale
    )
    desorption_balance = term_balance_weights(
        term_bits, desorption_scale, output_bits, balance_scale
    )
    positive = (
        weighted_code(context.gas_codes[:, 1, component_index], gas_weights)
        + weighted_code(context.face_flux_codes[:, 0, component_index], face_weights)
        + weighted_code(desorption_code, desorption_balance)
    )
    negative = (
        weighted_code(context.face_flux_codes[:, 1, component_index], face_weights)
        + weighted_code(adsorption_code, adsorption_balance)
    )
    next_code = positive - negative
    next_approx = next_code / output_levels * balance_scale
    next_exact = context.terms["next_gas"][:, component_index]
    next_scale = float(balance_row["next_gas_scale_mol"])
    next_error = np.abs(next_approx - next_exact) / next_scale
    exact_difference = (
        context.exact_next_loading[:, component_index]
        - context.current_loading[:, component_index]
    )
    nonzero_transfer = exact_difference != 0.0
    result = {
        "component": component,
        "component_index": component_index,
        "factor_bits": factor_bits,
        "address_bits": address_bits,
        "coefficient_bits": coefficient_bits,
        "affinity_bits": affinity_bits,
        "reciprocal_segments": 1 << address_bits,
        "loading_bits": loading_bits,
        "loading_scale_mol_per_kg": loading_scale,
        "term_bits": term_bits,
        "adsorption_term_scale_mol": adsorption_scale,
        "desorption_term_scale_mol": desorption_scale,
        "adsorption_scale_headroom_ratio": adsorption_scale
        / max(float(np.max(exact_adsorption)), 1.0e-30),
        "desorption_scale_headroom_ratio": (
            desorption_scale / max(float(np.max(exact_desorption)), 1.0e-30)
            if np.max(exact_desorption) > 0.0
            else None
        ),
        "next_p95_scale_normalized_absolute_error": float(
            np.quantile(next_error, 0.95)
        ),
        "next_max_scale_normalized_absolute_error": float(np.max(next_error)),
        "negative_sum_underflow_fraction": float(np.mean(next_code < 0)),
        "next_output_overflow_fraction": float(np.mean(next_code > output_levels)),
        "adsorption_term_overflow_fraction": float(
            np.mean(adsorption_code > term_levels)
        ),
        "desorption_term_overflow_fraction": float(
            np.mean(desorption_code > term_levels)
        ),
        "nonzero_transfer_erased_fraction": float(
            np.mean(nonzero_transfer & (difference == 0))
        ),
        "signed_change_branch_mismatch_fraction": float(
            np.mean(np.sign(difference) != np.sign(exact_difference))
        ),
        "qstar_p95_loading_scale_error_max_over_runs": max(
            row["qstar_p95_loading_scale_error"] for row in run_diagnostics
        ),
        "qstar_max_loading_scale_error_max_over_runs": max(
            row["qstar_max_loading_scale_error"] for row in run_diagnostics
        ),
        "ldf_next_p95_loading_scale_error_max_over_runs": max(
            row["ldf_next_p95_loading_scale_error"] for row in run_diagnostics
        ),
        "ldf_next_max_loading_scale_error_max_over_runs": max(
            row["ldf_next_max_loading_scale_error"] for row in run_diagnostics
        ),
        "qstar_output_overflow_fraction_max_over_runs": max(
            row["qstar_output_overflow_fraction"] for row in run_diagnostics
        ),
        "run_diagnostics": run_diagnostics,
        "gas_weights": gas_weights,
        "adsorption_conversion_weights": adsorption_conversion,
        "desorption_conversion_weights": desorption_conversion,
        "adsorption_balance_weights": adsorption_balance,
        "desorption_balance_weights": desorption_balance,
    }
    result["passes_joint_balance_gate"] = bool(
        result["next_p95_scale_normalized_absolute_error"]
        <= P95_NEXT_SCALE_NORMALIZED_GATE
        and result["next_max_scale_normalized_absolute_error"]
        <= MAX_NEXT_SCALE_NORMALIZED_GATE
        and result["negative_sum_underflow_fraction"] == 0.0
        and result["next_output_overflow_fraction"] == 0.0
        and result["adsorption_term_overflow_fraction"] == 0.0
        and result["desorption_term_overflow_fraction"] == 0.0
        and result["nonzero_transfer_erased_fraction"] == 0.0
        and result["qstar_output_overflow_fraction_max_over_runs"] == 0.0
        and result["qstar_p95_loading_scale_error_max_over_runs"] <= 2.5e-3
        and result["ldf_next_p95_loading_scale_error_max_over_runs"] <= 2.5e-3
    )
    if keep_designs:
        result["run_designs"] = designs
    return result


def screen_components(context: Context) -> tuple[list[dict], list[dict]]:
    selected: list[dict] = []
    rows: list[dict] = []
    for component_index, component in enumerate(COMPONENTS):
        minimum_address = int(
            context.prior_ldf["components"][component_index][
                "denominator_address_bits"
            ]
        )
        base_term_bits = int(
            context.normalized["selected_balance_rows"][component_index][
                "input_bits_per_nonface_term"
            ]
        )
        address_choice: dict | None = None
        # Wider term registers did not change the propagated error in the
        # preliminary screen; the binding controls are reciprocal and LDF
        # coefficient precision.  Keep the previously selected 16-bit term
        # interface and search those two dimensions directly.
        base_loading_bits = int(
            context.prior_ldf["components"][component_index][
                "widened_ldf_precision"
            ]["arithmetic_bits"]
        )
        for loading_increment in LOADING_BIT_INCREMENTS:
            loading_bits = base_loading_bits + loading_increment
            if loading_bits > 2 * JOINT_LDF_INPUT_BITS:
                continue
            width_probe = evaluate_component(
                context,
                component_index,
                max(FACTOR_BITS),
                MAX_ADDRESS_BITS,
                coefficient_bits=max(COEFFICIENT_BITS),
                affinity_bits=max(AFFINITY_BITS),
                term_bits_override=base_term_bits,
                loading_bits_override=loading_bits,
            )
            rows.append(
                {key: value for key, value in width_probe.items() if key != "run_diagnostics"}
            )
            print(
                json.dumps(
                    {
                        "stage": "loading_width_probe",
                        "component": component,
                        "factor_bits": max(FACTOR_BITS),
                        "loading_bits": loading_bits,
                        "address_bits": MAX_ADDRESS_BITS,
                        "affinity_bits": max(AFFINITY_BITS),
                        "coefficient_bits": max(COEFFICIENT_BITS),
                        "term_bits": base_term_bits,
                        "p95": width_probe[
                            "next_p95_scale_normalized_absolute_error"
                        ],
                        "maximum": width_probe[
                            "next_max_scale_normalized_absolute_error"
                        ],
                        "nonzero_transfer_erased_fraction": width_probe[
                            "nonzero_transfer_erased_fraction"
                        ],
                        "pass": width_probe["passes_joint_balance_gate"],
                    }
                ),
                flush=True,
            )
            if width_probe["nonzero_transfer_erased_fraction"] > 0.0:
                continue
            for term_bits in (base_term_bits,):
                for address_bits in range(minimum_address, MAX_ADDRESS_BITS + 1):
                    passing_at_address: list[dict] = []
                    for affinity_bits in AFFINITY_BITS:
                        for coefficient_bits in COEFFICIENT_BITS:
                            row = evaluate_component(
                                context,
                                component_index,
                                max(FACTOR_BITS),
                                address_bits,
                                coefficient_bits=coefficient_bits,
                                affinity_bits=affinity_bits,
                                term_bits_override=term_bits,
                                loading_bits_override=loading_bits,
                            )
                            rows.append(
                                {key: value for key, value in row.items() if key != "run_diagnostics"}
                            )
                            print(
                                json.dumps(
                                    {
                                        "stage": "address_coefficient_screen",
                                        "component": component,
                                        "factor_bits": max(FACTOR_BITS),
                                        "loading_bits": loading_bits,
                                        "address_bits": address_bits,
                                        "affinity_bits": affinity_bits,
                                        "coefficient_bits": coefficient_bits,
                                        "term_bits": term_bits,
                                        "p95": row["next_p95_scale_normalized_absolute_error"],
                                        "maximum": row["next_max_scale_normalized_absolute_error"],
                                        "pass": row["passes_joint_balance_gate"],
                                    }
                                ),
                                flush=True,
                            )
                            if row["passes_joint_balance_gate"]:
                                passing_at_address.append(row)
                    if passing_at_address:
                        address_choice = min(
                            passing_at_address,
                            key=lambda row: (
                                int(row["affinity_bits"]),
                                int(row["coefficient_bits"]),
                                int(row["term_bits"]),
                            ),
                        )
                        break
                if address_choice is not None:
                    break
            if address_choice is not None:
                break
        if address_choice is None:
            raise AssertionError(f"no joint address tier passes for {component}")

        factor_choice: dict | None = None
        for factor_bits in FACTOR_BITS:
            row = evaluate_component(
                context,
                component_index,
                factor_bits,
                int(address_choice["address_bits"]),
                coefficient_bits=int(address_choice["coefficient_bits"]),
                affinity_bits=int(address_choice["affinity_bits"]),
                term_bits_override=int(address_choice["term_bits"]),
                loading_bits_override=int(address_choice["loading_bits"]),
            )
            rows.append({key: value for key, value in row.items() if key != "run_diagnostics"})
            print(
                json.dumps(
                    {
                        "stage": "factor_screen",
                        "component": component,
                        "factor_bits": factor_bits,
                        "loading_bits": address_choice["loading_bits"],
                        "address_bits": address_choice["address_bits"],
                        "affinity_bits": address_choice["affinity_bits"],
                        "coefficient_bits": address_choice["coefficient_bits"],
                        "term_bits": address_choice["term_bits"],
                        "p95": row["next_p95_scale_normalized_absolute_error"],
                        "maximum": row["next_max_scale_normalized_absolute_error"],
                        "pass": row["passes_joint_balance_gate"],
                    }
                ),
                flush=True,
            )
            if row["passes_joint_balance_gate"]:
                factor_choice = evaluate_component(
                    context,
                    component_index,
                    factor_bits,
                    int(address_choice["address_bits"]),
                    coefficient_bits=int(address_choice["coefficient_bits"]),
                    affinity_bits=int(address_choice["affinity_bits"]),
                    term_bits_override=int(address_choice["term_bits"]),
                    loading_bits_override=int(address_choice["loading_bits"]),
                    keep_designs=True,
                )
                break
        if factor_choice is None:
            raise AssertionError(f"no joint factor tier passes for {component}")
        selected.append(factor_choice)
    return selected, rows


def transfer_selected(component: dict, sign_component: dict) -> dict:
    selected = dict(sign_component["selected"])
    selected["loading_bits"] = int(component["loading_bits"])
    selected["loading_scale_mol_per_kg"] = float(
        component["loading_scale_mol_per_kg"]
    )
    selected["adsorption_conversion_weights"] = [
        int(value) for value in component["adsorption_conversion_weights"]
    ]
    selected["desorption_conversion_weights"] = [
        int(value) for value in component["desorption_conversion_weights"]
    ]
    return selected


def build_joint_circuit(
    context: Context,
    selected_components: list[dict],
    compile_run_index: int,
    component_indices: list[int] | None = None,
) -> tuple[QuantumCircuit, dict, list[dict]]:
    active_indices = (
        list(range(len(COMPONENTS)))
        if component_indices is None
        else [int(index) for index in component_indices]
    )
    if not active_indices or any(
        index < 0 or index >= len(COMPONENTS) for index in active_indices
    ):
        raise ValueError(active_indices)
    if len(set(active_indices)) != len(active_indices):
        raise ValueError(active_indices)
    normalized = context.normalized
    normalizer, normalizer_layout = build_composition_normalizer(
        context.normalization_selected, normalized["selected_pressure"]
    )
    pressure_module, pressure_layout = build_pressure_circuit(
        normalized["selected_pressure"]
    )
    face_module, face_layout = build_face_circuit(normalized["selected_face"])
    pressure_gas_bits = len(register_indices(pressure_module, "gas_components"))
    pressure_bits = len(register_indices(pressure_module, "pressure"))
    composition_bits_total = len(register_indices(normalizer, "composition"))
    face_flux_bits_total = len(register_indices(face_module, "component_flux"))
    face_bits = face_flux_bits_total // len(COMPONENTS)

    quantized = quantize_factors(
        context.factors, max(int(row["factor_bits"]) for row in selected_components)
    )[compile_run_index]
    component_modules: list[dict] = []
    workspace_size = 0
    for component_index in active_indices:
        component = COMPONENTS[component_index]
        component_row = selected_components[component_index]
        factor_bits = int(component_row["factor_bits"])
        run_factors = quantize_factors(context.factors, factor_bits)[compile_run_index]
        constants = specialized_constants(
            context,
            float(run_factors[0]),
            float(run_factors[1]),
            affinity_coefficient_bits=int(component_row["affinity_bits"]),
        )
        run_slice = slice(
            compile_run_index * RECORDS_PER_RUN,
            (compile_run_index + 1) * RECORDS_PER_RUN,
        )
        encoded = integer_interface_inputs(
            context, run_slice, constants, component_index
        )
        design = component_row["run_designs"][compile_run_index]
        ldf, ldf_layout = build_clean_microstep(
            constants,
            encoded,
            design,
            component_index,
            ldf_coefficient_bits=int(design["ldf_coefficient_bits"]),
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
        transfer_spec = transfer_selected(
            component_row, context.sign["components"][component_index]
        )
        transfer, transfer_layout = build_loading_to_terms(transfer_spec)
        process_sources = set(
            preparation_layout["pressure"] + preparation_layout["composition"]
        )
        current_sources = set(register_indices(ldf, f"q_{component.lower()}"))
        ldf_unmapped = [
            index
            for index in range(ldf.num_qubits)
            if index not in process_sources and index not in current_sources
        ]
        next_sources = register_indices(ldf, f"q_{component.lower()}_next")
        next_positions = [ldf_unmapped.index(index) for index in next_sources]
        transfer_fixed = set(register_indices(transfer, "q_current")) | set(
            register_indices(transfer, "q_next")
        )
        transfer_other = [
            index for index in range(transfer.num_qubits) if index not in transfer_fixed
        ]
        workspace_size = max(
            workspace_size,
            len(ldf_unmapped),
            len(next_sources) + len(transfer_other),
        )
        component_modules.append(
            {
                "component": component,
                "component_index": component_index,
                "ldf": ldf,
                "ldf_layout": ldf_layout,
                "preparation_layout": preparation_layout,
                "transfer": transfer,
                "transfer_layout": transfer_layout,
                "ldf_unmapped": ldf_unmapped,
                "next_positions": next_positions,
                "transfer_other": transfer_other,
                "design": design,
                "quantized_factors": run_factors.tolist(),
            }
        )

    adders: dict[int, tuple[WeightedAdder, WeightedAdder]] = {}
    for component_index in active_indices:
        row = selected_components[component_index]
        balance = normalized["selected_balance_rows"][component_index]
        positive_weights = (
            [int(value) for value in row["gas_weights"]]
            + [int(value) for value in balance["direct_face_flux_weights"]]
            + [int(value) for value in row["desorption_balance_weights"]]
        )
        negative_weights = (
            [int(value) for value in balance["direct_face_flux_weights"]]
            + [int(value) for value in row["adsorption_balance_weights"]]
        )
        adders[component_index] = (
            WeightedAdder(len(positive_weights), positive_weights),
            WeightedAdder(len(negative_weights), negative_weights),
        )
    positive_sum_bits = max(pair[0].num_sum_qubits for pair in adders.values())
    negative_sum_bits = max(pair[1].num_sum_qubits for pair in adders.values())
    positive_work_bits = max(pair[0].num_ancillas for pair in adders.values())
    negative_work_bits = max(pair[1].num_ancillas for pair in adders.values())
    common_bits = max(
        positive_sum_bits,
        negative_sum_bits,
        max(
            int(row["next_output_bits"])
            for row in normalized["selected_balance_rows"]
        ),
    )

    next_index = 0

    def allocate(size: int) -> list[int]:
        nonlocal next_index
        output = list(range(next_index, next_index + size))
        next_index += size
        return output

    gas = [allocate(pressure_gas_bits) for _ in range(3)]
    compositions = [allocate(composition_bits_total) for _ in range(2)]
    normalizer_shared = {
        register.name: allocate(len(register))
        for register in normalizer.qregs
        if register.name not in {"gas_components", "composition"}
    }
    pressure_output = [allocate(pressure_bits) for _ in range(3)]
    pressure_shared = {
        register.name: allocate(len(register))
        for register in pressure_module.qregs
        if register.name not in {"gas_components", "pressure"}
    }
    face_flux = [allocate(face_flux_bits_total) for _ in range(2)]
    face_shared = {
        register.name: allocate(len(register))
        for register in face_module.qregs
        if register.name
        not in {"pressure_left", "pressure_right", "composition_left", "component_flux"}
    }
    current_loading = [
        allocate(int(row["loading_bits"])) for row in selected_components
    ]
    next_gas = [
        allocate(
            int(normalized["selected_balance_rows"][component]["next_output_bits"])
        )
        for component in range(len(COMPONENTS))
    ]
    component_workspace = allocate(workspace_size)
    positive_sum = allocate(positive_sum_bits)
    negative_sum = allocate(negative_sum_bits)
    positive_work = allocate(positive_work_bits)
    negative_work = allocate(negative_work_bits)
    negative_pad = allocate(common_bits)
    balance_register = allocate(common_bits)

    circuit = QuantumCircuit(
        next_index,
        name=(
            "clean_joint_normalized_transport_ldf_five_component_balance"
            if len(active_indices) == len(COMPONENTS)
            else "clean_joint_normalized_transport_ldf_"
            + "_".join(COMPONENTS[index].lower() for index in active_indices)
            + "_balance"
        ),
    )
    normalizer_maps = [
        module_register_map(
            normalizer,
            {"gas_components": gas[cell], "composition": compositions[cell]},
            normalizer_shared,
        )
        for cell in range(2)
    ]
    for mapping in normalizer_maps:
        circuit.compose(normalizer, qubits=mapping, inplace=True)
    pressure_maps = [
        module_register_map(
            pressure_module,
            {"gas_components": gas[cell], "pressure": pressure_output[cell]},
            pressure_shared,
        )
        for cell in range(3)
    ]
    for mapping in pressure_maps:
        circuit.compose(pressure_module, qubits=mapping, inplace=True)
    face_maps = [
        module_register_map(
            face_module,
            {
                "pressure_left": pressure_output[face],
                "pressure_right": pressure_output[face + 1],
                "composition_left": compositions[face],
                "component_flux": face_flux[face],
            },
            face_shared,
        )
        for face in range(2)
    ]
    for mapping in face_maps:
        circuit.compose(face_module, qubits=mapping, inplace=True)

    module_layouts: list[dict] = []
    pressure_target = pressure_output[1][pressure_bits - JOINT_LDF_INPUT_BITS :]
    composition_target = [
        index
        for component in range(len(COMPONENTS))
        for index in compositions[1][
            component * (composition_bits_total // len(COMPONENTS))
            + (composition_bits_total // len(COMPONENTS) - JOINT_LDF_INPUT_BITS) :
            (component + 1) * (composition_bits_total // len(COMPONENTS))
        ]
    ]
    for module in component_modules:
        component_index = int(module["component_index"])
        pair = adders[component_index]
        component = COMPONENTS[component_index]
        ldf = module["ldf"]
        prep = module["preparation_layout"]
        ldf_map = [-1] * ldf.num_qubits
        for source, target in zip(prep["pressure"], pressure_target):
            ldf_map[source] = target
        for source, target in zip(prep["composition"], composition_target):
            ldf_map[source] = target
        for source, target in zip(
            register_indices(ldf, f"q_{component.lower()}"),
            current_loading[component_index],
        ):
            ldf_map[source] = target
        for position, source in enumerate(module["ldf_unmapped"]):
            ldf_map[source] = component_workspace[position]
        if any(index < 0 for index in ldf_map) or len(set(ldf_map)) != len(ldf_map):
            raise AssertionError(f"invalid LDF map for {component}")

        transfer = module["transfer"]
        transfer_map = [-1] * transfer.num_qubits
        for source, target in zip(
            register_indices(transfer, "q_current"),
            current_loading[component_index],
        ):
            transfer_map[source] = target
        ldf_next_target = [
            component_workspace[position] for position in module["next_positions"]
        ]
        for source, target in zip(
            register_indices(transfer, "q_next"), ldf_next_target
        ):
            transfer_map[source] = target
        available = [
            index for index in component_workspace if index not in set(ldf_next_target)
        ]
        for source, target in zip(module["transfer_other"], available):
            transfer_map[source] = target
        if any(index < 0 for index in transfer_map) or len(set(transfer_map)) != len(
            transfer_map
        ):
            raise AssertionError(f"invalid transfer map for {component}")

        transfer_terms = {
            name: [
                transfer_map[index] for index in register_indices(transfer, name)
            ]
            for name in ("desorption_term", "adsorption_term")
        }
        positive_adder, negative_adder = pair
        left_flux = face_flux[0][
            component_index * face_bits : (component_index + 1) * face_bits
        ]
        right_flux = face_flux[1][
            component_index * face_bits : (component_index + 1) * face_bits
        ]
        gas_bits = int(
            normalized["selected_pressure"]["gas_bits_per_component"]
        )
        centre_gas = gas[1][
            component_index * gas_bits : (component_index + 1) * gas_bits
        ]
        positive_state = centre_gas + left_flux + transfer_terms["desorption_term"]
        negative_state = right_flux + transfer_terms["adsorption_term"]
        positive_qargs = (
            positive_state
            + positive_sum[: positive_adder.num_sum_qubits]
            + positive_work[: positive_adder.num_ancillas]
        )
        negative_qargs = (
            negative_state
            + negative_sum[: negative_adder.num_sum_qubits]
            + negative_work[: negative_adder.num_ancillas]
        )

        circuit.compose(ldf, qubits=ldf_map, inplace=True)
        circuit.compose(transfer, qubits=transfer_map, inplace=True)
        circuit.append(positive_adder, positive_qargs)
        circuit.append(negative_adder, negative_qargs)
        for source, target in zip(
            positive_sum[: positive_adder.num_sum_qubits], balance_register
        ):
            circuit.cx(source, target)
        negative_operand = (
            negative_sum[: negative_adder.num_sum_qubits]
            + negative_pad[: common_bits - negative_adder.num_sum_qubits]
        )
        subtractor = ModularAdderGate(common_bits)
        circuit.append(subtractor.inverse(), negative_operand + balance_register)
        for source, target in zip(
            balance_register[
                : int(
                    normalized["selected_balance_rows"][component_index][
                        "next_output_bits"
                    ]
                )
            ],
            next_gas[component_index],
        ):
            circuit.cx(source, target)
        circuit.append(subtractor, negative_operand + balance_register)
        for source, target in reversed(
            list(
                zip(
                    positive_sum[: positive_adder.num_sum_qubits],
                    balance_register,
                )
            )
        ):
            circuit.cx(source, target)
        circuit.append(negative_adder.inverse(), negative_qargs)
        circuit.append(positive_adder.inverse(), positive_qargs)
        circuit.compose(transfer.inverse(), qubits=transfer_map, inplace=True)
        circuit.compose(ldf.inverse(), qubits=ldf_map, inplace=True)
        module_layouts.append(
            {
                "component": component,
                "ldf_logical_qubits": ldf.num_qubits,
                "transfer_logical_qubits": transfer.num_qubits,
                "ldf_next_workspace": ldf_next_target,
                "quantized_factors": module["quantized_factors"],
            }
        )

    for mapping in reversed(face_maps):
        circuit.compose(face_module.inverse(), qubits=mapping, inplace=True)
    for mapping in reversed(pressure_maps):
        circuit.compose(pressure_module.inverse(), qubits=mapping, inplace=True)
    for mapping in reversed(normalizer_maps):
        circuit.compose(normalizer.inverse(), qubits=mapping, inplace=True)

    retained = sorted(
        set(
            [index for group in gas for index in group]
            + [index for group in current_loading for index in group]
            + [index for group in next_gas for index in group]
        )
    )
    layout = {
        "compile_run_index": compile_run_index,
        "compile_sample": int(context.samples[compile_run_index]),
        "compile_run_quantized_factors_at_max_selected_bits": quantized.tolist(),
        "active_components": [COMPONENTS[index] for index in active_indices],
        "three_cell_gas_inventory_inputs": gas,
        "current_loading_inputs": current_loading,
        "next_gas_outputs": next_gas,
        "temporary_compositions": compositions,
        "temporary_pressures": pressure_output,
        "temporary_face_fluxes": face_flux,
        "shared_component_workspace_qubits": len(component_workspace),
        "retained_input_output_qubits": len(retained),
        "cleared_workspace_qubits": circuit.num_qubits - len(retained),
        "normalizer_layout": normalizer_layout,
        "pressure_layout": pressure_layout,
        "face_layout": face_layout,
        "component_modules": module_layouts,
        "directly_composed_modules": [
            "two support-adaptive gas-composition normalizers",
            "three pressure reconstructions and two five-component internal faces",
            "five parameter-specialized competitive-Langmuir/LDF microsteps",
            "five loading-sign and solid-mass conversion interfaces",
            "five balances sharing the exact generated face and loading-transfer registers",
            "exact reverse of every LDF, transfer, face, pressure, and normalization workspace",
        ],
    }
    return circuit, layout, component_modules


def flatten_rows(rows: list[dict]) -> list[dict]:
    keys = (
        "component",
        "factor_bits",
        "loading_bits",
        "address_bits",
        "coefficient_bits",
        "affinity_bits",
        "reciprocal_segments",
        "next_p95_scale_normalized_absolute_error",
        "next_max_scale_normalized_absolute_error",
        "negative_sum_underflow_fraction",
        "next_output_overflow_fraction",
        "adsorption_term_overflow_fraction",
        "desorption_term_overflow_fraction",
        "nonzero_transfer_erased_fraction",
        "signed_change_branch_mismatch_fraction",
        "qstar_p95_loading_scale_error_max_over_runs",
        "ldf_next_p95_loading_scale_error_max_over_runs",
        "passes_joint_balance_gate",
    )
    return [{key: row.get(key) for key in keys} for row in rows]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--screen-only",
        action="store_true",
        help="run the precision/interface screen without transpiling the joint circuit",
    )
    parser.add_argument(
        "--componentwise-compile",
        action="store_true",
        help=(
            "transpile five directly connected one-component paths sequentially "
            "and report their conservative additive resource bound"
        ),
    )
    args = parser.parse_args()
    if args.screen_only and args.componentwise_compile:
        parser.error("--screen-only and --componentwise-compile are mutually exclusive")
    context = load_context()
    selected, rows = screen_components(context)

    # Choose the run with the largest componentwise p95 LDF error under the
    # selected settings.  This is the conservative constant-specialized compile.
    run_scores = []
    for run_index in range(len(context.samples)):
        run_scores.append(
            max(
                component["run_diagnostics"][run_index][
                    "ldf_next_p95_loading_scale_error"
                ]
                for component in selected
            )
        )
    compile_run = int(np.argmax(run_scores))
    compiled_resources = None
    componentwise_resources = None
    direct_layout = None
    if not args.screen_only:
        if args.componentwise_compile:
            componentwise_resources = []
            direct_layout = []
            for component_index, component in enumerate(COMPONENTS):
                circuit, component_layout, modules = build_joint_circuit(
                    context,
                    selected,
                    compile_run,
                    component_indices=[component_index],
                )
                print(
                    json.dumps(
                        {
                            "stage": "component_joint_circuit_built",
                            "component": component,
                            "logical_qubits": circuit.num_qubits,
                            "compile_run": compile_run,
                            "sample": int(context.samples[compile_run]),
                        }
                    ),
                    flush=True,
                )
                compiled = transpile(
                    circuit,
                    basis_gates=["u", "cx"],
                    optimization_level=1,
                    seed_transpiler=TRANSPILER_SEED,
                )
                resources = resource_record(compiled)
                if resources["measurement"] or resources["reset"]:
                    raise AssertionError(resources)
                resources["component"] = component
                componentwise_resources.append(resources)
                direct_layout.append(component_layout)
                print(
                    json.dumps(
                        {
                            "stage": "component_joint_circuit_transpiled",
                            "component": component,
                            **resources,
                        }
                    ),
                    flush=True,
                )
                del compiled, circuit, modules
                gc.collect()
            compiled_resources = {
                "interpretation": (
                    "conservative serial sum of five directly connected "
                    "one-component normalized-transport/LDF/balance paths; "
                    "the common transport path is repeated five times"
                ),
                "logical_qubits_peak": max(
                    int(row["logical_qubits"]) for row in componentwise_resources
                ),
                "depth_all_to_all_additive_upper_bound": sum(
                    int(row["depth_all_to_all"])
                    for row in componentwise_resources
                ),
                "cx_additive_upper_bound": sum(
                    int(row["cx"]) for row in componentwise_resources
                ),
                "u_additive_upper_bound": sum(
                    int(row["u"]) for row in componentwise_resources
                ),
                "measurement": 0,
                "reset": 0,
                "transpiler_seed": TRANSPILER_SEED,
                "basis_gates": ["u", "cx"],
                "optimization_level": 1,
                "monolithic_five_component_transpile": False,
            }
        else:
            circuit, direct_layout, modules = build_joint_circuit(
                context, selected, compile_run
            )
            print(
                json.dumps(
                    {
                        "stage": "joint_circuit_built",
                        "logical_qubits": circuit.num_qubits,
                        "compile_run": compile_run,
                        "sample": int(context.samples[compile_run]),
                    }
                ),
                flush=True,
            )
            compiled = transpile(
                circuit,
                basis_gates=["u", "cx"],
                optimization_level=1,
                seed_transpiler=TRANSPILER_SEED,
            )
            compiled_resources = resource_record(compiled)
            if compiled_resources["measurement"] or compiled_resources["reset"]:
                raise AssertionError(compiled_resources)
            del compiled, circuit, modules
            gc.collect()

    selected_serializable = []
    for component in selected:
        serializable = {
            key: value
            for key, value in component.items()
            if key not in {"run_designs", "run_diagnostics"}
        }
        serializable["run_diagnostics"] = component["run_diagnostics"]
        serializable["compiled_run_design"] = component["run_designs"][compile_run]
        selected_serializable.append(serializable)

    payload = {
        "schema": "psa-qae-cce-primary-joint-normalized-transport-ldf-balance/v1",
        "status": (
            "screen_pass_parameter_specialized_joint_circuit_not_transpiled"
            if args.screen_only
            else (
                "parameter_specialized_componentwise_direct_paths_compiled_additive_upper_bound_monolithic_open"
                if args.componentwise_compile
                else "parameter_specialized_joint_normalized_transport_ldf_balance_compiled_coherent_parameter_register_open"
            )
        ),
        "qpu_submission": False,
        "physical_state_source": {
            "runs": 32,
            "interior_cell_states": int(len(context.current_loading)),
            "component_balances": int(
                len(context.current_loading) * len(COMPONENTS)
            ),
            "normalization_states": int(2 * len(context.current_loading)),
        },
        "factor_encoding": {
            "range": [FACTOR_LOW, FACTOR_HIGH],
            "candidate_bits": list(FACTOR_BITS),
            "meaning": ["capacity_factor", "affinity_factor", "ldf_factor"],
            "coherent_register_compiled": False,
        },
        "joint_ldf_input_bits_per_pressure_and_composition": JOINT_LDF_INPUT_BITS,
        "selected_components": selected_serializable,
        "screen_rows": flatten_rows(rows),
        "compile_run_selection": {
            "criterion": "maximum selected componentwise per-run p95 LDF loading-scale error",
            "run_index": compile_run,
            "sample": int(context.samples[compile_run]),
            "score": float(run_scores[compile_run]),
        },
        "direct_composition_layout": direct_layout,
        "compiled_clean_joint_specialized_circuit": compiled_resources,
        "componentwise_compiled_direct_paths": componentwise_resources,
        "claim_boundary": {
            "supported": "frozen-support precision audit of 32 factor-quantized parameter-specialized paths and direct all-to-all u/CX compilation of each one-component normalized-transport/LDF/balance path for the conservative selected run when componentwise compilation is enabled",
            "unsupported": "a monolithic five-component transpilation, one coherent superposition-capable run-parameter register, out-of-support normalization, negative-flow switching outside the cached orientation, boundary/tank withdrawal, adaptive phase integration, routing, hardware feasibility, or quantum advantage",
        },
    }
    OUT_JSON.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    flat = flatten_rows(selected)
    with OUT_CSV.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(flat[0]))
        writer.writeheader()
        writer.writerows(flat)

    lines = [
        "# Joint normalized transport, LDF, and interior-cell balance",
        "",
        f"The frozen audit covers **{len(context.current_loading):,} interior-cell states**, **{len(context.current_loading) * len(COMPONENTS):,} component balances**, and 32 parameter-specialized source rows. No QPU job was submitted.",
        "",
        "| Component | factor bits | loading bits | affinity bits | reciprocal address bits | LDF coefficient bits | segments | next-gas p95 | next-gas max | branch mismatch |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in selected:
        lines.append(
            f"| {row['component']} | {row['factor_bits']} | {row['loading_bits']} | {row['affinity_bits']} | {row['address_bits']} | {row['coefficient_bits']} | {row['reciprocal_segments']:,} | "
            f"{row['next_p95_scale_normalized_absolute_error']:.3e} | {row['next_max_scale_normalized_absolute_error']:.3e} | "
            f"{row['signed_change_branch_mismatch_fraction']:.3e} |"
        )
    lines += [
        "",
        "The centre-cell current gas is taken directly from the same 18-bit gas inventories used for normalization and pressure reconstruction. The LDF path consumes the full 20-bit reconstructed pressure and normalized composition outputs. Generated face fluxes and generated adsorption/desorption terms enter the same balance; no independent current-gas, composition, face, or uptake registers are supplied.",
        "",
        "The passing precision panel uses factor-quantized, run-specialized constants. It demonstrates the arithmetic interface and quantifies its precision/resource cost, but 32 specialized circuits are not one coherent scenario oracle. A reversible scenario-parameter register and its variable-coefficient arithmetic remain open.",
    ]
    if componentwise_resources is not None:
        lines += [
            "",
            "| Direct compiled path | logical qubits | depth | CX |",
            "|---|---:|---:|---:|",
        ]
        for resources in componentwise_resources:
            lines.append(
                f"| {resources['component']} | {resources['logical_qubits']:,} | "
                f"{resources['depth_all_to_all']:,} | {resources['cx']:,} |"
            )
        lines += [
            "",
            f"The conservative serial additive upper bound has peak **{compiled_resources['logical_qubits_peak']:,} logical qubits**, depth **{compiled_resources['depth_all_to_all_additive_upper_bound']:,}**, and **{compiled_resources['cx_additive_upper_bound']:,} CX**. It repeats the common normalized-transport path five times and is therefore an upper bound, not a monolithic five-component transpilation.",
        ]
    elif compiled_resources is not None:
        lines += [
            "",
            f"The conservative selected specialization compiles to **{compiled_resources['logical_qubits']:,} logical qubits**, depth **{compiled_resources['depth_all_to_all']:,}**, and **{compiled_resources['cx']:,} CX** in the all-to-all `u/CX` basis.",
        ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": payload["status"],
                "selected": [
                    {
                        "component": row["component"],
                        "factor_bits": row["factor_bits"],
                        "address_bits": row["address_bits"],
                        "affinity_bits": row["affinity_bits"],
                        "coefficient_bits": row["coefficient_bits"],
                        "p95": row["next_p95_scale_normalized_absolute_error"],
                        "max": row["next_max_scale_normalized_absolute_error"],
                    }
                    for row in selected
                ],
                "compiled_resources": compiled_resources,
                "qpu_submission": False,
            },
            indent=2,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
