"""Directly compose gas normalization, pressure, two faces, and cell balances.

The preceding interior-cell circuit supplied two 20-bit five-component
upwind-composition registers independently of the three encoded gas inventory
registers.  This script removes that interface over the frozen physical
support.  For the left and centre cells it

1. converts the five component-specific 18-bit gas codes to one common amount
   scale;
2. forms a total-gas code and a support-adaptive reciprocal address;
3. loads a bounded reciprocal from a clean QROM;
4. multiplies each common-scale component amount by that reciprocal to produce
   five 20-bit mole fractions;
5. feeds those temporary mole fractions, reconstructed pressures, and both
   temporary face-flux registers directly into five centre-cell balances; and
6. reverses the face, pressure, and normalization work after copying the five
   next-gas outputs.

The reciprocal segmentation is frozen from the same cached physical support
used by the resource audit.  It is not a general out-of-domain normalization
oracle.  Centre-cell LDF generation, run-specific parameter registers,
boundary/tank logic, adaptive integration, routing, and a complete phase/cycle
remain open.  No QPU work is submitted.
"""

from __future__ import annotations

import csv
import heapq
import json
import math
from pathlib import Path

import numpy as np
from qiskit import QuantumCircuit, QuantumRegister, transpile
from qiskit.circuit.library import IntegerComparator, MultiplierGate, WeightedAdder

from cce_primary_internal_face_balance_composition import (
    INPUT_BITS as BALANCE_INPUT_BITS,
    OUTPUT_BITS as BALANCE_OUTPUT_BITS,
    P95_NEXT_SCALE_NORMALIZED_GATE,
    MAX_NEXT_SCALE_NORMALIZED_GATE,
    P95_ARITHMETIC_ONLY_GATE,
    MAX_ARITHMETIC_ONLY_GATE,
    interior_terms,
    module_register_map,
    precision_row as balance_precision_row,
    resource_record,
)
from cce_primary_internal_transport_reversible_microsteps import (
    OUT_JSON as TRANSPORT_JSON,
    build_face_circuit,
    build_pressure_circuit,
)
from cce_primary_loading_sign_balance_interface import register_indices
from cce_primary_qstar_ldf_reversible_microstep import (
    append_address_extractor,
    append_reciprocal_qrom,
)
from psa_spatial_network_probe_n2 import COMPONENTS


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RESULTS = ROOT / "10_TEA_LCA_Python" / "results" / "pycharm_publication_enhancement"
OUT_JSON = RESULTS / "PSA_QAE_CCE_PRIMARY_COMPOSITION_NORMALIZED_INTERNAL_FACE_BALANCE.json"
OUT_CSV = RESULTS / "PSA_QAE_CCE_PRIMARY_COMPOSITION_NORMALIZED_INTERNAL_FACE_BALANCE.csv"
OUT_MD = RESULTS / "PSA_QAE_CCE_PRIMARY_COMPOSITION_NORMALIZED_INTERNAL_FACE_BALANCE.md"

AMOUNT_BITS = (18, 20, 22)
RECIPROCAL_BITS = (18, 20, 22, 24)
ADDRESS_BITS = (5, 6, 7, 8)
COMPOSITION_BITS = 20

# These are interface checks on the reconstructed mole fractions.  Candidate
# selection additionally requires the already frozen face and next-inventory
# precision gates to pass after the generated composition is propagated.
COMPOSITION_P95_ABSOLUTE_GATE = 2.5e-3
COMPOSITION_MAX_ABSOLUTE_GATE = 5.0e-3
COMPOSITION_SUM_P95_GATE = 2.5e-3
COMPOSITION_SUM_MAX_GATE = 5.0e-3
FACE_FLUX_P95_FLOW_SCALE_GATE = 2.5e-3
TOTAL_SCALE_HEADROOM_FACTOR = 1.001
TRANSPILER_SEED = 20261009


def encoded_gas(
    gas: np.ndarray,
    selected_pressure: dict,
) -> tuple[np.ndarray, np.ndarray, int]:
    gas_bits = int(selected_pressure["gas_bits_per_component"])
    levels = (1 << gas_bits) - 1
    scales = np.asarray(selected_pressure["gas_component_scales_mol"], dtype=float)
    codes = np.rint(gas / scales[None, :] * levels).astype(np.int64)
    if np.any(codes < 0) or np.any(codes > levels):
        raise AssertionError("gas code outside the retained pressure-input register")
    return codes, scales, levels


def common_amount_weights(
    amount_bits: int,
    selected_pressure: dict,
    total_scale: float,
) -> list[list[int]]:
    gas_bits = int(selected_pressure["gas_bits_per_component"])
    gas_levels = (1 << gas_bits) - 1
    amount_levels = (1 << amount_bits) - 1
    scales = np.asarray(selected_pressure["gas_component_scales_mol"], dtype=float)
    return [
        [
            int(
                round(
                    scales[component]
                    / gas_levels
                    * (1 << bit)
                    / total_scale
                    * amount_levels
                )
            )
            for bit in range(gas_bits)
        ]
        for component in range(len(COMPONENTS))
    ]


