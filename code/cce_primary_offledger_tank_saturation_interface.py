"""Compile a pressure-derived saturated tank-withdrawal interface.

The frozen 32-run PSA support contains four tank-sourced calls per final
cycle.  The older controller loads their withdrawals from a run/slot QROM.
This audit removes that lookup on the branch actually exercised by the
support.  It reconstructs the source-end pressure from five encoded endpoint
gas inventories, forms the end-pressure demand lower bound

    k_in * duration * max(P_high - P_end, 0),

and compares it reversibly with the five-component tank inventory.  Every
cached call is demand-saturated, so the clean withdrawal is the current tank
and the next tank is zero.  The lower bound is validated against the exact
integrated phase inflow for every record.  Unsaturated withdrawal allocation,
out-of-support trajectories, and adaptive phase integration remain open.

No QPU work is submitted.
"""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import numpy as np
from qiskit import QuantumCircuit, QuantumRegister, transpile
from qiskit.circuit.library import IntegerComparator, ModularAdderGate, WeightedAdder

from cce_primary_coherent_run_schedule_tank_interface import COMPONENTS, RESULTS
from cce_primary_joint_normalized_transport_ldf_balance import load_context
from psa_spatial_network_probe_n2 import SpatialParams, cell_pressure, unpack
from psa_two_bed_spatial_network_n2 import equalize_endpoints, oriented_step
import psa_two_bed_spatial_tank_n2 as tank_model


HERE = Path(__file__).resolve().parent
LEDGER = RESULTS / "PSA_QAE_CCE_PRIMARY_PHASE_LEDGER.json"
CACHE = HERE / "cce_primary_physical_css_horizon_cache.npz"
PRIOR_TANK = RESULTS / "PSA_QAE_CCE_COHERENT_RUN_SCHEDULE_TANK_INTERFACE.json"
OUT_JSON = RESULTS / "PSA_QAE_CCE_OFFLEDGER_TANK_SATURATION_INTERFACE.json"
OUT_CSV = RESULTS / "PSA_QAE_CCE_OFFLEDGER_TANK_SATURATION_INTERFACE.csv"
OUT_MD = RESULTS / "PSA_QAE_CCE_OFFLEDGER_TANK_SATURATION_INTERFACE.md"

TANK_BITS = 18
COMMON_BITS_CASES = (16, 18, 20)
COMMON_P95_GATE = 1.0e-5
MEANINGFUL_MOL = 1.0e-15
TRANSPILER_SEED = 20261010
P_HIGH_BAR = 15.65
K_IN_MOL_S_BAR = 1.0
PHASE_DURATION_S = 10.0


def json_default(value):
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    raise TypeError(type(value).__name__)


def make_params(run: dict) -> SpatialParams:
    base_feed = np.asarray([0.655, 0.283, 0.041, 0.006, 0.014], dtype=float)
    base_feed /= base_feed.sum()
    p = run["parameters"]
    return SpatialParams(
        n_cells=4,
        P_high_bar=P_HIGH_BAR,
        P_low_bar=float(p["P_low_bar"]),
        phase_duration_s=PHASE_DURATION_S,
        feed_y_dry=tuple(base_feed.tolist()),
        purge_y_dry=tuple(float(p[name]) for name in ("source_h2", "source_co2", "source_ch4", "source_co", "source_n2")),
        k_in_mol_s_bar=K_IN_MOL_S_BAR,
        k_out_mol_s_bar=1.0,
        k_internal_mol_s_bar=5.0,
        capacity_factor=float(p["capacity_factor"]),
        affinity_factor=float(p["affinity_factor"]),
        ldf_factor=float(p["ldf_factor"]),
        max_step_points=12,
        solver_method="BDF",
    )


