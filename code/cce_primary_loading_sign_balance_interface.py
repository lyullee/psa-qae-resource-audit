"""Compile loading-sign extraction directly into interior-cell gas balance.

The earlier cell-balance circuits accepted nonnegative adsorption and
desorption terms as independent inputs.  This audit starts instead from
current and next adsorbed-loading registers, reversibly extracts the sign and
magnitude of their difference, converts the loading change to a gas amount
with the fixed cell solid mass, feeds those terms into the clean interior-cell
balance, and uncomputes the sign/conversion workspace.

The upstream competitive-Langmuir/LDF and face-transport circuits remain
separate.  In particular, the precision screen may require wider current/next
loading registers than the previously compiled standalone LDF microsteps.
No QPU work is submitted.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
from qiskit import QuantumCircuit, QuantumRegister, transpile
from qiskit.circuit.library import ModularAdderGate, WeightedAdder
from qiskit.quantum_info import Statevector

from cce_primary_cell_balance_reversible_microsteps import (
    CACHE,
    NEGATIVE_TERM_INDICES,
    POSITIVE_TERM_INDICES,
    RESULTS,
    ROUND_OFF_ZERO_MOL,
    TERM_NAMES,
    build_clean_balance,
    encoded_term,
    physical_balance_terms,
    source_rows,
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
LDF_JSON = RESULTS / "PSA_QAE_CCE_PRIMARY_ALL_COMPONENT_LDF_MICROSTEPS.json"
CELL_JSON = RESULTS / "PSA_QAE_CCE_PRIMARY_CELL_BALANCE_MICROSTEPS.json"
OUT_JSON = RESULTS / "PSA_QAE_CCE_PRIMARY_LOADING_SIGN_BALANCE_INTERFACE.json"
OUT_CSV = RESULTS / "PSA_QAE_CCE_PRIMARY_LOADING_SIGN_BALANCE_INTERFACE.csv"
OUT_MD = RESULTS / "PSA_QAE_CCE_PRIMARY_LOADING_SIGN_BALANCE_INTERFACE.md"

LOADING_BITS = list(range(20, 43, 2))
P95_NEXT_SCALE_NORMALIZED_GATE = 2.5e-5
MAX_NEXT_SCALE_NORMALIZED_GATE = 5.0e-5
TRANSPILER_SEED = 20261009


def physical_loading_pairs() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return interior-cell q_current, q_next, and solid mass in balance order."""
    cache = np.load(CACHE)
    samples = np.asarray(cache["samples"], dtype=int)
    boundaries = np.asarray(cache["boundaries"], dtype=float)
    if boundaries.shape != (32, 101, 85):
        raise AssertionError(boundaries.shape)
    rows = source_rows()
    current: list[np.ndarray] = []
    following: list[np.ndarray] = []
    solid_mass: list[float] = []
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
                next_loading = loading + params.ldf_factor * kinetic * (
                    qstar(pressure, composition, params) - loading
                )
                for cell in (1, 2):
                    current.append(loading[:, cell])
                    following.append(next_loading[:, cell])
                    solid_mass.append(float(solid[cell]))
    current_array = np.asarray(current, dtype=float)
    next_array = np.asarray(following, dtype=float)
    solid_array = np.asarray(solid_mass, dtype=float)
    if float(np.ptp(solid_array)) > 1.0e-12:
        raise AssertionError("cell solid mass is not constant on the frozen support")
    return current_array, next_array, solid_array


def weighted_code(values: np.ndarray, weights: list[int]) -> np.ndarray:
    output = np.zeros(len(values), dtype=np.int64)
    for bit, weight in enumerate(weights):
        output += ((values >> bit) & 1) * int(weight)
    return output


def conversion_weights(
    loading_bits: int,
    loading_scale: float,
    solid_mass: float,
    term_bits: int,
    term_scale: float,
) -> list[int]:
    if term_scale <= 0.0:
        return [0] * loading_bits
    loading_levels = (1 << loading_bits) - 1
    term_levels = (1 << term_bits) - 1
    one_code_mol = solid_mass * loading_scale / loading_levels
    return [
        int(round((1 << bit) * one_code_mol / term_scale * term_levels))
        for bit in range(loading_bits)
    ]


