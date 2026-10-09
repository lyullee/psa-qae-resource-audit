"""Compile a clean reversible CO2 equilibrium/LDF microstep.

This circuit extends the primary competitive-Langmuir preparation with

* reversible bin extraction from the prepared denominator register,
* a bounded piecewise-constant reciprocal QROM,
* multiplication by the already prepared ``P*y_CO2`` numerator, and
* one explicit one-second CO2 LDF Euler microstep.

The circuit copies the updated loading to a clean output register and then
uncomputes the LDF workspace, product, reciprocal, address, numerator,
denominator, and affinity sum.  Precision is screened over every cell state in
the 32-run, 100-cycle physical cache.  It is one AC-cell/one-component
microstep, not a transport phase, adaptive BDF solve, or full PSA cycle.
No QPU work is submitted.
"""

from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from qiskit import QuantumCircuit, QuantumRegister, transpile
from qiskit.circuit.library import IntegerComparator, MultiplierGate, WeightedAdder
from qiskit.synthesis.multi_controlled import synth_mcx_n_clean_m15


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RESULTS = ROOT / "10_TEA_LCA_Python" / "results" / "pycharm_publication_enhancement"
CACHE = HERE / "cce_primary_physical_css_horizon_cache.npz"
PREPARATION_JSON = RESULTS / "PSA_QAE_CCE_PRIMARY_QSTAR_REVERSIBLE_MICROKERNEL.json"
OUT_JSON = RESULTS / "PSA_QAE_CCE_PRIMARY_QSTAR_LDF_REVERSIBLE_MICROSTEP.json"
OUT_CSV = RESULTS / "PSA_QAE_CCE_PRIMARY_QSTAR_LDF_REVERSIBLE_MICROSTEP.csv"
OUT_MD = RESULTS / "PSA_QAE_CCE_PRIMARY_QSTAR_LDF_REVERSIBLE_MICROSTEP.md"
OUT_PNG = RESULTS / "PSA_QAE_CCE_PRIMARY_QSTAR_LDF_REVERSIBLE_MICROSTEP_FIGURE.png"
OUT_PDF = RESULTS / "PSA_QAE_CCE_PRIMARY_QSTAR_LDF_REVERSIBLE_MICROSTEP_FIGURE.pdf"

sys.path.insert(0, str(HERE.parent))
from psa_qae.psa_spatial_network_probe_n2 import (  # noqa: E402
    A1,
    A2,
    B1,
    B2,
    COMPONENTS,
    LDF,
    SpatialParams,
    cell_pressure,
    cell_y,
)


INPUT_BITS = 18
AFFINITY_COEFFICIENT_BITS = 8
ARITHMETIC_BITS = [20, 22, 24, 26]
ADDRESS_BITS = [4, 5, 6, 7, 8]
LDF_COEFFICIENT_BITS = 8
EULER_DT_S = 1.0
QSTAR_P95_RELATIVE_ERROR_GATE = 5.0e-2
LDF_P95_RELATIVE_ERROR_GATE = 1.0e-3
TRANSPILER_SEED = 20261009


def physical_states() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    cache = np.load(CACHE)
    boundaries = np.asarray(cache["boundaries"], dtype=float)
    if boundaries.shape != (32, 101, 85):
        raise AssertionError(boundaries.shape)
    params = SpatialParams(n_cells=4)
    pressures: list[float] = []
    compositions: list[np.ndarray] = []
    co2_loading: list[float] = []
    for state in boundaries[:, :, :80].reshape(-1, 40):
        gas = state[:20].reshape(5, 4)
        adsorbed = state[20:].reshape(5, 4)
        pressures.extend(cell_pressure(gas, params).tolist())
        compositions.extend(cell_y(gas).T)
        co2_loading.extend(adsorbed[1].tolist())
    return (
        np.asarray(pressures, dtype=float),
        np.asarray(compositions, dtype=float),
        np.asarray(co2_loading, dtype=float),
    )


