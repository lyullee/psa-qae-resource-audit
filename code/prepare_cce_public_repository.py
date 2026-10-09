"""Stage the verified CCE package as a compact public GitHub/Zenodo repository.

The script never submits QPU work, creates a remote repository, or uploads a
deposit.  It copies only files already listed in the SHA-256 submission
manifest, verifies every source and staged copy, and writes repository metadata.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import date
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RESULTS = ROOT / "10_TEA_LCA_Python" / "results" / "pycharm_publication_enhancement"
MANIFEST = RESULTS / "PSA_QAE_CCE_SUBMISSION_PACKAGE_MANIFEST.json"
AUTHORS = RESULTS / "PSA_QAE_CCE_AUTHOR_METADATA.json"
DEFAULT_DESTINATION = ROOT / "10_TEA_LCA_Python" / "release" / "psa-qae-resource-audit"
VERSION_DOI = "10.5281/zenodo.23271867"

GROUP_DIRECTORIES = {
    "main_text": "manuscript",
    "supporting_information": "results",
    "reproducibility": "reproducibility",
    "code": "code",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_readme(destination: Path, manifest: dict, author_data: dict) -> None:
    names = ", ".join(author["name_en"] for author in author_data["authors"])
    normalized_product = json.loads(
        (
            RESULTS
            / "PSA_QAE_CCE_PRIMARY_NORMALIZED_PRODUCT_LDF_VALVE_BALANCE.json"
        ).read_text(encoding="utf-8")
    )
    normalized_product_resources = normalized_product[
        "componentwise_compiled_direct_paths"
    ]
    normalized_product_upper = normalized_product[
        "conservative_five_component_upper_bound"
    ]
    coherent_consumer = json.loads(
        (
            RESULTS
            / "PSA_QAE_CCE_COHERENT_COEFFICIENT_LDF_BALANCE_INTERFACE.json"
        ).read_text(encoding="utf-8")
    )
    coherent_consumer_resources = coherent_consumer[
        "componentwise_compiled_direct_paths"
    ]
    coherent_consumer_upper = coherent_consumer[
        "conservative_five_component_upper_bound"
    ]
    coherent_dynamic = json.loads(
        (
            RESULTS
            / "PSA_QAE_CCE_COHERENT_DYNAMIC_LANGMUIR_LDF_BALANCE_INTERFACE.json"
        ).read_text(encoding="utf-8")
    )
    coherent_dynamic_resources = coherent_dynamic[
        "componentwise_compiled_direct_paths"
    ]
    coherent_dynamic_upper = coherent_dynamic[
        "conservative_five_component_upper_bound"
    ]
    coherent_normalized_dynamic = json.loads(
        (
            RESULTS
            / "PSA_QAE_CCE_COHERENT_NORMALIZED_DYNAMIC_TRANSPORT_LDF_BALANCE.json"
        ).read_text(encoding="utf-8")
    )
    coherent_normalized_dynamic_resources = coherent_normalized_dynamic[
        "componentwise_compiled_direct_paths"
    ]
    coherent_normalized_dynamic_upper = coherent_normalized_dynamic[
        "conservative_five_component_upper_bound"
    ]
    offledger_tank = json.loads(
        (
            RESULTS
            / "PSA_QAE_CCE_OFFLEDGER_TANK_SATURATION_INTERFACE.json"
        ).read_text(encoding="utf-8")
    )
    offledger_proportional = json.loads(
        (
            RESULTS
            / "PSA_QAE_CCE_OFFLEDGER_TANK_PROPORTIONAL_INTERFACE.json"
        ).read_text(encoding="utf-8")
    )
    physical_unsaturated = json.loads(
        (
            RESULTS
            / "PSA_QAE_CCE_PHYSICAL_UNSATURATED_TANK_TRAJECTORY.json"
        ).read_text(encoding="utf-8")
    )
    text = f"""# Resource-aware quantum amplitude estimation for chance-constrained pressure swing adsorption: classical baselines, compiled oracle costs, and a hardware boundary

