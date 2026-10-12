"""Chance/QAE bridge parameterized by the installed dense-Pd area.

The earlier chance oracle used a single-stage-equivalent membrane-area
coordinate.  This script replaces that coordinate with the installed area of
the dense-Pd polishing module in the stage-resolved physical train.  Saved
packet-wise stage-1 permeate traces are propagated through a vectorized
Sieverts-law Pd stage.  Eight uncertainty-cube corners define a trilinear
response and eight predeclared interior cases remain hold-outs.

The compact QAE oracle is an affine, deliberately conservative approximation
to the hold-out-error-buffered trilinear event.  Its overprediction buffer is
audited on the same fixed Sobol point sets used for the probability estimate.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import os
from pathlib import Path
import sys

import matplotlib.pyplot as plt
import numpy as np
try:
    import qiskit
    from qiskit import qasm3, transpile
    QISKIT_AVAILABLE = True
    QISKIT_IMPORT_ERROR = None
except ImportError as exc:
    qiskit = None
    qasm3 = None
    transpile = None
    QISKIT_AVAILABLE = False
    QISKIT_IMPORT_ERROR = repr(exc)
from scipy.stats import qmc

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from psa_qae.psa_literature_anchored_strict_margin_qae_bridge import (  # noqa: E402
    build_oracle,
    convergence_rows,
    encode_points,
    exact_encoded_probability,
    exact_weighted_uniform_pass_probability,
    integerize,
)
import psa_qae.psa_public_schedule_strict_uncertainty_ensemble as strict  # noqa: E402
import psa_qae.psa_stage_resolved_membrane_train as train  # noqa: E402


ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"
TRAIN_DIR = RESULTS / os.environ.get("PSA_QAE_TRAIN_DIR", "stage_resolved_membrane_train")
TRAIN_JSON = TRAIN_DIR / "PSA_STAGE_RESOLVED_MEMBRANE_TRAIN.json"
V19_JSON = RESULTS / "final_objective_evidence_v19" / "PSA_FINAL_OBJECTIVE_EVIDENCE_V19.json"
OUT = RESULTS / os.environ.get("PSA_QAE_OUTPUT_DIR", "physical_pd_area_qae_bridge")
OUT_JSON = OUT / "PSA_PHYSICAL_PD_AREA_QAE_BRIDGE.json"
OUT_MD = OUT / "PSA_PHYSICAL_PD_AREA_QAE_BRIDGE.md"
OUT_CASES = OUT / "Table_physical_pd_area_direct_validation.csv"
OUT_SCREEN = OUT / "Table_physical_pd_area_chance_screen.csv"
OUT_RESOURCES = OUT / "Table_physical_pd_area_oracle_resources.csv"
OUT_CONVERGENCE = OUT / "Table_physical_pd_area_mc_rqmc.csv"
OUT_FIGURE = OUT / "Fig_physical_pd_area_qae_bridge.png"
OUT_FIGURE_PDF = OUT / "Fig_physical_pd_area_qae_bridge.pdf"
OUT_FIGURE_SVG = OUT / "Fig_physical_pd_area_qae_bridge.svg"
OUT_QASM = OUT / "PSA_PHYSICAL_PD_AREA_EVENT_ORACLE_10BIT.qasm"
OUT_UNCOMPILED = OUT / "PSA_PHYSICAL_PD_AREA_EVENT_ORACLE_INTEGER_SPEC.json"
OUT_MANIFEST = OUT / "PSA_PHYSICAL_PD_AREA_QAE_BRIDGE_MANIFEST.json"
FALLBACK_QAE_DIR = RESULTS / "physical_pd_area_qae_bridge"
FALLBACK_QAE_JSON = FALLBACK_QAE_DIR / "PSA_PHYSICAL_PD_AREA_QAE_BRIDGE.json"
FALLBACK_QAE_RESOURCES = FALLBACK_QAE_DIR / "Table_physical_pd_area_oracle_resources.csv"
FALLBACK_QAE_QASM = FALLBACK_QAE_DIR / "PSA_PHYSICAL_PD_AREA_EVENT_ORACLE_10BIT.qasm"

INPUT_BITS_CASES = (2, 3, 4, 6, 8, 10)
PROBABILITY_POWER = 17
PROBABILITY_SCRAMBLES = 8
PROBABILITY_SEED = 202610120
TRANSPILE_SEED = 20261012
CHANCE_TARGET = 0.95
AREA_ROUNDING_M2 = 0.001
AREA_BISECTION_TOLERANCE_M2 = 1.0e-6
PD_AREA_STEPS = 144


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise ValueError(f"no rows for {path}")
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


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


def affine_matrix(x: np.ndarray) -> np.ndarray:
    return np.column_stack([np.ones(len(x)), x])


def dense_pd_vectorized(feed_packets: np.ndarray, duration_s: float, area_m2: float) -> np.ndarray:
    """Return pure-H2 product moles for every packet using the train Pd law."""
    feed = np.maximum(np.asarray(feed_packets, dtype=float), 0.0)
    h2 = feed[:, strict.INDEX["H2"]].copy()
    non_h2 = feed.sum(axis=1) - h2
    product = np.zeros_like(h2)
    d_area = float(area_m2) / PD_AREA_STEPS
    for _ in range(PD_AREA_STEPS):
        total = h2 + non_h2
        active = (total > 1.0e-18) & (h2 > 1.0e-18)
        x_h2 = np.divide(h2, total, out=np.zeros_like(h2), where=active)
        driving = np.sqrt(train.PD_FEED_PRESSURE_PA * x_h2) - math.sqrt(
            train.PD_PERMEATE_PRESSURE_PA
        )
        transfer = train.PD_H2_PERMEANCE_MOL_M2_S_PA_HALF * np.maximum(
            driving, 0.0
        ) * d_area * float(duration_s)
        transfer = np.minimum(transfer, 0.999999 * h2)
        transfer[~active] = 0.0
        h2 -= transfer
        product += transfer
    return product


def receiver_requirement_from_packets(product_h2: np.ndarray, cycle_time_s: float) -> dict:
    packets_per_cycle = 4 * strict.ADSORPTION_SUBSTEPS
    packet_duration_s = float(cycle_time_s) / packets_per_cycle
    slots_per_packet = int(round(packet_duration_s / strict.RECEIVER_DT_S))
    if slots_per_packet < 1:
        raise AssertionError("receiver grid is coarser than a membrane packet")
    per_slot = np.repeat(np.asarray(product_h2, dtype=float) / slots_per_packet, slots_per_packet)
    constant_per_slot = float(per_slot.mean())
    imbalance = np.concatenate(([0.0], np.cumsum(per_slot - constant_per_slot)))
    swing = float(imbalance.max() - imbalance.min())
    capacity = swing / max(1.0 - strict.RECEIVER_HEEL_FRACTION, 1.0e-30)
    return {
        "receiver_inventory_swing_mol": swing,
        "minimum_receiver_capacity_mol": capacity,
    }


def load_cases() -> list[dict]:
    records = []
    for kind, prefix in (("uncertainty_corner", "corner"), ("predeclared_interior_holdout", "holdout")):
        for index in range(8):
            case_id = f"{prefix}_{index:02d}"
            state_path = TRAIN_DIR / "states" / f"{case_id}.json"
            trace_path = TRAIN_DIR / "states" / f"{case_id}_traces.npz"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            with np.load(trace_path, allow_pickle=False) as archive:
                stage1 = np.asarray(archive["stage1_product_mol"], dtype=float)
            records.append(
                {
                    "validation_kind": kind,
                    "case_id": case_id,
                    "state_path": state_path,
                    "trace_path": trace_path,
                    "coordinates_saved": (
                        state.get("feed_u"),
                        state.get("equilibrium_pc_u"),
                        state.get("ldf_u"),
                    ),
                    "feed_h2_multiplier": float(state["feed_h2_multiplier"]),
                    "capacity_coordinate_c": float(state["capacity_coordinate_c"]),
                    "ldf_factor": float(state["ldf_factor"]),
                    "stage1_product_mol": stage1,
                    "packet_duration_s": float(state["cycle_time_s"])
                    / (4 * strict.ADSORPTION_SUBSTEPS),
                    "cycle_time_s": float(state["cycle_time_s"]),
                    "elapsed_s": float(state["n_cycles"]) * float(state["cycle_time_s"]),
                    "raw_h2_mol": float(state["raw_h2_rate_mol_s"])
                    * float(state["n_cycles"])
                    * float(state["cycle_time_s"]),
                    "surge_required_capacity_mol": float(state["surge_required_capacity_mol"]),
                    "source_reserve_gate": bool(state["source_reserve_gate"]),
                    "source_css_gate": bool(state["source_css_gate"]),
                    "source_numerical_gate": bool(state["source_numerical_gate"]),
                }
            )
    corners = [row for row in records if row["validation_kind"] == "uncertainty_corner"]
    feed_min = min(row["feed_h2_multiplier"] for row in corners)
    feed_max = max(row["feed_h2_multiplier"] for row in corners)
    capacity_min = min(row["capacity_coordinate_c"] for row in corners)
    capacity_max = max(row["capacity_coordinate_c"] for row in corners)
    ldf_min = min(row["ldf_factor"] for row in corners)
    ldf_max = max(row["ldf_factor"] for row in corners)
    cases = []
    for row in records:
        saved = row.pop("coordinates_saved")
        derived = np.asarray(
            [
                (row["feed_h2_multiplier"] - feed_min) / (feed_max - feed_min),
                (capacity_max - row["capacity_coordinate_c"])
                / (capacity_max - capacity_min),
                (row["ldf_factor"] - ldf_min) / (ldf_max - ldf_min),
            ],
            dtype=float,
        )
        if all(value is not None for value in saved):
            stored = np.asarray(saved, dtype=float)
            if float(np.max(np.abs(stored - derived))) > 1.0e-10:
                raise AssertionError(f"stored and derived uncertainty coordinates disagree for {row['case_id']}")
        row["coordinates"] = derived
        cases.append(row)
    return cases


def direct_rows_for_area(
    cases: list[dict],
    *,
    pd_area_m2: float,
    surge_capacity_mol: float,
    receiver_capacity_mol: float,
    recovery_floor: float,
    shipment_floor_mol_s: float,
) -> list[dict]:
    rows = []
    for case in cases:
        product_h2 = dense_pd_vectorized(
            case["stage1_product_mol"], case["packet_duration_s"], pd_area_m2
        )
        total_product_h2 = float(product_h2.sum())
        recovery = total_product_h2 / max(float(case["raw_h2_mol"]), 1.0e-30)
        shipment = total_product_h2 / max(float(case["elapsed_s"]), 1.0e-30)
        receiver = receiver_requirement_from_packets(product_h2, case["cycle_time_s"])
        recovery_margin = recovery / recovery_floor - 1.0
        shipment_margin = shipment / shipment_floor_mol_s - 1.0
        surge_margin = surge_capacity_mol / case["surge_required_capacity_mol"] - 1.0
        receiver_margin = (
            receiver_capacity_mol
            / max(float(receiver["minimum_receiver_capacity_mol"]), 1.0e-30)
            - 1.0
        )
        inherited_margin = 1.0 if (
            case["source_reserve_gate"]
            and case["source_css_gate"]
            and case["source_numerical_gate"]
        ) else -1.0
        joint_margin = min(
            recovery_margin,
            shipment_margin,
            surge_margin,
            receiver_margin,
            inherited_margin,
        )
        chance_margin = min(recovery_margin, shipment_margin)
        rows.append(
            {
                "validation_kind": case["validation_kind"],
                "case_id": case["case_id"],
                "feed_u": float(case["coordinates"][0]),
                "equilibrium_pc_u": float(case["coordinates"][1]),
                "ldf_u": float(case["coordinates"][2]),
                "pd_area_m2": float(pd_area_m2),
                "overall_h2_recovery": recovery,
                "qualified_h2_rate_mol_s": shipment,
                "surge_required_capacity_mol": case["surge_required_capacity_mol"],
                "receiver_required_capacity_mol": receiver["minimum_receiver_capacity_mol"],
                "recovery_relative_margin": recovery_margin,
                "shipment_relative_margin": shipment_margin,
                "surge_relative_margin": surge_margin,
                "receiver_relative_margin": receiver_margin,
                "chance_relative_margin": chance_margin,
                "joint_relative_margin": joint_margin,
                "direct_physical_event": bool(joint_margin >= 0.0),
            }
        )
    return rows


def probability_samples() -> list[np.ndarray]:
    return [
        qmc.Sobol(d=3, scramble=True, seed=PROBABILITY_SEED + scramble).random_base2(
            PROBABILITY_POWER
        )
        for scramble in range(PROBABILITY_SCRAMBLES)
    ]


def surface_for_area(rows: list[dict], samples: list[np.ndarray]) -> dict:
    corners = [row for row in rows if row["validation_kind"] == "uncertainty_corner"]
    holdouts = [
        row for row in rows if row["validation_kind"] == "predeclared_interior_holdout"
    ]
    x_corner = np.asarray(
        [[row["feed_u"], row["equilibrium_pc_u"], row["ldf_u"]] for row in corners]
    )
    y_corner = np.asarray([row["chance_relative_margin"] for row in corners])
    x_holdout = np.asarray(
        [[row["feed_u"], row["equilibrium_pc_u"], row["ldf_u"]] for row in holdouts]
    )
    y_holdout = np.asarray([row["chance_relative_margin"] for row in holdouts])
    tri_coeff = np.linalg.solve(trilinear_matrix(x_corner), y_corner)
    tri_corner = trilinear_matrix(x_corner) @ tri_coeff
    tri_holdout = trilinear_matrix(x_holdout) @ tri_coeff
    holdout_error = float(np.max(np.abs(tri_holdout - y_holdout)))

    affine_coeff, *_ = np.linalg.lstsq(affine_matrix(x_corner), y_corner, rcond=None)
    overprediction = 0.0
    tri_probabilities = []
    sample_pairs = []
    for points in samples:
        tri_values = trilinear_matrix(points) @ tri_coeff
        affine_values = affine_matrix(points) @ affine_coeff
        overprediction = max(overprediction, float(np.max(affine_values - tri_values)))
        sample_pairs.append((tri_values, affine_values))
        tri_probabilities.append(float(np.mean(tri_values - holdout_error >= 0.0)))
    oracle_buffer = holdout_error + max(overprediction, 0.0) + 1.0e-12
    conservative_intercept = float(affine_coeff[0] - oracle_buffer)
    conservative_slopes = np.asarray(affine_coeff[1:], dtype=float)
    affine_probability = exact_weighted_uniform_pass_probability(
        conservative_intercept, conservative_slopes
    )
    direct_x = np.asarray(
        [[row["feed_u"], row["equilibrium_pc_u"], row["ldf_u"]] for row in rows]
    )
    tri_direct = trilinear_matrix(direct_x) @ tri_coeff - holdout_error
    affine_direct = conservative_intercept + direct_x @ conservative_slopes
    tri_label = tri_direct >= 0.0
    affine_label = affine_direct >= 0.0
    return {
        "trilinear_coefficients": tri_coeff,
        "affine_coefficients": affine_coeff,
        "holdout_maximum_absolute_error_margin": holdout_error,
        "affine_maximum_dense_overprediction_margin": max(overprediction, 0.0),
        "oracle_total_buffer_margin": oracle_buffer,
        "conservative_affine_intercept": conservative_intercept,
        "conservative_affine_slopes": conservative_slopes,
        "trilinear_probability_mean": float(np.mean(tri_probabilities)),
        "trilinear_probability_minimum_scramble": float(np.min(tri_probabilities)),
        "trilinear_probability_maximum_scramble": float(np.max(tri_probabilities)),
        "conservative_affine_probability": float(affine_probability),
        "corner_interpolation_max_abs_error": float(np.max(np.abs(tri_corner - y_corner))),
        "direct_trilinear_buffered_labels": tri_label,
        "direct_affine_conservative_labels": affine_label,
        "direct_affine_false_positive": int(np.sum(affine_label & ~tri_label)),
        "direct_affine_false_negative": int(np.sum(~affine_label & tri_label)),
        "direct_affine_accuracy": float(np.mean(affine_label == tri_label)),
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    train_summary = json.loads(TRAIN_JSON.read_text(encoding="utf-8"))
    v19 = json.loads(V19_JSON.read_text(encoding="utf-8"))
    cases = load_cases()
    samples = probability_samples()
    installed = train_summary["selected_design"]
    surge_capacity = float(installed["surge_buffer_capacity_mol"])
    receiver_capacity = float(installed["receiver_capacity_mol"])
    robust_pd_area = float(installed["pd_area_m2"])
    decision = v19["primary_engineering_decision"]
    recovery_floor = float(decision["minimum_h2_recovery"])
    shipment_floor = float(decision["minimum_qualified_h2_rate_mol_s"])
    cache: dict[float, tuple[list[dict], dict]] = {}

    def evaluate(area: float) -> tuple[list[dict], dict]:
        key = round(float(area), 12)
        if key not in cache:
            rows = direct_rows_for_area(
                cases,
                pd_area_m2=key,
                surge_capacity_mol=surge_capacity,
                receiver_capacity_mol=receiver_capacity,
                recovery_floor=recovery_floor,
                shipment_floor_mol_s=shipment_floor,
            )
            cache[key] = (rows, surface_for_area(rows, samples))
        return cache[key]

    def passes(surface: dict) -> bool:
        return bool(
            surface["trilinear_probability_minimum_scramble"] >= CHANCE_TARGET
            and surface["conservative_affine_probability"] >= CHANCE_TARGET
        )

    low = 0.05
    high = robust_pd_area
    _rows_high, surface_high = evaluate(high)
    if not passes(surface_high):
        raise RuntimeError(
            "the literature-bounded robust Pd design does not pass the physical chance event: "
            + json.dumps(
                {
                    "trilinear_probability_minimum_scramble": surface_high[
                        "trilinear_probability_minimum_scramble"
                    ],
                    "conservative_affine_probability": surface_high[
                        "conservative_affine_probability"
                    ],
                    "holdout_error": surface_high[
                        "holdout_maximum_absolute_error_margin"
                    ],
                    "dense_overprediction": surface_high[
                        "affine_maximum_dense_overprediction_margin"
                    ],
                }
            )
        )
    _rows_low, surface_low = evaluate(low)
    if passes(surface_low):
        raise RuntimeError("lower Pd-area bound is already trivial; decrease the bound")
    while high - low > AREA_BISECTION_TOLERANCE_M2:
        middle = 0.5 * (low + high)
        _rows_middle, surface_middle = evaluate(middle)
        if passes(surface_middle):
            high = middle
        else:
            low = middle
    selected_area = math.ceil(high / AREA_ROUNDING_M2) * AREA_ROUNDING_M2
    selected_rows, selected_surface = evaluate(selected_area)
    while not passes(selected_surface):
        selected_area += AREA_ROUNDING_M2
        selected_rows, selected_surface = evaluate(selected_area)
    robust_rows, robust_surface = evaluate(robust_pd_area)
    deterministic_gate_pass = all(
        row["surge_relative_margin"] >= -1.0e-12
        and row["receiver_relative_margin"] >= -1.0e-12
        for row in selected_rows
    )
    if not deterministic_gate_pass:
        raise AssertionError("a fixed surge or receiver capacity gate failed at the selected physical chance design")

    robust_recovery_differences = []
    robust_rate_differences = []
    for row in robust_rows:
        saved = json.loads(
            (TRAIN_DIR / "states" / f"{row['case_id']}.json").read_text(encoding="utf-8")
        )
        robust_recovery_differences.append(
            abs(float(row["overall_h2_recovery"]) - float(saved["overall_h2_recovery"]))
        )
        robust_rate_differences.append(
            abs(
                float(row["qualified_h2_rate_mol_s"])
                - float(saved["qualified_h2_rate_mol_s"])
            )
        )
    maximum_robust_recovery_reproduction_error = max(robust_recovery_differences)
    maximum_robust_rate_reproduction_error = max(robust_rate_differences)
    if maximum_robust_recovery_reproduction_error > 1.0e-8:
        raise AssertionError(
            "vectorized Pd calculation does not reproduce the saved robust recovery: "
            f"{maximum_robust_recovery_reproduction_error:.12g}"
        )
    if maximum_robust_rate_reproduction_error > 1.0e-10:
        raise AssertionError(
            "vectorized Pd calculation does not reproduce the saved robust shipment rate: "
            f"{maximum_robust_rate_reproduction_error:.12g}"
        )

    screen_areas = sorted(
        set(
            np.linspace(max(0.05, selected_area - 0.08), robust_pd_area, 31).tolist()
            + [selected_area, robust_pd_area]
        )
    )
    screen_rows = []
    for area in screen_areas:
        direct, surface = evaluate(float(area))
        screen_rows.append(
            {
                "pd_area_m2": float(area),
                "direct_pass_count": int(sum(row["direct_physical_event"] for row in direct)),
                "direct_case_count": len(direct),
                "minimum_direct_joint_relative_margin": min(
                    float(row["joint_relative_margin"]) for row in direct
                ),
                "holdout_maximum_absolute_error_margin": surface[
                    "holdout_maximum_absolute_error_margin"
                ],
                "trilinear_probability_mean": surface["trilinear_probability_mean"],
                "trilinear_probability_minimum_scramble": surface[
                    "trilinear_probability_minimum_scramble"
                ],
                "conservative_affine_probability": surface[
                    "conservative_affine_probability"
                ],
                "chance_target_pass": passes(surface),
            }
        )

    convergence = convergence_rows(
        selected_surface["conservative_affine_probability"],
        selected_surface["conservative_affine_intercept"],
        selected_surface["conservative_affine_slopes"],
    )
    direct_x = np.asarray(
        [[row["feed_u"], row["equilibrium_pc_u"], row["ldf_u"]] for row in selected_rows]
    )
    tri_labels = selected_surface["direct_trilinear_buffered_labels"]
    resource_rows = []
    integer_specs = []
    qasm_circuit = None
    qasm_reused = False
    all_fallback_specs_identical = True
    fallback_payload = None
    fallback_resources = None
    if not QISKIT_AVAILABLE:
        fallback_payload = json.loads(FALLBACK_QAE_JSON.read_text(encoding="utf-8"))
        with FALLBACK_QAE_RESOURCES.open(newline="", encoding="utf-8-sig") as handle:
            fallback_resources = {
                int(row["input_bits_per_variable"]): row for row in csv.DictReader(handle)
            }
        fallback_specs = {
            int(spec["input_bits_per_variable"]): spec
            for spec in fallback_payload["conservative_affine_oracle"]["integer_specs"]
        }
    for bits in INPUT_BITS_CASES:
        spec = integerize(
            selected_surface["conservative_affine_intercept"],
            selected_surface["conservative_affine_slopes"],
            bits,
        )
        encoded_label = encode_points(direct_x, spec)
        discrete_probability = exact_encoded_probability(spec)
        if QISKIT_AVAILABLE:
            circuit, registers = build_oracle(spec)
            circuit.name = f"S_physical_pd_area_{selected_area:.3f}m2_b{bits}"
            isa = transpile(
                circuit,
                basis_gates=["u", "cx"],
                optimization_level=1,
                seed_transpiler=TRANSPILE_SEED,
            )
            transpiled = {
                "transpiled_depth": int(isa.depth()),
                "transpiled_size": int(isa.size()),
                "transpiled_cx": int(isa.count_ops().get("cx", 0)),
            }
        else:
            prior_spec = fallback_specs[bits]
            topology_fields = (
                "input_bits_per_variable",
                "levels_per_variable",
                "state_qubits",
                "negative_bit_mask",
                "integer_weights",
                "integer_weight_sum",
                "integer_threshold",
            )
            spec_identical = not any(
                spec[name] != prior_spec[name] for name in topology_fields
            )
            all_fallback_specs_identical &= spec_identical
            prior = fallback_resources[bits]
            registers = {
                "state_qubits": int(prior["state_qubits"]),
                "sum_qubits": int(prior["sum_qubits"]),
                "adder_ancillas": int(prior["adder_ancillas"]),
                "phase_flag_qubits": int(prior["phase_flag_qubits"]),
                "comparator_ancillas": int(prior["comparator_ancillas"]),
                "total_logical_qubits": int(prior["total_logical_qubits"]),
            }
            transpiled = (
                {
                    "transpiled_depth": int(prior["transpiled_depth"]),
                    "transpiled_size": int(prior["transpiled_size"]),
                    "transpiled_cx": int(prior["transpiled_cx"]),
                }
                if spec_identical
                else {
                    "transpiled_depth": None,
                    "transpiled_size": None,
                    "transpiled_cx": None,
                }
            )
        resource_rows.append(
            {
                "input_bits_per_variable": bits,
                **registers,
                "direct_states_checked": len(selected_rows),
                "direct_label_disagreement_vs_buffered_trilinear": int(
                    np.sum(encoded_label != tri_labels)
                ),
                "direct_false_positive_vs_buffered_trilinear": int(
                    np.sum(encoded_label & ~tri_labels)
                ),
                "direct_false_negative_vs_buffered_trilinear": int(
                    np.sum(~encoded_label & tri_labels)
                ),
                "exact_continuous_conservative_affine_probability": selected_surface[
                    "conservative_affine_probability"
                ],
                "exact_discrete_oracle_probability": discrete_probability,
                "absolute_probability_discretization_error": abs(
                    discrete_probability
                    - selected_surface["conservative_affine_probability"]
                ),
                **transpiled,
            }
        )
        integer_specs.append(spec)
        if bits == 10 and QISKIT_AVAILABLE:
            qasm_circuit = circuit
    if QISKIT_AVAILABLE and qasm_circuit is None:
        raise AssertionError("10-bit physical Pd-area oracle was not built")

    write_csv(OUT_CASES, selected_rows)
    write_csv(OUT_SCREEN, screen_rows)
    write_csv(OUT_RESOURCES, resource_rows)
    write_csv(OUT_CONVERGENCE, convergence)
    if QISKIT_AVAILABLE:
        OUT_QASM.write_text(qasm3.dumps(qasm_circuit), encoding="utf-8")
        if OUT_UNCOMPILED.exists():
            OUT_UNCOMPILED.unlink()
    elif all_fallback_specs_identical:
        OUT_QASM.write_bytes(FALLBACK_QAE_QASM.read_bytes())
        qasm_reused = True
        if OUT_UNCOMPILED.exists():
            OUT_UNCOMPILED.unlink()
    else:
        if OUT_QASM.exists():
            OUT_QASM.unlink()
        OUT_UNCOMPILED.write_text(
            json.dumps(
                {
                    "status": "integer_oracle_spec_updated_qasm_compilation_blocked_by_host_policy",
                    "qiskit_import_error": QISKIT_IMPORT_ERROR,
                    "integer_specs": integer_specs,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    ten_bit = resource_rows[-1]
    payload = {
        "schema": "psa-physical-pd-area-qae-bridge/v1",
        "status": (
            "physical_pd_area_chance_event_compiled"
            if QISKIT_AVAILABLE or qasm_reused
            else "physical_pd_area_chance_event_numerically_verified_qasm_recompile_pending"
        ),
        "qiskit_version": (
            qiskit.__version__
            if QISKIT_AVAILABLE
            else fallback_payload["qiskit_version"]
        ),
        "circuit_compilation_provenance": {
            "qiskit_available_in_current_run": QISKIT_AVAILABLE,
            "current_import_error": QISKIT_IMPORT_ERROR,
            "qasm_reused_from_previous_compilation": qasm_reused,
            "qasm_compilation_complete": bool(QISKIT_AVAILABLE or qasm_reused),
            "reuse_basis": (
                "all integer weights, sign masks, thresholds, and register sizes are identical at 2, 3, 4, 6, 8, and 10 bits"
                if qasm_reused
                else (
                    "compiled in the current run"
                    if QISKIT_AVAILABLE
                    else "new integer specification differs; QASM and transpiled gate counts intentionally withheld"
                )
            ),
            "source_qasm_sha256": sha256(FALLBACK_QAE_QASM) if qasm_reused else None,
        },
        "event": {
            "physical_design_variable": "installed dense-Pd polishing area",
            "selected_chance_pd_area_m2": selected_area,
            "robust_literature_bounded_pd_area_m2": robust_pd_area,
            "fixed_polymer_concentrator_area_m2": installed["concentrator_area_m2"],
            "fixed_surge_capacity_mol": surge_capacity,
            "fixed_product_receiver_capacity_mol": receiver_capacity,
            "joint_event": (
                "regeneration reserve and numerical gates pass; installed surge capacity is adequate; "
                "H2 recovery and qualified shipment meet the frozen floors; product receiver capacity is adequate"
            ),
            "probabilistic_sub_event": (
                "H2 recovery and qualified shipment meet their frozen floors; the regeneration, surge, "
                "receiver, and numerical gates are separately fixed and directly audited"
            ),
            "uncertainty_coordinates": ["feed_u", "equilibrium_pc_u", "ldf_u"],
            "measure": "independent uniform engineering measure over the declared uncertainty cube",
            "chance_target": CHANCE_TARGET,
            "dense_pd_assumption": "ideal defect-free H2-only permeation",
        },
        "frozen_thresholds": {
            "minimum_h2_recovery": recovery_floor,
            "minimum_qualified_h2_rate_mol_s": shipment_floor,
        },
        "validation": {
            "corner_count": 8,
            "predeclared_holdout_count": 8,
            "selected_area_direct_pass_count": int(
                sum(row["direct_physical_event"] for row in selected_rows)
            ),
            "selected_area_direct_case_count": len(selected_rows),
            "selected_area_fixed_surge_receiver_gate_pass": deterministic_gate_pass,
            "selected_area_minimum_direct_recovery": min(
                row["overall_h2_recovery"] for row in selected_rows
            ),
            "selected_area_minimum_direct_shipment_mol_s": min(
                row["qualified_h2_rate_mol_s"] for row in selected_rows
            ),
            "corner_interpolation_max_abs_error": selected_surface[
                "corner_interpolation_max_abs_error"
            ],
            "holdout_maximum_absolute_error_margin": selected_surface[
                "holdout_maximum_absolute_error_margin"
            ],
            "trilinear_probability_mean": selected_surface[
                "trilinear_probability_mean"
            ],
            "trilinear_probability_minimum_scramble": selected_surface[
                "trilinear_probability_minimum_scramble"
            ],
            "trilinear_probability_maximum_scramble": selected_surface[
                "trilinear_probability_maximum_scramble"
            ],
            "affine_maximum_dense_overprediction_margin": selected_surface[
                "affine_maximum_dense_overprediction_margin"
            ],
            "oracle_total_buffer_margin": selected_surface[
                "oracle_total_buffer_margin"
            ],
            "conservative_affine_probability": selected_surface[
                "conservative_affine_probability"
            ],
            "direct_affine_false_positive": selected_surface[
                "direct_affine_false_positive"
            ],
            "direct_affine_false_negative": selected_surface[
                "direct_affine_false_negative"
            ],
            "direct_affine_accuracy": selected_surface["direct_affine_accuracy"],
            "robust_area_trilinear_probability_minimum_scramble": robust_surface[
                "trilinear_probability_minimum_scramble"
            ],
            "robust_area_conservative_affine_probability": robust_surface[
                "conservative_affine_probability"
            ],
            "maximum_robust_recovery_reproduction_error": maximum_robust_recovery_reproduction_error,
            "maximum_robust_shipment_rate_reproduction_error_mol_s": maximum_robust_rate_reproduction_error,
            "sobol_points_per_scramble": 2**PROBABILITY_POWER,
            "sobol_scrambles": PROBABILITY_SCRAMBLES,
        },
        "conservative_affine_oracle": {
            "intercept": selected_surface["conservative_affine_intercept"],
            "slopes": {
                name: float(value)
                for name, value in zip(
                    ("feed_u", "equilibrium_pc_u", "ldf_u"),
                    selected_surface["conservative_affine_slopes"],
                )
            },
            "ten_bit_resources": ten_bit,
            "integer_specs": integer_specs,
        },
        "sources": {
            "stage_train": str(TRAIN_JSON.relative_to(ROOT)),
            "v19_evidence": str(V19_JSON.relative_to(ROOT)),
            "direct_stage1_states_and_traces": 16,
        },
        "claim_boundary": {
            "allowed": (
                "The compact QAE event now uses the installed dense-Pd area of the stage-resolved train, "
                "and its affine oracle is conservative relative to the hold-out-buffered trilinear response on the audited domain."
            ),
            "not_allowed": (
                "The Pd module is experimentally certified for simultaneous CO/CO2/N2/CH4 leakage, "
                "or the independent-uniform uncertainty law is plant-calibrated."
            ),
        },
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Physical Pd-area chance/QAE bridge",
        "",
        "The QAE decision variable is now the installed area of the dense-Pd polishing module in the stage-resolved process train.",
        "",
        f"- chance-constrained Pd area: **{selected_area:.3f} m²**;",
        f"- literature-bounded robust Pd area: **{robust_pd_area:.4f} m²**;",
        f"- minimum scrambled-Sobol trilinear probability: **{selected_surface['trilinear_probability_minimum_scramble']:.6f}**;",
        f"- exact conservative-affine probability: **{selected_surface['conservative_affine_probability']:.6f}**;",
        f"- direct cases passing at the chance design: **{sum(row['direct_physical_event'] for row in selected_rows)}/16**;",
        (
            f"- 10-bit oracle: **{ten_bit['total_logical_qubits']} logical qubits**, **{ten_bit['transpiled_cx']:,} CX**, depth **{ten_bit['transpiled_depth']:,}**;"
            if ten_bit["transpiled_cx"] is not None
            else f"- 10-bit oracle register requirement: **{ten_bit['total_logical_qubits']} logical qubits**; QASM recompilation is pending because the host blocked Qiskit's native dependency;"
        ),
        f"- 10-bit discrete probability: **{ten_bit['exact_discrete_oracle_probability']:.6f}**.",
        "",
        "The physical event combines regeneration reserve, numerical convergence, surge capacity, H2 recovery, specification-qualified shipment, and product-receiver capacity. Product composition remains conditional on an ideal defect-free dense-Pd layer.",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    fig, axes = plt.subplots(2, 2, figsize=(12.4, 8.6), constrained_layout=True)
    area_axis = [row["pd_area_m2"] for row in screen_rows]
    axes[0, 0].plot(
        area_axis,
        [row["trilinear_probability_minimum_scramble"] for row in screen_rows],
        "o-",
        label="trilinear, minimum scramble",
        color="#2563eb",
    )
    axes[0, 0].plot(
        area_axis,
        [row["conservative_affine_probability"] for row in screen_rows],
        "s--",
        label="conservative affine oracle",
        color="#7c3aed",
    )
    axes[0, 0].axhline(CHANCE_TARGET, color="#dc2626", linestyle=":", label="95% target")
    axes[0, 0].axvline(selected_area, color="#059669", linestyle="--", label=f"selected {selected_area:.3f} m²")
    axes[0, 0].set(xlabel="Installed Pd area (m²)", ylabel="Pass probability", ylim=(0.80, 1.005), title="(a) Physical chance boundary")
    axes[0, 0].legend(fontsize=8, frameon=False)

    x = np.arange(len(selected_rows))
    axes[0, 1].bar(
        x,
        [100.0 * row["joint_relative_margin"] for row in selected_rows],
        color=["#2563eb" if row["validation_kind"] == "uncertainty_corner" else "#f59e0b" for row in selected_rows],
    )
    axes[0, 1].axhline(0.0, color="#111827", linewidth=1.0)
    axes[0, 1].set_xticks(x, [row["case_id"] for row in selected_rows], rotation=55, ha="right", fontsize=7)
    axes[0, 1].set(ylabel="Joint relative margin (%)", title="(b) Sixteen direct dynamic cases")

    axes[1, 0].plot(
        [row["input_bits_per_variable"] for row in resource_rows],
        [row["absolute_probability_discretization_error"] for row in resource_rows],
        "o-",
        color="#7c3aed",
        label="probability error",
    )
    axes[1, 0].set(xlabel="Bits per uncertainty variable", ylabel="Absolute probability error", title="(c) Oracle precision and cost")
    cx_values = [
        np.nan if row["transpiled_cx"] is None else row["transpiled_cx"]
        for row in resource_rows
    ]
    if np.isfinite(cx_values).any():
        twin = axes[1, 0].twinx()
        twin.plot(
            [row["input_bits_per_variable"] for row in resource_rows],
            cx_values,
            "s--",
            color="#ef4444",
            label="CX/oracle",
        )
        twin.set_ylabel("CX gates")
        h2, l2 = twin.get_legend_handles_labels()
    else:
        axes[1, 0].text(
            0.98,
            0.92,
            "QASM recompilation pending\n(host DLL policy)",
            transform=axes[1, 0].transAxes,
            ha="right",
            va="top",
            fontsize=8,
            color="#b91c1c",
        )
        h2, l2 = [], []
    h1, l1 = axes[1, 0].get_legend_handles_labels()
    axes[1, 0].legend(h1 + h2, l1 + l2, fontsize=8, frameon=False)

    for method, color, marker in (("MC", "#dc2626", "o"), ("scrambled_Sobol_RQMC", "#059669", "s")):
        subset = [row for row in convergence if row["method"] == method]
        axes[1, 1].loglog(
            [row["n"] for row in subset],
            [row["rmse"] for row in subset],
            marker=marker,
            color=color,
            label=method,
        )
    axes[1, 1].set(xlabel="Samples", ylabel="Probability RMSE", title="(d) Classical probability baselines")
    axes[1, 1].legend(fontsize=8, frameon=False)
    for axis in axes.flat:
        axis.grid(alpha=0.25)
    fig.savefig(OUT_FIGURE, dpi=300, bbox_inches="tight")
    fig.savefig(OUT_FIGURE_PDF, bbox_inches="tight")
    fig.savefig(OUT_FIGURE_SVG, bbox_inches="tight")
    plt.close(fig)

    source_paths = [TRAIN_JSON, V19_JSON]
    for case in cases:
        source_paths.extend([case["state_path"], case["trace_path"]])
    output_paths = [
        OUT_JSON,
        OUT_MD,
        OUT_CASES,
        OUT_SCREEN,
        OUT_RESOURCES,
        OUT_CONVERGENCE,
        OUT_FIGURE,
        OUT_FIGURE_PDF,
        OUT_FIGURE_SVG,
    ]
    output_paths.append(OUT_QASM if OUT_QASM.exists() else OUT_UNCOMPILED)
    manifest = {
        "schema": "psa-physical-pd-area-qae-bridge-manifest/v1",
        "sources": [
            {
                "path": str(path.relative_to(ROOT)),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
            for path in source_paths
        ],
        "outputs": [
            {
                "path": str(path.relative_to(ROOT)),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
            for path in output_paths
        ],
    }
    OUT_MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": payload["status"],
                "selected_pd_area_m2": selected_area,
                "validation": payload["validation"],
                "ten_bit_oracle": ten_bit,
                "outputs": [str(path) for path in output_paths] + [str(OUT_MANIFEST)],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
