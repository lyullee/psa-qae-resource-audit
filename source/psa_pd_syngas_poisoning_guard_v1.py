"""Size the Pd stage against public actual-syngas permeance-loss evidence.

Guazzone et al. reported a 40--50% H2-permeance decrease when large Pd and Pd--Au
membranes were exposed to actual desulfurized coal syngas
(doi:10.1021/ef302130s).  The previously frozen design guarded a 20% loss.
This audit keeps the same finite-selectivity transport law and sizes installed
area at 100, 80, 60, and 50% permeance retention.  It therefore tests the
engineering consequence of the public loss range without claiming that the
literature apparatus is a matched validation of the present five-component
train.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import os
from pathlib import Path

import matplotlib.pyplot as plt

import psa_independent_ode_membrane_audit as ode
import psa_public_schedule_strict_uncertainty_ensemble as strict


ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"
SOURCE = RESULTS / os.environ.get("PSA_SYNGAS_ODE_DIR", "independent_ode_membrane_audit") / "PSA_INDEPENDENT_ODE_MEMBRANE_AUDIT.json"
V22 = RESULTS / "final_objective_evidence_v22" / "PSA_FINAL_OBJECTIVE_EVIDENCE_V22.json"
OUT = RESULTS / os.environ.get("PSA_SYNGAS_OUTPUT_DIR", "pd_actual_syngas_poisoning_guard_v1")
RETENTIONS = (1.0, 0.8, 0.6, 0.5)


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
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    v22 = json.loads(V22.read_text(encoding="utf-8"))
    decision = v22["primary_engineering_decision"]
    recovery_floor = float(decision["minimum_h2_recovery"])
    shipment_floor = float(decision["minimum_qualified_h2_rate_mol_s"])
    gate = strict.strict_gate(strict.load_contract())
    selectivity = {
        key: float(value)
        for key, value in source["revised_guard_design"]["selected_effective_selectivity"].items()
    }

    cases = ode.case_data()
    for case in cases:
        product, _retentate, info = ode.integrate_polymer(
            case["surge_outlet_mol"], case["packet_duration_s"]
        )
        case["ode_stage1_product_mol"] = product
        case["ode_stage1_balance"] = float(info["mass_balance_max_abs_mol"])

    def evaluate(area_m2: float, retention: float):
        products = []
        balances = []
        for case in cases:
            product, _retentate, info = ode.integrate_pd(
                case["ode_stage1_product_mol"],
                case["packet_duration_s"],
                area_m2=area_m2,
                retention=retention,
                selectivity=selectivity,
            )
            products.append(product)
            balances.append(max(case["ode_stage1_balance"], info["mass_balance_max_abs_mol"]))
        rows, receiver = ode.receiver_rows(
            cases,
            products,
            area_m2=area_m2,
            retention=retention,
            recovery_floor=recovery_floor,
            shipment_floor=shipment_floor,
            gate=gate,
            module_balances=balances,
        )
        return rows, receiver, ode.summarize(rows, receiver)

    def performance_pass(rows: list[dict]) -> bool:
        return all(
            row["overall_h2_recovery"] >= recovery_floor
            and row["qualified_h2_rate_mol_s"] >= shipment_floor
            and row["receiver_inventory_gate"]
            for row in rows
        )

    # With the declared transport equations, area and permeance retention enter
    # as their product.  Find the required effective area once, then verify every
    # installed-area design by direct adaptive-ODE replay.
    low, high = 0.1, 0.8
    high_rows, _high_receiver, _high_summary = evaluate(high, 1.0)
    if not performance_pass(high_rows):
        raise AssertionError("effective-area upper bound does not pass")
    for _ in range(38):
        mid = 0.5 * (low + high)
        rows, _receiver, _summary = evaluate(mid, 1.0)
        if performance_pass(rows):
            high = mid
        else:
            low = mid
    minimum_effective_area = high

    summary_rows: list[dict] = []
    case_rows_50: list[dict] = []
    for retention in RETENTIONS:
        unrounded = minimum_effective_area / retention
        installed = math.ceil(unrounded * 1000.0) / 1000.0
        rows, receiver, summary = evaluate(installed, retention)
        if not summary["all_pass"]:
            raise AssertionError(f"retention={retention:.3f} direct replay did not pass")
        summary_rows.append(
            {
                "permeance_retention": retention,
                "permeance_loss_percent": 100.0 * (1.0 - retention),
                "minimum_unrounded_installed_area_m2": unrounded,
                "selected_rounded_installed_area_m2": installed,
                "area_increase_vs_0p554_percent": 100.0 * (installed / 0.554 - 1.0),
                "effective_area_m2": installed * retention,
                "pass_count": summary["pass_count"],
                "case_count": summary["case_count"],
                "minimum_overall_h2_recovery": summary["minimum_recovery"],
                "minimum_qualified_h2_rate_mol_s": summary["minimum_qualified_h2_rate_mol_s"],
                "receiver_capacity_mol": receiver,
                "receiver_volume_L_at_1bar_298K": receiver
                * ode.train.R_J_MOL_K
                * ode.train.COMPRESSION_T_K
                / ode.train.PD_PERMEATE_PRESSURE_PA
                * 1000.0,
                "maximum_co_ppm": summary["maximum_co_ppm"],
                "maximum_co2_ppm": summary["maximum_co2_ppm"],
                "maximum_n2_ppm": summary["maximum_n2_ppm"],
                "maximum_ch4_ppm": summary["maximum_ch4_ppm"],
                "maximum_module_mass_balance_abs_mol": summary["maximum_module_mass_balance_abs_mol"],
                "maximum_receiver_mass_balance_abs_mol": summary["maximum_receiver_mass_balance_abs_mol"],
            }
        )
        if retention == 0.5:
            case_rows_50 = rows

    write_csv(OUT / "Table_pd_actual_syngas_permeance_guard.csv", summary_rows)
    write_csv(OUT / "Table_pd_50pct_retention_direct_cases.csv", case_rows_50)

    fig, axes = plt.subplots(1, 2, figsize=(10.8, 4.3))
    loss = [row["permeance_loss_percent"] for row in summary_rows]
    area = [row["selected_rounded_installed_area_m2"] for row in summary_rows]
    recovery = [100.0 * row["minimum_overall_h2_recovery"] for row in summary_rows]
    axes[0].plot(loss, area, "o-", color="#2b6cb0", linewidth=2.2)
    axes[0].axvspan(40, 50, color="#f6ad55", alpha=0.22, label="Actual-syngas loss range")
    axes[0].axhline(0.554, color="#555", linestyle="--", linewidth=1.2, label="20% guard design")
    axes[0].set(xlabel="Pd permeance loss (%)", ylabel="Required installed Pd area (m$^2$)")
    axes[0].grid(alpha=0.25)
    axes[0].legend(frameon=False, fontsize=8)
    axes[1].plot(loss, recovery, "s-", color="#2f855a", linewidth=2.2)
    axes[1].axhline(100.0 * recovery_floor, color="#b83280", linestyle="--", linewidth=1.2, label="Frozen recovery floor")
    axes[1].set(xlabel="Pd permeance loss (%)", ylabel="Minimum overall H$_2$ recovery (%)")
    axes[1].grid(alpha=0.25)
    axes[1].legend(frameon=False, fontsize=8)
    fig.suptitle("Pd installed-area guard against public actual-syngas permeance loss", fontsize=11)
    fig.tight_layout()
    figure = OUT / "Fig_pd_actual_syngas_poisoning_guard_v1.png"
    fig.savefig(figure, dpi=300, bbox_inches="tight")
    plt.close(fig)

    worst = summary_rows[-1]
    result = {
        "schema": "psa-pd-actual-syngas-poisoning-guard/v1",
        "status": "public_actual_syngas_permeance_loss_guard_completed",
        "literature_anchor": {
            "citation": "Guazzone et al., Energy & Fuels 27 (2013) 4150-4160",
            "doi": "10.1021/ef302130s",
            "apparatus": "200 cm2 Pd and Pd-Au membranes in actual desulfurized coal-derived syngas",
            "reported_h2_purity_percent": [99.8, 99.9],
            "reported_h2_permeance_loss_percent": [40.0, 50.0],
            "reported_pd_au_stable_exposure_h": 473.0,
        },
        "model_contract": {
            "solver": "scipy solve_ivp DOP853",
            "case_count": len(cases),
            "transport_law": "same finite-selectivity Pd law as the independent ODE audit",
            "selected_effective_selectivity": selectivity,
            "minimum_effective_pd_area_m2": minimum_effective_area,
            "rounding": "installed area rounded upward to 0.001 m2",
        },
        "retention_designs": summary_rows,
        "conservative_50_percent_retention_design": worst,
        "claim_boundary": {
            "supported": "A 50% permeance-retention design directly passes all 16 frozen uncertainty and hold-out cases under the same adaptive finite-selectivity model.",
            "not_supported": "The public coal-syngas experiment is not a matched validation of the present feed, module, four impurity detection limits, or long-term plant control.",
        },
    }
    json_path = OUT / "PSA_PD_ACTUAL_SYNGAS_POISONING_GUARD_V1.json"
    json_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    md_path = OUT / "PSA_PD_ACTUAL_SYNGAS_POISONING_GUARD_V1.md"
    md_path.write_text(
        "\n".join(
            [
                "# Pd actual-syngas permeance-loss guard",
                "",
                "The public actual-coal-syngas experiment reports a 40--50% H2-permeance loss.",
                f"The conservative 50% retention design requires **{worst['selected_rounded_installed_area_m2']:.3f} m2** Pd area.",
                f"It passes **{worst['pass_count']}/{worst['case_count']}** direct cases with minimum recovery **{100.0*worst['minimum_overall_h2_recovery']:.3f}%**.",
                f"The required area is **{worst['area_increase_vs_0p554_percent']:.1f}%** above the prior 0.554-m2 20%-loss guard.",
                "",
                "This is a literature-anchored degradation stress test, not matched experimental validation.",
            ]
        ) + "\n",
        encoding="utf-8",
    )
    files = [
        json_path,
        md_path,
        OUT / "Table_pd_actual_syngas_permeance_guard.csv",
        OUT / "Table_pd_50pct_retention_direct_cases.csv",
        figure,
    ]
    manifest = {
        "schema": "psa-pd-actual-syngas-poisoning-guard-manifest/v1",
        "files": [
            {
                "path": str(path.relative_to(ROOT)),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
            for path in files
        ],
    }
    (OUT / "MANIFEST_SHA256.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps({"output": str(json_path), "design": worst}, indent=2))


if __name__ == "__main__":
    main()
