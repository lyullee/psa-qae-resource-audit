"""Compile pressure reconstruction and oriented internal-face transport modules.

The physical finite-volume model computes cell pressure from five gas
inventories and moves gas across each internal face according to

    F = k_internal * (P_left - P_right)

with the upstream composition.  The cached source trajectories are stored in
the local flow orientation: every nonzero internal-face flow is left-to-right.
This script therefore compiles two clean, separately verified modules:

1. five encoded gas inventories -> a pressure code; and
2. two pressure codes plus the encoded left-cell composition -> five signed-
   orientation component transfer magnitudes for one second.

The precision screen feeds reconstructed pressure codes into the face module,
so its numerical error includes pressure reconstruction.  The circuits remain
modular because reversible composition normalization from gas inventories,
adsorption/transport accumulation into the next state, adaptive integration,
routing, and a complete phase/cycle are not compiled.  No QPU work is
submitted.
"""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import numpy as np
from qiskit import QuantumCircuit, QuantumRegister, transpile
from qiskit.circuit.library import ModularAdderGate, MultiplierGate, WeightedAdder

from psa_spatial_network_probe_n2 import BAR, COMPONENTS, R, SpatialParams, cell_pressure, cell_y


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RESULTS = ROOT / "10_TEA_LCA_Python" / "results" / "pycharm_publication_enhancement"
CACHE = HERE / "cce_primary_physical_css_horizon_cache.npz"
OUT_JSON = RESULTS / "PSA_QAE_CCE_PRIMARY_INTERNAL_TRANSPORT_MICROSTEPS.json"
OUT_CSV = RESULTS / "PSA_QAE_CCE_PRIMARY_INTERNAL_TRANSPORT_MICROSTEPS.csv"
OUT_MD = RESULTS / "PSA_QAE_CCE_PRIMARY_INTERNAL_TRANSPORT_MICROSTEPS.md"

GAS_BITS = [14, 16, 18, 20]
PRESSURE_BITS = [16, 18, 20]
FLOW_EFFECTIVE_BITS = [22, 24, 26]
COMPOSITION_BITS = [18, 20, 22]

PRESSURE_P95_SCALE_NORMALIZED_GATE = 2.5e-5
PRESSURE_MAX_SCALE_NORMALIZED_GATE = 5.0e-5
FACE_ACTIVE_P95_RELATIVE_GATE = 5.0e-3
FACE_FLUX_P95_FLOW_SCALE_NORMALIZED_GATE = 2.5e-3
TRANSPILER_SEED = 20261009


def physical_states() -> dict[str, np.ndarray]:
    cache = np.load(CACHE)
    boundaries = np.asarray(cache["boundaries"], dtype=float)
    if boundaries.shape != (32, 101, 85):
        raise AssertionError(boundaries.shape)
    params = SpatialParams(
        n_cells=4,
        k_internal_mol_s_bar=5.0,
        k_in_mol_s_bar=1.0,
        k_out_mol_s_bar=1.0,
    )
    gas_rows: list[np.ndarray] = []
    pressure_rows: list[np.ndarray] = []
    composition_rows: list[np.ndarray] = []
    face_left: list[int] = []
    face_right: list[int] = []
    for boundary in boundaries.reshape(-1, 85):
        for offset in (0, 40):
            gas = boundary[offset : offset + 20].reshape(5, 4)
            pressure = cell_pressure(gas, params)
            composition = cell_y(gas).T
            base = len(gas_rows) * 4
            gas_rows.append(gas.T)
            pressure_rows.append(pressure)
            composition_rows.append(composition)
            for face in range(3):
                face_left.append(base + face)
                face_right.append(base + face + 1)
    gas = np.concatenate(gas_rows, axis=0)
    pressure = np.concatenate(pressure_rows, axis=0)
    composition = np.concatenate(composition_rows, axis=0)
    return {
        "gas": gas,
        "pressure": pressure,
        "composition": composition,
        "face_left": np.asarray(face_left, dtype=int),
        "face_right": np.asarray(face_right, dtype=int),
    }


