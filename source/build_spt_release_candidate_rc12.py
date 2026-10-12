"""Build and audit the pressure-consistent v0.2.0-rc12 release candidate."""

from __future__ import annotations

import hashlib
import json
import shutil
import zipfile
from pathlib import Path


HERE = Path(__file__).resolve().parent
TEA = HERE.parent
PROJECT = TEA.parent
RESULTS = HERE / "results"
RELEASE = TEA / "release" / "spt_v020_rc12"
PACKAGE = RELEASE / "psa-qae-spt-v0.2.0-pressure-consistent"
MANUSCRIPT = RESULTS / "spt_pressure_consistent_manuscript_v2"
EVIDENCE = RESULTS / "final_objective_evidence_v44"
OLD_META = TEA / "release" / "spt_v020_rc11" / "psa-qae-spt-v0.2.0"

RESULT_DIRS = [
    "pressure_consistency_audit_v1",
    "hydraulically_feasible_policy_6cell_confirmation_v1",
    "hydraulically_feasible_full_6cell_cube_v1",
    "hydraulically_feasible_selected_6cell_holdout_v1",
    "pressure_consistent_stage_resolved_membrane_train_v1",
    "pressure_consistent_pd_leakage_aging_sensitivity_v1",
    "pressure_consistent_independent_ode_membrane_audit_v1",
    "pressure_consistent_pd_actual_syngas_poisoning_guard_v1",
    "pressure_consistent_physical_pd_area_qae_bridge_v1",
    "pressure_consistent_independent_rk4_membrane_crosscheck_v1",
    "pressure_consistent_public_selectivity_acceptance_audit_v1",
    "pressure_consistent_portable_qasm_oracle_v1",
    "wang_2023_public_experimental_benchmark",
    "membrane_public_evidence_audit_v2",
    "ververs_2024_mass_transfer_validation_v1",
    "sanchez_2014_validation_audit_v1",
    "doe_pall_2008_mixed_gas_validation_v1",
    "utrc_2012_high_recovery_validation_v1",
    "bang_2021_joint_gate_validation_v1",
]