def precision_row(
    component_index: int,
    loading_bits: int,
    loading_scale: float,
    current_loading: np.ndarray,
    next_loading: np.ndarray,
    solid_mass: np.ndarray,
    terms: dict[str, np.ndarray],
    cell_selected: dict,
) -> dict:
    component = COMPONENTS[component_index]
    term_bits = int(cell_selected["input_bits_per_term"])
    next_bits = int(cell_selected["next_output_bits"])
    term_levels = (1 << term_bits) - 1
    next_levels = (1 << next_bits) - 1
    loading_levels = (1 << loading_bits) - 1

    exact_change = (
        next_loading[:, component_index] - current_loading[:, component_index]
    ) * solid_mass
    exact_change[np.abs(exact_change) < ROUND_OFF_ZERO_MOL] = 0.0
    cleaned_next = next_loading[:, component_index].copy()
    cleaned_next[exact_change == 0.0] = current_loading[:, component_index][
        exact_change == 0.0
    ]
    current_code = np.rint(
        current_loading[:, component_index] / loading_scale * loading_levels
    ).astype(np.int64)
    next_code = np.rint(cleaned_next / loading_scale * loading_levels).astype(
        np.int64
    )
    signed_change_code = next_code - current_code
    adsorption_magnitude = np.maximum(signed_change_code, 0)
    desorption_magnitude = np.maximum(-signed_change_code, 0)

    solid_value = float(solid_mass[0])
    adsorption_weights = conversion_weights(
        loading_bits,
        loading_scale,
        solid_value,
        term_bits,
        float(cell_selected["term_scales_mol"]["adsorption"]),
    )
    desorption_weights = conversion_weights(
        loading_bits,
        loading_scale,
        solid_value,
        term_bits,
        float(cell_selected["term_scales_mol"]["desorption"]),
    )
    adsorption_code = weighted_code(adsorption_magnitude, adsorption_weights)
    desorption_code = weighted_code(desorption_magnitude, desorption_weights)

    balance_scale = float(cell_selected["balance_scale_mol"])
    output_codes: list[np.ndarray] = []
    for term_name in TERM_NAMES[:3]:
        code, _ = encoded_term(
            terms[term_name][:, component_index],
            float(cell_selected["term_scales_mol"][term_name]),
            term_bits,
            next_bits,
            balance_scale,
        )
        output_codes.append(code)
    output_codes.append(
        weighted_code(
            desorption_code,
            [int(value) for value in cell_selected["term_weights"]["desorption"]],
        )
    )
    output_codes.append(
        weighted_code(
            adsorption_code,
            [int(value) for value in cell_selected["term_weights"]["adsorption"]],
        )
    )
    positive = sum(output_codes[index] for index in POSITIVE_TERM_INDICES)
    negative = sum(output_codes[index] for index in NEGATIVE_TERM_INDICES)
    next_code_balance = positive - negative
    next_approx = next_code_balance / next_levels * balance_scale
    exact_next = terms["next_gas"][:, component_index]
    next_scale = float(cell_selected["next_gas_scale_mol"])
    normalized_error = np.abs(next_approx - exact_next) / next_scale

    nonzero = exact_change != 0.0
    branch_mismatch = np.sign(signed_change_code) != np.sign(exact_change)
    result = {
        "component": component,
        "component_index": component_index,
        "loading_bits": loading_bits,
        "loading_scale_mol_per_kg": loading_scale,
        "cell_solid_mass_kg": solid_value,
        "cell_balance_term_bits": term_bits,
        "cell_balance_next_bits": next_bits,
        "adsorption_conversion_weights": adsorption_weights,
        "desorption_conversion_weights": desorption_weights,
        "signed_change_code_min": int(np.min(signed_change_code)),
        "signed_change_code_max": int(np.max(signed_change_code)),
        "branch_mismatch_fraction": float(np.mean(branch_mismatch)),
        "nonzero_change_erased_fraction": float(
            np.mean(nonzero & (signed_change_code == 0))
        ),
        "zero_change_false_activation_fraction": float(
            np.mean((~nonzero) & (signed_change_code != 0))
        ),
        "adsorption_term_overflow_fraction": float(
            np.mean(adsorption_code > term_levels)
        ),
        "desorption_term_overflow_fraction": float(
            np.mean(desorption_code > term_levels)
        ),
        "negative_sum_underflow_fraction": float(np.mean(negative > positive)),
        "next_output_overflow_fraction": float(
            np.mean(next_code_balance > next_levels)
        ),
        "next_p95_scale_normalized_absolute_error": float(
            np.quantile(normalized_error, 0.95)
        ),
        "next_max_scale_normalized_absolute_error": float(
            np.max(normalized_error)
        ),
    }
    result["passes_loading_sign_balance_interface_gate"] = bool(
        result["branch_mismatch_fraction"] == 0.0
        and result["nonzero_change_erased_fraction"] == 0.0
        and result["zero_change_false_activation_fraction"] == 0.0
        and result["adsorption_term_overflow_fraction"] == 0.0
        and result["desorption_term_overflow_fraction"] == 0.0
        and result["negative_sum_underflow_fraction"] == 0.0
        and result["next_output_overflow_fraction"] == 0.0
        and result["next_p95_scale_normalized_absolute_error"]
        <= P95_NEXT_SCALE_NORMALIZED_GATE
        and result["next_max_scale_normalized_absolute_error"]
        <= MAX_NEXT_SCALE_NORMALIZED_GATE
    )
    return result


