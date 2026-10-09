"""Compile conservative one-second interior-cell gas-balance accumulators.

For each component in an interior finite-volume cell, the source model uses

    n_next = n + left_face_flux + desorption
                 - right_face_flux - adsorption.

The adsorption contribution is the solid mass times the one-second LDF
loading change.  This script evaluates that equation over the cached physical
states, encodes its five nonnegative terms, and compiles a clean
compute-copy-uncompute accumulator.  Uptake and release are supplied as a
sign-split interface; reversible sign extraction from the current/next
loading registers and monolithic connection to the upstream LDF/face circuits
remain open.  No QPU work is submitted.
"""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import numpy as np
from qiskit import QuantumCircuit, QuantumRegister, transpile
from qiskit.circuit.library import ModularAdderGate, WeightedAdder

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
CACHE = HERE / "cce_primary_physical_css_horizon_cache.npz"
SOURCE = HERE / "psa_two_bed_spatial_tank_n2_independent_source_uncertainty_32.csv"
OUT_JSON = RESULTS / "PSA_QAE_CCE_PRIMARY_CELL_BALANCE_MICROSTEPS.json"
OUT_CSV = RESULTS / "PSA_QAE_CCE_PRIMARY_CELL_BALANCE_MICROSTEPS.csv"
OUT_MD = RESULTS / "PSA_QAE_CCE_PRIMARY_CELL_BALANCE_MICROSTEPS.md"

INPUT_BITS = [16, 18, 20, 22]
OUTPUT_BITS = [20, 22, 24, 26]
P95_NEXT_SCALE_NORMALIZED_GATE = 2.5e-5
MAX_NEXT_SCALE_NORMALIZED_GATE = 5.0e-5
ROUND_OFF_ZERO_MOL = 1.0e-15
TRANSPILER_SEED = 20261009

TERM_NAMES = ("current_gas", "left_influx", "right_outflux", "desorption", "adsorption")
POSITIVE_TERM_INDICES = (0, 1, 3)
NEGATIVE_TERM_INDICES = (2, 4)


def source_rows() -> dict[int, dict[str, str]]:
    with SOURCE.open(newline="", encoding="utf-8-sig") as handle:
        return {int(row["sample"]): row for row in csv.DictReader(handle)}


def physical_balance_terms() -> dict[str, np.ndarray]:
    cache = np.load(CACHE)
    samples = np.asarray(cache["samples"], dtype=int)
    boundaries = np.asarray(cache["boundaries"], dtype=float)
    if boundaries.shape != (32, 101, 85):
        raise AssertionError(boundaries.shape)
    rows = source_rows()
    records: list[tuple[np.ndarray, ...]] = []
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
                    adsorbed_transfer = solid[cell] * (
                        loading_next[:, cell] - loading[:, cell]
                    )
                    adsorbed_transfer[
                        np.abs(adsorbed_transfer) < ROUND_OFF_ZERO_MOL
                    ] = 0.0
                    records.append(
                        (
                            gas[:, cell],
                            face_flux[:, cell - 1],
                            face_flux[:, cell],
                            np.maximum(-adsorbed_transfer, 0.0),
                            np.maximum(adsorbed_transfer, 0.0),
                        )
                    )
    terms = {
        name: np.asarray([record[index] for record in records], dtype=float)
        for index, name in enumerate(TERM_NAMES)
    }
    terms["next_gas"] = (
        terms["current_gas"]
        + terms["left_influx"]
        + terms["desorption"]
        - terms["right_outflux"]
        - terms["adsorption"]
    )
    return terms


def encoded_term(
    values: np.ndarray,
    scale: float,
    input_bits: int,
    output_bits: int,
    balance_scale: float,
) -> tuple[np.ndarray, list[int]]:
    input_levels = (1 << input_bits) - 1
    output_levels = (1 << output_bits) - 1
    if scale <= 0.0:
        return np.zeros(len(values), dtype=np.int64), [0] * input_bits
    input_code = np.rint(values / scale * input_levels).astype(np.int64)
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
    output_code = np.zeros(len(values), dtype=np.int64)
    for bit, weight in enumerate(weights):
        output_code += ((input_code >> bit) & 1) * weight
    return output_code, weights


