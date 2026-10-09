"""Compile a reversible competitive-Langmuir numerator/denominator microkernel.

The primary physical model evaluates, for each cell,

    q_i* = qcap_i b_i P y_i / (1 + P sum_j b_j y_j).

This audit compiles the shared affinity sum, the CO2 numerator ``P*y_CO2``,
and the pressure-affinity product used in the denominator.  The constant one
is preloaded at the correct fixed-point scale.  It deliberately leaves the
reciprocal/division, final q* scaling, LDF update, and ODE integration open.

Precision is screened against every cell state retained in the 32-run,
100-cycle physical CSS cache.  No QPU work is submitted.
"""

from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit.circuit.library import MultiplierGate, WeightedAdder


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RESULTS = ROOT / "10_TEA_LCA_Python" / "results" / "pycharm_publication_enhancement"
CACHE = HERE / "cce_primary_physical_css_horizon_cache.npz"
OUT_JSON = RESULTS / "PSA_QAE_CCE_PRIMARY_QSTAR_REVERSIBLE_MICROKERNEL.json"
OUT_CSV = RESULTS / "PSA_QAE_CCE_PRIMARY_QSTAR_REVERSIBLE_MICROKERNEL.csv"
OUT_MD = RESULTS / "PSA_QAE_CCE_PRIMARY_QSTAR_REVERSIBLE_MICROKERNEL.md"
OUT_PNG = RESULTS / "PSA_QAE_CCE_PRIMARY_QSTAR_REVERSIBLE_MICROKERNEL_FIGURE.png"
OUT_PDF = RESULTS / "PSA_QAE_CCE_PRIMARY_QSTAR_REVERSIBLE_MICROKERNEL_FIGURE.pdf"

sys.path.insert(0, str(HERE.parent))
from psa_qae.psa_spatial_network_probe_n2 import (  # noqa: E402
    B1,
    B2,
    COMPONENTS,
    SpatialParams,
    cell_pressure,
    cell_y,
)


INPUT_BITS = [2, 4, 6, 8, 10, 12, 14, 16, 18, 20]
AFFINITY_COEFFICIENT_BITS = 8
DENOMINATOR_P95_RELATIVE_ERROR_GATE = 1.0e-3
CO2_QSTAR_P95_RELATIVE_ERROR_GATE = 5.0e-2
TRANSPILER_SEED = 20261009


def physical_states() -> tuple[np.ndarray, np.ndarray]:
    cache = np.load(CACHE)
    boundaries = np.asarray(cache["boundaries"], dtype=float)
    if boundaries.shape != (32, 101, 85):
        raise AssertionError(boundaries.shape)
    params = SpatialParams(n_cells=4)
    pressures: list[float] = []
    compositions: list[np.ndarray] = []
    for state in boundaries[:, :, :80].reshape(-1, 40):
        gas = state[:20].reshape(5, 4)
        pressures.extend(cell_pressure(gas, params).tolist())
        compositions.extend(cell_y(gas).T)
    return np.asarray(pressures, dtype=float), np.asarray(compositions, dtype=float)


def nominal_affinities() -> tuple[np.ndarray, np.ndarray]:
    params = SpatialParams(n_cells=1)
    b = B1 * np.exp(B2 / params.temperature_K)
    coeff_max = (1 << AFFINITY_COEFFICIENT_BITS) - 1
    integer = np.rint(b / np.max(b) * coeff_max).astype(int)
    return b, integer