def pressure_row(gas_bits: int, pressure_bits: int, state: dict[str, np.ndarray]) -> dict:
    gas = state["gas"]
    pressure = state["pressure"]
    params = SpatialParams(n_cells=4)
    gas_levels = (1 << gas_bits) - 1
    pressure_levels = (1 << pressure_bits) - 1
    component_scales = np.max(gas, axis=0)
    pressure_scale = float(np.max(pressure))
    pressure_factor = R * params.temperature_K / (params.gas_cell_volume_m3 * BAR)
    gas_code = np.rint(gas / component_scales * gas_levels).astype(np.int64)
    weights = [
        int(
            round(
                component_scales[component] / gas_levels
                * (1 << bit)
                * pressure_factor
                / pressure_scale
                * pressure_levels
            )
        )
        for component in range(len(COMPONENTS))
        for bit in range(gas_bits)
    ]
    pressure_code = np.zeros(len(gas), dtype=np.int64)
    for component in range(len(COMPONENTS)):
        for bit in range(gas_bits):
            pressure_code += (
                (gas_code[:, component] >> bit) & 1
            ) * weights[component * gas_bits + bit]
    pressure_approx = pressure_code / pressure_levels * pressure_scale
    normalized = np.abs(pressure_approx - pressure) / pressure_scale
    erased = (gas > 0.0) & (gas_code == 0)
    output_overflow = pressure_code > pressure_levels
    result = {
        "gas_bits_per_component": gas_bits,
        "pressure_output_bits": pressure_bits,
        "pressure_sum_bits": int(math.ceil(math.log2(sum(weights) + 1))),
        "gas_component_scales_mol": component_scales.tolist(),
        "pressure_scale_bar": pressure_scale,
        "pressure_weights": weights,
        "pressure_p95_scale_normalized_absolute_error": float(np.quantile(normalized, 0.95)),
        "pressure_max_scale_normalized_absolute_error": float(np.max(normalized)),
        "maximum_component_nonzero_erased_fraction": float(np.max(np.mean(erased, axis=0))),
        "physical_pressure_output_overflow_fraction": float(np.mean(output_overflow)),
    }
    result["passes_pressure_precision_gate"] = bool(
        result["pressure_p95_scale_normalized_absolute_error"]
        <= PRESSURE_P95_SCALE_NORMALIZED_GATE
        and result["pressure_max_scale_normalized_absolute_error"]
        <= PRESSURE_MAX_SCALE_NORMALIZED_GATE
        and result["maximum_component_nonzero_erased_fraction"] == 0.0
        and result["physical_pressure_output_overflow_fraction"] == 0.0
    )
    return result


def reconstruct_pressure_codes(selected: dict, state: dict[str, np.ndarray]) -> np.ndarray:
    gas = state["gas"]
    gas_bits = int(selected["gas_bits_per_component"])
    gas_levels = (1 << gas_bits) - 1
    scales = np.asarray(selected["gas_component_scales_mol"], dtype=float)
    gas_code = np.rint(gas / scales * gas_levels).astype(np.int64)
    weights = [int(value) for value in selected["pressure_weights"]]
    pressure_code = np.zeros(len(gas), dtype=np.int64)
    for component in range(len(COMPONENTS)):
        for bit in range(gas_bits):
            pressure_code += (
                (gas_code[:, component] >> bit) & 1
            ) * weights[component * gas_bits + bit]
    return pressure_code


