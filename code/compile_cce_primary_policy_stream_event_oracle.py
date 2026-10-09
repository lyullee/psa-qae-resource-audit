"""Compile the candidate-policy stream-to-event oracle for the primary PSA case.

The two calibrated adsorption maps are affine.  For a fixed candidate recycle
policy, their six event-active outputs can therefore be collapsed exactly into
three affine observables: adsorption-feed H2, external-product H2, and external
product impurity.  This script quantizes those three collapsed maps, constructs
their registers reversibly, evaluates the purity/recovery event, applies a
joint phase, and uncomputes the complete calculation.

The circuit starts from encoded phase-start states and shared process
parameters.  Recycle is a classically fixed policy constant, as it is in each
candidate-policy probability oracle.  Physical repeated-cycle CSS, state
preparation, backend routing/noise, and external validation remain separate.
"""

from __future__ import annotations

import csv
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import qiskit
from qiskit import QuantumCircuit, transpile
from qiskit.circuit.library import IntegerComparator, WeightedAdder

from cce_primary_phase_event_fixed_point_screen import phase_inputs, raw_affine


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RESULTS = ROOT / "10_TEA_LCA_Python" / "results" / "pycharm_publication_enhancement"
LEDGER = RESULTS / "PSA_QAE_CCE_PRIMARY_PHASE_LEDGER.json"
BRIDGE = RESULTS / "PSA_QAE_CCE_PRIMARY_PHASE_EVENT_BRIDGE.json"
FIXED_POINT = RESULTS / "PSA_QAE_CCE_PRIMARY_PHASE_EVENT_FIXED_POINT_SCREEN.json"
OUT_JSON = RESULTS / "PSA_QAE_CCE_PRIMARY_POLICY_STREAM_EVENT_ORACLE.json"
OUT_CSV = RESULTS / "PSA_QAE_CCE_PRIMARY_POLICY_STREAM_EVENT_ORACLE.csv"
OUT_MD = RESULTS / "PSA_QAE_CCE_PRIMARY_POLICY_STREAM_EVENT_ORACLE.md"
OUT_PNG = RESULTS / "PSA_QAE_CCE_PRIMARY_POLICY_STREAM_EVENT_ORACLE_FIGURE.png"
OUT_PDF = RESULTS / "PSA_QAE_CCE_PRIMARY_POLICY_STREAM_EVENT_ORACLE_FIGURE.pdf"

POLICIES = (0.420, 0.427, 0.430)
PURITY_THRESHOLD = 0.9998
RECOVERY_THRESHOLD = 0.789
AGGREGATE_BITS_CASES = tuple(range(14, 23))
COEFFICIENT_BITS_CASES = tuple(range(1, 17))

# source_co2 (index 11) is constant zero in the frozen design.  Recycle
# (index 20) is folded into each candidate-policy circuit.
SHARED_PARAMETER_INDICES = (10, 12, 13, 14, 15, 16, 17, 18, 19)
AGGREGATES = {
    "feed_h2": ((10,), False),
    "external_h2": ((15,), True),
    "external_impurity": ((16, 17, 18, 19), True),
}


def unique_variable_definitions(models: dict) -> list[dict]:
    rows: list[dict] = []
    for phase in ("A", "B"):
        model = models[f"{phase}_adsorption"]
        for index in range(10):
            rows.append(
                {
                    "kind": "state",
                    "phase": phase,
                    "source_index": index,
                    "name": f"{phase}_state_{index}",
                    "minimum": float(model["x_min"][index]),
                    "maximum": float(model["x_max"][index]),
                }
            )
    reference = models["A_adsorption"]
    other = models["B_adsorption"]
    for index in SHARED_PARAMETER_INDICES:
        if (
            abs(float(reference["x_min"][index]) - float(other["x_min"][index]))
            > 1.0e-14
            or abs(float(reference["x_max"][index]) - float(other["x_max"][index]))
            > 1.0e-14
        ):
            raise AssertionError(f"shared parameter range differs at index {index}")
        rows.append(
            {
                "kind": "parameter",
                "phase": "shared",
                "source_index": index,
                "name": f"parameter_{index}",
                "minimum": float(reference["x_min"][index]),
                "maximum": float(reference["x_max"][index]),
            }
        )
    return rows


