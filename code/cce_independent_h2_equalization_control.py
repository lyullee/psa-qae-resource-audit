"""Build an independent same-chemistry H2 PSA equalization control.

The source is Thelen's public 2023 TU Wien diploma thesis (DOI
10.34726/hss.2023.101204).  In automated four-column experiment VA-10,
operating points BP1 and BP2 differed only in equalization pressure.  This
script records the reported purity and the two recovery measurements, checks
them against the frozen local event thresholds, and writes a deliberately
narrow claim boundary.

This is an independent H2 mechanism control.  It is not a replication of the
local product-gas recycle policy and it cannot validate the local chance
probabilities or policy selection.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RESULTS = ROOT / "10_TEA_LCA_Python" / "results" / "pycharm_publication_enhancement"
SOURCE_DIR = HERE / "external_data" / "h2_psa_thelen_2023"

OUT_STEM = "PSA_QAE_CCE_INDEPENDENT_H2_EQUALIZATION_CONTROL"
OUT_JSON = RESULTS / f"{OUT_STEM}.json"
OUT_CSV = RESULTS / f"{OUT_STEM}.csv"
OUT_MD = RESULTS / f"{OUT_STEM}.md"
OUT_PNG = RESULTS / f"{OUT_STEM}_FIGURE.png"
OUT_PDF = RESULTS / f"{OUT_STEM}_FIGURE.pdf"

PURITY_THRESHOLD_PCT = 99.98
RECOVERY_THRESHOLD_PCT = 78.9

ROWS = [
    {
        "experiment": "VA-10",
        "operating_point": "BP1",
        "equalization_pressure_bara": 4.50,
        "h2_purity_pct": 99.95,
        "h2_recovery_direct_bellows_meter_pct": 81.45,
        "h2_recovery_pulse_transmitter_pct": 80.78,
        "source_table24_recovery_pct": 81.3,
        "source_table24_productivity_slm_per_kg": 1.36,
    },
    {
        "experiment": "VA-10",
        "operating_point": "BP2",
        "equalization_pressure_bara": 4.75,
        "h2_purity_pct": 99.93,
        "h2_recovery_direct_bellows_meter_pct": 79.15,
        "h2_recovery_pulse_transmitter_pct": 79.47,
        "source_table24_recovery_pct": 79.0,
        "source_table24_productivity_slm_per_kg": 1.33,
    },
]


def main() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)

    rows = []
    for source_row in ROWS:
        row = dict(source_row)
        recoveries = np.array(
            [
                row["h2_recovery_direct_bellows_meter_pct"],
                row["h2_recovery_pulse_transmitter_pct"],
            ],
            dtype=float,
        )
        row["h2_recovery_method_mean_pct"] = float(np.mean(recoveries))
        row["h2_recovery_method_range_pct_point"] = float(np.ptp(recoveries))
        row["passes_frozen_purity_threshold"] = bool(
            row["h2_purity_pct"] >= PURITY_THRESHOLD_PCT
        )
        row["passes_frozen_recovery_threshold_both_methods"] = bool(
            np.all(recoveries >= RECOVERY_THRESHOLD_PCT)
        )
        row["passes_frozen_joint_event"] = bool(
            row["passes_frozen_purity_threshold"]
            and row["passes_frozen_recovery_threshold_both_methods"]
        )
        rows.append(row)

    bp1, bp2 = rows
    direct_delta = (
        bp2["h2_recovery_direct_bellows_meter_pct"]
        - bp1["h2_recovery_direct_bellows_meter_pct"]
    )
    pulse_delta = (
        bp2["h2_recovery_pulse_transmitter_pct"]
        - bp1["h2_recovery_pulse_transmitter_pct"]
    )
    mean_delta = (
        bp2["h2_recovery_method_mean_pct"] - bp1["h2_recovery_method_mean_pct"]
    )
    purity_delta = bp2["h2_purity_pct"] - bp1["h2_purity_pct"]
    productivity_delta = (
        bp2["source_table24_productivity_slm_per_kg"]
        - bp1["source_table24_productivity_slm_per_kg"]
    )

    payload = {
        "schema": "psa-qae-cce-independent-h2-equalization-control/v1",
        "status": "independent_same_chemistry_equalization_direction_control_not_same_recycle_policy_event_validation",
        "source": {
            "citation": "F. Thelen, Optimierung einer Druckwechseladsorptionsanlage fuer die Gewinnung von hochreinem Wasserstoff, TU Wien, 2023",
            "doi": "10.34726/hss.2023.101204",
            "repository": "https://repositum.tuwien.at/handle/20.500.12708/175664",
            "local_pdf": str(SOURCE_DIR / "Thelen_2023_H2_PSA.pdf"),
            "source_locations": {
                "only_changed_factor": "Section 6.2.2, extracted-text lines 3559-3563",
                "recovery_measurements": "Table 19, extracted-text lines 3690-3725",
                "purity_and_productivity": "Table 24, extracted-text lines 6560-6582",
                "measurement_warning": "Section 6.2.2, extracted-text lines 3681-3688",
            },
            "system": "automated four-column H2/N2/CO/CO2/CH4 PSA pilot, maximum 1 Nm3/h feed and 7 bara",
        },
        "frozen_local_event_for_nontransfer_check": {
            "h2_purity_min_pct": PURITY_THRESHOLD_PCT,
            "h2_recovery_min_pct": RECOVERY_THRESHOLD_PCT,
        },
        "rows": rows,
        "paired_effects_bp2_minus_bp1": {
            "equalization_pressure_bara": 0.25,
            "h2_purity_pct_point": purity_delta,
            "h2_recovery_direct_bellows_meter_pct_point": direct_delta,
            "h2_recovery_pulse_transmitter_pct_point": pulse_delta,
            "h2_recovery_method_mean_pct_point": mean_delta,
            "h2_productivity_slm_per_kg": productivity_delta,
            "recovery_direction_consistent_across_measurement_methods": bool(
                direct_delta < 0 and pulse_delta < 0
            ),
        },
        "measurement_context": {
            "reported_feed_flow_sensitivity": "a 1% feed-flow deviation causes an H2-recovery deviation of the same order",
            "recovery_method_difference_bp1_pct_point": abs(
                bp1["h2_recovery_direct_bellows_meter_pct"]
                - bp1["h2_recovery_pulse_transmitter_pct"]
            ),
            "recovery_method_difference_bp2_pct_point": abs(
                bp2["h2_recovery_direct_bellows_meter_pct"]
                - bp2["h2_recovery_pulse_transmitter_pct"]
            ),
            "excluded_bp2_with_continuous_raffinate_analysis": {
                "direct_bellows_meter_recovery_pct": 57.95,
                "pulse_transmitter_recovery_pct": 56.90,
                "reason": "the analyser withdrew about 1 slm of raffinate and changed column pressurization; this is not the same operating pair",
            },
        },
        "claim_boundary": {
            "supported": [
                "same-chemistry H2 PSA evidence that a 0.25 bara increase in equalization pressure lowered recovery under an otherwise matched operating pair",
                "the recovery direction is consistent for direct bellows-meter and pulse-transmitter calculations",
                "the local recovery threshold is passed at both literature operating points",
            ],
            "not_supported": [
                "validation of the local product-gas recycle fractions 0.420/0.427/0.430",
                "validation of the frozen joint purity/recovery event because both literature purities are below 99.98%",
                "reproduction of the local 0.420 policy selection or its event probabilities",
                "synchronized raw historian validation or industrial plant validation",
            ],
        },
        "conclusion": (
            "Thelen VA-10 supplies an independent, same-chemistry, one-factor equalization-pressure control. "
            f"Raising equalization pressure from 4.50 to 4.75 bara changes H2 recovery by {direct_delta:.2f} and {pulse_delta:.2f} percentage points under the two reported measurement methods, while purity changes by {purity_delta:.2f} percentage point. "
            "This strengthens the process-mechanism evidence tier but does not close the same-policy, same-event validation gate."
        ),
    }

    OUT_JSON.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    with OUT_CSV.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    md = [
        "# Independent same-chemistry H2 equalization control",
        "",
        "Thelen's automated four-column H2 PSA experiment VA-10 contains a matched pair whose only reported change was equalization pressure: 4.50 bara at BP1 and 4.75 bara at BP2. This is a same-chemistry mechanism control, not a replication of the local product-gas recycle policy.",
        "",
        "| operating point | equalization, bara | H2 purity, % | recovery: direct BGZ, % | recovery: pulse, % | productivity, slm/kg | frozen joint event |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        md.append(
            f"| {row['operating_point']} | {row['equalization_pressure_bara']:.2f} | "
            f"{row['h2_purity_pct']:.2f} | {row['h2_recovery_direct_bellows_meter_pct']:.2f} | "
            f"{row['h2_recovery_pulse_transmitter_pct']:.2f} | "
            f"{row['source_table24_productivity_slm_per_kg']:.2f} | "
            f"{row['passes_frozen_joint_event']} |"
        )
    md += [
        "",
        f"For BP2 minus BP1, purity changes by `{purity_delta:+.2f}` percentage point, direct-meter recovery by `{direct_delta:+.2f}` percentage points, pulse-derived recovery by `{pulse_delta:+.2f}` percentage points, and the two-method mean recovery by `{mean_delta:+.3f}` percentage points. The recovery sign is therefore measurement-method robust within the reported pair.",
        "",
        f"Both recovery estimates remain above the frozen local recovery threshold of `{RECOVERY_THRESHOLD_PCT:.1f}%`, but both reported purities are below the frozen `{PURITY_THRESHOLD_PCT:.2f}%` purity threshold. The literature pair therefore cannot validate the frozen joint event. The source also warns that a 1% feed-flow deviation causes a recovery deviation of similar order, so the paired effect should be interpreted as a direction control rather than a precise transferable effect size.",
        "",
        "**Claim boundary.** Supported: matched same-chemistry evidence for the sign of the equalization-pressure/recovery response. Unsupported: the local recycle candidates, the local chance probabilities, the 0.420 selection, a synchronized historian claim, or industrial H2 validation.",
        "",
        "Source: F. Thelen, TU Wien (2023), DOI `10.34726/hss.2023.101204`; Section 6.2.2 and Tables 19 and 24.",
    ]
    OUT_MD.write_text("\n".join(md) + "\n", encoding="utf-8")

    pressures = np.array([row["equalization_pressure_bara"] for row in rows])
    purities = np.array([row["h2_purity_pct"] for row in rows])
    recovery_direct = np.array(
        [row["h2_recovery_direct_bellows_meter_pct"] for row in rows]
    )
    recovery_pulse = np.array(
        [row["h2_recovery_pulse_transmitter_pct"] for row in rows]
    )

    plt.rcParams.update({"font.size": 9, "axes.titlesize": 10})
    fig, axes = plt.subplots(1, 2, figsize=(9.1, 3.7), constrained_layout=True)

    ax = axes[0]
    ax.plot(pressures, purities, marker="o", linewidth=1.8, color="#1368aa")
    ax.axhline(PURITY_THRESHOLD_PCT, color="#b03a2e", linestyle="--", linewidth=1.2)
    for x, y, label in zip(pressures, purities, ["BP1", "BP2"]):
        ax.annotate(f"{label}: {y:.2f}%", (x, y), xytext=(0, -15), textcoords="offset points", ha="center")
    ax.set_xlabel("Equalization pressure (bara)")
    ax.set_ylabel("H$_2$ purity (%)")
    ax.set_title("(a) Purity does not meet the frozen 99.98% event")
    ax.set_xlim(4.43, 4.82)
    ax.set_ylim(99.90, 100.00)
    ax.grid(alpha=0.25)

    ax = axes[1]
    ax.plot(pressures, recovery_direct, marker="o", linewidth=1.8, label="direct bellows meter", color="#117864")
    ax.plot(pressures, recovery_pulse, marker="s", linewidth=1.8, label="pulse transmitter", color="#7d3c98")
    ax.axhline(RECOVERY_THRESHOLD_PCT, color="#b03a2e", linestyle="--", linewidth=1.2, label="frozen threshold")
    for x, y, label in zip(pressures, recovery_direct, ["BP1", "BP2"]):
        ax.annotate(f"{label}: {y:.2f}%", (x, y), xytext=(0, 7), textcoords="offset points", ha="center", fontsize=8)
    ax.set_xlabel("Equalization pressure (bara)")
    ax.set_ylabel("H$_2$ recovery (%)")
    ax.set_title("(b) Recovery direction agrees across two methods")
    ax.set_xlim(4.43, 4.82)
    ax.set_ylim(78.5, 82.0)
    ax.grid(alpha=0.25)
    ax.legend(loc="upper right", fontsize=7.5, frameon=False)

    fig.suptitle("Independent H$_2$ PSA equalization-pressure control (Thelen VA-10)", fontsize=11)
    fig.savefig(OUT_PNG, dpi=300, bbox_inches="tight")
    fig.savefig(OUT_PDF, bbox_inches="tight")
    plt.close(fig)

    print(
        json.dumps(
            {
                "status": payload["status"],
                "recovery_delta_direct_pct_point": direct_delta,
                "recovery_delta_pulse_pct_point": pulse_delta,
                "joint_event_labels": [row["passes_frozen_joint_event"] for row in rows],
                "outputs": [
                    str(OUT_JSON),
                    str(OUT_CSV),
                    str(OUT_MD),
                    str(OUT_PNG),
                    str(OUT_PDF),
                ],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