def weighted_component_codes(
    gas_codes: np.ndarray,
    weights: list[list[int]],
) -> np.ndarray:
    output = np.zeros((len(gas_codes), len(COMPONENTS)), dtype=np.int64)
    for component in range(len(COMPONENTS)):
        for bit, weight in enumerate(weights[component]):
            output[:, component] += (
                (gas_codes[:, component] >> bit) & 1
            ) * int(weight)
    return output


def support_adaptive_bins(
    values: np.ndarray,
    bin_count: int,
) -> tuple[list[int], list[int], float]:
    """Split observed positive codes by repeatedly bisecting log-width.

    Empty physical intervals consume no address.  Each table value later uses
    the largest observed denominator in its bin, which makes the reconstructed
    composition conservative and prevents overflow on the frozen support.
    """

    unique = np.unique(np.asarray(values, dtype=np.int64))
    if unique[0] <= 0:
        raise AssertionError("normalization denominator must be positive")
    if len(unique) < bin_count:
        raise AssertionError((len(unique), bin_count))
    bins: dict[int, tuple[int, int]] = {0: (0, len(unique) - 1)}
    heap: list[tuple[float, int, int]] = []
    serial = 0

    def push(key: int, low: int, high: int) -> None:
        nonlocal serial
        if high <= low:
            return
        score = math.log(float(unique[high]) / float(unique[low]))
        heapq.heappush(heap, (-score, serial, key))
        serial += 1

    push(0, 0, len(unique) - 1)
    next_key = 1
    while len(bins) < bin_count:
        if not heap:
            raise AssertionError("insufficient distinct denominator support")
        _, _, key = heapq.heappop(heap)
        if key not in bins:
            continue
        low, high = bins.pop(key)
        target = math.sqrt(float(unique[low]) * float(unique[high]))
        split = int(np.searchsorted(unique, target, side="right"))
        split = min(max(split, low + 1), high)
        left_key, right_key = next_key, next_key + 1
        next_key += 2
        bins[left_key] = (low, split - 1)
        bins[right_key] = (split, high)
        push(left_key, low, split - 1)
        push(right_key, split, high)

    ordered = sorted(bins.values())
    thresholds = [int(unique[low]) for low, _ in ordered[1:]]
    upper = [int(unique[high]) for _, high in ordered]
    lower = [int(unique[low]) for low, _ in ordered]
    max_ratio = max(float(high) / float(low) for low, high in zip(lower, upper))
    if len(thresholds) != bin_count - 1 or len(upper) != bin_count:
        raise AssertionError((len(thresholds), len(upper), bin_count))
    return thresholds, upper, max_ratio


def normalization_design(
    gas_support: np.ndarray,
    exact_composition: np.ndarray,
    selected_pressure: dict,
    amount_bits: int,
    reciprocal_bits: int,
    address_bits: int,
    keep_circuit_constants: bool = False,
) -> tuple[dict, np.ndarray]:
    gas_codes, _, _ = encoded_gas(gas_support, selected_pressure)
    total_scale = float(np.max(np.sum(gas_support, axis=1))) * TOTAL_SCALE_HEADROOM_FACTOR
    weights = common_amount_weights(amount_bits, selected_pressure, total_scale)
    component_codes = weighted_component_codes(gas_codes, weights)
    total_codes = np.sum(component_codes, axis=1)
    segments = 1 << address_bits
    thresholds, upper, max_bin_ratio = support_adaptive_bins(total_codes, segments)
    addresses = np.searchsorted(
        np.asarray(thresholds, dtype=np.int64), total_codes, side="right"
    )

    composition_levels = (1 << COMPOSITION_BITS) - 1
    reciprocal_levels = (1 << reciprocal_bits) - 1
    shift = int(
        math.floor(
            math.log2(reciprocal_levels * float(upper[0]) / composition_levels)
        )
    )
    if shift < 0:
        raise AssertionError("reciprocal register cannot represent the lowest denominator")
    table = np.floor(
        composition_levels
        * float(1 << shift)
        / np.asarray(upper, dtype=float)
    ).astype(np.int64)
    if np.any(table < 0) or np.any(table > reciprocal_levels):
        raise AssertionError("reciprocal table overflow")
    full_shifted_product = (
        component_codes * table[addresses, None]
    ) >> shift
    output_overflow = full_shifted_product > composition_levels
    composition_codes = full_shifted_product & composition_levels
    approx = composition_codes.astype(float) / composition_levels
    error = np.abs(approx - exact_composition)
    sum_error = np.abs(np.sum(approx, axis=1) - 1.0)
    erased = (exact_composition > 0.0) & (composition_codes == 0)
    total_weight_sum = int(sum(sum(row) for row in weights))
    component_sum_bits = [
        int(math.ceil(math.log2(sum(row) + 1))) for row in weights
    ]
    row = {
        "amount_bits": amount_bits,
        "reciprocal_bits": reciprocal_bits,
        "address_bits": address_bits,
        "reciprocal_segments": segments,
        "composition_output_bits_per_component": COMPOSITION_BITS,
        "total_scale_mol": total_scale,
        "total_scale_headroom_factor": TOTAL_SCALE_HEADROOM_FACTOR,
        "total_sum_bits": int(math.ceil(math.log2(total_weight_sum + 1))),
        "maximum_component_sum_bits": max(component_sum_bits),
        "multiplier_state_bits": max(max(component_sum_bits), reciprocal_bits),
        "reciprocal_shift_bits": shift,
        "minimum_observed_total_code": int(np.min(total_codes)),
        "maximum_observed_total_code": int(np.max(total_codes)),
        "maximum_bin_upper_to_lower_ratio": max_bin_ratio,
        "composition_p95_absolute_error": {
            component: float(np.quantile(error[:, index], 0.95))
            for index, component in enumerate(COMPONENTS)
        },
        "composition_max_absolute_error": {
            component: float(np.max(error[:, index]))
            for index, component in enumerate(COMPONENTS)
        },
        "composition_sum_p95_absolute_error": float(np.quantile(sum_error, 0.95)),
        "composition_sum_max_absolute_error": float(np.max(sum_error)),
        "maximum_nonzero_composition_erased_fraction": float(
            np.max(np.mean(erased, axis=0))
        ),
        "composition_output_overflow_fraction": float(np.mean(output_overflow)),
    }
    row["passes_composition_precision_gate"] = bool(
        max(row["composition_p95_absolute_error"].values())
        <= COMPOSITION_P95_ABSOLUTE_GATE
        and max(row["composition_max_absolute_error"].values())
        <= COMPOSITION_MAX_ABSOLUTE_GATE
        and row["composition_sum_p95_absolute_error"] <= COMPOSITION_SUM_P95_GATE
        and row["composition_sum_max_absolute_error"] <= COMPOSITION_SUM_MAX_GATE
        and row["maximum_nonzero_composition_erased_fraction"] == 0.0
        and row["composition_output_overflow_fraction"] == 0.0
    )
    if keep_circuit_constants:
        row |= {
            "common_amount_weights_by_component": weights,
            "component_sum_bits": component_sum_bits,
            "denominator_threshold_codes": thresholds,
            "denominator_bin_upper_codes": upper,
            "reciprocal_table": table.astype(int).tolist(),
        }
    return row, composition_codes