def replay_final_cycle(run: dict, boundary: np.ndarray, expected_end: np.ndarray) -> tuple[list[dict], float]:
    """Replay cycle 100 from its cached boundary and retain endpoint gases."""

    p = make_params(run)
    state_size = 2 * p.n_component * p.n_cells
    state_a = np.asarray(boundary[:state_size], dtype=float).copy()
    state_b = np.asarray(boundary[state_size : 2 * state_size], dtype=float).copy()
    tank = np.asarray(boundary[2 * state_size :], dtype=float).copy()
    y_feed = tank_model._normalise(np.asarray(p.feed_y_dry, dtype=float))
    y_purge = tank_model._normalise(np.asarray(p.purge_y_dry, dtype=float))
    recycle_fraction = float(run["parameters"]["recycle_fraction"])
    equalization_conductance = float(run["parameters"]["equalization_conductance"])
    records: list[dict] = []

    def tank_call(state, bed: str, step: str, reverse: bool):
        nonlocal tank
        tank_start = np.asarray(tank, dtype=float).copy()
        state_next, stream, tank_next, makeup = tank_model._tank_step(
            state,
            step,
            PHASE_DURATION_S,
            p,
            tank,
            y_purge,
            reverse=reverse,
        )
        ng_end, _ = unpack(state_next, p)
        if step == "pressurization":
            inlet_index = p.n_cells - 1 if reverse else 0
        elif step == "purge":
            inlet_index = 0 if reverse else p.n_cells - 1
        else:
            raise ValueError(step)
        endpoint_gas = np.asarray(ng_end[:, inlet_index], dtype=float)
        endpoint_pressure = float(cell_pressure(ng_end, p)[inlet_index])
        exact_demand = float(np.sum(stream["in_mol"]))
        demand_lower = K_IN_MOL_S_BAR * PHASE_DURATION_S * max(P_HIGH_BAR - endpoint_pressure, 0.0)
        records.append(
            {
                "sample": int(run["sample"]),
                "slot": len(records),
                "bed": bed,
                "step": step,
                "reverse": bool(reverse),
                "endpoint_cell": int(inlet_index),
                "endpoint_gas_mol": endpoint_gas,
                "endpoint_pressure_bar": endpoint_pressure,
                "exact_integrated_demand_mol": exact_demand,
                "end_pressure_demand_lower_bound_mol": demand_lower,
                "tank_start_mol": tank_start,
                "tank_withdrawal_mol": np.asarray(stream["tank_withdrawal_mol"], dtype=float),
                "makeup_mol": np.asarray(makeup, dtype=float),
                "tank_end_mol": np.asarray(tank_next, dtype=float),
            }
        )
        tank = np.asarray(tank_next, dtype=float)
        return state_next, stream

    state_a, adsorption_a = oriented_step(
        state_a, "adsorption", PHASE_DURATION_S, y_feed, p, reverse=False
    )
    state_b, _ = tank_call(state_b, "B", "pressurization", True)
    tank, _, _ = tank_model._add_recycle(
        tank, np.asarray(adsorption_a["out_mol"], dtype=float), recycle_fraction, 100.0
    )
    state_a, state_b, _ = equalize_endpoints(
        state_a,
        state_b,
        p,
        index_a=p.n_cells - 1,
        index_b=0,
        duration_s=2.0,
        conductance_mol_s_bar=equalization_conductance,
    )

    state_a, _ = oriented_step(
        state_a, "blowdown", PHASE_DURATION_S, y_feed, p, reverse=False
    )
    state_b, adsorption_b = oriented_step(
        state_b, "adsorption", PHASE_DURATION_S, y_feed, p, reverse=True
    )
    tank, _, _ = tank_model._add_recycle(
        tank, np.asarray(adsorption_b["out_mol"], dtype=float), recycle_fraction, 100.0
    )
    state_a, state_b, _ = equalize_endpoints(
        state_a,
        state_b,
        p,
        index_a=0,
        index_b=p.n_cells - 1,
        duration_s=2.0,
        conductance_mol_s_bar=equalization_conductance,
    )

    state_a, _ = tank_call(state_a, "A", "purge", False)
    state_b, _ = oriented_step(
        state_b, "blowdown", PHASE_DURATION_S, y_feed, p, reverse=True
    )
    state_a, _ = tank_call(state_a, "A", "pressurization", False)
    state_b, _ = tank_call(state_b, "B", "purge", True)

    end = np.r_[state_a, state_b, tank]
    replay_error = float(np.max(np.abs(end - np.asarray(expected_end, dtype=float))))
    if len(records) != 4:
        raise AssertionError(len(records))
    return records, replay_error