def register_indices(circuit: QuantumCircuit, name: str) -> list[int]:
    register = next(reg for reg in circuit.qregs if reg.name == name)
    return [circuit.find_bit(qubit).index for qubit in register]


def build_sign_split_compute(loading_bits: int) -> tuple[QuantumCircuit, dict]:
    current = QuantumRegister(loading_bits, "q_current")
    following = QuantumRegister(loading_bits, "q_next")
    pad = QuantumRegister(1, "operand_pad")
    difference = QuantumRegister(loading_bits + 1, "signed_difference")
    release_flag = QuantumRegister(1, "release_flag")
    adsorption = QuantumRegister(loading_bits, "adsorption_magnitude")
    desorption = QuantumRegister(loading_bits, "desorption_magnitude")
    circuit = QuantumCircuit(
        current,
        following,
        pad,
        difference,
        release_flag,
        adsorption,
        desorption,
        name=f"loading_sign_split_{loading_bits}bit",
    )
    subtractor = ModularAdderGate(loading_bits + 1)

    # q_next - q_current in a width-(b+1) two's-complement register.
    for source, target in zip(following, difference):
        circuit.cx(source, target)
    circuit.append(
        subtractor.inverse(),
        list(current) + list(pad) + list(difference),
    )
    circuit.cx(difference[loading_bits], release_flag[0])
    circuit.x(release_flag[0])
    for source, target in zip(difference[:loading_bits], adsorption):
        circuit.ccx(release_flag[0], source, target)
    circuit.x(release_flag[0])
    circuit.append(
        subtractor,
        list(current) + list(pad) + list(difference),
    )
    for source, target in reversed(list(zip(following, difference))):
        circuit.cx(source, target)

    # q_current - q_next supplies the positive desorption magnitude.
    for source, target in zip(current, difference):
        circuit.cx(source, target)
    circuit.append(
        subtractor.inverse(),
        list(following) + list(pad) + list(difference),
    )
    for source, target in zip(difference[:loading_bits], desorption):
        circuit.ccx(release_flag[0], source, target)
    circuit.append(
        subtractor,
        list(following) + list(pad) + list(difference),
    )
    for source, target in reversed(list(zip(current, difference))):
        circuit.cx(source, target)

    return circuit, {
        "q_current": register_indices(circuit, "q_current"),
        "q_next": register_indices(circuit, "q_next"),
        "release_flag": register_indices(circuit, "release_flag"),
        "adsorption_magnitude": register_indices(
            circuit, "adsorption_magnitude"
        ),
        "desorption_magnitude": register_indices(
            circuit, "desorption_magnitude"
        ),
        "cleared_workspace": register_indices(circuit, "operand_pad")
        + register_indices(circuit, "signed_difference"),
    }