def normalized_face_flux_codes(
    terms: dict[str, np.ndarray],
    selected_pressure: dict,
    selected_face: dict,
    composition_codes: np.ndarray,
) -> tuple[np.ndarray, dict]:
    state_count = len(terms["next_gas"])
    composition_codes = composition_codes.reshape(
        state_count, 2, len(COMPONENTS)
    )
    gas = terms["gas_triplet"]
    gas_bits = int(selected_pressure["gas_bits_per_component"])
    gas_levels = (1 << gas_bits) - 1
    scales = np.asarray(selected_pressure["gas_component_scales_mol"], dtype=float)
    gas_codes = np.rint(gas / scales[None, None, :] * gas_levels).astype(np.int64)
    pressure_weights = [int(value) for value in selected_pressure["pressure_weights"]]
    pressure_codes = np.zeros(gas.shape[:2], dtype=np.int64)
    for component in range(len(COMPONENTS)):
        for bit in range(gas_bits):
            pressure_codes += ((gas_codes[:, :, component] >> bit) & 1) * pressure_weights[
                component * gas_bits + bit
            ]
    differences = pressure_codes[:, :-1] - pressure_codes[:, 1:]
    if np.any(differences < 0):
        raise AssertionError("reconstructed pressure difference underflow")
    flow_weights = [int(value) for value in selected_face["flow_weights"]]
    flow_codes = np.zeros_like(differences)
    for bit, weight in enumerate(flow_weights):
        flow_codes += ((differences >> bit) & 1) * weight
    flux_codes = (
        flow_codes[:, :, None] * composition_codes
    ) >> COMPOSITION_BITS
    flow_levels = (1 << int(selected_face["flow_effective_bits"])) - 1
    flow_scale = float(selected_face["flow_scale_mol_s"])
    approx = flux_codes / flow_levels * flow_scale
    exact = np.stack(
        [terms["left_influx"], terms["right_outflux"]], axis=1
    )
    error = np.abs(approx - exact) / flow_scale
    erased = (exact > 0.0) & (flux_codes == 0)
    diagnostics = {
        "pressure_difference_underflow_fraction": float(np.mean(differences < 0)),
        "nonzero_face_flux_erased_fraction": float(np.mean(erased)),
        "component_p95_flow_scale_normalized_error": {
            component: float(np.quantile(error[:, :, index], 0.95))
            for index, component in enumerate(COMPONENTS)
        },
        "component_max_flow_scale_normalized_error": {
            component: float(np.max(error[:, :, index]))
            for index, component in enumerate(COMPONENTS)
        },
    }
    diagnostics["passes_propagated_face_precision_gate"] = bool(
        max(diagnostics["component_p95_flow_scale_normalized_error"].values())
        <= FACE_FLUX_P95_FLOW_SCALE_GATE
        and diagnostics["pressure_difference_underflow_fraction"] == 0.0
        and diagnostics["nonzero_face_flux_erased_fraction"] == 0.0
    )
    return flux_codes.astype(np.int64), diagnostics