def support_records() -> tuple[list[dict], dict]:
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    runs = {int(run["sample"]): run for run in ledger["runs"]}
    cache = np.load(CACHE)
    samples = np.asarray(cache["samples"], dtype=int)
    boundaries = np.asarray(cache["boundaries"], dtype=float)
    all_records: list[dict] = []
    replay_errors: list[float] = []
    ledger_pressure_errors: list[float] = []
    for row, sample in enumerate(samples):
        run = runs[int(sample)]
        records, replay_error = replay_final_cycle(
            run, boundaries[row, 99], boundaries[row, 100]
        )
        replay_errors.append(replay_error)
        expected = run["tank_withdrawal_records"]
        phase_indices = (1, 4, 6, 7)
        for record, expected_tank, phase_index in zip(records, expected, phase_indices):
            record["ledger_tank_start_mol"] = np.asarray(
                expected_tank["tank_start_mol"], dtype=float
            )
            record["ledger_tank_withdrawal_mol"] = np.asarray(
                expected_tank["tank_withdrawal_mol"], dtype=float
            )
            record["ledger_tank_end_mol"] = np.asarray(
                expected_tank["tank_end_mol"], dtype=float
            )
            phase = run["phase_records"][phase_index]
            if record["step"] == "pressurization":
                side = "right" if record["reverse"] else "left"
            else:
                side = "left" if record["reverse"] else "right"
            expected_pressure = float(phase["state_end"][f"pressure_{side}_bar"])
            ledger_pressure_errors.append(abs(record["endpoint_pressure_bar"] - expected_pressure))
            all_records.append(record)
    return all_records, {
        "maximum_cached_cycle_end_absolute_error": float(max(replay_errors)),
        "maximum_ledger_endpoint_pressure_absolute_error_bar": float(
            max(ledger_pressure_errors)
        ),
    }