def aggregate_affine(
    models: dict,
    variables: list[dict],
    output_indices: tuple[int, ...],
    policy: float,
    apply_external_fraction: bool,
) -> tuple[float, np.ndarray]:
    factor = 1.0 - policy if apply_external_fraction else 1.0
    intercepts: dict[str, np.ndarray] = {}
    slopes: dict[str, np.ndarray] = {}
    for phase in ("A", "B"):
        intercepts[phase], slopes[phase] = raw_affine(models[f"{phase}_adsorption"])

    constant = factor * sum(
        float(intercepts[phase][list(output_indices)].sum()) for phase in ("A", "B")
    )
    coefficients = []
    for variable in variables:
        index = int(variable["source_index"])
        if variable["kind"] == "state":
            phase = str(variable["phase"])
            coefficient = factor * float(slopes[phase][index, list(output_indices)].sum())
        else:
            coefficient = factor * sum(
                float(slopes[phase][index, list(output_indices)].sum())
                for phase in ("A", "B")
            )
        coefficients.append(coefficient)

    # Fold the inactive source_co2 parameter and fixed recycle policy into the
    # intercept.  The former is zero in this design but is kept explicit.
    for index, value in ((11, float(models["A_adsorption"]["x_min"][11])), (20, policy)):
        constant += factor * value * sum(
            float(slopes[phase][index, list(output_indices)].sum())
            for phase in ("A", "B")
        )
    return constant, np.asarray(coefficients, dtype=float)


def make_integer_aggregate_spec(
    models: dict,
    variables: list[dict],
    name: str,
    policy: float,
    input_bits: int,
    aggregate_bits: int,
) -> dict:
    output_indices, apply_external_fraction = AGGREGATES[name]
    intercept, coefficients = aggregate_affine(
        models, variables, output_indices, policy, apply_external_fraction
    )
    levels = 2**input_bits - 1
    minima = np.asarray([row["minimum"] for row in variables], dtype=float)
    spans = np.asarray(
        [float(row["maximum"]) - float(row["minimum"]) for row in variables],
        dtype=float,
    )
    constant_at_minimum = float(intercept + minima @ coefficients)
    unit_weights = coefficients * spans / levels
    bit_weights = np.asarray(
        [unit_weights[index] * (2**bit) for index in range(len(variables)) for bit in range(input_bits)],
        dtype=float,
    )
    negative_mask = bit_weights < 0.0
    transformed_constant = constant_at_minimum - float(np.abs(bit_weights[negative_mask]).sum())
    if transformed_constant <= 0.0:
        raise AssertionError(f"{policy} {name}: nonpositive hyperrectangle minimum")
    maximum = transformed_constant + float(np.abs(bit_weights).sum())
    aggregate_levels = 2**aggregate_bits - 1
    quantum = maximum / aggregate_levels
    for _ in range(32):
        integer_weights = np.rint(np.abs(bit_weights) / quantum).astype(int)
        constant_code = int(round(transformed_constant / quantum))
        maximum_code = constant_code + int(integer_weights.sum())
        if maximum_code <= aggregate_levels:
            break
        quantum *= maximum_code / aggregate_levels * 1.0000001
    else:
        raise AssertionError("aggregate scaling did not converge")
    return {
        "name": name,
        "policy": policy,
        "input_bits": input_bits,
        "aggregate_bits": aggregate_bits,
        "output_indices": list(output_indices),
        "external_fraction_applied": bool(apply_external_fraction),
        "transformed_constant_mol": transformed_constant,
        "hyperrectangle_maximum_mol": maximum,
        "quantum_mol": float(quantum),
        "constant_code": constant_code,
        "maximum_code": maximum_code,
        "negative_mask": negative_mask.tolist(),
        "integer_weights": integer_weights.tolist(),
        "nonzero_integer_weights": int(np.count_nonzero(integer_weights)),
        "negative_bit_controls": int(np.count_nonzero(negative_mask & (integer_weights > 0))),
    }


def encode_unique_inputs(
    values_a: np.ndarray,
    values_b: np.ndarray,
    variables: list[dict],
    input_bits: int,
) -> tuple[np.ndarray, np.ndarray]:
    levels = 2**input_bits - 1
    codes = []
    clipped = []
    for variable in variables:
        index = int(variable["source_index"])
        if variable["kind"] == "state":
            value = values_a[index] if variable["phase"] == "A" else values_b[index]
        else:
            value = values_a[index]
            if abs(value - values_b[index]) > 1.0e-12:
                raise AssertionError("shared parameter values differ between phase inputs")
        minimum = float(variable["minimum"])
        maximum = float(variable["maximum"])
        was_clipped = value < minimum or value > maximum
        normalized = np.clip((value - minimum) / (maximum - minimum), 0.0, 1.0)
        codes.append(int(round(normalized * levels)))
        clipped.append(was_clipped)
    return np.asarray(codes, dtype=int), np.asarray(clipped, dtype=bool)


def decode_aggregate(codes: np.ndarray, spec: dict) -> tuple[int, float]:
    bits = int(spec["input_bits"])
    bit_values = np.asarray(
        [(int(code) >> bit) & 1 for code in codes for bit in range(bits)], dtype=int
    )
    integer_weights = np.asarray(spec["integer_weights"], dtype=int)
    negative = np.asarray(spec["negative_mask"], dtype=bool)
    active_negative = negative & (integer_weights > 0)
    bit_values[active_negative] = 1 - bit_values[active_negative]
    code = int(spec["constant_code"] + bit_values @ integer_weights)
    return code, float(code * float(spec["quantum_mol"]))


