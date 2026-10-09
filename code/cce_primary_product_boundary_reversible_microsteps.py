"""Compile reversible product-boundary valve/flux and tank-ledger modules.

The first module starts from the primary model's encoded product-end pressure
and five-component gas composition.  It evaluates the actual boundary law

    F_out = k_out * max(P_product - P_back, 0)

with a piecewise-constant pressure QROM, multiplies the flow by every component
fraction, copies five one-second component-flux outputs, and uncomputes all
work registers.

The second module implements the fixed 0.420 product split used by the primary
policy, copies recycle and external-product amounts, forms a product-tank
candidate, and uncomputes the weighted sums.  A separate clean vector block
sums all five candidate tank components and copies the capacity flag.  The
precision screen uses the 64 final-cycle product/recycle records.

These modules do not compose the valve flux through adaptive phase integration
into the integrated product record.  Internal face transport, pressure
recomputation from gas inventory, tank withdrawal, routing, and a complete PSA
phase/cycle remain open.  No QPU work is submitted.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
from qiskit import QuantumCircuit, QuantumRegister, transpile
from qiskit.circuit.library import IntegerComparator, MultiplierGate, WeightedAdder
from qiskit.synthesis.multi_controlled import synth_mcx_n_clean_m15

from psa_spatial_network_probe_n2 import COMPONENTS, SpatialParams, cell_pressure, cell_y


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RESULTS = ROOT / "10_TEA_LCA_Python" / "results" / "pycharm_publication_enhancement"
CACHE = HERE / "cce_primary_physical_css_horizon_cache.npz"
LEDGER = RESULTS / "PSA_QAE_CCE_PRIMARY_PHASE_LEDGER.json"
OUT_JSON = RESULTS / "PSA_QAE_CCE_PRIMARY_PRODUCT_BOUNDARY_MICROSTEPS.json"
OUT_CSV = RESULTS / "PSA_QAE_CCE_PRIMARY_PRODUCT_BOUNDARY_MICROSTEPS.csv"
OUT_MD = RESULTS / "PSA_QAE_CCE_PRIMARY_PRODUCT_BOUNDARY_MICROSTEPS.md"

PRESSURE_BITS = 18
COMPOSITION_BITS = 18
VALVE_ADDRESS_BITS = list(range(8, 14))
FLOW_BITS = [18, 20, 22]
VALVE_ACTIVE_P95_RELATIVE_GATE = 5.0e-3
FLUX_SCALE_NORMALIZED_P95_GATE = 2.5e-3

AMOUNT_BITS = [20, 22, 24, 26]
FRACTION_BITS = [10, 12, 14, 16]
AMOUNT_SCALE_MOL = 100.0
PRIMARY_RECYCLE_FRACTION = 0.420
TANK_NORMALIZED_P95_GATE = 1.0e-6
TANK_CAPACITY_MOL = 100.0
TRANSPILER_SEED = 20261009


def valve_states() -> tuple[np.ndarray, np.ndarray]:
    cache = np.load(CACHE)
    boundaries = np.asarray(cache["boundaries"], dtype=float)
    if boundaries.shape != (32, 101, 85):
        raise AssertionError(boundaries.shape)
    params = SpatialParams(n_cells=4)
    pressure: list[float] = []
    composition: list[np.ndarray] = []
    for row in boundaries.reshape(-1, 85):
        for offset in (0, 40):
            gas = row[offset : offset + 20].reshape(5, 4)
            pressure.append(float(cell_pressure(gas, params)[-1]))
            composition.append(cell_y(gas)[:, -1])
    return np.asarray(pressure, dtype=float), np.asarray(composition, dtype=float)


def product_tank_records() -> tuple[np.ndarray, np.ndarray]:
    payload = json.loads(LEDGER.read_text(encoding="utf-8"))
    product: list[list[float]] = []
    tank: list[list[float]] = []
    for run in payload["runs"]:
        for record in run["product_recycle_records"]:
            product.append(record["adsorption_product_mol"])
            tank.append(record["tank_start_mol"])
    arrays = np.asarray(product, dtype=float), np.asarray(tank, dtype=float)
    if arrays[0].shape != (64, 5) or arrays[1].shape != (64, 5):
        raise AssertionError((arrays[0].shape, arrays[1].shape))
    return arrays


def valve_row(address_bits: int, flow_bits: int, pressure: np.ndarray, composition: np.ndarray) -> dict:
    params = SpatialParams(n_cells=4)
    pressure_levels = (1 << PRESSURE_BITS) - 1
    flow_levels = (1 << flow_bits) - 1
    pressure_max = float(np.max(pressure))
    back_pressure = float(params.P_high_bar - params.product_outlet_drop_bar)
    pressure_code = np.rint(pressure / pressure_max * pressure_levels).astype(int)
    composition_code = np.rint(composition * pressure_levels).astype(int)
    exact_flow = params.k_out_mol_s_bar * np.maximum(pressure - back_pressure, 0.0)
    flow_scale = float(np.max(exact_flow))
    shift = PRESSURE_BITS - address_bits
    address = pressure_code >> shift
    table: list[int] = []
    for code in range(1 << address_bits):
        representative = min(
            (code << shift) + ((1 << (shift - 1)) if shift else 0),
            pressure_levels,
        )
        representative_pressure = representative / pressure_levels * pressure_max
        flow = params.k_out_mol_s_bar * max(representative_pressure - back_pressure, 0.0)
        table.append(int(round(flow / flow_scale * flow_levels)))
    flow_code = np.asarray([table[value] for value in address], dtype=object)
    flow_approx = np.asarray(flow_code, dtype=float) / flow_levels * flow_scale
    exact_flux = exact_flow[:, None] * composition
    flux_code = np.empty_like(composition_code, dtype=object)
    for row_index in range(len(pressure)):
        for component_index in range(len(COMPONENTS)):
            flux_code[row_index, component_index] = (
                int(flow_code[row_index]) * int(composition_code[row_index, component_index])
            ) >> COMPOSITION_BITS
    flux_approx = np.asarray(flux_code, dtype=float) / flow_levels * flow_scale
    active = exact_flow > 0.0
    active_relative = np.abs(flow_approx[active] - exact_flow[active]) / exact_flow[active]
    component_metrics = []
    for component_index, component in enumerate(COMPONENTS):
        raw_relative = np.abs(flux_approx[:, component_index] - exact_flux[:, component_index]) / np.maximum(
            np.abs(exact_flux[:, component_index]), 1.0e-15
        )
        normalized = np.abs(flux_approx[:, component_index] - exact_flux[:, component_index]) / flow_scale
        erased = (exact_flux[:, component_index] > 0.0) & (
            np.asarray(flux_code[:, component_index], dtype=float) == 0.0
        )
        component_metrics.append(
            {
                "component": component,
                "flux_p95_relative_error": float(np.quantile(raw_relative, 0.95)),
                "flux_p95_flow_scale_normalized_absolute_error": float(np.quantile(normalized, 0.95)),
                "nonzero_flux_erased_fraction": float(np.mean(erased)),
            }
        )
    result = {
        "pressure_bits": PRESSURE_BITS,
        "composition_bits_per_component": COMPOSITION_BITS,
        "valve_address_bits": address_bits,
        "valve_qrom_entries": 1 << address_bits,
        "flow_bits": flow_bits,
        "pressure_scale_bar": pressure_max,
        "back_pressure_bar": back_pressure,
        "flow_scale_mol_s": flow_scale,
        "flow_table_codes": table,
        "active_state_count": int(np.sum(active)),
        "active_label_mismatch_fraction": float(np.mean((flow_approx > 0.0) != active)),
        "active_flow_p95_relative_error": float(np.quantile(active_relative, 0.95)),
        "flow_p95_scale_normalized_absolute_error": float(
            np.quantile(np.abs(flow_approx - exact_flow) / flow_scale, 0.95)
        ),
        "component_metrics": component_metrics,
    }
    result["passes_declared_precision_gate"] = bool(
        result["active_label_mismatch_fraction"] == 0.0
        and result["active_flow_p95_relative_error"] <= VALVE_ACTIVE_P95_RELATIVE_GATE
        and max(
            metric["flux_p95_flow_scale_normalized_absolute_error"]
            for metric in component_metrics
        )
        <= FLUX_SCALE_NORMALIZED_P95_GATE
        and max(metric["nonzero_flux_erased_fraction"] for metric in component_metrics) == 0.0
    )
    return result


def append_qrom(
    circuit: QuantumCircuit,
    address: list,
    output: list,
    workspace: list,
    table: list[int],
    *,
    inverse: bool = False,
) -> None:
    mcx = synth_mcx_n_clean_m15(len(address))
    order = range(len(table) - 1, -1, -1) if inverse else range(len(table))
    for code in order:
        zero_controls = [bit for bit in range(len(address)) if not ((code >> bit) & 1)]
        for bit in zero_controls:
            circuit.x(address[bit])
        output_bits = [bit for bit in range(len(output)) if (table[code] >> bit) & 1]
        if inverse:
            output_bits.reverse()
        for bit in output_bits:
            circuit.append(mcx, address + [output[bit]] + workspace[: len(address) - 2])
        for bit in reversed(zero_controls):
            circuit.x(address[bit])


def build_valve_flux_circuit(selected: dict) -> tuple[QuantumCircuit, dict]:
    address_bits = int(selected["valve_address_bits"])
    flow_bits = int(selected["flow_bits"])
    pressure_reg = QuantumRegister(PRESSURE_BITS, "pressure")
    composition_reg = QuantumRegister(len(COMPONENTS) * COMPOSITION_BITS, "composition")
    address_reg = QuantumRegister(address_bits, "pressure_bin")
    workspace_reg = QuantumRegister(max(address_bits - 2, flow_bits - COMPOSITION_BITS), "work")
    flow_reg = QuantumRegister(flow_bits, "valve_flow")
    product_reg = QuantumRegister(flow_bits + COMPOSITION_BITS, "flow_times_y")
    flux_reg = QuantumRegister(len(COMPONENTS) * flow_bits, "component_flux")
    circuit = QuantumCircuit(
        pressure_reg,
        composition_reg,
        address_reg,
        workspace_reg,
        flow_reg,
        product_reg,
        flux_reg,
        name="clean_product_valve_component_flux",
    )
    shift = PRESSURE_BITS - address_bits
    for bit in range(address_bits):
        circuit.cx(pressure_reg[shift + bit], address_reg[bit])
    append_qrom(
        circuit,
        list(address_reg),
        list(flow_reg),
        list(workspace_reg),
        [int(value) for value in selected["flow_table_codes"]],
    )
    multiplier = MultiplierGate(flow_bits, flow_bits + COMPOSITION_BITS)
    padding = list(workspace_reg)[: flow_bits - COMPOSITION_BITS]
    for component_index in range(len(COMPONENTS)):
        y = list(composition_reg)[
            component_index * COMPOSITION_BITS : (component_index + 1) * COMPOSITION_BITS
        ]
        qargs = list(flow_reg) + y + padding + list(product_reg)
        circuit.append(multiplier, qargs)
        high_product = list(product_reg)[COMPOSITION_BITS : COMPOSITION_BITS + flow_bits]
        output = list(flux_reg)[component_index * flow_bits : (component_index + 1) * flow_bits]
        for source, target in zip(high_product, output):
            circuit.cx(source, target)
        circuit.append(multiplier.inverse(), qargs)
    append_qrom(
        circuit,
        list(address_reg),
        list(flow_reg),
        list(workspace_reg),
        [int(value) for value in selected["flow_table_codes"]],
        inverse=True,
    )
    for bit in reversed(range(address_bits)):
        circuit.cx(pressure_reg[shift + bit], address_reg[bit])
    return circuit, {
        "retained_inputs": [f"{PRESSURE_BITS}-bit pressure", f"5 x {COMPOSITION_BITS}-bit composition"],
        "clean_outputs": f"5 x {flow_bits}-bit one-second component flux",
        "cleared": ["pressure-bin address", "valve-flow QROM", "multiplier product", "shared workspace"],
        "qrom_clean_ancillas": address_bits - 2,
    }


def tank_row(amount_bits: int, fraction_bits: int, product: np.ndarray, tank: np.ndarray) -> dict:
    levels = (1 << amount_bits) - 1
    product_code = np.rint(product / AMOUNT_SCALE_MOL * levels).astype(object)
    tank_code = np.rint(tank / AMOUNT_SCALE_MOL * levels).astype(object)
    recycle_integer = int(round(PRIMARY_RECYCLE_FRACTION * (1 << fraction_bits)))
    external_integer = (1 << fraction_bits) - recycle_integer
    rounding = 1 << (fraction_bits - 1)
    recycle_code = np.empty_like(product_code)
    external_code = np.empty_like(product_code)
    candidate_code = np.empty_like(product_code)
    for row_index in range(len(product)):
        for component_index in range(len(COMPONENTS)):
            recycle_code[row_index, component_index] = (
                int(product_code[row_index, component_index]) * recycle_integer + rounding
            ) >> fraction_bits
            external_code[row_index, component_index] = (
                int(product_code[row_index, component_index]) * external_integer + rounding
            ) >> fraction_bits
            candidate_code[row_index, component_index] = (
                int(tank_code[row_index, component_index])
                + int(recycle_code[row_index, component_index])
            )
    recycle_approx = np.asarray(recycle_code, dtype=float) / levels * AMOUNT_SCALE_MOL
    external_approx = np.asarray(external_code, dtype=float) / levels * AMOUNT_SCALE_MOL
    candidate_approx = np.asarray(candidate_code, dtype=float) / levels * AMOUNT_SCALE_MOL
    recycle_exact = product * PRIMARY_RECYCLE_FRACTION
    external_exact = product * (1.0 - PRIMARY_RECYCLE_FRACTION)
    candidate_exact = tank + recycle_exact
    normalized = np.concatenate(
        [
            np.abs(recycle_approx - recycle_exact).ravel(),
            np.abs(external_approx - external_exact).ravel(),
            np.abs(candidate_approx - candidate_exact).ravel(),
        ]
    ) / AMOUNT_SCALE_MOL
    erased = (recycle_exact > 0.0) & (np.asarray(recycle_code, dtype=float) == 0.0)
    capacity_exact = np.sum(candidate_exact, axis=1) > TANK_CAPACITY_MOL
    capacity_approx = np.sum(candidate_approx, axis=1) > TANK_CAPACITY_MOL
    result = {
        "amount_bits": amount_bits,
        "fraction_bits": fraction_bits,
        "amount_scale_mol": AMOUNT_SCALE_MOL,
        "recycle_fraction_exact": PRIMARY_RECYCLE_FRACTION,
        "recycle_fraction_integer": recycle_integer,
        "recycle_fraction_implemented": recycle_integer / (1 << fraction_bits),
        "external_fraction_integer": external_integer,
        "p95_amount_scale_normalized_absolute_error": float(np.quantile(normalized, 0.95)),
        "max_amount_scale_normalized_absolute_error": float(np.max(normalized)),
        "nonzero_recycle_erased_fraction": float(np.mean(erased)),
        "capacity_flag_mismatch_fraction": float(np.mean(capacity_exact != capacity_approx)),
        "maximum_candidate_tank_total_mol": float(np.max(np.sum(candidate_exact, axis=1))),
        "minimum_capacity_headroom_mol": float(
            TANK_CAPACITY_MOL - np.max(np.sum(candidate_exact, axis=1))
        ),
    }
    result["passes_declared_precision_gate"] = bool(
        result["p95_amount_scale_normalized_absolute_error"] <= TANK_NORMALIZED_P95_GATE
        and result["nonzero_recycle_erased_fraction"] == 0.0
        and result["capacity_flag_mismatch_fraction"] == 0.0
    )
    return result


def build_scalar_tank_split(selected: dict) -> tuple[QuantumCircuit, dict]:
    bits = int(selected["amount_bits"])
    fraction_bits = int(selected["fraction_bits"])
    recycle_integer = int(selected["recycle_fraction_integer"])
    external_integer = int(selected["external_fraction_integer"])
    recycle_adder = WeightedAdder(bits, [recycle_integer * (1 << bit) for bit in range(bits)])
    external_adder = WeightedAdder(bits, [external_integer * (1 << bit) for bit in range(bits)])
    candidate_adder = WeightedAdder(
        2 * bits,
        [1 << bit for bit in range(bits)] + [1 << bit for bit in range(bits)],
    )
    max_sum_bits = max(
        recycle_adder.num_sum_qubits,
        external_adder.num_sum_qubits,
        candidate_adder.num_sum_qubits,
    )
    max_ancillas = max(
        recycle_adder.num_ancillas,
        external_adder.num_ancillas,
        candidate_adder.num_ancillas,
    )
    product_reg = QuantumRegister(bits, "product")
    tank_reg = QuantumRegister(bits, "tank")
    recycle_reg = QuantumRegister(bits, "recycle")
    external_reg = QuantumRegister(bits, "external")
    candidate_reg = QuantumRegister(bits, "tank_candidate")
    carry_reg = QuantumRegister(1, "candidate_carry")
    sum_reg = QuantumRegister(max_sum_bits, "sum")
    work_reg = QuantumRegister(max_ancillas, "work")
    circuit = QuantumCircuit(
        product_reg,
        tank_reg,
        recycle_reg,
        external_reg,
        candidate_reg,
        carry_reg,
        sum_reg,
        work_reg,
        name="clean_product_split_tank_candidate",
    )

    def apply_fraction(adder: WeightedAdder, output: QuantumRegister) -> None:
        qargs = list(product_reg) + list(sum_reg)[: adder.num_sum_qubits] + list(work_reg)[: adder.num_ancillas]
        circuit.append(adder, qargs)
        for source, target in zip(
            list(sum_reg)[fraction_bits : fraction_bits + bits],
            list(output),
        ):
            circuit.cx(source, target)
        circuit.append(adder.inverse(), qargs)

    apply_fraction(recycle_adder, recycle_reg)
    apply_fraction(external_adder, external_reg)
    candidate_qargs = (
        list(tank_reg)
        + list(recycle_reg)
        + list(sum_reg)[: candidate_adder.num_sum_qubits]
        + list(work_reg)[: candidate_adder.num_ancillas]
    )
    circuit.append(candidate_adder, candidate_qargs)
    for source, target in zip(list(sum_reg)[:bits], list(candidate_reg)):
        circuit.cx(source, target)
    circuit.cx(sum_reg[bits], carry_reg[0])
    circuit.append(candidate_adder.inverse(), candidate_qargs)
    return circuit, {
        "retained_inputs": [f"{bits}-bit product", f"{bits}-bit tank"],
        "clean_outputs": [f"{bits}-bit recycle", f"{bits}-bit external product", f"{bits}-bit tank candidate", "candidate carry"],
        "cleared": ["fraction weighted sums", "tank-candidate weighted sum", "shared ancillas"],
    }


def build_capacity_flag(selected: dict) -> tuple[QuantumCircuit, dict]:
    bits = int(selected["amount_bits"])
    levels = (1 << bits) - 1
    weights = [1 << bit for _component in COMPONENTS for bit in range(bits)]
    adder = WeightedAdder(len(weights), weights)
    comparator = IntegerComparator(adder.num_sum_qubits, levels, geq=True)
    candidates_reg = QuantumRegister(len(COMPONENTS) * bits, "tank_candidates")
    sum_reg = QuantumRegister(adder.num_sum_qubits, "tank_total")
    flag_reg = QuantumRegister(1, "compare_flag")
    output_reg = QuantumRegister(1, "capacity_exceeded")
    work_reg = QuantumRegister(max(adder.num_ancillas, comparator.num_ancillas), "work")
    circuit = QuantumCircuit(
        candidates_reg,
        sum_reg,
        flag_reg,
        output_reg,
        work_reg,
        name="clean_tank_capacity_flag",
    )
    adder_qargs = list(candidates_reg) + list(sum_reg) + list(work_reg)[: adder.num_ancillas]
    comparator_qargs = list(sum_reg) + list(flag_reg) + list(work_reg)[: comparator.num_ancillas]
    circuit.append(adder, adder_qargs)
    circuit.append(comparator, comparator_qargs)
    circuit.cx(flag_reg[0], output_reg[0])
    circuit.append(comparator.inverse(), comparator_qargs)
    circuit.append(adder.inverse(), adder_qargs)
    return circuit, {
        "retained_inputs": f"5 x {bits}-bit tank candidates",
        "clean_output": "capacity_exceeded",
        "capacity_threshold_code": levels,
        "cleared": ["tank total", "comparator flag", "shared ancillas"],
    }


def resources(circuit: QuantumCircuit) -> dict:
    compiled = transpile(
        circuit,
        basis_gates=["u", "cx"],
        optimization_level=1,
        seed_transpiler=TRANSPILER_SEED,
    )
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
    pressure, composition = valve_states()
    valve_rows = [
        valve_row(address_bits, flow_bits, pressure, composition)
        for flow_bits in FLOW_BITS
        for address_bits in VALVE_ADDRESS_BITS
    ]
    selected_valve = next(
        (row for row in valve_rows if row["passes_declared_precision_gate"]),
        None,
    )
    if selected_valve is None:
        raise AssertionError("no valve/flux precision tier passes")
    valve_circuit, valve_layout = build_valve_flux_circuit(selected_valve)
    valve_resources = resources(valve_circuit)
    print(
        json.dumps(
            {
                "module": "product_valve_component_flux",
                "address_bits": selected_valve["valve_address_bits"],
                "flow_bits": selected_valve["flow_bits"],
                "logical_qubits": valve_resources["logical_qubits"],
                "cx": valve_resources["cx"],
            }
        ),
        flush=True,
    )

    product, tank = product_tank_records()
    tank_rows = [
        tank_row(amount_bits, fraction_bits, product, tank)
        for amount_bits in AMOUNT_BITS
        for fraction_bits in FRACTION_BITS
    ]
    selected_tank = next(
        (row for row in tank_rows if row["passes_declared_precision_gate"]),
        None,
    )
    if selected_tank is None:
        raise AssertionError("no product-split/tank precision tier passes")
    scalar_circuit, scalar_layout = build_scalar_tank_split(selected_tank)
    scalar_resources = resources(scalar_circuit)
    print(
        json.dumps(
            {
                "module": "scalar_product_split_tank_candidate",
                "amount_bits": selected_tank["amount_bits"],
                "fraction_bits": selected_tank["fraction_bits"],
                "logical_qubits": scalar_resources["logical_qubits"],
                "cx": scalar_resources["cx"],
            }
        ),
        flush=True,
    )
    capacity_circuit, capacity_layout = build_capacity_flag(selected_tank)
    capacity_resources = resources(capacity_circuit)
    print(
        json.dumps(
            {
                "module": "tank_capacity_flag",
                "logical_qubits": capacity_resources["logical_qubits"],
                "cx": capacity_resources["cx"],
            }
        ),
        flush=True,
    )

    bits = int(selected_tank["amount_bits"])
    scalar_retained = 5 * bits
    full_retained = len(COMPONENTS) * scalar_retained
    scalar_workspace = scalar_resources["logical_qubits"] - scalar_retained
    capacity_workspace = capacity_resources["logical_qubits"] - len(COMPONENTS) * bits
    tank_accounting = {
        "accounting": "five identical compiled scalar split/tank-candidate modules executed sequentially with workspace reuse, followed by the compiled vector capacity flag",
        "logical_qubits": full_retained + max(scalar_workspace, capacity_workspace),
        "retained_product_tank_recycle_external_candidate_qubits": full_retained,
        "shared_workspace_qubits": max(scalar_workspace, capacity_workspace),
        "cx_additive_module_bound": len(COMPONENTS) * scalar_resources["cx"] + capacity_resources["cx"],
        "depth_all_to_all_additive_module_bound": len(COMPONENTS) * scalar_resources["depth_all_to_all"] + capacity_resources["depth_all_to_all"],
        "interpretation": "modular arithmetic accounting; not a monolithic transpilation and not linked through adaptive phase integration to the valve-flux module",
    }
    payload = {
        "schema": "psa-qae-cce-primary-product-boundary-microsteps/v1",
        "status": "product_valve_flux_and_recycle_tank_capacity_modules_compiled_internal_transport_pressure_cycle_open",
        "qpu_submission": False,
        "valve_state_source": {
            "runs": 32,
            "cycles_per_run": 100,
            "beds": 2,
            "states": int(len(pressure)),
            "pressure_range_bar": [float(np.min(pressure)), float(np.max(pressure))],
            "active_states": int(np.sum(SpatialParams().k_out_mol_s_bar * np.maximum(pressure - selected_valve["back_pressure_bar"], 0.0) > 0.0)),
        },
        "valve_precision_gate": {
            "active_flow_p95_relative_error_max": VALVE_ACTIVE_P95_RELATIVE_GATE,
            "component_flux_p95_flow_scale_normalized_absolute_error_max": FLUX_SCALE_NORMALIZED_P95_GATE,
            "active_label_mismatch_fraction_required": 0.0,
            "nonzero_flux_erased_fraction_required": 0.0,
        },
        "valve_rows": valve_rows,
        "selected_valve": selected_valve,
        "valve_register_layout": valve_layout,
        "compiled_clean_valve_component_flux": valve_resources,
        "tank_record_source": {
            "runs": 32,
            "product_recycle_records": int(len(product)),
            "tank_capacity_mol": TANK_CAPACITY_MOL,
            "maximum_observed_tank_start_total_mol": float(np.max(np.sum(tank, axis=1))),
        },
        "tank_precision_gate": {
            "p95_amount_scale_normalized_absolute_error_max": TANK_NORMALIZED_P95_GATE,
            "nonzero_recycle_erased_fraction_required": 0.0,
            "capacity_flag_mismatch_fraction_required": 0.0,
        },
        "tank_rows": tank_rows,
        "selected_tank": selected_tank,
        "scalar_tank_register_layout": scalar_layout,
        "compiled_clean_scalar_product_split_tank_candidate": scalar_resources,
        "capacity_register_layout": capacity_layout,
        "compiled_clean_tank_capacity_flag": capacity_resources,
        "five_component_tank_accounting": tank_accounting,
        "claim_boundary": {
            "supported": "encoded product-end pressure/composition to clean five-component one-second outlet flux, plus separately compiled fixed-policy product split, tank-candidate arithmetic, and capacity flag over final-cycle ledger ranges",
            "unsupported": "pressure recomputation from gas inventory, internal face transport, adsorption coupling, tank withdrawal, adaptive phase integration, monolithic valve-to-integrated-product composition, routing, a complete reversible phase/cycle, hardware feasibility, or quantum advantage",
        },
    }
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    flat_rows = [
        {
            "module": "product valve to five component fluxes",
            "precision": f"{selected_valve['valve_address_bits']}-bit pressure address; {selected_valve['flow_bits']}-bit flow",
            "logical_qubits": valve_resources["logical_qubits"],
            "depth_all_to_all": valve_resources["depth_all_to_all"],
            "cx": valve_resources["cx"],
            "p95_error": selected_valve["active_flow_p95_relative_error"],
        },
        {
            "module": "scalar product split and tank candidate",
            "precision": f"{selected_tank['amount_bits']}-bit amount; {selected_tank['fraction_bits']}-bit fraction",
            "logical_qubits": scalar_resources["logical_qubits"],
            "depth_all_to_all": scalar_resources["depth_all_to_all"],
            "cx": scalar_resources["cx"],
            "p95_error": selected_tank["p95_amount_scale_normalized_absolute_error"],
        },
        {
            "module": "five-component tank capacity flag",
            "precision": f"5 x {selected_tank['amount_bits']}-bit tank candidates",
            "logical_qubits": capacity_resources["logical_qubits"],
            "depth_all_to_all": capacity_resources["depth_all_to_all"],
            "cx": capacity_resources["cx"],
            "p95_error": selected_tank["capacity_flag_mismatch_fraction"],
        },
    ]
    with OUT_CSV.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(flat_rows[0]))
        writer.writeheader()
        writer.writerows(flat_rows)
    OUT_MD.write_text(
        "\n".join(
            [
                "# Clean product-boundary valve/flux and tank-ledger modules",
                "",
                f"The product-valve precision screen covers **{len(pressure):,} encoded product-end states**. The first passing tier uses a **{selected_valve['valve_address_bits']}-bit pressure address** and **{selected_valve['flow_bits']}-bit flow/flux outputs**. Active/inactive labels agree for every state, active-flow p95 relative error is **{selected_valve['active_flow_p95_relative_error']:.4%}**, and the largest component-flux p95 error is **{max(row['flux_p95_flow_scale_normalized_absolute_error'] for row in selected_valve['component_metrics']):.4%} of the flow register range**.",
                "",
                f"The clean valve-to-five-component-flux circuit uses **{valve_resources['logical_qubits']:,} logical qubits**, depth **{valve_resources['depth_all_to_all']:,}**, and **{valve_resources['cx']:,} CX** in the all-to-all `u/CX` basis.",
                "",
                f"The product/tank screen covers **{len(product)} final-cycle product-recycle records**. The first passing tier uses **{selected_tank['amount_bits']}-bit amounts** and a **{selected_tank['fraction_bits']}-bit fixed recycle coefficient**. Its p95 error is **{selected_tank['p95_amount_scale_normalized_absolute_error']:.3e} of the 100-mol register range**, with zero nonzero-recycle erasure and zero capacity-flag mismatch. Maximum candidate tank inventory is **{selected_tank['maximum_candidate_tank_total_mol']:.6f} mol**, leaving **{selected_tank['minimum_capacity_headroom_mol']:.6f} mol** headroom.",
                "",
                f"One clean scalar split/tank-candidate block uses **{scalar_resources['logical_qubits']:,} qubits** and **{scalar_resources['cx']:,} CX**; the clean vector capacity block uses **{capacity_resources['logical_qubits']:,} qubits** and **{capacity_resources['cx']:,} CX**. Sequential five-component accounting with all product/tank/recycle/external/candidate registers retained requires **{tank_accounting['logical_qubits']:,} qubits** and **{tank_accounting['cx_additive_module_bound']:,} additive CX**.",
                "",
                "The valve-flux and integrated product/tank records remain separate evidence tiers. Pressure recomputation, internal face transport, adsorption coupling, tank withdrawal, adaptive integration, monolithic composition, routing, and a complete reversible phase/cycle remain open.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": payload["status"],
                "valve_logical_qubits": valve_resources["logical_qubits"],
                "valve_cx": valve_resources["cx"],
                "tank_accounting_logical_qubits": tank_accounting["logical_qubits"],
                "tank_accounting_cx": tank_accounting["cx_additive_module_bound"],
                "qpu_submission": False,
            },
            indent=2,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