def encode_support(records: list[dict], common_bits: int, selected_pressure: dict, tank_selected: dict) -> tuple[dict, dict]:
    pressure_bits = int(selected_pressure["pressure_output_bits"])
    pressure_levels = (1 << pressure_bits) - 1
    pressure_scale = float(selected_pressure["pressure_scale_bar"])
    gas_bits = int(selected_pressure["gas_bits_per_component"])
    gas_levels = (1 << gas_bits) - 1
    gas_scales = np.asarray(selected_pressure["gas_component_scales_mol"], dtype=float)
    pressure_weights = np.asarray(selected_pressure["pressure_weights"], dtype=object)
    tank_levels = (1 << TANK_BITS) - 1
    tank_scales = np.asarray(
        [tank_selected["component_scales_mol"][name] for name in COMPONENTS],
        dtype=float,
    )
    common_levels = (1 << common_bits) - 1

    endpoint_gas = np.asarray([row["endpoint_gas_mol"] for row in records], dtype=float)
    exact_pressure = np.asarray([row["endpoint_pressure_bar"] for row in records], dtype=float)
    exact_demand = np.asarray([row["exact_integrated_demand_mol"] for row in records], dtype=float)
    exact_lower = np.asarray([row["end_pressure_demand_lower_bound_mol"] for row in records], dtype=float)
    exact_tank = np.asarray([row["tank_start_mol"] for row in records], dtype=float)
    exact_withdrawal = np.asarray([row["tank_withdrawal_mol"] for row in records], dtype=float)
    exact_tank_total = np.sum(exact_tank, axis=1)
    common_scale = 1.01 * max(float(np.max(exact_lower)), float(np.max(exact_tank_total)), 1.0)

    gas_code = np.rint(endpoint_gas / gas_scales * gas_levels).astype(np.int64)
    if np.any(gas_code < 0) or np.any(gas_code > gas_levels):
        raise AssertionError("endpoint gas outside encoded pressure support")
    pressure_code = np.zeros(len(records), dtype=object)
    for component in range(len(COMPONENTS)):
        for bit in range(gas_bits):
            pressure_code += ((gas_code[:, component] >> bit) & 1) * pressure_weights[component * gas_bits + bit]
    pressure_code = np.asarray(pressure_code, dtype=np.int64)
    pressure_approx = pressure_code.astype(float) / pressure_levels * pressure_scale
    deficit_code = pressure_levels - pressure_code

    demand_weights = [
        int(
            round(
                (1 << bit)
                * pressure_scale
                / pressure_levels
                * K_IN_MOL_S_BAR
                * PHASE_DURATION_S
                / common_scale
                * common_levels
            )
        )
        for bit in range(pressure_bits)
    ]
    demand_code = np.zeros(len(records), dtype=object)
    for bit, weight in enumerate(demand_weights):
        demand_code += ((deficit_code >> bit) & 1) * weight
    demand_code = np.asarray(demand_code, dtype=np.int64)

    tank_code = np.rint(exact_tank / tank_scales * tank_levels).astype(np.int64)
    tank_weights = [
        int(
            round(
                tank_scales[component]
                / tank_levels
                * (1 << bit)
                / common_scale
                * common_levels
            )
        )
        for component in range(len(COMPONENTS))
        for bit in range(TANK_BITS)
    ]
    tank_total_code = np.zeros(len(records), dtype=object)
    for component in range(len(COMPONENTS)):
        for bit in range(TANK_BITS):
            tank_total_code += ((tank_code[:, component] >> bit) & 1) * tank_weights[component * TANK_BITS + bit]
    tank_total_code = np.asarray(tank_total_code, dtype=np.int64)

    demand_approx = demand_code.astype(float) / common_levels * common_scale
    tank_total_approx = tank_total_code.astype(float) / common_levels * common_scale
    exact_saturated = exact_demand >= exact_tank_total
    lower_saturated = exact_lower >= exact_tank_total
    approx_saturated = demand_code >= tank_total_code
    withdrawal_code = np.where(approx_saturated[:, None], tank_code, 0)
    next_code = tank_code - withdrawal_code
    withdrawal_approx = withdrawal_code.astype(float) / tank_levels * tank_scales
    next_approx = next_code.astype(float) / tank_levels * tank_scales
    exact_next = exact_tank - exact_withdrawal

    errors = np.concatenate(
        [
            np.abs(demand_approx - exact_lower) / common_scale,
            np.abs(tank_total_approx - exact_tank_total) / common_scale,
            (np.abs(withdrawal_approx - exact_withdrawal) / tank_scales).ravel(),
            (np.abs(next_approx - exact_next) / tank_scales).ravel(),
        ]
    )
    result = {
        "common_bits": int(common_bits),
        "common_scale_mol": float(common_scale),
        "pressure_bits": pressure_bits,
        "endpoint_gas_bits_per_component": gas_bits,
        "tank_bits_per_component": TANK_BITS,
        "pressure_p95_scale_normalized_absolute_error": float(
            np.quantile(np.abs(pressure_approx - exact_pressure) / pressure_scale, 0.95)
        ),
        "demand_lower_p95_common_scale_normalized_absolute_error": float(
            np.quantile(np.abs(demand_approx - exact_lower) / common_scale, 0.95)
        ),
        "tank_total_p95_common_scale_normalized_absolute_error": float(
            np.quantile(np.abs(tank_total_approx - exact_tank_total) / common_scale, 0.95)
        ),
        "all_output_p95_scale_normalized_absolute_error": float(np.quantile(errors, 0.95)),
        "all_output_max_scale_normalized_absolute_error": float(np.max(errors)),
        "exact_demand_saturated_records": int(np.sum(exact_saturated)),
        "end_pressure_lower_bound_saturated_records": int(np.sum(lower_saturated)),
        "encoded_saturated_records": int(np.sum(approx_saturated)),
        "saturation_flag_mismatch_count": int(np.sum(approx_saturated != exact_saturated)),
        "lower_bound_violation_count": int(np.sum(exact_lower > exact_demand + 1.0e-12)),
        "minimum_exact_demand_minus_tank_mol": float(np.min(exact_demand - exact_tank_total)),
        "minimum_lower_bound_minus_tank_mol": float(np.min(exact_lower - exact_tank_total)),
        "maximum_tank_start_total_mol": float(np.max(exact_tank_total)),
        "minimum_exact_integrated_demand_mol": float(np.min(exact_demand)),
        "modular_next_tank_underflow_count": int(np.sum(next_code < 0)),
        "meaningful_withdrawal_erased_count": int(
            np.sum((exact_withdrawal > MEANINGFUL_MOL) & (withdrawal_code == 0))
        ),
        "recorded_withdrawal_equals_start_max_abs_mol": float(
            np.max(np.abs(exact_withdrawal - exact_tank))
        ),
        "all_next_tanks_zero_at_threshold": bool(
            np.all(np.abs(exact_next) <= MEANINGFUL_MOL)
        ),
        "pressure_output_overflow_count": int(np.sum(pressure_code > pressure_levels)),
        "passes_declared_support_gate": False,
    }
    result["passes_declared_support_gate"] = bool(
        result["saturation_flag_mismatch_count"] == 0
        and result["lower_bound_violation_count"] == 0
        and result["end_pressure_lower_bound_saturated_records"] == len(records)
        and result["modular_next_tank_underflow_count"] == 0
        and result["meaningful_withdrawal_erased_count"] == 0
        and result["pressure_output_overflow_count"] == 0
        and result["demand_lower_p95_common_scale_normalized_absolute_error"]
        <= COMMON_P95_GATE
        and result["tank_total_p95_common_scale_normalized_absolute_error"]
        <= COMMON_P95_GATE
        and result["all_output_p95_scale_normalized_absolute_error"] <= COMMON_P95_GATE
    )
    design = {
        "pressure_weights": [int(value) for value in pressure_weights],
        "demand_weights": demand_weights,
        "tank_total_weights": tank_weights,
        "pressure_levels": pressure_levels,
        "common_levels": common_levels,
        "common_scale_mol": float(common_scale),
        "gas_bits": gas_bits,
        "pressure_bits": pressure_bits,
        "tank_bits": TANK_BITS,
    }
    return result, design


