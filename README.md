# Resource-aware quantum amplitude estimation for chance-constrained pressure swing adsorption: classical baselines, compiled oracle costs, and a hardware boundary

This repository is the reproducibility package for a *Computers & Chemical Engineering* manuscript on chance-constrained pressure swing adsorption (PSA), matched classical and quantum probability estimators, reversible-oracle resource accounting, and a nine-job, three-backend IBM QPU hardware boundary.

## Authors

Ugwiyeon Lee, Seong-Yun Bae, Hakrae Kim, Jungsu Lee. All authors are affiliated with Korea Gas Safety Corporation, Republic of Korea. Ugwiyeon Lee is the corresponding author. ORCIDs and the CRediT statement are recorded in `reproducibility/PSA_QAE_CCE_AUTHOR_METADATA.md`.

## Supported conclusions

- Scrambled-Sobol RQMC is the best current estimator for the frozen smooth, moderate-dimensional surrogate.
- Noiseless MLAE improves over matched crude Monte Carlo but does not create an end-to-end advantage after state loading, reversible process evaluation, and hardware noise are counted.
- The compiled process/event tiers include direct five-component LDF-to-loading-sign-to-solid-conversion-to-interior-cell-balance circuits, gas-inventory-normalized interior and product-cell paths, a finite-support run/schedule controller, coefficient generation, and five paths that connect three raw gas-inventory vectors through normalization, pressure reconstruction, two oriented faces, the run-affinity Langmuir denominator/reciprocal, q*/LDF/loading conversion, and conservative balance. These highest component paths compile to 2,696–2,885 logical qubits and 55,337,688–56,289,028 CX per component, with a 279,319,932-CX repeated-path upper bound. A 557-qubit/195,276-CX pressure-derived circuit replaces the recorded tank-withdrawal lookup on all 128 frozen saturated calls. A 647-qubit/705,194-CX extension preserves 128 observed saturated and 224 bounded-counterfactual unsaturated proportional-allocation labels. A separate 845-qubit/1,078,054-CX source-model control supplies 128 physically generated unsaturated, zero-makeup calls using start/end-pressure trapezoidal demand. It keeps the recycle fraction but uses a declared 0.02-s non-adsorption schedule; frozen-schedule unsaturated coverage and monolithic five-component phase integration remain open.
- Public H2 evidence and independent simulator controls do not validate the selected industrial recycle policy. This limitation is retained as part of the result.

The repository does **not** claim quantum advantage, industrial H2 validation, a global recycle optimum, or deployment readiness.

## Contents

- `manuscript/`: review manuscript, figures, tables, references, highlights, and cover-letter draft
- `results/`: machine-readable estimator, process, circuit, QPU, external-control, and audit outputs
- `code/`: local generation, compilation, audit, and verification scripts
- `reproducibility/`: environments, submission checks, author metadata, and readiness records
- `checksums/sha256.txt`: SHA-256 values for every copied manifest artifact and repository metadata file

The staged release contains 360 manifest artifacts. The source manifest status is `local_submission_packet_assembled_external_evidence_gates_open` and `submission_ready=false`. Open scientific boundaries are documented rather than converted into positive validation claims.

## Reproduction entry points

From the repository root, restore the recorded Python environments and run the relevant scripts from `code/`. The primary package and gate-compilation runners default to local simulation and dry-run behavior; IBM credentials are intentionally excluded. Read `reproducibility/PSA_QAE_CCE_SUBMISSION_READINESS_2026-10-09.md` before interpreting evidence tiers.

## Licensing

Project code is released under the MIT License. Original text, tables, figures, and generated data are released under CC BY 4.0. Third-party source code and data are not redistributed by this compact release and remain under their original licenses and citations.

## Citation

Use `CITATION.cff`. Archived release: https://doi.org/10.5281/zenodo.23271867