def structural_basis_check() -> dict:
    bits = 3
    circuit, layout = build_sign_split_compute(bits)
    mismatches = 0
    dirty_workspace = 0
    for current_value in range(1 << bits):
        for next_value in range(1 << bits):
            prepared = QuantumCircuit(circuit.num_qubits)
            for bit, qubit in enumerate(layout["q_current"]):
                if (current_value >> bit) & 1:
                    prepared.x(qubit)
            for bit, qubit in enumerate(layout["q_next"]):
                if (next_value >> bit) & 1:
                    prepared.x(qubit)
            prepared.compose(circuit, inplace=True)
            state = Statevector.from_instruction(prepared)
            basis = int(np.argmax(np.abs(state.data)))

            def read(indices: list[int]) -> int:
                return sum(((basis >> index) & 1) << bit for bit, index in enumerate(indices))

            observed_current = read(layout["q_current"])
            observed_next = read(layout["q_next"])
            observed_flag = read(layout["release_flag"])
            observed_adsorption = read(layout["adsorption_magnitude"])
            observed_desorption = read(layout["desorption_magnitude"])
            expected_flag = int(next_value < current_value)
            expected_adsorption = max(next_value - current_value, 0)
            expected_desorption = max(current_value - next_value, 0)
            if (
                observed_current != current_value
                or observed_next != next_value
                or observed_flag != expected_flag
                or observed_adsorption != expected_adsorption
                or observed_desorption != expected_desorption
            ):
                mismatches += 1
            if read(layout["cleared_workspace"]) != 0:
                dirty_workspace += 1
    return {
        "bits": bits,
        "basis_pairs": (1 << bits) ** 2,
        "mismatches": mismatches,
        "dirty_workspace_pairs": dirty_workspace,
        "passes": mismatches == 0 and dirty_workspace == 0,
    }


def build_loading_to_terms(selected: dict) -> tuple[QuantumCircuit, dict]:
    loading_bits = int(selected["loading_bits"])
    term_bits = int(selected["cell_balance_term_bits"])
    sign_split, sign_layout = build_sign_split_compute(loading_bits)
    adsorption_weights = [
        int(value) for value in selected["adsorption_conversion_weights"]
    ]
    desorption_weights = [
        int(value) for value in selected["desorption_conversion_weights"]
    ]
    adders = {
        "adsorption": WeightedAdder(loading_bits, adsorption_weights)
        if any(adsorption_weights)
        else None,
        "desorption": WeightedAdder(loading_bits, desorption_weights)
        if any(desorption_weights)
        else None,
    }
    active_adders = [adder for adder in adders.values() if adder is not None]
    if not active_adders:
        raise AssertionError("both loading-to-gas conversions are empty")
    sum_bits = max(int(adder.num_sum_qubits) for adder in active_adders)
    work_bits = max(int(adder.num_ancillas) for adder in active_adders)

    adsorption_term = QuantumRegister(term_bits, "adsorption_term")
    desorption_term = QuantumRegister(term_bits, "desorption_term")
    conversion_sum = QuantumRegister(sum_bits, "conversion_sum")
    conversion_work = QuantumRegister(work_bits, "conversion_work")
    circuit = QuantumCircuit(
        *sign_split.qregs,
        adsorption_term,
        desorption_term,
        conversion_sum,
        conversion_work,
        name=f"clean_{selected['component'].lower()}_loading_to_terms",
    )
    sign_qubits = list(range(sign_split.num_qubits))
    circuit.append(sign_split.to_gate(), sign_qubits)

    magnitude_names = {
        "adsorption": "adsorption_magnitude",
        "desorption": "desorption_magnitude",
    }
    output_registers = {
        "adsorption": adsorption_term,
        "desorption": desorption_term,
    }
    for name in ("adsorption", "desorption"):
        adder = adders[name]
        if adder is None:
            continue
        if int(adder.num_sum_qubits) < term_bits:
            raise AssertionError((name, adder.num_sum_qubits, term_bits))
        magnitude = [
            circuit.qubits[index]
            for index in sign_layout[magnitude_names[name]]
        ]
        qargs = (
            magnitude
            + list(conversion_sum)[: adder.num_sum_qubits]
            + list(conversion_work)[: adder.num_ancillas]
        )
        circuit.append(adder, qargs)
        for source, target in zip(conversion_sum[:term_bits], output_registers[name]):
            circuit.cx(source, target)
        circuit.append(adder.inverse(), qargs)

    circuit.append(sign_split.inverse().to_gate(), sign_qubits)
    return circuit, {
        "q_current": register_indices(circuit, "q_current"),
        "q_next": register_indices(circuit, "q_next"),
        "desorption_term": register_indices(circuit, "desorption_term"),
        "adsorption_term": register_indices(circuit, "adsorption_term"),
        "retained_input_qubits": 2 * loading_bits,
        "retained_output_qubits": 2 * term_bits,
        "cleared_workspace_qubits": circuit.num_qubits
        - 2 * loading_bits
        - 2 * term_bits,
        "conversion_sum_bits": sum_bits,
        "conversion_work_bits": work_bits,
    }


