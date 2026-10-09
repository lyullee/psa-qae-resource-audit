"""Compile clean competitive-Langmuir/LDF microsteps for all five components.

Each component circuit uses the same physical-cache pressure/composition states
and the shared five-component competitive-Langmuir denominator.  The circuit
computes one component numerator and equilibrium loading, applies one explicit
one-second LDF update, copies the updated loading, and uncomputes every work
register.  Components are compiled separately so the reported sequential
five-component accounting can reuse arithmetic workspace.

This is a local primitive-gate audit.  It does not submit QPU work and it does
not synthesize gas transport, pressure, valve, tank, adaptive integration, a
complete adsorption phase, or a cyclic PSA oracle.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
from qiskit import transpile

from cce_primary_qstar_ldf_reversible_microstep import (
    ADDRESS_BITS,
    ARITHMETIC_BITS,
    CACHE,
    COMPONENTS,
    INPUT_BITS,
    PREPARATION_JSON,
    TRANSPILER_SEED,
    build_clean_microstep,
    integer_inputs,
    physical_constants,
    precision_row,
)
from psa_spatial_network_probe_n2 import SpatialParams, cell_pressure, cell_y


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RESULTS = ROOT / "10_TEA_LCA_Python" / "results" / "pycharm_publication_enhancement"
OUT_JSON = RESULTS / "PSA_QAE_CCE_PRIMARY_ALL_COMPONENT_LDF_MICROSTEPS.json"
OUT_CSV = RESULTS / "PSA_QAE_CCE_PRIMARY_ALL_COMPONENT_LDF_MICROSTEPS.csv"
OUT_MD = RESULTS / "PSA_QAE_CCE_PRIMARY_ALL_COMPONENT_LDF_MICROSTEPS.md"
SCALE_NORMALIZED_P95_GATE = 2.5e-3


def physical_states_all() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    cache = np.load(CACHE)
    boundaries = np.asarray(cache["boundaries"], dtype=float)
    if boundaries.shape != (32, 101, 85):
        raise AssertionError(boundaries.shape)
    params = SpatialParams(n_cells=4)
    pressures: list[float] = []
    compositions: list[np.ndarray] = []
    loadings: list[np.ndarray] = []
    for state in boundaries[:, :, :80].reshape(-1, 40):
        gas = state[:20].reshape(5, 4)
        adsorbed = state[20:].reshape(5, 4)
        pressures.extend(cell_pressure(gas, params).tolist())
        compositions.extend(cell_y(gas).T)
        loadings.extend(adsorbed.T)
    return (
        np.asarray(pressures, dtype=float),
        np.asarray(compositions, dtype=float),
        np.asarray(loadings, dtype=float),
    )


def main() -> None:
    prior = json.loads(PREPARATION_JSON.read_text(encoding="utf-8"))
    if prior["selected"]["bits_per_pressure_and_composition"] != INPUT_BITS:
        raise AssertionError(prior["selected"])

    pressure, composition, loadings = physical_states_all()
    constants = physical_constants()
    component_results: list[dict] = []
    flat_rows: list[dict] = []

    for component_index, component in enumerate(COMPONENTS):
        encoded = integer_inputs(pressure, composition, constants, component_index)
        rows = [
            precision_row(
                arithmetic_bits,
                address_bits,
                pressure,
                composition,
                loadings[:, component_index],
                constants,
                encoded,
                component_index,
            )
            for arithmetic_bits in ARITHMETIC_BITS
            for address_bits in ADDRESS_BITS
        ]
        for row in rows:
            row["passes_all_component_precision_gate"] = bool(
                row["qstar_p95_loading_scale_normalized_absolute_error"]
                <= SCALE_NORMALIZED_P95_GATE
                and row["ldf_next_p95_loading_scale_normalized_absolute_error"]
                <= SCALE_NORMALIZED_P95_GATE
                and row["nonzero_qstar_erased_fraction"] == 0.0
                and row["loading_input_overflow_fraction"] == 0.0
                and (component != "CO2" or row["passes_declared_precision_gate"])
            )
        selected = next(
            (row for row in rows if row["passes_all_component_precision_gate"]),
            None,
        )
        if selected is None:
            raise AssertionError(f"no reciprocal/LDF precision tier passes for {component}")

        circuit, layout = build_clean_microstep(
            constants,
            encoded,
            selected,
            component_index,
        )
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
            "transpiler_seed": TRANSPILER_SEED,
            "basis_gates": ["u", "cx"],
            "optimization_level": 1,
        }
        result = {
            "component": component,
            "component_index": component_index,
            "loading_range_mol_per_kg": [
                float(np.min(loadings[:, component_index])),
                float(np.max(loadings[:, component_index])),
            ],
            "selected": selected,
            "register_layout": layout,
            "compiled_clean_microstep": resources,
            "screen_rows": rows,
        }
        component_results.append(result)
        flat_rows.append(
            {
                "component": component,
                "arithmetic_bits": selected["arithmetic_bits"],
                "denominator_address_bits": selected["denominator_address_bits"],
                "reciprocal_segments": selected["reciprocal_segments"],
                "qstar_p95_relative_error": selected["qstar_p95_relative_error"],
                "qstar_p95_scale_normalized_error": selected[
                    "qstar_p95_loading_scale_normalized_absolute_error"
                ],
                "ldf_next_p95_relative_error": selected["ldf_next_p95_relative_error"],
                "ldf_next_p95_scale_normalized_error": selected[
                    "ldf_next_p95_loading_scale_normalized_absolute_error"
                ],
                "nonzero_qstar_erased_fraction": selected["nonzero_qstar_erased_fraction"],
                "logical_qubits": resources["logical_qubits"],
                "depth_all_to_all": resources["depth_all_to_all"],
                "cx": resources["cx"],
                "u": resources["u"],
            }
        )
        print(
            json.dumps(
                {
                    "component": component,
                    "logical_qubits": resources["logical_qubits"],
                    "cx": resources["cx"],
                    "qstar_p95": selected["qstar_p95_relative_error"],
                    "ldf_p95": selected["ldf_next_p95_relative_error"],
                },
                ensure_ascii=False,
            ),
            flush=True,
        )

    arithmetic_bits = [int(row["selected"]["arithmetic_bits"]) for row in component_results]
    shared_non_loading_qubits = max(
        int(row["compiled_clean_microstep"]["logical_qubits"]) - 2 * bits
        for row, bits in zip(component_results, arithmetic_bits)
    )
    sequential = {
        "accounting": "five individually compiled clean modules, executed sequentially with arithmetic workspace reuse and all five loading inputs/outputs retained",
        "logical_qubits": shared_non_loading_qubits + 2 * sum(arithmetic_bits),
        "shared_non_loading_qubits": shared_non_loading_qubits,
        "retained_loading_input_output_qubits": 2 * sum(arithmetic_bits),
        "depth_all_to_all_additive_module_bound": sum(
            int(row["compiled_clean_microstep"]["depth_all_to_all"])
            for row in component_results
        ),
        "cx_additive_module_bound": sum(
            int(row["compiled_clean_microstep"]["cx"]) for row in component_results
        ),
        "u_additive_module_bound": sum(
            int(row["compiled_clean_microstep"]["u"]) for row in component_results
        ),
        "interpretation": "modular upper accounting before cross-component cancellation, routing, transport, valve/tank arithmetic, and repeated time integration",
    }
    payload = {
        "schema": "psa-qae-cce-primary-all-component-ldf-microsteps/v1",
        "status": "all_five_competitive_langmuir_ldf_microsteps_compiled_transport_valve_tank_cycle_open",
        "qpu_submission": False,
        "physical_state_source": {
            "runs": 32,
            "cycles_per_run": 100,
            "beds": 2,
            "cells_per_bed": 4,
            "cell_states_evaluated": int(len(pressure)),
            "pressure_range_bar": [float(np.min(pressure)), float(np.max(pressure))],
        },
        "components": component_results,
        "precision_gate": {
            "qstar_p95_loading_scale_normalized_absolute_error_max": SCALE_NORMALIZED_P95_GATE,
            "ldf_next_p95_loading_scale_normalized_absolute_error_max": SCALE_NORMALIZED_P95_GATE,
            "loading_input_overflow_fraction_required": 0.0,
            "nonzero_qstar_erased_fraction_required": 0.0,
            "co2_additional_relative_error_gate": "retains the original q* <= 5% and LDF-next <= 0.1% p95 relative-error requirements",
            "reason": "tail relative errors are unstable for trace adsorbate loadings; scale-normalized absolute error is reported against the component register range, while raw relative errors remain visible",
        },
        "sequential_five_component_accounting": sequential,
        "cleanliness_by_construction": {
            "per_component": "compute competitive denominator and component numerator; compute reciprocal, q*, and LDF update; copy next loading; reverse every work operation",
            "retained": "18-bit pressure/composition inputs and each selected-width current/next component-loading register",
            "measurements": 0,
            "resets": 0,
        },
        "claim_boundary": {
            "supported": "physical-cache precision screen and all-to-all u/CX compilation of clean one-cell, one-second competitive-Langmuir/LDF updates for H2, CO2, CH4, CO, and N2",
            "unsupported": "gas-phase transport, pressure evolution, valve or tank balances, adaptive integration, a complete adsorption phase or cyclic PSA oracle, routed hardware feasibility, or quantum advantage",
        },
    }
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with OUT_CSV.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(flat_rows[0]))
        writer.writeheader()
        writer.writerows(flat_rows)

    lines = [
        "# Clean five-component competitive-Langmuir/LDF microsteps",
        "",
        f"The precision screen covers **{len(pressure):,}** physical cell states from the 32-run, 100-cycle cache. Each component uses the shared five-component competitive-Langmuir denominator and a component-specific numerator and LDF coefficient.",
        "",
        "| Component | bits | reciprocal segments | q* p95 rel. | q* p95 / register scale | LDF p95 rel. | LDF p95 / register scale | qubits | CX |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in flat_rows:
        lines.append(
            f"| {row['component']} | {row['arithmetic_bits']} | {row['reciprocal_segments']} | "
            f"{row['qstar_p95_relative_error']:.4%} | {row['qstar_p95_scale_normalized_error']:.4%} | "
            f"{row['ldf_next_p95_relative_error']:.4%} | {row['ldf_next_p95_scale_normalized_error']:.4%} | "
            f"{row['logical_qubits']:,} | {row['cx']:,} |"
        )
    lines += [
        "",
        f"The all-component gate requires q* and LDF-next p95 absolute errors below **{SCALE_NORMALIZED_P95_GATE:.2%} of the component loading-register range**, zero loading overflow, and zero erasure of nonzero q*. CO2 additionally retains the original 5%/0.1% relative-error gates. Raw relative errors are reported because they become large for trace loadings near zero.",
        "",
        f"With component arithmetic workspace reused sequentially and all current/next loading registers retained, the modular accounting is **{sequential['logical_qubits']:,} logical qubits**, **{sequential['cx_additive_module_bound']:,} CX**, and additive all-to-all depth **{sequential['depth_all_to_all_additive_module_bound']:,}**.",
        "",
        "This closes the five-component equilibrium/loading microstep item only. Gas transport, pressure evolution, valves, product tank balances, adaptive phase integration, routing, and the complete cyclic oracle remain outside the compiled circuit.",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "status": payload["status"],
                "components": len(component_results),
                "cell_states": len(pressure),
                "sequential_logical_qubits": sequential["logical_qubits"],
                "sequential_cx": sequential["cx_additive_module_bound"],
                "qpu_submission": False,
            },
            indent=2,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
