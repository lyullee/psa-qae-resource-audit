"""Compile a pressure-derived saturated/unsaturated tank-allocation interface.

The frozen final-cycle support exercises only demand-saturated withdrawals.
That support is retained verbatim.  To test the missing arithmetic branch, the
32 nonzero tank compositions are also paired with seven declared pressure
counterfactuals whose requested withdrawal is 5--95% of the tank inventory.
The counterfactuals are an arithmetic-domain test and are not plant data.

Five endpoint gas inventories generate pressure and a withdrawal-demand proxy.
The proxy is compared with the tank total.  A saturated call copies the whole
tank.  An unsaturated call evaluates

    withdrawal_i = demand * tank_i / sum_j(tank_j)

with a support-adaptive reciprocal, two reversible multiplications, exact
branch selection, componentwise subtraction, and full workspace reversal.

No QPU work is submitted.
"""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import numpy as np
from qiskit import QuantumCircuit, QuantumRegister, transpile
from qiskit.circuit.library import (
    IntegerComparator,
    ModularAdderGate,
    MultiplierGate,
    WeightedAdder,
)

from cce_primary_composition_normalized_internal_face_balance import (
    support_adaptive_bins,
)
from cce_primary_offledger_tank_saturation_interface import (
    COMPONENTS,
    K_IN_MOL_S_BAR,
    PHASE_DURATION_S,
    P_HIGH_BAR,
    PRIOR_TANK,
    RESULTS,
    TANK_BITS,
    json_default,
    support_records,
)
from cce_primary_qstar_ldf_reversible_microstep import (
    append_address_extractor,
    append_reciprocal_qrom,
)
from psa_spatial_network_probe_n2 import BAR, R, SpatialParams


OUT_JSON = RESULTS / "PSA_QAE_CCE_OFFLEDGER_TANK_PROPORTIONAL_INTERFACE.json"
OUT_CSV = RESULTS / "PSA_QAE_CCE_OFFLEDGER_TANK_PROPORTIONAL_INTERFACE.csv"
OUT_MD = RESULTS / "PSA_QAE_CCE_OFFLEDGER_TANK_PROPORTIONAL_INTERFACE.md"

COUNTERFACTUAL_DEMAND_FRACTIONS = (0.05, 0.125, 0.25, 0.50, 0.75, 0.875, 0.95)
COMMON_BITS_CASES = (18, 20, 22)
ADDRESS_BITS_CASES = (3, 4, 5)
RECIPROCAL_BITS_CASES = (16, 18, 20)
FRACTION_BITS = TANK_BITS
PRESSURE_BITS = 20
GAS_BITS = 18
PRESSURE_SCALE_HEADROOM = 1.001
GAS_SCALE_HEADROOM = 1.001
COMMON_SCALE_HEADROOM = 1.01
MEANINGFUL_MOL = 1.0e-15
PRESSURE_P95_GATE = 1.0e-5
PRESSURE_MAX_GATE = 2.0e-5
DEMAND_P95_GATE = 1.5e-5
TANK_TOTAL_P95_GATE = 1.0e-5
WITHDRAWAL_P95_COMPONENT_SCALE_GATE = 2.5e-4
WITHDRAWAL_MAX_COMPONENT_SCALE_GATE = 5.0e-4
TRANSPILER_SEED = 20261010


