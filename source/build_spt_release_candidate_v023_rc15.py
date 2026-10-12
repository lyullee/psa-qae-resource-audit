"""Build and audit the v0.2.3 package with two public experimental hold-outs."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import zipfile


HERE = Path(__file__).resolve().parent
TEA = HERE.parent
RESULTS = HERE / "results"
RELEASE = TEA / "release" / "spt_v023_rc15"
PACKAGE = RELEASE / "psa-qae-spt-v0.2.3-pressure-consistent"
PREVIOUS = TEA / "release" / "spt_v022_rc14" / "psa-qae-spt-v0.2.2-pressure-consistent"
MANUSCRIPT = RESULTS / "spt_pressure_consistent_manuscript_v5"
EVIDENCE = RESULTS / "final_objective_evidence_v46"
IBM = RESULTS / "ibm_final_event_2bit_probe"
EXTERNAL_HOLDOUT = RESULTS / "spt_external_experimental_holdouts_v1"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def copytree(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def make_zip(source: Path, destination: Path, compact: bool) -> int:
    candidates = []
    for path in sorted(p for p in source.rglob("*") if p.is_file()):
        if compact and ("states" in path.parts or path.suffix.lower() in {".npz", ".svg"}):
            continue
        candidates.append(path)
    count = 0
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in candidates:
            rel = path.relative_to(source.parent).as_posix()
            info = zipfile.ZipInfo(rel, date_time=(2026, 10, 13, 6, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, path.read_bytes())
            count += 1
    return count


def zip_audit(path: Path) -> dict:
    with zipfile.ZipFile(path) as archive:
        bad = archive.testzip()
        names = archive.namelist()
    return {
        "path": str(path),
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
        "file_count": len(names),
        "duplicate_count": len(names) - len(set(names)),
        "bad_member": bad,
    }


def update_metadata() -> None:
    zenodo_path = PACKAGE / ".zenodo.json"
    zenodo = json.loads(zenodo_path.read_text(encoding="utf-8"))
    zenodo.update({
        "version": "0.2.3",
        "publication_date": "2026-10-13",
        "description": (
            "Reproducibility package for a pressure-consistent dynamic hydrogen PSA, staged polymer and palladium polishing, "
            "public-data validation, uncertainty analysis, two post-freeze public experimental hold-outs, a verified "
            "66-logical-qubit portable OpenQASM oracle, and an exact two-bit final-event truth-mapping probe executed over "
            "all 64 inputs on IBM Kingston."
        ),
        "notes": (
            "The v0.2.3 update adds Chen et al. 2023 and Voigt 2022 experimental tables without refitting. All 12 Chen "
            "endpoint-direction tests pass; 6/13 Voigt cycles pass the source Type-1-plus-70%-recovery event, with at least one "
            "pass in each feed stage. The IBM result remains a basis-state truth-mapping test, not coherent QAE or quantum advantage."
        ),
    })
    zenodo_path.write_text(json.dumps(zenodo, indent=2), encoding="utf-8")

    citation_path = PACKAGE / "CITATION.cff"
    citation = citation_path.read_text(encoding="utf-8").replace('version: "0.2.2"', 'version: "0.2.3"').replace("date-released: 2026-10-12", "date-released: 2026-10-13")
    citation_path.write_text(citation, encoding="utf-8")


def write_readme() -> None:
    text = """# Pressure-consistent regeneration-reserve-aware hydrogen PSA and QAE event

This is the **v0.2.3** reproducibility package for a Separation and
Purification Technology-oriented study. It contains the corrected process
model, public-data checks, process-simulator cross-check, portable probability
oracle, and the final-event IBM QPU probe.

## Current engineering result

- Corrected topology: 6.2 bar product manifold -> 6.0 bar regulated tank ->
  discharge booster -> 6.5 bar purge/repressurization header.
- The selected 4 s purge and 540 s adsorption policy passes 8/8 uncertainty
  corners and 8/8 predeclared hold-outs; the 6 s/480 s comparison passes 0/8.
- Qualified H2 shipment improves by 6.785-7.341%, with regeneration-booster
  duty no greater than 0.197 kWh kg-1 qualified H2.
- The 0.554 m2 20%-permeance-loss guard and 0.887 m2 public actual-syngas
  50%-retention guard each pass all 16 direct cases.
