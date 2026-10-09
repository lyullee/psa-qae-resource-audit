"""Connect the coherent run address to five-component LDF coefficients.

The existing finite-support controller loads eleven 12-bit run parameters and
decodes the six paired-bed schedule stages.  This module consumes the loaded
capacity, affinity, and LDF-factor words in reversible arithmetic.  It forms
the capacity-affinity product, maps it to five component equilibrium
prefactors, maps the LDF factor to five kinetic coefficients, and derives the
two bed-adsorption flags from the decoded schedule.

This closes a specific controller-to-kinetics interface on the frozen 32-run
support.  Pressure/composition evaluation, reciprocal division, loading-state
updates, tank demand outside the ledger, and phase integration remain separate.
No QPU work is submitted.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
from qiskit import QuantumCircuit, QuantumRegister, transpile
from qiskit.circuit.library import MultiplierGate, WeightedAdder
from qiskit.synthesis.multi_controlled import synth_mcx_n_clean_m15

from cce_primary_coherent_run_schedule_tank_interface import (
    COMPONENTS,
    LEDGER,
    PARAMETERS,
    PARAMETER_BITS,
    RESULTS,
    SCHEDULE,
    STEP_CODE,
    TRANSPILER_SEED,
    append_qrom,
    make_schedule_rows,
    parameter_tables,
)
from cce_primary_qstar_ldf_reversible_microstep import physical_constants
from psa_spatial_network_probe_n2 import LDF


OUT_JSON = RESULTS / "PSA_QAE_CCE_COHERENT_RUN_FACTOR_LDF_INTERFACE.json"
OUT_CSV = RESULTS / "PSA_QAE_CCE_COHERENT_RUN_FACTOR_LDF_INTERFACE.csv"
OUT_MD = RESULTS / "PSA_QAE_CCE_COHERENT_RUN_FACTOR_LDF_INTERFACE.md"

COEFFICIENT_SCALE_BITS = 20
COEFFICIENT_SCALE = 1 << COEFFICIENT_SCALE_BITS
RELATIVE_ERROR_GATE = 5.0e-3


def integer_weights_for_affine_product(
    capacity_min: float,
    capacity_span: float,
    affinity_min: float,
    affinity_span: float,
) -> list[int]:
    """Weights for S*(c0+dc*c/L)*(a0+da*a/L)."""

    levels = (1 << PARAMETER_BITS) - 1
    weights = [int(round(capacity_min * affinity_min * COEFFICIENT_SCALE))]
    weights += [
        int(
            round(
                affinity_min
                * capacity_span
                / levels
                * COEFFICIENT_SCALE
                * (1 << bit)
            )
        )
        for bit in range(PARAMETER_BITS)
    ]
    weights += [
        int(
            round(
                capacity_min
                * affinity_span
                / levels
                * COEFFICIENT_SCALE
                * (1 << bit)
            )
        )
        for bit in range(PARAMETER_BITS)
    ]
    weights += [
        int(
            round(
                capacity_span
                * affinity_span
                / (levels * levels)
                * COEFFICIENT_SCALE
                * (1 << bit)
            )
        )
        for bit in range(2 * PARAMETER_BITS)
    ]
    return weights


def integer_weights_for_affine(
    lower: float,
    span: float,
) -> list[int]:
    levels = (1 << PARAMETER_BITS) - 1
    return [int(round(lower * COEFFICIENT_SCALE))] + [
        int(round(span / levels * COEFFICIENT_SCALE * (1 << bit)))
        for bit in range(PARAMETER_BITS)
    ]


def constant_multiplier_weights(input_bits: int, constant: float) -> list[int]:
    return [int(round(constant * (1 << bit))) for bit in range(input_bits)]


def weighted_code(value: int, weights: list[int], *, constant: bool = False) -> int:
    offset = int(weights[0]) if constant else 0
    active = weights[1:] if constant else weights
    return offset + sum(
        int(weight) for bit, weight in enumerate(active) if (int(value) >> bit) & 1
    )


def product_weighted_code(
    capacity_code: int,
    affinity_code: int,
    weights: list[int],
) -> int:
    product = int(capacity_code) * int(affinity_code)
    cursor = 1
    result = int(weights[0])
    for value, width in (
        (capacity_code, PARAMETER_BITS),
        (affinity_code, PARAMETER_BITS),
        (product, 2 * PARAMETER_BITS),
    ):
        result += sum(
            int(weights[cursor + bit])
            for bit in range(width)
            if (int(value) >> bit) & 1
        )
        cursor += width
    return result


def component_weights(input_bits: int, constants: np.ndarray) -> list[list[int]]:
    return [
        constant_multiplier_weights(input_bits, float(value)) for value in constants
    ]


def append_step_flag(
    circuit: QuantumCircuit,
    step_bits: list,
    target,
    workspace,
) -> None:
    """Set target iff the little-endian three-bit step code is adsorption."""

    adsorption = int(STEP_CODE["adsorption"])
    zero_controls = [bit for bit in range(3) if not ((adsorption >> bit) & 1)]
    for bit in zero_controls:
        circuit.x(step_bits[bit])
    circuit.append(
        synth_mcx_n_clean_m15(3),
        step_bits + [target, workspace],
    )
    for bit in reversed(zero_controls):
        circuit.x(step_bits[bit])


def build_circuit(
    parameter_tables_by_name: dict[str, list[int]],
    schedule_table: list[int],
    factor_product_adder: WeightedAdder,
    ldf_factor_adder: WeightedAdder,
    equilibrium_adders: list[WeightedAdder],
    alpha_adders: list[WeightedAdder],
) -> tuple[QuantumCircuit, dict]:
    max_sum_bits = max(
        adder.num_sum_qubits
        for adder in [
            factor_product_adder,
            ldf_factor_adder,
            *equilibrium_adders,
            *alpha_adders,
        ]
    )
    max_work_bits = max(
        adder.num_ancillas
        for adder in [
            factor_product_adder,
            ldf_factor_adder,
            *equilibrium_adders,
            *alpha_adders,
        ]
    )
    eq_bits = max(adder.num_sum_qubits for adder in equilibrium_adders)
    alpha_bits = max(adder.num_sum_qubits for adder in alpha_adders)

    run = QuantumRegister(5, "run")
    stage = QuantumRegister(3, "stage")
    parameter = QuantumRegister(len(PARAMETERS) * PARAMETER_BITS, "parameter")
    schedule = QuantumRegister(23, "schedule")
    factor_product = QuantumRegister(
        factor_product_adder.num_sum_qubits, "capacity_affinity_factor"
    )
    ldf_factor = QuantumRegister(ldf_factor_adder.num_sum_qubits, "ldf_factor")
    equilibrium = QuantumRegister(len(COMPONENTS) * eq_bits, "equilibrium_prefactor")
    alpha = QuantumRegister(len(COMPONENTS) * alpha_bits, "ldf_alpha")
    adsorption = QuantumRegister(2, "adsorption_active")
    cross_product = QuantumRegister(2 * PARAMETER_BITS, "factor_cross_product")
    arithmetic_sum = QuantumRegister(max_sum_bits, "arithmetic_sum")
    arithmetic_work = QuantumRegister(max_work_bits, "arithmetic_work")
    qrom_work = QuantumRegister(3, "qrom_work")
    constant_one = QuantumRegister(1, "constant_one")
    flag_work = QuantumRegister(1, "flag_work")
    circuit = QuantumCircuit(
        run,
        stage,
        parameter,
        schedule,
        factor_product,
        ldf_factor,
        equilibrium,
        alpha,
        adsorption,
        cross_product,
        arithmetic_sum,
        arithmetic_work,
        qrom_work,
        constant_one,
        flag_work,
        name="coherent_run_factor_to_five_component_ldf_interface",
    )

    for index, name in enumerate(PARAMETERS):
        output = list(parameter)[index * PARAMETER_BITS : (index + 1) * PARAMETER_BITS]
        append_qrom(circuit, list(run), output, list(qrom_work), parameter_tables_by_name[name])
    append_qrom(circuit, list(stage), list(schedule), list(qrom_work), schedule_table)

    parameter_index = {name: index for index, name in enumerate(PARAMETERS)}
    factor_registers = {
        name: list(parameter)[
            parameter_index[name] * PARAMETER_BITS : (parameter_index[name] + 1)
            * PARAMETER_BITS
        ]
        for name in ("capacity_factor", "affinity_factor", "ldf_factor")
    }

    multiplier = MultiplierGate(PARAMETER_BITS, 2 * PARAMETER_BITS)
    circuit.append(
        multiplier,
        factor_registers["capacity_factor"]
        + factor_registers["affinity_factor"]
        + list(cross_product),
    )
    circuit.x(constant_one[0])

    factor_state = (
        list(constant_one)
        + factor_registers["capacity_factor"]
        + factor_registers["affinity_factor"]
        + list(cross_product)
    )
    factor_qargs = (
        factor_state
        + list(arithmetic_sum)[: factor_product_adder.num_sum_qubits]
        + list(arithmetic_work)[: factor_product_adder.num_ancillas]
    )
    circuit.append(factor_product_adder, factor_qargs)
    for source, target in zip(
        list(arithmetic_sum)[: factor_product_adder.num_sum_qubits],
        list(factor_product),
    ):
        circuit.cx(source, target)
    circuit.append(factor_product_adder.inverse(), factor_qargs)

    for component_index, adder in enumerate(equilibrium_adders):
        qargs = (
            list(factor_product)
            + list(arithmetic_sum)[: adder.num_sum_qubits]
            + list(arithmetic_work)[: adder.num_ancillas]
        )
        circuit.append(adder, qargs)
        target = list(equilibrium)[
            component_index * eq_bits : component_index * eq_bits + adder.num_sum_qubits
        ]
        for source, output in zip(
            list(arithmetic_sum)[: adder.num_sum_qubits], target
        ):
            circuit.cx(source, output)
        circuit.append(adder.inverse(), qargs)

    circuit.append(
        multiplier.inverse(),
        factor_registers["capacity_factor"]
        + factor_registers["affinity_factor"]
        + list(cross_product),
    )

    ldf_state = list(constant_one) + factor_registers["ldf_factor"]
    ldf_qargs = (
        ldf_state
        + list(arithmetic_sum)[: ldf_factor_adder.num_sum_qubits]
        + list(arithmetic_work)[: ldf_factor_adder.num_ancillas]
    )
    circuit.append(ldf_factor_adder, ldf_qargs)
    for source, target in zip(
        list(arithmetic_sum)[: ldf_factor_adder.num_sum_qubits], list(ldf_factor)
    ):
        circuit.cx(source, target)
    circuit.append(ldf_factor_adder.inverse(), ldf_qargs)

    for component_index, adder in enumerate(alpha_adders):
        qargs = (
            list(ldf_factor)
            + list(arithmetic_sum)[: adder.num_sum_qubits]
            + list(arithmetic_work)[: adder.num_ancillas]
        )
        circuit.append(adder, qargs)
        target = list(alpha)[
            component_index * alpha_bits : component_index * alpha_bits + adder.num_sum_qubits
        ]
        for source, output in zip(
            list(arithmetic_sum)[: adder.num_sum_qubits], target
        ):
            circuit.cx(source, output)
        circuit.append(adder.inverse(), qargs)

    append_step_flag(
        circuit, list(schedule)[0:3], adsorption[0], flag_work[0]
    )
    append_step_flag(
        circuit, list(schedule)[3:6], adsorption[1], flag_work[0]
    )
    circuit.x(constant_one[0])

    retained = set(
        list(run)
        + list(stage)
        + list(parameter)
        + list(schedule)
        + list(factor_product)
        + list(ldf_factor)
        + list(equilibrium)
        + list(alpha)
        + list(adsorption)
    )
    layout = {
        "parameter_bits_each": PARAMETER_BITS,
        "coefficient_scale_bits": COEFFICIENT_SCALE_BITS,
        "capacity_affinity_factor_bits": len(factor_product),
        "ldf_factor_bits": len(ldf_factor),
        "equilibrium_prefactor_bits_per_component": eq_bits,
        "ldf_alpha_bits_per_component": alpha_bits,
        "adsorption_flag_bits": len(adsorption),
        "retained_input_output_qubits": len(retained),
        "cleared_workspace_qubits": circuit.num_qubits - len(retained),
        "workspace_registers": {
            "factor_cross_product": len(cross_product),
            "arithmetic_sum": len(arithmetic_sum),
            "arithmetic_work": len(arithmetic_work),
            "qrom_work": len(qrom_work),
            "constant_one": len(constant_one),
            "flag_work": len(flag_work),
        },
    }
    return circuit, layout


def resource_record(circuit: QuantumCircuit) -> dict:
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
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    runs = sorted(ledger["runs"], key=lambda row: int(row["sample"]))
    if len(runs) != 32 or [int(run["sample"]) for run in runs] != list(range(32)):
        raise AssertionError("expected contiguous 32-run primary support")
    if tuple(ledger["components"]) != COMPONENTS:
        raise AssertionError(ledger["components"])

    tables, parameter_rows, parameter_precision = parameter_tables(runs)
    schedule_table, schedule_rows = make_schedule_rows()
    row_by_name = {row["parameter"]: row for row in parameter_rows}
    capacity_row = row_by_name["capacity_factor"]
    affinity_row = row_by_name["affinity_factor"]
    ldf_row = row_by_name["ldf_factor"]

    factor_weights = integer_weights_for_affine_product(
        float(capacity_row["support_min"]),
        float(capacity_row["support_span"]),
        float(affinity_row["support_min"]),
        float(affinity_row["support_span"]),
    )
    ldf_factor_weights = integer_weights_for_affine(
        float(ldf_row["support_min"]), float(ldf_row["support_span"])
    )
    factor_product_adder = WeightedAdder(len(factor_weights), factor_weights)
    ldf_factor_adder = WeightedAdder(len(ldf_factor_weights), ldf_factor_weights)

    constants = physical_constants()
    equilibrium_base = np.asarray(constants["qcap"], dtype=float) * np.asarray(
        constants["affinity"], dtype=float
    )
    alpha_base = np.asarray(LDF, dtype=float)
    equilibrium_weights = component_weights(
        factor_product_adder.num_sum_qubits, equilibrium_base
    )
    alpha_weights = component_weights(ldf_factor_adder.num_sum_qubits, alpha_base)
    equilibrium_adders = [WeightedAdder(len(row), row) for row in equilibrium_weights]
    alpha_adders = [WeightedAdder(len(row), row) for row in alpha_weights]

    circuit, layout = build_circuit(
        tables,
        schedule_table,
        factor_product_adder,
        ldf_factor_adder,
        equilibrium_adders,
        alpha_adders,
    )

    rows: list[dict] = []
    all_equilibrium_relative_errors: list[float] = []
    all_alpha_relative_errors: list[float] = []
    factor_relative_errors: list[float] = []
    ldf_factor_relative_errors: list[float] = []
    for run_index, run in enumerate(runs):
        capacity_code = int(tables["capacity_factor"][run_index])
        affinity_code = int(tables["affinity_factor"][run_index])
        ldf_code = int(tables["ldf_factor"][run_index])
        factor_code = product_weighted_code(
            capacity_code, affinity_code, factor_weights
        )
        ldf_factor_code = weighted_code(
            ldf_code, ldf_factor_weights, constant=True
        )
        decoded_factor = factor_code / COEFFICIENT_SCALE
        decoded_ldf_factor = ldf_factor_code / COEFFICIENT_SCALE
        exact_capacity = float(run["parameters"]["capacity_factor"])
        exact_affinity = float(run["parameters"]["affinity_factor"])
        exact_ldf_factor = float(run["parameters"]["ldf_factor"])
        exact_factor = exact_capacity * exact_affinity
        factor_error = abs(decoded_factor - exact_factor) / exact_factor
        ldf_factor_error = abs(decoded_ldf_factor - exact_ldf_factor) / exact_ldf_factor
        factor_relative_errors.append(factor_error)
        ldf_factor_relative_errors.append(ldf_factor_error)
        for component_index, component in enumerate(COMPONENTS):
            equilibrium_code = weighted_code(
                factor_code, equilibrium_weights[component_index]
            )
            alpha_code = weighted_code(
                ldf_factor_code, alpha_weights[component_index]
            )
            decoded_equilibrium = equilibrium_code / COEFFICIENT_SCALE
            decoded_alpha = alpha_code / COEFFICIENT_SCALE
            exact_equilibrium = float(equilibrium_base[component_index] * exact_factor)
            exact_alpha = float(alpha_base[component_index] * exact_ldf_factor)
            equilibrium_error = abs(decoded_equilibrium - exact_equilibrium) / exact_equilibrium
            alpha_error = abs(decoded_alpha - exact_alpha) / exact_alpha
            all_equilibrium_relative_errors.append(equilibrium_error)
            all_alpha_relative_errors.append(alpha_error)
            rows.append(
                {
                    "run": run_index,
                    "sample": int(run["sample"]),
                    "component": component,
                    "capacity_code": capacity_code,
                    "affinity_code": affinity_code,
                    "ldf_factor_code": ldf_code,
                    "capacity_affinity_code": factor_code,
                    "decoded_capacity_affinity_factor": decoded_factor,
                    "exact_capacity_affinity_factor": exact_factor,
                    "capacity_affinity_relative_error": factor_error,
                    "equilibrium_prefactor_code": equilibrium_code,
                    "decoded_equilibrium_prefactor": decoded_equilibrium,
                    "exact_equilibrium_prefactor": exact_equilibrium,
                    "equilibrium_prefactor_relative_error": equilibrium_error,
                    "decoded_ldf_factor": decoded_ldf_factor,
                    "exact_ldf_factor": exact_ldf_factor,
                    "ldf_factor_relative_error": ldf_factor_error,
                    "ldf_alpha_code": alpha_code,
                    "decoded_ldf_alpha": decoded_alpha,
                    "exact_ldf_alpha": exact_alpha,
                    "ldf_alpha_relative_error": alpha_error,
                }
            )

    schedule_checks = 0
    schedule_flag_rows = []
    for stage in range(8):
        code = int(schedule_table[stage])
        flag_a = bool((code & 0b111) == STEP_CODE["adsorption"])
        flag_b = bool(((code >> 3) & 0b111) == STEP_CODE["adsorption"])
        expected_a = bool(stage < len(SCHEDULE) and SCHEDULE[stage]["A"] == "adsorption")
        expected_b = bool(stage < len(SCHEDULE) and SCHEDULE[stage]["B"] == "adsorption")
        if flag_a != expected_a or flag_b != expected_b:
            raise AssertionError((stage, flag_a, flag_b, expected_a, expected_b))
        schedule_checks += 2
        schedule_flag_rows.append(
            {
                "stage": stage,
                "name": SCHEDULE[stage]["name"] if stage < len(SCHEDULE) else "unused",
                "bed_A_adsorption": flag_a,
                "bed_B_adsorption": flag_b,
            }
        )

    precision = {
        "coefficient_scale_bits": COEFFICIENT_SCALE_BITS,
        "capacity_affinity_factor_p95_relative_error": float(
            np.quantile(factor_relative_errors, 0.95)
        ),
        "capacity_affinity_factor_max_relative_error": float(
            np.max(factor_relative_errors)
        ),
        "ldf_factor_p95_relative_error": float(
            np.quantile(ldf_factor_relative_errors, 0.95)
        ),
        "ldf_factor_max_relative_error": float(np.max(ldf_factor_relative_errors)),
        "five_component_equilibrium_prefactor_p95_relative_error": float(
            np.quantile(all_equilibrium_relative_errors, 0.95)
        ),
        "five_component_equilibrium_prefactor_max_relative_error": float(
            np.max(all_equilibrium_relative_errors)
        ),
        "five_component_ldf_alpha_p95_relative_error": float(
            np.quantile(all_alpha_relative_errors, 0.95)
        ),
        "five_component_ldf_alpha_max_relative_error": float(
            np.max(all_alpha_relative_errors)
        ),
        "relative_error_gate": RELATIVE_ERROR_GATE,
    }
    precision["passes_declared_precision_gate"] = bool(
        max(
            precision["capacity_affinity_factor_max_relative_error"],
            precision["ldf_factor_max_relative_error"],
            precision["five_component_equilibrium_prefactor_max_relative_error"],
            precision["five_component_ldf_alpha_max_relative_error"],
        )
        <= RELATIVE_ERROR_GATE
    )
    if not precision["passes_declared_precision_gate"]:
        raise AssertionError(precision)

    resources = resource_record(circuit)
    if resources["measurement"] or resources["reset"]:
        raise AssertionError(resources)

    payload = {
        "schema": "psa-qae-cce-coherent-run-factor-ldf-interface/v1",
        "status": "finite_support_coherent_run_factors_directly_wired_to_five_component_ldf_coefficients_full_state_update_open",
        "source": LEDGER.name,
        "support": {
            "runs": len(runs),
            "run_address_qubits": 5,
            "schedule_addresses": 8,
            "valid_schedule_stages": len(SCHEDULE),
            "components": list(COMPONENTS),
            "coefficient_records_checked": len(rows) * 2,
            "schedule_flags_checked": schedule_checks,
        },
        "parameter_encoding": {
            "parameters": list(PARAMETERS),
            "bits_each": PARAMETER_BITS,
            "aggregate": parameter_precision,
        },
        "precision": precision,
        "schedule_adsorption_flags": schedule_flag_rows,
        "register_layout": layout,
        "compiled_interface": resources,
        "cleanliness_by_construction": {
            "retained": [
                "run and stage addresses",
                "eleven run-parameter words",
                "decoded schedule word",
                "capacity-affinity factor",
                "LDF factor",
                "five equilibrium prefactors",
                "five LDF alpha coefficients",
                "two bed-adsorption flags",
            ],
            "cleared": [
                "capacity-affinity cross product",
                "weighted-adder sums and carries",
                "QROM clean ancillas",
                "constant-one helper",
                "schedule-flag clean ancilla",
            ],
        },
        "claim_boundary": {
            "supported": "direct all-to-all u/CX compilation from the coherent 32-run parameter and six-stage schedule interface through reversible factor multiplication to five component equilibrium prefactors, five LDF alpha coefficients, and paired-bed adsorption flags",
            "unsupported": "direct consumption of these coefficients by the 20-bit pressure/composition reciprocal/LDF/loading/balance paths, state-dependent pressure/flow tank demand, a monolithic five-component transpilation, adaptive integration, a complete phase/cycle unitary, routing, hardware feasibility, external H2 validation, or quantum advantage",
        },
        "qpu_submission": False,
    }
    RESULTS.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    with OUT_CSV.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    lines = [
        "# Coherent run-factor to five-component LDF coefficient interface",
        "",
        "The frozen 32-run controller now feeds reversible arithmetic rather than ending at a parameter register. Its 12-bit capacity, affinity, and LDF-factor words generate a capacity-affinity product, five component equilibrium prefactors, five LDF alpha coefficients, and two adsorption-active flags decoded from the synchronized paired-bed schedule.",
        "",
        f"The table audit checks **{len(rows) * 2} component coefficients** and **{schedule_checks} bed/stage flags**. The equilibrium-prefactor p95/maximum relative errors are **{precision['five_component_equilibrium_prefactor_p95_relative_error']:.3e}/{precision['five_component_equilibrium_prefactor_max_relative_error']:.3e}**; the LDF-alpha p95/maximum errors are **{precision['five_component_ldf_alpha_p95_relative_error']:.3e}/{precision['five_component_ldf_alpha_max_relative_error']:.3e}**.",
        "",
        f"The directly transpiled circuit uses **{resources['logical_qubits']:,} logical qubits**, depth **{resources['depth_all_to_all']:,}**, **{resources['cx']:,} CX**, and **{resources['u']:,} u** gates, with no measurement or reset. It clears the multiplier, weighted-adder, QROM, constant, and flag workspaces while retaining the parameter, schedule, coefficient, and adsorption-flag registers.",
        "",
        "This is a finite-support controller-to-kinetics coefficient interface. Direct use of the coefficient registers inside the pressure/composition reciprocal, loading update, component balance, off-ledger tank demand, and adaptive phase/cycle remains open.",
        "",
        f"Artifacts: `{OUT_JSON.name}`, `{OUT_CSV.name}`. No QPU job was submitted.",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": payload["status"],
                "precision": precision,
                "resources": resources,
                "qpu_submission": False,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