def face_row(
    pressure_candidate: dict,
    flow_effective_bits: int,
    composition_bits: int,
    state: dict[str, np.ndarray],
) -> dict:
    params = SpatialParams(n_cells=4, k_internal_mol_s_bar=5.0)
    pressure = state["pressure"]
    composition = state["composition"]
    left = state["face_left"]
    right = state["face_right"]
    exact_flow = params.k_internal_mol_s_bar * (pressure[left] - pressure[right])
    exact_upwind = np.where(exact_flow[:, None] >= 0.0, composition[left], composition[right])
    exact_flux = exact_flow[:, None] * exact_upwind
    negative = exact_flow < 0.0
    active = exact_flow > 0.0
    pressure_codes = reconstruct_pressure_codes(pressure_candidate, state)
    left_code = pressure_codes[left]
    right_code = pressure_codes[right]
    difference_code = left_code - right_code
    pressure_bits = int(pressure_candidate["pressure_output_bits"])
    pressure_levels = (1 << pressure_bits) - 1
    pressure_scale = float(pressure_candidate["pressure_scale_bar"])
    flow_scale = float(np.max(np.abs(exact_flow)))
    flow_levels = (1 << flow_effective_bits) - 1
    flow_gain = (
        flow_levels
        * params.k_internal_mol_s_bar
        * pressure_scale
        / (pressure_levels * flow_scale)
    )
    flow_weights = [int(round(flow_gain * (1 << bit))) for bit in range(pressure_bits)]
    flow_code = np.zeros(len(difference_code), dtype=np.int64)
    for bit, weight in enumerate(flow_weights):
        flow_code += ((difference_code >> bit) & 1) * weight
    flow_register_bits = int(math.ceil(math.log2(sum(flow_weights) + 1)))
    flow_approx = flow_code / flow_levels * flow_scale
    composition_levels = (1 << composition_bits) - 1
    composition_code = np.rint(exact_upwind * composition_levels).astype(np.int64)
    flux_code = np.empty_like(composition_code)
    for component in range(len(COMPONENTS)):
        flux_code[:, component] = (
            flow_code * composition_code[:, component]
        ) >> composition_bits
    flux_approx = flux_code / flow_levels * flow_scale
    active_relative = np.abs(flow_approx[active] - exact_flow[active]) / exact_flow[active]
    component_metrics = []
    for component_index, component in enumerate(COMPONENTS):
        normalized = (
            np.abs(flux_approx[:, component_index] - exact_flux[:, component_index])
            / flow_scale
        )
        erased = (exact_flux[:, component_index] > 0.0) & (
            flux_code[:, component_index] == 0
        )
        component_metrics.append(
            {
                "component": component,
                "flux_p95_flow_scale_normalized_absolute_error": float(
                    np.quantile(normalized, 0.95)
                ),
                "nonzero_flux_erased_fraction": float(np.mean(erased)),
            }
        )
    result = {
        "gas_bits_per_component": int(pressure_candidate["gas_bits_per_component"]),
        "pressure_bits": pressure_bits,
        "flow_effective_bits": flow_effective_bits,
        "flow_register_bits": flow_register_bits,
        "composition_bits_per_component": composition_bits,
        "flow_scale_mol_s": flow_scale,
        "flow_weights": flow_weights,
        "negative_exact_face_count": int(np.sum(negative)),
        "zero_exact_face_count": int(np.sum(exact_flow == 0.0)),
        "positive_exact_face_count": int(np.sum(active)),
        "reconstructed_pressure_difference_underflow_fraction": float(
            np.mean(difference_code < 0)
        ),
        "active_label_mismatch_fraction": float(np.mean((flow_approx > 0.0) != active)),
        "active_flow_p95_relative_error": float(np.quantile(active_relative, 0.95)),
        "flow_p95_scale_normalized_absolute_error": float(
            np.quantile(np.abs(flow_approx - exact_flow) / flow_scale, 0.95)
        ),
        "component_metrics": component_metrics,
    }
    result["passes_oriented_face_precision_gate"] = bool(
        pressure_candidate["passes_pressure_precision_gate"]
        and result["negative_exact_face_count"] == 0
        and result["reconstructed_pressure_difference_underflow_fraction"] == 0.0
        and result["active_label_mismatch_fraction"] == 0.0
        and result["active_flow_p95_relative_error"] <= FACE_ACTIVE_P95_RELATIVE_GATE
        and max(
            metric["flux_p95_flow_scale_normalized_absolute_error"]
            for metric in component_metrics
        )
        <= FACE_FLUX_P95_FLOW_SCALE_NORMALIZED_GATE
        and max(metric["nonzero_flux_erased_fraction"] for metric in component_metrics)
        == 0.0
    )
    return result


def build_pressure_circuit(selected: dict) -> tuple[QuantumCircuit, dict]:
    gas_bits = int(selected["gas_bits_per_component"])
    pressure_bits = int(selected["pressure_output_bits"])
    weights = [int(value) for value in selected["pressure_weights"]]
    adder = WeightedAdder(len(weights), weights)
    gas_reg = QuantumRegister(len(weights), "gas_components")
    sum_reg = QuantumRegister(adder.num_sum_qubits, "pressure_sum")
    work_reg = QuantumRegister(adder.num_ancillas, "work")
    pressure_reg = QuantumRegister(pressure_bits, "pressure")
    circuit = QuantumCircuit(gas_reg, sum_reg, work_reg, pressure_reg, name="clean_pressure_from_gas")
    qargs = list(gas_reg) + list(sum_reg) + list(work_reg)
    circuit.append(adder, qargs)
    for source, target in zip(list(sum_reg)[:pressure_bits], pressure_reg):
        circuit.cx(source, target)
    circuit.append(adder.inverse(), qargs)
    return circuit, {
        "retained_input": f"5 x {gas_bits}-bit component gas inventories",
        "clean_output": f"{pressure_bits}-bit pressure code",
        "cleared": ["weighted pressure sum", "weighted-adder workspace"],
        "physical_output_overflow_fraction": selected[
            "physical_pressure_output_overflow_fraction"
        ],
    }


