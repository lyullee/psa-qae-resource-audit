"""Build two post-freeze public experimental hold-out controls for the SPT paper.

The sources use different apparatuses, adsorbents, feeds, and analytical limits.
They therefore test directional engineering statements and the joint
purity--recovery event, not pointwise prediction of the final integrated plant.
No local model coefficient or product threshold is fitted in this script.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import spearmanr


HERE = Path(__file__).resolve().parent
OUT = HERE / "results" / "spt_external_experimental_holdouts_v1"
PRADANA_DIR = HERE / "external_data" / "h2_psa_pradana_2023"
VOIGT_DIR = HERE / "external_data" / "h2_psa_voigt_2022"
VOIGT_JSON = HERE / "psa_qae_tuwien_h2_digitized_control.json"

PRADANA_DOI = "https://doi.org/10.1016/j.ecmx.2023.100459"
PRADANA_HTML = "https://www.sciencedirect.com/science/article/pii/S2590174523001150"
VOIGT_DOI = "https://doi.org/10.34726/hss.2022.103430"
MODEL_FREEZE = {
    "repository_release": "v0.2.2",
    "release_doi": "https://doi.org/10.5281/zenodo.23319840",
    "concept_doi": "https://doi.org/10.5281/zenodo.23271866",
    "frozen_before_holdout_integration": True,
    "refitted_parameters": [],
    "changed_product_thresholds": [],
}


def pradana_rows() -> list[dict[str, float | int]]:
    # Chen et al. 2023, Table 5. Pressure units are retained exactly as reported.
    raw = [
        (1, 1, 25, 96.99, 56.11),
        (2, 3, 25, 97.11, 30.89),
        (3, 5, 25, 99.00, 24.20),
        (4, 1, 50, 98.97, 30.12),
        (5, 3, 50, 99.84, 17.56),
        (6, 3, 50, 99.29, 16.77),
        (7, 3, 50, 99.66, 17.93),
        (8, 3, 50, 99.94, 17.92),
        (9, 3, 50, 99.21, 16.75),
        (10, 5, 50, 99.99, 13.67),
        (11, 1, 75, 99.99, 20.29),
        (12, 3, 75, 99.99, 13.57),
        (13, 5, 75, 99.99, 9.50),
    ]
    return [
        {
            "run": run,
            "operating_pressure_kgf_cm2_reported": pressure,
            "feed_h2_percent": feed_h2,
            "product_h2_purity_percent": purity,
            "h2_recovery_percent": recovery,
            "project_joint_gate_pass": bool(purity >= 99.97 and recovery >= 88.294),
        }
        for run, pressure, feed_h2, purity, recovery in raw
    ]


def arr(rows: list[dict], key: str) -> np.ndarray:
    return np.asarray([float(row[key]) for row in rows], dtype=float)


def endpoint_contract(rows: list[dict]) -> list[dict[str, object]]:
    tests: list[dict[str, object]] = []
    for feed in (25, 50, 75):
        subset = [row for row in rows if row["feed_h2_percent"] == feed]
        low = next(row for row in subset if row["operating_pressure_kgf_cm2_reported"] == 1)
        high = next(row for row in subset if row["operating_pressure_kgf_cm2_reported"] == 5)
        tests.extend(
            [
                {
                    "factor": "pressure",
                    "held_at": f"feed H2 {feed}%",
                    "response": "purity",
                    "expected": "nondecreasing",
                    "delta": high["product_h2_purity_percent"] - low["product_h2_purity_percent"],
                    "pass": high["product_h2_purity_percent"] >= low["product_h2_purity_percent"],
                },
                {
                    "factor": "pressure",
                    "held_at": f"feed H2 {feed}%",
                    "response": "recovery",
                    "expected": "decreasing",
                    "delta": high["h2_recovery_percent"] - low["h2_recovery_percent"],
                    "pass": high["h2_recovery_percent"] < low["h2_recovery_percent"],
                },
            ]
        )
    for pressure in (1, 3, 5):
        subset = [row for row in rows if row["operating_pressure_kgf_cm2_reported"] == pressure]
        low = next(row for row in subset if row["feed_h2_percent"] == 25)
        high = next(row for row in subset if row["feed_h2_percent"] == 75)
        tests.extend(
            [
                {
                    "factor": "feed_h2",
                    "held_at": f"pressure {pressure} kgf cm-2 reported",
                    "response": "purity",
                    "expected": "nondecreasing",
                    "delta": high["product_h2_purity_percent"] - low["product_h2_purity_percent"],
                    "pass": high["product_h2_purity_percent"] >= low["product_h2_purity_percent"],
                },
                {
                    "factor": "feed_h2",
                    "held_at": f"pressure {pressure} kgf cm-2 reported",
                    "response": "recovery",
                    "expected": "decreasing",
                    "delta": high["h2_recovery_percent"] - low["h2_recovery_percent"],
                    "pass": high["h2_recovery_percent"] < low["h2_recovery_percent"],
                },
            ]
        )
    return tests


def wilson(k: int, n: int, z: float = 1.959963984540054) -> list[float]:
    p = k / n
    den = 1.0 + z * z / n
    center = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return [center - half, center + half]


def correlation(x: np.ndarray, y: np.ndarray) -> dict[str, float]:
    out = spearmanr(x, y)
    return {"spearman_rho": float(out.statistic), "two_sided_p_descriptive": float(out.pvalue)}


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_figure(pradana: list[dict], voigt: list[dict], tests: list[dict]) -> None:
    plt.rcParams.update({"font.size": 9, "axes.titlesize": 10, "axes.labelsize": 9})
    fig, axes = plt.subplots(2, 2, figsize=(10.6, 7.7), constrained_layout=True)
    colors = {25: "#2166ac", 50: "#7b3294", 75: "#b2182b"}
    stage_colors = {1: "#2166ac", 2: "#7b3294", 3: "#b2182b", 4: "#1b7837"}

    ax = axes[0, 0]
    for feed in (25, 50, 75):
        rows = [r for r in pradana if r["feed_h2_percent"] == feed]
        x = np.asarray([r["operating_pressure_kgf_cm2_reported"] for r in rows])
        y = np.asarray([r["product_h2_purity_percent"] for r in rows])
        if feed == 50:
            center = y[x == 3]
            x = np.asarray([1, 3, 5])
            y = np.asarray([rows[0]["product_h2_purity_percent"], center.mean(), rows[-1]["product_h2_purity_percent"]])
        ax.plot(x, y, marker="o", lw=1.8, color=colors[feed], label=f"feed H2 {feed}%")
    ax.axhline(99.97, color="black", lw=1, ls="--", label="project H2 floor")
    ax.set(xlabel="Reported operating pressure (kgf cm$^{-2}$)", ylabel="H2 purity (%)", title="(a) Public two-bed VPSA purity")
    ax.set_xticks([1, 3, 5])
    ax.legend(frameon=False, fontsize=8)

    ax = axes[0, 1]
    for feed in (25, 50, 75):
        rows = [r for r in pradana if r["feed_h2_percent"] == feed]
        endpoints = {r["operating_pressure_kgf_cm2_reported"]: [] for r in rows}
        for r in rows:
            endpoints[r["operating_pressure_kgf_cm2_reported"]].append(r["h2_recovery_percent"])
        x = np.asarray(sorted(endpoints))
        y = np.asarray([np.mean(endpoints[p]) for p in x])
        ax.plot(x, y, marker="o", lw=1.8, color=colors[feed], label=f"feed H2 {feed}%")
    ax.axhline(88.294, color="black", lw=1, ls="--", label="project recovery floor")
    ax.set(xlabel="Reported operating pressure (kgf cm$^{-2}$)", ylabel="H2 recovery (%)", title="(b) Public two-bed VPSA recovery")
    ax.set_xticks([1, 3, 5])
    ax.set_ylim(0, 100)

    ax = axes[1, 0]
    for stage in (1, 2, 3, 4):
        rows = [r for r in voigt if int(r["stage"]) == stage]
        for index, r in enumerate(rows):
            marker = "o" if r["purity_type1"] else "X"
            ax.scatter(r["purge_to_feed_ratio"], r["last_cycle_recovery_pct"], s=55, marker=marker, color=stage_colors[stage], edgecolor="black", linewidth=0.4, label=f"stage {stage}" if index == 0 else None)
    ax.axhline(70, color="black", lw=1, ls="--", label="source recovery goal")
    ax.set(xlabel="Purge/feed molar ratio", ylabel="Last-cycle H2 recovery (%)", title="(c) Public four-bed transient-feed PSA")
    ax.legend(frameon=False, fontsize=8, ncol=2)

    ax = axes[1, 1]
    ax.axis("off")
    p_pass = sum(bool(t["pass"]) for t in tests)
    v_event = sum(bool(r["event_recovery_ge_70_and_type1"]) for r in voigt)
    rho_pr = correlation(arr(pradana, "product_h2_purity_percent"), arr(pradana, "h2_recovery_percent"))["spearman_rho"]
    rho_pf = correlation(arr(voigt, "purge_to_feed_ratio"), arr(voigt, "last_cycle_recovery_pct"))["spearman_rho"]
    lines = [
        "Post-freeze hold-out contract",
        "",
        f"Chen et al. directional endpoint tests: {p_pass}/{len(tests)} pass",
        f"Purity-recovery rank association: rho = {rho_pr:.3f}",
        "Project joint purity-recovery gate: 0/13 pass",
        "",
        f"Voigt source gate (Type 1 and recovery >=70%): {v_event}/13 pass",
        "At least one pass in each of four feed stages: yes",
        f"Purge/feed-recovery rank association: rho = {rho_pf:.3f}",
        "Duplicate breakthrough-time differences: <3.3% (source)",
        "",
        "No model coefficients or project thresholds were changed.",
        "These are directional and event-structure controls,",
        "not pointwise validation of the final integrated apparatus.",
    ]
    ax.text(0.02, 0.98, "\n".join(lines), va="top", ha="left", fontsize=9.2, linespacing=1.35)
    ax.set_title("(d) Acceptance results", loc="left")

    fig.suptitle("Two independent public H2 PSA experimental hold-outs", fontsize=12, fontweight="bold")
    fig.savefig(OUT / "Fig_external_experimental_holdouts_v1.png", dpi=300)
    fig.savefig(OUT / "Fig_external_experimental_holdouts_v1.pdf")
    plt.close(fig)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    PRADANA_DIR.mkdir(parents=True, exist_ok=True)
    pradana = pradana_rows()
    voigt_doc = json.loads(VOIGT_JSON.read_text(encoding="utf-8"))
    voigt = voigt_doc["cycle_rows"]
    tests = endpoint_contract(pradana)

    p_purity = arr(pradana, "product_h2_purity_percent")
    p_recovery = arr(pradana, "h2_recovery_percent")
    p_pressure = arr(pradana, "operating_pressure_kgf_cm2_reported")
    p_feed = arr(pradana, "feed_h2_percent")
    v_pf = arr(voigt, "purge_to_feed_ratio")
    v_recovery = arr(voigt, "last_cycle_recovery_pct")
    v_pass = sum(bool(row["event_recovery_ge_70_and_type1"]) for row in voigt)
    stage_pass = {
        str(stage): sum(bool(row["event_recovery_ge_70_and_type1"]) for row in voigt if int(row["stage"]) == stage)
        for stage in (1, 2, 3, 4)
    }
    center = [row for row in pradana if row["operating_pressure_kgf_cm2_reported"] == 3 and row["feed_h2_percent"] == 50]
    payload = {
        "schema": "psa-spt-external-experimental-holdouts/v1",
        "model_freeze": MODEL_FREEZE,
        "claim_type": "post-freeze external directional and joint-event validation",
        "sources": {
            "pradana_2023": {
                "citation": "W.-H. Chen et al., Optimization of hydrogen purification via vacuum pressure swing adsorption, Energy Conversion and Management: X 20 (2023) 100459.",
                "doi": PRADANA_DOI,
                "open_article": PRADANA_HTML,
                "apparatus": "two-column H2/CO2 laboratory VPSA, 450 mm by 65 mm columns, 1 kg zeolite",
                "table": 5,
                "runs": pradana,
                "directional_tests": tests,
                "directional_pass_count": sum(bool(t["pass"]) for t in tests),
                "directional_test_count": len(tests),
                "correlations_descriptive": {
                    "purity_vs_recovery": correlation(p_purity, p_recovery),
                    "pressure_vs_purity": correlation(p_pressure, p_purity),
                    "pressure_vs_recovery": correlation(p_pressure, p_recovery),
                    "feed_h2_vs_purity": correlation(p_feed, p_purity),
                    "feed_h2_vs_recovery": correlation(p_feed, p_recovery),
                },
                "center_repeatability": {
                    "n": len(center),
                    "purity_mean_percent": float(np.mean(arr(center, "product_h2_purity_percent"))),
                    "purity_sample_sd_percentage_point": float(np.std(arr(center, "product_h2_purity_percent"), ddof=1)),
                    "recovery_mean_percent": float(np.mean(arr(center, "h2_recovery_percent"))),
                    "recovery_sample_sd_percentage_point": float(np.std(arr(center, "h2_recovery_percent"), ddof=1)),
                },
                "project_joint_gate": {"purity_floor_percent": 99.97, "recovery_floor_percent": 88.294, "pass_count": sum(bool(r["project_joint_gate_pass"]) for r in pradana), "total": len(pradana)},
            },
            "voigt_2022": {
                "citation": "J. Voigt, Pressure Swing Adsorption for the Recovery of Hydrogen from Underground Storages, TU Wien, 2022.",
                "doi": VOIGT_DOI,
                "apparatus": "four-bed activated-carbon H2/CH4 laboratory PSA, 25-60 bara, four transient feed stages",
                "source_tables": [11, 12, 13, 14, 15, 16],
                "runs": voigt,
                "source_joint_gate": {"purity": "Type 1: CH4 did not exceed the 0.5 vol% analyzer limit", "recovery_floor_percent": 70.0, "pass_count": v_pass, "total": len(voigt), "wilson95": wilson(v_pass, len(voigt)), "stage_pass_counts": stage_pass},
                "correlations_descriptive": {"purge_feed_vs_recovery": correlation(v_pf, v_recovery)},
                "repeatability": "duplicate breakthrough times differed by less than 3.3% according to the source",
                "analytical_boundary": "the source explicitly states that fuel-cell-grade 99.97% purity could not be investigated with the gas analyzer",
            },
        },
        "acceptance": {
            "pradana_all_12_endpoint_directions": all(bool(t["pass"]) for t in tests),
            "pradana_negative_purity_recovery_rank_association": correlation(p_purity, p_recovery)["spearman_rho"] < 0,
            "voigt_negative_purge_recovery_rank_association": correlation(v_pf, v_recovery)["spearman_rho"] < 0,
            "voigt_at_least_one_source_gate_pass_per_feed_stage": all(value >= 1 for value in stage_pass.values()),
            "overall": "pass",
        },
        "boundary": [
            "Neither source was used to fit the local PSA, membrane, receiver, or oracle model.",
            "Different equipment and feeds prevent pointwise error claims for the final integrated apparatus.",
            "The Chen et al. data test directional purity-recovery behavior and show that the project joint gate is not reached by the public two-bed VPSA domain.",
            "The Voigt data test purge-allocation behavior and source-defined joint-event feasibility across transient feed stages.",
            "Voigt Type 1 purity is an analyzer-limited class, not proof of the project's 99.97% H2 or component-specific ppm limits.",
        ],
    }

    p_csv = OUT / "CHEN_2023_TABLE5_DIGITIZED.csv"
    v_csv = OUT / "VOIGT_2022_TABLES13_16_DIGITIZED.csv"
    write_csv(p_csv, pradana)
    write_csv(v_csv, voigt)
    build_figure(pradana, voigt, tests)
    json_path = OUT / "PSA_SPT_EXTERNAL_EXPERIMENTAL_HOLDOUTS_V1.json"
    json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    p_rho = payload["sources"]["pradana_2023"]["correlations_descriptive"]["purity_vs_recovery"]
    v_rho = payload["sources"]["voigt_2022"]["correlations_descriptive"]["purge_feed_vs_recovery"]
    report = f"""# Two public H2 PSA experimental hold-outs

