"""Compose gas normalization and two-face transport with the coherent controller path.

For each PSA component, this audit starts from three five-component gas-inventory
registers.  Two clean normalizers generate the left and centre compositions, three
pressure modules generate the local pressure triplet, and two oriented face modules
generate the inward/outward component fluxes.  The centre pressure/composition and
the generated fluxes are consumed directly by the coherent run/stage controller,
dynamic run-affinity Langmuir response, q*, schedule-gated LDF update, loading-sign
conversion, and conservative component balance.  All transport and controller
workspace is reversed after copying the next loading and gas inventory.  No QPU job
is submitted.
"""

from __future__ import annotations

import argparse
import csv
import gc
import json

import numpy as np
from qiskit import QuantumCircuit, transpile

from cce_primary_coherent_coefficient_ldf_balance_interface import (
    build_component_circuit,
    component_precision_rows,
    controller_bundle,
    resource_record,
)
from cce_primary_coherent_dynamic_langmuir_ldf_balance_interface import (
    build_dynamic_response_module,
    response_design,
    serializable_design,
)
from cce_primary_coherent_run_schedule_tank_interface import COMPONENTS, RESULTS
from cce_primary_composition_normalized_internal_face_balance import (
    build_composition_normalizer,
)
from cce_primary_internal_face_balance_composition import module_register_map
from cce_primary_internal_transport_reversible_microsteps import (
    build_face_circuit,
    build_pressure_circuit,
)
from cce_primary_joint_normalized_transport_ldf_balance import load_context
from cce_primary_loading_sign_balance_interface import register_indices


OUT_JSON = (
    RESULTS
    / "PSA_QAE_CCE_COHERENT_NORMALIZED_DYNAMIC_TRANSPORT_LDF_BALANCE.json"
)
OUT_CSV = (
    RESULTS
    / "PSA_QAE_CCE_COHERENT_NORMALIZED_DYNAMIC_TRANSPORT_LDF_BALANCE.csv"
)
OUT_MD = (
    RESULTS
    / "PSA_QAE_CCE_COHERENT_NORMALIZED_DYNAMIC_TRANSPORT_LDF_BALANCE.md"
)
CHECKPOINT_JSON = (
    RESULTS
    / "PSA_QAE_CCE_COHERENT_NORMALIZED_DYNAMIC_TRANSPORT_LDF_BALANCE.checkpoint.json"
)
PRIOR_JOINT_JSON = (
    RESULTS / "PSA_QAE_CCE_PRIMARY_JOINT_NORMALIZED_TRANSPORT_LDF_BALANCE.json"
)
AFFINITY_BITS = 8
DENOMINATOR_ADDRESS_BITS = 12
TRANSPILER_SEED = 20261010