def select_balance_rows(
    terms: dict[str, np.ndarray],
    flux_codes: np.ndarray,
    selected_face: dict,
) -> tuple[list[dict], list[dict]]:
    selected_rows: list[dict] = []
    all_rows: list[dict] = []
    for component_index in range(len(COMPONENTS)):
        rows = [
            balance_precision_row(
                component_index,
                input_bits,
                output_bits,
                terms,
                flux_codes,
                selected_face,
            )
            for input_bits in BALANCE_INPUT_BITS
            for output_bits in BALANCE_OUTPUT_BITS
        ]
        selected = next(
            (
                row
                for row in rows
                if row["passes_internal_face_balance_precision_gate"]
            ),
            None,
        )
        if selected is None:
            return [], all_rows + rows
        selected_rows.append(selected)
        all_rows.extend(rows)
    return selected_rows, all_rows


def screen_candidates(
    terms: dict[str, np.ndarray],
    selected_pressure: dict,
    selected_face: dict,
) -> tuple[list[dict], dict, list[dict], dict]:
    gas_support = terms["gas_triplet"][:, :2, :].reshape(-1, len(COMPONENTS))
    exact_composition = terms["composition_pair"].reshape(-1, len(COMPONENTS))
    rows: list[dict] = []
    selected_summary: dict | None = None
    selected_balance: list[dict] = []
    selected_face_diagnostics: dict | None = None
    ordering = sorted(
        (
            (amount_bits, reciprocal_bits, address_bits)
            for amount_bits in AMOUNT_BITS
            for reciprocal_bits in RECIPROCAL_BITS
            for address_bits in ADDRESS_BITS
        ),
        key=lambda item: (
            item[2],
            max(item[0], item[1]),
            item[0] + item[1],
            item[0],
            item[1],
        ),
    )
    for amount_bits, reciprocal_bits, address_bits in ordering:
        row, composition_codes = normalization_design(
            gas_support,
            exact_composition,
            selected_pressure,
            amount_bits,
            reciprocal_bits,
            address_bits,
        )
        flux_codes, face_diagnostics = normalized_face_flux_codes(
            terms,
            selected_pressure,
            selected_face,
            composition_codes,
        )
        balance_selected, _ = select_balance_rows(terms, flux_codes, selected_face)
        row |= {
            "passes_propagated_face_precision_gate": face_diagnostics[
                "passes_propagated_face_precision_gate"
            ],
            "propagated_face_flux_p95_error_max": max(
                face_diagnostics[
                    "component_p95_flow_scale_normalized_error"
                ].values()
            ),
            "all_five_balance_precision_gates_pass": len(balance_selected)
            == len(COMPONENTS),
            "balance_next_p95_scale_error_max": (
                max(
                    selected[
                        "next_p95_scale_normalized_absolute_error"
                    ]
                    for selected in balance_selected
                )
                if balance_selected
                else None
            ),
            "passes_end_to_end_precision_gate": bool(
                row["passes_composition_precision_gate"]
                and face_diagnostics["passes_propagated_face_precision_gate"]
                and len(balance_selected) == len(COMPONENTS)
            ),
        }
        rows.append(row)
        if selected_summary is None and row["passes_end_to_end_precision_gate"]:
            selected_summary = row
            selected_balance = balance_selected
            selected_face_diagnostics = face_diagnostics
    if selected_summary is None or selected_face_diagnostics is None:
        raise AssertionError("no normalization candidate passes the end-to-end gate")
    selected, selected_codes = normalization_design(
        gas_support,
        exact_composition,
        selected_pressure,
        int(selected_summary["amount_bits"]),
        int(selected_summary["reciprocal_bits"]),
        int(selected_summary["address_bits"]),
        keep_circuit_constants=True,
    )
    selected_flux, selected_face_diagnostics = normalized_face_flux_codes(
        terms,
        selected_pressure,
        selected_face,
        selected_codes,
    )
    selected_balance, _ = select_balance_rows(terms, selected_flux, selected_face)
    selected |= {
        key: selected_summary[key]
        for key in (
            "passes_propagated_face_precision_gate",
            "propagated_face_flux_p95_error_max",
            "all_five_balance_precision_gates_pass",
            "balance_next_p95_scale_error_max",
            "passes_end_to_end_precision_gate",
        )
    }
    return rows, selected, selected_balance, selected_face_diagnostics