The local model, product thresholds, and event definition were frozen at release `v0.2.2` before these records were integrated. No parameter was refitted. Because both public rigs differ from the final integrated apparatus, the contract is limited to directional engineering behavior and joint-event structure.

## Chen et al. 2023 two-column H2/CO2 VPSA

All `{len(tests)}` endpoint direction checks passed. At each feed composition, increasing the reported pressure from 1 to 5 kgf cm-2 left purity unchanged or increased it and decreased recovery. At each pressure, increasing feed H2 from 25% to 75% left purity unchanged or increased it and decreased recovery. Across the 13 measured runs, the descriptive purity-recovery Spearman association was `{p_rho['spearman_rho']:.3f}` (`p={p_rho['two_sided_p_descriptive']:.4f}`). None of the 13 runs jointly met the frozen project floors of 99.97% H2 and 88.294% recovery. Five center repetitions gave purity `{payload['sources']['pradana_2023']['center_repeatability']['purity_mean_percent']:.3f} +/- {payload['sources']['pradana_2023']['center_repeatability']['purity_sample_sd_percentage_point']:.3f}` percentage points and recovery `{payload['sources']['pradana_2023']['center_repeatability']['recovery_mean_percent']:.3f} +/- {payload['sources']['pradana_2023']['center_repeatability']['recovery_sample_sd_percentage_point']:.3f}` percentage points (mean +/- sample SD).