- Independent fixed-area RK4 reproduces all 32 DOP853 design-case labels.
- Two post-freeze public experimental hold-outs were added without fitting:
  the Chen 13-run two-bed H2/CO2 VPSA table passes 12/12 directional endpoint
  checks, and the Voigt 13-run four-bed H2/CH4 PSA table gives 6/13
  source-event passes with at least one pass in every transient feed stage.
- Corrected DWSIM 8.7.1 Peng-Robinson calculations solve all 16 cases at the
  physical 6.2 bar inlet. Compression is 3.091-3.183 kWh kg-1 H2.
- The 0.440 m2 chance design has continuous affine probability 0.951210 and
  10-bit probability 0.950629, an absolute discretization error of 0.000581.
- The complete portable arithmetic oracle requires 66 logical qubits and has
  24,042 CX gates, 61,269 primitive gates, and all-to-all depth 36,163 before
  device optimization or routing.
- The exact two-bit reduction of the **same final event** was compiled to a
  seven-qubit Boolean circuit and executed on IBM Kingston as job
  `db6emt04qg6s73c4lja0`. All 64 inputs were majority-correct at 256 shots per
  state; mean expected-label probability was 0.8389, minimum was 0.6523, and
  usage was 7 QPU s. Read-only retrieval reproduced all 64 count dictionaries.

## Quantum claim boundary

The IBM result is an exhaustive basis-state truth-mapping test at two-bit
resolution. It connects the final engineering inequality to real-device
compilation, routing, and measurement. It is not coherent amplitude
estimation, execution of the 42-qubit two-bit arithmetic oracle or the
66-qubit ten-bit arithmetic oracle, and it is not evidence of quantum
advantage. RQMC remains the practical estimator for the present three-variable
event.

## Contents

- `manuscript/`: render-checked Word, PDF, Markdown, and reference audit.
- `evidence/`: V46 consolidated evidence, gates, progress, and hashes.
- `results/ibm_final_event_2bit_probe/`: routed resources, all 64 raw count
  dictionaries, QASM, figure, and read-only job verification.
- `results/`: corrected machine-readable calculations and public-data audits.
- `results/spt_external_experimental_holdouts_v1/`: digitized Chen and Voigt
  tables, acceptance contract, statistics, figure, and hashes.
- `source/`: rerun scripts, including guarded free-Open-Plan IBM execution and
  read-only verification.
- `dwsim_crosscheck/`: corrected DWSIM inputs, outputs, saved cases, and build
  provenance.
- `figures/`: 19 manuscript figures.
- `checksums/sha256.txt`: file-level SHA-256 ledger.

The remaining principal external check is a synchronized component-resolved
experiment on the final integrated PSA and membrane apparatus.
"""
    (PACKAGE / "README.md").write_text(text, encoding="utf-8")


def write_boundaries() -> None:
    text = """# Execution and claim boundaries

## Completed on the corrected pressure topology

- Six-cell, 60-cycle eight-corner operating-policy cube and eight predeclared hold-outs.
- Pressure and booster audit for the 6.2/6.0/6.5 bar routing.
- Stage-resolved polymer/Pd train, adaptive DOP853 guards, and independent RK4 replay.
- Continuous, affine, and 10-bit discrete probability calculations.
- Corrected 16-case DWSIM 8.7.1 Peng-Robinson pressure, duty, temperature, and closure audit.

## Portable arithmetic oracle completed

- The frozen integer event is serialized as exact OpenQASM 3.
- Exhaustive 2-, 3-, and 4-bit checks, all 16 direct 10-bit engineering states,
  and 4,096 seeded random 10-bit states give zero phase-label or restoration errors.
- The 10-bit construction requires 66 logical qubits and 24,042 CX gates before routing.

## IBM QPU final-event probe completed

- The exact final affine event at two bits per uncertainty variable was reduced
  to six input qubits and one flag through an exact three-cube complement cover.
- All 128 reversible input/flag mappings pass local statevector verification.
- All 64 zero-flag input states were run on IBM Kingston at 256 shots per state.
- Job `db6emt04qg6s73c4lja0` used 7 QPU s; 64/64 states were majority-correct.
- A separate read-only retrieval exactly matched all 64 archived count dictionaries.