def physical_constants() -> dict:
    params = SpatialParams(n_cells=1)
    affinity = B1 * np.exp(B2 / params.temperature_K)
    qcap = A1 - A2 * params.temperature_K
    coefficient_levels = (1 << AFFINITY_COEFFICIENT_BITS) - 1
    affinity_integer = np.rint(affinity / np.max(affinity) * coefficient_levels).astype(int)
    return {
        "params": params,
        "affinity": affinity,
        "qcap": qcap,
        "affinity_integer": affinity_integer,
    }


def integer_inputs(
    pressure: np.ndarray,
    composition: np.ndarray,
    constants: dict,
    component_index: int = 1,
) -> dict:
    if not 0 <= component_index < len(COMPONENTS):
        raise ValueError(component_index)
    levels = (1 << INPUT_BITS) - 1
    coefficient_levels = (1 << AFFINITY_COEFFICIENT_BITS) - 1
    pressure_max = float(np.max(pressure))
    affinity = constants["affinity"]
    affinity_integer = constants["affinity_integer"]
    pressure_code = np.rint(pressure / pressure_max * levels).astype(object)
    composition_code = np.rint(composition * levels).astype(object)
    affinity_sum_code = np.asarray(
        [
            sum(int(composition_code[row, component]) * int(affinity_integer[component]) for component in range(len(COMPONENTS)))
            for row in range(len(pressure))
        ],
        dtype=object,
    )
    denominator_scale = levels * levels * coefficient_levels / (
        pressure_max * float(np.max(affinity))
    )
    denominator_one_code = int(round(denominator_scale))
    denominator_code = np.asarray(
        [denominator_one_code + int(pressure_code[row]) * int(affinity_sum_code[row]) for row in range(len(pressure))],
        dtype=object,
    )
    numerator_code = np.asarray(
        [
            int(pressure_code[row]) * int(composition_code[row, component_index])
            for row in range(len(pressure))
        ],
        dtype=object,
    )
    affinity_q = affinity_integer / coefficient_levels * float(np.max(affinity))
    pressure_q = np.asarray(pressure_code, dtype=float) / levels * pressure_max
    composition_q = np.asarray(composition_code, dtype=float) / levels
    denominator_q = 1.0 + pressure_q * np.sum(composition_q * affinity_q[None, :], axis=1)
    return {
        "levels": levels,
        "pressure_max": pressure_max,
        "pressure_code": pressure_code,
        "composition_code": composition_code,
        "affinity_sum_code": affinity_sum_code,
        "denominator_scale": float(denominator_scale),
        "denominator_one_code": denominator_one_code,
        "denominator_code": denominator_code,
        "denominator_q": denominator_q,
        "numerator_code": numerator_code,
    }