def build_face_circuit(selected: dict) -> tuple[QuantumCircuit, dict]:
    pressure_bits = int(selected["pressure_bits"])
    composition_bits = int(selected["composition_bits_per_component"])
    flow_bits = int(selected["flow_register_bits"])
    flow_weights = [int(value) for value in selected["flow_weights"]]
    flow_adder = WeightedAdder(pressure_bits, flow_weights)
    pressure_left = QuantumRegister(pressure_bits, "pressure_left")
    pressure_right = QuantumRegister(pressure_bits, "pressure_right")
    composition_left = QuantumRegister(
        len(COMPONENTS) * composition_bits, "composition_left"
    )
    difference = QuantumRegister(pressure_bits, "pressure_difference")
    flow = QuantumRegister(flow_adder.num_sum_qubits, "face_flow")
    work = QuantumRegister(
        max(flow_adder.num_ancillas, flow_bits - composition_bits), "work"
    )
    product = QuantumRegister(flow_bits + composition_bits, "flow_times_y")
    flux = QuantumRegister(len(COMPONENTS) * flow_bits, "component_flux")
    circuit = QuantumCircuit(
        pressure_left,
        pressure_right,
        composition_left,
        difference,
        flow,
        work,
        product,
        flux,
        name="clean_oriented_internal_face_component_flux",
    )
    for source, target in zip(pressure_left, difference):
        circuit.cx(source, target)
    subtract = ModularAdderGate(pressure_bits).inverse()
    circuit.append(subtract, list(pressure_right) + list(difference))
    flow_qargs = (
        list(difference)
        + list(flow)
        + list(work)[: flow_adder.num_ancillas]
    )
    circuit.append(flow_adder, flow_qargs)
    multiplier = MultiplierGate(flow_bits, flow_bits + composition_bits)
    padding = list(work)[: flow_bits - composition_bits]
    for component in range(len(COMPONENTS)):
        y = list(composition_left)[
            component * composition_bits : (component + 1) * composition_bits
        ]
        qargs = list(flow) + y + padding + list(product)
        circuit.append(multiplier, qargs)
        high_product = list(product)[composition_bits : composition_bits + flow_bits]
        output = list(flux)[component * flow_bits : (component + 1) * flow_bits]
        for source, target in zip(high_product, output):
            circuit.cx(source, target)
        circuit.append(multiplier.inverse(), qargs)
    circuit.append(flow_adder.inverse(), flow_qargs)
    circuit.append(ModularAdderGate(pressure_bits), list(pressure_right) + list(difference))
    for source, target in zip(pressure_left, difference):
        circuit.cx(source, target)
    return circuit, {
        "retained_inputs": [
            f"2 x {pressure_bits}-bit reconstructed pressure",
            f"5 x {composition_bits}-bit left/upwind composition",
        ],
        "clean_outputs": f"5 x {flow_bits}-bit one-second oriented component transfer",
        "cleared": [
            "pressure difference",
            "flow weighted sum",
            "multiplier product",
            "shared workspace",
        ],
        "orientation_support": "all 19,392 cached faces are zero or left-to-right in the source model's local flow coordinate",
    }