This repository is the reproducibility package for a *Computers & Chemical Engineering* manuscript on chance-constrained pressure swing adsorption (PSA), matched classical and quantum probability estimators, reversible-oracle resource accounting, and a nine-job, three-backend IBM QPU hardware boundary.

## Authors

{names}. All authors are affiliated with Korea Gas Safety Corporation, Republic of Korea. Ugwiyeon Lee is the corresponding author. ORCIDs and the CRediT statement are recorded in `reproducibility/PSA_QAE_CCE_AUTHOR_METADATA.md`.

## Supported conclusions

- Scrambled-Sobol RQMC is the best current estimator for the frozen smooth, moderate-dimensional surrogate.
- Noiseless MLAE improves over matched crude Monte Carlo but does not create an end-to-end advantage after state loading, reversible process evaluation, and hardware noise are counted.
- The compiled process/event tiers include direct five-component LDF-to-loading-sign-to-solid-conversion-to-interior-cell-balance circuits, gas-inventory-normalized interior and product-cell paths, a finite-support run/schedule controller, coefficient generation, and five paths that connect three raw gas-inventory vectors through normalization, pressure reconstruction, two oriented faces, the run-affinity Langmuir denominator/reciprocal, q*/LDF/loading conversion, and conservative balance. These highest component paths compile to {min(row['logical_qubits'] for row in coherent_normalized_dynamic_resources):,}–{max(row['logical_qubits'] for row in coherent_normalized_dynamic_resources):,} logical qubits and {min(row['cx'] for row in coherent_normalized_dynamic_resources):,}–{max(row['cx'] for row in coherent_normalized_dynamic_resources):,} CX per component, with a {coherent_normalized_dynamic_upper['cx_additive_upper_bound']:,}-CX repeated-path upper bound. A {offledger_tank['compiled_clean_circuit']['logical_qubits']}-qubit/{offledger_tank['compiled_clean_circuit']['cx']:,}-CX pressure-derived circuit replaces the recorded tank-withdrawal lookup on all {offledger_tank['support']['records']} frozen saturated calls. A {offledger_proportional['compiled_clean_circuit']['logical_qubits']}-qubit/{offledger_proportional['compiled_clean_circuit']['cx']:,}-CX extension preserves {offledger_proportional['support']['observed_saturated_records']} observed saturated and {offledger_proportional['support']['counterfactual_unsaturated_records']} bounded-counterfactual unsaturated proportional-allocation labels. A separate {physical_unsaturated['compiled_clean_circuit']['logical_qubits']}-qubit/{physical_unsaturated['compiled_clean_circuit']['cx']:,}-CX source-model control supplies {physical_unsaturated['trajectory']['unsaturated_calls']} physically generated unsaturated, zero-makeup calls using start/end-pressure trapezoidal demand. It keeps the recycle fraction but uses a declared {physical_unsaturated['trajectory']['non_adsorption_duration_s']:.2f}-s non-adsorption schedule; frozen-schedule unsaturated coverage and monolithic five-component phase integration remain open.
- Public H2 evidence and independent simulator controls do not validate the selected industrial recycle policy. This limitation is retained as part of the result.

The repository does **not** claim quantum advantage, industrial H2 validation, a global recycle optimum, or deployment readiness.

## Contents

- `manuscript/`: review manuscript, figures, tables, references, highlights, and cover-letter draft
- `results/`: machine-readable estimator, process, circuit, QPU, external-control, and audit outputs
- `code/`: local generation, compilation, audit, and verification scripts
- `reproducibility/`: environments, submission checks, author metadata, and readiness records
- `checksums/sha256.txt`: SHA-256 values for every copied manifest artifact and repository metadata file