def precision_row(
    arithmetic_bits: int,
    address_bits: int,
    pressure: np.ndarray,
    composition: np.ndarray,
    component_loading: np.ndarray,
    constants: dict,
    encoded: dict,
    component_index: int = 1,
) -> dict:
    if not 0 <= component_index < len(COMPONENTS):
        raise ValueError(component_index)
    affinity = constants["affinity"]
    qcap = constants["qcap"]
    exact_denominator = 1.0 + pressure * np.sum(composition * affinity[None, :], axis=1)
    exact_numerator = pressure * composition[:, component_index]
    exact_qstar = (
        qcap[component_index]
        * affinity[component_index]
        * exact_numerator
        / exact_denominator
    )

    denominator_physical = np.asarray(
        [int(value) / encoded["denominator_scale"] for value in encoded["denominator_code"]],
        dtype=float,
    )
    denominator_min = 1.0
    denominator_max = float(max(np.max(exact_denominator), np.max(denominator_physical)))
    address_levels = (1 << address_bits) - 1
    thresholds = [
        int(round((denominator_min + (index - 0.5) * (denominator_max - denominator_min) / address_levels) * encoded["denominator_scale"]))
        for index in range(1, address_levels + 1)
    ]
    address = np.asarray(
        [sum(int(value) >= threshold for threshold in thresholds) for value in encoded["denominator_code"]],
        dtype=int,
    )
    denominator_grid = denominator_min + (denominator_max - denominator_min) * address / address_levels

    arithmetic_levels = (1 << arithmetic_bits) - 1
    natural_loading_scale = float(
        qcap[component_index] * affinity[component_index] * encoded["pressure_max"]
    )
    loading_scale = max(
        natural_loading_scale,
        float(np.max(component_loading)) * 1.001,
    )
    reciprocal_scale_ratio = natural_loading_scale / loading_scale
    reciprocal_code = np.rint(
        (1.0 / denominator_grid) * arithmetic_levels * reciprocal_scale_ratio
    ).astype(object)
    qstar_code = np.asarray(
        [
            (int(encoded["numerator_code"][row]) * int(reciprocal_code[row])) >> (2 * INPUT_BITS)
            for row in range(len(pressure))
        ],
        dtype=object,
    )
    qstar_approx = np.asarray(qstar_code, dtype=float) / arithmetic_levels * loading_scale

    alpha_exact = float(LDF[component_index] * EULER_DT_S)
    alpha_integer = int(round(alpha_exact * (1 << LDF_COEFFICIENT_BITS)))
    retained_integer = (1 << LDF_COEFFICIENT_BITS) - alpha_integer
    loading_code = np.rint(component_loading / loading_scale * arithmetic_levels).astype(object)
    rounding = 1 << (LDF_COEFFICIENT_BITS - 1)
    next_code = np.asarray(
        [
            (
                retained_integer * int(loading_code[row])
                + alpha_integer * int(qstar_code[row])
                + rounding
            )
            >> LDF_COEFFICIENT_BITS
            for row in range(len(pressure))
        ],
        dtype=object,
    )
    next_approx = np.asarray(next_code, dtype=float) / arithmetic_levels * loading_scale
    next_exact = component_loading + alpha_exact * (exact_qstar - component_loading)

    qstar_error = np.abs(qstar_approx - exact_qstar) / np.maximum(np.abs(exact_qstar), 1.0e-15)
    ldf_error = np.abs(next_approx - next_exact) / np.maximum(np.abs(next_exact), 1.0e-15)
    qstar_scale_normalized_error = np.abs(qstar_approx - exact_qstar) / loading_scale
    ldf_scale_normalized_error = np.abs(next_approx - next_exact) / loading_scale
    erased = (exact_qstar > 0.0) & (np.asarray(qstar_code, dtype=float) == 0.0)
    loading_overflow = np.asarray(loading_code, dtype=float) > arithmetic_levels
    row = {
        "component": COMPONENTS[component_index],
        "component_index": component_index,
        "arithmetic_bits": arithmetic_bits,
        "denominator_address_bits": address_bits,
        "reciprocal_segments": 1 << address_bits,
        "ldf_coefficient_bits": LDF_COEFFICIENT_BITS,
        "ldf_alpha_exact": alpha_exact,
        "ldf_alpha_integer": alpha_integer,
        "ldf_alpha_implemented": alpha_integer / (1 << LDF_COEFFICIENT_BITS),
        "natural_qstar_scale_mol_per_kg": natural_loading_scale,
        "loading_scale_mol_per_kg": loading_scale,
        "reciprocal_scale_ratio": reciprocal_scale_ratio,
        "denominator_range": [denominator_min, denominator_max],
        "denominator_threshold_codes": thresholds,
        "qstar_p95_relative_error": float(np.quantile(qstar_error, 0.95)),
        "qstar_max_relative_error": float(np.max(qstar_error)),
        "qstar_p95_loading_scale_normalized_absolute_error": float(
            np.quantile(qstar_scale_normalized_error, 0.95)
        ),
        "ldf_next_p95_relative_error": float(np.quantile(ldf_error, 0.95)),
        "ldf_next_max_relative_error": float(np.max(ldf_error)),
        "ldf_next_p95_loading_scale_normalized_absolute_error": float(
            np.quantile(ldf_scale_normalized_error, 0.95)
        ),
        "nonzero_qstar_erased_fraction": float(np.mean(erased)),
        "loading_input_overflow_fraction": float(np.mean(loading_overflow)),
    }
    row["passes_declared_precision_gate"] = bool(
        row["qstar_p95_relative_error"] <= QSTAR_P95_RELATIVE_ERROR_GATE
        and row["ldf_next_p95_relative_error"] <= LDF_P95_RELATIVE_ERROR_GATE
        and row["nonzero_qstar_erased_fraction"] == 0.0
        and row["loading_input_overflow_fraction"] == 0.0
    )
    return row


