"""Strict-product compliance surface and QAE oracle for the 2000 cm2 device.

The event is the simultaneous product-quality gate, represented by the signed
margin ``1 - worst_gate_factor``.  Positive values pass every declared gas
composition limit.  The eight uncertainty-cube corners train the response
surface; eight predeclared Sobol interior calculations are hold-out data.

Only the selected policy is compiled.  Its compliance event is non-trivial.
The baseline affine fit does not reproduce all corner labels, so the script
reports baseline direct results without turning that inadequate fit into an
oracle.
"""

from __future__ import annotations

import csv
import itertools
import json
import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
try:
    import qiskit
    from qiskit import QuantumCircuit, qasm3, transpile
    from qiskit.circuit.library import IntegerComparator, WeightedAdder
    QISKIT_AVAILABLE = True
    QISKIT_IMPORT_ERROR = None
except ImportError as exc:  # pure numerical audit remains usable on locked-down hosts
    qiskit = None
    QuantumCircuit = None
    qasm3 = None
    transpile = None
    IntegerComparator = None
    WeightedAdder = None
    QISKIT_AVAILABLE = False
    QISKIT_IMPORT_ERROR = repr(exc)
from scipy.stats import qmc


HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
TRAIN_SOURCE = (
    RESULTS
    / "literature_anchored_policy_uncertainty_screen_2000cm2"
    / "PSA_LITERATURE_CALIBRATED_POLICY_UNCERTAINTY_SCREEN.json"
)
HOLDOUT_SOURCE = (
    RESULTS
    / "literature_anchored_continuous_holdout_2000cm2"
    / "PSA_FINAL_CODESIGN_CONTINUOUS_HOLDOUT.json"
)
SIX_CELL_SOURCE = (
    RESULTS
    / "literature_anchored_policy_6cell_area_2000"
    / "PSA_FINAL_CODESIGN_POLICY_6CELL_REPOLISH_CONFIRMATION.json"
)
OUT = RESULTS / "literature_anchored_strict_margin_qae_bridge_2000cm2"
OUT_JSON = OUT / "PSA_LITERATURE_ANCHORED_STRICT_MARGIN_QAE_BRIDGE.json"
OUT_RESOURCES = OUT / "PSA_LITERATURE_ANCHORED_STRICT_MARGIN_ORACLE_RESOURCES.csv"
OUT_CONVERGENCE = OUT / "PSA_LITERATURE_ANCHORED_STRICT_MARGIN_MC_RQMC.csv"
OUT_MD = OUT / "PSA_LITERATURE_ANCHORED_STRICT_MARGIN_QAE_BRIDGE.md"
OUT_FIG = OUT / "PSA_LITERATURE_ANCHORED_STRICT_MARGIN_QAE_BRIDGE.png"
OUT_QASM = OUT / "PSA_SELECTED_STRICT_PRODUCT_EVENT_ORACLE_8BIT.qasm"

POLICIES = ("baseline", "selected")
INPUT_BITS_CASES = (2, 3, 4, 6, 8)
SUM_BITS = 12
TRANSPILE_SEED = 20261012
CONVERGENCE_N = (16, 32, 64, 128, 256, 512, 1024)
CONVERGENCE_REPLICATES = 64
MC_SEED = 20261021
RQMC_SEED = 20261121


def affine_matrix(x: np.ndarray) -> np.ndarray:
    return np.column_stack([np.ones(len(x)), x])


def trilinear_matrix(x: np.ndarray) -> np.ndarray:
    return np.column_stack(
        [
            np.ones(len(x)),
            x,
            x[:, 0] * x[:, 1],
            x[:, 0] * x[:, 2],
            x[:, 1] * x[:, 2],
            x[:, 0] * x[:, 1] * x[:, 2],
        ]
    )


def metrics(y: np.ndarray, prediction: np.ndarray) -> dict[str, object]:
    truth = y >= 0.0
    label = prediction >= 0.0
    return {
        "n": int(len(y)),
        "rmse_margin": float(np.sqrt(np.mean((prediction - y) ** 2))),
        "maximum_absolute_error_margin": float(np.max(np.abs(prediction - y))),
        "mean_error_margin": float(np.mean(prediction - y)),
        "event_accuracy": float(np.mean(label == truth)),
        "false_positive": int(np.sum(label & ~truth)),
        "false_negative": int(np.sum(~label & truth)),
    }