The staged release contains {manifest['artifact_count']} manifest artifacts. The source manifest status is `{manifest['status']}` and `submission_ready={str(manifest['submission_ready']).lower()}`. Open scientific boundaries are documented rather than converted into positive validation claims.

## Reproduction entry points

From the repository root, restore the recorded Python environments and run the relevant scripts from `code/`. The primary package and gate-compilation runners default to local simulation and dry-run behavior; IBM credentials are intentionally excluded. Read `reproducibility/PSA_QAE_CCE_SUBMISSION_READINESS_2026-10-09.md` before interpreting evidence tiers.

## Licensing

Project code is released under the MIT License. Original text, tables, figures, and generated data are released under CC BY 4.0. Third-party source code and data are not redistributed by this compact release and remain under their original licenses and citations.

## Citation

Use `CITATION.cff`. Archived release: https://doi.org/{VERSION_DOI}
"""
    (destination / "README.md").write_text(text, encoding="utf-8")


def write_citation(destination: Path, author_data: dict) -> None:
    author_blocks = []
    for author in author_data["authors"]:
        parts = author["name_en"].split()
        given = " ".join(parts[:-1])
        family = parts[-1]
        author_blocks.extend(
            [
                f"  - family-names: \"{family}\"",
                f"    given-names: \"{given}\"",
                f"    orcid: \"https://orcid.org/{author['orcid']}\"",
                "    affiliation: \"Korea Gas Safety Corporation\"",
            ]
        )
    content = "\n".join(
        [
            "cff-version: 1.2.0",
            'message: "If you use this software or data, please cite the archived release."',
            'title: "Resource-aware quantum amplitude estimation for chance-constrained pressure swing adsorption: classical baselines, compiled oracle costs, and a hardware boundary"',
            "type: software",
            "version: 0.1.0",
            f"date-released: {date.today().isoformat()}",
            f'doi: "{VERSION_DOI}"',
            f'url: "https://doi.org/{VERSION_DOI}"',
            "authors:",
            *author_blocks,
            "keywords:",
            '  - "pressure swing adsorption"',
            '  - "quantum amplitude estimation"',
            '  - "chance constraints"',
            '  - "process systems engineering"',
            '  - "resource estimation"',
            "license: MIT",
            "repository-code: \"https://github.com/lyullee/psa-qae-resource-audit\"",
            "",
        ]
    )
    (destination / "CITATION.cff").write_text(content, encoding="utf-8")


def write_zenodo_metadata(destination: Path, author_data: dict) -> None:
    creators = []
    for author in author_data["authors"]:
        given, family = author["name_en"].rsplit(" ", 1)
        creators.append(
            {
                "name": f"{family}, {given}",
                "affiliation": "Korea Gas Safety Corporation",
                "orcid": author["orcid"],
            }
        )
    payload = {
        "title": "Resource-aware quantum amplitude estimation for chance-constrained pressure swing adsorption: classical baselines, compiled oracle costs, and a hardware boundary",
        "version": "0.1.0",
        "publication_date": date.today().isoformat(),
        "upload_type": "software",
        "description": (
            "Reproducibility package for a process-linked audit of quantum amplitude estimation in "
            "pressure swing adsorption, including classical baselines, process and circuit resource "
            "boundaries, external controls, and a nine-job three-backend IBM QPU experiment."
        ),
        "creators": creators,
        "access_right": "open",
        "license": "cc-by-4.0",
        "keywords": [
            "pressure swing adsorption",
            "quantum amplitude estimation",
            "chance-constrained optimization",
            "process systems engineering",
            "quantum resource estimation",
        ],
        "related_identifiers": [
            {
                "identifier": "https://github.com/lyullee/psa-qae-resource-audit",
                "relation": "isSupplementTo",
                "scheme": "url",
            }
        ],
        "notes": (
            "The package reports negative and conditional findings. It does not establish quantum "
            "advantage or industrial H2 validation. Original generated data and figures are also "
            "available under CC BY 4.0 as stated in the repository README."
        ),
    }
    (destination / ".zenodo.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_licenses(destination: Path) -> None:
    license_dir = destination / "LICENSES"
    license_dir.mkdir(exist_ok=True)
    mit = """MIT License