def arithmetic_domain(records: list[dict]) -> tuple[dict[str, np.ndarray], list[dict]]:
    rows: list[dict] = []
    for record in records:
        gas = np.maximum(np.asarray(record["endpoint_gas_mol"], dtype=float), 0.0)
        tank = np.maximum(np.asarray(record["tank_start_mol"], dtype=float), 0.0)
        tank_total = float(np.sum(tank))
        pressure = float(record["endpoint_pressure_bar"])
        demand = K_IN_MOL_S_BAR * PHASE_DURATION_S * max(P_HIGH_BAR - pressure, 0.0)
        saturated = bool(demand >= tank_total)
        fraction = 1.0 if tank_total <= MEANINGFUL_MOL else min(1.0, demand / tank_total)
        rows.append(
            {
                "source": "observed_frozen_final_cycle",
                "sample": int(record["sample"]),
                "slot": int(record["slot"]),
                "demand_fraction": float(fraction),
                "endpoint_pressure_bar": pressure,
                "endpoint_gas_mol": gas,
                "tank_start_mol": tank,
                "demand_proxy_mol": float(demand),
                "exact_saturated": saturated,
                "exact_withdrawal_mol": tank if saturated else fraction * tank,
            }
        )
        if tank_total <= MEANINGFUL_MOL:
            continue
        for fraction in COUNTERFACTUAL_DEMAND_FRACTIONS:
            demand = float(fraction * tank_total)
            pressure = float(P_HIGH_BAR - demand / (K_IN_MOL_S_BAR * PHASE_DURATION_S))
            scaled_gas = gas * (pressure / float(record["endpoint_pressure_bar"]))
            rows.append(
                {
                    "source": "bounded_pressure_counterfactual_arithmetic_test",
                    "sample": int(record["sample"]),
                    "slot": int(record["slot"]),
                    "demand_fraction": float(fraction),
                    "endpoint_pressure_bar": pressure,
                    "endpoint_gas_mol": scaled_gas,
                    "tank_start_mol": tank,
                    "demand_proxy_mol": demand,
                    "exact_saturated": False,
                    "exact_withdrawal_mol": fraction * tank,
                }
            )
    domain = {
        "endpoint_gas_mol": np.asarray([row["endpoint_gas_mol"] for row in rows]),
        "endpoint_pressure_bar": np.asarray([row["endpoint_pressure_bar"] for row in rows]),
        "tank_start_mol": np.asarray([row["tank_start_mol"] for row in rows]),
        "demand_proxy_mol": np.asarray([row["demand_proxy_mol"] for row in rows]),
        "exact_saturated": np.asarray([row["exact_saturated"] for row in rows], dtype=bool),
        "exact_withdrawal_mol": np.asarray([row["exact_withdrawal_mol"] for row in rows]),
    }
    return domain, rows


def pressure_design(
    domain: dict[str, np.ndarray],
    *,
    gas_scale_basis: np.ndarray | None = None,
) -> tuple[dict, np.ndarray, np.ndarray]:
    gas = domain["endpoint_gas_mol"]
    exact_pressure = domain["endpoint_pressure_bar"]
    gas_levels = (1 << GAS_BITS) - 1
    pressure_levels = (1 << PRESSURE_BITS) - 1
    scale_basis = gas if gas_scale_basis is None else np.asarray(gas_scale_basis)
    gas_scales = np.max(scale_basis, axis=0) * GAS_SCALE_HEADROOM
    pressure_scale = P_HIGH_BAR * PRESSURE_SCALE_HEADROOM
    high_pressure_code = int(round(P_HIGH_BAR / pressure_scale * pressure_levels))
    params = SpatialParams(n_cells=4)
    pressure_factor = (
        R * params.temperature_K / (params.gas_cell_volume_m3 * BAR)
    )
    gas_code = np.rint(gas / gas_scales * gas_levels).astype(np.int64)
    weights = [
        int(
            round(
                gas_scales[component]
                / gas_levels
                * (1 << bit)
                * pressure_factor
                / pressure_scale
                * pressure_levels
            )
        )
        for component in range(len(COMPONENTS))
        for bit in range(GAS_BITS)
    ]
    pressure_code = np.zeros(len(gas), dtype=np.int64)
    for component in range(len(COMPONENTS)):
        for bit in range(GAS_BITS):
            pressure_code += ((gas_code[:, component] >> bit) & 1) * weights[
                component * GAS_BITS + bit
            ]
    pressure_approx = pressure_code / pressure_levels * pressure_scale
    normalized_error = np.abs(pressure_approx - exact_pressure) / pressure_scale
    above_high = pressure_code > high_pressure_code
    result = {
        "gas_bits_per_component": GAS_BITS,
        "pressure_output_bits": PRESSURE_BITS,
        "gas_component_scales_mol": gas_scales.tolist(),
        "pressure_scale_bar": float(pressure_scale),
        "high_pressure_code": high_pressure_code,
        "pressure_weights": weights,
        "pressure_p95_scale_normalized_absolute_error": float(
            np.quantile(normalized_error, 0.95)
        ),
        "pressure_max_scale_normalized_absolute_error": float(
            np.max(normalized_error)
        ),
        "pressure_above_high_code_count": int(np.sum(above_high)),
        "gas_input_overflow_count": int(
            np.sum((gas_code < 0) | (gas_code > gas_levels))
        ),
    }
    result["passes_pressure_gate"] = bool(
        result["pressure_p95_scale_normalized_absolute_error"] <= PRESSURE_P95_GATE
        and result["pressure_max_scale_normalized_absolute_error"] <= PRESSURE_MAX_GATE
        and result["pressure_above_high_code_count"] == 0
        and result["gas_input_overflow_count"] == 0
    )
    return result, gas_code, pressure_code