def exact_weighted_uniform_pass_probability(
    intercept: float, slopes: np.ndarray, threshold: float = 0.0
) -> float:
    """Exact volume of an affine half-space in a unit cube.

    Negative slopes are changed to positive weights by reflecting the
    corresponding uniform coordinate.  Inclusion-exclusion then evaluates the
    generalized Irwin-Hall CDF exactly.
    """

    slopes = np.asarray(slopes, dtype=float)
    reflected_intercept = intercept + float(slopes[slopes < 0.0].sum())
    weights = np.abs(slopes)
    if np.any(weights <= 0.0):
        raise ValueError("all affine slopes must be non-zero")
    t = threshold - reflected_intercept
    dimension = len(weights)
    cdf = 0.0
    for mask in itertools.product((0, 1), repeat=dimension):
        shifted = t - sum(value * bit for value, bit in zip(weights, mask))
        cdf += (-1) ** sum(mask) * max(shifted, 0.0) ** dimension
    cdf /= math.factorial(dimension) * float(np.prod(weights))
    return float(1.0 - np.clip(cdf, 0.0, 1.0))


def integerize(intercept: float, slopes: np.ndarray, bits: int) -> dict[str, object]:
    levels = 2**bits - 1
    raw_weights = np.asarray(
        [slope * (2**bit) / levels for slope in slopes for bit in range(bits)]
    )
    negative = raw_weights < 0.0
    transformed_constant = intercept - float(np.abs(raw_weights[negative]).sum())
    magnitude = np.abs(raw_weights)
    target_sum = 2**SUM_BITS - 1
    ideal = magnitude / magnitude.sum() * target_sum
    weights = np.floor(ideal).astype(int)
    residual = target_sum - int(weights.sum())
    if residual:
        order = np.argsort(-(ideal - weights), kind="mergesort")
        weights[order[:residual]] += 1
    scale = target_sum / float(magnitude.sum())
    integer_threshold = int(math.ceil((0.0 - transformed_constant) * scale))
    if not 0 <= integer_threshold <= target_sum:
        raise AssertionError("non-trivial oracle threshold outside weighted-sum support")
    return {
        "input_bits_per_variable": bits,
        "levels_per_variable": levels,
        "state_qubits": len(slopes) * bits,
        "negative_bit_mask": negative.tolist(),
        "integer_weights": weights.tolist(),
        "integer_weight_sum": int(weights.sum()),
        "integer_threshold": integer_threshold,
        "integer_scale": scale,
        "transformed_constant": transformed_constant,
    }


def encoded_contributions(spec: dict[str, object]) -> list[np.ndarray]:
    bits = int(spec["input_bits_per_variable"])
    levels = int(spec["levels_per_variable"])
    weights = np.asarray(spec["integer_weights"], dtype=int)
    negative = np.asarray(spec["negative_bit_mask"], dtype=bool)
    result = []
    for feature in range(3):
        values = np.zeros(levels + 1, dtype=int)
        for code in range(levels + 1):
            total = 0
            for bit in range(bits):
                index = feature * bits + bit
                state = (code >> bit) & 1
                if negative[index]:
                    state = 1 - state
                total += state * weights[index]
            values[code] = total
        result.append(values)
    return result


def exact_encoded_probability(spec: dict[str, object]) -> float:
    contributions = encoded_contributions(spec)
    third = np.sort(contributions[2])
    threshold = int(spec["integer_threshold"])
    count = 0
    for first in contributions[0]:
        needed = threshold - first - contributions[1]
        count += int(np.sum(len(third) - np.searchsorted(third, needed, side="left")))
    return count / len(contributions[0]) ** 3


def encode_points(x: np.ndarray, spec: dict[str, object]) -> np.ndarray:
    levels = int(spec["levels_per_variable"])
    codes = np.rint(np.clip(x, 0.0, 1.0) * levels).astype(int)
    contributions = encoded_contributions(spec)
    sums = sum(contributions[j][codes[:, j]] for j in range(3))
    return sums >= int(spec["integer_threshold"])


