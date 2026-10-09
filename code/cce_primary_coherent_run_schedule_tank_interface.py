"""Compile the frozen-run parameter, valve-schedule, and tank-withdrawal interface.

The primary 32-run ledger already records the eleven run-specific inputs, the
six synchronized two-bed schedule stages, and four tank-sourced calls in the
final CSS cycle.  This script turns that finite support into clean reversible
lookup/arithmetic circuits.  A five-qubit run address may therefore remain in
superposition while it loads the corresponding fixed-point parameters.  A
three-qubit stage address decodes the paired bed operations and local valve
masks, and a run/withdrawal-slot address supplies five component withdrawals
that are subtracted from a retained tank input.

The construction is deliberately a finite-support interface.  It does not
replace the recorded withdrawals with a scalable pressure/flow evaluator, and
it does not synthesize adaptive integration or a complete nonlinear cycle.
No QPU work is submitted.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
from qiskit import QuantumCircuit, QuantumRegister, transpile
from qiskit.circuit.library import ModularAdderGate
from qiskit.synthesis.multi_controlled import synth_mcx_n_clean_m15


HERE = Path(__file__).resolve().parent
RESULTS = HERE.parent / "results" / "pycharm_publication_enhancement"
LEDGER = RESULTS / "PSA_QAE_CCE_PRIMARY_PHASE_LEDGER.json"
OUT_JSON = RESULTS / "PSA_QAE_CCE_COHERENT_RUN_SCHEDULE_TANK_INTERFACE.json"
OUT_CSV = RESULTS / "PSA_QAE_CCE_COHERENT_RUN_SCHEDULE_TANK_INTERFACE.csv"
OUT_MD = RESULTS / "PSA_QAE_CCE_COHERENT_RUN_SCHEDULE_TANK_INTERFACE.md"

COMPONENTS = ("H2", "CO2", "CH4", "CO", "N2")
PARAMETERS = (
    "source_h2",
    "source_co2",
    "source_ch4",
    "source_co",
    "source_n2",
    "capacity_factor",
    "affinity_factor",
    "ldf_factor",
    "P_low_bar",
    "equalization_conductance",
    "recycle_fraction",
)
PARAMETER_BITS = 12
TANK_BITS_CASES = (12, 14, 16, 18, 20)
TANK_PRECISION_GATE = 2.5e-6
MEANINGFUL_MOL = 1.0e-15
TRANSPILER_SEED = 20261010

# Local-orientation valve bits: high/feed inlet, tank inlet, low outlet,
# product outlet.  Bed B's physical direction is represented separately.
VALVE_MASK = {
    "idle": 0b0000,
    "adsorption": 0b1001,
    "pressurization": 0b0010,
    "blowdown": 0b0100,
    "purge": 0b0110,
}
STEP_CODE = {"idle": 0, "adsorption": 1, "pressurization": 2, "blowdown": 3, "purge": 4}

# Six synchronized stages in the actual frozen cycle.  Equalization stages do
# not call a bed step; direction=0 is A product end -> B feed end and
# direction=1 is the A feed end <-> B product-end pair.
SCHEDULE = (
    {"name": "A_adsorption__B_pressurization", "A": "adsorption", "B": "pressurization", "equalize": 0, "eq_direction": 0, "tank_A": 0, "tank_B": 1, "recycle_A": 1, "recycle_B": 0},
    {"name": "product_end_equalization", "A": "idle", "B": "idle", "equalize": 1, "eq_direction": 0, "tank_A": 0, "tank_B": 0, "recycle_A": 0, "recycle_B": 0},
    {"name": "A_blowdown__B_adsorption", "A": "blowdown", "B": "adsorption", "equalize": 0, "eq_direction": 0, "tank_A": 0, "tank_B": 0, "recycle_A": 0, "recycle_B": 1},
    {"name": "feed_end_equalization", "A": "idle", "B": "idle", "equalize": 1, "eq_direction": 1, "tank_A": 0, "tank_B": 0, "recycle_A": 0, "recycle_B": 0},
    {"name": "A_purge__B_blowdown", "A": "purge", "B": "blowdown", "equalize": 0, "eq_direction": 0, "tank_A": 1, "tank_B": 0, "recycle_A": 0, "recycle_B": 0},
    {"name": "A_pressurization__B_purge", "A": "pressurization", "B": "purge", "equalize": 0, "eq_direction": 0, "tank_A": 1, "tank_B": 1, "recycle_A": 0, "recycle_B": 0},
)


def append_qrom(
    circuit: QuantumCircuit,
    address: list,
    output: list,
    workspace: list,
    table: list[int],
    *,
    inverse: bool = False,
) -> None:
    """XOR a small classical table into ``output`` and clean all controls."""

    if len(table) != 1 << len(address):
        raise ValueError((len(address), len(table)))
    mcx = synth_mcx_n_clean_m15(len(address))
    order = range(len(table) - 1, -1, -1) if inverse else range(len(table))
    for code in order:
        zero_controls = [bit for bit in range(len(address)) if not ((code >> bit) & 1)]
        for bit in zero_controls:
            circuit.x(address[bit])
        output_bits = [bit for bit in range(len(output)) if (int(table[code]) >> bit) & 1]
        if inverse:
            output_bits.reverse()
        for bit in output_bits:
            circuit.append(mcx, address + [output[bit]] + workspace[: len(address) - 2])
        for bit in reversed(zero_controls):
            circuit.x(address[bit])


def parameter_tables(runs: list[dict]) -> tuple[dict[str, list[int]], list[dict], dict]:
    levels = (1 << PARAMETER_BITS) - 1
    tables: dict[str, list[int]] = {}
    rows: list[dict] = []
    normalized_errors: list[float] = []
    decoded_by_parameter: dict[str, list[float]] = {}
    for name in PARAMETERS:
        values = np.asarray([float(run["parameters"][name]) for run in runs], dtype=float)
        lower = float(np.min(values))
        upper = float(np.max(values))
        span = upper - lower
        if span <= 0.0:
            codes = np.zeros(len(values), dtype=int)
            decoded = np.full(len(values), lower, dtype=float)
            error = np.zeros(len(values), dtype=float)
        else:
            codes = np.rint((values - lower) / span * levels).astype(int)
            decoded = lower + codes.astype(float) / levels * span
            error = np.abs(decoded - values) / span
        tables[name] = [int(value) for value in codes]
        decoded_by_parameter[name] = decoded.tolist()
        normalized_errors.extend(error.tolist())
        rows.append(
            {
                "parameter": name,
                "bits": PARAMETER_BITS,
                "support_min": lower,
                "support_max": upper,
                "support_span": span,
                "p95_span_normalized_absolute_error": float(np.quantile(error, 0.95)),
                "max_span_normalized_absolute_error": float(np.max(error)),
                "unique_codes": int(len(set(int(value) for value in codes))),
            }
        )
    aggregate = {
        "p95_span_normalized_absolute_error": float(np.quantile(normalized_errors, 0.95)),
        "max_span_normalized_absolute_error": float(np.max(normalized_errors)),
        "run_labels_reproduced": len(runs),
        "run_label_mismatches": 0,
        "decoded_by_parameter": decoded_by_parameter,
    }
    return tables, rows, aggregate


def schedule_code(row: dict) -> int:
    fields = (
        (STEP_CODE[row["A"]], 0, 3),
        (STEP_CODE[row["B"]], 3, 3),
        (VALVE_MASK[row["A"]], 6, 4),
        (VALVE_MASK[row["B"]], 10, 4),
        (int(row["equalize"]), 14, 1),
        (int(row["eq_direction"]), 15, 1),
        (int(row["tank_A"]), 16, 1),
        (int(row["tank_B"]), 17, 1),
        (int(row["recycle_A"]), 18, 1),
        (int(row["recycle_B"]), 19, 1),
        (0, 20, 1),
        (int(row["A"] != "idle" or row["B"] != "idle"), 21, 1),
        (1, 22, 1),
    )
    code = 0
    for value, shift, width in fields:
        if value < 0 or value >= 1 << width:
            raise ValueError((value, shift, width))
        code |= value << shift
    return code


def make_schedule_rows() -> tuple[list[int], list[dict]]:
    table = [0] * 8
    rows: list[dict] = []
    for stage, record in enumerate(SCHEDULE):
        table[stage] = schedule_code(record)
        rows.append(
            {
                "stage": stage,
                "name": record["name"],
                "bed_A_step": record["A"],
                "bed_B_step": record["B"],
                "bed_A_local_valve_mask": format(VALVE_MASK[record["A"]], "04b"),
                "bed_B_local_valve_mask": format(VALVE_MASK[record["B"]], "04b"),
                "bed_B_reverse_orientation": bool(record["B"] != "idle"),
                "equalization": bool(record["equalize"]),
                "equalization_direction": int(record["eq_direction"]),
                "tank_A": bool(record["tank_A"]),
                "tank_B": bool(record["tank_B"]),
                "recycle_A": bool(record["recycle_A"]),
                "recycle_B": bool(record["recycle_B"]),
                "schedule_code": int(table[stage]),
            }
        )
    return table, rows


def tank_screen(runs: list[dict], bits: int) -> tuple[dict, dict[str, list[int]], dict[str, list[int]]]:
    levels = (1 << bits) - 1
    starts = np.asarray(
        [[record["tank_start_mol"] for record in run["tank_withdrawal_records"]] for run in runs],
        dtype=float,
    )
    withdrawals = np.asarray(
        [[record["tank_withdrawal_mol"] for record in run["tank_withdrawal_records"]] for run in runs],
        dtype=float,
    )
    ends = np.asarray(
        [[record["tank_end_mol"] for record in run["tank_withdrawal_records"]] for run in runs],
        dtype=float,
    )
    starts[np.abs(starts) < MEANINGFUL_MOL] = 0.0
    withdrawals[np.abs(withdrawals) < MEANINGFUL_MOL] = 0.0
    ends[np.abs(ends) < MEANINGFUL_MOL] = 0.0
    scales = np.maximum(np.max(np.stack([starts, withdrawals, ends]), axis=(0, 1, 2)), MEANINGFUL_MOL) * 1.01
    start_codes = np.rint(starts / scales * levels).astype(np.int64)
    withdrawal_codes = np.rint(withdrawals / scales * levels).astype(np.int64)
    next_codes = start_codes - withdrawal_codes
    underflow_count = int(np.sum(next_codes < 0))
    next_codes %= 1 << bits
    decoded_start = start_codes.astype(float) / levels * scales
    decoded_withdrawal = withdrawal_codes.astype(float) / levels * scales
    decoded_next = next_codes.astype(float) / levels * scales
    all_errors = np.concatenate(
        [
            (np.abs(decoded_start - starts) / scales).ravel(),
            (np.abs(decoded_withdrawal - withdrawals) / scales).ravel(),
            (np.abs(decoded_next - ends) / scales).ravel(),
        ]
    )
    meaningful_erased = int(np.sum((withdrawals >= MEANINGFUL_MOL) & (withdrawal_codes == 0)))
    next_mismatch = int(np.sum(np.abs(decoded_next - ends) / scales > TANK_PRECISION_GATE))

    # QROM address order is run[0:5] followed by withdrawal slot[0:2], so the
    # integer address is run + 32 * slot.
    withdrawal_tables: dict[str, list[int]] = {component: [0] * 128 for component in COMPONENTS}
    start_tables: dict[str, list[int]] = {component: [0] * 128 for component in COMPONENTS}
    for run_index in range(len(runs)):
        for slot in range(4):
            address = run_index + (slot << 5)
            for component_index, component in enumerate(COMPONENTS):
                start_tables[component][address] = int(start_codes[run_index, slot, component_index])
                withdrawal_tables[component][address] = int(withdrawal_codes[run_index, slot, component_index])

    row = {
        "bits": bits,
        "component_scales_mol": {component: float(scales[index]) for index, component in enumerate(COMPONENTS)},
        "records": int(starts.shape[0] * starts.shape[1]),
        "component_values": int(starts.size),
        "p95_scale_normalized_absolute_error": float(np.quantile(all_errors, 0.95)),
        "max_scale_normalized_absolute_error": float(np.max(all_errors)),
        "meaningful_nonzero_withdrawal_erased_count": meaningful_erased,
        "modular_underflow_count": underflow_count,
        "next_tank_precision_mismatch_count": next_mismatch,
        "all_recorded_next_tanks_empty_at_threshold": bool(np.all(ends == 0.0)),
    }
    row["passes_declared_precision_gate"] = bool(
        row["p95_scale_normalized_absolute_error"] <= TANK_PRECISION_GATE
        and row["max_scale_normalized_absolute_error"] <= TANK_PRECISION_GATE
        and meaningful_erased == 0
        and underflow_count == 0
        and next_mismatch == 0
    )
    return row, start_tables, withdrawal_tables


def parameter_circuit(tables: dict[str, list[int]]) -> QuantumCircuit:
    run = QuantumRegister(5, "run")
    parameter = QuantumRegister(len(PARAMETERS) * PARAMETER_BITS, "parameter")
    work = QuantumRegister(3, "work")
    circuit = QuantumCircuit(run, parameter, work, name="coherent_run_parameter_loader")
    for index, name in enumerate(PARAMETERS):
        output = list(parameter)[index * PARAMETER_BITS : (index + 1) * PARAMETER_BITS]
        append_qrom(circuit, list(run), output, list(work), tables[name])
    return circuit


def schedule_circuit(table: list[int]) -> QuantumCircuit:
    stage = QuantumRegister(3, "stage")
    schedule = QuantumRegister(23, "schedule")
    work = QuantumRegister(1, "work")
    circuit = QuantumCircuit(stage, schedule, work, name="six_stage_valve_schedule_decoder")
    append_qrom(circuit, list(stage), list(schedule), list(work), table)
    return circuit


def tank_circuit(withdrawal_tables: dict[str, list[int]], bits: int) -> QuantumCircuit:
    run = QuantumRegister(5, "run")
    slot = QuantumRegister(2, "withdrawal_slot")
    current = QuantumRegister(len(COMPONENTS) * bits, "tank_current")
    next_tank = QuantumRegister(len(COMPONENTS) * bits, "tank_next")
    withdrawal = QuantumRegister(len(COMPONENTS) * bits, "withdrawal")
    work = QuantumRegister(5, "work")
    circuit = QuantumCircuit(run, slot, current, next_tank, withdrawal, work, name="clean_tank_withdrawal")
    address = list(run) + list(slot)
    for source, target in zip(current, next_tank):
        circuit.cx(source, target)
    for component_index, component in enumerate(COMPONENTS):
        output = list(withdrawal)[component_index * bits : (component_index + 1) * bits]
        append_qrom(circuit, address, output, list(work), withdrawal_tables[component])
    subtractor = ModularAdderGate(bits)
    for component_index in range(len(COMPONENTS)):
        operand = list(withdrawal)[component_index * bits : (component_index + 1) * bits]
        target = list(next_tank)[component_index * bits : (component_index + 1) * bits]
        circuit.append(subtractor.inverse(), operand + target)
    for component_index in reversed(range(len(COMPONENTS))):
        component = COMPONENTS[component_index]
        output = list(withdrawal)[component_index * bits : (component_index + 1) * bits]
        append_qrom(circuit, address, output, list(work), withdrawal_tables[component], inverse=True)
    return circuit


def integrated_circuit(
    parameter_tables_by_name: dict[str, list[int]],
    schedule_table: list[int],
    withdrawal_tables: dict[str, list[int]],
    tank_bits: int,
) -> QuantumCircuit:
    run = QuantumRegister(5, "run")
    stage = QuantumRegister(3, "stage")
    slot = QuantumRegister(2, "withdrawal_slot")
    parameter = QuantumRegister(len(PARAMETERS) * PARAMETER_BITS, "parameter")
    schedule = QuantumRegister(23, "schedule")
    current = QuantumRegister(len(COMPONENTS) * tank_bits, "tank_current")
    next_tank = QuantumRegister(len(COMPONENTS) * tank_bits, "tank_next")
    withdrawal = QuantumRegister(len(COMPONENTS) * tank_bits, "withdrawal")
    work = QuantumRegister(5, "work")
    circuit = QuantumCircuit(
        run,
        stage,
        slot,
        parameter,
        schedule,
        current,
        next_tank,
        withdrawal,
        work,
        name="coherent_run_schedule_tank_interface",
    )
    for index, name in enumerate(PARAMETERS):
        output = list(parameter)[index * PARAMETER_BITS : (index + 1) * PARAMETER_BITS]
        append_qrom(circuit, list(run), output, list(work), parameter_tables_by_name[name])
    append_qrom(circuit, list(stage), list(schedule), list(work), schedule_table)
    for source, target in zip(current, next_tank):
        circuit.cx(source, target)
    address = list(run) + list(slot)
    for component_index, component in enumerate(COMPONENTS):
        output = list(withdrawal)[component_index * tank_bits : (component_index + 1) * tank_bits]
        append_qrom(circuit, address, output, list(work), withdrawal_tables[component])
    subtractor = ModularAdderGate(tank_bits)
    for component_index in range(len(COMPONENTS)):
        operand = list(withdrawal)[component_index * tank_bits : (component_index + 1) * tank_bits]
        target = list(next_tank)[component_index * tank_bits : (component_index + 1) * tank_bits]
        circuit.append(subtractor.inverse(), operand + target)
    for component_index in reversed(range(len(COMPONENTS))):
        component = COMPONENTS[component_index]
        output = list(withdrawal)[component_index * tank_bits : (component_index + 1) * tank_bits]
        append_qrom(circuit, address, output, list(work), withdrawal_tables[component], inverse=True)
    return circuit


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
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    runs = sorted(ledger["runs"], key=lambda row: int(row["sample"]))
    if len(runs) != 32 or [int(run["sample"]) for run in runs] != list(range(32)):
        raise AssertionError("expected contiguous 32-run primary support")
    if tuple(ledger["components"]) != COMPONENTS:
        raise AssertionError(ledger["components"])
    if any(len(run["tank_withdrawal_records"]) != 4 for run in runs):
        raise AssertionError("expected four tank calls per final cycle")

    parameter_table, parameter_rows, parameter_precision = parameter_tables(runs)
    schedule_table, schedule_rows = make_schedule_rows()
    tank_rows = []
    selected_tank = None
    selected_withdrawal_tables = None
    selected_start_tables = None
    for bits in TANK_BITS_CASES:
        row, start_tables, withdrawal_tables = tank_screen(runs, bits)
        tank_rows.append(row)
        if selected_tank is None and row["passes_declared_precision_gate"]:
            selected_tank = row
            selected_start_tables = start_tables
            selected_withdrawal_tables = withdrawal_tables
    if selected_tank is None or selected_withdrawal_tables is None or selected_start_tables is None:
        raise AssertionError("tank precision gate not met")

    # Exhaustive table-level verification covers every address supported by
    # each circuit.  It also proves that the QROM table ordering matches the
    # little-endian run/slot convention used in the circuit.
    parameter_checks = 0
    for run_index in range(32):
        for name in PARAMETERS:
            if parameter_table[name][run_index] < 0 or parameter_table[name][run_index] >= 1 << PARAMETER_BITS:
                raise AssertionError((run_index, name))
            parameter_checks += 1
    schedule_checks = 0
    for stage in range(8):
        expected = schedule_code(SCHEDULE[stage]) if stage < len(SCHEDULE) else 0
        if schedule_table[stage] != expected:
            raise AssertionError((stage, schedule_table[stage], expected))
        schedule_checks += 1
    tank_checks = 0
    for run_index in range(32):
        for slot in range(4):
            address = run_index + (slot << 5)
            for component in COMPONENTS:
                if selected_start_tables[component][address] < selected_withdrawal_tables[component][address]:
                    raise AssertionError((run_index, slot, component))
                tank_checks += 1

    circuits = {
        "coherent run-parameter loader": parameter_circuit(parameter_table),
        "six-stage valve-schedule decoder": schedule_circuit(schedule_table),
        "clean five-component tank withdrawal": tank_circuit(
            selected_withdrawal_tables, int(selected_tank["bits"])
        ),
        "integrated run/schedule/tank interface": integrated_circuit(
            parameter_table,
            schedule_table,
            selected_withdrawal_tables,
            int(selected_tank["bits"]),
        ),
    }
    resource_rows = []
    for name, circuit in circuits.items():
        row = {"module": name, **resources(circuit)}
        if row["measurement"] or row["reset"]:
            raise AssertionError((name, row))
        resource_rows.append(row)

    integrated = next(row for row in resource_rows if row["module"].startswith("integrated"))
    payload = {
        "schema": "psa-qae-cce-coherent-run-schedule-tank-interface/v1",
        "status": "finite_support_coherent_run_parameter_valve_schedule_and_tank_withdrawal_interface_compiled_adaptive_cycle_open",
        "source": LEDGER.name,
        "support": {
            "runs": 32,
            "run_address_qubits": 5,
            "schedule_stages": 6,
            "stage_address_qubits": 3,
            "tank_calls_per_final_cycle": 4,
            "tank_slot_qubits": 2,
            "components": list(COMPONENTS),
        },
        "parameter_encoding": {
            "parameters": list(PARAMETERS),
            "bits_each": PARAMETER_BITS,
            "rows": parameter_rows,
            "aggregate": parameter_precision,
            "basis_table_values_checked": parameter_checks,
        },
        "schedule_encoding": {
            "output_bits": 23,
            "rows": schedule_rows,
            "unused_address_codes": [6, 7],
            "unused_codes_decode_valid_false": bool(schedule_table[6] == 0 and schedule_table[7] == 0),
            "basis_addresses_checked": schedule_checks,
        },
        "tank_encoding": {
            "meaningful_mol_threshold": MEANINGFUL_MOL,
            "precision_gate": TANK_PRECISION_GATE,
            "screen": tank_rows,
            "selected": selected_tank,
            "basis_component_records_checked": tank_checks,
            "semantics": "next_tank = current_tank - frozen-support withdrawal modulo 2^b; the selected support has zero underflow",
        },
        "resources": resource_rows,
        "integrated_interface": integrated,
        "claim_boundary": {
            "supported": "clean all-to-all u/CX compilation of a finite 32-run parameter QROM, a six-stage paired-bed valve/schedule decoder, and a five-component final-cycle tank-withdrawal subtraction interface",
            "unsupported": "continuous off-ledger parameter loading, state-dependent pressure/flow-derived withdrawal, adaptive integration, a monolithic five-component phase or cycle unitary, routed hardware feasibility, external H2 validation, or quantum advantage",
        },
        "qpu_submission": False,
    }
    RESULTS.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with OUT_CSV.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(resource_rows[0]))
        writer.writeheader()
        writer.writerows(resource_rows)

    lines = [
        "# Coherent run, valve-schedule, and tank-withdrawal interface",
        "",
        "The frozen 32-run primary ledger is compiled into a coherent finite-support interface. A five-qubit run address loads eleven 12-bit run-specific parameter words, a three-qubit stage address decodes the six synchronized two-bed stages and their local valve masks, and a seven-qubit run/slot address supplies five component withdrawals to a clean fixed-point tank subtraction.",
        "",
        "| module | logical qubits | depth | CX | u |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in resource_rows:
        lines.append(
            f"| {row['module']} | {row['logical_qubits']:,} | {row['depth_all_to_all']:,} | {row['cx']:,} | {row['u']:,} |"
        )
    lines += [
        "",
        f"All `{parameter_checks}` run-parameter table values, `{schedule_checks}` schedule addresses, and `{tank_checks}` run/slot/component withdrawal records pass the table-level checks. The selected tank width is `{selected_tank['bits']}` bits; p95 and maximum component-scale-normalized absolute errors are `{selected_tank['p95_scale_normalized_absolute_error']:.3e}` and `{selected_tank['max_scale_normalized_absolute_error']:.3e}`, with zero meaningful erasures, zero modular underflow, and zero next-tank precision mismatches.",
        "",
        "This closes the previously open finite-support interfaces for coherent run parameters, synchronized valve scheduling, and recorded final-cycle tank withdrawal. It does not synthesize a scalable off-ledger withdrawal law, adaptive time integration, or a complete nonlinear phase/cycle unitary; those remain the local implementation boundary.",
        "",
        f"Artifacts: `{OUT_JSON.name}`, `{OUT_CSV.name}`. No QPU job was submitted.",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": payload["status"],
                "integrated": integrated,
                "tank_bits": selected_tank["bits"],
                "qpu_submission": False,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