def build_preparation(
    constants: dict,
    encoded: dict,
    component_index: int = 1,
    input_bits: int = INPUT_BITS,
) -> tuple[QuantumCircuit, dict]:
    if not 0 <= component_index < len(COMPONENTS):
        raise ValueError(component_index)
    bits = int(input_bits)
    if bits < 1:
        raise ValueError(bits)
    affinity_integer = constants["affinity_integer"]
    weights = [
        int(affinity_integer[component]) * (1 << bit)
        for component in range(len(COMPONENTS))
        for bit in range(bits)
    ]
    adder = WeightedAdder(len(weights), weights)
    sum_bits = int(adder.num_sum_qubits)
    ancillas = int(adder.num_ancillas)
    p0 = 0
    y0 = sum_bits
    sum0 = y0 + len(COMPONENTS) * bits
    anc0 = sum0 + sum_bits
    numerator0 = anc0 + ancillas
    denominator0 = numerator0 + 2 * bits
    total_qubits = denominator0 + 2 * sum_bits
    component_slug = COMPONENTS[component_index].lower()
    circuit = QuantumCircuit(total_qubits, name=f"competitive_langmuir_{component_slug}_preparation")

    state_qubits = list(range(y0, y0 + len(COMPONENTS) * bits))
    sum_qubits = list(range(sum0, sum0 + sum_bits))
    ancilla_qubits = list(range(anc0, anc0 + ancillas))
    circuit.append(adder, state_qubits + sum_qubits + ancilla_qubits)

    component_qubits = list(
        range(y0 + component_index * bits, y0 + (component_index + 1) * bits)
    )
    numerator_qubits = list(range(numerator0, numerator0 + 2 * bits))
    circuit.append(
        MultiplierGate(bits, 2 * bits),
        list(range(p0, p0 + bits)) + component_qubits + numerator_qubits,
    )
    denominator_qubits = list(range(denominator0, denominator0 + 2 * sum_bits))
    for bit in range(2 * sum_bits):
        if (encoded["denominator_one_code"] >> bit) & 1:
            circuit.x(denominator_qubits[bit])
    circuit.append(
        MultiplierGate(sum_bits, 2 * sum_bits),
        list(range(p0, p0 + sum_bits)) + sum_qubits + denominator_qubits,
    )
    return circuit, {
        "pressure": list(range(p0, p0 + bits)),
        "composition": state_qubits,
        "affinity_sum": sum_qubits,
        "numerator": numerator_qubits,
        "denominator": denominator_qubits,
        "component": COMPONENTS[component_index],
        "component_index": component_index,
        "sum_bits": sum_bits,
        "weighted_adder_ancillas": ancillas,
    }


def append_address_extractor(
    circuit: QuantumCircuit,
    denominator: list,
    address: list,
    flag,
    workspace: list,
    thresholds: list[int],
    inverse: bool = False,
) -> None:
    order = range(len(thresholds) - 1, -1, -1) if inverse else range(len(thresholds))
    for offset in order:
        index = offset + 1
        comparator = IntegerComparator(len(denominator), thresholds[offset], geq=True)
        qargs = denominator + [flag] + workspace[: comparator.num_ancillas]
        circuit.append(comparator, qargs)
        changed = index ^ (index - 1)
        for bit in range(len(address)):
            if (changed >> bit) & 1:
                circuit.cx(flag, address[bit])
        circuit.append(comparator.inverse(), qargs)


def reciprocal_table(row: dict) -> list[int]:
    levels = (1 << int(row["arithmetic_bits"])) - 1
    address_levels = (1 << int(row["denominator_address_bits"])) - 1
    dmin, dmax = row["denominator_range"]
    return [
        int(
            round(
                (1.0 / (dmin + (dmax - dmin) * address / address_levels))
                * levels
                * float(row.get("reciprocal_scale_ratio", 1.0))
            )
        )
        for address in range(address_levels + 1)
    ]