def build_integrated_interface(
    transfer: QuantumCircuit,
    transfer_layout: dict,
    cell_selected: dict,
) -> tuple[QuantumCircuit, dict]:
    cell, _ = build_clean_balance(cell_selected)
    term_map = {
        "desorption": transfer_layout["desorption_term"],
        "adsorption": transfer_layout["adsorption_term"],
    }
    cell_map: list[int] = [-1] * cell.num_qubits
    next_index = transfer.num_qubits
    for register in cell.qregs:
        source_indices = [cell.find_bit(qubit).index for qubit in register]
        if register.name in term_map:
            shared = term_map[register.name]
            if len(shared) != len(source_indices):
                raise AssertionError((register.name, len(shared), len(source_indices)))
            for source, target in zip(source_indices, shared):
                cell_map[source] = target
        else:
            for source in source_indices:
                cell_map[source] = next_index
                next_index += 1
    if any(index < 0 for index in cell_map):
        raise AssertionError("incomplete cell-circuit mapping")

    circuit = QuantumCircuit(
        next_index,
        name=f"integrated_{cell_selected['component'].lower()}_loading_sign_balance",
    )
    transfer_map = list(range(transfer.num_qubits))
    circuit.compose(transfer, qubits=transfer_map, inplace=True)
    circuit.compose(cell, qubits=cell_map, inplace=True)
    circuit.compose(transfer.inverse(), qubits=transfer_map, inplace=True)

    cell_inputs = {
        name: [cell_map[index] for index in register_indices(cell, name)]
        for name in ("current_gas", "left_influx", "right_outflux")
    }
    next_gas = [cell_map[index] for index in register_indices(cell, "next_gas")]
    retained = (
        int(transfer_layout["retained_input_qubits"])
        + sum(len(values) for values in cell_inputs.values())
        + len(next_gas)
    )
    return circuit, {
        "loading_inputs": transfer_layout["q_current"]
        + transfer_layout["q_next"],
        "gas_and_face_inputs": cell_inputs,
        "next_gas_output": next_gas,
        "retained_input_output_qubits": retained,
        "cleared_workspace_qubits": circuit.num_qubits - retained,
        "directly_composed_modules": [
            "loading sign/magnitude extraction",
            "solid-mass loading-to-gas conversion",
            "interior-cell current/left/right/adsorption/desorption balance",
        ],
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
    ldf = json.loads(LDF_JSON.read_text(encoding="utf-8"))
    cell = json.loads(CELL_JSON.read_text(encoding="utf-8"))
    terms = physical_balance_terms()
    current_loading, next_loading, solid_mass = physical_loading_pairs()
    sample_count = len(current_loading)
    if sample_count != int(cell["physical_state_source"]["interior_cell_samples"]):
        raise AssertionError(sample_count)

    exact_transfer = (next_loading - current_loading) * solid_mass[:, None]
    exact_transfer[np.abs(exact_transfer) < ROUND_OFF_ZERO_MOL] = 0.0
    if not np.allclose(
        np.maximum(exact_transfer, 0.0),
        terms["adsorption"],
        rtol=0.0,
        atol=1.0e-12,
    ):
        raise AssertionError("adsorption transfer ordering mismatch")
    if not np.allclose(
        np.maximum(-exact_transfer, 0.0),
        terms["desorption"],
        rtol=0.0,
        atol=1.0e-12,
    ):
        raise AssertionError("desorption transfer ordering mismatch")

    structural = structural_basis_check()
    if not structural["passes"]:
        raise AssertionError(structural)

    components: list[dict] = []
    flat_rows: list[dict] = []
    for component_index, component in enumerate(COMPONENTS):
        ldf_component = ldf["components"][component_index]
        cell_component = cell["components"][component_index]
        loading_scale = float(
            ldf_component["selected"]["loading_scale_mol_per_kg"]
        )
        rows = [
            precision_row(
                component_index,
                loading_bits,
                loading_scale,
                current_loading,
                next_loading,
                solid_mass,
                terms,
                cell_component["selected"],
            )
            for loading_bits in LOADING_BITS
        ]
        selected = next(
            (
                row
                for row in rows
                if row["passes_loading_sign_balance_interface_gate"]
            ),
            None,
        )
        if selected is None:
            raise AssertionError(f"no loading-sign interface tier passes for {component}")

        transfer, transfer_layout = build_loading_to_terms(selected)
        compiled_transfer = transpile(
            transfer,
            basis_gates=["u", "cx"],
            optimization_level=1,
            seed_transpiler=TRANSPILER_SEED,
        )
        integrated, integrated_layout = build_integrated_interface(
            transfer,
            transfer_layout,
            cell_component["selected"],
        )
        compiled_integrated = transpile(
            integrated,
            basis_gates=["u", "cx"],
            optimization_level=1,
            seed_transpiler=TRANSPILER_SEED,
        )
        transfer_resources = resource_record(compiled_transfer)
        integrated_resources = resource_record(compiled_integrated)
        previous_bits = int(ldf_component["selected"]["arithmetic_bits"])
        result = {
            "component": component,
            "component_index": component_index,
            "previous_standalone_ldf_loading_bits": previous_bits,
            "selected": selected,
            "loading_bit_increase_for_balance_interface": int(
                selected["loading_bits"] - previous_bits
            ),
            "loading_to_terms_layout": transfer_layout,
            "integrated_layout": integrated_layout,
            "compiled_clean_loading_to_terms": transfer_resources,
            "compiled_integrated_loading_sign_cell_balance": integrated_resources,
            "screen_rows": rows,
        }
        components.append(result)
        flat_rows.append(
            {
                "component": component,
                "standalone_ldf_loading_bits": previous_bits,
                "integrated_loading_bits": selected["loading_bits"],
                "bit_increase": selected["loading_bits"] - previous_bits,
                "next_p95_scale_normalized_error": selected[
                    "next_p95_scale_normalized_absolute_error"
                ],
                "next_max_scale_normalized_error": selected[
                    "next_max_scale_normalized_absolute_error"
                ],
                "branch_mismatch_fraction": selected[
                    "branch_mismatch_fraction"
                ],
                "term_overflow_fraction": max(
                    selected["adsorption_term_overflow_fraction"],
                    selected["desorption_term_overflow_fraction"],
                ),
                "loading_to_terms_qubits": transfer_resources["logical_qubits"],
                "loading_to_terms_cx": transfer_resources["cx"],
                "integrated_qubits": integrated_resources["logical_qubits"],
                "integrated_depth": integrated_resources["depth_all_to_all"],
                "integrated_cx": integrated_resources["cx"],
            }
        )
        print(
            json.dumps(
                {
                    "component": component,
                    "loading_bits": selected["loading_bits"],
                    "integrated_qubits": integrated_resources["logical_qubits"],
                    "integrated_cx": integrated_resources["cx"],
                }
            ),
            flush=True,
        )

    retained = [
        int(row["integrated_layout"]["retained_input_output_qubits"])
        for row in components
    ]
    shared_workspace = max(
        int(row["compiled_integrated_loading_sign_cell_balance"]["logical_qubits"])
        - retained_qubits
        for row, retained_qubits in zip(components, retained)
    )
    sequential = {
        "accounting": "five loading-sign/conversion/cell-balance interfaces executed sequentially with shared workspace and all component inputs/next-gas outputs retained",
        "logical_qubits": shared_workspace + sum(retained),
        "retained_input_output_qubits": sum(retained),
        "shared_workspace_qubits": shared_workspace,
        "cx_additive_module_bound": sum(
            int(row["compiled_integrated_loading_sign_cell_balance"]["cx"])
            for row in components
        ),
        "depth_all_to_all_additive_module_bound": sum(
            int(
                row["compiled_integrated_loading_sign_cell_balance"][
                    "depth_all_to_all"
                ]
            )
            for row in components
        ),
    }
    payload = {
        "schema": "psa-qae-cce-primary-loading-sign-balance-interface/v1",
        "status": "five_component_loading_sign_solid_conversion_cell_balance_compiled_upstream_ldf_face_phase_open",
        "qpu_submission": False,
        "physical_state_source": {
            "runs": 32,
            "cycles_per_run": 100,
            "beds": 2,
            "interior_cells_per_bed": 2,
            "interior_cell_samples": sample_count,
            "component_balance_samples": sample_count * len(COMPONENTS),
            "cell_solid_mass_kg": float(solid_mass[0]),
        },
        "precision_gate": {
            "branch_mismatch_fraction_required": 0.0,
            "nonzero_change_erased_fraction_required": 0.0,
            "zero_change_false_activation_fraction_required": 0.0,
            "term_overflow_fraction_required": 0.0,
            "negative_sum_underflow_fraction_required": 0.0,
            "next_output_overflow_fraction_required": 0.0,
            "p95_next_scale_normalized_absolute_error_max": P95_NEXT_SCALE_NORMALIZED_GATE,
            "max_next_scale_normalized_absolute_error_max": MAX_NEXT_SCALE_NORMALIZED_GATE,
        },
        "small_width_structural_check": structural,
        "components": components,
        "sequential_five_component_accounting": sequential,
        "precision_interface_finding": "the loading precision that is adequate for standalone q_next accuracy is not automatically adequate for the smaller signed loading difference; the balance interface therefore screens and reports wider current/next registers",
        "claim_boundary": {
            "supported": "physical-cache precision screen and clean u/CX compilation from supplied current/next loading registers through sign extraction, solid-mass conversion, and conservative interior-cell next-gas accumulation",
            "unsupported": "direct composition with the current lower-width competitive-Langmuir/LDF outputs or oriented-face circuits, reversible composition normalization, boundary-cell valve/tank withdrawal, adaptive integration, complete phase/cycle, routing, hardware feasibility, or quantum advantage",
        },
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    with OUT_CSV.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(flat_rows[0]))
        writer.writeheader()
        writer.writerows(flat_rows)
    lines = [
        "# Reversible loading-sign extraction and interior-cell balance interface",
        "",
        f"The screen covers **{sample_count:,} interior-cell states** and **{sample_count * len(COMPONENTS):,} component balances**. A three-bit exhaustive control checks all **{structural['basis_pairs']}** current/next loading pairs with zero branch, magnitude, or workspace mismatch.",
        "",
        "| Component | earlier LDF bits | interface bits | added bits | p95 next error | max next error | integrated qubits | integrated CX |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in flat_rows:
        lines.append(
            f"| {row['component']} | {row['standalone_ldf_loading_bits']} | "
            f"{row['integrated_loading_bits']} | {row['bit_increase']} | "
            f"{row['next_p95_scale_normalized_error']:.3e} | "
            f"{row['next_max_scale_normalized_error']:.3e} | "
            f"{row['integrated_qubits']:,} | {row['integrated_cx']:,} |"
        )
    lines += [
        "",
        f"Sequential workspace-reuse accounting retains all five component inputs and next-gas outputs at **{sequential['logical_qubits']:,} logical qubits** and **{sequential['cx_additive_module_bound']:,} additive CX**.",
        "",
        "The widened register requirement is itself a resource result: precision adequate for q_next can erase the much smaller signed q_next-q_current transfer. The compiled interface closes sign extraction and solid-mass conversion from supplied current/next loading registers. Direct composition with the existing lower-width LDF outputs, face circuits, boundary terms, adaptive integration, routing, and a complete phase/cycle remain open.",
        "",
        "No QPU job was submitted.",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": payload["status"],
                "selected_loading_bits": {
                    row["component"]: row["selected"]["loading_bits"]
                    for row in components
                },
                "sequential_logical_qubits": sequential["logical_qubits"],
                "sequential_cx": sequential["cx_additive_module_bound"],
                "qpu_submission": False,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