def precision_row(
    component_index: int,
    input_bits: int,
    output_bits: int,
    terms: dict[str, np.ndarray],
) -> dict:
    values = [terms[name][:, component_index] for name in TERM_NAMES]
    exact_next = terms["next_gas"][:, component_index]
    scales = [float(np.max(value)) for value in values]
    balance_scale = float(
        np.max(values[0] + values[1] + values[3])
    )
    encoded = [
        encoded_term(
            value,
            scale,
            input_bits,
            output_bits,
            balance_scale,
        )
        for value, scale in zip(values, scales)
    ]
    output_codes = [item[0] for item in encoded]
    positive = sum(output_codes[index] for index in POSITIVE_TERM_INDICES)
    negative = sum(output_codes[index] for index in NEGATIVE_TERM_INDICES)
    next_code = positive - negative
    output_levels = (1 << output_bits) - 1
    next_approx = next_code / output_levels * balance_scale
    next_scale = float(np.max(exact_next))
    normalized_error = np.abs(next_approx - exact_next) / next_scale
    erasure = [
        float(np.mean((value > 0.0) & (code == 0)))
        for value, code in zip(values, output_codes)
    ]
    result = {
        "component": COMPONENTS[component_index],
        "component_index": component_index,
        "input_bits_per_term": input_bits,
        "next_output_bits": output_bits,
        "term_scales_mol": dict(zip(TERM_NAMES, scales)),
        "balance_scale_mol": balance_scale,
        "next_gas_scale_mol": next_scale,
        "term_weights": {
            name: encoded[index][1] for index, name in enumerate(TERM_NAMES)
        },
        "next_p95_scale_normalized_absolute_error": float(
            np.quantile(normalized_error, 0.95)
        ),
        "next_max_scale_normalized_absolute_error": float(
            np.max(normalized_error)
        ),
        "maximum_nonzero_term_erased_fraction": float(max(erasure)),
        "positive_sum_overflow_fraction": float(np.mean(positive > output_levels)),
        "negative_sum_underflow_fraction": float(np.mean(negative > positive)),
        "next_output_overflow_fraction": float(
            np.mean(next_code > output_levels)
        ),
        "minimum_exact_next_gas_mol": float(np.min(exact_next)),
    }
    result["passes_cell_balance_precision_gate"] = bool(
        result["next_p95_scale_normalized_absolute_error"]
        <= P95_NEXT_SCALE_NORMALIZED_GATE
        and result["next_max_scale_normalized_absolute_error"]
        <= MAX_NEXT_SCALE_NORMALIZED_GATE
        and result["maximum_nonzero_term_erased_fraction"] == 0.0
        and result["positive_sum_overflow_fraction"] == 0.0
        and result["negative_sum_underflow_fraction"] == 0.0
        and result["next_output_overflow_fraction"] == 0.0
        and result["minimum_exact_next_gas_mol"] > 0.0
    )
    return result