def build_normalized_dynamic_component_circuit(
    context,
    component_index: int,
    component_module: QuantumCircuit,
    component_layout: dict,
) -> tuple[QuantumCircuit, dict]:
    """Wrap one coherent component path with generated composition and faces."""

    normalized = context.normalized
    normalizer, normalizer_layout = build_composition_normalizer(
        context.normalization_selected, normalized["selected_pressure"]
    )
    pressure_module, pressure_layout = build_pressure_circuit(
        normalized["selected_pressure"]
    )
    face_module, face_layout = build_face_circuit(normalized["selected_face"])

    gas_width = len(register_indices(pressure_module, "gas_components"))
    pressure_bits = len(register_indices(pressure_module, "pressure"))
    composition_width = len(register_indices(normalizer, "composition"))
    face_width = len(register_indices(face_module, "component_flux"))
    gas_bits = int(normalized["selected_pressure"]["gas_bits_per_component"])
    face_bits = int(normalized["selected_face"]["flow_register_bits"])
    if gas_width != len(register_indices(normalizer, "gas_components")):
        raise AssertionError("normalizer/pressure gas width mismatch")
    if pressure_bits != len(component_layout["pressure_input"]):
        raise AssertionError("pressure width mismatch")
    if composition_width != len(component_layout["composition_input"]):
        raise AssertionError("composition width mismatch")
    if face_width != face_bits * len(COMPONENTS):
        raise AssertionError("face width mismatch")
    if len(component_layout["current_gas_input"]) != gas_bits:
        raise AssertionError("current-gas width mismatch")
    if len(component_layout["left_flux_input"]) != face_bits:
        raise AssertionError("left-face width mismatch")
    if len(component_layout["right_flux_input"]) != face_bits:
        raise AssertionError("right-face width mismatch")

    next_index = 0

    def allocate(size: int) -> list[int]:
        nonlocal next_index
        result = list(range(next_index, next_index + int(size)))
        next_index += int(size)
        return result

    run = allocate(len(component_layout["run_address"]))
    stage = allocate(len(component_layout["stage_address"]))
    bed = allocate(len(component_layout["bed_address"]))
    gas = [allocate(gas_width) for _ in range(3)]
    current_loading = allocate(len(component_layout["current_loading_input"]))
    next_loading = allocate(len(component_layout["next_loading_output"]))
    next_gas = allocate(len(component_layout["next_gas_output"]))

    compositions = [allocate(composition_width) for _ in range(2)]
    normalizer_shared = {
        register.name: allocate(len(register))
        for register in normalizer.qregs
        if register.name not in {"gas_components", "composition"}
    }
    pressures = [allocate(pressure_bits) for _ in range(3)]
    pressure_shared = {
        register.name: allocate(len(register))
        for register in pressure_module.qregs
        if register.name not in {"gas_components", "pressure"}
    }
    face_fluxes = [allocate(face_width) for _ in range(2)]
    face_shared = {
        register.name: allocate(len(register))
        for register in face_module.qregs
        if register.name
        not in {
            "pressure_left",
            "pressure_right",
            "composition_left",
            "component_flux",
        }
    }

    fixed_sources = set(
        component_layout["run_address"]
        + component_layout["stage_address"]
        + component_layout["bed_address"]
        + component_layout["pressure_input"]
        + component_layout["composition_input"]
        + component_layout["current_loading_input"]
        + component_layout["next_loading_output"]
        + component_layout["current_gas_input"]
        + component_layout["left_flux_input"]
        + component_layout["right_flux_input"]
        + component_layout["next_gas_output"]
    )
    if len(fixed_sources) != sum(
        len(component_layout[name])
        for name in (
            "run_address",
            "stage_address",
            "bed_address",
            "pressure_input",
            "composition_input",
            "current_loading_input",
            "next_loading_output",
            "current_gas_input",
            "left_flux_input",
            "right_flux_input",
            "next_gas_output",
        )
    ):
        raise AssertionError("overlapping fixed component registers")
    component_other_sources = [
        index
        for index in range(component_module.num_qubits)
        if index not in fixed_sources
    ]
    component_workspace = allocate(len(component_other_sources))

    component = COMPONENTS[component_index]
    circuit = QuantumCircuit(
        next_index,
        name=f"coherent_normalized_dynamic_transport_{component.lower()}_balance",
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
            {"gas_components": gas[cell], "pressure": pressures[cell]},
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
                "pressure_left": pressures[face],
                "pressure_right": pressures[face + 1],
                "composition_left": compositions[face],
                "component_flux": face_fluxes[face],
            },
            face_shared,
        )
        for face in range(2)
    ]
    for mapping in face_maps:
        circuit.compose(face_module, qubits=mapping, inplace=True)

    component_map = [-1] * component_module.num_qubits
    named_targets = {
        "run_address": run,
        "stage_address": stage,
        "bed_address": bed,
        "pressure_input": pressures[1],
        "composition_input": compositions[1],
        "current_loading_input": current_loading,
        "next_loading_output": next_loading,
        "current_gas_input": gas[1][
            component_index * gas_bits : (component_index + 1) * gas_bits
        ],
        "left_flux_input": face_fluxes[0][
            component_index * face_bits : (component_index + 1) * face_bits
        ],
        "right_flux_input": face_fluxes[1][
            component_index * face_bits : (component_index + 1) * face_bits
        ],
        "next_gas_output": next_gas,
    }
    for name, targets in named_targets.items():
        for source, target in zip(component_layout[name], targets):
            component_map[source] = target
    for source, target in zip(component_other_sources, component_workspace):
        component_map[source] = target
    if any(index < 0 for index in component_map):
        raise AssertionError("incomplete coherent-component map")
    if len(set(component_map)) != len(component_map):
        raise AssertionError("non-injective coherent-component map")
    circuit.compose(component_module, qubits=component_map, inplace=True)

    for mapping in reversed(face_maps):
        circuit.compose(face_module.inverse(), qubits=mapping, inplace=True)
    for mapping in reversed(pressure_maps):
        circuit.compose(pressure_module.inverse(), qubits=mapping, inplace=True)
    for mapping in reversed(normalizer_maps):
        circuit.compose(normalizer.inverse(), qubits=mapping, inplace=True)

    retained = set(
        run
        + stage
        + bed
        + [index for cell in gas for index in cell]
        + current_loading
        + next_loading
        + next_gas
    )
    layout = {
        "component": component,
        "run_address": run,
        "stage_address": stage,
        "bed_address": bed,
        "three_cell_gas_inventory_inputs": gas,
        "current_loading_input": current_loading,
        "next_loading_output": next_loading,
        "next_gas_output": next_gas,
        "temporary_compositions": compositions,
        "temporary_pressures": pressures,
        "temporary_face_fluxes": face_fluxes,
        "retained_input_output_qubits": len(retained),
        "cleared_workspace_qubits": circuit.num_qubits - len(retained),
        "component_module_logical_qubits": component_module.num_qubits,
        "normalizer_layout": normalizer_layout,
        "pressure_layout": pressure_layout,
        "face_layout": face_layout,
        "directly_composed_modules": [
            "two support-adaptive gas-composition normalizers",
            "three gas-inventory pressure reconstructions",
            "two pressure-driven oriented five-component faces",
            "32-run/six-stage controller and coefficient generator",
            "dynamic run-affinity competitive-Langmuir denominator/reciprocal",
            "schedule-gated q*/LDF/loading-sign update",
            "one conservative component balance",
            "exact reverse of controller, transport, and normalization workspace",
        ],
    }
    return circuit, layout