def build_composition_normalizer(
    selected: dict,
    selected_pressure: dict,
) -> tuple[QuantumCircuit, dict]:
    gas_bits = int(selected_pressure["gas_bits_per_component"])
    weights_by_component = [
        [int(value) for value in row]
        for row in selected["common_amount_weights_by_component"]
    ]
    total_weights = [value for row in weights_by_component for value in row]
    total_adder = WeightedAdder(len(total_weights), total_weights)
    component_adders = [
        WeightedAdder(gas_bits, row) for row in weights_by_component
    ]
    address_bits = int(selected["address_bits"])
    reciprocal_bits = int(selected["reciprocal_bits"])
    multiplier_bits = int(selected["multiplier_state_bits"])
    thresholds = [int(value) for value in selected["denominator_threshold_codes"]]
    table = [int(value) for value in selected["reciprocal_table"]]
    comparator = IntegerComparator(total_adder.num_sum_qubits, thresholds[0], geq=True)
    work_bits = max(
        total_adder.num_ancillas,
        max(adder.num_ancillas for adder in component_adders),
        comparator.num_ancillas,
        address_bits - 2,
        multiplier_bits - reciprocal_bits,
    )

    gas_reg = QuantumRegister(len(total_weights), "gas_components")
    composition_reg = QuantumRegister(
        len(COMPONENTS) * COMPOSITION_BITS, "composition"
    )
    total_reg = QuantumRegister(total_adder.num_sum_qubits, "total_amount")
    address_reg = QuantumRegister(address_bits, "reciprocal_address")
    flag_reg = QuantumRegister(1, "compare_flag")
    reciprocal_reg = QuantumRegister(reciprocal_bits, "reciprocal")
    component_reg = QuantumRegister(multiplier_bits, "component_amount")
    product_reg = QuantumRegister(2 * multiplier_bits, "amount_times_reciprocal")
    work_reg = QuantumRegister(work_bits, "work")
    circuit = QuantumCircuit(
        gas_reg,
        composition_reg,
        total_reg,
        address_reg,
        flag_reg,
        reciprocal_reg,
        component_reg,
        product_reg,
        work_reg,
        name="clean_gas_to_five_component_composition",
    )

    total_qargs = (
        list(gas_reg)
        + list(total_reg)
        + list(work_reg)[: total_adder.num_ancillas]
    )
    circuit.append(total_adder, total_qargs)
    append_address_extractor(
        circuit,
        list(total_reg),
        list(address_reg),
        flag_reg[0],
        list(work_reg),
        thresholds,
    )
    append_reciprocal_qrom(
        circuit,
        list(address_reg),
        list(reciprocal_reg),
        list(work_reg),
        table,
    )
    reciprocal_operand = list(reciprocal_reg) + list(work_reg)[
        : multiplier_bits - reciprocal_bits
    ]
    multiplier = MultiplierGate(multiplier_bits, 2 * multiplier_bits)
    shift = int(selected["reciprocal_shift_bits"])
    for component, adder in enumerate(component_adders):
        gas = list(gas_reg)[
            component * gas_bits : (component + 1) * gas_bits
        ]
        component_qargs = (
            gas
            + list(component_reg)[: adder.num_sum_qubits]
            + list(work_reg)[: adder.num_ancillas]
        )
        circuit.append(adder, component_qargs)
        multiply_qargs = (
            list(component_reg)
            + reciprocal_operand
            + list(product_reg)
        )
        circuit.append(multiplier, multiply_qargs)
        output = list(composition_reg)[
            component * COMPOSITION_BITS : (component + 1) * COMPOSITION_BITS
        ]
        product_window = list(product_reg)[shift : shift + COMPOSITION_BITS]
        if len(product_window) != COMPOSITION_BITS:
            raise AssertionError((shift, multiplier_bits))
        for source, target in zip(product_window, output):
            circuit.cx(source, target)
        circuit.append(multiplier.inverse(), multiply_qargs)
        circuit.append(adder.inverse(), component_qargs)
    append_reciprocal_qrom(
        circuit,
        list(address_reg),
        list(reciprocal_reg),
        list(work_reg),
        table,
        inverse=True,
    )
    append_address_extractor(
        circuit,
        list(total_reg),
        list(address_reg),
        flag_reg[0],
        list(work_reg),
        thresholds,
        inverse=True,
    )
    circuit.append(total_adder.inverse(), total_qargs)
    return circuit, {
        "retained_input": f"5 x {gas_bits}-bit component gas inventories",
        "clean_output": f"5 x {COMPOSITION_BITS}-bit normalized composition",
        "total_sum_bits": total_adder.num_sum_qubits,
        "address_bits": address_bits,
        "reciprocal_bits": reciprocal_bits,
        "multiplier_state_bits": multiplier_bits,
        "product_bits": 2 * multiplier_bits,
        "shared_work_bits": work_bits,
        "cleared": [
            "common-scale total amount",
            "support-adaptive reciprocal address",
            "comparator flag",
            "reciprocal QROM output",
            "per-component common amount",
            "multiplier product",
            "shared arithmetic workspace",
        ],
    }


