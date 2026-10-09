"""Compose widened LDF outputs directly into loading-sign/cell-balance circuits.

The standalone five-component competitive-Langmuir/LDF audit selected loading
register widths for equilibrium/loading accuracy.  The later balance interface
showed that the smaller signed difference ``q_next - q_current`` requires wider
registers.  This script recompiles each LDF microstep at the interface width and
maps its retained current/next loading registers directly into the reversible
sign extraction, solid-mass conversion, and interior-cell gas balance.

For a clean oracle boundary the composed circuit then reverses the loading-sign
conversion and the complete LDF microstep, retaining only pressure/composition,
current loading, current/face gas inputs, and next gas.  Face-flux generation,
composition normalization, run-specific parameter registers, boundary-cell
withdrawal, phase integration, routing, and hardware execution remain outside
the circuit.  No QPU work is submitted.
"""

from __future__ import annotations

import csv
import gc
import json
from pathlib import Path

from qiskit import QuantumCircuit, transpile

from cce_primary_cell_balance_reversible_microsteps import build_clean_balance
from cce_primary_loading_sign_balance_interface import (
    CELL_JSON,
    LDF_JSON,
    RESULTS,
    build_loading_to_terms,
    register_indices,
)
from cce_primary_qstar_ldf_reversible_microstep import (
    COMPONENTS,
    TRANSPILER_SEED,
    build_clean_microstep,
    build_preparation,
    integer_inputs,
    physical_constants,
    precision_row,
)
from cce_primary_all_component_ldf_reversible_microsteps import (
    SCALE_NORMALIZED_P95_GATE,
    physical_states_all,
)


HERE = Path(__file__).resolve().parent
SIGN_JSON = RESULTS / "PSA_QAE_CCE_PRIMARY_LOADING_SIGN_BALANCE_INTERFACE.json"
OUT_JSON = RESULTS / "PSA_QAE_CCE_PRIMARY_LDF_SIGN_BALANCE_COMPOSITION.json"
OUT_CSV = RESULTS / "PSA_QAE_CCE_PRIMARY_LDF_SIGN_BALANCE_COMPOSITION.csv"
OUT_MD = RESULTS / "PSA_QAE_CCE_PRIMARY_LDF_SIGN_BALANCE_COMPOSITION.md"


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


def passes_component_ldf_gate(component: str, row: dict) -> bool:
    return bool(
        row["qstar_p95_loading_scale_normalized_absolute_error"]
        <= SCALE_NORMALIZED_P95_GATE
        and row["ldf_next_p95_loading_scale_normalized_absolute_error"]
        <= SCALE_NORMALIZED_P95_GATE
        and row["nonzero_qstar_erased_fraction"] == 0.0
        and row["loading_input_overflow_fraction"] == 0.0
        and (component != "CO2" or row["passes_declared_precision_gate"])
    )


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


