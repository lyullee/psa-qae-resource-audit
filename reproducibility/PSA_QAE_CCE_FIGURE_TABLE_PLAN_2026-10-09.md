# CCE main-text figure and table plan

## Main figures

| No. | Purpose | Current source | Status |
|---|---|---|---|
| Figure 1 | Connect the process-decision experiment to the loader, reversible oracle, amplification, QPU, and validity audit | PSA_QAE_CCE_WORKFLOW_FIGURE.png/pdf | ready |
| Figure 2 | Compare probability error and policy selection for MC, RQMC, IS, and MLAE on the frozen event | PSA_QAE_CONTINUOUS_POLICY_SELECTION_FIGURE.png/pdf | ready; relabel for journal typography |
| Figure 3 | Show the equal-RMSE MC crossover, observed RQMC boundary, and optimistic QAE proxy | PSA_QAE_CCE_PRIMARY_RESOURCE_BOUNDARY_FIGURE.png/pdf | ready |
| Figure 4 | Show the end-to-end resource ladder: response-oracle precision, dense-loader boundary, calibrated phase-map precision, and affine-block CX cost | PSA_QAE_CCE_RESOURCE_LADDER_FIGURE.png/pdf | ready; generated directly from seven authoritative JSON artifacts |
| Figure 5 | Compare ideal and observed amplified probabilities and report the hardware MLAE estimate | FIG_QPU_MLAE_HARDWARE_BOUNDARY.png/pdf | ready; add future replication panel only after jobs exist |
| Figure 6 | Separate process-model discrepancy from independent public-model policy resolution | PSA_QAE_CCE_VALIDITY_BOUNDARY_FIGURE.png/pdf | ready; residual-stress, estimator scale, external purity direction, and resolution ratio combined |

The finite-table compiler, threshold-activity grid, IBM target preflight, detailed external numerical-refinement plots, and Thelen VA-10 independent H2 equalization-control figure belong in the Supporting Information.

## Main tables

| No. | Content | Authoritative source |
|---|---|---|
| Table 1 | Frozen policy candidates, chance event, prior, estimator budgets, endpoints, and prohibited claims | PSA_QAE_CCE_PRIMARY_CASE_PROTOCOL.json |
| Table 2 | MC/RQMC/IS/MLAE RMSE, MAE, bias, classification error, policy-selection interval, calls, and local timing | PSA_QAE_CONTINUOUS_POLICY_SELECTION.json |
| Table 3 | Eight decision-relevant resource tiers in the main text; the complete 29-tier ladder is Supplementary Table S1 | PSA_QAE_CCE_RESOURCE_TABLE3.json/csv/md; includes the 2,696–2,885-qubit gas-inventory-to-dynamic-Langmuir/transport/LDF/balance paths and the 647-qubit pressure-derived saturated/unsaturated proportional tank-allocation interface while preserving the counterfactual boundary and all exclusions |
| Table 4 | Eight claim-critical evidence tiers in the main text; the complete 30-tier hierarchy is Supplementary Table S2 | PSA_QAE_CCE_TABLE4_EVIDENCE_HIERARCHY.json/csv/md; manuscript Sections 2.1 and 2.4 |

## Supporting Information

1. Complete 200-replicate estimator records and reference-scramble results.
2. Threshold-activity grid and all candidate-policy probability summaries.
3. Finite-oracle truth-table verification, connectivity stress test, and IBM target preflight.
4. Response-oracle and calibrated phase-map fixed-point scans plus all 72 affine-block register/gate counts.
5. Dense-loader cell occupancy, fidelity check, and storage extrapolation.
6. Raw QPU counts, circuits, layouts, calibration record, runtime metrics, and retrieval metadata.
7. Phase ledger, equalization branch flags, CSS and mass-balance diagnostics.
8. External model scenarios, 1,200/4,800-point numerical refinement, and source/version provenance.
9. SHA-256 manifests, environment files, seeds, and the complete machine-readable claim audits.

## Required editorial pass

- Use one notation for event probability, policy, prior state, oracle, and query count across every panel.
- Distinguish samples, surrogate evaluations, amplitude-oracle queries, logical gates, native two-qubit gates, QPU charge time, and local wall time.
- Put the conditional-model and non-industrial-validation limits in the captions of Figures 2, 3, 4, and 6.
- Do not add a multi-backend panel until real job IDs, counts, and calibration records exist.