SOURCE_FILES = [
    "psa_pressure_consistency_audit_v1.py",
    "psa_hydraulically_feasible_policy_6cell_confirmation_v1.py",
    "psa_hydraulically_feasible_full_6cell_cube_v1.py",
    "psa_hydraulically_feasible_selected_6cell_holdout_v1.py",
    "psa_stage_resolved_membrane_train.py",
    "psa_pressure_consistent_stage_resolved_membrane_train_v1.py",
    "psa_pd_leakage_aging_sensitivity.py",
    "psa_independent_ode_membrane_audit.py",
    "psa_pd_syngas_poisoning_guard_v1.py",
    "psa_pressure_consistent_membrane_validation_chain_v1.py",
    "psa_physical_pd_area_qae_bridge.py",
    "psa_literature_anchored_strict_margin_qae_bridge.py",
    "psa_independent_rk4_membrane_crosscheck_v1.py",
    "psa_public_selectivity_acceptance_audit_v1.py",
    "psa_pressure_consistent_public_selectivity_acceptance_audit_v1.py",
    "psa_pressure_consistent_portable_qasm_oracle_v1.py",
    "build_spt_full_manuscript.py",
    "build_final_objective_evidence_v44.py",
    "build_spt_pressure_consistent_manuscript_v2.py",
    "finalize_spt_pressure_consistent_manuscript_v2.py",
    "export_pressure_consistent_docx_qa.ps1",
    "build_render_contact_sheet.py",
    "build_spt_release_candidate_rc12.py",
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def copytree(src: Path, dst: Path) -> None:
    if src.exists():
        shutil.copytree(src, dst)


def write_readme() -> None:
    text = """# Pressure-consistent regeneration-reserve-aware hydrogen PSA and QAE event

This is the **v0.2.0** reproducibility package for a Separation and
Purification Technology-oriented study. It supersedes v0.1.0 because the former
7.0 bar regeneration tank could not be passively filled from the 6.2 bar
product manifold.

## Current engineering result

- Corrected topology: 6.2 bar product manifold -> 6.0 bar regulated tank ->
  discharge booster -> 6.5 bar purge/repressurization header.
- Selected policy: 4 s active purge and 540 s adsorption; comparison: 6 s and
  480 s. Both use the same 6.0 bar tank set point.
- Direct decisions: 8/8 uncertainty corners and 8/8 predeclared hold-outs pass;
  the comparison passes 0/8 corners.
- Qualified H2 shipment improves by 6.785-7.341%; conservative regeneration
  booster duty is at most 0.197 kWh kg-1 qualified H2.
- The ideal stage-resolved train uses 0.1892 m2 polymer and 0.4799 m2 dense Pd.
- The 20%-permeance-loss guard is 0.554 m2 and passes 16/16 direct cases.
- A public 50%-retention actual-syngas stress requires 0.887 m2 and passes 16/16.
- Corrected module selectivity guards are H2/CO >=5,660, H2/CO2 >=168,660,
  H2/N2 >=540, and H2/CH4 >=40; the simultaneous rounded vector passes 16/16.
- Independent fixed-area RK4 reproduces all 32 DOP853 design-case labels.
- The 0.440 m2 chance design has conservative continuous probability 0.951210
  and 10-bit probability 0.950629 with zero direct label errors.
- Reversible register allocation requires 66 logical qubits.
- The included OpenQASM 3 oracle has 24,042 CX gates, 61,269 primitive gates,
  and all-to-all depth 36,163 before device optimization or routing. Its
  reported basis-state tests have zero phase-label or work-qubit-restoration
  errors.

## Execution boundary

The corrected integer specification, portable OpenQASM 3 oracle, and corrected
DWSIM input deck are included. Device-specific Qiskit optimization/routing and
DWSIM execution were blocked on the current Windows host by Application Control
rejecting their native DLLs. Earlier DWSIM and C# runs are not used as current
corrected-input evidence. The manuscript states these boundaries explicitly.

## Contents

- `manuscript/`: render-checked Word, PDF, Markdown, and reference audit.
- `evidence/`: V44 consolidated evidence, gates, progress, and hashes.
- `results/`: corrected machine-readable calculation records and public-data audits.
- `source/`: scripts needed to rerun the corrected analyses and rebuild artifacts.
- `dwsim_corrected_input/`: the 16-case corrected DWSIM input deck and runner tools.
- `figures/`: 19 manuscript figures.
- `checksums/sha256.txt`: file-level SHA-256 ledger.

The package does not claim current quantum advantage or matched experimental
certification of the final integrated apparatus. The remaining external checks
are stated in `EXECUTION_BOUNDARIES.md`.
"""
    (PACKAGE / "README.md").write_text(text, encoding="utf-8")


def write_boundaries() -> None:
    text = """# Execution and claim boundaries

## Completed on the corrected pressure topology

- Six-cell, 60-cycle eight-corner operating-policy cube.
- Eight predeclared interior hold-outs.
- Pressure and booster audit for the 6.2/6.0/6.5 bar routing.
- Stage-resolved polymer/Pd train over all 16 cases.
- Adaptive DOP853 finite-selectivity, defect, and permeance-loss guards.
- Independent fixed-area RK4 mesh replay of both final guard designs.
- Continuous, affine, and 10-bit discrete probability calculations.
- Corrected component-specific module selectivity acceptance audit.

## Portable oracle completed

- The frozen integer event is serialized as OpenQASM 3 using an exact
  Clifford+T decomposition and verified by exhaustive small-register tests,
  all 16 direct 10-bit engineering states, and 4,096 seeded random 10-bit
  states.

## Requiring another execution host

- Device-specific Qiskit optimization, coupling-map routing, and hardware
  execution. The present Windows Application Control policy blocks the native
  rustworkx DLL.
- DWSIM execution of the corrected 16-case deck. The same policy blocks
  DWSIM.FileStorage.dll before a flowsheet can solve.

## Experimental boundary

Public studies support model family, concentration polarization, pressure and
temperature feasibility, recovery scale, aging stress, and rejection controls.
No public experiment synchronously measures the final five-component product
at the declared ppm limits for this exact integrated PSA/membrane topology.
"""
    (PACKAGE / "EXECUTION_BOUNDARIES.md").write_text(text, encoding="utf-8")


def write_zenodo_metadata() -> None:
    path = PACKAGE / ".zenodo.json"
    metadata = json.loads(path.read_text(encoding="utf-8"))
    metadata.update(
        {
            "title": "Hydraulically feasible regeneration-reserve-aware hydrogen pressure swing adsorption under uncertainty with staged membrane polishing and a quantum-ready probability event",
            "version": "0.2.0",
            "publication_date": "2026-10-12",
            "description": "Reproducibility package for a pressure-consistent dynamic hydrogen PSA, staged polymer and palladium polishing, public-data validation, uncertainty analysis, and a verified portable OpenQASM probability oracle.",
            "notes": "The portable OpenQASM oracle and all claimed corrected calculations are included. Device-specific quantum execution, corrected-input DWSIM execution, and matched integrated experimental certification remain outside the quantitative claim.",
        }
    )
    path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")


def make_zip(source: Path, destination: Path, *, compact: bool) -> int:
    count = 0
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(p for p in source.rglob("*") if p.is_file()):
            rel = path.relative_to(source.parent)
            if compact and ("states" in path.parts or path.suffix.lower() in {".npz", ".pdf", ".svg"}):
                if "manuscript" not in path.parts or path.suffix.lower() != ".pdf":
                    continue
            info = zipfile.ZipInfo(str(rel).replace("\\", "/"), date_time=(2026, 10, 12, 12, 0, 0))
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


def main() -> None:
    assert EVIDENCE.exists()
    assert (MANUSCRIPT / "SPT_PRESSURE_CONSISTENT_MANUSCRIPT.docx").exists()
    assert (MANUSCRIPT / "SPT_PRESSURE_CONSISTENT_MANUSCRIPT.pdf").exists()
    if RELEASE.exists():
        shutil.rmtree(RELEASE)
    PACKAGE.mkdir(parents=True)

    for name in ("AUTHORS.md", "LICENSE", ".zenodo.json"):
        shutil.copy2(OLD_META / name, PACKAGE / name)
    citation = (OLD_META / "CITATION.cff").read_text(encoding="utf-8")
    citation = citation.replace(
        "Regeneration reserve aware hydrogen pressure swing adsorption under uncertainty with staged membrane polishing and a quantum ready probability oracle",
        "Hydraulically feasible regeneration-reserve-aware hydrogen pressure swing adsorption under uncertainty with staged membrane polishing and a quantum-ready probability event",
    )
    (PACKAGE / "CITATION.cff").write_text(citation, encoding="utf-8")
    write_zenodo_metadata()
    write_readme()
    write_boundaries()

    manuscript_dst = PACKAGE / "manuscript"
    manuscript_dst.mkdir()
    for name in (
        "SPT_PRESSURE_CONSISTENT_MANUSCRIPT.docx",
        "SPT_PRESSURE_CONSISTENT_MANUSCRIPT.pdf",
        "SPT_PRESSURE_CONSISTENT_MANUSCRIPT.md",
        "REFERENCE_METADATA_AUDIT.json",
        "MANIFEST_SHA256.json",
    ):
        shutil.copy2(MANUSCRIPT / name, manuscript_dst / name)
    copytree(EVIDENCE, PACKAGE / "evidence")

    results_dst = PACKAGE / "results"
    results_dst.mkdir()
    for name in RESULT_DIRS:
        copytree(RESULTS / name, results_dst / name)

    source_dst = PACKAGE / "source"
    source_dst.mkdir()
    for name in SOURCE_FILES:
        src = HERE / name
        if src.exists():
            shutil.copy2(src, source_dst / name)

    dwsim_dst = PACKAGE / "dwsim_corrected_input"
    dwsim_dst.mkdir()
    dwsim_input = PROJECT / "07_DWSIM_Aspen_재현" / "results" / "pressure_consistent_stage_train_v1" / "psa_stage_train_dwsim_input.csv"
    shutil.copy2(dwsim_input, dwsim_dst / dwsim_input.name)
    for name in ("make_psa_stage_train_dwsim_deck.py", "finalize_psa_stage_train_dwsim_crosscheck.py", "DwsimPsaStageTrainCrosscheck.cs"):
        src = PROJECT / "07_DWSIM_Aspen_재현" / "tools" / name
        if src.exists():
            shutil.copy2(src, dwsim_dst / name)

    figure_dst = PACKAGE / "figures"
    figure_dst.mkdir()
    builder_spec = __import__("importlib.util").util.spec_from_file_location("pc_builder", HERE / "build_spt_pressure_consistent_manuscript_v2.py")
    builder = __import__("importlib.util").util.module_from_spec(builder_spec)
    assert builder_spec.loader is not None
    builder_spec.loader.exec_module(builder)
    for number, src in builder.FIGURES.items():
        shutil.copy2(src, figure_dst / f"Fig{number:02d}_{src.name}")

    current = RESULTS / "CURRENT_FINAL_OBJECTIVE_EVIDENCE.json"
    shutil.copy2(EVIDENCE / "PSA_FINAL_OBJECTIVE_EVIDENCE_V44.json", current)

    checksum_dir = PACKAGE / "checksums"
    checksum_dir.mkdir()
    files = sorted(p for p in PACKAGE.rglob("*") if p.is_file() and "checksums" not in p.parts)
    ledger = "\n".join(f"{sha256(p)}  {p.relative_to(PACKAGE).as_posix()}" for p in files) + "\n"
    (checksum_dir / "sha256.txt").write_text(ledger, encoding="utf-8")
    manifest = {
        "schema": "psa-qae-spt-release-candidate/v0.2.0-rc12",
        "status": "pressure_consistent_local_release_candidate_portable_qasm_verified_dwsim_external",
        "file_count": len(files) + 1,
        "current_evidence": "psa-final-objective-evidence/v44",
        "manuscript_pages": 23,
        "release_boundary": "portable QASM complete; device-specific routing and corrected-input DWSIM execution remain external",
    }
    (PACKAGE / "MANIFEST.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    compact = RELEASE / "psa-qae-spt-v0.2.0-pressure-consistent-rc12.zip"
    full = RELEASE / "psa-qae-spt-v0.2.0-pressure-consistent-full-evidence-rc12.zip"
    compact_count = make_zip(PACKAGE, compact, compact=True)
    full_count = make_zip(PACKAGE, full, compact=False)
    audit = {
        "schema": "psa-qae-spt-release-candidate-audit/v0.2.0-rc12",
        "status": "verified_local_pressure_consistent_release_candidate_portable_qasm_complete",
        "package_directory": str(PACKAGE),
        "compact_archive": zip_audit(compact),
        "full_evidence_archive": zip_audit(full),
        "expected_counts": {"compact": compact_count, "full": full_count},
        "release_ready_for_public_replacement": True,
        "reason": "portable QASM and all claimed corrected calculations are included; device routing and DWSIM execution are explicitly outside the quantitative claim",
    }
    (RELEASE / "RELEASE_CANDIDATE_AUDIT.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
    print(json.dumps(audit, indent=2))


if __name__ == "__main__":
    main()