def float_aggregates(models: dict, values_a: np.ndarray, values_b: np.ndarray, policy: float) -> dict:
    outputs = {}
    for phase, values in (("A", values_a), ("B", values_b)):
        intercept, slopes = raw_affine(models[f"{phase}_adsorption"])
        outputs[phase] = intercept + values @ slopes
    feed = float(outputs["A"][10] + outputs["B"][10])
    factor = 1.0 - policy
    product = float(factor * (outputs["A"][15] + outputs["B"][15]))
    impurity = float(factor * (outputs["A"][16:20].sum() + outputs["B"][16:20].sum()))
    return {"feed_h2": feed, "external_h2": product, "external_impurity": impurity}


def event_from_aggregates(values: dict) -> tuple[float, float, bool]:
    purity = float(values["external_h2"] / (values["external_h2"] + values["external_impurity"]))
    recovery = float(values["external_h2"] / values["feed_h2"])
    return purity, recovery, bool(purity >= PURITY_THRESHOLD and recovery >= RECOVERY_THRESHOLD)


def evaluate_precision(
    models: dict,
    variables: list[dict],
    inputs_a: np.ndarray,
    inputs_b: np.ndarray,
    input_bits: int,
    aggregate_bits: int,
) -> tuple[dict, dict[float, dict], list[dict]]:
    specs_by_policy = {}
    rows = []
    for policy in POLICIES:
        specs = {
            name: make_integer_aggregate_spec(
                models, variables, name, policy, input_bits, aggregate_bits
            )
            for name in AGGREGATES
        }
        specs_by_policy[policy] = specs
        for sample, (values_a, values_b) in enumerate(zip(inputs_a, inputs_b)):
            values_a = values_a.copy()
            values_b = values_b.copy()
            values_a[20] = policy
            values_b[20] = policy
            input_codes, clipped = encode_unique_inputs(values_a, values_b, variables, input_bits)
            floating = float_aggregates(models, values_a, values_b, policy)
            quantized = {}
            aggregate_codes = {}
            for name, spec in specs.items():
                code, value = decode_aggregate(input_codes, spec)
                aggregate_codes[name] = code
                quantized[name] = value
            float_purity, float_recovery, float_event = event_from_aggregates(floating)
            quantized_purity, quantized_recovery, quantized_event = event_from_aggregates(quantized)
            rows.append(
                {
                    "sample": sample,
                    "policy": policy,
                    "input_clip_count": int(clipped.sum()),
                    "float_purity": float_purity,
                    "float_recovery": float_recovery,
                    "float_event": float_event,
                    "quantized_purity": quantized_purity,
                    "quantized_recovery": quantized_recovery,
                    "quantized_event": quantized_event,
                    "purity_abs_error": abs(quantized_purity - float_purity),
                    "recovery_abs_error": abs(quantized_recovery - float_recovery),
                    "aggregate_codes": aggregate_codes,
                }
            )
    purity_error = np.asarray([row["purity_abs_error"] for row in rows], dtype=float)
    recovery_error = np.asarray([row["recovery_abs_error"] for row in rows], dtype=float)
    summary = {
        "row_type": "precision",
        "input_bits": input_bits,
        "aggregate_bits": aggregate_bits,
        "candidate_policy_state_points": len(rows),
        "p95_purity_abs_error": float(np.quantile(purity_error, 0.95)),
        "p95_recovery_abs_error": float(np.quantile(recovery_error, 0.95)),
        "max_purity_abs_error": float(purity_error.max()),
        "max_recovery_abs_error": float(recovery_error.max()),
        "event_matches_vs_float": int(sum(row["quantized_event"] == row["float_event"] for row in rows)),
        "input_clip_count": int(sum(row["input_clip_count"] for row in rows)),
    }
    return summary, specs_by_policy, rows