def screen_design(
    domain: dict[str, np.ndarray],
    pressure: dict,
    pressure_code: np.ndarray,
    tank_selected: dict,
    common_bits: int,
    address_bits: int,
    reciprocal_bits: int,
    *,
    keep_constants: bool = False,
    demand_duration_s: float = PHASE_DURATION_S,
) -> tuple[dict, dict]:
    pressure_levels = (1 << PRESSURE_BITS) - 1
    common_levels = (1 << common_bits) - 1
    tank_levels = (1 << TANK_BITS) - 1
    fraction_levels = (1 << FRACTION_BITS) - 1
    reciprocal_levels = (1 << reciprocal_bits) - 1
    pressure_scale = float(pressure["pressure_scale_bar"])
    high_pressure_code = int(pressure["high_pressure_code"])

    tank = domain["tank_start_mol"]
    tank_total = np.sum(tank, axis=1)
    exact_demand = domain["demand_proxy_mol"]
    exact_saturated = domain["exact_saturated"]
    exact_withdrawal = domain["exact_withdrawal_mol"]
    exact_next = tank - exact_withdrawal
    common_scale = COMMON_SCALE_HEADROOM * max(
        float(np.max(exact_demand)), float(np.max(tank_total)), 1.0
    )
    deficit_code = high_pressure_code - pressure_code
    if np.any(deficit_code < 0):
        raise AssertionError("pressure exceeds retained P_high code")
    demand_weights = [
        int(
            round(
                (1 << bit)
                * pressure_scale
                / pressure_levels
                * K_IN_MOL_S_BAR
                * demand_duration_s
                / common_scale
                * common_levels
            )
        )
        for bit in range(PRESSURE_BITS)
    ]
    demand_code = np.zeros(len(tank), dtype=np.int64)
    for bit, weight in enumerate(demand_weights):
        demand_code += ((deficit_code >> bit) & 1) * weight

    tank_scales = np.asarray(
        [tank_selected["component_scales_mol"][name] for name in COMPONENTS],
        dtype=float,
    )
    tank_code = np.rint(tank / tank_scales * tank_levels).astype(np.int64)
    tank_weights = [
        int(
            round(
                tank_scales[component]
                / tank_levels
                * (1 << bit)
                / common_scale
                * common_levels
            )
        )
        for component in range(len(COMPONENTS))
        for bit in range(TANK_BITS)
    ]
    tank_total_code = np.zeros(len(tank), dtype=np.int64)
    for component in range(len(COMPONENTS)):
        for bit in range(TANK_BITS):
            tank_total_code += ((tank_code[:, component] >> bit) & 1) * tank_weights[
                component * TANK_BITS + bit
            ]

    positive_totals = np.unique(tank_total_code[tank_total_code > 0])
    thresholds, bin_upper, max_bin_ratio = support_adaptive_bins(
        positive_totals, 1 << address_bits
    )
    address = np.searchsorted(
        np.asarray(thresholds, dtype=np.int64), tank_total_code, side="right"
    )
    reciprocal_shift = int(
        math.floor(
            math.log2(
                reciprocal_levels * float(bin_upper[0]) / fraction_levels
            )
        )
    )
    reciprocal_table = np.floor(
        fraction_levels
        * float(1 << reciprocal_shift)
        / np.asarray(bin_upper, dtype=float)
    ).astype(np.int64)
    reciprocal_code = reciprocal_table[address]
    full_fraction_code = np.asarray(
        (demand_code.astype(object) * reciprocal_code.astype(object))
        >> reciprocal_shift,
        dtype=np.int64,
    )
    fraction_code = full_fraction_code & fraction_levels
    encoded_saturated = demand_code >= tank_total_code
    unsaturated_overflow = (~encoded_saturated) & (
        full_fraction_code > fraction_levels
    )
    proportional_code = np.asarray(
        (tank_code.astype(object) * fraction_code[:, None].astype(object))
        >> FRACTION_BITS,
        dtype=np.int64,
    )
    withdrawal_code = np.where(
        encoded_saturated[:, None], tank_code, proportional_code
    )
    next_code = tank_code - withdrawal_code

    demand_approx = demand_code / common_levels * common_scale
    tank_total_approx = tank_total_code / common_levels * common_scale
    withdrawal_approx = withdrawal_code / tank_levels * tank_scales
    next_approx = next_code / tank_levels * tank_scales
    withdrawal_error = np.abs(withdrawal_approx - exact_withdrawal) / tank_scales
    next_error = np.abs(next_approx - exact_next) / tank_scales
    combined_error = np.concatenate([withdrawal_error.ravel(), next_error.ravel()])
    meaningful_erased = (exact_withdrawal > MEANINGFUL_MOL) & (
        withdrawal_code == 0
    )
    decoded_tank = tank_code / tank_levels * tank_scales
    conservation_error = np.abs(
        np.sum(withdrawal_approx + next_approx - decoded_tank, axis=1)
    ) / common_scale

    result = {
        "common_bits": int(common_bits),
        "address_bits": int(address_bits),
        "reciprocal_bits": int(reciprocal_bits),
        "fraction_bits": FRACTION_BITS,
        "demand_duration_s": float(demand_duration_s),
        "reciprocal_segments": 1 << address_bits,
        "common_scale_mol": float(common_scale),
        "reciprocal_shift_bits": reciprocal_shift,
        "maximum_bin_upper_to_lower_ratio": float(max_bin_ratio),
        "demand_p95_common_scale_normalized_absolute_error": float(
            np.quantile(np.abs(demand_approx - exact_demand) / common_scale, 0.95)
        ),
        "tank_total_p95_common_scale_normalized_absolute_error": float(
            np.quantile(np.abs(tank_total_approx - tank_total) / common_scale, 0.95)
        ),
        "withdrawal_and_next_p95_component_scale_normalized_absolute_error": float(
            np.quantile(combined_error, 0.95)
        ),
        "withdrawal_and_next_max_component_scale_normalized_absolute_error": float(
            np.max(combined_error)
        ),
        "saturation_flag_mismatch_count": int(
            np.sum(encoded_saturated != exact_saturated)
        ),
        "encoded_saturated_records": int(np.sum(encoded_saturated)),
        "encoded_unsaturated_records": int(np.sum(~encoded_saturated)),
        "unsaturated_fraction_overflow_count": int(np.sum(unsaturated_overflow)),
        "modular_next_tank_underflow_count": int(np.sum(next_code < 0)),
        "meaningful_withdrawal_erased_count": int(np.sum(meaningful_erased)),
        "maximum_decoded_component_conservation_error_common_scale": float(
            np.max(conservation_error)
        ),
        "passes_declared_domain_gate": False,
    }
    result["passes_declared_domain_gate"] = bool(
        pressure["passes_pressure_gate"]
        and result["demand_p95_common_scale_normalized_absolute_error"]
        <= DEMAND_P95_GATE
        and result["tank_total_p95_common_scale_normalized_absolute_error"]
        <= TANK_TOTAL_P95_GATE
        and result["withdrawal_and_next_p95_component_scale_normalized_absolute_error"]
        <= WITHDRAWAL_P95_COMPONENT_SCALE_GATE
        and result["withdrawal_and_next_max_component_scale_normalized_absolute_error"]
        <= WITHDRAWAL_MAX_COMPONENT_SCALE_GATE
        and result["saturation_flag_mismatch_count"] == 0
        and result["unsaturated_fraction_overflow_count"] == 0
        and result["modular_next_tank_underflow_count"] == 0
        and result["meaningful_withdrawal_erased_count"] == 0
    )
    design = {
        "pressure_weights": [int(value) for value in pressure["pressure_weights"]],
        "pressure_scale_bar": pressure_scale,
        "high_pressure_code": high_pressure_code,
        "demand_weights": demand_weights,
        "tank_total_weights": tank_weights,
        "denominator_threshold_codes": thresholds,
        "reciprocal_table": reciprocal_table.astype(int).tolist(),
        "common_bits": int(common_bits),
        "address_bits": int(address_bits),
        "reciprocal_bits": int(reciprocal_bits),
        "fraction_bits": FRACTION_BITS,
        "demand_duration_s": float(demand_duration_s),
        "reciprocal_shift_bits": reciprocal_shift,
    }
    if keep_constants:
        result["denominator_threshold_codes"] = thresholds
        result["denominator_bin_upper_codes"] = bin_upper
        result["reciprocal_table"] = reciprocal_table.astype(int).tolist()
    return result, design