def write_checkpoint(design: dict, compiled: list[dict], layouts: list[dict]) -> None:
    CHECKPOINT_JSON.write_text(
        json.dumps(
            {
                "selected_dynamic_response_design": serializable_design(design),
                "componentwise_compiled_direct_paths": compiled,
                "componentwise_layouts": layouts,
            },
            ensure_ascii=False,
            indent=2,
            default=lambda value: value.item()
            if isinstance(value, np.generic)
            else str(value),
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--screen-only", action="store_true")
    parser.add_argument("--build-only", action="store_true")
    parser.add_argument("--componentwise-compile", action="store_true")
    args = parser.parse_args()
    if sum((args.screen_only, args.build_only, args.componentwise_compile)) > 1:
        parser.error("choose at most one execution mode")

    context = load_context()
    bundle = controller_bundle()
    selected_components = json.loads(PRIOR_JOINT_JSON.read_text(encoding="utf-8"))[
        "selected_components"
    ]
    design = response_design(
        context, bundle, AFFINITY_BITS, DENOMINATOR_ADDRESS_BITS
    )
    precision_rows = component_precision_rows(
        context,
        bundle,
        selected_components,
        response_codes_by_component=design["response_codes"],
    )
    if not all(row["passes_declared_precision_gate"] for row in precision_rows):
        raise AssertionError("dynamic component precision gate failed")

    compiled_rows: list[dict] = []
    layouts: list[dict] = []
    if args.componentwise_compile and CHECKPOINT_JSON.exists():
        checkpoint = json.loads(CHECKPOINT_JSON.read_text(encoding="utf-8"))
        checkpoint_design = checkpoint.get("selected_dynamic_response_design", {})
        if (
            int(checkpoint_design.get("affinity_bits", -1)) == AFFINITY_BITS
            and int(checkpoint_design.get("denominator_address_bits", -1))
            == DENOMINATOR_ADDRESS_BITS
        ):
            compiled_rows = list(
                checkpoint.get("componentwise_compiled_direct_paths", [])
            )
            layouts = list(checkpoint.get("componentwise_layouts", []))

    if args.screen_only:
        component_indices: list[int] = []
    elif args.componentwise_compile:
        complete = {row["component"] for row in compiled_rows}
        component_indices = [
            index
            for index, component in enumerate(COMPONENTS)
            if component not in complete
        ]
    else:
        component_indices = [0]

    build_only_rows: list[dict] = []
    for component_index in component_indices:
        response_module, response_layout = build_dynamic_response_module(
            design, component_index
        )
        component_module, component_layout = build_component_circuit(
            context,
            bundle,
            selected_components,
            component_index,
            response_module=response_module,
            response_module_layout=response_layout,
        )
        circuit, layout = build_normalized_dynamic_component_circuit(
            context, component_index, component_module, component_layout
        )
        if args.build_only:
            build_only_rows.append(
                {
                    "component": COMPONENTS[component_index],
                    "logical_qubits_untranspiled": circuit.num_qubits,
                    "retained_input_output_qubits": layout[
                        "retained_input_output_qubits"
                    ],
                    "cleared_workspace_qubits": layout["cleared_workspace_qubits"],
                }
            )
        else:
            compiled = transpile(
                circuit,
                basis_gates=["u", "cx"],
                optimization_level=1,
                seed_transpiler=TRANSPILER_SEED,
            )
            resources = resource_record(compiled, COMPONENTS[component_index])
            if resources["measurement"] or resources["reset"]:
                raise AssertionError(resources)
            compiled_rows.append(resources)
            layouts.append(layout)
            write_checkpoint(design, compiled_rows, layouts)
            del compiled
        del response_module, component_module, circuit
        gc.collect()

    upper_bound = None
    if compiled_rows:
        upper_bound = {
            "logical_qubits_peak": max(row["logical_qubits"] for row in compiled_rows),
            "depth_all_to_all_additive_upper_bound": sum(
                row["depth_all_to_all"] for row in compiled_rows
            ),
            "cx_additive_upper_bound": sum(row["cx"] for row in compiled_rows),
            "u_additive_upper_bound": sum(row["u"] for row in compiled_rows),
            "common_controller_and_transport_repeated_per_component": True,
            "monolithic_five_component_transpile": False,
        }

    payload = {
        "schema": "psa-qae-cce-coherent-normalized-dynamic-transport-ldf-balance/v1",
        "status": (
            "gas_inventory_to_dynamic_langmuir_ldf_balance_five_component_paths_compiled"
            if len(compiled_rows) == len(COMPONENTS)
            else "gas_inventory_to_dynamic_langmuir_ldf_balance_precision_pass_compile_pending"
        ),
        "qpu_submission": False,
        "support": {
            "runs": 32,
            "physical_records_per_component": int(len(context.current_loading)),
            "component_balance_records_checked": int(
                len(context.current_loading) * len(COMPONENTS)
            ),
            "normalization_states": int(2 * len(context.current_loading)),
            "components": list(COMPONENTS),
        },
        "selected_dynamic_response_design": serializable_design(design),
        "components": precision_rows,
        "componentwise_compiled_direct_paths": compiled_rows,
        "componentwise_layouts": layouts,
        "build_only_rows": build_only_rows,
        "conservative_five_component_upper_bound": upper_bound,
        "register_consistency": {
            "pressure_codes_consumed_from_generated_centre_pressure": True,
            "composition_codes_consumed_from_generated_centre_composition": True,
            "left_and_right_flux_codes_consumed_from_generated_faces": True,
            "normalization_and_face_support_matches_precision_screen": True,
        },
        "cleanliness_by_construction": {
            "retained": [
                "run, stage and bed addresses",
                "three five-component gas-inventory inputs",
                "current loading",
                "next loading and next component gas inventory",
            ],
            "cleared": [
                "two generated compositions, three pressures and two face vectors",
                "normalization reciprocal and transport arithmetic",
                "dynamic Langmuir denominator, reciprocal and response arithmetic",
                "controller, coefficient, q*, LDF, loading-transfer and balance workspace",
            ],
        },
        "claim_boundary": {
            "supported": "direct all-to-all u/CX composition from three raw five-component gas inventories and coherent run/stage control through normalization, pressure reconstruction, two oriented faces, a dynamic run-affinity Langmuir response, schedule-gated LDF/loading conversion, and one conservative component balance",
            "unsupported": "negative-flow switching outside the frozen orientation, out-of-support normalization, continuous off-ledger tank demand, a monolithic five-component transpilation, adaptive phase/cycle integration, routed hardware feasibility, external H2 validation, or quantum advantage",
        },
    }

    RESULTS.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            default=lambda value: value.item()
            if isinstance(value, np.generic)
            else str(value),
        )
        + "\n",
        encoding="utf-8",
    )
    with OUT_CSV.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(precision_rows[0]))
        writer.writeheader()
        writer.writerows(precision_rows)

    lines = [
        "# Coherent gas-inventory-to-dynamic-Langmuir/LDF/balance paths",
        "",
        f"Status: **{payload['status']}**",
        "",
        "Three raw five-component gas inventories now generate both normalized upwind compositions, the pressure triplet, and two oriented face-flux vectors. The centre pressure/composition and component face words feed the coherent run/stage controller, dynamic run-affinity Langmuir response, q*/LDF/loading conversion, and conservative balance directly; all temporary transport and controller registers are reversed.",
        "",
        f"The frozen support contains **{payload['support']['normalization_states']:,} normalization states** and **{payload['support']['component_balance_records_checked']:,} component-balance records**. The dynamic response uses **{AFFINITY_BITS} affinity bits** and **{1 << DENOMINATOR_ADDRESS_BITS:,} reciprocal segments**.",
        "",
        "| component | response p95/max | q* p95/max | LDF-next p95/max | next-gas p95/max | pass |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for row in precision_rows:
        lines.append(
            f"| {row['component']} | "
            f"{row['response_p95_scale_normalized_absolute_error']:.3e}/"
            f"{row['response_max_scale_normalized_absolute_error']:.3e} | "
            f"{row['qstar_p95_loading_scale_normalized_absolute_error']:.3e}/"
            f"{row['qstar_max_loading_scale_normalized_absolute_error']:.3e} | "
            f"{row['ldf_next_p95_loading_scale_normalized_absolute_error']:.3e}/"
            f"{row['ldf_next_max_loading_scale_normalized_absolute_error']:.3e} | "
            f"{row['next_gas_p95_scale_normalized_absolute_error']:.3e}/"
            f"{row['next_gas_max_scale_normalized_absolute_error']:.3e} | "
            f"{row['passes_declared_precision_gate']} |"
        )
    if compiled_rows:
        lines += [
            "",
            "| compiled component path | logical qubits | depth | CX |",
            "|---|---:|---:|---:|",
        ]
        for row in compiled_rows:
            lines.append(
                f"| {row['component']} | {row['logical_qubits']:,} | "
                f"{row['depth_all_to_all']:,} | {row['cx']:,} |"
            )
    if build_only_rows:
        lines += ["", f"Build-only diagnostic: `{build_only_rows}`"]
    lines += [
        "",
        "Continuous off-ledger tank demand, out-of-support flow reversal/normalization, monolithic five-component phase/cycle integration, routing, external H2 validation, and quantum advantage remain open.",
        "",
        "No QPU job was submitted.",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    if len(compiled_rows) == len(COMPONENTS) and CHECKPOINT_JSON.exists():
        CHECKPOINT_JSON.unlink()
    print(
        json.dumps(
            {
                "status": payload["status"],
                "compiled_paths": len(compiled_rows),
                "build_only_paths": len(build_only_rows),
                "qpu_submission": False,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