def precision_row(
    bits: int,
    pressure: np.ndarray,
    composition: np.ndarray,
    affinities: np.ndarray,
    affinity_integer: np.ndarray,
) -> dict:
    levels = (1 << bits) - 1
    coefficient_levels = (1 << AFFINITY_COEFFICIENT_BITS) - 1
    pressure_max = float(np.max(pressure))
    pressure_q = np.rint(pressure / pressure_max * levels) / levels * pressure_max
    composition_q = np.rint(composition * levels) / levels
    affinity_q = affinity_integer / coefficient_levels * float(np.max(affinities))

    denominator = 1.0 + pressure * np.sum(composition * affinities[None, :], axis=1)
    denominator_q = 1.0 + pressure_q * np.sum(composition_q * affinity_q[None, :], axis=1)
    numerator = pressure * composition[:, 1]
    numerator_q = pressure_q * composition_q[:, 1]
    qstar_factor = affinities[1]
    qstar = qstar_factor * numerator / denominator
    qstar_q = qstar_factor * numerator_q / denominator_q

    denominator_error = np.abs(denominator_q - denominator) / denominator
    numerator_error = np.abs(numerator_q - numerator) / np.maximum(np.abs(numerator), 1.0e-15)
    qstar_error = np.abs(qstar_q - qstar) / np.maximum(np.abs(qstar), 1.0e-15)
    nonzero_numerator_zeroed = (numerator > 0.0) & (numerator_q == 0.0)

    weights = [
        int(affinity_integer[component]) * (1 << bit)
        for component in range(len(COMPONENTS))
        for bit in range(bits)
    ]
    adder = WeightedAdder(len(weights), weights)
    sum_bits = int(adder.num_sum_qubits)
    ancillas = int(adder.num_ancillas)

    # Registers: padded P, five y registers, affinity sum, adder workspace,
    # P*y_CO2 output, and scaled denominator accumulator.
    p0 = 0
    y0 = sum_bits
    sum0 = y0 + 5 * bits
    anc0 = sum0 + sum_bits
    numerator0 = anc0 + ancillas
    denominator0 = numerator0 + 2 * bits
    total_qubits = denominator0 + 2 * sum_bits
    circuit = QuantumCircuit(total_qubits, name=f"qstar_num_den_{bits}b")

    state_qubits = list(range(y0, y0 + 5 * bits))
    sum_qubits = list(range(sum0, sum0 + sum_bits))
    ancilla_qubits = list(range(anc0, anc0 + ancillas))
    circuit.append(adder, state_qubits + sum_qubits + ancilla_qubits)

    co2_qubits = list(range(y0 + bits, y0 + 2 * bits))
    numerator_qubits = list(range(numerator0, numerator0 + 2 * bits))
    circuit.append(
        MultiplierGate(bits, 2 * bits),
        list(range(p0, p0 + bits)) + co2_qubits + numerator_qubits,
    )

    denominator_scale = levels * levels * coefficient_levels / (
        pressure_max * float(np.max(affinities))
    )
    denominator_one_code = int(round(denominator_scale))
    if denominator_one_code >= (1 << (2 * sum_bits)):
        raise AssertionError((bits, sum_bits, denominator_one_code))
    for bit in range(2 * sum_bits):
        if (denominator_one_code >> bit) & 1:
            circuit.x(denominator0 + bit)
    circuit.append(
        MultiplierGate(sum_bits, 2 * sum_bits),
        list(range(p0, p0 + sum_bits))
        + sum_qubits
        + list(range(denominator0, denominator0 + 2 * sum_bits)),
    )

    compiled = transpile(
        circuit,
        basis_gates=["u", "cx"],
        optimization_level=1,
        seed_transpiler=TRANSPILER_SEED,
    )
    forward_cx = int(compiled.count_ops().get("cx", 0))
    forward_u = int(compiled.count_ops().get("u", 0))
    row = {
        "bits_per_pressure_and_composition": bits,
        "affinity_coefficient_bits": AFFINITY_COEFFICIENT_BITS,
        "affinity_sum_bits": sum_bits,
        "weighted_adder_ancillas": ancillas,
        "logical_qubits": int(compiled.num_qubits),
        "forward_depth_all_to_all": int(compiled.depth()),
        "forward_cx": forward_cx,
        "forward_u": forward_u,
        "clean_compute_uncompute_cx": 2 * forward_cx,
        "clean_compute_uncompute_u": 2 * forward_u,
        "denominator_one_code": denominator_one_code,
        "denominator_p95_relative_error": float(np.quantile(denominator_error, 0.95)),
        "denominator_max_relative_error": float(np.max(denominator_error)),
        "co2_numerator_p95_relative_error": float(np.quantile(numerator_error, 0.95)),
        "co2_qstar_p95_relative_error": float(np.quantile(qstar_error, 0.95)),
        "co2_qstar_max_relative_error": float(np.max(qstar_error)),
        "nonzero_co2_numerator_zeroed_fraction": float(np.mean(nonzero_numerator_zeroed)),
    }
    row["passes_declared_microkernel_precision_gate"] = bool(
        row["denominator_p95_relative_error"] <= DENOMINATOR_P95_RELATIVE_ERROR_GATE
        and row["co2_qstar_p95_relative_error"] <= CO2_QSTAR_P95_RELATIVE_ERROR_GATE
        and row["nonzero_co2_numerator_zeroed_fraction"] == 0.0
    )
    return row