def build_circuit(design: dict) -> tuple[QuantumCircuit, dict]:
    gas_bits = int(design["gas_bits"])
    pressure_bits = int(design["pressure_bits"])
    tank_bits = int(design["tank_bits"])
    pressure_weights = [int(value) for value in design["pressure_weights"]]
    demand_weights = [int(value) for value in design["demand_weights"]]
    tank_weights = [int(value) for value in design["tank_total_weights"]]

    pressure_adder = WeightedAdder(len(pressure_weights), pressure_weights)
    demand_adder = WeightedAdder(pressure_bits, demand_weights)
    tank_adder = WeightedAdder(len(tank_weights), tank_weights)
    value_bits = max(demand_adder.num_sum_qubits, tank_adder.num_sum_qubits)
    compare_weights = [1 << bit for bit in range(value_bits)] * 2
    compare_adder = WeightedAdder(2 * value_bits, compare_weights)
    comparator = IntegerComparator(
        compare_adder.num_sum_qubits, (1 << value_bits) - 1, geq=True
    )
    work_bits = max(
        pressure_adder.num_ancillas,
        demand_adder.num_ancillas,
        tank_adder.num_ancillas,
        compare_adder.num_ancillas,
        comparator.num_ancillas,
    )

    endpoint_gas = QuantumRegister(len(COMPONENTS) * gas_bits, "endpoint_gas")
    tank_current = QuantumRegister(len(COMPONENTS) * tank_bits, "tank_current")
    withdrawal = QuantumRegister(len(COMPONENTS) * tank_bits, "withdrawal")
    tank_next = QuantumRegister(len(COMPONENTS) * tank_bits, "tank_next")
    demand_output = QuantumRegister(value_bits, "demand_lower")
    tank_total_output = QuantumRegister(value_bits, "tank_total")
    saturated_output = QuantumRegister(1, "saturated")
    pressure = QuantumRegister(pressure_bits, "pressure")
    pressure_sum = QuantumRegister(pressure_adder.num_sum_qubits, "pressure_sum")
    deficit = QuantumRegister(pressure_bits, "pressure_deficit")
    demand_value = QuantumRegister(value_bits, "demand_value")
    tank_value = QuantumRegister(value_bits, "tank_value")
    compare_sum = QuantumRegister(compare_adder.num_sum_qubits, "compare_sum")
    compare_flag = QuantumRegister(1, "compare_flag")
    work = QuantumRegister(work_bits, "work")
    circuit = QuantumCircuit(
        endpoint_gas,
        tank_current,
        withdrawal,
        tank_next,
        demand_output,
        tank_total_output,
        saturated_output,
        pressure,
        pressure_sum,
        deficit,
        demand_value,
        tank_value,
        compare_sum,
        compare_flag,
        work,
        name="clean_pressure_derived_saturated_tank_withdrawal",
    )

    pressure_qargs = (
        list(endpoint_gas)
        + list(pressure_sum)
        + list(work)[: pressure_adder.num_ancillas]
    )
    circuit.append(pressure_adder, pressure_qargs)
    for source, target in zip(pressure_sum, pressure):
        circuit.cx(source, target)

    for qubit in deficit:
        circuit.x(qubit)
    circuit.append(
        ModularAdderGate(pressure_bits).inverse(), list(pressure) + list(deficit)
    )
    demand_qargs = (
        list(deficit)
        + list(demand_value)[: demand_adder.num_sum_qubits]
        + list(work)[: demand_adder.num_ancillas]
    )
    tank_qargs = (
        list(tank_current)
        + list(tank_value)[: tank_adder.num_sum_qubits]
        + list(work)[: tank_adder.num_ancillas]
    )
    circuit.append(demand_adder, demand_qargs)
    circuit.append(tank_adder, tank_qargs)
    for source, target in zip(demand_value, demand_output):
        circuit.cx(source, target)
    for source, target in zip(tank_value, tank_total_output):
        circuit.cx(source, target)

    for qubit in tank_value:
        circuit.x(qubit)
    compare_qargs = (
        list(demand_value)
        + list(tank_value)
        + list(compare_sum)
        + list(work)[: compare_adder.num_ancillas]
    )
    circuit.append(compare_adder, compare_qargs)
    comparator_qargs = (
        list(compare_sum)
        + list(compare_flag)
        + list(work)[: comparator.num_ancillas]
    )
    circuit.append(comparator, comparator_qargs)
    circuit.cx(compare_flag[0], saturated_output[0])
    for source, target in zip(tank_current, withdrawal):
        circuit.ccx(compare_flag[0], source, target)
    for source, target in zip(tank_current, tank_next):
        circuit.cx(source, target)
    subtractor = ModularAdderGate(tank_bits).inverse()
    for component in range(len(COMPONENTS)):
        operand = list(withdrawal)[component * tank_bits : (component + 1) * tank_bits]
        target = list(tank_next)[component * tank_bits : (component + 1) * tank_bits]
        circuit.append(subtractor, operand + target)

    circuit.append(comparator.inverse(), comparator_qargs)
    circuit.append(compare_adder.inverse(), compare_qargs)
    for qubit in reversed(list(tank_value)):
        circuit.x(qubit)
    circuit.append(tank_adder.inverse(), tank_qargs)
    circuit.append(demand_adder.inverse(), demand_qargs)
    circuit.append(ModularAdderGate(pressure_bits), list(pressure) + list(deficit))
    for qubit in reversed(list(deficit)):
        circuit.x(qubit)
    for source, target in reversed(list(zip(list(pressure_sum), list(pressure)))):
        circuit.cx(source, target)
    circuit.append(pressure_adder.inverse(), pressure_qargs)

    return circuit, {
        "retained_inputs": [
            f"five x {gas_bits}-bit endpoint gas inventories",
            f"five x {tank_bits}-bit tank inventories",
        ],
        "clean_outputs": [
            f"{value_bits}-bit demand lower bound",
            f"{value_bits}-bit tank total",
            "saturation flag",
            f"five x {tank_bits}-bit withdrawal",
            f"five x {tank_bits}-bit next tank",
        ],
        "cleared": [
            "pressure",
            "pressure deficit",
            "demand and tank sums",
            "comparison sum and flag",
            "all weighted-adder workspace",
        ],
        "value_bits": int(value_bits),
    }