def coefficient_screen(rows: list[dict], specs: dict) -> tuple[list[dict], dict]:
    q_feed = float(specs["feed_h2"]["quantum_mol"])
    q_product = float(specs["external_h2"]["quantum_mol"])
    q_impurity = float(specs["external_impurity"]["quantum_mol"])
    purity_ratio = PURITY_THRESHOLD / (1.0 - PURITY_THRESHOLD) * q_impurity / q_product
    recovery_ratio = RECOVERY_THRESHOLD * q_feed / q_product
    exact_purity_margin = min(
        abs(row["aggregate_codes"]["external_h2"] - purity_ratio * row["aggregate_codes"]["external_impurity"])
        / max(row["aggregate_codes"]["external_impurity"], 1)
        for row in rows
    )
    exact_recovery_margin = min(
        abs(row["aggregate_codes"]["external_h2"] - recovery_ratio * row["aggregate_codes"]["feed_h2"])
        / max(row["aggregate_codes"]["feed_h2"], 1)
        for row in rows
    )
    margin_gate = 0.10 * min(exact_purity_margin, exact_recovery_margin)
    results = []
    for coefficient_bits in COEFFICIENT_BITS_CASES:
        scale = 2**coefficient_bits
        purity_weight = int(round(purity_ratio * scale))
        recovery_weight = int(round(recovery_ratio * scale))
        purity_matches = recovery_matches = event_matches = 0
        for row in rows:
            product = int(row["aggregate_codes"]["external_h2"])
            impurity = int(row["aggregate_codes"]["external_impurity"])
            feed = int(row["aggregate_codes"]["feed_h2"])
            exact_purity = row["quantized_purity"] >= PURITY_THRESHOLD
            exact_recovery = row["quantized_recovery"] >= RECOVERY_THRESHOLD
            integer_purity = scale * product >= purity_weight * impurity
            integer_recovery = scale * product >= recovery_weight * feed
            purity_matches += int(integer_purity == exact_purity)
            recovery_matches += int(integer_recovery == exact_recovery)
            event_matches += int((integer_purity and integer_recovery) == row["quantized_event"])
        coefficient_error = max(
            abs(purity_weight / scale - purity_ratio),
            abs(recovery_weight / scale - recovery_ratio),
        )
        results.append(
            {
                "row_type": "coefficient",
                "coefficient_bits": coefficient_bits,
                "coefficient_scale": scale,
                "purity_weight": purity_weight,
                "recovery_weight": recovery_weight,
                "purity_ratio": purity_ratio,
                "recovery_ratio": recovery_ratio,
                "max_coefficient_abs_error": coefficient_error,
                "ten_percent_minimum_normalized_margin": margin_gate,
                "coefficient_error_within_margin_gate": bool(coefficient_error <= margin_gate),
                "purity_matches": purity_matches,
                "recovery_matches": recovery_matches,
                "event_matches": event_matches,
            }
        )
    adequate = [
        row
        for row in results
        if row["coefficient_error_within_margin_gate"]
        and row["purity_matches"] == len(rows)
        and row["recovery_matches"] == len(rows)
        and row["event_matches"] == len(rows)
    ]
    if not adequate:
        raise AssertionError("no coefficient precision preserves candidate-policy flags")
    return results, min(adequate, key=lambda row: int(row["coefficient_bits"]))


def build_aggregate_xor(
    qc: QuantumCircuit,
    input_qubits: list[int],
    constant_one: int,
    target: list[int],
    workspace: list[int],
    spec: dict,
) -> dict:
    weights_all = np.asarray(spec["integer_weights"], dtype=int)
    negative_all = np.asarray(spec["negative_mask"], dtype=bool)
    active = np.flatnonzero(weights_all > 0)
    controls = [input_qubits[int(index)] for index in active] + [constant_one]
    weights = [int(weights_all[index]) for index in active] + [int(spec["constant_code"])]
    adder = WeightedAdder(len(controls), weights)
    if adder.num_sum_qubits != len(target):
        raise AssertionError(
            f"{spec['name']}: adder sum bits {adder.num_sum_qubits} != target {len(target)}"
        )
    negative_controls = [
        input_qubits[int(index)] for index in active if bool(negative_all[int(index)])
    ]
    if negative_controls:
        qc.x(negative_controls)
    qc.compose(adder, [*controls, *target, *workspace[: adder.num_ancillas]], inplace=True)
    if negative_controls:
        qc.x(negative_controls)
    return {
        "state_controls": len(controls),
        "adder_ancillas": int(adder.num_ancillas),
        "sum_bits": int(adder.num_sum_qubits),
        "nonzero_bit_weights": int(len(active)),
        "constant_code": int(spec["constant_code"]),
    }


def threshold_workspace_need(bits: int, negative_weight: int, scale: int) -> int:
    weights = [scale * (2**bit) for bit in range(bits)] + [
        negative_weight * (2**bit) for bit in range(bits)
    ]
    adder = WeightedAdder(2 * bits, weights)
    comparator = IntegerComparator(
        adder.num_sum_qubits, negative_weight * (2**bits - 1), geq=True
    )
    return adder.num_sum_qubits + adder.num_ancillas + 1 + comparator.num_ancillas


