"""Derive Pd-module acceptance selectivities and test public membrane anchors.

The audit replays the final 0.887-m2, 50%-permeance-retention design over all
eight uncertainty corners and eight predeclared hold-outs.  Each impurity
selectivity is reduced independently while the other three remain at the
selected values.  Public Li (2011) and DOE/MPT (2005) measurements are then
inserted as explicit stress cases.  The result is a module procurement screen,
not a claim that any literature apparatus validates the final product.
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

sys.path.insert(0, str(Path(__file__).resolve().parent))
import psa_independent_ode_membrane_audit as ode
import psa_public_schedule_strict_uncertainty_ensemble as strict


ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"
ODE_JSON = (
    RESULTS
    / os.environ.get("PSA_SELECTIVITY_ODE_DIR", "independent_ode_membrane_audit")
    / "PSA_INDEPENDENT_ODE_MEMBRANE_AUDIT.json"
)
V22_JSON = RESULTS / "final_objective_evidence_v22" / "PSA_FINAL_OBJECTIVE_EVIDENCE_V22.json"
OUT = RESULTS / os.environ.get(
    "PSA_SELECTIVITY_OUTPUT_DIR", "public_selectivity_acceptance_audit_v1"
)

AREA_M2 = 0.887
RETENTION = 0.50
IMPURITIES = ("CO", "CO2", "N2", "CH4")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    source = json.loads(ODE_JSON.read_text(encoding="utf-8"))
    v22 = json.loads(V22_JSON.read_text(encoding="utf-8"))
    decision = v22["primary_engineering_decision"]
    recovery_floor = float(decision["minimum_h2_recovery"])
    shipment_floor = float(decision["minimum_qualified_h2_rate_mol_s"])
    gate = strict.strict_gate(strict.load_contract())
    selected = {
        name: float(source["revised_guard_design"]["selected_effective_selectivity"][name])
        for name in IMPURITIES
    }

    cases = ode.case_data()
    for case in cases:
        product, _retentate, info = ode.integrate_polymer(
            case["surge_outlet_mol"], case["packet_duration_s"]
        )
        case["ode_stage1_product_mol"] = product
        case["ode_stage1_balance"] = float(info["mass_balance_max_abs_mol"])

    cache: dict[tuple[float, ...], tuple[list[dict], float, dict]] = {}

    def evaluate(selectivity: dict[str, float]) -> tuple[list[dict], float, dict]:
        key = tuple(round(float(selectivity[name]), 8) for name in IMPURITIES)
        if key in cache:
            return cache[key]
        products = []
        balances = []
        for case in cases:
            product, _retentate, info = ode.integrate_pd(
                case["ode_stage1_product_mol"],
                case["packet_duration_s"],
                area_m2=AREA_M2,
                retention=RETENTION,
                selectivity=selectivity,
            )
            products.append(product)
            balances.append(max(case["ode_stage1_balance"], info["mass_balance_max_abs_mol"]))
        rows, receiver = ode.receiver_rows(
            cases,
            products,
            area_m2=AREA_M2,
            retention=RETENTION,
            recovery_floor=recovery_floor,
            shipment_floor=shipment_floor,
            gate=gate,
            module_balances=balances,
        )
        cache[key] = (rows, receiver, ode.summarize(rows, receiver))
        return cache[key]

    baseline_rows, baseline_receiver, baseline_summary = evaluate(selected)
    if not baseline_summary["all_pass"]:
        raise AssertionError("frozen 0.887-m2 baseline no longer passes")

    threshold_rows: list[dict] = []
    for impurity in IMPURITIES:
        def passes(alpha: float) -> bool:
            trial = dict(selected)
            trial[impurity] = float(alpha)
            return bool(evaluate(trial)[2]["all_pass"])

        low_log = math.log(1.0)
        high_log = math.log(max(selected[impurity], 1.0e8))
        if passes(math.exp(low_log)):
            minimum = math.exp(low_log)
        else:
            if not passes(math.exp(high_log)):
                raise AssertionError(f"upper bound does not pass for {impurity}")
            for _ in range(32):
                mid_log = 0.5 * (low_log + high_log)
                if passes(math.exp(mid_log)):
                    high_log = mid_log
                else:
                    low_log = mid_log
            minimum = math.exp(high_log)
        guard = 1.25 * minimum
        trial = dict(selected)
        trial[impurity] = guard
        guard_summary = evaluate(trial)[2]
        threshold_rows.append(
            {
                "impurity": impurity,
                "product_limit_ppm": 1.0e6 * float(gate["impurity_max_fraction"][impurity]),
                "minimum_effective_selectivity": minimum,
                "guard_banded_selectivity_1p25x": guard,
                "selected_effective_selectivity": selected[impurity],
                "selected_to_minimum_ratio": selected[impurity] / minimum,
                "guard_direct_pass_count": guard_summary["pass_count"],
                "guard_direct_case_count": guard_summary["case_count"],
            }
        )

    guard_vector = {
        row["impurity"]: row["guard_banded_selectivity_1p25x"]
        for row in threshold_rows
    }
    procurement_vector = {
        name: math.ceil(value / 10.0) * 10.0
        for name, value in guard_vector.items()
    }
    scenarios = [
        {
            "scenario_id": "selected_final_design",
            "source": "project selected finite-selectivity vector",
            "selectivity": dict(selected),
            "interpretation": "final numerical baseline",
        },
        {
            "scenario_id": "simultaneous_1p25x_component_guard",
            "source": "component-specific adaptive-ODE acceptance bisections",
            "selectivity": guard_vector,
            "interpretation": "all four independently derived 1.25x guards imposed together",
        },
        {
            "scenario_id": "rounded_procurement_guard",
            "source": "component-specific adaptive-ODE acceptance bisections",
            "selectivity": procurement_vector,
            "interpretation": "all four 1.25x guards rounded upward to the next 10",
        },
        {
            "scenario_id": "li_2011_n2_end_of_test",
            "source": "Li et al. 2011, 8.0e-7 H2 and 2.6e-9 N2 permeance",
            "selectivity": {**selected, "N2": 8.0e-7 / 2.6e-9},
            "interpretation": "N2-only transfer; other impurity selectivities remain selected",
        },
        {
            "scenario_id": "li_2011_n2_recovered_h2_permeance",
            "source": "Li et al. 2011, 1.2e-6 H2 and 2.6e-9 N2 permeance",
            "selectivity": {**selected, "N2": 1.2e-6 / 2.6e-9},
            "interpretation": "N2-only transfer; other impurity selectivities remain selected",
        },
        {
            "scenario_id": "doe_mpt_2005_shell_30psig",
            "source": "DOE/MPT 2005 Table 1, shell feed, 400 C, 30 psig",
            "selectivity": {"CO": 74.4, "CO2": 96.1, "N2": 74.6, "CH4": 74.6},
            "interpretation": "CH4 conservatively represented by the report's N2 substitute",
        },
        {
            "scenario_id": "doe_mpt_2005_shell_60psig",
            "source": "DOE/MPT 2005 Table 1, shell feed, 400 C, 60 psig",
            "selectivity": {"CO": 92.0, "CO2": 115.5, "N2": 92.2, "CH4": 92.2},
            "interpretation": "CH4 conservatively represented by the report's N2 substitute",
        },
        {
            "scenario_id": "generic_alpha_100_defective_module",
            "source": "DOE/MPT 2005 reported order-of-magnitude",
            "selectivity": {name: 100.0 for name in IMPURITIES},
            "interpretation": "defective supported-Pd rejection stress",
        },
        {
            "scenario_id": "pure_pd_n2_gt_6000_transfer",
            "source": "DOE final report OSTI 898816; H2/N2 >6000",
            "selectivity": {**selected, "N2": 6000.0},
            "interpretation": "N2 lower-bound transfer only; other impurity selectivities remain selected",
        },
    ]
    scenario_rows: list[dict] = []
    all_case_rows: list[dict] = []
    for scenario in scenarios:
        rows, receiver, summary = evaluate(scenario["selectivity"])
        scenario_rows.append(
            {
                "scenario_id": scenario["scenario_id"],
                "source": scenario["source"],
                "interpretation": scenario["interpretation"],
                "alpha_co": scenario["selectivity"]["CO"],
                "alpha_co2": scenario["selectivity"]["CO2"],
                "alpha_n2": scenario["selectivity"]["N2"],
                "alpha_ch4": scenario["selectivity"]["CH4"],
                "pass_count": summary["pass_count"],
                "case_count": summary["case_count"],
                "all_pass": summary["all_pass"],
                "minimum_recovery": summary["minimum_recovery"],
                "minimum_qualified_h2_rate_mol_s": summary["minimum_qualified_h2_rate_mol_s"],
                "maximum_co_ppm": summary["maximum_co_ppm"],
                "maximum_co2_ppm": summary["maximum_co2_ppm"],
                "maximum_n2_ppm": summary["maximum_n2_ppm"],
                "maximum_ch4_ppm": summary["maximum_ch4_ppm"],
                "receiver_capacity_mol": receiver,
            }
        )
        for row in rows:
            all_case_rows.append({"scenario_id": scenario["scenario_id"], **row})

    write_csv(OUT / "Table_component_selectivity_acceptance.csv", threshold_rows)
    write_csv(OUT / "Table_public_selectivity_stress_summary.csv", scenario_rows)
    write_csv(OUT / "Table_public_selectivity_stress_direct_cases.csv", all_case_rows)

    labels = [row["impurity"] for row in threshold_rows]
    minimums = [row["minimum_effective_selectivity"] for row in threshold_rows]
    guards = [row["guard_banded_selectivity_1p25x"] for row in threshold_rows]
    selected_values = [row["selected_effective_selectivity"] for row in threshold_rows]
    x = list(range(len(labels)))
    width = 0.24
    fig, ax = plt.subplots(figsize=(9.2, 5.1))
    ax.bar([v - width for v in x], minimums, width, label="Minimum", color="#b83280")
    ax.bar(x, guards, width, label="1.25x acceptance guard", color="#dd6b20")
    ax.bar([v + width for v in x], selected_values, width, label="Selected", color="#2b6cb0")
    ax.set_yscale("log")
    ax.set_xticks(x, labels)
    ax.set_ylabel("Effective H2/impurity selectivity (log scale)")
    ax.set_title("Component-specific Pd-module acceptance threshold\n0.887 m2, 50% permeance retention, 16 direct cases")
    ax.grid(axis="y", which="both", alpha=0.25)
    ax.legend(frameon=False)
    fig.tight_layout()
    figure = OUT / "Fig_public_selectivity_acceptance_audit_v1.png"
    fig.savefig(figure, dpi=300, bbox_inches="tight")
    plt.close(fig)

    result = {
        "schema": "psa-public-selectivity-acceptance-audit/v1",
        "status": "component_acceptance_threshold_and_public_stress_completed",
        "design": {
            "pd_area_m2": AREA_M2,
            "permeance_retention": RETENTION,
            "case_count": len(cases),
            "selected_effective_selectivity": selected,
            "baseline_receiver_capacity_mol": baseline_receiver,
            "baseline_summary": baseline_summary,
            "simultaneous_guard_vector": guard_vector,
            "rounded_procurement_acceptance_vector": procurement_vector,
        },
        "component_acceptance_thresholds": threshold_rows,
        "public_stress_scenarios": scenario_rows,
        "sources": [
            {
                "citation": "Li et al., Energy Procedia 4 (2011) 666-673",
                "doi": "10.1016/j.egypro.2011.01.103",
                "scope": "20-35 bara, 673 K, five-component WGS feed; N2 ideal-selectivity transfer only",
            },
            {
                "citation": "Media and Process Technology Inc., DOE DE-FG36-04GO14330 (2005)",
                "url": "https://www.osti.gov/servlets/purl/883041",
                "scope": "single-component supported-Pd permeance at 400 C and 30/60 psig",
            },
            {
                "citation": "DOE final report OSTI 898816",
                "url": "https://www.osti.gov/servlets/purl/898816",
                "scope": "pure-Pd H2/N2 selectivity lower bound; not a mixed-gas product certificate",
            },
        ],
        "decision": {
            "engineering_use": "Specify component-resolved acceptance selectivities and reject defect-leaking Pd modules before plant integration.",
            "claim_boundary": "The threshold is model-derived for the frozen PSA/polymer/Pd train. Literature values are transfer stresses and do not replace synchronized multicomponent permeate measurements.",
        },
    }
    json_path = OUT / "PSA_PUBLIC_SELECTIVITY_ACCEPTANCE_AUDIT_V1.json"
    json_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    threshold_text = "\n".join(
        f"- {row['impurity']}: minimum {row['minimum_effective_selectivity']:.1f}; "
        f"1.25x guard {row['guard_banded_selectivity_1p25x']:.1f}; "
        f"selected {row['selected_effective_selectivity']:.1f}."
        for row in threshold_rows
    )
    stress_text = "\n".join(
        f"- {row['scenario_id']}: {row['pass_count']}/{row['case_count']} pass; "
        f"max CO/CO2/N2/CH4 = {row['maximum_co_ppm']:.3f}/"
        f"{row['maximum_co2_ppm']:.3f}/{row['maximum_n2_ppm']:.3f}/"
        f"{row['maximum_ch4_ppm']:.3f} ppm."
        for row in scenario_rows
    )
    md_path = OUT / "PSA_PUBLIC_SELECTIVITY_ACCEPTANCE_AUDIT_V1.md"
    md_path.write_text(
        "# Public selectivity acceptance audit\n\n"
        "The final 0.887-m2 design was replayed over all 16 direct cases while each impurity selectivity was reduced independently.\n\n"
        "## Component thresholds\n\n" + threshold_text +
        "\n\n## Public stress cases\n\n" + stress_text +
        "\n\nThese values define a model-based incoming-module acceptance test. They are not experimental certification of a commercial module.\n",
        encoding="utf-8",
    )

    files = [
        json_path,
        md_path,
        OUT / "Table_component_selectivity_acceptance.csv",
        OUT / "Table_public_selectivity_stress_summary.csv",
        OUT / "Table_public_selectivity_stress_direct_cases.csv",
        figure,
    ]
    manifest = {
        "schema": "psa-public-selectivity-acceptance-audit-manifest/v1",
        "files": [
            {"path": str(path.relative_to(ROOT)), "bytes": path.stat().st_size, "sha256": sha256(path)}
            for path in files
        ],
    }
    (OUT / "MANIFEST_SHA256.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps({"thresholds": threshold_rows, "scenarios": scenario_rows}, indent=2))


if __name__ == "__main__":
    main()