def build_oracle(spec: dict[str, object]) -> tuple[QuantumCircuit, dict[str, int]]:
    if not QISKIT_AVAILABLE:
        raise RuntimeError(f"Qiskit is unavailable: {QISKIT_IMPORT_ERROR}")
    state_qubits = int(spec["state_qubits"])
    adder = WeightedAdder(state_qubits, list(map(int, spec["integer_weights"])))
    comparator = IntegerComparator(
        adder.num_sum_qubits, int(spec["integer_threshold"]), geq=True
    )
    sum_qubits = adder.num_sum_qubits
    adder_ancillas = adder.num_ancillas
    comparator_ancillas = comparator.num_ancillas
    total = state_qubits + sum_qubits + adder_ancillas + 1 + comparator_ancillas
    circuit = QuantumCircuit(total, name=f"S_selected_strict_b{spec['input_bits_per_variable']}")
    state = list(range(state_qubits))
    sums = list(range(state_qubits, state_qubits + sum_qubits))
    adder_work = list(
        range(state_qubits + sum_qubits, state_qubits + sum_qubits + adder_ancillas)
    )
    flag = state_qubits + sum_qubits + adder_ancillas
    comparator_work = list(range(flag + 1, total))
    negative_state = [
        index for index, value in enumerate(spec["negative_bit_mask"]) if value
    ]
    if negative_state:
        circuit.x(negative_state)
    circuit.compose(adder, qubits=state + sums + adder_work, inplace=True)
    circuit.compose(comparator, qubits=sums + [flag] + comparator_work, inplace=True)
    circuit.z(flag)
    circuit.compose(comparator.inverse(), qubits=sums + [flag] + comparator_work, inplace=True)
    circuit.compose(adder.inverse(), qubits=state + sums + adder_work, inplace=True)
    if negative_state:
        circuit.x(negative_state)
    return circuit, {
        "state_qubits": state_qubits,
        "sum_qubits": sum_qubits,
        "adder_ancillas": adder_ancillas,
        "phase_flag_qubits": 1,
        "comparator_ancillas": comparator_ancillas,
        "total_logical_qubits": total,
    }


def convergence_rows(
    exact_probability: float, intercept: float, slopes: np.ndarray
) -> list[dict[str, object]]:
    rows = []
    for n in CONVERGENCE_N:
        power = int(round(math.log2(n)))
        estimates = {"MC": [], "scrambled_Sobol_RQMC": []}
        for replicate in range(CONVERGENCE_REPLICATES):
            rng = np.random.default_rng(MC_SEED + 1009 * replicate + n)
            x_mc = rng.random((n, 3))
            estimates["MC"].append(float(np.mean(intercept + x_mc @ slopes >= 0.0)))
            x_rqmc = qmc.Sobol(
                d=3, scramble=True, seed=RQMC_SEED + 1009 * replicate + n
            ).random_base2(power)
            estimates["scrambled_Sobol_RQMC"].append(
                float(np.mean(intercept + x_rqmc @ slopes >= 0.0))
            )
        for method, values_list in estimates.items():
            values = np.asarray(values_list)
            rows.append(
                {
                    "method": method,
                    "n": n,
                    "replicates": CONVERGENCE_REPLICATES,
                    "mean_probability": float(np.mean(values)),
                    "bias": float(np.mean(values) - exact_probability),
                    "rmse": float(np.sqrt(np.mean((values - exact_probability) ** 2))),
                    "mean_absolute_error": float(np.mean(np.abs(values - exact_probability))),
                    "standard_deviation": float(np.std(values, ddof=1)),
                }
            )
    return rows