## Quantum work that remains external

- Coherent state preparation and amplitude-estimation iterations.
- Hardware execution of the 42-logical-qubit two-bit arithmetic oracle or the
  66-logical-qubit ten-bit arithmetic oracle.
- Any claim of quantum speedup, cost advantage, or fault-tolerant resource sufficiency.

## Experimental boundary

Public studies support model family, concentration polarization, pressure and
temperature feasibility, recovery scale, aging stress, and rejection controls.
The Chen and Voigt tables additionally support the purity-recovery trade-off,
purge-allocation cost, and feed-dependent cycle settings without local refitting.
No public experiment synchronously measures the final five-component product
at the declared ppm limits for this exact integrated PSA/membrane topology.
"""
    (PACKAGE / "EXECUTION_BOUNDARIES.md").write_text(text, encoding="utf-8")


def main() -> None:
    required = [
        PREVIOUS,
        MANUSCRIPT / "SPT_PRESSURE_CONSISTENT_MANUSCRIPT.docx",
        MANUSCRIPT / "SPT_PRESSURE_CONSISTENT_MANUSCRIPT.pdf",
        EVIDENCE / "PSA_FINAL_OBJECTIVE_EVIDENCE_V46.json",
        IBM / "PSA_IBM_FINAL_EVENT_2BIT_PROBE.json",
        IBM / "PSA_IBM_FINAL_EVENT_2BIT_JOB_VERIFICATION.json",
        EXTERNAL_HOLDOUT / "PSA_SPT_EXTERNAL_EXPERIMENTAL_HOLDOUTS_V1.json",
        EXTERNAL_HOLDOUT / "CHEN_2023_TABLE5_DIGITIZED.csv",
        EXTERNAL_HOLDOUT / "VOIGT_2022_TABLES13_16_DIGITIZED.csv",
    ]
    for path in required:
        assert path.exists(), path
    if RELEASE.exists():
        resolved = RELEASE.resolve()
        assert resolved.parent == (TEA / "release").resolve() and resolved.name == "spt_v023_rc15"
        shutil.rmtree(resolved)
    RELEASE.mkdir(parents=True)
    shutil.copytree(PREVIOUS, PACKAGE)

    update_metadata()
    write_readme()
    write_boundaries()

    manuscript_dst = PACKAGE / "manuscript"
    for old in manuscript_dst.glob("*"):
        if old.is_file():
            old.unlink()
    for name in (
        "SPT_PRESSURE_CONSISTENT_MANUSCRIPT.docx",
        "SPT_PRESSURE_CONSISTENT_MANUSCRIPT.pdf",
        "SPT_PRESSURE_CONSISTENT_MANUSCRIPT.md",
        "REFERENCE_METADATA_AUDIT.json",
        "MANIFEST_SHA256.json",
        "PAGE_TEXT_INDEX.json",
        "WORD_EXPORT_RENDER_AUDIT.json",
    ):
        shutil.copy2(MANUSCRIPT / name, manuscript_dst / name)

    copytree(EVIDENCE, PACKAGE / "evidence")
    copytree(IBM, PACKAGE / "results" / "ibm_final_event_2bit_probe")
    copytree(EXTERNAL_HOLDOUT, PACKAGE / "results" / "spt_external_experimental_holdouts_v1")
    shutil.copy2(EVIDENCE / "PSA_FINAL_OBJECTIVE_EVIDENCE_V46.json", PACKAGE / "results" / "CURRENT_FINAL_OBJECTIVE_EVIDENCE.json")
    shutil.copy2(IBM / "Fig_qae_oracle_and_ibm_hardware_v2.png", PACKAGE / "figures" / "Fig09_Fig_qae_oracle_and_ibm_hardware_v2.png")
    shutil.copy2(EXTERNAL_HOLDOUT / "Fig_external_experimental_holdouts_v1.png", PACKAGE / "figures" / "Fig19_Fig_external_experimental_holdouts_v1.png")
    old_fig = PACKAGE / "figures" / "Fig09_Fig_pressure_consistent_portable_qasm_oracle_v1.png"
    if old_fig.exists():
        old_fig.unlink()
    old_fig19 = PACKAGE / "figures" / "Fig19_Fig_csharp_direct_transport_crosscheck_v1.png"
    if old_fig19.exists():
        old_fig19.unlink()

    source_dst = PACKAGE / "source"
    for name in (
        "psa_ibm_final_event_2bit_probe.py",
        "verify_ibm_final_event_2bit_job.py",
        "build_ibm_qpu_oracle_figure.py",
        "build_final_objective_evidence_v46.py",
        "spt_external_experimental_holdouts_v1.py",
        "build_spt_pressure_consistent_manuscript_v5.py",
        "finalize_spt_pressure_consistent_manuscript_v5.py",
        "build_spt_release_candidate_v023_rc15.py",
    ):
        shutil.copy2(HERE / name, source_dst / name)
    (source_dst / "requirements_ibm_qpu.txt").write_text(
        "qiskit==2.5.2\nqiskit-ibm-runtime==0.50.0\nqiskit-aer==0.17.2\nmatplotlib\nnumpy\n",
        encoding="utf-8",
    )

    manifest = {
        "schema": "psa-qae-spt-release-candidate/v0.2.3-rc15",
        "status": "pressure_consistent_release_with_two_public_experimental_holdouts",
        "current_evidence": "psa-final-objective-evidence/v46",
        "manuscript_pages": 25,
        "external_experimental_holdouts": {
            "chen_directional_tests": "12/12",
            "voigt_source_event_passes": "6/13",
            "voigt_feed_stages_with_at_least_one_pass": "4/4",
            "model_refit": False,
        },
        "ibm_qpu": {
            "job_id": "db6emt04qg6s73c4lja0",
            "backend": "ibm_kingston",
            "states": 64,
            "shots_per_state": 256,
            "majority_correct": 64,
            "qpu_usage_seconds": 7,
        },
        "release_boundary": (
            "portable 66-qubit arithmetic oracle, final-event two-bit IBM truth-mapping probe, and two post-freeze public "
            "experimental controls complete; coherent QAE, full arithmetic-oracle hardware execution, and matched integrated "
            "experiment remain external"
        ),
    }
    (PACKAGE / "MANIFEST.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    checksum_dir = PACKAGE / "checksums"
    if checksum_dir.exists():
        shutil.rmtree(checksum_dir)
    checksum_dir.mkdir()
    files = sorted(path for path in PACKAGE.rglob("*") if path.is_file() and "checksums" not in path.parts)
    ledger = "\n".join(f"{sha256(path)}  {path.relative_to(PACKAGE).as_posix()}" for path in files) + "\n"
    (checksum_dir / "sha256.txt").write_text(ledger, encoding="utf-8")
    manifest["file_count"] = len(files) + 1
    (PACKAGE / "MANIFEST.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    # Rebuild once because MANIFEST.json changed after file count insertion.
    files = sorted(path for path in PACKAGE.rglob("*") if path.is_file() and "checksums" not in path.parts)
    ledger = "\n".join(f"{sha256(path)}  {path.relative_to(PACKAGE).as_posix()}" for path in files) + "\n"
    (checksum_dir / "sha256.txt").write_text(ledger, encoding="utf-8")

    compact = RELEASE / "psa-qae-spt-v0.2.3-pressure-consistent-rc15.zip"
    full = RELEASE / "psa-qae-spt-v0.2.3-pressure-consistent-full-evidence-rc15.zip"
    compact_count = make_zip(PACKAGE, compact, compact=True)
    full_count = make_zip(PACKAGE, full, compact=False)
    audit = {
        "schema": "psa-qae-spt-release-candidate-audit/v0.2.3-rc15",
        "status": "verified_local_release_with_two_public_experimental_holdouts",
        "package_directory": str(PACKAGE),
        "compact_archive": zip_audit(compact),
        "full_evidence_archive": zip_audit(full),
        "expected_counts": {"compact": compact_count, "full": full_count},
        "release_ready": True,
        "reason": "the Chen and Voigt digitized tables, acceptance calculations, updated manuscript, final-event IBM records, corrected process evidence, and hashes are included",
    }
    (RELEASE / "RELEASE_CANDIDATE_AUDIT.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
    print(json.dumps(audit, indent=2))


if __name__ == "__main__":
    main()