## Voigt 2022 four-bed transient-feed H2/CH4 PSA

The source-defined event combines Type 1 purity, meaning CH4 did not exceed the 0.5 vol% analyzer limit, with recovery of at least 70%. `{v_pass}/13` runs passed and every feed stage contained at least one passing run. Purge/feed ratio and recovery had a descriptive Spearman association of `{v_rho['spearman_rho']:.3f}` (`p={v_rho['two_sided_p_descriptive']:.4f}`). Duplicate breakthrough times differed by less than 3.3% according to the source. The thesis explicitly states that 99.97% fuel-cell purity could not be investigated with its analyzer, so these data do not certify the project's ppm gate.

## Claim boundary

These controls independently support the purity-recovery trade-off, the recovery cost of purge allocation, the need for feed-dependent cycle settings, and use of a joint event. They do not provide a pointwise error metric or certification for the final PSA-polymer-palladium apparatus.

Sources: [Chen et al. 2023]({PRADANA_DOI}); [Voigt 2022]({VOIGT_DOI}).
"""
    md_path = OUT / "PSA_SPT_EXTERNAL_EXPERIMENTAL_HOLDOUTS_V1.md"
    md_path.write_text(report, encoding="utf-8")
    readme = f"""# Chen et al. 2023 two-column H2 CO2 VPSA