def build_clean_balance(selected: dict) -> tuple[QuantumCircuit, dict]:
    input_bits = int(selected["input_bits_per_term"])
    output_bits = int(selected["next_output_bits"])
    weights_by_name = {
        name: [int(value) for value in selected["term_weights"][name]]
        for name in TERM_NAMES
    }
    positive_weights = [
        weight
        for index in POSITIVE_TERM_INDICES
        for weight in weights_by_name[TERM_NAMES[index]]
    ]
    negative_weights = [
        weight
        for index in NEGATIVE_TERM_INDICES
        for weight in weights_by_name[TERM_NAMES[index]]
    ]
    positive_adder = WeightedAdder(len(positive_weights), positive_weights)
    negative_adder = WeightedAdder(len(negative_weights), negative_weights)
    common_bits = max(
        int(positive_adder.num_sum_qubits),
        int(negative_adder.num_sum_qubits),
        output_bits,
    )

    registers = {
        name: QuantumRegister(input_bits, name) for name in TERM_NAMES
    }
    positive_sum = QuantumRegister(positive_adder.num_sum_qubits, "positive_sum")
    negative_sum = QuantumRegister(negative_adder.num_sum_qubits, "negative_sum")
    positive_work = QuantumRegister(positive_adder.num_ancillas, "positive_work")
    negative_work = QuantumRegister(negative_adder.num_ancillas, "negative_work")
    negative_pad = QuantumRegister(
        common_bits - negative_adder.num_sum_qubits,
        "negative_pad",
    )
    balance = QuantumRegister(common_bits, "balance")
    next_gas = QuantumRegister(output_bits, "next_gas")
    circuit = QuantumCircuit(
        *registers.values(),
        positive_sum,
        negative_sum,
        positive_work,
        negative_work,
        negative_pad,
        balance,
        next_gas,
        name=f"clean_{selected['component'].lower()}_interior_cell_balance",
    )
    positive_state = [
        qubit
        for index in POSITIVE_TERM_INDICES
        for qubit in registers[TERM_NAMES[index]]
    ]
    negative_state = [
        qubit
        for index in NEGATIVE_TERM_INDICES
        for qubit in registers[TERM_NAMES[index]]
    ]
    positive_qargs = (
        positive_state + list(positive_sum) + list(positive_work)
    )
    negative_qargs = (
        negative_state + list(negative_sum) + list(negative_work)
    )
    circuit.append(positive_adder, positive_qargs)
    circuit.append(negative_adder, negative_qargs)
    for source, target in zip(positive_sum, balance):
        circuit.cx(source, target)
    negative_operand = list(negative_sum) + list(negative_pad)
    subtractor = ModularAdderGate(common_bits)
    circuit.append(subtractor.inverse(), negative_operand + list(balance))
    for source, target in zip(list(balance)[:output_bits], next_gas):
        circuit.cx(source, target)
    circuit.append(subtractor, negative_operand + list(balance))
    for source, target in reversed(list(zip(positive_sum, balance))):
        circuit.cx(source, target)
    circuit.append(negative_adder.inverse(), negative_qargs)
    circuit.append(positive_adder.inverse(), positive_qargs)
    return circuit, {
        "retained_inputs": [
            f"{input_bits}-bit {name}" for name in TERM_NAMES
        ],
        "clean_output": f"{output_bits}-bit next gas inventory",
        "positive_sum_bits": int(positive_adder.num_sum_qubits),
        "negative_sum_bits": int(negative_adder.num_sum_qubits),
        "common_balance_bits": common_bits,
        "cleared": [
            "positive weighted sum",
            "negative weighted sum",
            "subtraction balance",
            "adder workspace",
        ],
    }