def main() -> None:
    pressure, composition = physical_states()
    affinities, affinity_integer = nominal_affinities()
    rows = [
        precision_row(bits, pressure, composition, affinities, affinity_integer)
        for bits in INPUT_BITS
    ]
    selected = next((row for row in rows if row["passes_declared_microkernel_precision_gate"]), None)
    if selected is None:
        raise AssertionError("no screened precision passes the microkernel gate")

    payload = {
        "schema": "psa-qae-cce-primary-qstar-reversible-microkernel/v1",
        "status": "competitive_langmuir_numerator_denominator_preparation_compiled_reciprocal_ode_open",
        "qpu_submission": False,
        "physical_state_source": {
            "runs": 32,
            "cycles_per_run": 100,
            "cells_per_bed": 4,
            "beds": 2,
            "cell_states_evaluated": int(len(pressure)),
            "pressure_range_bar": [float(np.min(pressure)), float(np.max(pressure))],
            "co2_mole_fraction_range": [float(np.min(composition[:, 1])), float(np.max(composition[:, 1]))],
        },
        "equation": {
            "form": "q_i_star = qcap_i*b_i*P*y_i/(1 + P*sum_j(b_j*y_j))",
            "components": list(COMPONENTS),
            "temperature_K": SpatialParams(n_cells=1).temperature_K,
            "nominal_affinity_1_per_bar": affinities.tolist(),
            "affinity_coefficient_bits": AFFINITY_COEFFICIENT_BITS,
            "normalized_integer_affinity_weights": affinity_integer.tolist(),
            "compiled_terms": [
                "eight-bit-coefficient weighted sum of five composition registers",
                "CO2 numerator P*y_CO2",
                "pressure times shared affinity sum",
                "fixed-point preload of the denominator constant one",
            ],
        },
        "precision_gate": {
            "denominator_p95_relative_error_max": DENOMINATOR_P95_RELATIVE_ERROR_GATE,
            "co2_qstar_p95_relative_error_max": CO2_QSTAR_P95_RELATIVE_ERROR_GATE,
            "nonzero_co2_numerator_zeroed_fraction_required": 0.0,
        },
        "rows": rows,
        "selected": selected,
        "claim_boundary": {
            "supported": "primitive-gate compilation and physical-state precision screen for the shared competitive-Langmuir denominator preparation and CO2 numerator",
            "unsupported": "a complete qstar divider/reciprocal, all five qstar outputs, reversible LDF/ODE integration, a full phase or cycle unitary, hardware feasibility, or quantum advantage",
        },
    }
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with OUT_CSV.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    lines = [
        "# Reversible competitive-Langmuir numerator/denominator microkernel",
        "",
        f"The screen uses **{len(pressure):,}** cell states from all 32 physical 100-cycle trajectories. The compiled block prepares the shared five-component affinity sum, `P*y_CO2`, and the scaled denominator `1 + P sum(b_i y_i)` in separate output registers.",
        "",
        f"The first tier passing p95 denominator error <= `{DENOMINATOR_P95_RELATIVE_ERROR_GATE:.0e}`, p95 CO2 qstar-factor error <= `{CO2_QSTAR_P95_RELATIVE_ERROR_GATE:.2f}`, and zero nonzero-numerator erasures is **{selected['bits_per_pressure_and_composition']} bits**. It uses **{selected['logical_qubits']} logical qubits**, depth **{selected['forward_depth_all_to_all']:,}**, **{selected['forward_cx']:,} forward CX**, and **{selected['clean_compute_uncompute_cx']:,} clean-equivalent CX** in an all-to-all `u/CX` basis.",
        "",
        "The equilibrium reciprocal/division, final loading scaling, all five outputs, LDF update, and ODE time integration are not compiled. The result is a measured nonlinear subkernel boundary rather than a completed physical phase or cycle oracle.",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    bits = [row["bits_per_pressure_and_composition"] for row in rows]
    fig, axes = plt.subplots(1, 3, figsize=(13.2, 4.35), constrained_layout=True)
    axes[0].semilogy(bits, [row["denominator_p95_relative_error"] for row in rows], "o-", label="denominator")
    axes[0].semilogy(bits, [row["co2_qstar_p95_relative_error"] for row in rows], "s-", label="CO2 q* factor")
    axes[0].axhline(DENOMINATOR_P95_RELATIVE_ERROR_GATE, color="#1d4ed8", ls="--", lw=1)
    axes[0].axhline(CO2_QSTAR_P95_RELATIVE_ERROR_GATE, color="#b91c1c", ls="--", lw=1)
    axes[0].axvline(selected["bits_per_pressure_and_composition"], color="#166534", ls=":")
    axes[0].set(xlabel="bits per P and y component", ylabel="p95 relative error", title="Physical-cache precision")
    axes[0].grid(alpha=0.25, which="both"); axes[0].legend(fontsize=8)

    axes[1].plot(bits, [row["logical_qubits"] for row in rows], "o-", label="logical qubits")
    axes[1].plot(bits, [row["affinity_sum_bits"] for row in rows], "s--", label="affinity-sum bits")
    axes[1].set(xlabel="bits per P and y component", ylabel="qubits / bits", title="Register growth")
    axes[1].grid(alpha=0.25); axes[1].legend(fontsize=8)

    axes[2].semilogy(bits, [row["forward_cx"] for row in rows], "o-", label="forward CX")
    axes[2].semilogy(bits, [row["clean_compute_uncompute_cx"] for row in rows], "s--", label="clean-equivalent CX")
    axes[2].scatter([selected["bits_per_pressure_and_composition"]], [selected["forward_cx"]], color="#b91c1c", s=65, zorder=3)
    axes[2].set(xlabel="bits per P and y component", ylabel="CX gates", title="Primitive-gate cost")
    axes[2].grid(alpha=0.25, which="both"); axes[2].legend(fontsize=8)
    fig.suptitle("Actual competitive-Langmuir preparation is already large before reciprocal or ODE integration", fontsize=13.5, fontweight="bold")
    fig.savefig(OUT_PNG, dpi=260)
    fig.savefig(OUT_PDF)
    plt.close(fig)

    print(
        json.dumps(
            {
                "status": payload["status"],
                "selected_bits": selected["bits_per_pressure_and_composition"],
                "logical_qubits": selected["logical_qubits"],
                "forward_cx": selected["forward_cx"],
                "clean_compute_uncompute_cx": selected["clean_compute_uncompute_cx"],
                "qpu_submission": False,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