def main() -> None:
    train_payload = json.loads(TRAIN_SOURCE.read_text(encoding="utf-8"))
    holdout_payload = json.loads(HOLDOUT_SOURCE.read_text(encoding="utf-8"))
    six_cell_payload = json.loads(SIX_CELL_SOURCE.read_text(encoding="utf-8"))
    train_rows = train_payload["rows"]
    holdout_rows = holdout_payload["rows"]
    corner_scenarios = [
        row
        for row in train_payload["run_signature"]["scenarios"]
        if row["scenario_kind"] == "corner"
    ]
    capacity_endpoints = sorted(
        {float(row["capacity_coordinate_c"]) for row in corner_scenarios}, reverse=True
    )
    capacity_u0, capacity_u1 = capacity_endpoints

    def coordinates(row: dict) -> np.ndarray:
        return np.asarray(
            [
                (float(row["feed_h2_multiplier"]) - 0.95) / 0.10,
                (float(row["capacity_coordinate_c"]) - capacity_u0)
                / (capacity_u1 - capacity_u0),
                (float(row["ldf_factor"]) - 0.8) / 0.4,
            ]
        )

    models: dict[str, dict[str, object]] = {}
    direct_by_policy: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    for policy in POLICIES:
        train = [
            row
            for row in train_rows
            if row["policy"] == policy and row["scenario_kind"] == "corner"
        ]
        holdout = [row for row in holdout_rows if row["policy"] == policy]
        x_train = np.asarray([coordinates(row) for row in train])
        y_train = np.asarray([1.0 - float(row["worst_gate_factor"]) for row in train])
        x_holdout = np.asarray([coordinates(row) for row in holdout])
        y_holdout = np.asarray(
            [1.0 - float(row["worst_gate_factor"]) for row in holdout]
        )
        affine = np.linalg.lstsq(affine_matrix(x_train), y_train, rcond=None)[0]
        trilinear = np.linalg.lstsq(
            trilinear_matrix(x_train), y_train, rcond=None
        )[0]
        affine_train_metrics = metrics(y_train, affine_matrix(x_train) @ affine)
        affine_holdout_metrics = metrics(y_holdout, affine_matrix(x_holdout) @ affine)
        trilinear_holdout_metrics = metrics(
            y_holdout, trilinear_matrix(x_holdout) @ trilinear
        )
        other_gates_pass = all(
            bool(row["reserve_gate"])
            and bool(row["numerical_gate"])
            and float(row["qualified_h2_rate_mol_s"]) >= 2.0e-3
            for row in train + holdout
        )
        event_equivalence = all(
            (1.0 - float(row["worst_gate_factor"]) >= 0.0)
            == bool(row["conditional_design_event"])
            for row in train + holdout
        )
        models[policy] = {
            "training_corner_count": len(train),
            "holdout_count": len(holdout),
            "direct_pass_count": int(
                sum(bool(row["conditional_design_event"]) for row in train + holdout)
            ),
            "direct_total_count": len(train) + len(holdout),
            "all_noncomposition_gates_pass": other_gates_pass,
            "quality_margin_event_matches_full_design_event": event_equivalence,
            "affine_coefficients": {
                "intercept": float(affine[0]),
                "feed_u": float(affine[1]),
                "equilibrium_pc_u": float(affine[2]),
                "ldf_u": float(affine[3]),
            },
            "affine_training_metrics": affine_train_metrics,
            "affine_holdout_metrics": affine_holdout_metrics,
            "trilinear_holdout_metrics": trilinear_holdout_metrics,
            "affine_oracle_eligible": bool(
                affine_train_metrics["event_accuracy"] == 1.0
                and affine_holdout_metrics["event_accuracy"] == 1.0
                and other_gates_pass
                and event_equivalence
            ),
        }
        direct_by_policy[policy] = (
            np.vstack([x_train, x_holdout]),
            np.hstack([y_train >= 0.0, y_holdout >= 0.0]),
        )

    if not models["selected"]["affine_oracle_eligible"]:
        raise AssertionError("selected affine strict-product surface failed eligibility")
    if models["baseline"]["affine_oracle_eligible"]:
        raise AssertionError("baseline fit unexpectedly became oracle-eligible")

    selected_coefficients = models["selected"]["affine_coefficients"]
    intercept = float(selected_coefficients["intercept"])
    slopes = np.asarray(
        [
            selected_coefficients["feed_u"],
            selected_coefficients["equilibrium_pc_u"],
            selected_coefficients["ldf_u"],
        ]
    )
    exact_probability = exact_weighted_uniform_pass_probability(intercept, slopes)
    maximum_holdout_error = float(
        models["selected"]["affine_holdout_metrics"]["maximum_absolute_error_margin"]
    )
    probability_bracket = [
        exact_weighted_uniform_pass_probability(
            intercept, slopes, threshold=maximum_holdout_error
        ),
        exact_weighted_uniform_pass_probability(
            intercept, slopes, threshold=-maximum_holdout_error
        ),
    ]
    models["selected"]["exact_uniform_envelope_pass_probability"] = exact_probability
    models["selected"]["holdout_max_error_probability_bracket"] = probability_bracket

    convergence = convergence_rows(exact_probability, intercept, slopes)
    direct_x, direct_truth = direct_by_policy["selected"]
    resource_rows = []
    integer_specs = []
    qasm_circuit = None
    for bits in INPUT_BITS_CASES:
        spec = integerize(intercept, slopes, bits)
        labels = encode_points(direct_x, spec)
        encoded_probability = exact_encoded_probability(spec)
        circuit, registers = build_oracle(spec)
        isa = transpile(
            circuit,
            basis_gates=["u", "cx"],
            optimization_level=1,
            seed_transpiler=TRANSPILE_SEED,
        )
        row = {
            "input_bits_per_variable": bits,
            **registers,
            "direct_states_checked": int(len(direct_truth)),
            "direct_label_disagreement": float(np.mean(labels != direct_truth)),
            "direct_false_positive": int(np.sum(labels & ~direct_truth)),
            "direct_false_negative": int(np.sum(~labels & direct_truth)),
            "exact_continuous_affine_probability": exact_probability,
            "exact_discrete_oracle_probability": encoded_probability,
            "absolute_probability_discretization_error": abs(
                encoded_probability - exact_probability
            ),
            "transpiled_depth": int(isa.depth()),
            "transpiled_size": int(isa.size()),
            "transpiled_cx": int(isa.count_ops().get("cx", 0)),
        }
        resource_rows.append(row)
        integer_specs.append(spec)
        if bits == 8:
            qasm_circuit = circuit

    six_selected = [
        row for row in six_cell_payload["rows"] if row["policy"] == "selected"
    ]
    low_resolution_selected = {
        row["scenario"]: bool(row["continuous_gate_pass"])
        for row in train_rows
        if row["policy"] == "selected"
    }
    representative_mesh_comparison = []
    for row in six_selected:
        scenario = row["scenario"]
        representative_mesh_comparison.append(
            {
                "scenario": scenario,
                "two_cell_pass": low_resolution_selected[scenario],
                "six_cell_pass": bool(row["continuous_gate_pass"]),
                "label_disagreement": bool(
                    low_resolution_selected[scenario]
                    != bool(row["continuous_gate_pass"])
                ),
            }
        )

    qae_comparison = []
    for epsilon in (0.10, 0.05, 0.025, 0.01):
        qae_queries = int(math.ceil(math.pi / epsilon))
        mc_bound = int(math.ceil(math.log(2.0 / 0.05) / (2.0 * epsilon**2)))
        qae_comparison.append(
            {
                "absolute_error_target": epsilon,
                "ideal_qae_query_proxy": qae_queries,
                "hoeffding_mc_95_percent_bound": mc_bound,
                "eight_bit_oracle_cx_lower_bound": qae_queries
                * resource_rows[-1]["transpiled_cx"],
            }
        )

    payload = {
        "schema": "psa-literature-anchored-strict-margin-qae-bridge/v1",
        "status": "selected_policy_strict_product_event_compiled",
        "qiskit_version": qiskit.__version__,
        "event": {
            "definition": "all declared strict product-composition limits pass",
            "signed_margin": "1 - worst_gate_factor",
            "pass_condition": "signed_margin >= 0",
            "measure": "independent uniform measure over the declared three-dimensional engineering envelope",
            "coordinates": ["feed_u", "equilibrium_pc_u", "ldf_u"],
            "device": "2000 cm2 membrane, 7.5x selectivity multiplier",
        },
        "sources": {
            "corner_training": str(TRAIN_SOURCE.relative_to(HERE)),
            "predeclared_interior_holdout": str(HOLDOUT_SOURCE.relative_to(HERE)),
            "six_cell_representative_check": str(SIX_CELL_SOURCE.relative_to(HERE)),
        },
        "models": models,
        "engineering_decision": {
            "baseline_direct_pass_count": models["baseline"]["direct_pass_count"],
            "baseline_direct_total_count": models["baseline"]["direct_total_count"],
            "baseline_affine_oracle_rejected": True,
            "selected_direct_pass_count": models["selected"]["direct_pass_count"],
            "selected_direct_total_count": models["selected"]["direct_total_count"],
            "selected_exact_uniform_envelope_pass_probability": exact_probability,
            "selected_holdout_error_probability_bracket": probability_bracket,
            "selected_policy_qae_event_nontrivial": bool(0.0 < exact_probability < 1.0),
        },
        "mesh_resolution_audit": {
            "representative_cases": representative_mesh_comparison,
            "label_disagreement_count": int(
                sum(row["label_disagreement"] for row in representative_mesh_comparison)
            ),
            "interpretation": "The QAE probability is conditional on the two-cell screening model; two low-feed representative labels improve from fail to pass at six cells, so it is not a mesh-independent plant reliability estimate.",
        },
        "mc_rqmc_convergence": convergence,
        "oracle_resources": resource_rows,
        "integer_specs": integer_specs,
        "ideal_query_comparison": qae_comparison,
        "claim_limits": [
            "The uniform envelope is an engineering sensitivity measure, not a plant-calibrated probability distribution.",
            "The affine surrogate is trained on eight direct two-cell corners and validated on eight predeclared direct two-cell interior points.",
            "The strict-product QAE event is compiled for the selected policy only; the baseline affine model was rejected because it misclassified two training corners.",
            "Two of three representative selected-policy labels differ between two-cell and six-cell calculations, and the six-cell labels are more favorable.",
            "The 2000 cm2/7.5x membrane is a literature-anchored conditional numerical device pending one-device simultaneous multicomponent measurements.",
            "Circuit counts cover one all-to-all compute-compare-phase-uncompute oracle call and exclude routing, QAE reflections, noise, error correction, and readout overhead.",
            "The low-dimensional affine probability is inexpensive classically; no present practical quantum advantage is claimed.",
        ],
    }

    OUT.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    with OUT_RESOURCES.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(resource_rows[0]))
        writer.writeheader()
        writer.writerows(resource_rows)
    with OUT_CONVERGENCE.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(convergence[0]))
        writer.writeheader()
        writer.writerows(convergence)
    if qasm_circuit is None:
        raise AssertionError("8-bit oracle was not built")
    OUT_QASM.write_text(qasm3.dumps(qasm_circuit), encoding="utf-8")

    eight_bit = resource_rows[-1]
    lines = [
        "# Strict-product compliance probability and QAE bridge",
        "",
        "The 2000 cm2 device changes the controlling event. Product flow, tank reserve, and numerical gates pass all 16 selected-policy direct cases; strict product composition determines success. The signed response is `1 - worst_gate_factor`, so zero is the simultaneous impurity boundary.",
        "",
        f"- selected direct corner passes: **{sum(bool(r['conditional_design_event']) for r in train_rows if r['policy']=='selected' and r['scenario_kind']=='corner')}/8**",
        f"- selected predeclared interior passes: **{sum(bool(r['conditional_design_event']) for r in holdout_rows if r['policy']=='selected')}/8**",
        f"- selected affine corner event accuracy: **{models['selected']['affine_training_metrics']['event_accuracy']:.0%}**",
        f"- selected affine hold-out event accuracy: **{models['selected']['affine_holdout_metrics']['event_accuracy']:.0%}**",
        f"- exact uniform-envelope pass probability: **{exact_probability:.6f}**",
        f"- hold-out-error probability bracket: **[{probability_bracket[0]:.6f}, {probability_bracket[1]:.6f}]**",
        "",
        "The baseline has zero full-event passes in its 16 direct corner and hold-out cases. Its affine margin fit misclassifies two training corners, so no baseline QAE oracle is reported.",
        "",
        "| bits/variable | state qubits | total qubits | direct disagreement | discrete probability | probability error | CX/oracle | depth/oracle |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in resource_rows:
        lines.append(
            f"| {row['input_bits_per_variable']} | {row['state_qubits']} | {row['total_logical_qubits']} | "
            f"{row['direct_label_disagreement']:.6f} | {row['exact_discrete_oracle_probability']:.6f} | "
            f"{row['absolute_probability_discretization_error']:.6f} | {row['transpiled_cx']:,} | {row['transpiled_depth']:,} |"
        )
    lines += [
        "",
        f"The 8-bit selected-policy oracle uses **{eight_bit['total_logical_qubits']} logical qubits**, **{eight_bit['transpiled_cx']:,} CX gates**, and depth **{eight_bit['transpiled_depth']:,}** per all-to-all oracle call.",
        "",
        "Two of three representative selected-policy labels change from fail at two cells to pass at six cells. The reported probability therefore describes the conservative two-cell screening surface. A full six-cell uncertainty cube is required before calling it a mesh-independent reliability estimate.",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    fig, axes = plt.subplots(1, 3, figsize=(15.4, 4.3), constrained_layout=True)
    direct_counts = [
        models["baseline"]["direct_pass_count"],
        models["selected"]["direct_pass_count"],
    ]
    axes[0].bar(["baseline", "selected"], direct_counts, color=["#6b7280", "#2563eb"])
    axes[0].set_ylim(0, 16.8)
    axes[0].set(ylabel="Direct passes (of 16)", title="Direct strict-product outcomes")
    for i, value in enumerate(direct_counts):
        axes[0].text(i, value + 0.35, f"{value}/16", ha="center")

    for method, color, marker in (
        ("MC", "#dc2626", "o"),
        ("scrambled_Sobol_RQMC", "#059669", "s"),
    ):
        subset = [row for row in convergence if row["method"] == method]
        axes[1].loglog(
            [row["n"] for row in subset],
            [row["rmse"] for row in subset],
            marker=marker,
            color=color,
            label=method,
        )
    axes[1].set(xlabel="samples", ylabel="Probability RMSE", title="Classical convergence")
    axes[1].grid(True, which="both", alpha=0.25)
    axes[1].legend(frameon=False, fontsize=8)

    axes[2].plot(
        [row["input_bits_per_variable"] for row in resource_rows],
        [row["absolute_probability_discretization_error"] for row in resource_rows],
        "o-",
        color="#7c3aed",
        label="probability error",
    )
    axes[2].set(
        xlabel="fixed-point bits per variable",
        ylabel="Probability discretization error",
        title="Oracle precision and resources",
    )
    axes[2].grid(alpha=0.25)
    twin = axes[2].twinx()
    twin.plot(
        [row["input_bits_per_variable"] for row in resource_rows],
        [row["transpiled_cx"] for row in resource_rows],
        "s--",
        color="#ed7d31",
        label="CX/oracle",
    )
    twin.set_ylabel("CX gates")
    h1, l1 = axes[2].get_legend_handles_labels()
    h2, l2 = twin.get_legend_handles_labels()
    axes[2].legend(h1 + h2, l1 + l2, frameon=False, fontsize=8, loc="upper right")
    axes[0].grid(axis="y", alpha=0.25)
    fig.savefig(OUT_FIG, dpi=220)
    plt.close(fig)

    print(
        json.dumps(
            {
                "status": payload["status"],
                "selected_probability": exact_probability,
                "selected_probability_bracket": probability_bracket,
                "mesh_label_disagreements": payload["mesh_resolution_audit"][
                    "label_disagreement_count"
                ],
                "eight_bit_oracle": eight_bit,
                "outputs": [
                    str(OUT_JSON),
                    str(OUT_RESOURCES),
                    str(OUT_CONVERGENCE),
                    str(OUT_MD),
                    str(OUT_FIG),
                    str(OUT_QASM),
                ],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