def build_direct_composition(
    ldf: QuantumCircuit,
    ldf_preparation_layout: dict,
    transfer: QuantumCircuit,
    transfer_layout: dict,
    cell_selected: dict,
    component: str,
) -> tuple[QuantumCircuit, dict]:
    """Return LDF -> sign/solid conversion -> balance -> exact reverse."""

    slug = component.lower()
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
    next_index = ldf.num_qubits
    for index in range(transfer.num_qubits):
        if transfer_map[index] < 0:
            transfer_map[index] = next_index
            next_index += 1

    transfer_terms = {
        name: [transfer_map[index] for index in register_indices(transfer, name)]
        for name in ("desorption_term", "adsorption_term")
    }
    cell, _ = build_clean_balance(cell_selected)
    cell_map = [-1] * cell.num_qubits
    for register in cell.qregs:
        source = [cell.find_bit(qubit).index for qubit in register]
        if register.name in {"desorption", "adsorption"}:
            map_register(
                cell_map,
                source,
                transfer_terms[f"{register.name}_term"],
                register.name,
            )
        else:
            for index in source:
                cell_map[index] = next_index
                next_index += 1
    if any(index < 0 for index in transfer_map + cell_map):
        raise AssertionError("incomplete direct-composition mapping")

    circuit = QuantumCircuit(
        next_index,
        name=f"clean_{slug}_ldf_sign_cell_balance",
    )
    ldf_map = list(range(ldf.num_qubits))
    circuit.compose(ldf, qubits=ldf_map, inplace=True)
    circuit.compose(transfer, qubits=transfer_map, inplace=True)
    circuit.compose(cell, qubits=cell_map, inplace=True)
    circuit.compose(transfer.inverse(), qubits=transfer_map, inplace=True)
    circuit.compose(ldf.inverse(), qubits=ldf_map, inplace=True)

    process_inputs = sorted(
        set(
            int(index)
            for name in ("pressure", "composition")
            for index in ldf_preparation_layout[name]
        )
    )
    gas_face_inputs = {
        name: [cell_map[index] for index in register_indices(cell, name)]
        for name in ("current_gas", "left_influx", "right_outflux")
    }
    next_gas = [cell_map[index] for index in register_indices(cell, "next_gas")]
    retained = sorted(
        set(
            process_inputs
            + ldf_current
            + [index for values in gas_face_inputs.values() for index in values]
            + next_gas
        )
    )
    if set(ldf_next) & set(retained):
        raise AssertionError("the temporary next-loading register must be uncomputed")
    return circuit, {
        "process_pressure_composition_inputs": process_inputs,
        "current_loading_input": ldf_current,
        "temporary_next_loading": ldf_next,
        "gas_and_face_inputs": gas_face_inputs,
        "next_gas_output": next_gas,
        "retained_input_output_qubits": len(retained),
        "cleared_workspace_qubits": circuit.num_qubits - len(retained),
        "directly_composed_modules": [
            "competitive-Langmuir denominator, reciprocal, q*, and one-second LDF update",
            "loading sign and magnitude extraction",
            "solid-mass loading-to-gas conversion",
            "interior-cell current/left/right/adsorption/desorption balance",
            "exact reverse of conversion and LDF work",
        ],
    }


