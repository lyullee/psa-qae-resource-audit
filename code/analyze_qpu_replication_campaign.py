"""Aggregate the frozen 3-backend x 3-seed IBM QPU replication campaign.

The default command is safe on an incomplete campaign: it inventories only
completed real-QPU artifacts and writes an explicitly incomplete audit.  Pass
``--require-complete`` for the manuscript-grade analysis gate.  This script
never connects to IBM Quantum and never submits a workload.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import t as student_t

from qpu_breakthrough_phase_mlae import EXACT_PROBABILITY, POWERS, expected_probability


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = ROOT / "10_TEA_LCA_Python" / "results" / "pycharm_publication_enhancement"
BACKENDS = ("ibm_marrakesh", "ibm_fez", "ibm_kingston")
SEEDS = (20261009, 20261010, 20261011)
SHOTS = 4096
BOOTSTRAP_REPLICATES = 100_000
BOOTSTRAP_SEED = 20261009
STEM = "PSA_QAE_QPU_REPLICATION_CAMPAIGN_ANALYSIS"


def _load_completed() -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    planned: list[dict[str, object]] = []
    legacy: list[dict[str, object]] = []
    pattern = "QAE_QPU_BREAKTHROUGH_PHASE_MLAE_IBM_*.json"
    for path in sorted(OUT.glob(pattern)):
        if "PREFLIGHT" in path.name:
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if payload.get("status") != "real_qpu_completed":
            continue
        payload["_source_file"] = path.name
        seed = payload.get("transpiler_seed")
        backend = payload.get("backend")
        if backend in BACKENDS and seed in SEEDS:
            planned.append(payload)
        else:
            legacy.append(payload)
    return planned, legacy


def _validate_and_rows(payloads: list[dict[str, object]]) -> tuple[list[dict[str, object]], list[str]]:
    rows: list[dict[str, object]] = []
    errors: list[str] = []
    seen: dict[tuple[str, int], str] = {}
    for payload in payloads:
        backend = str(payload.get("backend"))
        seed = int(payload.get("transpiler_seed"))
        key = (backend, seed)
        source = str(payload["_source_file"])
        if key in seen:
            errors.append(f"duplicate completed cell {key}: {seen[key]} and {source}")
            continue
        seen[key] = source
        if payload.get("verified_plan") != "open":
            errors.append(f"{source}: verified_plan is not open")
        if payload.get("dry_run") is not False:
            errors.append(f"{source}: dry_run is not false")
        if [int(x) for x in payload.get("powers", [])] != list(POWERS):
            errors.append(f"{source}: Grover powers differ from the frozen plan")
        if int(payload.get("shots_per_power", -1)) != SHOTS:
            errors.append(f"{source}: shots_per_power differs from {SHOTS}")
        if not math.isclose(float(payload.get("exact_probability", math.nan)), EXACT_PROBABILITY, abs_tol=1e-12):
            errors.append(f"{source}: exact probability differs from {EXACT_PROBABILITY}")

        estimate = payload.get("estimate", {})
        metrics = payload.get("runtime_metrics", {})
        usage = metrics.get("usage", {}) if isinstance(metrics, dict) else {}
        good = [int(x) for x in payload.get("good_counts", [])]
        totals = [int(x) for x in payload.get("total_counts", [])]
        circuits = payload.get("circuits", [])
        if len(good) != len(POWERS) or len(totals) != len(POWERS) or len(circuits) != len(POWERS):
            errors.append(f"{source}: expected three count and circuit rows")
            continue
        row: dict[str, object] = {
            "backend": backend,
            "transpiler_seed": seed,
            "job_id": payload.get("job_id"),
            "submitted_utc": payload.get("submitted_utc"),
            "completed_utc": payload.get("completed_utc"),
            "calibration_timestamp": payload.get("backend_properties_last_update"),
            "estimate": float(estimate["estimate"]),
            "absolute_error": float(estimate["absolute_error"]),
            "ideal_likelihood_95_low": float(estimate["likelihood_95_low"]),
            "ideal_likelihood_95_high": float(estimate["likelihood_95_high"]),
            "qpu_charge_seconds": float(usage.get("qpu_charge_time_seconds", math.nan)),
            "resource_units": float(usage.get("value", math.nan)),
            "source_file": source,
        }
        for i, power in enumerate(POWERS):
            row[f"m{power}_good"] = good[i]
            row[f"m{power}_shots"] = totals[i]
            observed = good[i] / totals[i]
            row[f"m{power}_observed"] = observed
            row[f"m{power}_ideal"] = expected_probability(power)
            row[f"m{power}_deviation"] = observed - expected_probability(power)
            row[f"m{power}_depth"] = int(circuits[i]["depth"])
            row[f"m{power}_two_qubit"] = int(circuits[i]["two_qubit_instructions"])
        rows.append(row)
    return sorted(rows, key=lambda x: (BACKENDS.index(str(x["backend"])), int(x["transpiler_seed"]))), errors


def _summary(rows: list[dict[str, object]], complete: bool) -> dict[str, object]:
    values = np.asarray([float(row["estimate"]) for row in rows], dtype=float)
    errors = np.asarray([float(row["absolute_error"]) for row in rows], dtype=float)
    qpu = np.asarray([float(row["qpu_charge_seconds"]) for row in rows], dtype=float)
    result: dict[str, object] = {
        "completed_cells": len(rows),
        "planned_cells": len(BACKENDS) * len(SEEDS),
        "exact_probability": EXACT_PROBABILITY,
    }
    if not len(rows):
        return result
    result.update(
        {
            "estimate_mean": float(values.mean()),
            "estimate_min": float(values.min()),
            "estimate_max": float(values.max()),
            "mean_absolute_error": float(errors.mean()),
            "max_absolute_error": float(errors.max()),
            "total_qpu_charge_seconds_recorded": float(np.nansum(qpu)),
        }
    )
    if len(rows) >= 2:
        sd = float(values.std(ddof=1))
        sem = sd / math.sqrt(len(rows))
        critical = float(student_t.ppf(0.975, df=len(rows) - 1))
        result.update(
            {
                "between_job_sd": sd,
                "descriptive_t95_low": float(values.mean() - critical * sem),
                "descriptive_t95_high": float(values.mean() + critical * sem),
                "descriptive_interval_scope": "mean over the observed backend/seed cells; does not calibrate unobserved devices or times",
            }
        )
    if complete:
        matrix = np.empty((len(BACKENDS), len(SEEDS)), dtype=float)
        for row in rows:
            i = BACKENDS.index(str(row["backend"]))
            j = SEEDS.index(int(row["transpiler_seed"]))
            matrix[i, j] = float(row["estimate"])
        backend_means = matrix.mean(axis=1)
        seed_means = matrix.mean(axis=0)
        fitted = backend_means[:, None] + seed_means[None, :] - matrix.mean()
        interaction = matrix - fitted
        rng = np.random.default_rng(BOOTSTRAP_SEED)
        boot = np.empty(BOOTSTRAP_REPLICATES, dtype=float)
        for k in range(BOOTSTRAP_REPLICATES):
            bi = rng.integers(0, len(BACKENDS), size=len(BACKENDS))
            sj = rng.integers(0, len(SEEDS), size=len(SEEDS))
            boot[k] = matrix[np.ix_(bi, sj)].mean()
        low, high = np.quantile(boot, [0.025, 0.975])
        result.update(
            {
                "backend_means": {name: float(backend_means[i]) for i, name in enumerate(BACKENDS)},
                "seed_means": {str(seed): float(seed_means[j]) for j, seed in enumerate(SEEDS)},
                "backend_mean_range": float(np.ptp(backend_means)),
                "seed_mean_range": float(np.ptp(seed_means)),
                "backend_seed_interaction_rmse": float(np.sqrt(np.mean(interaction**2))),
                "crossed_design_bootstrap": {
                    "replicates": BOOTSTRAP_REPLICATES,
                    "seed": BOOTSTRAP_SEED,
                    "low_2_5_percent": float(low),
                    "high_97_5_percent": float(high),
                    "scope": "independent resampling of the three observed backend and three transpiler-seed levels; descriptive design variability, not a universal hardware confidence interval",
                },
            }
        )
    return result


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        path.write_text("backend,transpiler_seed,status\n", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _write_figure(path_png: Path, path_pdf: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        return
    colors = {BACKENDS[0]: "#3366cc", BACKENDS[1]: "#44aa66", BACKENDS[2]: "#ee7733"}
    fig, axes = plt.subplots(1, 3, figsize=(13.2, 4.2), constrained_layout=True)
    ax = axes[0]
    for row in rows:
        x = SEEDS.index(int(row["transpiler_seed"]))
        ax.scatter(x, float(row["estimate"]), color=colors[str(row["backend"])], s=55, label=str(row["backend"]))
    handles, labels = ax.get_legend_handles_labels()
    unique = dict(zip(labels, handles))
    ax.legend(unique.values(), unique.keys(), fontsize=8)
    ax.axhline(EXACT_PROBABILITY, color="black", linestyle="--", linewidth=1.2, label="exact")
    ax.set_xticks(range(len(SEEDS)), [str(seed) for seed in SEEDS], rotation=25)
    ax.set_ylabel("MLAE estimate")
    ax.set_title("(a) Backend × transpiler seed")
    ax.grid(alpha=0.25)

    ax = axes[1]
    for power in POWERS:
        vals = np.asarray([float(row[f"m{power}_observed"]) for row in rows])
        x = power
        ax.scatter(np.full(len(vals), x), vals, color="#6a51a3", alpha=0.65, s=34)
        ax.errorbar(x, vals.mean(), yerr=[[vals.mean() - vals.min()], [vals.max() - vals.mean()]], fmt="o", color="black", capsize=4)
        ax.scatter(x, expected_probability(power), marker="x", color="#d62728", s=70)
    ax.set_xticks(list(POWERS))
    ax.set_xlabel("Grover power, m")
    ax.set_ylabel("Observed good-state probability")
    ax.set_title("(b) Amplification distortion")
    ax.grid(alpha=0.25)

    ax = axes[2]
    labels = [f"{str(r['backend']).replace('ibm_', '')}\n{r['transpiler_seed']}" for r in rows]
    errors = [float(r["absolute_error"]) for r in rows]
    ax.bar(range(len(rows)), errors, color=[colors[str(r["backend"])] for r in rows])
    ax.set_xticks(range(len(rows)), labels, rotation=55, ha="right", fontsize=7)
    ax.set_ylabel("Absolute error from p=0.625")
    ax.set_title("(c) Job-level hardware error")
    ax.grid(axis="y", alpha=0.25)
    fig.suptitle("IBM QPU replication boundary for the frozen three-qubit PSA event", fontsize=12)
    fig.savefig(path_png, dpi=240)
    fig.savefig(path_pdf)
    plt.close(fig)


def _write_markdown(path: Path, payload: dict[str, object], rows: list[dict[str, object]]) -> None:
    summary = payload["summary"]
    lines = [
        "# IBM QPU replication-campaign analysis",
        "",
        f"Status: **{payload['status']}**. Completed planned cells: **{len(rows)}/9**.",
        "",
        "This analysis inventories only completed real-QPU artifacts that match the frozen three-backend × three-seed design. It never submits or retrieves a workload.",
        "",
    ]
    if rows:
        lines += [
            "| backend | seed | job | estimate | abs. error | QPU s |",
            "|---|---:|---|---:|---:|---:|",
        ]
        for row in rows:
            lines.append(
                f"| {row['backend']} | {row['transpiler_seed']} | `{row['job_id']}` | "
                f"{float(row['estimate']):.6f} | {float(row['absolute_error']):.6f} | "
                f"{float(row['qpu_charge_seconds']):.1f} |"
            )
        lines += [
            "",
            f"The current mean estimate is `{summary['estimate_mean']:.6f}` with mean absolute error `{summary['mean_absolute_error']:.6f}`. These values describe the completed cells only.",
        ]
    if payload["status"] != "complete_9_of_9":
        lines += [
            "",
            "No manuscript-grade hardware interval is reported until all nine planned cells complete. The earlier single job remains a reference boundary and is not silently counted as a campaign replicate when its transpiler seed is absent.",
        ]
    else:
        crossed = summary["crossed_design_bootstrap"]
        lines += [
            "",
            f"Across the complete design, the between-job SD is `{summary['between_job_sd']:.6f}` and the crossed-design bootstrap interval for the sampled backend/seed mean is `[{crossed['low_2_5_percent']:.6f}, {crossed['high_97_5_percent']:.6f}]`. This is a descriptive design-variability interval, not a universal noise-calibrated confidence interval.",
            "",
            "The hardware campaign remains a three-qubit event-kernel boundary. It does not establish end-to-end quantum advantage or industrial PSA validation.",
        ]
    if payload["validation_errors"]:
        lines += ["", "## Validation errors", ""] + [f"- {value}" for value in payload["validation_errors"]]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()
    planned, legacy = _load_completed()
    rows, errors = _validate_and_rows(planned)
    expected = {(backend, seed) for backend in BACKENDS for seed in SEEDS}
    observed = {(str(row["backend"]), int(row["transpiler_seed"])) for row in rows}
    missing = sorted(expected - observed)
    complete = not errors and not missing and len(rows) == len(expected)
    status = "complete_9_of_9" if complete else f"incomplete_{len(rows)}_of_9"
    payload = {
        "schema": "psa-qae-qpu-replication-campaign-analysis/v1",
        "status": status,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "frozen_design": {
            "backends": list(BACKENDS),
            "transpiler_seeds": list(SEEDS),
            "powers": list(POWERS),
            "shots_per_circuit": SHOTS,
            "exact_probability": EXACT_PROBABILITY,
        },
        "missing_cells": [{"backend": b, "transpiler_seed": s} for b, s in missing],
        "validation_errors": errors,
        "legacy_completed_reference_jobs": [
            {"job_id": row.get("job_id"), "backend": row.get("backend"), "source_file": row.get("_source_file")}
            for row in legacy
        ],
        "summary": _summary(rows, complete),
        "rows": rows,
        "claim_boundary": "hardware event-kernel replication only; no end-to-end quantum advantage or industrial PSA validation",
        "qpu_submission_by_this_script": False,
    }
    json_path = OUT / f"{STEM}.json"
    csv_path = OUT / f"{STEM}.csv"
    md_path = OUT / f"{STEM}.md"
    png_path = OUT / f"{STEM}_FIGURE.png"
    pdf_path = OUT / f"{STEM}_FIGURE.pdf"
    json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    _write_csv(csv_path, rows)
    _write_markdown(md_path, payload, rows)
    _write_figure(png_path, pdf_path, rows)
    print(json.dumps({"status": status, "completed_cells": len(rows), "missing_cells": len(missing), "validation_errors": errors}, indent=2))
    if args.require_complete and not complete:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
