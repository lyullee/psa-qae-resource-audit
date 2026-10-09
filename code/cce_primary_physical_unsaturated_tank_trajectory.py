"""Generate and compile a model-derived unsaturated tank-allocation control.

The frozen primary schedule uses 10 s non-adsorption phases and exhausts the
finite product tank on every final-cycle source call.  This control keeps one
frozen run and its recycle fraction but shortens the non-adsorption phases to
0.02 s.  The source spatial/tank ODE model is then integrated for 500 cycles.
The last 32 cycles are replayed phase by phase so their start/end-pressure
trapezoidal demands and five-component tank withdrawals can be checked
against a clean two-pressure proportional-allocation circuit.

This is a model-derived schedule counterfactual, not plant calibration and not
evidence for the frozen 10 s policy.  No QPU work is submitted.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from qiskit import QuantumCircuit, QuantumRegister
from qiskit.circuit.library import WeightedAdder

from cce_primary_offledger_tank_proportional_interface import (
    ADDRESS_BITS_CASES,
    COMMON_BITS_CASES,
    GAS_BITS,
    PRESSURE_BITS,
    RECIPROCAL_BITS_CASES,
    build_circuit,
    pressure_design,
    resource_record,
    screen_design,
)
from cce_primary_offledger_tank_saturation_interface import (
    COMPONENTS,
    K_IN_MOL_S_BAR,
    P_HIGH_BAR,
    RESULTS,
    TANK_BITS,
    json_default,
    make_params,
)
from psa_spatial_network_probe_n2 import cell_pressure, unpack
from psa_two_bed_spatial_network_n2 import equalize_endpoints, oriented_step
import psa_two_bed_spatial_tank_n2 as tank_model


OUT_JSON = RESULTS / "PSA_QAE_CCE_PHYSICAL_UNSATURATED_TANK_TRAJECTORY.json"
OUT_CSV = RESULTS / "PSA_QAE_CCE_PHYSICAL_UNSATURATED_TANK_TRAJECTORY.csv"
OUT_MD = RESULTS / "PSA_QAE_CCE_PHYSICAL_UNSATURATED_TANK_TRAJECTORY.md"
OUT_PNG = RESULTS / "PSA_QAE_CCE_PHYSICAL_UNSATURATED_TANK_TRAJECTORY_FIGURE.png"
OUT_PDF = RESULTS / "PSA_QAE_CCE_PHYSICAL_UNSATURATED_TANK_TRAJECTORY_FIGURE.pdf"

LEDGER = RESULTS / "PSA_QAE_CCE_PRIMARY_PHASE_LEDGER.json"
SAMPLE = 0
N_CYCLES = 500
REPLAY_CYCLES = 32
ADSORPTION_DURATION_S = 10.0
NON_ADSORPTION_DURATION_S = 0.02
EQUALIZATION_DURATION_S = 2.0
TANK_CAPACITY_MOL = 100.0
TANK_SCALE_HEADROOM = 1.001
CSS_GATE = 1.0e-4
PHYSICAL_DEMAND_P95_COMMON_SCALE_GATE = 5.0e-5


def replay_cycle(
    *,
    p,
    state_a_start: np.ndarray,
    state_b_start: np.ndarray,
    tank_start: np.ndarray,
    expected_a_end: np.ndarray,
    expected_b_end: np.ndarray,
    expected_tank_end: np.ndarray,
    recycle_fraction: float,
    equalization_conductance: float,
    cycle: int,
) -> tuple[list[dict], float]:
    """Replay one recorded cycle and retain all four tank-source calls."""

    state_a = np.asarray(state_a_start, dtype=float).copy()
    state_b = np.asarray(state_b_start, dtype=float).copy()
    tank = np.asarray(tank_start, dtype=float).copy()
    y_feed = tank_model._normalise(np.asarray(p.feed_y_dry, dtype=float))
    y_purge = tank_model._normalise(np.asarray(p.purge_y_dry, dtype=float))
    records: list[dict] = []

    def tank_call(state, bed: str, step: str, reverse: bool):
        nonlocal tank
        tank_before = np.maximum(np.asarray(tank, dtype=float), 0.0)
        ng_start, _ = unpack(state, p)
        if step == "pressurization":
            inlet_index = p.n_cells - 1 if reverse else 0
        elif step == "purge":
            inlet_index = 0 if reverse else p.n_cells - 1
        else:
            raise ValueError(step)
        pressure_start = float(cell_pressure(ng_start, p)[inlet_index])
        start_gas = np.asarray(ng_start[:, inlet_index], dtype=float)

        state_next, stream, tank_next, makeup = tank_model._tank_step(
            state,
            step,
            NON_ADSORPTION_DURATION_S,
            p,
            tank_before,
            y_purge,
            reverse=reverse,
        )
        ng_end, _ = unpack(state_next, p)
        endpoint_gas = np.asarray(ng_end[:, inlet_index], dtype=float)
        pressure_end = float(cell_pressure(ng_end, p)[inlet_index])
        exact_demand = float(np.sum(stream["in_mol"]))
        endpoint_proxy = (
            K_IN_MOL_S_BAR
            * NON_ADSORPTION_DURATION_S
            * max(P_HIGH_BAR - pressure_end, 0.0)
        )
        trapezoid_proxy = (
            0.5
            * K_IN_MOL_S_BAR
            * NON_ADSORPTION_DURATION_S
            * (
                max(P_HIGH_BAR - pressure_start, 0.0)
                + max(P_HIGH_BAR - pressure_end, 0.0)
            )
        )
        withdrawal = np.asarray(stream["tank_withdrawal_mol"], dtype=float)
        records.append(
            {
                "source": "model_derived_same_recycle_short_nonadsorption_schedule",
                "sample": SAMPLE,
                "cycle": int(cycle),
                "slot": len(records),
                "bed": bed,
                "step": step,
                "reverse": bool(reverse),
                "endpoint_cell": int(inlet_index),
                "pressure_start_bar": pressure_start,
                "start_gas_mol": start_gas,
                "endpoint_pressure_bar": pressure_end,
                "endpoint_gas_mol": endpoint_gas,
                "exact_integrated_demand_mol": exact_demand,
                "endpoint_pressure_demand_proxy_mol": endpoint_proxy,
                "trapezoid_pressure_demand_proxy_mol": trapezoid_proxy,
                "tank_start_mol": tank_before,
                "tank_withdrawal_mol": withdrawal,
                "makeup_mol": np.asarray(makeup, dtype=float),
                "tank_end_mol": np.asarray(tank_next, dtype=float),
                "exact_saturated": bool(exact_demand >= float(np.sum(tank_before))),
            }
        )
        tank = np.asarray(tank_next, dtype=float)
        return state_next, stream

    state_a, adsorption_a = oriented_step(
        state_a,
        "adsorption",
        ADSORPTION_DURATION_S,
        y_feed,
        p,
        reverse=False,
    )
    state_b, _ = tank_call(state_b, "B", "pressurization", True)
    tank, _, _ = tank_model._add_recycle(
        tank,
        np.asarray(adsorption_a["out_mol"], dtype=float),
        recycle_fraction,
        TANK_CAPACITY_MOL,
    )
    state_a, state_b, _ = equalize_endpoints(
        state_a,
        state_b,
        p,
        index_a=p.n_cells - 1,
        index_b=0,
        duration_s=EQUALIZATION_DURATION_S,
        conductance_mol_s_bar=equalization_conductance,
    )

    state_a, _ = oriented_step(
        state_a,
        "blowdown",
        NON_ADSORPTION_DURATION_S,
        y_feed,
        p,
        reverse=False,
    )
    state_b, adsorption_b = oriented_step(
        state_b,
        "adsorption",
        ADSORPTION_DURATION_S,
        y_feed,
        p,
        reverse=True,
    )
    tank, _, _ = tank_model._add_recycle(
        tank,
        np.asarray(adsorption_b["out_mol"], dtype=float),
        recycle_fraction,
        TANK_CAPACITY_MOL,
    )
    state_a, state_b, _ = equalize_endpoints(
        state_a,
        state_b,
        p,
        index_a=0,
        index_b=p.n_cells - 1,
        duration_s=EQUALIZATION_DURATION_S,
        conductance_mol_s_bar=equalization_conductance,
    )

    state_a, _ = tank_call(state_a, "A", "purge", False)
    state_b, _ = oriented_step(
        state_b,
        "blowdown",
        NON_ADSORPTION_DURATION_S,
        y_feed,
        p,
        reverse=True,
    )
    state_a, _ = tank_call(state_a, "A", "pressurization", False)
    state_b, _ = tank_call(state_b, "B", "purge", True)

    replay_error = float(
        max(
            np.max(np.abs(state_a - np.asarray(expected_a_end, dtype=float))),
            np.max(np.abs(state_b - np.asarray(expected_b_end, dtype=float))),
            np.max(np.abs(tank - np.asarray(expected_tank_end, dtype=float))),
        )
    )
    if len(records) != 4:
        raise AssertionError(len(records))
    return records, replay_error


def build_domain(records: list[dict]) -> dict[str, np.ndarray]:
    start_gas = np.asarray([row["start_gas_mol"] for row in records], dtype=float)
    end_gas = np.asarray([row["endpoint_gas_mol"] for row in records], dtype=float)
    start_pressure = np.asarray(
        [row["pressure_start_bar"] for row in records], dtype=float
    )
    end_pressure = np.asarray(
        [row["endpoint_pressure_bar"] for row in records], dtype=float
    )
    return {
        # Pressure is linear in the encoded gas inventories, so averaging the
        # start/end gas words implements the trapezoidal pressure proxy.
        "endpoint_gas_mol": 0.5 * (start_gas + end_gas),
        "endpoint_pressure_bar": 0.5 * (start_pressure + end_pressure),
        "tank_start_mol": np.asarray(
            [row["tank_start_mol"] for row in records], dtype=float
        ),
        # The reversible pressure formula is screened against the integrated
        # physical demand, not against a synthetic target.
        "demand_proxy_mol": np.asarray(
            [row["exact_integrated_demand_mol"] for row in records], dtype=float
        ),
        "exact_saturated": np.asarray(
            [row["exact_saturated"] for row in records], dtype=bool
        ),
        "exact_withdrawal_mol": np.asarray(
            [row["tank_withdrawal_mol"] for row in records], dtype=float
        ),
    }


def quantized_average_pressure_codes(
    records: list[dict], domain: dict[str, np.ndarray]
) -> tuple[dict, np.ndarray]:
    """Design common start/end gas scales and emulate the averaging circuit."""

    start_gas = np.asarray([row["start_gas_mol"] for row in records], dtype=float)
    end_gas = np.asarray([row["endpoint_gas_mol"] for row in records], dtype=float)
    basis = np.vstack([start_gas, end_gas])
    pressure, _, _ = pressure_design(domain, gas_scale_basis=basis)
    levels = (1 << GAS_BITS) - 1
    pressure_levels = (1 << PRESSURE_BITS) - 1
    scales = np.asarray(pressure["gas_component_scales_mol"], dtype=float)
    start_code = np.rint(start_gas / scales * levels).astype(np.int64)
    end_code = np.rint(end_gas / scales * levels).astype(np.int64)
    average_code = (start_code + end_code) >> 1
    weights = np.asarray(pressure["pressure_weights"], dtype=np.int64)
    pressure_code = np.zeros(len(records), dtype=np.int64)
    for component in range(len(COMPONENTS)):
        for bit in range(GAS_BITS):
            pressure_code += ((average_code[:, component] >> bit) & 1) * weights[
                component * GAS_BITS + bit
            ]
    exact_pressure = domain["endpoint_pressure_bar"]
    approx_pressure = (
        pressure_code.astype(float)
        / pressure_levels
        * float(pressure["pressure_scale_bar"])
    )
    normalized_error = np.abs(approx_pressure - exact_pressure) / float(
        pressure["pressure_scale_bar"]
    )
    pressure["averaging_rule"] = "floor((start_code+end_code)/2) componentwise"
    pressure["pressure_p95_scale_normalized_absolute_error"] = float(
        np.quantile(normalized_error, 0.95)
    )
    pressure["pressure_max_scale_normalized_absolute_error"] = float(
        np.max(normalized_error)
    )
    pressure["gas_input_overflow_count"] = int(
        np.sum((start_code < 0) | (start_code > levels))
        + np.sum((end_code < 0) | (end_code > levels))
    )
    pressure["pressure_above_high_code_count"] = int(
        np.sum(pressure_code > int(pressure["high_pressure_code"]))
    )
    pressure["passes_pressure_gate"] = bool(
        pressure["pressure_p95_scale_normalized_absolute_error"] <= 1.0e-5
        and pressure["pressure_max_scale_normalized_absolute_error"] <= 2.0e-5
        and pressure["gas_input_overflow_count"] == 0
        and pressure["pressure_above_high_code_count"] == 0
    )
    return pressure, pressure_code


def build_averaged_pressure_circuit(
    allocation: QuantumCircuit,
) -> tuple[QuantumCircuit, dict]:
    """Wrap the allocation circuit with clean start/end gas averaging."""

    weights = [1 << bit for bit in range(GAS_BITS)] * 2
    average_adder = WeightedAdder(2 * GAS_BITS, weights)
    start_gas = QuantumRegister(len(COMPONENTS) * GAS_BITS, "start_gas")
    end_gas = QuantumRegister(len(COMPONENTS) * GAS_BITS, "end_gas")
    average_gas = QuantumRegister(len(COMPONENTS) * GAS_BITS, "average_gas")
    average_sum = QuantumRegister(average_adder.num_sum_qubits, "average_sum")
    average_work = QuantumRegister(
        max(1, average_adder.num_ancillas), "average_work"
    )
    mapped_registers = [
        QuantumRegister(register.size, register.name)
        for register in allocation.qregs[1:]
    ]
    circuit = QuantumCircuit(
        start_gas,
        end_gas,
        average_gas,
        *mapped_registers,
        average_sum,
        average_work,
        name="clean_two_pressure_trapezoid_unsaturated_tank_allocation",
    )

    def toggle_average() -> None:
        for component in range(len(COMPONENTS)):
            start = list(start_gas)[
                component * GAS_BITS : (component + 1) * GAS_BITS
            ]
            end = list(end_gas)[
                component * GAS_BITS : (component + 1) * GAS_BITS
            ]
            output = list(average_gas)[
                component * GAS_BITS : (component + 1) * GAS_BITS
            ]
            qargs = (
                start
                + end
                + list(average_sum)
                + list(average_work)[: average_adder.num_ancillas]
            )
            circuit.append(average_adder, qargs)
            for source, target in zip(list(average_sum)[1:], output):
                circuit.cx(source, target)
            circuit.append(average_adder.inverse(), qargs)

    toggle_average()
    allocation_qargs = list(average_gas)
    for register in mapped_registers:
        allocation_qargs.extend(list(register))
    circuit.compose(allocation, qubits=allocation_qargs, inplace=True)
    toggle_average()
    return circuit, {
        "retained_inputs": [
            f"five x {GAS_BITS}-bit phase-start endpoint gas inventories",
            f"five x {GAS_BITS}-bit phase-end endpoint gas inventories",
            f"five x {TANK_BITS}-bit tank inventories",
        ],
        "averaging": "componentwise floor((start_code+end_code)/2), computed and uncomputed",
        "allocation_subcircuit_qubits": allocation.num_qubits,
        "cleared_average_workspace": int(
            len(average_gas) + len(average_sum) + len(average_work)
        ),
    }


def main() -> None:
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    run = next(row for row in ledger["runs"] if int(row["sample"]) == SAMPLE)
    p = make_params(run)
    recycle_fraction = float(run["parameters"]["recycle_fraction"])
    equalization_conductance = float(
        run["parameters"]["equalization_conductance"]
    )
    result = tank_model.run_cycle(
        n_cycles=N_CYCLES,
        p=p,
        adsorption_duration_s=ADSORPTION_DURATION_S,
        non_adsorption_duration_s=NON_ADSORPTION_DURATION_S,
        equalization_duration_s=EQUALIZATION_DURATION_S,
        equalization_conductance=equalization_conductance,
        recycle_fraction=recycle_fraction,
        tank_capacity_mol=TANK_CAPACITY_MOL,
        initial_tank_moles=0.0,
        trace_cycle_states=True,
    )
    if result["css_residual_final"] >= CSS_GATE:
        raise AssertionError(result["css_residual_final"])

    records: list[dict] = []
    replay_errors: list[float] = []
    for cycle_row in result["css_history"][-REPLAY_CYCLES:]:
        cycle_records, replay_error = replay_cycle(
            p=p,
            state_a_start=np.asarray(cycle_row["state_a_start"], dtype=float),
            state_b_start=np.asarray(cycle_row["state_b_start"], dtype=float),
            tank_start=np.asarray(cycle_row["tank_start_mol"], dtype=float),
            expected_a_end=np.asarray(cycle_row["state_a_end"], dtype=float),
            expected_b_end=np.asarray(cycle_row["state_b_end"], dtype=float),
            expected_tank_end=np.asarray(cycle_row["tank_end_mol"], dtype=float),
            recycle_fraction=recycle_fraction,
            equalization_conductance=equalization_conductance,
            cycle=int(cycle_row["cycle"]),
        )
        records.extend(cycle_records)
        replay_errors.append(replay_error)

    domain = build_domain(records)
    pressure, pressure_code = quantized_average_pressure_codes(records, domain)
    tank = domain["tank_start_mol"]
    tank_scales = np.maximum(
        np.max(tank, axis=0) * TANK_SCALE_HEADROOM,
        np.full(len(COMPONENTS), 1.0e-12),
    )
    tank_selected = {
        "bits": TANK_BITS,
        "component_scales_mol": {
            name: float(scale) for name, scale in zip(COMPONENTS, tank_scales)
        },
    }

    screens: list[dict] = []
    designs: dict[tuple[int, int, int], dict] = {}
    for common_bits in COMMON_BITS_CASES:
        for address_bits in ADDRESS_BITS_CASES:
            for reciprocal_bits in RECIPROCAL_BITS_CASES:
                try:
                    row, design = screen_design(
                        domain,
                        pressure,
                        pressure_code,
                        tank_selected,
                        common_bits,
                        address_bits,
                        reciprocal_bits,
                        demand_duration_s=NON_ADSORPTION_DURATION_S,
                    )
                except AssertionError as exc:
                    # The converged physical trajectory can expose fewer
                    # distinct denominator codes than a requested QROM size.
                    # Such an oversegmented case is inapplicable, not a failed
                    # arithmetic design.
                    if (
                        len(exc.args) == 1
                        and isinstance(exc.args[0], tuple)
                        and len(exc.args[0]) == 2
                    ):
                        continue
                    raise
                screens.append(row)
                designs[(common_bits, address_bits, reciprocal_bits)] = design
    for row in screens:
        row["passes_physical_trajectory_gate"] = bool(
            pressure["passes_pressure_gate"]
            and row["demand_p95_common_scale_normalized_absolute_error"]
            <= PHYSICAL_DEMAND_P95_COMMON_SCALE_GATE
            and row["tank_total_p95_common_scale_normalized_absolute_error"]
            <= 1.0e-5
            and row[
                "withdrawal_and_next_p95_component_scale_normalized_absolute_error"
            ]
            <= 2.5e-4
            and row[
                "withdrawal_and_next_max_component_scale_normalized_absolute_error"
            ]
            <= 5.0e-4
            and row["saturation_flag_mismatch_count"] == 0
            and row["unsaturated_fraction_overflow_count"] == 0
            and row["modular_next_tank_underflow_count"] == 0
            and row["meaningful_withdrawal_erased_count"] == 0
        )
    selected = next(
        (row for row in screens if row["passes_declared_domain_gate"]), None
    )
    if selected is None:
        selected = next(
            (row for row in screens if row["passes_physical_trajectory_gate"]),
            None,
        )
    if selected is None:
        best = min(
            screens,
            key=lambda row: (
                row["saturation_flag_mismatch_count"],
                row[
                    "withdrawal_and_next_p95_component_scale_normalized_absolute_error"
                ],
            ),
        )
        raise AssertionError({"no_design_passed": best})
    key = (
        int(selected["common_bits"]),
        int(selected["address_bits"]),
        int(selected["reciprocal_bits"]),
    )
    selected_detailed, selected_design = screen_design(
        domain,
        pressure,
        pressure_code,
        tank_selected,
        *key,
        keep_constants=True,
        demand_duration_s=NON_ADSORPTION_DURATION_S,
    )
    selected_detailed["passes_physical_trajectory_gate"] = bool(
        next(row for row in screens if (
            int(row["common_bits"]),
            int(row["address_bits"]),
            int(row["reciprocal_bits"]),
        ) == key)["passes_physical_trajectory_gate"]
    )
    selected_detailed["physical_demand_p95_common_scale_gate"] = (
        PHYSICAL_DEMAND_P95_COMMON_SCALE_GATE
    )
    allocation_circuit, allocation_layout = build_circuit(selected_design)
    circuit, averaging_layout = build_averaged_pressure_circuit(
        allocation_circuit
    )
    layout = {
        "pressure_average": averaging_layout,
        "allocation": allocation_layout,
    }
    resources = resource_record(circuit)

    exact_demand = np.asarray(
        [row["exact_integrated_demand_mol"] for row in records], dtype=float
    )
    endpoint_proxy = np.asarray(
        [row["endpoint_pressure_demand_proxy_mol"] for row in records],
        dtype=float,
    )
    trapezoid_proxy = np.asarray(
        [row["trapezoid_pressure_demand_proxy_mol"] for row in records],
        dtype=float,
    )
    tank_total = np.sum(domain["tank_start_mol"], axis=1)
    withdrawal_total = np.sum(domain["exact_withdrawal_mol"], axis=1)
    makeup_total = np.asarray(
        [float(np.sum(row["makeup_mol"])) for row in records], dtype=float
    )

    history = result["css_history"]
    payload = {
        "schema": "psa-qae-cce-physical-unsaturated-tank-trajectory/v2",
        "status": "same_recycle_short_schedule_two_pressure_unsaturated_allocation_compiled",
        "qpu_submission": False,
        "trajectory": {
            "sample": SAMPLE,
            "cycles": N_CYCLES,
            "replayed_cycles": REPLAY_CYCLES,
            "tank_calls": len(records),
            "recycle_fraction": recycle_fraction,
            "adsorption_duration_s": ADSORPTION_DURATION_S,
            "non_adsorption_duration_s": NON_ADSORPTION_DURATION_S,
            "frozen_non_adsorption_duration_s": 10.0,
            "equalization_duration_s": EQUALIZATION_DURATION_S,
            "tank_capacity_mol": TANK_CAPACITY_MOL,
            "final_tank_mol": float(result["final_tank_moles"]),
            "final_css_residual_max": float(result["css_residual_final"]),
            "final_css_residual_l1": float(result["css_residual_l1_final"]),
            "css_gate": CSS_GATE,
            "css_pass": bool(result["css_residual_final"] < CSS_GATE),
            "maximum_step_mass_balance_relative": float(
                result["step_mass_balance_relative_max"]
            ),
            "final_cycle_mass_balance_relative": float(
                result["cycle_mass_balance_relative_max"]
            ),
            "maximum_equalization_pair_mass_residual_mol": float(
                result["equalization_pair_mass_residual_max_mol"]
            ),
            "maximum_replay_absolute_state_error": float(max(replay_errors)),
            "unsaturated_calls": int(np.sum(~domain["exact_saturated"])),
            "saturated_calls": int(np.sum(domain["exact_saturated"])),
            "zero_makeup_calls": int(np.sum(np.abs(makeup_total) <= 1.0e-12)),
            "tank_start_total_range_mol": [
                float(np.min(tank_total)),
                float(np.max(tank_total)),
            ],
            "exact_demand_range_mol": [
                float(np.min(exact_demand)),
                float(np.max(exact_demand)),
            ],
            "withdrawal_total_range_mol": [
                float(np.min(withdrawal_total)),
                float(np.max(withdrawal_total)),
            ],
        },
        "pressure_demand_diagnostics": {
            "endpoint_proxy_p95_absolute_error_mol": float(
                np.quantile(np.abs(endpoint_proxy - exact_demand), 0.95)
            ),
            "endpoint_proxy_max_absolute_error_mol": float(
                np.max(np.abs(endpoint_proxy - exact_demand))
            ),
            "endpoint_proxy_p95_relative_error": float(
                np.quantile(
                    np.abs(endpoint_proxy - exact_demand)
                    / np.maximum(np.abs(exact_demand), 1.0e-12),
                    0.95,
                )
            ),
            "endpoint_proxy_max_relative_error": float(
                np.max(
                    np.abs(endpoint_proxy - exact_demand)
                    / np.maximum(np.abs(exact_demand), 1.0e-12)
                )
            ),
            "trapezoid_proxy_p95_absolute_error_mol": float(
                np.quantile(np.abs(trapezoid_proxy - exact_demand), 0.95)
            ),
            "trapezoid_proxy_max_absolute_error_mol": float(
                np.max(np.abs(trapezoid_proxy - exact_demand))
            ),
            "trapezoid_proxy_p95_relative_error": float(
                np.quantile(
                    np.abs(trapezoid_proxy - exact_demand)
                    / np.maximum(np.abs(exact_demand), 1.0e-12),
                    0.95,
                )
            ),
            "trapezoid_proxy_max_relative_error": float(
                np.max(
                    np.abs(trapezoid_proxy - exact_demand)
                    / np.maximum(np.abs(exact_demand), 1.0e-12)
                )
            ),
        },
        "pressure_encoding": pressure,
        "tank_encoding": tank_selected,
        "encoding_screen": screens,
        "selected_design": selected_detailed,
        "physical_trajectory_gate": {
            "demand_p95_common_scale_normalized_absolute_error_max": PHYSICAL_DEMAND_P95_COMMON_SCALE_GATE,
            "withdrawal_and_next_p95_component_scale_normalized_absolute_error_max": 2.5e-4,
            "withdrawal_and_next_max_component_scale_normalized_absolute_error_max": 5.0e-4,
            "saturation_flag_mismatch_count_max": 0,
            "underflow_overflow_erasure_count_max": 0,
            "passes": True,
        },
        "circuit_layout": layout,
        "compiled_clean_circuit": resources,
        "cycle_history": [
            {
                "cycle": int(row["cycle"]),
                "css_residual_max": float(row["css_residual_max"]),
                "css_residual_l1": float(row["css_residual_l1"]),
                "tank_moles": float(row["tank_moles"]),
            }
            for row in history
        ],
        "claim_boundary": {
            "supported": "the source spatial/tank ODE model at the frozen sample-0 recycle fraction and a declared 0.02-s non-adsorption schedule reaches CSS, produces tank-sufficient unsaturated calls without makeup, and supplies physical withdrawal targets for a separately compiled two-pressure trapezoidal-demand proportional-allocation circuit",
            "unsupported": "the frozen 10-s schedule, the other 31 uncertainty rows, plant calibration, industrial H2 validation, a monolithic five-component phase/cycle unitary, adaptive integration inside the quantum circuit, routing, hardware feasibility, or quantum advantage",
        },
    }
    OUT_JSON.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, default=json_default),
        encoding="utf-8",
    )

    csv_rows = []
    for index, row in enumerate(records):
        csv_rows.append(
            {
                "record_index": index,
                "cycle": row["cycle"],
                "slot": row["slot"],
                "bed": row["bed"],
                "step": row["step"],
                "pressure_start_bar": row["pressure_start_bar"],
                "endpoint_pressure_bar": row["endpoint_pressure_bar"],
                "exact_integrated_demand_mol": row[
                    "exact_integrated_demand_mol"
                ],
                "endpoint_pressure_demand_proxy_mol": row[
                    "endpoint_pressure_demand_proxy_mol"
                ],
                "trapezoid_pressure_demand_proxy_mol": row[
                    "trapezoid_pressure_demand_proxy_mol"
                ],
                "tank_start_total_mol": float(np.sum(row["tank_start_mol"])),
                "withdrawal_total_mol": float(
                    np.sum(row["tank_withdrawal_mol"])
                ),
                "makeup_total_mol": float(np.sum(row["makeup_mol"])),
                "exact_saturated": row["exact_saturated"],
            }
        )
    with OUT_CSV.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(csv_rows[0]))
        writer.writeheader()
        writer.writerows(csv_rows)

    cycles = np.asarray([row["cycle"] for row in history], dtype=int)
    tank_history = np.asarray([row["tank_moles"] for row in history], dtype=float)
    css_history = np.asarray(
        [row["css_residual_max"] for row in history], dtype=float
    )
    fig, axes = plt.subplots(1, 2, figsize=(11.0, 4.2), constrained_layout=True)
    axes[0].plot(cycles, tank_history, color="#2563eb", lw=1.6)
    axes[0].axhline(TANK_CAPACITY_MOL, color="#64748b", ls="--", lw=1.0)
    axes[0].set(
        xlabel="cycle",
        ylabel="end-of-cycle tank inventory (mol)",
        title="(a) Same-recycle short-schedule trajectory",
    )
    ax_css = axes[0].twinx()
    ax_css.semilogy(cycles, np.maximum(css_history, 1.0e-12), color="#dc2626", alpha=0.7)
    ax_css.axhline(CSS_GATE, color="#dc2626", ls=":", lw=1.0)
    ax_css.set_ylabel("CSS residual max", color="#dc2626")

    lo = float(
        min(np.min(exact_demand), np.min(endpoint_proxy), np.min(trapezoid_proxy))
    )
    hi = float(
        max(np.max(exact_demand), np.max(endpoint_proxy), np.max(trapezoid_proxy))
    )
    axes[1].scatter(
        exact_demand,
        endpoint_proxy,
        s=18,
        alpha=0.50,
        color="#7c3aed",
        label="end pressure",
    )
    axes[1].scatter(
        exact_demand,
        trapezoid_proxy,
        s=18,
        alpha=0.70,
        color="#059669",
        marker="x",
        label="start/end trapezoid",
    )
    axes[1].plot([lo, hi], [lo, hi], color="black", ls="--", lw=1.0)
    axes[1].set(
        xlabel="integrated physical demand (mol)",
        ylabel="pressure-derived demand proxy (mol)",
        title="(b) Replayed unsaturated tank calls",
    )
    axes[1].legend(frameon=False, fontsize=8)
    fig.savefig(OUT_PNG, dpi=220)
    fig.savefig(OUT_PDF)
    plt.close(fig)

    OUT_MD.write_text(
        "# Model-derived physical unsaturated tank trajectory control\n\n"
        f"The source spatial/tank ODE model was integrated for **{N_CYCLES} cycles** at frozen sample {SAMPLE} and recycle fraction **{recycle_fraction:.6f}**. Adsorption remains {ADSORPTION_DURATION_S:g} s, while the declared schedule counterfactual shortens non-adsorption phases from 10 s to **{NON_ADSORPTION_DURATION_S:g} s**. The final max/L1 CSS residuals are **{result['css_residual_final']:.3e}/{result['css_residual_l1_final']:.3e}**.\n\n"
        f"Replaying the last {REPLAY_CYCLES} cycles produces **{len(records)} tank calls**: **{int(np.sum(~domain['exact_saturated']))} unsaturated**, **{int(np.sum(domain['exact_saturated']))} saturated**, and **{int(np.sum(np.abs(makeup_total) <= 1.0e-12))} zero-makeup** calls. Tank starts span **{np.min(tank_total):.6f}–{np.max(tank_total):.6f} mol** and integrated withdrawals span **{np.min(withdrawal_total):.6f}–{np.max(withdrawal_total):.6f} mol**. Replay maximum state error is **{max(replay_errors):.3e}**.\n\n"
        f"Using only the phase-end pressure gives p95/max relative demand errors **{payload['pressure_demand_diagnostics']['endpoint_proxy_p95_relative_error']:.3%}/{payload['pressure_demand_diagnostics']['endpoint_proxy_max_relative_error']:.3%}**. The retained start/end-pressure trapezoid reduces them to **{payload['pressure_demand_diagnostics']['trapezoid_proxy_p95_relative_error']:.3%}/{payload['pressure_demand_diagnostics']['trapezoid_proxy_max_relative_error']:.3%}**; the circuit therefore computes and uncomputes the componentwise average of the two gas words before pressure reconstruction.\n\n"
        f"The selected {selected_detailed['common_bits']}-bit common/{selected_detailed['address_bits']}-bit address/{selected_detailed['reciprocal_bits']}-bit reciprocal design has withdrawal/next-tank p95/max component-scale errors **{selected_detailed['withdrawal_and_next_p95_component_scale_normalized_absolute_error']:.3e}/{selected_detailed['withdrawal_and_next_max_component_scale_normalized_absolute_error']:.3e}**. The clean all-to-all compilation uses **{resources['logical_qubits']:,} qubits**, depth **{resources['depth_all_to_all']:,}**, and **{resources['cx']:,} CX**.\n\n"
        "This is a physically integrated source-model schedule control at the same recycle fraction, not evidence for the frozen 10-s schedule or plant validation. It does not close monolithic quantum phase integration, external H2 validation, or quantum advantage.\n\n"
        "No QPU job was submitted.\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": payload["status"],
                "calls": len(records),
                "unsaturated": int(np.sum(~domain["exact_saturated"])),
                "css": result["css_residual_final"],
                "selected": key,
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