def main() -> None:
    terms = physical_balance_terms()
    sample_count = int(len(terms["next_gas"]))
    component_results: list[dict] = []
    flat_rows: list[dict] = []
    for component_index, component in enumerate(COMPONENTS):
        rows = [
            precision_row(component_index, input_bits, output_bits, terms)
            for input_bits in INPUT_BITS
            for output_bits in OUTPUT_BITS
        ]
        selected = next(
            (row for row in rows if row["passes_cell_balance_precision_gate"]),
            None,
        )
        if selected is None:
            raise AssertionError(f"no cell-balance precision tier passes for {component}")
        circuit, layout = build_clean_balance(selected)
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
            "basis_gates": ["u", "cx"],
            "optimization_level": 1,
            "transpiler_seed": TRANSPILER_SEED,
        }
        component_results.append(
            {
                "component": component,
                "component_index": component_index,
                "selected": selected,
                "register_layout": layout,
                "compiled_clean_balance": resources,
                "screen_rows": rows,
            }
        )
        flat_rows.append(
            {
                "component": component,
                "input_bits_per_term": selected["input_bits_per_term"],
                "next_output_bits": selected["next_output_bits"],
                "next_p95_scale_normalized_error": selected[
                    "next_p95_scale_normalized_absolute_error"
                ],
                "next_max_scale_normalized_error": selected[
                    "next_max_scale_normalized_absolute_error"
                ],
                "nonzero_erased_fraction": selected[
                    "maximum_nonzero_term_erased_fraction"
                ],
                "underflow_fraction": selected["negative_sum_underflow_fraction"],
                "logical_qubits": resources["logical_qubits"],
                "depth_all_to_all": resources["depth_all_to_all"],
                "cx": resources["cx"],
            }
        )
        print(
            json.dumps(
                {
                    "component": component,
                    "input_bits": selected["input_bits_per_term"],
                    "output_bits": selected["next_output_bits"],
                    "logical_qubits": resources["logical_qubits"],
                    "cx": resources["cx"],
                }
            ),
            flush=True,
        )

    retained_per_component = [
        len(TERM_NAMES) * int(row["selected"]["input_bits_per_term"])
        + int(row["selected"]["next_output_bits"])
        for row in component_results
    ]
    shared_workspace = max(
        int(row["compiled_clean_balance"]["logical_qubits"]) - retained
        for row, retained in zip(component_results, retained_per_component)
    )
    sequential = {
        "accounting": "five clean component balances executed sequentially with shared arithmetic workspace and all sign-split term inputs/next-gas outputs retained",
        "logical_qubits": shared_workspace + sum(retained_per_component),
        "retained_term_and_next_gas_qubits": sum(retained_per_component),
        "shared_workspace_qubits": shared_workspace,
        "cx_additive_module_bound": sum(
            int(row["compiled_clean_balance"]["cx"])
            for row in component_results
        ),
        "depth_all_to_all_additive_module_bound": sum(
            int(row["compiled_clean_balance"]["depth_all_to_all"])
            for row in component_results
        ),
        "interpretation": "modular interior-cell balance accounting; upstream sign extraction, direct circuit composition, boundary cells, adaptive integration, routing, and a complete phase remain open",
    }
    minimum_next = {
        component: float(np.min(terms["next_gas"][:, index]))
        for index, component in enumerate(COMPONENTS)
    }
    payload = {
        "schema": "psa-qae-cce-primary-cell-balance-microsteps/v1",
        "status": "five_component_interior_cell_balance_accumulators_compiled_sign_extraction_phase_cycle_open",
        "qpu_submission": False,
        "physical_state_source": {
            "runs": 32,
            "cycles_per_run": 100,
            "beds": 2,
            "interior_cells_per_bed": 2,
            "interior_cell_samples": sample_count,
            "component_balance_samples": sample_count * len(COMPONENTS),
            "minimum_exact_next_gas_mol": minimum_next,
            "negative_exact_next_count": int(np.sum(terms["next_gas"] < 0.0)),
        },
        "precision_gate": {
            "p95_next_scale_normalized_absolute_error_max": P95_NEXT_SCALE_NORMALIZED_GATE,
            "max_next_scale_normalized_absolute_error_max": MAX_NEXT_SCALE_NORMALIZED_GATE,
            "nonzero_term_erased_fraction_required": 0.0,
            "positive_sum_overflow_fraction_required": 0.0,
            "negative_sum_underflow_fraction_required": 0.0,
            "next_output_overflow_fraction_required": 0.0,
        },
        "components": component_results,
        "sequential_five_component_accounting": sequential,
        "conservation_statement": "the same oriented internal-face component transfer is subtracted from the upstream cell and added to the downstream cell; it cancels exactly in a two-cell sum before boundary and adsorption terms",
        "claim_boundary": {
            "supported": "physical-cache precision screen and clean u/CX compilation of five separate one-second interior-cell component balances joining current gas, left/right face transfers, sign-split LDF transfer, and next gas",
            "unsupported": "reversible derivation of sign-split adsorption/desorption from current/next loadings, monolithic composition with the upstream LDF and face circuits, boundary-cell valve or tank terms, adaptive integration, complete phase/cycle, routing, hardware feasibility, or quantum advantage",
        },
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    with OUT_CSV.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(flat_rows[0]))
        writer.writeheader()
        writer.writerows(flat_rows)
    lines = [
        "# Clean five-component interior-cell gas-balance accumulators",
        "",
        f"The physical screen contains **{sample_count:,} interior-cell states** and **{sample_count * len(COMPONENTS):,} component balances**. Every exact one-second next-gas value is positive.",
        "",
        "| Component | input bits/term | next bits | p95 error / next scale | max error / next scale | qubits | CX |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in flat_rows:
        lines.append(
            f"| {row['component']} | {row['input_bits_per_term']} | {row['next_output_bits']} | "
            f"{row['next_p95_scale_normalized_error']:.3e} | "
            f"{row['next_max_scale_normalized_error']:.3e} | "
            f"{row['logical_qubits']:,} | {row['cx']:,} |"
        )
    lines += [
        "",
        f"Sequential workspace-reuse accounting retains all sign-split balance inputs and next-gas outputs at **{sequential['logical_qubits']:,} logical qubits** and **{sequential['cx_additive_module_bound']:,} additive CX**.",
        "",
        "This closes the clean interior-cell accumulation interface. Reversible sign extraction from loading differences, direct monolithic composition with the LDF/face modules, boundary-cell terms, adaptive integration, routing, and a complete phase/cycle remain open.",
        "",
        "No QPU job was submitted.",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": payload["status"],
                "interior_cell_samples": sample_count,
                "sequential_logical_qubits": sequential["logical_qubits"],
                "sequential_cx": sequential["cx_additive_module_bound"],
                "qpu_submission": False,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