def build_circuit(design: dict) -> tuple[QuantumCircuit, dict]:
    pressure_weights = [int(value) for value in design["pressure_weights"]]
    demand_weights = [int(value) for value in design["demand_weights"]]
    tank_weights = [int(value) for value in design["tank_total_weights"]]
    address_bits = int(design["address_bits"])
    reciprocal_bits = int(design["reciprocal_bits"])
    fraction_bits = int(design["fraction_bits"])
    reciprocal_shift = int(design["reciprocal_shift_bits"])
    thresholds = [int(value) for value in design["denominator_threshold_codes"]]
    reciprocal_table = [int(value) for value in design["reciprocal_table"]]

    pressure_adder = WeightedAdder(len(pressure_weights), pressure_weights)
    demand_adder = WeightedAdder(PRESSURE_BITS, demand_weights)
    tank_adder = WeightedAdder(len(tank_weights), tank_weights)
    value_bits = max(demand_adder.num_sum_qubits, tank_adder.num_sum_qubits)
    compare_weights = [1 << bit for bit in range(value_bits)] * 2
    compare_adder = WeightedAdder(2 * value_bits, compare_weights)
    comparator = IntegerComparator(
        compare_adder.num_sum_qubits, (1 << value_bits) - 1, geq=True
    )
    ratio_bits = max(value_bits, reciprocal_bits)
    ratio_multiplier = MultiplierGate(ratio_bits, 2 * ratio_bits)
    component_bits = max(TANK_BITS, fraction_bits)
    component_multiplier = MultiplierGate(component_bits, 2 * component_bits)
    ratio_pad_bits = max(
        1, (ratio_bits - value_bits) + (ratio_bits - reciprocal_bits)
    )
    work_bits = max(
        pressure_adder.num_ancillas,
        demand_adder.num_ancillas,
        tank_adder.num_ancillas,
        compare_adder.num_ancillas,
        comparator.num_ancillas,
        address_bits - 2,
    )

    endpoint_gas = QuantumRegister(len(COMPONENTS) * GAS_BITS, "endpoint_gas")
    tank_current = QuantumRegister(len(COMPONENTS) * TANK_BITS, "tank_current")
    withdrawal = QuantumRegister(len(COMPONENTS) * TANK_BITS, "withdrawal")
    tank_next = QuantumRegister(len(COMPONENTS) * TANK_BITS, "tank_next")
    demand_output = QuantumRegister(value_bits, "demand")
    tank_total_output = QuantumRegister(value_bits, "tank_total")
    saturated_output = QuantumRegister(1, "saturated")
    pressure = QuantumRegister(PRESSURE_BITS, "pressure")
    pressure_sum = QuantumRegister(pressure_adder.num_sum_qubits, "pressure_sum")
    deficit = QuantumRegister(PRESSURE_BITS, "pressure_deficit")
    demand_value = QuantumRegister(value_bits, "demand_value")
    tank_value = QuantumRegister(value_bits, "tank_value")
    compare_sum = QuantumRegister(compare_adder.num_sum_qubits, "compare_sum")
    compare_flag = QuantumRegister(1, "compare_flag")
    address = QuantumRegister(address_bits, "tank_total_address")
    address_flag = QuantumRegister(1, "address_flag")
    reciprocal = QuantumRegister(reciprocal_bits, "tank_total_reciprocal")
    ratio_pad = QuantumRegister(ratio_pad_bits, "ratio_pad")
    ratio_product = QuantumRegister(2 * ratio_bits, "demand_times_reciprocal")
    component_product = QuantumRegister(
        2 * component_bits, "tank_component_times_fraction"
    )
    work = QuantumRegister(work_bits, "work")
    circuit = QuantumCircuit(
        endpoint_gas,
        tank_current,
        withdrawal,
        tank_next,
        demand_output,
        tank_total_output,
        saturated_output,
        pressure,
        pressure_sum,
        deficit,
        demand_value,
        tank_value,
        compare_sum,
        compare_flag,
        address,
        address_flag,
        reciprocal,
        ratio_pad,
        ratio_product,
        component_product,
        work,
        name="clean_pressure_derived_saturated_unsaturated_tank_allocation",
    )

    pressure_qargs = (
        list(endpoint_gas)
        + list(pressure_sum)
        + list(work)[: pressure_adder.num_ancillas]
    )
    circuit.append(pressure_adder, pressure_qargs)
    for source, target in zip(pressure_sum, pressure):
        circuit.cx(source, target)
    high_pressure_code = int(design["high_pressure_code"])
    for bit, qubit in enumerate(deficit):
        if (high_pressure_code >> bit) & 1:
            circuit.x(qubit)
    circuit.append(
        ModularAdderGate(PRESSURE_BITS).inverse(), list(pressure) + list(deficit)
    )

    demand_qargs = (
        list(deficit)
        + list(demand_value)[: demand_adder.num_sum_qubits]
        + list(work)[: demand_adder.num_ancillas]
    )
    tank_qargs = (
        list(tank_current)
        + list(tank_value)[: tank_adder.num_sum_qubits]
        + list(work)[: tank_adder.num_ancillas]
    )
    circuit.append(demand_adder, demand_qargs)
    circuit.append(tank_adder, tank_qargs)
    for source, target in zip(demand_value, demand_output):
        circuit.cx(source, target)
    for source, target in zip(tank_value, tank_total_output):
        circuit.cx(source, target)

    for qubit in tank_value:
        circuit.x(qubit)
    compare_qargs = (
        list(demand_value)
        + list(tank_value)
        + list(compare_sum)
        + list(work)[: compare_adder.num_ancillas]
    )
    circuit.append(compare_adder, compare_qargs)
    comparator_qargs = (
        list(compare_sum)
        + list(compare_flag)
        + list(work)[: comparator.num_ancillas]
    )
    circuit.append(comparator, comparator_qargs)
    circuit.cx(compare_flag[0], saturated_output[0])
    for source, target in zip(tank_current, withdrawal):
        circuit.ccx(compare_flag[0], source, target)

    # The compare adder consumes the one's-complement representation of the
    # tank total.  Restore the original value before using it to address the
    # reciprocal table for the proportional-allocation branch.
    for qubit in reversed(list(tank_value)):
        circuit.x(qubit)

    append_address_extractor(
        circuit,
        list(tank_value),
        list(address),
        address_flag[0],
        list(work),
        thresholds,
    )
    append_reciprocal_qrom(
        circuit,
        list(address),
        list(reciprocal),
        list(work),
        reciprocal_table,
    )
    demand_pad_count = ratio_bits - value_bits
    reciprocal_pad_count = ratio_bits - reciprocal_bits
    demand_operand = list(demand_value) + list(ratio_pad)[:demand_pad_count]
    reciprocal_operand = list(reciprocal) + list(ratio_pad)[
        demand_pad_count : demand_pad_count + reciprocal_pad_count
    ]
    ratio_qargs = demand_operand + reciprocal_operand + list(ratio_product)
    circuit.append(ratio_multiplier, ratio_qargs)
    fraction_operand = list(ratio_product)[
        reciprocal_shift : reciprocal_shift + fraction_bits
    ]
    if len(fraction_operand) != fraction_bits:
        raise AssertionError((reciprocal_shift, ratio_bits, fraction_bits))

    for component in range(len(COMPONENTS)):
        tank_operand = list(tank_current)[
            component * TANK_BITS : (component + 1) * TANK_BITS
        ]
        component_qargs = tank_operand + fraction_operand + list(component_product)
        circuit.append(component_multiplier, component_qargs)
        proportional_window = list(component_product)[
            fraction_bits : fraction_bits + TANK_BITS
        ]
        output = list(withdrawal)[
            component * TANK_BITS : (component + 1) * TANK_BITS
        ]
        circuit.x(compare_flag[0])
        for source, target in zip(proportional_window, output):
            circuit.ccx(compare_flag[0], source, target)
        circuit.x(compare_flag[0])
        circuit.append(component_multiplier.inverse(), component_qargs)

    for source, target in zip(tank_current, tank_next):
        circuit.cx(source, target)
    subtractor = ModularAdderGate(TANK_BITS).inverse()
    for component in range(len(COMPONENTS)):
        operand = list(withdrawal)[
            component * TANK_BITS : (component + 1) * TANK_BITS
        ]
        target = list(tank_next)[
            component * TANK_BITS : (component + 1) * TANK_BITS
        ]
        circuit.append(subtractor, operand + target)

    circuit.append(ratio_multiplier.inverse(), ratio_qargs)
    append_reciprocal_qrom(
        circuit,
        list(address),
        list(reciprocal),
        list(work),
        reciprocal_table,
        inverse=True,
    )
    append_address_extractor(
        circuit,
        list(tank_value),
        list(address),
        address_flag[0],
        list(work),
        thresholds,
        inverse=True,
    )

    # Recreate the complemented operand expected by the comparison inverse.
    for qubit in tank_value:
        circuit.x(qubit)
    circuit.append(comparator.inverse(), comparator_qargs)
    circuit.append(compare_adder.inverse(), compare_qargs)
    for qubit in reversed(list(tank_value)):
        circuit.x(qubit)
    circuit.append(tank_adder.inverse(), tank_qargs)
    circuit.append(demand_adder.inverse(), demand_qargs)
    circuit.append(ModularAdderGate(PRESSURE_BITS), list(pressure) + list(deficit))
    for bit, qubit in reversed(list(enumerate(deficit))):
        if (high_pressure_code >> bit) & 1:
            circuit.x(qubit)
    for source, target in reversed(list(zip(list(pressure_sum), list(pressure)))):
        circuit.cx(source, target)
    circuit.append(pressure_adder.inverse(), pressure_qargs)

    return circuit, {
        "retained_inputs": [
            f"five x {GAS_BITS}-bit endpoint gas inventories",
            f"five x {TANK_BITS}-bit tank inventories",
        ],
        "clean_outputs": [
            f"{value_bits}-bit pressure-derived demand",
            f"{value_bits}-bit tank total",
            "saturation flag",
            f"five x {TANK_BITS}-bit branch-selected withdrawal",
            f"five x {TANK_BITS}-bit next tank",
        ],
        "value_bits": int(value_bits),
        "address_bits": address_bits,
        "reciprocal_bits": reciprocal_bits,
        "fraction_bits": fraction_bits,
        "ratio_multiplier_bits": ratio_bits,
        "component_multiplier_bits": component_bits,
        "cleared": [
            "pressure and pressure deficit",
            "demand/tank sums and comparison flag",
            "tank-total reciprocal address and QROM output",
            "demand-times-reciprocal product",
            "all five component-times-fraction products",
            "all weighted-adder, comparator, multiplier, and QROM workspace",
        ],
    }