def build_threshold_xor(
    qc: QuantumCircuit,
    positive: list[int],
    negative: list[int],
    positive_weight: int,
    negative_weight: int,
    target: int,
    workspace: list[int],
) -> dict:
    bits = len(positive)
    weights = [positive_weight * (2**bit) for bit in range(bits)] + [
        negative_weight * (2**bit) for bit in range(bits)
    ]
    threshold = negative_weight * (2**bits - 1)
    adder = WeightedAdder(2 * bits, weights)
    comparator = IntegerComparator(adder.num_sum_qubits, threshold, geq=True)
    n_sum = adder.num_sum_qubits
    n_adder_anc = adder.num_ancillas
    n_comparator_anc = comparator.num_ancillas
    sum_qubits = workspace[:n_sum]
    adder_anc = workspace[n_sum : n_sum + n_adder_anc]
    comparator_target = workspace[n_sum + n_adder_anc]
    comparator_anc = workspace[
        n_sum + n_adder_anc + 1 : n_sum + n_adder_anc + 1 + n_comparator_anc
    ]
    qc.x(negative)
    qc.compose(adder, [*positive, *negative, *sum_qubits, *adder_anc], inplace=True)
    qc.compose(comparator, [*sum_qubits, comparator_target, *comparator_anc], inplace=True)
    qc.cx(comparator_target, target)
    qc.compose(comparator.inverse(), [*sum_qubits, comparator_target, *comparator_anc], inplace=True)
    qc.compose(adder.inverse(), [*positive, *negative, *sum_qubits, *adder_anc], inplace=True)
    qc.x(negative)
    return {
        "sum_bits": int(n_sum),
        "adder_ancillas": int(n_adder_anc),
        "comparator_ancillas": int(n_comparator_anc),
        "workspace_qubits": int(n_sum + n_adder_anc + 1 + n_comparator_anc),
        "threshold": int(threshold),
    }


def build_policy_circuits(
    input_bits: int,
    aggregate_bits: int,
    variable_count: int,
    specs: dict,
    coefficient: dict,
) -> tuple[QuantumCircuit, QuantumCircuit, QuantumCircuit, dict]:
    input_count = input_bits * variable_count
    input_qubits = list(range(input_count))
    cursor = input_count
    feed = list(range(cursor, cursor + aggregate_bits))
    cursor += aggregate_bits
    product = list(range(cursor, cursor + aggregate_bits))
    cursor += aggregate_bits
    impurity = list(range(cursor, cursor + aggregate_bits))
    cursor += aggregate_bits
    constant_one = cursor
    purity_flag = cursor + 1
    recovery_flag = cursor + 2
    cursor += 3

    aggregate_ancillas = []
    for spec in specs.values():
        weights = [int(value) for value in spec["integer_weights"] if int(value) > 0]
        weights.append(int(spec["constant_code"]))
        aggregate_ancillas.append(WeightedAdder(len(weights), weights).num_ancillas)
    scale = int(coefficient["coefficient_scale"])
    purity_weight = int(coefficient["purity_weight"])
    recovery_weight = int(coefficient["recovery_weight"])
    event_workspace = max(
        threshold_workspace_need(aggregate_bits, purity_weight, scale),
        threshold_workspace_need(aggregate_bits, recovery_weight, scale),
    )
    workspace_count = max(max(aggregate_ancillas), event_workspace)
    workspace = list(range(cursor, cursor + workspace_count))
    total_qubits = cursor + workspace_count

    aggregation = QuantumCircuit(total_qubits, name="policy_stream_aggregation")
    aggregation.x(constant_one)
    aggregate_resources = {}
    for name, target in (("feed_h2", feed), ("external_h2", product), ("external_impurity", impurity)):
        aggregate_resources[name] = build_aggregate_xor(
            aggregation, input_qubits, constant_one, target, workspace, specs[name]
        )

    compute = aggregation.copy(name="policy_stream_event_compute")
    purity_resources = build_threshold_xor(
        compute, product, impurity, scale, purity_weight, purity_flag, workspace
    )
    recovery_resources = build_threshold_xor(
        compute, product, feed, scale, recovery_weight, recovery_flag, workspace
    )
    oracle = QuantumCircuit(total_qubits, name="policy_stream_event_clean_oracle")
    oracle.compose(compute, inplace=True)
    oracle.cz(purity_flag, recovery_flag)
    oracle.compose(compute.inverse(), inplace=True)
    registers = {
        "encoded_input_qubits": input_count,
        "unique_input_variables": variable_count,
        "bits_per_input": input_bits,
        "aggregate_bits": aggregate_bits,
        "feed_h2_register": feed,
        "external_h2_register": product,
        "external_impurity_register": impurity,
        "constant_one": constant_one,
        "purity_flag": purity_flag,
        "recovery_flag": recovery_flag,
        "shared_workspace_qubits": workspace_count,
        "total_logical_qubits": total_qubits,
        "aggregate_resources": aggregate_resources,
        "purity_block": purity_resources,
        "recovery_block": recovery_resources,
    }
    return aggregation, compute, oracle, registers


def compiled_metrics(circuit: QuantumCircuit) -> dict:
    started = time.perf_counter()
    compiled = transpile(circuit, basis_gates=["u", "cx"], optimization_level=0)
    elapsed = time.perf_counter() - started
    operations = compiled.count_ops()
    return {
        "logical_qubits": int(compiled.num_qubits),
        "depth_all_to_all": int(compiled.depth()),
        "size": int(compiled.size()),
        "cx": int(operations.get("cx", 0)),
        "u": int(operations.get("u", 0)),
        "transpile_seconds": float(elapsed),
    }