def append_reciprocal_qrom(
    circuit: QuantumCircuit,
    address: list,
    reciprocal: list,
    workspace: list,
    table: list[int],
    inverse: bool = False,
) -> None:
    mcx = synth_mcx_n_clean_m15(len(address))
    address_order = range(len(table) - 1, -1, -1) if inverse else range(len(table))
    for code in address_order:
        zero_controls = [bit for bit in range(len(address)) if not ((code >> bit) & 1)]
        for bit in zero_controls:
            circuit.x(address[bit])
        output_bits = [bit for bit in range(len(reciprocal)) if (table[code] >> bit) & 1]
        if inverse:
            output_bits.reverse()
        for bit in output_bits:
            circuit.append(mcx, address + [reciprocal[bit]] + workspace[: len(address) - 2])
        for bit in reversed(zero_controls):
            circuit.x(address[bit])


def build_clean_microstep(
    constants: dict,
    encoded: dict,
    selected: dict,
    component_index: int = 1,
    ldf_coefficient_bits: int = LDF_COEFFICIENT_BITS,
    input_bits: int = INPUT_BITS,
) -> tuple[QuantumCircuit, dict]:
    if not 0 <= component_index < len(COMPONENTS):
        raise ValueError(component_index)
    component_slug = COMPONENTS[component_index].lower()
    input_bits = int(input_bits)
    preparation, layout = build_preparation(
        constants, encoded, component_index, input_bits=input_bits
    )
    circuit = QuantumCircuit(
        preparation.num_qubits,
        name=f"clean_{component_slug}_qstar_ldf_microstep",
    )
    circuit.compose(preparation, list(range(preparation.num_qubits)), inplace=True)

    arithmetic_bits = int(selected["arithmetic_bits"])
    if arithmetic_bits > 2 * input_bits:
        raise ValueError(
            f"arithmetic_bits={arithmetic_bits} exceeds 2*input_bits={2 * input_bits}"
        )
    address_bits = int(selected["denominator_address_bits"])
    address_reg = QuantumRegister(address_bits, "den_addr")
    work_reg = QuantumRegister(len(layout["denominator"]), "shared_work")
    reciprocal_reg = QuantumRegister(arithmetic_bits, "reciprocal")
    product_reg = QuantumRegister(2 * input_bits + arithmetic_bits, "num_times_recip")
    loading_reg = QuantumRegister(arithmetic_bits, f"q_{component_slug}")
    qstar_reg = QuantumRegister(arithmetic_bits, f"qstar_{component_slug}")

    selected_coefficient_bits = int(
        selected.get("ldf_coefficient_bits", ldf_coefficient_bits)
    )
    if selected_coefficient_bits != int(ldf_coefficient_bits):
        raise AssertionError(
            (selected_coefficient_bits, int(ldf_coefficient_bits))
        )
    alpha_integer = int(selected["ldf_alpha_integer"])
    retained_integer = (1 << selected_coefficient_bits) - alpha_integer
    weights = (
        [retained_integer * (1 << bit) for bit in range(arithmetic_bits)]
        + [alpha_integer * (1 << bit) for bit in range(arithmetic_bits)]
    )
    ldf_adder = WeightedAdder(len(weights), weights)
    ldf_sum_reg = QuantumRegister(ldf_adder.num_sum_qubits, "ldf_sum")
    next_loading_reg = QuantumRegister(arithmetic_bits, f"q_{component_slug}_next")
    circuit.add_register(
        address_reg,
        work_reg,
        reciprocal_reg,
        product_reg,
        loading_reg,
        qstar_reg,
        ldf_sum_reg,
        next_loading_reg,
    )

    denominator = [circuit.qubits[index] for index in layout["denominator"]]
    numerator = [circuit.qubits[index] for index in layout["numerator"]]
    address = list(address_reg)
    work = list(work_reg)
    thresholds = [int(value) for value in selected["denominator_threshold_codes"]]
    append_address_extractor(circuit, denominator, address, work[0], work[1:], thresholds)

    table = reciprocal_table(selected)
    append_reciprocal_qrom(circuit, address, list(reciprocal_reg), work, table)
    reciprocal_operand = list(reciprocal_reg) + work[: 2 * input_bits - arithmetic_bits]
    multiplier = MultiplierGate(2 * input_bits, 2 * input_bits + arithmetic_bits)
    circuit.append(multiplier, numerator + reciprocal_operand + list(product_reg))

    high_product = list(product_reg)[2 * input_bits : 2 * input_bits + arithmetic_bits]
    for source, target in zip(high_product, list(qstar_reg)):
        circuit.cx(source, target)

    rounding_bit = selected_coefficient_bits - 1
    circuit.x(ldf_sum_reg[rounding_bit])
    ldf_qargs = list(loading_reg) + list(qstar_reg) + list(ldf_sum_reg) + work[: ldf_adder.num_ancillas]
    circuit.append(ldf_adder, ldf_qargs)
    for source, target in zip(
        list(ldf_sum_reg)[
            selected_coefficient_bits : selected_coefficient_bits + arithmetic_bits
        ],
        list(next_loading_reg),
    ):
        circuit.cx(source, target)
    circuit.append(ldf_adder.inverse(), ldf_qargs)
    circuit.x(ldf_sum_reg[rounding_bit])

    for source, target in reversed(list(zip(high_product, list(qstar_reg)))):
        circuit.cx(source, target)
    circuit.append(multiplier.inverse(), numerator + reciprocal_operand + list(product_reg))
    append_reciprocal_qrom(circuit, address, list(reciprocal_reg), work, table, inverse=True)
    append_address_extractor(circuit, denominator, address, work[0], work[1:], thresholds, inverse=True)
    circuit.compose(preparation.inverse(), list(range(preparation.num_qubits)), inplace=True)

    return circuit, {
        "preparation_qubits": preparation.num_qubits,
        "input_bits_per_pressure_and_composition": input_bits,
        "denominator_register_bits": len(denominator),
        "numerator_register_bits": len(numerator),
        "denominator_address_bits": address_bits,
        "reciprocal_bits": arithmetic_bits,
        "loading_bits": arithmetic_bits,
        "ldf_coefficient_bits": selected_coefficient_bits,
        "ldf_sum_bits": ldf_adder.num_sum_qubits,
        "shared_workspace_bits": len(work),
        "qrom_clean_ancillas_reused": address_bits - 2,
        "multiplier_zero_padding_reused": 2 * input_bits - arithmetic_bits,
        "ldf_adder_ancillas_reused": ldf_adder.num_ancillas,
        "reciprocal_table": table,
        "component": COMPONENTS[component_index],
        "component_index": component_index,
        "clean_output": f"q_{component_slug}_next",
    }