def main() -> None:
    prior_ldf = json.loads(LDF_JSON.read_text(encoding="utf-8"))
    sign = json.loads(SIGN_JSON.read_text(encoding="utf-8"))
    cell = json.loads(CELL_JSON.read_text(encoding="utf-8"))
    pressure, composition, loadings = physical_states_all()
    constants = physical_constants()

    components: list[dict] = []
    flat_rows: list[dict] = []
    for component_index, component in enumerate(COMPONENTS):
        prior_component = prior_ldf["components"][component_index]
        sign_component = sign["components"][component_index]
        cell_component = cell["components"][component_index]
        target_bits = int(sign_component["selected"]["loading_bits"])
        address_bits = int(
            prior_component["selected"]["denominator_address_bits"]
        )
        encoded = integer_inputs(
            pressure,
            composition,
            constants,
            component_index,
        )
        selected = precision_row(
            target_bits,
            address_bits,
            pressure,
            composition,
            loadings[:, component_index],
            constants,
            encoded,
            component_index,
        )
        selected["passes_all_component_precision_gate"] = (
            passes_component_ldf_gate(component, selected)
        )
        if not selected["passes_all_component_precision_gate"]:
            raise AssertionError((component, selected))
        expected_scale = float(sign_component["selected"]["loading_scale_mol_per_kg"])
        if abs(float(selected["loading_scale_mol_per_kg"]) - expected_scale) > 1.0e-12:
            raise AssertionError(
                (component, selected["loading_scale_mol_per_kg"], expected_scale)
            )

        ldf, ldf_layout = build_clean_microstep(
            constants,
            encoded,
            selected,
            component_index,
        )
        preparation, preparation_layout = build_preparation(
            constants,
            encoded,
            component_index,
        )
        if preparation.num_qubits > ldf.num_qubits:
            raise AssertionError("preparation cannot exceed the clean LDF circuit")
        del preparation

        compiled_ldf = transpile(
            ldf,
            basis_gates=["u", "cx"],
            optimization_level=1,
            seed_transpiler=TRANSPILER_SEED,
        )
        ldf_resources = resource_record(compiled_ldf)
        del compiled_ldf
        gc.collect()

        transfer, transfer_layout = build_loading_to_terms(
            sign_component["selected"]
        )
        composed, composed_layout = build_direct_composition(
            ldf,
            preparation_layout,
            transfer,
            transfer_layout,
            cell_component["selected"],
            component,
        )
        compiled = transpile(
            composed,
            basis_gates=["u", "cx"],
            optimization_level=1,
            seed_transpiler=TRANSPILER_SEED,
        )
        resources = resource_record(compiled)
        additive_reference = (
            2 * int(ldf_resources["cx"])
            + int(
                sign_component["compiled_integrated_loading_sign_cell_balance"][
                    "cx"
                ]
            )
        )
        if resources["measurement"] or resources["reset"]:
            raise AssertionError((component, resources))
        result = {
            "component": component,
            "component_index": component_index,
            "previous_standalone_loading_bits": int(
                prior_component["selected"]["arithmetic_bits"]
            ),
            "register_compatible_loading_bits": target_bits,
            "denominator_address_bits": address_bits,
            "widened_ldf_precision": selected,
            "widened_ldf_layout": ldf_layout,
            "compiled_widened_clean_ldf_microstep": ldf_resources,
            "direct_composition_layout": composed_layout,
            "compiled_clean_ldf_sign_cell_balance": resources,
            "separate_module_additive_cx_reference": additive_reference,
            "direct_minus_additive_cx": int(resources["cx"] - additive_reference),
        }
        components.append(result)
        flat_rows.append(
            {
                "component": component,
                "old_bits": result["previous_standalone_loading_bits"],
                "compatible_bits": target_bits,
                "address_bits": address_bits,
                "ldf_qstar_p95_scale_error": selected[
                    "qstar_p95_loading_scale_normalized_absolute_error"
                ],
                "ldf_next_p95_scale_error": selected[
                    "ldf_next_p95_loading_scale_normalized_absolute_error"
                ],
                "widened_ldf_qubits": ldf_resources["logical_qubits"],
                "widened_ldf_cx": ldf_resources["cx"],
                "composed_qubits": resources["logical_qubits"],
                "composed_depth": resources["depth_all_to_all"],
                "composed_cx": resources["cx"],
                "direct_minus_additive_cx": result["direct_minus_additive_cx"],
            }
        )
        print(
            json.dumps(
                {
                    "component": component,
                    "bits": target_bits,
                    "widened_ldf_cx": ldf_resources["cx"],
                    "composed_qubits": resources["logical_qubits"],
                    "composed_cx": resources["cx"],
                }
            ),
            flush=True,
        )
        del compiled, composed, transfer, ldf
        gc.collect()

    process_input_count = len(
        components[0]["direct_composition_layout"][
            "process_pressure_composition_inputs"
        ]
    )
    if any(
        len(row["direct_composition_layout"]["process_pressure_composition_inputs"])
        != process_input_count
        for row in components
    ):
        raise AssertionError("process input width differs across components")
    retained_each = [
        int(row["direct_composition_layout"]["retained_input_output_qubits"])
        for row in components
    ]
    shared_workspace = max(
        int(row["compiled_clean_ldf_sign_cell_balance"]["logical_qubits"])
        - retained
        for row, retained in zip(components, retained_each)
    )
    retained_all = process_input_count + sum(
        retained - process_input_count for retained in retained_each
    )
    sequential = {
        "accounting": "five directly composed clean component modules executed sequentially with one shared pressure/composition input, all component loading/gas/face inputs and next-gas outputs retained, and arithmetic workspace reused",
        "logical_qubits": retained_all + shared_workspace,
        "shared_process_pressure_composition_input_qubits": process_input_count,
        "retained_input_output_qubits": retained_all,
        "shared_workspace_qubits": shared_workspace,
        "depth_all_to_all_additive_module_bound": sum(
            int(row["compiled_clean_ldf_sign_cell_balance"]["depth_all_to_all"])
            for row in components
        ),
        "cx_additive_module_bound": sum(
            int(row["compiled_clean_ldf_sign_cell_balance"]["cx"])
            for row in components
        ),
        "u_additive_module_bound": sum(
            int(row["compiled_clean_ldf_sign_cell_balance"]["u"])
            for row in components
        ),
    }
    payload = {
        "schema": "psa-qae-cce-primary-ldf-sign-balance-composition/v1",
        "status": "five_component_register_compatible_ldf_sign_balance_composed_face_normalization_phase_open",
        "qpu_submission": False,
        "physical_state_source": {
            "runs": 32,
            "cycles_per_run": 100,
            "beds": 2,
            "cells_per_bed": 4,
            "ldf_precision_cell_states": int(len(pressure)),
            "balance_interface_component_samples": int(
                sign["physical_state_source"]["component_balance_samples"]
            ),
        },
        "components": components,
        "sequential_five_component_accounting": sequential,
        "register_interface_finding": "recompiling the standalone LDF microsteps at the loading-sign widths removes the current/next loading-register mismatch and permits direct clean circuit composition; it also exposes the cost of preserving the smaller loading difference",
        "accuracy_boundary": "the widened LDF precision screen and the loading-sign/cell-balance precision screen are both passed on the frozen physical cache, but the LDF arithmetic remains constant-specialized rather than driven by reversible run-specific capacity, affinity, and kinetic parameter registers",
        "claim_boundary": {
            "supported": "all-to-all u/CX compilation of clean, register-compatible one-cell one-second LDF-to-loading-sign-to-solid-conversion-to-interior-cell-balance modules for all five components",
            "unsupported": "direct oriented-face generation and composition normalization, reversible run-specific LDF parameters, boundary-cell valve/tank withdrawal, adaptive phase integration, a complete phase/cycle, routing, hardware feasibility, or quantum advantage",
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
        "# Direct LDF-to-loading-sign-to-cell-balance composition",
        "",
        f"The widened LDF precision screen covers **{len(pressure):,}** physical cell states. The downstream balance interface covers **{sign['physical_state_source']['component_balance_samples']:,}** component balances. No QPU job was submitted.",
        "",
        "| Component | old bits | compatible bits | address bits | widened LDF qubits | widened LDF CX | composed qubits | composed depth | composed CX |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in flat_rows:
        lines.append(
            f"| {row['component']} | {row['old_bits']} | {row['compatible_bits']} | {row['address_bits']} | "
            f"{row['widened_ldf_qubits']:,} | {row['widened_ldf_cx']:,} | {row['composed_qubits']:,} | "
            f"{row['composed_depth']:,} | {row['composed_cx']:,} |"
        )
    lines += [
        "",
        f"With one shared pressure/composition input and sequential component workspace reuse, the five-component accounting is **{sequential['logical_qubits']:,} logical qubits**, **{sequential['cx_additive_module_bound']:,} additive CX**, and additive all-to-all depth **{sequential['depth_all_to_all_additive_module_bound']:,}**.",
        "",
        "The circuit maps each widened LDF current/next-loading register directly into sign extraction, solid-mass conversion, and conservative next-gas accumulation, then reverses the conversion and LDF work. Face-flux generation, composition normalization, reversible run-specific parameters, boundary withdrawal, adaptive integration, routing, and the complete phase/cycle remain open.",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": payload["status"],
                "components": len(components),
                "logical_qubits": sequential["logical_qubits"],
                "additive_cx": sequential["cx_additive_module_bound"],
                "qpu_submission": False,
            },
            indent=2,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
