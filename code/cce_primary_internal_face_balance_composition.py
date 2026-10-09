"""Compose reconstructed pressure and two internal faces into cell balances.

The existing transport audit compiled pressure reconstruction and one
locally oriented internal-face component-flux circuit, while the interior
cell-balance audit accepted left/right transfers as independent registers.
This script closes both register interfaces for one interior finite-volume
cell.  It

1. reconstructs pressure from five gas inventories in the left, centre, and
   right cells;
2. computes the five component transfers on the left and right faces from
   those pressure registers and two supplied upwind-composition registers;
3. consumes the exact temporary face-flux registers in five conservative
   one-second centre-cell balances;
4. copies the five next-gas outputs; and
5. exactly reverses both face circuits and all three pressure circuits.

Composition normalization, loading/LDF generation for the centre cell,
run-specific parameter registers, boundary/tank logic, adaptive integration,
and a complete phase/cycle remain open.  No QPU work is submitted.
"""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit.circuit.library import ModularAdderGate, WeightedAdder

from cce_primary_internal_transport_reversible_microsteps import (
    CACHE,
    OUT_JSON as TRANSPORT_JSON,
    build_face_circuit,
    build_pressure_circuit,
)
from cce_primary_loading_sign_balance_interface import register_indices
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
ROOT = HERE.parents[1]
RESULTS = ROOT / "10_TEA_LCA_Python" / "results" / "pycharm_publication_enhancement"
SOURCE = HERE / "psa_two_bed_spatial_tank_n2_independent_source_uncertainty_32.csv"
OUT_JSON = RESULTS / "PSA_QAE_CCE_PRIMARY_INTERNAL_FACE_BALANCE_COMPOSITION.json"
OUT_CSV = RESULTS / "PSA_QAE_CCE_PRIMARY_INTERNAL_FACE_BALANCE_COMPOSITION.csv"
OUT_MD = RESULTS / "PSA_QAE_CCE_PRIMARY_INTERNAL_FACE_BALANCE_COMPOSITION.md"

INPUT_BITS = [16, 18, 20, 22]
OUTPUT_BITS = [20, 22, 24, 26]
NONFACE_TERMS = ("current_gas", "desorption", "adsorption")
POSITIVE_NONFACE_TERMS = ("current_gas", "desorption")
NEGATIVE_NONFACE_TERMS = ("adsorption",)

# The face module already has an independent flow/flux gate.  These inventory
# gates explicitly include its pressure/composition error after propagation
# into a next-cell amount, so they are separated from the tighter arithmetic-
# only gate evaluated with exact physical face fluxes encoded at the same tier.
P95_NEXT_SCALE_NORMALIZED_GATE = 2.0e-4
MAX_NEXT_SCALE_NORMALIZED_GATE = 5.0e-4
P95_ARITHMETIC_ONLY_GATE = 2.5e-5
MAX_ARITHMETIC_ONLY_GATE = 5.0e-5
BALANCE_SCALE_HEADROOM_FACTOR = 1.001
ROUND_OFF_ZERO_MOL = 1.0e-15
TRANSPILER_SEED = 20261009


def source_rows() -> dict[int, dict[str, str]]:
    with SOURCE.open(newline="", encoding="utf-8-sig") as handle:
        return {int(row["sample"]): row for row in csv.DictReader(handle)}