def ledger_support_validation(
    models: dict,
    variables: list[dict],
    ledger: dict,
    inputs_a: np.ndarray,
    inputs_b: np.ndarray,
    input_bits: int,
    aggregate_bits: int,
) -> dict:
    rows = []
    for run, values_a, values_b in zip(ledger["runs"], inputs_a, inputs_b):
        policy = float(run["parameters"]["recycle_fraction"])
        specs = {
            name: make_integer_aggregate_spec(
                models, variables, name, policy, input_bits, aggregate_bits
            )
            for name in AGGREGATES
        }
        input_codes, clipped = encode_unique_inputs(values_a, values_b, variables, input_bits)
        quantized = {name: decode_aggregate(input_codes, spec)[1] for name, spec in specs.items()}
        q_purity, q_recovery, q_event = event_from_aggregates(quantized)
        actual = run["event_observables"]
        rows.append(
            {
                "sample": int(run["sample"]),
                "policy": policy,
                "quantized_event": q_event,
                "actual_event": bool(actual["joint_event"]),
                "purity_abs_error_vs_ledger": abs(q_purity - float(actual["h2_product"])),
                "recovery_abs_error_vs_ledger": abs(q_recovery - float(actual["h2_recovery_external_proxy"])),
                "input_clip_count": int(clipped.sum()),
            }
        )
    return {
        "rows": rows,
        "event_matches_vs_ledger": int(sum(row["quantized_event"] == row["actual_event"] for row in rows)),
        "p95_purity_abs_error_vs_ledger": float(np.quantile([row["purity_abs_error_vs_ledger"] for row in rows], 0.95)),
        "p95_recovery_abs_error_vs_ledger": float(np.quantile([row["recovery_abs_error_vs_ledger"] for row in rows], 0.95)),
        "input_clip_count": int(sum(row["input_clip_count"] for row in rows)),
    }