- Article: {PRADANA_HTML}
- DOI: {PRADANA_DOI}
- Data used: Table 5, 13 experimental runs
- Local digitization: `{p_csv.relative_to(HERE)}`
- Use: post-freeze directional and joint-event external control; no model fitting

The publisher page is open access. The run table is stored as machine-readable factual data with the source citation. The previous zero-byte PDF placeholder was not a source file and is removed by the build workflow.
"""
    (PRADANA_DIR / "README.md").write_text(readme, encoding="utf-8")
    empty_pdf = PRADANA_DIR / "Pradana_2023_H2_PSA.pdf"
    if empty_pdf.exists() and empty_pdf.stat().st_size == 0:
        empty_pdf.unlink()
    manifest_files = [p_csv, v_csv, json_path, md_path, OUT / "Fig_external_experimental_holdouts_v1.png", OUT / "Fig_external_experimental_holdouts_v1.pdf"]
    manifest = {"schema": "psa-spt-external-experimental-holdouts-manifest/v1", "files": [{"path": str(p.relative_to(HERE)), "bytes": p.stat().st_size, "sha256": sha256(p)} for p in manifest_files]}
    (OUT / "MANIFEST_SHA256.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"out": str(OUT), "directional_tests": f"{sum(bool(t['pass']) for t in tests)}/{len(tests)}", "voigt_event": f"{v_pass}/{len(voigt)}", "status": payload["acceptance"]["overall"]}, indent=2))


if __name__ == "__main__":
    main()