def interior_terms() -> dict[str, np.ndarray]:
    """Return three-cell inputs and centre-cell one-second balance terms."""

    cache = np.load(CACHE)
    samples = np.asarray(cache["samples"], dtype=int)
    boundaries = np.asarray(cache["boundaries"], dtype=float)
    if boundaries.shape != (32, 101, 85):
        raise AssertionError(boundaries.shape)
    rows = source_rows()
    records: list[dict[str, np.ndarray]] = []
    for run_index, sample in enumerate(samples):
        row = rows[int(sample)]
        params = SpatialParams(
            n_cells=4,
            P_high_bar=15.65,
            P_low_bar=float(row["P_low_bar"]),
            phase_duration_s=10.0,
            k_in_mol_s_bar=1.0,
            k_out_mol_s_bar=1.0,
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
                face_flow = params.k_internal_mol_s_bar * (
                    pressure[:-1] - pressure[1:]
                )
                if np.any(face_flow < -1.0e-15):
                    raise AssertionError("cached local face orientation changed")
                face_flux = np.asarray(
                    [
                        face_flow[face]
                        * (
                            composition[:, face]
                            if face_flow[face] >= 0.0
                            else composition[:, face + 1]
                        )
                        for face in range(3)
                    ],
                    dtype=float,
                ).T
                for cell in (1, 2):
                    solid_transfer = solid[cell] * (
                        loading_next[:, cell] - loading[:, cell]
                    )
                    solid_transfer[
                        np.abs(solid_transfer) < ROUND_OFF_ZERO_MOL
                    ] = 0.0
                    records.append(
                        {
                            "gas_triplet": gas[:, cell - 1 : cell + 2].T,
                            "pressure_triplet": pressure[cell - 1 : cell + 2],
                            "composition_pair": composition[:, cell - 1 : cell + 1].T,
                            "current_gas": gas[:, cell],
                            "left_influx": face_flux[:, cell - 1],
                            "right_outflux": face_flux[:, cell],
                            "desorption": np.maximum(-solid_transfer, 0.0),
                            "adsorption": np.maximum(solid_transfer, 0.0),
                        }
                    )
    result = {
        key: np.asarray([record[key] for record in records], dtype=float)
        for key in records[0]
    }
    result["next_gas"] = (
        result["current_gas"]
        + result["left_influx"]
        + result["desorption"]
        - result["right_outflux"]
        - result["adsorption"]
    )
    if np.any(result["next_gas"] <= 0.0):
        raise AssertionError("interior one-second balance underflows")
    return result


def weighted_code(codes: np.ndarray, weights: list[int]) -> np.ndarray:
    output = np.zeros(len(codes), dtype=np.int64)
    for bit, weight in enumerate(weights):
        output += ((codes >> bit) & 1) * int(weight)
    return output


def encode_values(
    values: np.ndarray,
    scale: float,
    input_bits: int,
    output_bits: int,
    balance_scale: float,
) -> tuple[np.ndarray, list[int], np.ndarray]:
    input_levels = (1 << input_bits) - 1
    output_levels = (1 << output_bits) - 1
    if scale <= 0.0:
        zeros = np.zeros(len(values), dtype=np.int64)
        return zeros, [0] * input_bits, zeros
    codes = np.rint(values / scale * input_levels).astype(np.int64)
    weights = [
        int(
            round(
                scale
                / input_levels
                * (1 << bit)
                / balance_scale
                * output_levels
            )
        )
        for bit in range(input_bits)
    ]
    return weighted_code(codes, weights), weights, codes


def pressure_codes(
    gas: np.ndarray,
    selected_pressure: dict,
) -> np.ndarray:
    """Return exact circuit pressure codes for an (N, cells, components) array."""

    gas_bits = int(selected_pressure["gas_bits_per_component"])
    levels = (1 << gas_bits) - 1
    scales = np.asarray(selected_pressure["gas_component_scales_mol"], dtype=float)
    weights = [int(value) for value in selected_pressure["pressure_weights"]]
    codes = np.rint(gas / scales[None, None, :] * levels).astype(np.int64)
    output = np.zeros(gas.shape[:2], dtype=np.int64)
    for component in range(len(COMPONENTS)):
        for bit in range(gas_bits):
            output += ((codes[:, :, component] >> bit) & 1) * weights[
                component * gas_bits + bit
            ]
    return output


def face_flux_codes(
    terms: dict[str, np.ndarray],
    selected_pressure: dict,
    selected_face: dict,
) -> tuple[np.ndarray, dict]:
    """Return circuit-exact left/right face component-flux codes."""

    pressures = pressure_codes(terms["gas_triplet"], selected_pressure)
    differences = pressures[:, :-1] - pressures[:, 1:]
    if np.any(differences < 0):
        raise AssertionError("reconstructed pressure difference underflow")
    flow_weights = [int(value) for value in selected_face["flow_weights"]]
    flow_codes = np.zeros_like(differences)
    for bit, weight in enumerate(flow_weights):
        flow_codes += ((differences >> bit) & 1) * weight
    composition_bits = int(selected_face["composition_bits_per_component"])
    composition_levels = (1 << composition_bits) - 1
    composition_codes = np.rint(
        terms["composition_pair"] * composition_levels
    ).astype(np.int64)
    flux_codes = (
        flow_codes[:, :, None] * composition_codes
    ) >> composition_bits
    flow_levels = (1 << int(selected_face["flow_effective_bits"])) - 1
    flow_scale = float(selected_face["flow_scale_mol_s"])
    approx = flux_codes / flow_levels * flow_scale
    exact = np.stack(
        [terms["left_influx"], terms["right_outflux"]], axis=1
    )
    normalized = np.abs(approx - exact) / flow_scale
    return flux_codes, {
        "maximum_flux_code": int(np.max(flux_codes)),
        "flow_effective_levels": int(flow_levels),
        "pressure_difference_underflow_fraction": float(np.mean(differences < 0)),
        "nonzero_face_flux_erased_fraction": float(
            np.mean((exact > 0.0) & (flux_codes == 0))
        ),
        "component_p95_flow_scale_normalized_error": {
            component: float(np.quantile(normalized[:, :, index], 0.95))
            for index, component in enumerate(COMPONENTS)
        },
        "component_max_flow_scale_normalized_error": {
            component: float(np.max(normalized[:, :, index]))
            for index, component in enumerate(COMPONENTS)
        },
    }


def direct_face_weights(
    face_bits: int,
    selected_face: dict,
    output_bits: int,
    balance_scale: float,
) -> list[int]:
    flow_levels = (1 << int(selected_face["flow_effective_bits"])) - 1
    output_levels = (1 << output_bits) - 1
    one_code_mol = float(selected_face["flow_scale_mol_s"]) / flow_levels
    return [
        int(round((1 << bit) * one_code_mol / balance_scale * output_levels))
        for bit in range(face_bits)
    ]


def precision_row(
    component_index: int,
    input_bits: int,
    output_bits: int,
    terms: dict[str, np.ndarray],
    flux_codes: np.ndarray,
    selected_face: dict,
) -> dict:
    component = COMPONENTS[component_index]
    values = {
        name: terms[name][:, component_index] for name in NONFACE_TERMS
    }
    left_exact = terms["left_influx"][:, component_index]
    right_exact = terms["right_outflux"][:, component_index]
    exact_next = terms["next_gas"][:, component_index]
    exact_positive_scale = float(
        np.max(values["current_gas"] + left_exact + values["desorption"])
    )
    balance_scale = exact_positive_scale * BALANCE_SCALE_HEADROOM_FACTOR
    nonface_scales = {name: float(np.max(value)) for name, value in values.items()}
    encoded = {
        name: encode_values(
            value,
            nonface_scales[name],
            input_bits,
            output_bits,
            balance_scale,
        )
        for name, value in values.items()
    }
    face_bits = int(selected_face["flow_register_bits"])
    face_weights = direct_face_weights(
        face_bits, selected_face, output_bits, balance_scale
    )
    left_code = weighted_code(flux_codes[:, 0, component_index], face_weights)
    right_code = weighted_code(flux_codes[:, 1, component_index], face_weights)
    positive = (
        encoded["current_gas"][0]
        + left_code
        + encoded["desorption"][0]
    )
    negative = right_code + encoded["adsorption"][0]
    next_code = positive - negative
    output_levels = (1 << output_bits) - 1
    next_approx = next_code / output_levels * balance_scale
    next_scale = float(np.max(exact_next))
    normalized_error = np.abs(next_approx - exact_next) / next_scale

    flow_levels = (1 << int(selected_face["flow_effective_bits"])) - 1
    flow_scale = float(selected_face["flow_scale_mol_s"])
    exact_left_code = np.rint(left_exact / flow_scale * flow_levels).astype(np.int64)
    exact_right_code = np.rint(right_exact / flow_scale * flow_levels).astype(np.int64)
    arithmetic_positive = (
        encoded["current_gas"][0]
        + weighted_code(exact_left_code, face_weights)
        + encoded["desorption"][0]
    )
    arithmetic_negative = (
        weighted_code(exact_right_code, face_weights)
        + encoded["adsorption"][0]
    )
    arithmetic_next = arithmetic_positive - arithmetic_negative
    arithmetic_approx = arithmetic_next / output_levels * balance_scale
    arithmetic_error = np.abs(arithmetic_approx - exact_next) / next_scale

    nonzero_erased = max(
        float(np.mean((values[name] > 0.0) & (encoded[name][2] == 0)))
        for name in NONFACE_TERMS
    )
    result = {
        "component": component,
        "component_index": component_index,
        "input_bits_per_nonface_term": input_bits,
        "face_flux_input_bits": face_bits,
        "next_output_bits": output_bits,
        "nonface_term_scales_mol": nonface_scales,
        "balance_scale_mol": balance_scale,
        "exact_positive_sum_scale_mol": exact_positive_scale,
        "balance_scale_headroom_factor": BALANCE_SCALE_HEADROOM_FACTOR,
        "next_gas_scale_mol": next_scale,
        "nonface_term_weights": {
            name: encoded[name][1] for name in NONFACE_TERMS
        },
        "direct_face_flux_weights": face_weights,
        "next_p95_scale_normalized_absolute_error": float(
            np.quantile(normalized_error, 0.95)
        ),
        "next_max_scale_normalized_absolute_error": float(np.max(normalized_error)),
        "arithmetic_only_p95_scale_normalized_absolute_error": float(
            np.quantile(arithmetic_error, 0.95)
        ),
        "arithmetic_only_max_scale_normalized_absolute_error": float(
            np.max(arithmetic_error)
        ),
        "maximum_nonzero_nonface_term_erased_fraction": nonzero_erased,
        "nonzero_direct_face_flux_erased_fraction": float(
            np.mean(
                (
                    np.stack([left_exact, right_exact], axis=1) > 0.0
                )
                & (flux_codes[:, :, component_index] == 0)
            )
        ),
        "positive_sum_overflow_fraction": float(np.mean(positive > output_levels)),
        "negative_sum_underflow_fraction": float(np.mean(negative > positive)),
        "next_output_overflow_fraction": float(np.mean(next_code > output_levels)),
        "minimum_exact_next_gas_mol": float(np.min(exact_next)),
    }
    result["passes_internal_face_balance_precision_gate"] = bool(
        result["next_p95_scale_normalized_absolute_error"]
        <= P95_NEXT_SCALE_NORMALIZED_GATE
        and result["next_max_scale_normalized_absolute_error"]
        <= MAX_NEXT_SCALE_NORMALIZED_GATE
        and result["arithmetic_only_p95_scale_normalized_absolute_error"]
        <= P95_ARITHMETIC_ONLY_GATE
        and result["arithmetic_only_max_scale_normalized_absolute_error"]
        <= MAX_ARITHMETIC_ONLY_GATE
        and result["maximum_nonzero_nonface_term_erased_fraction"] == 0.0
        and result["nonzero_direct_face_flux_erased_fraction"] == 0.0
        and result["positive_sum_overflow_fraction"] == 0.0
        and result["negative_sum_underflow_fraction"] == 0.0
        and result["next_output_overflow_fraction"] == 0.0
        and result["minimum_exact_next_gas_mol"] > 0.0
    )
    return result


def module_register_map(
    module: QuantumCircuit,
    named: dict[str, list[int]],
    shared: dict[str, list[int]],
) -> list[int]:
    result: list[int] = []
    for register in module.qregs:
        indices = named.get(register.name, shared.get(register.name))
        if indices is None or len(indices) != len(register):
            raise AssertionError((register.name, len(register), indices))
        result.extend(indices)
    if len(result) != module.num_qubits:
        raise AssertionError((len(result), module.num_qubits))
    return result


def build_direct_composition(
    pressure_module: QuantumCircuit,
    face_module: QuantumCircuit,
    selected_rows: list[dict],
) -> tuple[QuantumCircuit, dict]:
    """Compute 3 pressures and 2 faces, balance, then reverse all transport."""

    pressure_gas_bits = len(register_indices(pressure_module, "gas_components"))
    pressure_bits = len(register_indices(pressure_module, "pressure"))
    composition_bits = len(register_indices(face_module, "composition_left"))
    face_flux_bits_total = len(register_indices(face_module, "component_flux"))
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
        output = list(range(next_index, next_index + size))
        next_index += size
        return output

    pressure_gas = [allocate(pressure_gas_bits) for _ in range(3)]
    pressure_output = [allocate(pressure_bits) for _ in range(3)]
    pressure_shared = {
        register.name: allocate(len(register))
        for register in pressure_module.qregs
        if register.name not in {"gas_components", "pressure"}
    }
    compositions = [allocate(composition_bits) for _ in range(2)]
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
                name: allocate(bits) for name in NONFACE_TERMS
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
        name="clean_pressure_two_face_five_component_interior_balance",
    )
    pressure_maps = [
        module_register_map(
            pressure_module,
            {"gas_components": pressure_gas[cell], "pressure": pressure_output[cell]},
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
        positive_state = (
            layout["current_gas"] + left_flux + layout["desorption"]
        )
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

    retained_transport_inputs = [
        index for group in pressure_gas + compositions for index in group
    ]
    retained_balance_inputs = [
        index
        for layout in component_layouts
        for name in NONFACE_TERMS
        for index in layout[name]
    ]
    next_outputs = [
        index for layout in component_layouts for index in layout["next_gas"]
    ]
    retained = sorted(
        set(retained_transport_inputs + retained_balance_inputs + next_outputs)
    )
    temporary = sorted(
        set(
            [index for group in pressure_output + face_flux for index in group]
            + [index for group in pressure_shared.values() for index in group]
            + [index for group in face_shared.values() for index in group]
        )
    )
    if set(retained) & set(temporary):
        raise AssertionError("transport workspace overlaps retained I/O")
    return circuit, {
        "three_cell_gas_inventory_inputs": pressure_gas,
        "two_upwind_composition_inputs": compositions,
        "component_nonface_inputs": retained_balance_inputs,
        "next_gas_outputs": next_outputs,
        "temporary_pressure_outputs": pressure_output,
        "temporary_face_component_flux": face_flux,
        "retained_input_output_qubits": len(retained),
        "cleared_workspace_qubits": circuit.num_qubits - len(retained),
        "shared_arithmetic": {
            "pressure_workspace_qubits": sum(
                len(group) for group in pressure_shared.values()
            ),
            "face_workspace_qubits": sum(len(group) for group in face_shared.values()),
            "positive_sum_bits": positive_sum_bits,
            "negative_sum_bits": negative_sum_bits,
            "positive_work_bits": positive_work_bits,
            "negative_work_bits": negative_work_bits,
            "common_balance_bits": common_bits,
        },
        "directly_composed_modules": [
            "three gas-inventory-to-pressure weighted sums",
            "two reconstructed-pressure-driven oriented internal faces",
            "ten flow-times-composition multipliers",
            "five conservative interior-cell component balances",
            "exact reverse of both faces and all three pressure circuits",
        ],
    }


def resource_record(compiled: QuantumCircuit) -> dict:
    counts = compiled.count_ops()
    return {
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
    transport = json.loads(TRANSPORT_JSON.read_text(encoding="utf-8"))
    selected_pressure = transport["selected_pressure"]
    selected_face = transport["selected_face"]
    if not selected_pressure["passes_pressure_precision_gate"]:
        raise AssertionError("selected pressure tier no longer passes")
    if not selected_face["passes_oriented_face_precision_gate"]:
        raise AssertionError("selected face tier no longer passes")

    terms = interior_terms()
    flux_codes, face_diagnostics = face_flux_codes(
        terms, selected_pressure, selected_face
    )
    components: list[dict] = []
    selected_rows: list[dict] = []
    flat_rows: list[dict] = []
    for component_index, component in enumerate(COMPONENTS):
        rows = [
            precision_row(
                component_index,
                input_bits,
                output_bits,
                terms,
                flux_codes,
                selected_face,
            )
            for input_bits in INPUT_BITS
            for output_bits in OUTPUT_BITS
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
            raise AssertionError((component, rows))
        components.append(
            {
                "component": component,
                "component_index": component_index,
                "selected": selected,
                "precision_rows": rows,
            }
        )
        selected_rows.append(selected)
        flat_rows.append(
            {
                "component": component,
                "input_bits": selected["input_bits_per_nonface_term"],
                "face_flux_bits": selected["face_flux_input_bits"],
                "next_bits": selected["next_output_bits"],
                "next_p95_scale_error": selected[
                    "next_p95_scale_normalized_absolute_error"
                ],
                "next_max_scale_error": selected[
                    "next_max_scale_normalized_absolute_error"
                ],
                "arithmetic_only_p95": selected[
                    "arithmetic_only_p95_scale_normalized_absolute_error"
                ],
                "minimum_next_gas_mol": selected["minimum_exact_next_gas_mol"],
                "passes": selected["passes_internal_face_balance_precision_gate"],
            }
        )
        print(json.dumps(flat_rows[-1]), flush=True)

    pressure_module, pressure_layout = build_pressure_circuit(selected_pressure)
    face_module, face_layout = build_face_circuit(selected_face)
    direct, direct_layout = build_direct_composition(
        pressure_module, face_module, selected_rows
    )
    print(
        json.dumps(
            {
                "module": direct.name,
                "logical_qubits_before_transpile": direct.num_qubits,
                "stage": "transpiling_all_to_all_u_cx",
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

    payload = {
        "schema": "psa-qae-cce-primary-internal-face-balance-composition/v1",
        "status": "three_pressure_two_internal_face_five_component_balance_directly_composed_normalization_ldf_phase_open",
        "qpu_submission": False,
        "physical_state_source": {
            "runs": 32,
            "cycle_boundaries_per_run": 101,
            "beds": 2,
            "interior_cells_per_bed": 2,
            "interior_cell_states": int(len(terms["next_gas"])),
            "component_balances": int(len(terms["next_gas"]) * len(COMPONENTS)),
            "pressure_range_bar": [
                float(np.min(terms["pressure_triplet"])),
                float(np.max(terms["pressure_triplet"])),
            ],
        },
        "precision_gate": {
            "p95_next_scale_normalized_absolute_error_max": P95_NEXT_SCALE_NORMALIZED_GATE,
            "max_next_scale_normalized_absolute_error_max": MAX_NEXT_SCALE_NORMALIZED_GATE,
            "arithmetic_only_p95_scale_normalized_absolute_error_max": P95_ARITHMETIC_ONLY_GATE,
            "arithmetic_only_max_scale_normalized_absolute_error_max": MAX_ARITHMETIC_ONLY_GATE,
            "nonzero_term_erasure_required": 0.0,
            "positive_sum_overflow_required": 0.0,
            "negative_sum_underflow_required": 0.0,
            "next_output_overflow_required": 0.0,
            "balance_scale_headroom_factor": BALANCE_SCALE_HEADROOM_FACTOR,
        },
        "selected_pressure": selected_pressure,
        "selected_face": selected_face,
        "face_diagnostics_on_interior_cell_pairs": face_diagnostics,
        "components": components,
        "pressure_module_layout": pressure_layout,
        "face_module_layout": face_layout,
        "direct_composition_layout": direct_layout,
        "compiled_clean_internal_face_balance": resources,
        "accuracy_boundary": "the direct next-inventory error includes gas-to-pressure, pressure-difference, flow, supplied-composition multiplication, face-to-balance conversion, and nonface-term quantization; a separate arithmetic-only metric encodes exact physical face flux at the same output tier",
        "claim_boundary": {
            "supported": "all-to-all u/CX compilation of one clean circuit mapping three cells' encoded gas inventories and two supplied upwind compositions through three pressure reconstructions and two locally oriented internal faces into five centre-cell next-gas inventories, followed by exact transport-work uncomputation",
            "unsupported": "reversible composition normalization from gas inventories, negative-flow upwind switching outside the cached local orientation, direct centre-cell LDF/loading composition, reversible run-specific parameters, boundary/tank withdrawal, adaptive integration, complete phase/cycle, routing, hardware feasibility, or quantum advantage",
        },
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    with OUT_CSV.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(flat_rows[0]))
        writer.writeheader()
        writer.writerows(flat_rows)
    lines = [
        "# Direct pressure-to-two-face-to-interior-cell composition",
        "",
        f"The frozen precision screen covers **{len(terms['next_gas']):,} interior-cell states** and **{len(terms['next_gas']) * len(COMPONENTS):,} component balances**. No QPU job was submitted.",
        "",
        "| Component | non-face input bits | face-flux bits | next bits | propagated p95 / next scale | propagated max / next scale | arithmetic-only p95 |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in flat_rows:
        lines.append(
            f"| {row['component']} | {row['input_bits']} | {row['face_flux_bits']} | {row['next_bits']} | {row['next_p95_scale_error']:.3e} | {row['next_max_scale_error']:.3e} | {row['arithmetic_only_p95']:.3e} |"
        )
    lines += [
        "",
        f"The clean direct circuit uses **{resources['logical_qubits']:,} logical qubits**, all-to-all depth **{resources['depth_all_to_all']:,}**, and **{resources['cx']:,} CX** in the `u/CX` basis. It retains **{direct_layout['retained_input_output_qubits']:,}** input/output qubits and clears **{direct_layout['cleared_workspace_qubits']:,}** work qubits.",
        "",
        "The circuit computes three pressures and both five-component internal-face transfers, consumes those exact temporary flux registers in the centre-cell balances, copies five next-gas inventories, and reverses all pressure/face work. Composition normalization, direct centre-cell LDF/loading coupling, run-specific parameters, boundary/tank withdrawal, adaptive phase integration, routing, and a complete cycle remain open.",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": payload["status"],
                "interior_cell_states": payload["physical_state_source"][
                    "interior_cell_states"
                ],
                "component_balances": payload["physical_state_source"][
                    "component_balances"
                ],
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