def build_direct_composition(
    normalizer: QuantumCircuit,
    pressure_module: QuantumCircuit,
    face_module: QuantumCircuit,
    selected_rows: list[dict],
) -> tuple[QuantumCircuit, dict]:
    pressure_gas_bits = len(register_indices(pressure_module, "gas_components"))
    pressure_bits = len(register_indices(pressure_module, "pressure"))
    normalizer_gas_bits = len(register_indices(normalizer, "gas_components"))
    composition_bits_total = len(register_indices(normalizer, "composition"))
    face_composition_bits = len(register_indices(face_module, "composition_left"))
    face_flux_bits_total = len(register_indices(face_module, "component_flux"))
    if pressure_gas_bits != normalizer_gas_bits:
        raise AssertionError((pressure_gas_bits, normalizer_gas_bits))
    if composition_bits_total != face_composition_bits:
        raise AssertionError((composition_bits_total, face_composition_bits))
    face_bits = face_flux_bits_total // len(COMPONENTS)

    adders: list[tuple[WeightedAdder, WeightedAdder]] = []
    for row in selected_rows:
        positive_weights = (
            list(row["nonface_term_weights"]["current_gas"])
            + list(row["direct_face_flux_weights"])
            + list(row["nonface_term_weights"]["desorption"])
        )
        negative_weights = (
            list(row["direct_face_flux_weights"])
            + list(row["nonface_term_weights"]["adsorption"])
        )
        adders.append(
            (
                WeightedAdder(len(positive_weights), positive_weights),
                WeightedAdder(len(negative_weights), negative_weights),
            )
        )
    positive_sum_bits = max(pair[0].num_sum_qubits for pair in adders)
    negative_sum_bits = max(pair[1].num_sum_qubits for pair in adders)
    positive_work_bits = max(pair[0].num_ancillas for pair in adders)
    negative_work_bits = max(pair[1].num_ancillas for pair in adders)
    common_bits = max(
        positive_sum_bits,
        negative_sum_bits,
        max(int(row["next_output_bits"]) for row in selected_rows),
    )

    next_index = 0

    def allocate(size: int) -> list[int]:
        nonlocal next_index
        result = list(range(next_index, next_index + size))
        next_index += size
        return result

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
    component_layouts: list[dict[str, list[int]]] = []
    for row in selected_rows:
        bits = int(row["input_bits_per_nonface_term"])
        component_layouts.append(
            {
                name: allocate(bits)
                for name in ("current_gas", "desorption", "adsorption")
            }
            | {"next_gas": allocate(int(row["next_output_bits"]))}
        )
    positive_sum = allocate(positive_sum_bits)
    negative_sum = allocate(negative_sum_bits)
    positive_work = allocate(positive_work_bits)
    negative_work = allocate(negative_work_bits)
    negative_pad = allocate(common_bits)
    balance = allocate(common_bits)

    circuit = QuantumCircuit(
        next_index,
        name="clean_gas_normalized_pressure_two_face_five_component_balance",
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

    for component_index, (row, pair, layout) in enumerate(
        zip(selected_rows, adders, component_layouts)
    ):
        positive_adder, negative_adder = pair
        left_flux = face_flux[0][
            component_index * face_bits : (component_index + 1) * face_bits
        ]
        right_flux = face_flux[1][
            component_index * face_bits : (component_index + 1) * face_bits
        ]
        positive_state = layout["current_gas"] + left_flux + layout["desorption"]
        negative_state = right_flux + layout["adsorption"]
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
        circuit.append(positive_adder, positive_qargs)
        circuit.append(negative_adder, negative_qargs)
        for source, target in zip(
            positive_sum[: positive_adder.num_sum_qubits], balance
        ):
            circuit.cx(source, target)
        negative_operand = (
            negative_sum[: negative_adder.num_sum_qubits]
            + negative_pad[: common_bits - negative_adder.num_sum_qubits]
        )
        from qiskit.circuit.library import ModularAdderGate

        subtractor = ModularAdderGate(common_bits)
        circuit.append(subtractor.inverse(), negative_operand + balance)
        for source, target in zip(
            balance[: int(row["next_output_bits"])], layout["next_gas"]
        ):
            circuit.cx(source, target)
        circuit.append(subtractor, negative_operand + balance)
        for source, target in reversed(
            list(
                zip(
                    positive_sum[: positive_adder.num_sum_qubits],
                    balance,
                )
            )
        ):
            circuit.cx(source, target)
        circuit.append(negative_adder.inverse(), negative_qargs)
        circuit.append(positive_adder.inverse(), positive_qargs)

    for mapping in reversed(face_maps):
        circuit.compose(face_module.inverse(), qubits=mapping, inplace=True)
    for mapping in reversed(pressure_maps):
        circuit.compose(pressure_module.inverse(), qubits=mapping, inplace=True)
    for mapping in reversed(normalizer_maps):
        circuit.compose(normalizer.inverse(), qubits=mapping, inplace=True)

    retained_balance_inputs = [
        index
        for layout in component_layouts
        for name in ("current_gas", "desorption", "adsorption")
        for index in layout[name]
    ]
    next_outputs = [
        index for layout in component_layouts for index in layout["next_gas"]
    ]
    retained = sorted(
        set(
            [index for group in gas for index in group]
            + retained_balance_inputs
            + next_outputs
        )
    )
    temporary = sorted(
        set(
            [index for group in compositions + pressure_output + face_flux for index in group]
            + [index for group in normalizer_shared.values() for index in group]
            + [index for group in pressure_shared.values() for index in group]
            + [index for group in face_shared.values() for index in group]
        )
    )
    if set(retained) & set(temporary):
        raise AssertionError("workspace overlaps retained input/output")
    return circuit, {
        "three_cell_gas_inventory_inputs": gas,
        "temporary_two_normalized_compositions": compositions,
        "component_nonface_inputs": retained_balance_inputs,
        "next_gas_outputs": next_outputs,
        "temporary_pressure_outputs": pressure_output,
        "temporary_face_component_flux": face_flux,
        "retained_input_output_qubits": len(retained),
        "cleared_workspace_qubits": circuit.num_qubits - len(retained),
        "shared_arithmetic": {
            "normalizer_workspace_qubits": sum(
                len(group) for group in normalizer_shared.values()
            ),
            "pressure_workspace_qubits": sum(
                len(group) for group in pressure_shared.values()
            ),
            "face_workspace_qubits": sum(
                len(group) for group in face_shared.values()
            ),
            "positive_sum_bits": positive_sum_bits,
            "negative_sum_bits": negative_sum_bits,
            "positive_work_bits": positive_work_bits,
            "negative_work_bits": negative_work_bits,
            "common_balance_bits": common_bits,
        },
        "directly_composed_modules": [
            "two gas-inventory-to-five-component normalization circuits",
            "three gas-inventory-to-pressure weighted sums",
            "two reconstructed-pressure and generated-composition internal faces",
            "ten flow-times-composition multipliers",
            "five conservative interior-cell component balances",
            "exact reverse of both faces, all pressures, and both normalizers",
        ],
    }


def main() -> None:
    transport = json.loads(TRANSPORT_JSON.read_text(encoding="utf-8"))
    selected_pressure = transport["selected_pressure"]
    selected_face = transport["selected_face"]
    terms = interior_terms()
    rows, selected, selected_balance, face_diagnostics = screen_candidates(
        terms,
        selected_pressure,
        selected_face,
    )
    if len(selected_balance) != len(COMPONENTS):
        raise AssertionError("selected normalization lost a component balance")
    print(
        json.dumps(
            {
                "stage": "precision_selected",
                "amount_bits": selected["amount_bits"],
                "reciprocal_bits": selected["reciprocal_bits"],
                "address_bits": selected["address_bits"],
                "composition_p95_max": max(
                    selected["composition_p95_absolute_error"].values()
                ),
                "face_p95_max": selected["propagated_face_flux_p95_error_max"],
                "balance_p95_max": selected["balance_next_p95_scale_error_max"],
            }
        ),
        flush=True,
    )
    normalizer, normalizer_layout = build_composition_normalizer(
        selected, selected_pressure
    )
    pressure_module, pressure_layout = build_pressure_circuit(selected_pressure)
    face_module, face_layout = build_face_circuit(selected_face)
    direct, direct_layout = build_direct_composition(
        normalizer,
        pressure_module,
        face_module,
        selected_balance,
    )
    print(
        json.dumps(
            {
                "stage": "circuit_built",
                "normalizer_qubits": normalizer.num_qubits,
                "direct_logical_qubits": direct.num_qubits,
            }
        ),
        flush=True,
    )
    compiled = transpile(
        direct,
        basis_gates=["u", "cx"],
        optimization_level=1,
        seed_transpiler=TRANSPILER_SEED,
    )
    resources = resource_record(compiled)
    normalizer_compiled = transpile(
        normalizer,
        basis_gates=["u", "cx"],
        optimization_level=1,
        seed_transpiler=TRANSPILER_SEED,
    )
    normalizer_resources = resource_record(normalizer_compiled)

    payload = {
        "schema": "psa-qae-cce-primary-composition-normalized-internal-face-balance/v1",
        "status": "gas_inventory_normalization_pressure_two_internal_face_five_component_balance_directly_composed_ldf_phase_open",
        "qpu_submission": False,
        "physical_state_source": {
            "interior_cell_states": int(len(terms["next_gas"])),
            "normalization_cell_states": int(2 * len(terms["next_gas"])),
            "component_balances": int(len(terms["next_gas"]) * len(COMPONENTS)),
            "normalization_support": "left and centre upwind cells used by the two locally oriented faces of each audited interior-cell state",
        },
        "precision_gates": {
            "composition_p95_absolute_error_max": COMPOSITION_P95_ABSOLUTE_GATE,
            "composition_max_absolute_error_max": COMPOSITION_MAX_ABSOLUTE_GATE,
            "composition_sum_p95_absolute_error_max": COMPOSITION_SUM_P95_GATE,
            "composition_sum_max_absolute_error_max": COMPOSITION_SUM_MAX_GATE,
            "face_flux_p95_flow_scale_normalized_error_max": FACE_FLUX_P95_FLOW_SCALE_GATE,
            "next_p95_scale_normalized_absolute_error_max": P95_NEXT_SCALE_NORMALIZED_GATE,
            "next_max_scale_normalized_absolute_error_max": MAX_NEXT_SCALE_NORMALIZED_GATE,
            "arithmetic_only_p95_scale_normalized_absolute_error_max": P95_ARITHMETIC_ONLY_GATE,
            "arithmetic_only_max_scale_normalized_absolute_error_max": MAX_ARITHMETIC_ONLY_GATE,
            "erasure_and_overflow_fraction_required": 0.0,
        },
        "normalization_rows": rows,
        "selected_normalization": selected,
        "selected_balance_rows": selected_balance,
        "propagated_face_diagnostics": face_diagnostics,
        "selected_pressure": selected_pressure,
        "selected_face": selected_face,
        "normalizer_layout": normalizer_layout,
        "pressure_module_layout": pressure_layout,
        "face_module_layout": face_layout,
        "direct_composition_layout": direct_layout,
        "compiled_clean_composition_normalizer": normalizer_resources,
        "compiled_clean_normalized_internal_face_balance": resources,
        "accuracy_boundary": "the next-inventory error propagates component-specific gas quantization, common-scale amount conversion, support-adaptive reciprocal normalization, reconstructed pressure, pressure-difference flow, flow-times-generated-composition multiplication, face-to-balance conversion, and nonface-term quantization",
        "claim_boundary": {
            "supported": "all-to-all u/CX compilation of one clean circuit mapping three cells' encoded gas inventories through two cached-support composition normalizers, three pressure reconstructions, two locally oriented internal faces, and five centre-cell balances into five next-gas inventories, followed by exact work uncomputation",
            "unsupported": "out-of-support normalization guarantees, negative-flow upwind switching outside the cached local orientation, direct centre-cell LDF/loading composition, reversible run-specific parameters, boundary/tank withdrawal, adaptive integration, complete phase/cycle, routing, hardware feasibility, or quantum advantage",
        },
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    csv_rows = []
    for row in rows:
        csv_rows.append(
            {
                "row_type": "normalization_screen",
                "component": "ALL",
                "amount_bits": row["amount_bits"],
                "reciprocal_bits": row["reciprocal_bits"],
                "address_bits": row["address_bits"],
                "composition_p95_error": max(
                    row["composition_p95_absolute_error"].values()
                ),
                "composition_max_error": max(
                    row["composition_max_absolute_error"].values()
                ),
                "face_flux_p95_error": row[
                    "propagated_face_flux_p95_error_max"
                ],
                "next_p95_error": row["balance_next_p95_scale_error_max"],
                "passes": row["passes_end_to_end_precision_gate"],
            }
        )
    for row in selected_balance:
        csv_rows.append(
            {
                "row_type": "selected_balance",
                "component": row["component"],
                "amount_bits": selected["amount_bits"],
                "reciprocal_bits": selected["reciprocal_bits"],
                "address_bits": selected["address_bits"],
                "composition_p95_error": selected[
                    "composition_p95_absolute_error"
                ][row["component"]],
                "composition_max_error": selected[
                    "composition_max_absolute_error"
                ][row["component"]],
                "face_flux_p95_error": face_diagnostics[
                    "component_p95_flow_scale_normalized_error"
                ][row["component"]],
                "next_p95_error": row[
                    "next_p95_scale_normalized_absolute_error"
                ],
                "passes": row["passes_internal_face_balance_precision_gate"],
            }
        )
    with OUT_CSV.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(csv_rows[0]))
        writer.writeheader()
        writer.writerows(csv_rows)

    lines = [
        "# Direct gas-normalized internal-face cell balance",
        "",
        f"The frozen screen covers **{2 * len(terms['next_gas']):,} normalization states**, **{len(terms['next_gas']):,} interior-cell states**, and **{len(terms['next_gas']) * len(COMPONENTS):,} component balances**. No QPU job was submitted.",
        "",
        f"The first end-to-end passing design uses **{selected['amount_bits']}-bit common amounts**, **{selected['reciprocal_bits']}-bit reciprocals**, **{selected['address_bits']} address bits ({selected['reciprocal_segments']} support-adaptive segments)**, and five **{COMPOSITION_BITS}-bit** composition outputs. The largest component p95 absolute composition error is **{max(selected['composition_p95_absolute_error'].values()):.3e}** and the largest maximum error is **{max(selected['composition_max_absolute_error'].values()):.3e}**, with zero nonzero-value erasure and zero output overflow.",
        "",
        "| Component | composition p95 abs. | face-flux p95 / flow scale | next-gas p95 / next scale |",
        "|---|---:|---:|---:|",
    ]
    for row in selected_balance:
        component = row["component"]
        lines.append(
            f"| {component} | {selected['composition_p95_absolute_error'][component]:.3e} | {face_diagnostics['component_p95_flow_scale_normalized_error'][component]:.3e} | {row['next_p95_scale_normalized_absolute_error']:.3e} |"
        )
    lines += [
        "",
        f"The clean standalone normalizer uses **{normalizer_resources['logical_qubits']:,} logical qubits**, all-to-all depth **{normalizer_resources['depth_all_to_all']:,}**, and **{normalizer_resources['cx']:,} CX**. The clean direct normalized transport-balance circuit uses **{resources['logical_qubits']:,} logical qubits**, all-to-all depth **{resources['depth_all_to_all']:,}**, and **{resources['cx']:,} CX**. It retains **{direct_layout['retained_input_output_qubits']:,}** input/output qubits and clears **{direct_layout['cleared_workspace_qubits']:,}** work qubits.",
        "",
        "The circuit no longer accepts independently supplied upwind composition. Its reciprocal thresholds and table are calibrated to the frozen left/centre-cell support. Out-of-support normalization, direct centre-cell LDF/loading coupling, run-specific parameters, boundary/tank withdrawal, adaptive phase integration, routing, and a complete cycle remain open.",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": payload["status"],
                "selected_amount_bits": selected["amount_bits"],
                "selected_reciprocal_bits": selected["reciprocal_bits"],
                "selected_address_bits": selected["address_bits"],
                "normalizer_logical_qubits": normalizer_resources[
                    "logical_qubits"
                ],
                "normalizer_cx": normalizer_resources["cx"],
                "direct_logical_qubits": resources["logical_qubits"],
                "direct_depth": resources["depth_all_to_all"],
                "direct_cx": resources["cx"],
                "qpu_submission": False,
            },
            indent=2,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
