"""Compose product-valve component fluxes into boundary-cell balances.

The product-boundary audit already compiles the nonlinear outlet law

    F_out = k_out * max(P_product - P_back, 0)

and multiplies it by all five encoded component fractions.  The conservative
cell-balance audit, however, previously accepted the right-face transfer as an
independent register.  This script closes that register interface for the
product-end cell.  It computes all five outlet component fluxes, uses each
temporary flux register directly as the negative boundary term in a clean
one-second component balance, copies the five next-gas outputs, and reverses
the complete valve/flux circuit.

The pressure and composition registers are still supplied inputs.  Reversible
composition normalization from gas inventories, direct LDF coupling at the
same product cell, valve scheduling, adaptive phase integration, tank
withdrawal, routing, and a complete cycle remain outside this circuit.  No
QPU work is submitted.
"""

from __future__ import annotations

import csv
import gc
import json
from pathlib import Path

import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit.circuit.library import ModularAdderGate, WeightedAdder

from cce_primary_loading_sign_balance_interface import register_indices
from cce_primary_product_boundary_reversible_microsteps import (
    COMPOSITION_BITS,
    PRESSURE_BITS,
    RESULTS,
    TRANSPILER_SEED,
    build_valve_flux_circuit,
    valve_row,
    valve_states,
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
CACHE = HERE / "cce_primary_physical_css_horizon_cache.npz"
SOURCE = HERE / "psa_two_bed_spatial_tank_n2_independent_source_uncertainty_32.csv"
PRODUCT_JSON = RESULTS / "PSA_QAE_CCE_PRIMARY_PRODUCT_BOUNDARY_MICROSTEPS.json"
OUT_JSON = RESULTS / "PSA_QAE_CCE_PRIMARY_PRODUCT_BOUNDARY_BALANCE_COMPOSITION.json"
OUT_CSV = RESULTS / "PSA_QAE_CCE_PRIMARY_PRODUCT_BOUNDARY_BALANCE_COMPOSITION.csv"
OUT_MD = RESULTS / "PSA_QAE_CCE_PRIMARY_PRODUCT_BOUNDARY_BALANCE_COMPOSITION.md"

INPUT_BITS = [16, 18, 20, 22]
OUTPUT_BITS = [20, 22, 24, 26]
# The product-end screen propagates the already-declared 12-bit valve-QROM
# approximation.  Its inventory-level gate is therefore separated from the
# tighter arithmetic-only interior-cell gate.  Both bounds remain below 0.02%
# of the component next-inventory scale.
P95_NEXT_SCALE_NORMALIZED_GATE = 1.0e-4
MAX_NEXT_SCALE_NORMALIZED_GATE = 2.0e-4
ROUND_OFF_ZERO_MOL = 1.0e-15

INPUT_TERM_NAMES = ("current_gas", "left_influx", "desorption", "adsorption")
POSITIVE_TERM_NAMES = ("current_gas", "left_influx", "desorption")


def source_rows() -> dict[int, dict[str, str]]:
    with SOURCE.open(newline="", encoding="utf-8-sig") as handle:
        return {int(row["sample"]): row for row in csv.DictReader(handle)}


def boundary_terms() -> dict[str, np.ndarray]:
    """Return one-second product-end balance terms over the frozen cache."""

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
                face_flow = params.k_internal_mol_s_bar * (
                    pressure[:-1] - pressure[1:]
                )
                left_flux = face_flow[-1] * (
                    composition[:, -2]
                    if face_flow[-1] >= 0.0
                    else composition[:, -1]
                )
                outlet_flow = params.k_out_mol_s_bar * max(
                    pressure[-1]
                    - (params.P_high_bar - params.product_outlet_drop_bar),
                    0.0,
                )
                outlet_flux = outlet_flow * composition[:, -1]
                adsorbed_transfer = solid[-1] * (
                    loading_next[:, -1] - loading[:, -1]
                )
                adsorbed_transfer[
                    np.abs(adsorbed_transfer) < ROUND_OFF_ZERO_MOL
                ] = 0.0
                records.append(
                    (
                        gas[:, -1],
                        left_flux,
                        np.maximum(-adsorbed_transfer, 0.0),
                        np.maximum(adsorbed_transfer, 0.0),
                        outlet_flux,
                        np.full(len(COMPONENTS), pressure[-1]),
                        composition[:, -1],
                    )
                )
    result = {
        name: np.asarray([record[index] for record in records], dtype=float)
        for index, name in enumerate(INPUT_TERM_NAMES)
    }
    result["outlet_flux"] = np.asarray(
        [record[4] for record in records], dtype=float
    )
    result["pressure"] = np.asarray(
        [record[5] for record in records], dtype=float
    )[:, 0]
    result["composition"] = np.asarray(
        [record[6] for record in records], dtype=float
    )
    result["next_gas"] = (
        result["current_gas"]
        + result["left_influx"]
        + result["desorption"]
        - result["outlet_flux"]
        - result["adsorption"]
    )
    if np.any(result["left_influx"] < 0.0):
        raise AssertionError("cached product-end left influx changes orientation")
    if np.any(result["next_gas"] <= 0.0):
        raise AssertionError("one-second product boundary balance underflows")
    return result


def encode_term(
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


def valve_flux_codes(selected_valve: dict, terms: dict[str, np.ndarray]) -> np.ndarray:
    pressure_levels = (1 << PRESSURE_BITS) - 1
    flow_bits = int(selected_valve["flow_bits"])
    pressure_code = np.rint(
        terms["pressure"]
        / float(selected_valve["pressure_scale_bar"])
        * pressure_levels
    ).astype(np.int64)
    shift = PRESSURE_BITS - int(selected_valve["valve_address_bits"])
    address = pressure_code >> shift
    table = np.asarray(selected_valve["flow_table_codes"], dtype=np.int64)
    flow_code = table[address]
    composition_levels = (1 << COMPOSITION_BITS) - 1
    composition_code = np.rint(
        terms["composition"] * composition_levels
    ).astype(np.int64)
    return (flow_code[:, None] * composition_code) >> COMPOSITION_BITS


def precision_row(
    component_index: int,
    input_bits: int,
    output_bits: int,
    selected_valve: dict,
    terms: dict[str, np.ndarray],
    flux_codes: np.ndarray,
) -> dict:
    component_values = {
        name: terms[name][:, component_index] for name in INPUT_TERM_NAMES
    }
    exact_outlet = terms["outlet_flux"][:, component_index]
    exact_next = terms["next_gas"][:, component_index]
    balance_scale = float(
        np.max(
            component_values["current_gas"]
            + component_values["left_influx"]
            + component_values["desorption"]
        )
    )
    scales = {
        name: float(np.max(values)) for name, values in component_values.items()
    }
    encoded = {
        name: encode_term(
            values,
            scales[name],
            input_bits,
            output_bits,
            balance_scale,
        )
        for name, values in component_values.items()
    }
    output_levels = (1 << output_bits) - 1
    flow_bits = int(selected_valve["flow_bits"])
    flow_levels = (1 << flow_bits) - 1
    flow_scale = float(selected_valve["flow_scale_mol_s"])
    outlet_weights = [
        int(
            round(
                flow_scale
                / flow_levels
                * (1 << bit)
                / balance_scale
                * output_levels
            )
        )
        for bit in range(flow_bits)
    ]
    outlet_code = np.zeros(len(exact_outlet), dtype=np.int64)
    direct_flux_code = flux_codes[:, component_index]
    for bit, weight in enumerate(outlet_weights):
        outlet_code += ((direct_flux_code >> bit) & 1) * weight
    positive = sum(encoded[name][0] for name in POSITIVE_TERM_NAMES)
    negative = outlet_code + encoded["adsorption"][0]
    next_code = positive - negative
    next_approx = next_code / output_levels * balance_scale
    next_scale = float(np.max(exact_next))
    normalized_error = np.abs(next_approx - exact_next) / next_scale
    input_erasures = {
        name: float(np.mean((component_values[name] > 0.0) & (encoded[name][0] == 0)))
        for name in INPUT_TERM_NAMES
    }
    result = {
        "component": COMPONENTS[component_index],
        "component_index": component_index,
        "input_bits_per_nonvalve_term": input_bits,
        "valve_flux_input_bits": flow_bits,
        "next_output_bits": output_bits,
        "term_scales_mol": scales,
        "outlet_flux_scale_mol": flow_scale,
        "balance_scale_mol": balance_scale,
        "next_gas_scale_mol": next_scale,
        "term_weights": {
            name: encoded[name][1] for name in INPUT_TERM_NAMES
        },
        "direct_outlet_flux_weights": outlet_weights,
        "next_p95_scale_normalized_absolute_error": float(
            np.quantile(normalized_error, 0.95)
        ),
        "next_max_scale_normalized_absolute_error": float(
            np.max(normalized_error)
        ),
        "maximum_nonzero_nonvalve_term_erased_fraction": float(
            max(input_erasures.values())
        ),
        "nonzero_valve_flux_erased_by_valve_fraction": float(
            np.mean((exact_outlet > 0.0) & (direct_flux_code == 0))
        ),
        "nonzero_valve_flux_erased_by_balance_conversion_fraction": float(
            np.mean((exact_outlet > 0.0) & (outlet_code == 0))
        ),
        "positive_sum_overflow_fraction": float(
            np.mean(positive > output_levels)
        ),
        "negative_sum_underflow_fraction": float(np.mean(negative > positive)),
        "next_output_overflow_fraction": float(
            np.mean(next_code > output_levels)
        ),
        "minimum_exact_next_gas_mol": float(np.min(exact_next)),
    }
    result["passes_product_boundary_balance_precision_gate"] = bool(
        result["next_p95_scale_normalized_absolute_error"]
        <= P95_NEXT_SCALE_NORMALIZED_GATE
        and result["next_max_scale_normalized_absolute_error"]
        <= MAX_NEXT_SCALE_NORMALIZED_GATE
        and result["maximum_nonzero_nonvalve_term_erased_fraction"] == 0.0
        and result["nonzero_valve_flux_erased_by_valve_fraction"] == 0.0
        and result[
            "nonzero_valve_flux_erased_by_balance_conversion_fraction"
        ]
        == 0.0
        and result["positive_sum_overflow_fraction"] == 0.0
        and result["negative_sum_underflow_fraction"] == 0.0
        and result["next_output_overflow_fraction"] == 0.0
        and result["minimum_exact_next_gas_mol"] > 0.0
    )
    return result


def build_direct_composition(
    valve: QuantumCircuit,
    selected_rows: list[dict],
) -> tuple[QuantumCircuit, dict]:
    """Compute valve flux, apply five balances, and reverse the valve."""

    valve_flux = register_indices(valve, "component_flux")
    flow_bits = int(selected_rows[0]["valve_flux_input_bits"])
    if len(valve_flux) != len(COMPONENTS) * flow_bits:
        raise AssertionError((len(valve_flux), flow_bits))

    adders: list[tuple[WeightedAdder, WeightedAdder]] = []
    for row in selected_rows:
        positive_weights = [
            weight
            for name in POSITIVE_TERM_NAMES
            for weight in row["term_weights"][name]
        ]
        negative_weights = list(row["direct_outlet_flux_weights"]) + list(
            row["term_weights"]["adsorption"]
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

    next_index = valve.num_qubits

    def allocate(size: int) -> list[int]:
        nonlocal next_index
        result = list(range(next_index, next_index + size))
        next_index += size
        return result

    component_layouts: list[dict[str, list[int]]] = []
    for row in selected_rows:
        bits = int(row["input_bits_per_nonvalve_term"])
        component_layouts.append(
            {
                name: allocate(bits) for name in INPUT_TERM_NAMES
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
        name="clean_product_valve_five_component_boundary_balance",
    )
    valve_map = list(range(valve.num_qubits))
    circuit.compose(valve, qubits=valve_map, inplace=True)

    for component_index, (row, pair, layout) in enumerate(
        zip(selected_rows, adders, component_layouts)
    ):
        positive_adder, negative_adder = pair
        positive_state = [
            qubit
            for name in POSITIVE_TERM_NAMES
            for qubit in layout[name]
        ]
        component_flux = valve_flux[
            component_index * flow_bits : (component_index + 1) * flow_bits
        ]
        negative_state = component_flux + layout["adsorption"]
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

    circuit.compose(valve.inverse(), qubits=valve_map, inplace=True)
    process_inputs = sorted(
        register_indices(valve, "pressure")
        + register_indices(valve, "composition")
    )
    retained_component_inputs = [
        index
        for layout in component_layouts
        for name in INPUT_TERM_NAMES
        for index in layout[name]
    ]
    next_outputs = [
        index for layout in component_layouts for index in layout["next_gas"]
    ]
    retained = sorted(
        set(process_inputs + retained_component_inputs + next_outputs)
    )
    if set(valve_flux) & set(retained):
        raise AssertionError("temporary valve flux must be uncomputed")
    return circuit, {
        "pressure_composition_inputs": process_inputs,
        "component_nonvalve_inputs": retained_component_inputs,
        "next_gas_outputs": next_outputs,
        "temporary_valve_component_flux": valve_flux,
        "retained_input_output_qubits": len(retained),
        "cleared_workspace_qubits": circuit.num_qubits - len(retained),
        "shared_arithmetic": {
            "positive_sum_bits": positive_sum_bits,
            "negative_sum_bits": negative_sum_bits,
            "positive_work_bits": positive_work_bits,
            "negative_work_bits": negative_work_bits,
            "common_balance_bits": common_bits,
        },
        "directly_composed_modules": [
            "pressure-bin QROM product valve",
            "five flow-times-composition multipliers",
            "five conservative product-end component balances",
            "exact reverse of all valve/flux work",
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
    product = json.loads(PRODUCT_JSON.read_text(encoding="utf-8"))
    selected_valve = product["selected_valve"]
    pressure, composition = valve_states()
    recomputed_valve = valve_row(
        int(selected_valve["valve_address_bits"]),
        int(selected_valve["flow_bits"]),
        pressure,
        composition,
    )
    if recomputed_valve["flow_table_codes"] != selected_valve["flow_table_codes"]:
        raise AssertionError("product-valve source and selected table differ")
    terms = boundary_terms()
    if not np.allclose(pressure, terms["pressure"], rtol=0.0, atol=1.0e-12):
        raise AssertionError("product-boundary pressure ordering differs")
    if not np.allclose(composition, terms["composition"], rtol=0.0, atol=1.0e-12):
        raise AssertionError("product-boundary composition ordering differs")
    flux_codes = valve_flux_codes(selected_valve, terms)

    components: list[dict] = []
    selected_rows: list[dict] = []
    flat_rows: list[dict] = []
    for component_index, component in enumerate(COMPONENTS):
        rows = [
            precision_row(
                component_index,
                input_bits,
                output_bits,
                selected_valve,
                terms,
                flux_codes,
            )
            for input_bits in INPUT_BITS
            for output_bits in OUTPUT_BITS
        ]
        selected = next(
            (
                row
                for row in rows
                if row["passes_product_boundary_balance_precision_gate"]
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
                "input_bits": selected["input_bits_per_nonvalve_term"],
                "valve_flux_bits": selected["valve_flux_input_bits"],
                "next_bits": selected["next_output_bits"],
                "next_p95_scale_error": selected[
                    "next_p95_scale_normalized_absolute_error"
                ],
                "next_max_scale_error": selected[
                    "next_max_scale_normalized_absolute_error"
                ],
                "minimum_next_gas_mol": selected["minimum_exact_next_gas_mol"],
                "passes": selected[
                    "passes_product_boundary_balance_precision_gate"
                ],
            }
        )

    valve, valve_layout = build_valve_flux_circuit(selected_valve)
    direct, direct_layout = build_direct_composition(valve, selected_rows)
    compiled = transpile(
        direct,
        basis_gates=["u", "cx"],
        optimization_level=1,
        seed_transpiler=TRANSPILER_SEED,
    )
    resources = resource_record(compiled)
    if resources["measurement"] or resources["reset"]:
        raise AssertionError(resources)
    payload = {
        "schema": "psa-qae-cce-primary-product-boundary-balance-composition/v1",
        "status": "five_component_product_valve_to_boundary_balance_directly_composed_normalization_phase_open",
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
            "nonzero_erasure_required": 0.0,
            "underflow_overflow_required": 0.0,
        },
        "product_valve": {
            "address_bits": int(selected_valve["valve_address_bits"]),
            "pressure_bits": PRESSURE_BITS,
            "composition_bits_per_component": COMPOSITION_BITS,
            "flow_bits": int(selected_valve["flow_bits"]),
            "source_compiled_resources": product[
                "compiled_clean_valve_component_flux"
            ],
            "register_layout": valve_layout,
        },
        "components": components,
        "direct_composition_layout": direct_layout,
        "compiled_clean_product_valve_boundary_balance": resources,
        "accuracy_boundary": "the product-valve quantization is propagated through the same outlet-flux registers used by the reversible boundary balances; pressure/composition are still supplied registers and the one-second screen is evaluated on cached cycle-boundary states",
        "claim_boundary": {
            "supported": "all-to-all u/CX compilation of one clean five-component circuit mapping encoded product-end pressure/composition and nonvalve boundary terms through the product-valve law into five next-gas inventories, followed by exact valve-work uncomputation",
            "unsupported": "reversible composition normalization from gas inventory, direct product-cell LDF composition, valve schedule control, adaptive integration, tank withdrawal, complete phase/cycle, routing, hardware feasibility, or quantum advantage",
        },
    }
    OUT_JSON.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    with OUT_CSV.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(flat_rows[0]))
        writer.writeheader()
        writer.writerows(flat_rows)
    lines = [
        "# Direct product-valve-to-boundary-cell composition",
        "",
        f"The frozen precision screen covers **{len(terms['pressure']):,} product-end states** and **{len(terms['pressure']) * len(COMPONENTS):,} component balances**. The valve is active in **{payload['physical_state_source']['active_valve_states']:,} states**. No QPU job was submitted.",
        "",
        "| Component | nonvalve input bits | valve flux bits | next-gas bits | p95 scaled error | max scaled error | minimum next gas (mol) |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in flat_rows:
        lines.append(
            f"| {row['component']} | {row['input_bits']} | {row['valve_flux_bits']} | {row['next_bits']} | {row['next_p95_scale_error']:.3e} | {row['next_max_scale_error']:.3e} | {row['minimum_next_gas_mol']:.3e} |"
        )
    lines += [
        "",
        f"The clean five-component direct circuit uses **{resources['logical_qubits']:,} logical qubits**, all-to-all depth **{resources['depth_all_to_all']:,}**, and **{resources['cx']:,} CX** in the `u/CX` basis. It retains **{direct_layout['retained_input_output_qubits']:,}** input/output qubits and clears **{direct_layout['cleared_workspace_qubits']:,}** work qubits.",
        "",
        "The circuit computes all five product-valve component fluxes, consumes those exact temporary registers in the product-end material balances, copies five next-gas inventories, and reverses all valve/flux work. Composition normalization, direct product-cell LDF coupling, valve scheduling, adaptive phase integration, tank withdrawal, routing, and a complete cycle remain open.",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": payload["status"],
                "components": len(components),
                "states": len(terms["pressure"]),
                "logical_qubits": resources["logical_qubits"],
                "depth": resources["depth_all_to_all"],
                "cx": resources["cx"],
                "qpu_submission": False,
            },
            indent=2,
        ),
        flush=True,
    )
    del compiled, direct, valve
    gc.collect()


if __name__ == "__main__":
    main()