def resource_record(circuit: QuantumCircuit) -> dict:
    compiled = transpile(
        circuit,
        basis_gates=["u", "cx"],
        optimization_level=1,
        seed_transpiler=TRANSPILER_SEED,
    )
    counts = compiled.count_ops()
    return {
        "logical_qubits": int(circuit.num_qubits),
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
    observed, replay = support_records()
    domain, flat = arithmetic_domain(observed)
    pressure, _, pressure_code = pressure_design(domain)
    if not pressure["passes_pressure_gate"]:
        raise AssertionError(pressure)
    prior_tank = json.loads(PRIOR_TANK.read_text(encoding="utf-8"))
    tank_selected = prior_tank["tank_encoding"]["selected"]
    if int(tank_selected["bits"]) != TANK_BITS:
        raise AssertionError(tank_selected["bits"])

    screens: list[dict] = []
    designs: dict[tuple[int, int, int], dict] = {}
    for common_bits in COMMON_BITS_CASES:
        for address_bits in ADDRESS_BITS_CASES:
            for reciprocal_bits in RECIPROCAL_BITS_CASES:
                row, design = screen_design(
                    domain,
                    pressure,
                    pressure_code,
                    tank_selected,
                    common_bits,
                    address_bits,
                    reciprocal_bits,
                )
                screens.append(row)
                designs[(common_bits, address_bits, reciprocal_bits)] = design
    selected = next(
        (row for row in screens if row["passes_declared_domain_gate"]), None
    )
    if selected is None:
        raise AssertionError(screens)
    key = (
        int(selected["common_bits"]),
        int(selected["address_bits"]),
        int(selected["reciprocal_bits"]),
    )
    selected_detailed, selected_design = screen_design(
        domain,
        pressure,
        pressure_code,
        tank_selected,
        *key,
        keep_constants=True,
    )
    circuit, layout = build_circuit(selected_design)
    resources = resource_record(circuit)
    if resources["measurement"] or resources["reset"]:
        raise AssertionError(resources)

    csv_rows = []
    for index, row in enumerate(flat):
        csv_rows.append(
            {
                "source": row["source"],
                "sample": row["sample"],
                "slot": row["slot"],
                "demand_fraction": row["demand_fraction"],
                "endpoint_pressure_bar": row["endpoint_pressure_bar"],
                "tank_start_total_mol": float(np.sum(row["tank_start_mol"])),
                "demand_proxy_mol": row["demand_proxy_mol"],
                "exact_saturated": row["exact_saturated"],
                "withdrawal_total_mol": float(np.sum(row["exact_withdrawal_mol"])),
                "record_index": index,
            }
        )

    observed_mask = np.asarray(
        [row["source"].startswith("observed") for row in flat], dtype=bool
    )
    counterfactual_mask = ~observed_mask
    observed_count = int(np.sum(observed_mask))
    counterfactual_count = len(flat) - observed_count
    payload = {
        "schema": "psa-qae-cce-offledger-tank-proportional-interface/v1",
        "status": "pressure_derived_saturated_and_bounded_unsaturated_proportional_tank_allocation_compiled",
        "qpu_submission": False,
        "support": {
            "observed_frozen_final_cycle_records": observed_count,
            "observed_saturated_records": int(
                np.sum(domain["exact_saturated"][observed_mask])
            ),
            "counterfactual_arithmetic_records": counterfactual_count,
            "counterfactual_unsaturated_records": int(
                np.sum(~domain["exact_saturated"][counterfactual_mask])
            ),
            "nonzero_observed_tank_compositions": 32,
            "counterfactual_demand_fractions": list(
                COUNTERFACTUAL_DEMAND_FRACTIONS
            ),
            "components": list(COMPONENTS),
            "counterfactual_role": "bounded arithmetic-domain coverage; not physical trajectory, plant, or industrial validation",
            "allocation_law": "withdrawal_i=min(demand,tank_total)*tank_i/tank_total for tank_total>0; saturated branch copies tank",
        },
        "replay": replay,
        "pressure_encoding": pressure,
        "encoding_screen": screens,
        "selected_design": selected_detailed,
        "circuit_layout": layout,
        "compiled_clean_circuit": resources,
        "claim_boundary": {
            "supported": "one clean pressure-derived circuit selects saturated full-tank withdrawal or support-adaptive unsaturated proportional five-component allocation, subtracts the selected withdrawal, and exactly reverses all arithmetic workspace; observed frozen calls cover the saturated branch and declared counterfactual pressure points cover the unsaturated arithmetic branch",
            "unsupported": "physical occurrence or validation of the counterfactual unsaturated trajectories, an out-of-domain reciprocal guarantee, phase-end state generation inside a monolithic five-component phase unitary, adaptive integration, routing, external H2 validation, or quantum advantage",
        },
    }
    OUT_JSON.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, default=json_default),
        encoding="utf-8",
    )
    with OUT_CSV.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(csv_rows[0]))
        writer.writeheader()
        writer.writerows(csv_rows)
    OUT_MD.write_text(
        "# Pressure-derived saturated/unsaturated proportional tank allocation\n\n"
        f"Status: **{payload['status']}**\n\n"
        f"The domain retains **{observed_count} observed frozen final-cycle calls** and adds **{counterfactual_count} explicitly labelled pressure counterfactuals** over the 32 nonzero observed tank compositions. The counterfactuals cover demand fractions `{', '.join(f'{x:.3f}' for x in COUNTERFACTUAL_DEMAND_FRACTIONS)}` and test arithmetic only; they are not physical trajectories or plant validation.\n\n"
        "The clean circuit reconstructs pressure from five endpoint gas inventories, forms the demand proxy, compares it with tank total, copies the whole tank on saturation, and otherwise evaluates `demand*tank_i/sum(tank)` with a support-adaptive reciprocal and reversible multipliers. It then subtracts the selected five-component withdrawal and reverses all work registers.\n\n"
        f"The selected design uses **{selected_detailed['common_bits']} common bits**, **{selected_detailed['address_bits']} reciprocal-address bits** ({selected_detailed['reciprocal_segments']} segments), and **{selected_detailed['reciprocal_bits']} reciprocal bits**. It preserves **{selected_detailed['encoded_saturated_records']} saturated** and **{selected_detailed['encoded_unsaturated_records']} unsaturated** labels with zero mismatch, fraction overflow, underflow, or meaningful erasure. Withdrawal/next-tank component-scale error is p95 **{selected_detailed['withdrawal_and_next_p95_component_scale_normalized_absolute_error']:.3e}** and maximum **{selected_detailed['withdrawal_and_next_max_component_scale_normalized_absolute_error']:.3e}**.\n\n"
        f"The all-to-all `u`/`CX` compilation uses **{resources['logical_qubits']:,} logical qubits**, depth **{resources['depth_all_to_all']:,}**, and **{resources['cx']:,} CX**, with no measurement or reset.\n\n"
        "This closes the proportional-allocation arithmetic branch over a declared bounded domain. A physically generated unsaturated trajectory, monolithic five-component phase/cycle construction, adaptive integration, routing, external H2 validation, and quantum advantage remain open.\n\n"
        "No QPU job was submitted.\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": payload["status"],
                "records": len(flat),
                "observed": observed_count,
                "counterfactual": counterfactual_count,
                "selected": key,
                "logical_qubits": resources["logical_qubits"],
                "depth": resources["depth_all_to_all"],
                "cx": resources["cx"],
                "qpu_submission": False,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