def main() -> None:
    prior = json.loads(PREPARATION_JSON.read_text(encoding="utf-8"))
    if prior["selected"]["bits_per_pressure_and_composition"] != INPUT_BITS:
        raise AssertionError(prior["selected"])
    pressure, composition, co2_loading = physical_states()
    constants = physical_constants()
    encoded = integer_inputs(pressure, composition, constants)
    rows = [
        precision_row(bits, address, pressure, composition, co2_loading, constants, encoded)
        for bits in ARITHMETIC_BITS
        for address in ADDRESS_BITS
    ]
    selected = next((row for row in rows if row["passes_declared_precision_gate"]), None)
    if selected is None:
        raise AssertionError("no screened reciprocal/LDF precision passes")

    circuit, layout = build_clean_microstep(constants, encoded, selected)
    compiled = transpile(
        circuit,
        basis_gates=["u", "cx"],
        optimization_level=1,
        seed_transpiler=TRANSPILER_SEED,
    )
    resources = {
        "logical_qubits": int(compiled.num_qubits),
        "depth_all_to_all": int(compiled.depth()),
        "cx": int(compiled.count_ops().get("cx", 0)),
        "u": int(compiled.count_ops().get("u", 0)),
        "measurement": int(compiled.count_ops().get("measure", 0)),
        "reset": int(compiled.count_ops().get("reset", 0)),
        "transpiler_seed": TRANSPILER_SEED,
        "basis_gates": ["u", "cx"],
        "optimization_level": 1,
    }
    payload = {
        "schema": "psa-qae-cce-primary-qstar-ldf-reversible-microstep/v1",
        "status": "competitive_langmuir_reciprocal_and_co2_ldf_microstep_compiled_full_phase_cycle_open",
        "qpu_submission": False,
        "physical_state_source": {
            "runs": 32,
            "cycles_per_run": 100,
            "cells_per_bed": 4,
            "beds": 2,
            "cell_states_evaluated": int(len(pressure)),
            "pressure_range_bar": [float(np.min(pressure)), float(np.max(pressure))],
            "co2_mole_fraction_range": [float(np.min(composition[:, 1])), float(np.max(composition[:, 1]))],
            "co2_loading_range_mol_per_kg": [float(np.min(co2_loading)), float(np.max(co2_loading))],
        },
        "equations": {
            "equilibrium": "q_CO2_star = qcap_CO2*b_CO2*P*y_CO2/(1 + P*sum_j(b_j*y_j))",
            "ldf_microstep": "q_CO2_next = q_CO2 + k_CO2*dt*(q_CO2_star - q_CO2)",
            "k_CO2_s_inv": float(LDF[1]),
            "dt_s": EULER_DT_S,
            "adsorbent": "activated carbon branch of the primary spatial/tank model",
        },
        "precision_gate": {
            "qstar_p95_relative_error_max": QSTAR_P95_RELATIVE_ERROR_GATE,
            "ldf_next_p95_relative_error_max": LDF_P95_RELATIVE_ERROR_GATE,
            "nonzero_qstar_erased_fraction_required": 0.0,
        },
        "rows": rows,
        "selected": selected,
        "register_layout": layout,
        "compiled_clean_microstep": resources,
        "cleanliness_by_construction": {
            "sequence": [
                "competitive-Langmuir numerator/denominator preparation",
                "denominator-bin compute",
                "reciprocal QROM compute",
                "numerator-times-reciprocal multiply",
                "copy qstar high product",
                "weighted LDF sum and copy q_CO2_next",
                "inverse weighted LDF sum",
                "clear copied qstar",
                "inverse multiplier",
                "inverse reciprocal QROM",
                "inverse denominator-bin compute",
                "inverse numerator/denominator preparation",
            ],
            "retained_registers": ["18-bit pressure/composition inputs", "24-bit q_CO2 input", "24-bit q_CO2_next output"],
            "cleared_register_classes": ["affinity sum", "numerator", "denominator", "address", "reciprocal", "product", "qstar copy", "LDF sum", "shared workspace"],
        },
        "claim_boundary": {
            "supported": "physical-cache precision screen and primitive-gate compilation of one clean activated-carbon CO2 competitive-Langmuir reciprocal plus one-second explicit LDF loading microstep",
            "unsupported": "the other four component loadings, gas-phase transport, pressure/valve/tank arithmetic, adaptive BDF integration, a complete adsorption phase or cyclic PSA oracle, hardware feasibility, or quantum advantage",
        },
    }
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    csv_rows = []
    for row in rows:
        flat = {key: value for key, value in row.items() if key not in {"denominator_range", "denominator_threshold_codes"}}
        flat["denominator_min"] = row["denominator_range"][0]
        flat["denominator_max"] = row["denominator_range"][1]
        csv_rows.append(flat)
    with OUT_CSV.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(csv_rows[0]))
        writer.writeheader()
        writer.writerows(csv_rows)

    OUT_MD.write_text(
        "\n".join(
            [
                "# Clean competitive-Langmuir reciprocal and CO2 LDF microstep",
                "",
                f"The precision screen covers **{len(pressure):,}** physical cell states. The first passing tier uses **{selected['denominator_address_bits']} denominator-address bits** ({selected['reciprocal_segments']} QROM segments) and **{selected['arithmetic_bits']}-bit reciprocal/loading arithmetic**.",
                "",
                f"At this tier the p95 relative error is **{selected['qstar_p95_relative_error']:.4%}** for CO2 equilibrium loading and **{selected['ldf_next_p95_relative_error']:.4%}** for the one-second LDF update. No nonzero equilibrium loading is erased.",
                "",
                f"The clean compute-copy-uncompute circuit uses **{resources['logical_qubits']} logical qubits**, depth **{resources['depth_all_to_all']:,}**, and **{resources['cx']:,} CX** in the all-to-all `u/CX` basis. It includes the earlier 18-bit five-component numerator/denominator preparation and uncomputes all work registers after copying the updated CO2 loading.",
                "",
                "This is a one-cell, one-component, one-second explicit kinetic microstep. The other four loadings, gas transport, valve/tank balances, adaptive integration, repeated phase/cycle execution, routing, and QPU execution remain open.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    fig, axes = plt.subplots(1, 3, figsize=(13.4, 4.4), constrained_layout=True)
    for address_bits in ADDRESS_BITS:
        subset = [row for row in rows if row["denominator_address_bits"] == address_bits]
        axes[0].semilogy(
            [row["arithmetic_bits"] for row in subset],
            [row["qstar_p95_relative_error"] for row in subset],
            marker="o",
            label=f"{address_bits}-bit address",
        )
    axes[0].axhline(QSTAR_P95_RELATIVE_ERROR_GATE, color="#b91c1c", ls="--", lw=1)
    axes[0].scatter([selected["arithmetic_bits"]], [selected["qstar_p95_relative_error"]], color="#166534", s=70, zorder=4)
    axes[0].set(xlabel="reciprocal/loading bits", ylabel="q* p95 relative error", title="Equilibrium division accuracy")
    axes[0].grid(alpha=0.25, which="both"); axes[0].legend(fontsize=7)

    for address_bits in ADDRESS_BITS:
        subset = [row for row in rows if row["denominator_address_bits"] == address_bits]
        axes[1].semilogy(
            [row["arithmetic_bits"] for row in subset],
            [row["ldf_next_p95_relative_error"] for row in subset],
            marker="s",
            label=f"{address_bits}-bit address",
        )
    axes[1].axhline(LDF_P95_RELATIVE_ERROR_GATE, color="#b91c1c", ls="--", lw=1)
    axes[1].scatter([selected["arithmetic_bits"]], [selected["ldf_next_p95_relative_error"]], color="#166534", s=70, zorder=4)
    axes[1].set(xlabel="reciprocal/loading bits", ylabel="LDF-next p95 relative error", title="One-second kinetic update")
    axes[1].grid(alpha=0.25, which="both")

    axes[2].axis("off")
    summary = (
        f"Selected: {selected['denominator_address_bits']}-bit address, {selected['arithmetic_bits']}-bit arithmetic\n\n"
        f"Clean circuit\n{resources['logical_qubits']} logical qubits\n"
        f"{resources['cx']:,} CX\ndepth {resources['depth_all_to_all']:,}\n\n"
        "Includes reciprocal + CO2 LDF\n"
        "Excludes transport/valves/tank/full phase"
    )
    axes[2].text(0.5, 0.52, summary, ha="center", va="center", fontsize=12, bbox=dict(boxstyle="round,pad=0.8", facecolor="#fff4e6", edgecolor="#b35c00", linewidth=1.7))
    fig.suptitle("A clean physical CO2 equilibrium/kinetic microstep is compilable, but it is not a PSA phase", fontsize=13.5, fontweight="bold")
    fig.savefig(OUT_PNG, dpi=260)
    fig.savefig(OUT_PDF)
    plt.close(fig)

    print(
        json.dumps(
            {
                "status": payload["status"],
                "selected_arithmetic_bits": selected["arithmetic_bits"],
                "selected_address_bits": selected["denominator_address_bits"],
                "logical_qubits": resources["logical_qubits"],
                "cx": resources["cx"],
                "depth": resources["depth_all_to_all"],
                "qpu_submission": False,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