def resource_record(circuit: QuantumCircuit) -> dict:
    compiled = transpile(
        circuit,
        basis_gates=["u", "cx"],
        optimization_level=1,
        seed_transpiler=TRANSPILER_SEED,
    )
    counts = compiled.count_ops()
    return {
        "logical_qubits": int(circuit.num_qubits),
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
    records, replay = support_records()
    if len(records) != 128:
        raise AssertionError(len(records))
    context = load_context()
    selected_pressure = context.normalized["selected_pressure"]
    prior_tank = json.loads(PRIOR_TANK.read_text(encoding="utf-8"))
    tank_selected = prior_tank["tank_encoding"]["selected"]
    if int(tank_selected["bits"]) != TANK_BITS:
        raise AssertionError(tank_selected["bits"])

    screens = []
    designs = {}
    for bits in COMMON_BITS_CASES:
        row, design = encode_support(records, bits, selected_pressure, tank_selected)
        screens.append(row)
        designs[bits] = design
    selected = next((row for row in screens if row["passes_declared_support_gate"]), None)
    if selected is None:
        raise AssertionError(screens)
    selected_bits = int(selected["common_bits"])
    circuit, layout = build_circuit(designs[selected_bits])
    resources = resource_record(circuit)
    if resources["measurement"] or resources["reset"]:
        raise AssertionError(resources)

    flat_rows = []
    for record in records:
        flat_rows.append(
            {
                "sample": int(record["sample"]),
                "slot": int(record["slot"]),
                "bed": record["bed"],
                "step": record["step"],
                "reverse": bool(record["reverse"]),
                "endpoint_pressure_bar": float(record["endpoint_pressure_bar"]),
                "exact_integrated_demand_mol": float(record["exact_integrated_demand_mol"]),
                "end_pressure_demand_lower_bound_mol": float(record["end_pressure_demand_lower_bound_mol"]),
                "tank_start_total_mol": float(np.sum(record["tank_start_mol"])),
                "withdrawal_total_mol": float(np.sum(record["tank_withdrawal_mol"])),
                "tank_end_total_mol": float(np.sum(record["tank_end_mol"])),
                "exact_saturated": bool(
                    record["exact_integrated_demand_mol"]
                    >= float(np.sum(record["tank_start_mol"]))
                ),
                "lower_bound_saturated": bool(
                    record["end_pressure_demand_lower_bound_mol"]
                    >= float(np.sum(record["tank_start_mol"]))
                ),
            }
        )

    payload = {
        "schema": "psa-qae-cce-offledger-tank-saturation-interface/v1",
        "status": "frozen_support_pressure_derived_saturated_tank_withdrawal_compiled",
        "qpu_submission": False,
        "support": {
            "runs": 32,
            "tank_calls_per_final_cycle": 4,
            "records": len(records),
            "components": list(COMPONENTS),
            "pressure_source": "five raw endpoint component gas inventories",
            "demand_lower_bound": "k_in * duration * max(P_high - P_end, 0)",
            "P_high_bar": P_HIGH_BAR,
            "k_in_mol_s_bar": K_IN_MOL_S_BAR,
            "duration_s": PHASE_DURATION_S,
        },
        "replay": replay,
        "encoding_screen": screens,
        "selected_design": selected,
        "circuit_layout": layout,
        "compiled_clean_circuit": resources,
        "claim_boundary": {
            "supported": "on the frozen 128-call support, five raw endpoint gas inventories generate end pressure and a conservative demand proxy that proves every tank call saturated; the withdrawal QROM is replaced by a reversible saturation comparison, exact tank copy, and componentwise subtraction",
            "unsupported": "unsaturated proportional withdrawal allocation, a rigorous trajectory-wide analytic lower-bound proof outside the cached support, generation of phase-end endpoint gas from a monolithic phase unitary, adaptive integration, routing, external H2 validation, or quantum advantage",
        },
    }
    OUT_JSON.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, default=json_default),
        encoding="utf-8",
    )
    with OUT_CSV.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(flat_rows[0]))
        writer.writeheader()
        writer.writerows(flat_rows)
    OUT_MD.write_text(
        "# Pressure-derived saturated tank-withdrawal interface\n\n"
        f"Status: **{payload['status']}**\n\n"
        "The final-cycle support contains **128 tank calls**. Five encoded endpoint gas inventories reconstruct the source-end pressure, which generates the reversible end-pressure demand lower bound `k_in Δt max(P_high-P_end,0)`. The bound is compared with the five-component tank inventory; every cached call is saturated, so the clean withdrawal equals the current tank and the next tank is zero.\n\n"
        f"The exact integrated demand is at least **{selected['minimum_exact_integrated_demand_mol']:.6f} mol**, the maximum starting tank is **{selected['maximum_tank_start_total_mol']:.6f} mol**, and the minimum pressure-bound margin is **{selected['minimum_lower_bound_minus_tank_mol']:.6f} mol**. Saturation mismatches, lower-bound violations, underflows, and meaningful erasures are all zero.\n\n"
        f"The selected {selected_bits}-bit common encoding has p95 aggregate normalized error **{selected['all_output_p95_scale_normalized_absolute_error']:.3e}**. The clean all-to-all `u`/`CX` circuit uses **{resources['logical_qubits']:,} logical qubits**, depth **{resources['depth_all_to_all']:,}**, and **{resources['cx']:,} CX**, with no measurements or resets.\n\n"
        "This removes the recorded-withdrawal QROM on the frozen saturated branch. Unsaturated allocation, phase-end state generation inside a monolithic phase unitary, adaptive integration, routing, external H2 validation, and quantum advantage remain open.\n\n"
        "No QPU job was submitted.\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "status": payload["status"],
        "records": len(records),
        "selected_common_bits": selected_bits,
        "logical_qubits": resources["logical_qubits"],
        "depth": resources["depth_all_to_all"],
        "cx": resources["cx"],
        "qpu_submission": False,
    }, indent=2))


if __name__ == "__main__":
    main()
