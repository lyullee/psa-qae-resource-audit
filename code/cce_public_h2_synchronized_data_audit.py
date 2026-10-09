"""Create a machine-readable audit of public H2 PSA validation data.

The audit asks a deliberately strict question: can a public source validate the
frozen product-gas-recycle policy and purity/recovery event using synchronized
cycle data?  It does not score papers by scientific quality.  It records which
signals are publicly recoverable and therefore prevents table-level,
cross-chemistry, or simulation evidence from being relabelled as plant
validation.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT_DIR = ROOT / "10_TEA_LCA_Python" / "results" / "pycharm_publication_enhancement"
OUT_JSON = OUT_DIR / "PSA_QAE_CCE_PUBLIC_H2_SYNCHRONIZED_DATA_AUDIT.json"
OUT_CSV = OUT_DIR / "PSA_QAE_CCE_PUBLIC_H2_SYNCHRONIZED_DATA_AUDIT.csv"
OUT_MD = OUT_DIR / "PSA_QAE_CCE_PUBLIC_H2_SYNCHRONIZED_DATA_AUDIT.md"


# Coverage codes: Y = public and machine-readable/present; P = partial,
# derived, table, or figure only; N = absent; R = reported to exist but access
# restricted.  These codes describe the scoped public record, not everything
# the original investigators may hold.
ROWS = [
    {
        "source_id": "thelen_2023_va10",
        "source": "Thelen 2023 VA-10",
        "url": "https://doi.org/10.34726/hss.2023.101204",
        "chemistry_scale": "four-column automated H2/N2/CO/CO2/CH4 laboratory-pilot PSA",
        "process_type": "PSA",
        "control_variable": "equalization pressure and operating-point settings",
        "cycle_index": "P",
        "valve_or_step_schedule": "P",
        "pressure_time_series": "P",
        "feed_flow_time_series": "P",
        "product_flow_time_series": "P",
        "continuous_product_composition": "P",
        "purity_recovery": "Y",
        "repetitions": "matched BP1/BP2 pair; two recovery calculations; plotted VA-10 traces",
        "common_time_base": "P",
        "public_raw_file": "N",
        "same_product_recycle_policy": False,
        "same_frozen_event": False,
        "admissible_role": "same-chemistry equalization-pressure/recovery direction control",
        "exclusion_reason": "no historian export; different control; both reported purities are below 99.98%",
    },
    {
        "source_id": "voigt_2022_h2_ch4",
        "source": "Voigt 2022 H2/CH4 four-bed campaign",
        "url": "https://doi.org/10.34726/hss.2022.103430",
        "chemistry_scale": "four-bed H2/CH4 laboratory PSA",
        "process_type": "PSA",
        "control_variable": "purge/feed ratio and staged feed conditions",
        "cycle_index": "P",
        "valve_or_step_schedule": "P",
        "pressure_time_series": "P",
        "feed_flow_time_series": "P",
        "product_flow_time_series": "P",
        "continuous_product_composition": "N",
        "purity_recovery": "P",
        "repetitions": "13 cycle-level operating rows",
        "common_time_base": "N",
        "public_raw_file": "N",
        "same_product_recycle_policy": False,
        "same_frozen_event": False,
        "admissible_role": "table-level H2 trend and candidate-spacing resolution audit",
        "exclusion_reason": "purge/feed is not product recycle; continuous purity and synchronized streams are unavailable",
    },
    {
        "source_id": "schell_2013_h2_co2",
        "source": "Schell et al. 2013 laboratory H2/CO2 PSA",
        "url": "https://doi.org/10.1021/ie3026532",
        "chemistry_scale": "two-column laboratory H2/CO2 activated-carbon PSA",
        "process_type": "PSA",
        "control_variable": "adsorption pressure and adsorption time",
        "cycle_index": "P",
        "valve_or_step_schedule": "P",
        "pressure_time_series": "P",
        "feed_flow_time_series": "P",
        "product_flow_time_series": "P",
        "continuous_product_composition": "P",
        "purity_recovery": "Y",
        "repetitions": "product flow sampled at least every 5 s over at least three cycles; one repeated 100 s case",
        "common_time_base": "P",
        "public_raw_file": "N",
        "same_product_recycle_policy": False,
        "same_frozen_event": False,
        "admissible_role": "experimental H2/CO2 cyclic-model and transient measurement anchor",
        "exclusion_reason": "supplement contains figures/tables rather than joined raw files; controls differ from product recycle",
    },
    {
        "source_id": "yang_1997_topsail",
        "source": "Yang 1997 experiment with public toPSAil case",
        "url": "https://doi.org/10.1021/ie960728h",
        "chemistry_scale": "two-bed six-step H2/CO zeolite-5A PSA",
        "process_type": "PSA",
        "control_variable": "purge/feed ratio, pressure, step times, equalization time",
        "cycle_index": "P",
        "valve_or_step_schedule": "Y",
        "pressure_time_series": "P",
        "feed_flow_time_series": "P",
        "product_flow_time_series": "P",
        "continuous_product_composition": "N",
        "purity_recovery": "Y",
        "repetitions": "published experiment plus four archived model configurations",
        "common_time_base": "P",
        "public_raw_file": "N",
        "same_product_recycle_policy": False,
        "same_frozen_event": False,
        "admissible_role": "same-chemistry model/experiment and high-purity performance anchor",
        "exclusion_reason": "repository has inputs but no result MAT files; P/F differs from product recycle; recovery is 75.87%",
    },
    {
        "source_id": "gubin_2025_pilot",
        "source": "Gubin et al. 2025 integrated pilot",
        "url": "https://doi.org/10.1016/j.ijhydene.2025.02.357",
        "chemistry_scale": "50 kWth biomass gasifier/WGS/cleaning/H2 PSA pilot",
        "process_type": "PSA",
        "control_variable": "integrated pilot operating points",
        "cycle_index": "P",
        "valve_or_step_schedule": "P",
        "pressure_time_series": "P",
        "feed_flow_time_series": "P",
        "product_flow_time_series": "P",
        "continuous_product_composition": "P",
        "purity_recovery": "Y",
        "repetitions": "reported high-purity pilot operating points",
        "common_time_base": "P",
        "public_raw_file": "N",
        "same_product_recycle_policy": False,
        "same_frozen_event": False,
        "admissible_role": "pilot-scale end-product performance envelope",
        "exclusion_reason": "public supplement contains a tar table rather than synchronized PSA historian data",
    },
    {
        "source_id": "windbacher_2026_breakthrough",
        "source": "Windbacher 2026 H2 breakthrough archive",
        "url": "https://doi.org/10.34726/hss.2026.138181",
        "chemistry_scale": "single-bed H2/CH4(/C3H8) laboratory breakthrough",
        "process_type": "single-bed adsorption",
        "control_variable": "pressure, composition, and experiment sequence",
        "cycle_index": "N",
        "valve_or_step_schedule": "P",
        "pressure_time_series": "R",
        "feed_flow_time_series": "P",
        "product_flow_time_series": "N",
        "continuous_product_composition": "R",
        "purity_recovery": "N",
        "repetitions": "digital appendix reports multiple raw experiments",
        "common_time_base": "R",
        "public_raw_file": "R",
        "same_product_recycle_policy": False,
        "same_frozen_event": False,
        "admissible_role": "restricted lead for adsorption and analyzer-delay calibration",
        "exclusion_reason": "TU Wien account/group approval required; single manual-valve bed is not cyclic multi-bed PSA",
    },
    {
        "source_id": "anese_2026_refinery",
        "source": "Anese et al. 2026 refinery H2 PSA",
        "url": "https://doi.org/10.1021/acs.iecr.6c00849",
        "chemistry_scale": "six-vessel industrial refinery H2 PSA",
        "process_type": "PSA",
        "control_variable": "actual valve opening and valve-fault conditions",
        "cycle_index": "Y",
        "valve_or_step_schedule": "Y",
        "pressure_time_series": "Y",
        "feed_flow_time_series": "P",
        "product_flow_time_series": "P",
        "continuous_product_composition": "N",
        "purity_recovery": "N",
        "repetitions": "industrial normal/fault histories reported in normalized form",
        "common_time_base": "Y",
        "public_raw_file": "N",
        "same_product_recycle_policy": False,
        "same_frozen_event": False,
        "admissible_role": "industrial valve/pressure modeling precedent",
        "exclusion_reason": "values are normalized/confidential; product composition and raw files are not released",
    },
    {
        "source_id": "lee_2022_linde",
        "source": "Lee et al. 2022 industrial monitoring",
        "url": "https://doi.org/10.3389/fceng.2022.1064221",
        "chemistry_scale": "12-bed 15-step industrial H2 PSA",
        "process_type": "PSA",
        "control_variable": "normal operation and valve-fault classes",
        "cycle_index": "Y",
        "valve_or_step_schedule": "P",
        "pressure_time_series": "Y",
        "feed_flow_time_series": "N",
        "product_flow_time_series": "N",
        "continuous_product_composition": "N",
        "purity_recovery": "N",
        "repetitions": "2,070 normal cycles plus simulated and real faults",
        "common_time_base": "Y",
        "public_raw_file": "N",
        "same_product_recycle_policy": False,
        "same_frozen_event": False,
        "admissible_role": "industrial pressure-profile and fault-monitoring precedent",
        "exclusion_reason": "pressure-only continuous measurement; real axes and data are withheld",
    },
    {
        "source_id": "golmakani_2019_cranfield",
        "source": "Golmakani et al. 2019 Cranfield PVSA record",
        "url": "https://doi.org/10.17862/cranfield.rd.10123346",
        "chemistry_scale": "four-bed two-layer H2/CO2/CH4/CO/N2 PVSA simulation",
        "process_type": "PVSA simulation",
        "control_variable": "feed impurity composition",
        "cycle_index": "N",
        "valve_or_step_schedule": "P",
        "pressure_time_series": "N",
        "feed_flow_time_series": "N",
        "product_flow_time_series": "N",
        "continuous_product_composition": "N",
        "purity_recovery": "P",
        "repetitions": "three reported simulation runs",
        "common_time_base": "N",
        "public_raw_file": "N",
        "same_product_recycle_policy": False,
        "same_frozen_event": False,
        "admissible_role": "PVSA simulation and provenance lead",
        "exclusion_reason": "indexed record exposes only disclaimer.txt; associated study is simulation rather than synchronized experiment",
    },
    {
        "source_id": "otway_co2_historian",
        "source": "Otway field CO2 PSA historian",
        "url": "https://doi.org/10.17632/kb3b4sddzs.1",
        "chemistry_scale": "field CO2/natural-gas PSA",
        "process_type": "PSA",
        "control_variable": "valves and scheduled cycle operation",
        "cycle_index": "Y",
        "valve_or_step_schedule": "Y",
        "pressure_time_series": "Y",
        "feed_flow_time_series": "Y",
        "product_flow_time_series": "Y",
        "continuous_product_composition": "N",
        "purity_recovery": "N",
        "repetitions": "82,681 one-second rows; seven complete cycles",
        "common_time_base": "Y",
        "public_raw_file": "Y",
        "same_product_recycle_policy": False,
        "same_frozen_event": False,
        "admissible_role": "cross-chemistry hydraulic and signal-synchronization validation",
        "exclusion_reason": "not H2 chemistry and no equivalent continuous H2 product-composition signal",
    },
]


STRICT_CHANNELS = [
    "cycle_index",
    "valve_or_step_schedule",
    "pressure_time_series",
    "feed_flow_time_series",
    "product_flow_time_series",
    "continuous_product_composition",
    "common_time_base",
    "public_raw_file",
]


def strict_pass(row: dict[str, object]) -> bool:
    return (
        "H2" in str(row["chemistry_scale"])
        and all(row[field] == "Y" for field in STRICT_CHANNELS)
        and bool(row["same_product_recycle_policy"])
        and bool(row["same_frozen_event"])
    )


def main() -> None:
    rows = [dict(row, strict_same_policy_event_raw_pass=strict_pass(row)) for row in ROWS]
    strict_rows = [row["source_id"] for row in rows if row["strict_same_policy_event_raw_pass"]]
    public_raw_rows = [row["source_id"] for row in rows if row["public_raw_file"] == "Y"]
    same_chemistry_rows = [row["source_id"] for row in rows if "H2" in str(row["chemistry_scale"])]

    payload = {
        "schema": "psa-qae-cce-public-h2-synchronized-data-audit/v1",
        "status": "no_public_source_closes_same_product_recycle_same_event_synchronized_raw_gate",
        "audit_scope": "publicly recoverable files and reported source contents as screened on 2026-10-09",
        "coverage_legend": {
            "Y": "present and publicly machine-readable or explicitly available at the required level",
            "P": "partial, derived, table, figure, or summary only",
            "N": "absent from the scoped public record",
            "R": "reported to exist but access restricted",
        },
        "frozen_gate": {
            "policy": "product-gas recycle fraction 0.420/0.427/0.430",
            "event": "H2 purity >= 0.9998 and external recovery >= 0.789",
            "required_channels": STRICT_CHANNELS,
            "strict_rule": "H2 chemistry; every required channel Y; same product-recycle policy; same frozen event",
        },
        "summary": {
            "sources": len(rows),
            "same_chemistry_sources": len(same_chemistry_rows),
            "public_machine_readable_raw_sources": len(public_raw_rows),
            "strict_gate_pass_sources": len(strict_rows),
            "strict_gate_pass_source_ids": strict_rows,
            "best_public_h2_experimental_coverage": "thelen_2023_va10",
            "best_public_synchronized_historian": "otway_co2_historian",
            "closest_h2_model_experiment_anchor": "yang_1997_topsail",
        },
        "rows": rows,
        "claim_boundary": {
            "supported": [
                "a structured public-data availability audit for H2 PSA validation",
                "public sources collectively support same-chemistry performance, mechanism, model, and industrial-pressure precedents",
                "the Otway file supports cross-chemistry valve-pressure-flow synchronization",
            ],
            "not_supported": [
                "industrial H2 plant validation of the frozen product-recycle policy",
                "independent reproduction of the 0.420 policy choice",
                "same-event validation from a public synchronized H2 historian",
            ],
        },
        "minimum_new_evidence": {
            "design": "at least the three frozen recycle settings with independent cycles or runs",
            "signals": "timestamp, run/cycle/bed/step, commanded and actual valves, bed/header/buffer pressures, feed/product/tail/purge/equalization flows, and feed/product/tail H2/CO2/CH4/CO/N2 fractions",
            "quality": "native analyzer timestamps, transport-delay correction, calibration metadata, units, standard-state definition, and a held-out operating condition",
            "resolution": "valve/pressure/flow at 1 s or faster; composition at native rate with delay retained",
        },
    }

    OUT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    fieldnames = list(rows[0].keys())
    with OUT_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    columns = [
        ("source", "source"),
        ("type", "process_type"),
        ("cycle", "cycle_index"),
        ("valve/step", "valve_or_step_schedule"),
        ("P", "pressure_time_series"),
        ("feed F", "feed_flow_time_series"),
        ("product F", "product_flow_time_series"),
        ("product y", "continuous_product_composition"),
        ("clock", "common_time_base"),
        ("raw", "public_raw_file"),
        ("same policy", "same_product_recycle_policy"),
        ("same event", "same_frozen_event"),
    ]
    lines = [
        "# Public H2 PSA synchronized-data availability audit",
        "",
        "This audit separates public availability from scientific quality. A strict pass requires H2 chemistry, a public synchronized raw file with all declared channels, the same product-gas-recycle policy, and the same frozen purity/recovery event. Coverage codes are **Y** (present), **P** (partial/table/figure), **N** (absent), and **R** (restricted).",
        "",
        "| " + " | ".join(label for label, _ in columns) + " |",
        "|" + "|".join("---" if key in {"source", "process_type"} else "---:" for _, key in columns) + "|",
    ]
    for row in rows:
        values = []
        for _, key in columns:
            value = row[key]
            if isinstance(value, bool):
                value = "Y" if value else "N"
            values.append(str(value))
        lines.append("| " + " | ".join(values) + " |")
    lines += [
        "",
        f"**Strict gate result:** `{len(strict_rows)}/{len(rows)}` sources pass. The closest public H2 experiment is Thelen VA-10, but its historian is not downloadable and its control is equalization pressure. The only fully public synchronized historian in this set is Otway, which has different chemistry and lacks a continuous H2 product-composition channel.",
        "",
        "The Schell H2/CO2 study supplies a useful cyclic experimental database with pressure, product-flow, and mass-spectrometer evidence, but the public supplement exposes plots/tables rather than a joined raw archive and varies adsorption pressure/time instead of the frozen product-recycle coordinate. The Cranfield record exposes only `disclaimer.txt` in the scoped access and accompanies a simulation study.",
        "",
        "Accordingly, the manuscript may claim public H2 performance and mechanism anchors plus cross-chemistry hydraulic validation. It may not claim independent industrial H2 validation of the frozen policy or event.",
        "",
        f"Machine-readable outputs: `{OUT_JSON.name}` and `{OUT_CSV.name}`.",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "status": payload["status"],
                "sources": len(rows),
                "strict_gate_pass_sources": len(strict_rows),
                "json": str(OUT_JSON),
                "csv": str(OUT_CSV),
                "md": str(OUT_MD),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
