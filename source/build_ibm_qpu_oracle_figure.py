"""Build the manuscript quantum-event figure including the IBM QPU probe."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
QAE = RESULTS / "pressure_consistent_physical_pd_area_qae_bridge_v1" / "PSA_PHYSICAL_PD_AREA_QAE_BRIDGE.json"
PORTABLE = RESULTS / "pressure_consistent_portable_qasm_oracle_v1" / "PSA_PRESSURE_CONSISTENT_PORTABLE_QASM_ORACLE_V1.json"
HARDWARE = RESULTS / "ibm_final_event_2bit_probe" / "PSA_IBM_FINAL_EVENT_2BIT_PROBE.json"
VERIFICATION = RESULTS / "ibm_final_event_2bit_probe" / "PSA_IBM_FINAL_EVENT_2BIT_JOB_VERIFICATION.json"
OUTPUT = RESULTS / "ibm_final_event_2bit_probe" / "Fig_qae_oracle_and_ibm_hardware_v2.png"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    qae = load(QAE)
    portable = load(PORTABLE)
    hardware = load(HARDWARE)
    verification = load(VERIFICATION)

    resources = portable["resources"]
    validation = qae["validation"]
    ten_bit = qae["conservative_affine_oracle"]["ten_bit_resources"]
    compact = list(hardware["routing_rows"])
    compact.sort(key=lambda row: int(row["input_state"]))
    assert len(compact) == 64
    assert verification["comparison"]["exact_count_matches"] == 64

    plt.rcParams.update({"font.size": 9, "axes.titlesize": 10, "axes.labelsize": 9})
    fig, axes = plt.subplots(1, 3, figsize=(12.0, 3.7), constrained_layout=True)

    probabilities = [
        float(validation["conservative_affine_probability"]),
        float(ten_bit["exact_discrete_oracle_probability"]),
    ]
    axes[0].bar(["continuous\naffine", "10-bit\ndiscrete"], probabilities, color=["#2f6ce5", "#167d70"])
    axes[0].axhline(0.95, color="#d62728", linestyle="--", linewidth=1.2, label="chance target")
    axes[0].set_ylim(0.948, 0.953)
    axes[0].set_ylabel("Pass probability")
    axes[0].set_title("a  Frozen process event")
    axes[0].legend(frameon=False, fontsize=8)
    for index, value in enumerate(probabilities):
        axes[0].text(index, value + 0.00008, f"{value:.6f}", ha="center", va="bottom", fontsize=8)

    labels = ["logical\nqubits", "CX", "primitive\nsize", "all-to-all\ndepth"]
    values = [
        int(resources["total_logical_qubits"]),
        int(resources["portable_primitive_cx"]),
        int(resources["portable_primitive_size"]),
        int(resources["portable_primitive_depth_all_to_all"]),
    ]
    bars = axes[1].bar(labels, values, color=["#7c3aed", "#f59e0b", "#64748b", "#0f766e"])
    axes[1].set_yscale("log")
    axes[1].set_ylabel("Exact pre-routing count (log scale)")
    axes[1].set_title("b  Full portable oracle")
    axes[1].grid(axis="y", which="both", alpha=0.2)
    for bar, value in zip(bars, values):
        axes[1].text(bar.get_x() + bar.get_width() / 2, value * 1.08, f"{value:,}", ha="center", va="bottom", fontsize=7)

    states = np.array([int(row["input_state"]) for row in compact])
    observed = np.array([float(row["qpu_expected_probability"]) for row in compact])
    expected = np.array([int(row["expected_flag"]) for row in compact])
    colors = np.where(expected == 1, "#2f6ce5", "#c65a1e")
    axes[2].scatter(states, observed, color=colors, s=18)
    axes[2].axhline(0.5, color="#222222", linestyle="--", linewidth=1.0, label="majority threshold")
    axes[2].set_ylim(0, 1.02)
    axes[2].set_xticks(np.arange(0, 64, 8))
    axes[2].tick_params(axis="x", labelsize=7)
    axes[2].set_xlabel("Final-event two-bit input state")
    axes[2].set_ylabel("Observed expected-label fraction")
    axes[2].set_title("c  IBM Kingston, 256 shots/state")
    axes[2].legend(frameon=False, fontsize=8, loc="lower left")
    axes[2].text(
        0.98,
        0.06,
        f"64/64 majority correct\nmean = {observed.mean():.3f}\nQPU usage = {hardware['qpu_job']['usage_seconds']} s",
        transform=axes[2].transAxes,
        ha="right",
        va="bottom",
        fontsize=8,
        bbox={"facecolor": "white", "edgecolor": "#bbbbbb", "alpha": 0.9},
    )

    fig.suptitle("Process chance event, portable resource boundary, and final-event IBM QPU check", fontweight="bold")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT, dpi=260)
    plt.close(fig)
    print(OUTPUT)


if __name__ == "__main__":
    main()