def main() -> None:
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    bridge = json.loads(BRIDGE.read_text(encoding="utf-8"))
    fixed = json.loads(FIXED_POINT.read_text(encoding="utf-8"))
    models = bridge["full_fit_models"]
    variables = unique_variable_definitions(models)
    inputs_a = phase_inputs(ledger, "A")
    inputs_b = phase_inputs(ledger, "B")
    input_bits = int(fixed["minimum_configuration_within_budgets_and_all_labels"]["bits_per_input"])
    purity_budget = float(fixed["purity_quantization_budget"])
    recovery_budget = float(fixed["recovery_quantization_budget"])

    precision_rows = []
    details_by_bits = {}
    for aggregate_bits in AGGREGATE_BITS_CASES:
        summary, specs, rows = evaluate_precision(
            models, variables, inputs_a, inputs_b, input_bits, aggregate_bits
        )
        summary["purity_budget"] = purity_budget
        summary["recovery_budget"] = recovery_budget
        summary["within_purity_budget"] = bool(summary["p95_purity_abs_error"] <= purity_budget)
        summary["within_recovery_budget"] = bool(summary["p95_recovery_abs_error"] <= recovery_budget)
        summary["within_both_budgets_and_labels"] = bool(
            summary["within_purity_budget"]
            and summary["within_recovery_budget"]
            and summary["event_matches_vs_float"] == len(rows)
            and summary["input_clip_count"] == 0
        )
        precision_rows.append(summary)
        details_by_bits[aggregate_bits] = (specs, rows)
    adequate = [row for row in precision_rows if row["within_both_budgets_and_labels"]]
    if not adequate:
        raise AssertionError("no aggregate precision satisfies both budgets and labels")
    selected = min(adequate, key=lambda row: int(row["aggregate_bits"]))
    aggregate_bits = int(selected["aggregate_bits"])
    specs_by_policy, validation_rows = details_by_bits[aggregate_bits]

    coefficient_results = {}
    resources = []
    for policy in POLICIES:
        policy_rows = [row for row in validation_rows if abs(float(row["policy"]) - policy) < 1.0e-12]
        coefficient_rows, coefficient = coefficient_screen(policy_rows, specs_by_policy[policy])
        aggregation, compute, oracle, registers = build_policy_circuits(
            input_bits,
            aggregate_bits,
            len(variables),
            specs_by_policy[policy],
            coefficient,
        )
        print(f"compiling policy {policy:.3f} aggregation", flush=True)
        aggregation_metrics = compiled_metrics(aggregation)
        print(f"compiling policy {policy:.3f} flag compute", flush=True)
        compute_metrics = compiled_metrics(compute)
        print(f"compiling policy {policy:.3f} clean oracle", flush=True)
        oracle_metrics = compiled_metrics(oracle)
        coefficient_results[f"{policy:.3f}"] = {
            "selected": coefficient,
            "rows": coefficient_rows,
        }
        resources.append(
            {
                "row_type": "resource",
                "policy": policy,
                "registers": registers,
                "aggregation": aggregation_metrics,
                "forward_flag_compute": compute_metrics,
                "clean_phase_oracle": oracle_metrics,
            }
        )

    support = ledger_support_validation(
        models, variables, ledger, inputs_a, inputs_b, input_bits, aggregate_bits
    )
    candidate_integer_matches = 0
    for row in validation_rows:
        coefficient = coefficient_results[f"{float(row['policy']):.3f}"]["selected"]
        scale = int(coefficient["coefficient_scale"])
        p = int(row["aggregate_codes"]["external_h2"])
        i = int(row["aggregate_codes"]["external_impurity"])
        f = int(row["aggregate_codes"]["feed_h2"])
        integer_event = bool(
            scale * p >= int(coefficient["purity_weight"]) * i
            and scale * p >= int(coefficient["recovery_weight"]) * f
        )
        row["integer_event"] = integer_event
        candidate_integer_matches += int(integer_event == row["float_event"])

    payload = {
        "schema": "psa-qae-cce-primary-policy-stream-event-oracle/v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "candidate_policy_collapsed_stream_aggregation_and_joint_event_compiled_physical_css_open",
        "sources": [LEDGER.name, BRIDGE.name, FIXED_POINT.name],
        "policy_definition": {
            "candidate_recycle_fractions": list(POLICIES),
            "implementation": "one classically fixed recycle constant per candidate-policy probability oracle",
        },
        "input_interface": {
            "unique_variables": len(variables),
            "bits_per_variable": input_bits,
            "encoded_input_qubits": len(variables) * input_bits,
            "variables": variables,
            "source_co2": "inactive constant zero",
            "recycle_fraction": "folded into policy-specific affine coefficients",
        },
        "precision_screen": {
            "budget_definition": "p95 collapsed stream-to-event quantization error <= 10% of nested-held-out phase-stream p95 error for purity and recovery, with all candidate-policy float labels retained",
            "selected": selected,
            "rows": precision_rows,
        },
        "aggregate_specs_by_policy": {
            f"{policy:.3f}": specs_by_policy[policy] for policy in POLICIES
        },
        "coefficient_screens_by_policy": coefficient_results,
        "verification": {
            "candidate_policy_state_points": len(validation_rows),
            "candidate_quantized_event_matches_vs_float": int(
                sum(row["quantized_event"] == row["float_event"] for row in validation_rows)
            ),
            "candidate_integer_event_matches_vs_float": candidate_integer_matches,
            "candidate_input_clip_count": int(sum(row["input_clip_count"] for row in validation_rows)),
            "ledger_support_rows": len(support["rows"]),
            "ledger_support_event_matches_vs_actual": support["event_matches_vs_ledger"],
            "ledger_support_input_clip_count": support["input_clip_count"],
            "ledger_support_p95_purity_abs_error_vs_actual": support["p95_purity_abs_error_vs_ledger"],
            "ledger_support_p95_recovery_abs_error_vs_actual": support["p95_recovery_abs_error_vs_ledger"],
            "complete_oracle_inverse": "exact Qiskit circuit inverse after CZ on retained purity/recovery flags",
        },
        "candidate_validation_rows": validation_rows,
        "ledger_support_validation": support,
        "primitive_gate_compile": {
            "qiskit_version": qiskit.__version__,
            "basis": ["u", "cx"],
            "coupling_assumption": "all_to_all_no_backend_routing",
            "optimization_level": 0,
            "policy_resources": resources,
        },
        "qpu_submission": False,
        "claim_boundary": {
            "supported": "policy-specific reversible construction of feed-H2, external-product-H2, and external-impurity registers directly from encoded adsorption phase-start states and shared parameters, followed by joint purity/recovery phase marking and exact uncomputation",
            "unsupported": "physical repeated-cycle CSS, coherent superposition over the three classically enumerated policies, state preparation, backend routing/noise, external H2 validation, or quantum advantage",
        },
    }
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    csv_rows = precision_rows[:]
    for policy_key, data in coefficient_results.items():
        for row in data["rows"]:
            csv_rows.append({**row, "policy": policy_key})
    for resource in resources:
        csv_rows.append(
            {
                "row_type": "resource",
                "policy": resource["policy"],
                "aggregate_bits": aggregate_bits,
                "logical_qubits": resource["clean_phase_oracle"]["logical_qubits"],
                "clean_oracle_cx": resource["clean_phase_oracle"]["cx"],
                "clean_oracle_depth": resource["clean_phase_oracle"]["depth_all_to_all"],
                "aggregation_cx": resource["aggregation"]["cx"],
                "forward_compute_cx": resource["forward_flag_compute"]["cx"],
            }
        )
    fieldnames = sorted({key for row in csv_rows for key in row})
    with OUT_CSV.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(csv_rows)

    max_qubits = max(row["clean_phase_oracle"]["logical_qubits"] for row in resources)
    max_cx = max(row["clean_phase_oracle"]["cx"] for row in resources)
    max_depth = max(row["clean_phase_oracle"]["depth_all_to_all"] for row in resources)
    lines = [
        "# Candidate-policy stream-to-event clean oracle",
        "",
        "For each frozen recycle candidate, the two calibrated adsorption maps are collapsed algebraically into feed-H2, external-product-H2, and external-impurity registers. Recycle scaling is folded into the policy-specific coefficients. The three registers feed the purity/recovery comparisons, a joint CZ phase mark, and exact uncomputation.",
        "",
        "| quantity | result |",
        "|---|---:|",
        f"| encoded input interface | {len(variables)} variables x {input_bits} bits = {len(variables) * input_bits} qubits |",
        f"| selected aggregate precision | {aggregate_bits} bits |",
        f"| candidate-policy quantized/integer labels | {payload['verification']['candidate_quantized_event_matches_vs_float']}/{len(validation_rows)} / {candidate_integer_matches}/{len(validation_rows)} |",
        f"| ledger-support labels versus actual | {support['event_matches_vs_ledger']}/{len(support['rows'])} |",
        f"| p95 purity/recovery quantization error | {selected['p95_purity_abs_error']:.3e} / {selected['p95_recovery_abs_error']:.3e} |",
        f"| maximum clean policy oracle | {max_qubits:,} qubits; {max_cx:,} CX; depth {max_depth:,} |",
        "",
        "| policy | coefficient bits | logical qubits | aggregation CX | forward compute CX | clean oracle CX | clean depth |",
        "|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for resource in resources:
        key = f"{float(resource['policy']):.3f}"
        lines.append(
            f"| {key} | {coefficient_results[key]['selected']['coefficient_bits']} | "
            f"{resource['clean_phase_oracle']['logical_qubits']:,} | {resource['aggregation']['cx']:,} | "
            f"{resource['forward_flag_compute']['cx']:,} | {resource['clean_phase_oracle']['cx']:,} | "
            f"{resource['clean_phase_oracle']['depth_all_to_all']:,} |"
        )
    lines += [
        "",
        "This closes the arithmetic path from encoded adsorption phase-start states and shared parameters through policy-specific stream aggregation, recycle scaling, joint event marking, and exact uncomputation. It does not supply those phase-start states by a stable physical/reversible repeated-cycle CSS calculation, and it excludes loading, routing/noise, external H2 validation, and any end-to-end advantage claim.",
        "",
        f"Artifacts: `{OUT_JSON.name}`, `{OUT_CSV.name}`, `{OUT_PNG.name}`, `{OUT_PDF.name}`.",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    fig, axes = plt.subplots(1, 2, figsize=(11.2, 4.4), constrained_layout=True)
    axes[0].plot(
        [row["aggregate_bits"] for row in precision_rows],
        [row["p95_purity_abs_error"] for row in precision_rows],
        "o-",
        label="purity",
    )
    axes[0].plot(
        [row["aggregate_bits"] for row in precision_rows],
        [row["p95_recovery_abs_error"] for row in precision_rows],
        "s-",
        label="recovery",
    )
    axes[0].axhline(purity_budget, color="#2563eb", linestyle=":", label="purity budget")
    axes[0].axhline(recovery_budget, color="#f59e0b", linestyle=":", label="recovery budget")
    axes[0].axvline(aggregate_bits, color="#333333", linestyle="--")
    axes[0].set(
        xlabel="bits per aggregate stream",
        ylabel="p95 absolute error",
        title="Collapsed stream precision",
        yscale="log",
    )
    axes[0].grid(alpha=0.25)
    axes[0].legend(fontsize=7)

    x = np.arange(len(resources))
    axes[1].bar(
        x - 0.18,
        [row["clean_phase_oracle"]["cx"] for row in resources],
        0.36,
        label="CX",
        color="#2563eb",
    )
    axes[1].bar(
        x + 0.18,
        [row["clean_phase_oracle"]["depth_all_to_all"] for row in resources],
        0.36,
        label="depth",
        color="#f59e0b",
    )
    axes[1].set(
        xticks=x,
        xticklabels=[f"r={row['policy']:.3f}" for row in resources],
        ylabel="count",
        title="Clean stream-to-event policy oracles",
    )
    axes[1].grid(axis="y", alpha=0.25)
    axes[1].legend()
    fig.savefig(OUT_PNG, dpi=250)
    fig.savefig(OUT_PDF)
    plt.close(fig)

    print(
        json.dumps(
            {
                "status": payload["status"],
                "selected_aggregate_bits": aggregate_bits,
                "candidate_integer_event_matches": candidate_integer_matches,
                "ledger_support_event_matches": support["event_matches_vs_ledger"],
                "max_clean_oracle": {
                    "logical_qubits": max_qubits,
                    "cx": max_cx,
                    "depth": max_depth,
                },
                "qpu_submission": False,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