Copyright (c) 2026 Ugwiyeon Lee, Seong-Yun Bae, Hakrae Kim, and Jungsu Lee

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the \"Software\"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
    (destination / "LICENSE").write_text(mit, encoding="utf-8")
    (license_dir / "MIT.txt").write_text(mit, encoding="utf-8")
    (license_dir / "CC-BY-4.0.txt").write_text(
        "Original manuscript text, generated tables, figures, and data in this repository are licensed under Creative Commons Attribution 4.0 International (CC BY 4.0): https://creativecommons.org/licenses/by/4.0/legalcode\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--destination", type=Path, default=DEFAULT_DESTINATION)
    parser.add_argument(
        "--allow-open-gates",
        action="store_true",
        help="stage a boundary-paper release while submission_ready remains false",
    )
    args = parser.parse_args()

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    author_data = json.loads(AUTHORS.read_text(encoding="utf-8"))
    if not manifest["submission_ready"] and not args.allow_open_gates:
        raise RuntimeError("manifest has open gates; pass --allow-open-gates only for the disclosed boundary-paper release")

    destination = args.destination.resolve()
    allowed_parent = (ROOT / "10_TEA_LCA_Python" / "release").resolve()
    if destination != allowed_parent and allowed_parent not in destination.parents:
        raise RuntimeError(f"destination must remain under {allowed_parent}")
    destination.mkdir(parents=True, exist_ok=True)

    copied = []
    targets = set()
    for artifact in manifest["artifacts"]:
        source = ROOT / artifact["path"]
        if not source.is_file():
            raise FileNotFoundError(source)
        source_hash = sha256(source)
        if source_hash != artifact["sha256"] or source.stat().st_size != artifact["bytes"]:
            raise RuntimeError(f"source no longer matches manifest: {artifact['path']}")
        group_dir = GROUP_DIRECTORIES[artifact["group"]]
        target = destination / group_dir / source.name
        if target in targets:
            raise RuntimeError(f"target filename collision: {target}")
        targets.add(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        if sha256(target) != artifact["sha256"]:
            raise RuntimeError(f"staged hash mismatch: {target}")
        copied.append((target, artifact["sha256"]))

    write_readme(destination, manifest, author_data)
    write_citation(destination, author_data)
    write_zenodo_metadata(destination, author_data)
    write_licenses(destination)
    (destination / ".gitignore").write_text("__pycache__/\n*.py[cod]\n.env\n.venv/\n", encoding="utf-8")

    metadata_paths = [
        destination / "README.md",
        destination / "CITATION.cff",
        destination / ".zenodo.json",
        destination / "LICENSE",
        destination / "LICENSES" / "MIT.txt",
        destination / "LICENSES" / "CC-BY-4.0.txt",
        destination / ".gitignore",
    ]
    checksum_dir = destination / "checksums"
    checksum_dir.mkdir(exist_ok=True)
    checksum_lines = []
    for path, digest in copied + [(path, sha256(path)) for path in metadata_paths]:
        checksum_lines.append(f"{digest}  {path.relative_to(destination).as_posix()}")
    checksum_file = checksum_dir / "sha256.txt"
    checksum_file.write_text("\n".join(sorted(checksum_lines)) + "\n", encoding="utf-8")

    summary = {
        "status": "staged",
        "destination": str(destination),
        "manifest_artifacts": len(copied),
        "repository_metadata_files": len(metadata_paths) + 1,
        "total_files": len(copied) + len(metadata_paths) + 1,
        "submission_ready": manifest["submission_ready"],
        "open_gates": manifest["open_gates"],
        "qpu_submission": False,
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