def compile_clean(circuit: QuantumCircuit) -> dict:
    compiled = transpile(
        circuit,
        basis_gates=["u", "cx"],
        optimization_level=1,
        seed_transpiler=TRANSPILER_SEED,
    )
    counts = compiled.count_ops()
    return {
        "logical_qubits": circuit.num_qubits,
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
    state = physical_states()
    pressure_rows = [
        pressure_row(gas_bits, pressure_bits, state)
        for gas_bits in GAS_BITS
        for pressure_bits in PRESSURE_BITS
    ]
    face_rows: list[dict] = []
    selected_pressure = None
    selected_face = None
    for pressure_candidate in pressure_rows:
        if not pressure_candidate["passes_pressure_precision_gate"]:
            continue
        for flow_bits in FLOW_EFFECTIVE_BITS:
            for composition_bits in COMPOSITION_BITS:
                row = face_row(
                    pressure_candidate,
                    flow_bits,
                    composition_bits,
                    state,
                )
                face_rows.append(row)
                if selected_face is None and row["passes_oriented_face_precision_gate"]:
                    selected_pressure = pressure_candidate
                    selected_face = row
    if selected_pressure is None or selected_face is None:
        raise RuntimeError("no pressure/face precision tier passed")

    pressure_circuit, pressure_layout = build_pressure_circuit(selected_pressure)
    face_circuit, face_layout = build_face_circuit(selected_face)
    pressure_resources = compile_clean(pressure_circuit)
    print(
        json.dumps(
            {
                "module": "pressure_from_five_component_gas",
                "gas_bits": selected_pressure["gas_bits_per_component"],
                "pressure_bits": selected_pressure["pressure_output_bits"],
                "logical_qubits": pressure_resources["logical_qubits"],
                "cx": pressure_resources["cx"],
            }
        ),
        flush=True,
    )
    face_resources = compile_clean(face_circuit)
    print(
        json.dumps(
            {
                "module": "oriented_internal_face_component_flux",
                "pressure_bits": selected_face["pressure_bits"],
                "composition_bits": selected_face["composition_bits_per_component"],
                "logical_qubits": face_resources["logical_qubits"],
                "cx": face_resources["cx"],
            }
        ),
        flush=True,
    )

    pressure_workspace = (
        pressure_resources["logical_qubits"]
        - len(COMPONENTS) * int(selected_pressure["gas_bits_per_component"])
        - int(selected_pressure["pressure_output_bits"])
    )
    face_input_output = (
        2 * int(selected_face["pressure_bits"])
        + len(COMPONENTS) * int(selected_face["composition_bits_per_component"])
        + len(COMPONENTS) * int(selected_face["flow_register_bits"])
    )
    face_workspace = face_resources["logical_qubits"] - face_input_output
    retained = (
        2 * len(COMPONENTS) * int(selected_pressure["gas_bits_per_component"])
        + len(COMPONENTS) * int(selected_face["composition_bits_per_component"])
        + 2 * int(selected_face["pressure_bits"])
        + len(COMPONENTS) * int(selected_face["flow_register_bits"])
    )
    modular = {
        "accounting": "two clean pressure modules executed sequentially with retained gas/pressure registers, followed by one clean oriented-face module with separately supplied upwind composition",
        "logical_qubits": retained + max(pressure_workspace, face_workspace),
        "retained_gas_composition_pressure_flux_qubits": retained,
        "shared_workspace_qubits": max(pressure_workspace, face_workspace),
        "cx_additive_module_bound": 2 * pressure_resources["cx"] + face_resources["cx"],
        "depth_all_to_all_additive_module_bound": 2
        * pressure_resources["depth_all_to_all"]
        + face_resources["depth_all_to_all"],
        "interpretation": "modular physical-support accounting, not a monolithic transpilation; reversible composition normalization and next-state accumulation remain open",
    }
    payload = {
        "schema": "psa-qae-cce-primary-internal-transport-microsteps/v1",
        "status": "pressure_reconstruction_and_oriented_internal_face_transport_compiled_composition_normalization_phase_cycle_open",
        "qpu_submission": False,
        "physical_state_source": {
            "cell_states": int(len(state["gas"])),
            "internal_faces": int(len(state["face_left"])),
            "pressure_range_bar": [
                float(np.min(state["pressure"])),
                float(np.max(state["pressure"])),
            ],
        },
        "pressure_precision_gate": {
            "p95_pressure_scale_normalized_absolute_error_max": PRESSURE_P95_SCALE_NORMALIZED_GATE,
            "max_pressure_scale_normalized_absolute_error_max": PRESSURE_MAX_SCALE_NORMALIZED_GATE,
            "nonzero_component_erased_fraction_required": 0.0,
            "physical_output_overflow_fraction_required": 0.0,
        },
        "pressure_rows": pressure_rows,
        "selected_pressure": selected_pressure,
        "pressure_register_layout": pressure_layout,
        "compiled_clean_pressure_reconstruction": pressure_resources,
        "face_precision_gate": {
            "negative_exact_face_count_required": 0,
            "active_label_mismatch_fraction_required": 0.0,
            "active_flow_p95_relative_error_max": FACE_ACTIVE_P95_RELATIVE_GATE,
            "component_flux_p95_flow_scale_normalized_absolute_error_max": FACE_FLUX_P95_FLOW_SCALE_NORMALIZED_GATE,
            "nonzero_flux_erased_fraction_required": 0.0,
        },
        "face_rows": face_rows,
        "selected_face": selected_face,
        "face_register_layout": face_layout,
        "compiled_clean_oriented_internal_face_transport": face_resources,
        "pressure_to_face_modular_accounting": modular,
        "claim_boundary": {
            "supported": "five gas inventories to a clean pressure code and reconstructed-pressure-driven five-component transfer across one locally oriented internal face over the cached physical support",
            "unsupported": "negative-flow upwind switching outside the oriented support, reversible composition normalization from gas inventories, accumulation into next gas states, adsorption coupling, boundary valves/tank withdrawal in the same circuit, adaptive integration, monolithic phase/cycle, routing, hardware feasibility, or quantum advantage",
        },
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    csv_rows = []
    for row in pressure_rows:
        csv_rows.append(
            {
                "module": "pressure",
                "gas_bits": row["gas_bits_per_component"],
                "pressure_bits": row["pressure_output_bits"],
                "flow_effective_bits": "",
                "composition_bits": "",
                "register_bits": row["pressure_sum_bits"],
                "p95_primary_error": row[
                    "pressure_p95_scale_normalized_absolute_error"
                ],
                "p95_secondary_error": row[
                    "pressure_max_scale_normalized_absolute_error"
                ],
                "erasure_fraction": row[
                    "maximum_component_nonzero_erased_fraction"
                ],
                "passes": row["passes_pressure_precision_gate"],
            }
        )
    for row in face_rows:
        csv_rows.append(
            {
                "module": "oriented_face",
                "gas_bits": row["gas_bits_per_component"],
                "pressure_bits": row["pressure_bits"],
                "flow_effective_bits": row["flow_effective_bits"],
                "composition_bits": row["composition_bits_per_component"],
                "register_bits": row["flow_register_bits"],
                "p95_primary_error": row["active_flow_p95_relative_error"],
                "p95_secondary_error": max(
                    metric[
                        "flux_p95_flow_scale_normalized_absolute_error"
                    ]
                    for metric in row["component_metrics"]
                ),
                "erasure_fraction": max(
                    metric["nonzero_flux_erased_fraction"]
                    for metric in row["component_metrics"]
                ),
                "passes": row["passes_oriented_face_precision_gate"],
            }
        )
    with OUT_CSV.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(csv_rows[0]))
        writer.writeheader()
        writer.writerows(csv_rows)
    max_flux_error = max(
        metric["flux_p95_flow_scale_normalized_absolute_error"]
        for metric in selected_face["component_metrics"]
    )
    lines = [
        "# Pressure reconstruction and oriented internal-face transport",
        "",
        f"The physical cache contains **{len(state['gas']):,} cell states** and **{len(state['face_left']):,} internal faces**. In the source model's local flow coordinate, {selected_face['positive_exact_face_count']:,} faces are positive, {selected_face['zero_exact_face_count']:,} are zero, and no face is negative.",
        "",
        f"The first combined precision tier uses **{selected_pressure['gas_bits_per_component']}-bit component gas inventories**, a **{selected_pressure['pressure_output_bits']}-bit pressure output**, **{selected_face['flow_effective_bits']} effective flow bits**, and **{selected_face['composition_bits_per_component']}-bit upwind composition**. Pressure p95 scale-normalized error is **{selected_pressure['pressure_p95_scale_normalized_absolute_error']:.3e}**. The face-flow p95 relative error is **{selected_face['active_flow_p95_relative_error']:.3e}**; the largest component-flux p95 flow-scale-normalized error is **{max_flux_error:.3e}**, with zero active-label mismatch, pressure-difference underflow, and nonzero-flux erasure.",
        "",
        f"The clean pressure circuit uses **{pressure_resources['logical_qubits']} logical qubits**, depth **{pressure_resources['depth_all_to_all']:,}**, and **{pressure_resources['cx']:,} CX**. The clean oriented-face circuit uses **{face_resources['logical_qubits']} logical qubits**, depth **{face_resources['depth_all_to_all']:,}**, and **{face_resources['cx']:,} CX**.",
        "",
        f"Sequential modular accounting for two pressure calculations followed by one face transfer is **{modular['logical_qubits']} qubits** and **{modular['cx_additive_module_bound']:,} additive CX**. Composition is still supplied as a separate encoded input; normalization from gas inventories, next-state accumulation, adsorption coupling, adaptive integration, routing, and a complete phase/cycle remain open.",
        "",
        "No QPU job was submitted.",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": payload["status"],
                "pressure_logical_qubits": pressure_resources["logical_qubits"],
                "pressure_cx": pressure_resources["cx"],
                "face_logical_qubits": face_resources["logical_qubits"],
                "face_cx": face_resources["cx"],
                "modular_logical_qubits": modular["logical_qubits"],
                "modular_cx": modular["cx_additive_module_bound"],
                "qpu_submission": False,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
