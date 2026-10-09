# Candidate-policy stream-to-event clean oracle

For each frozen recycle candidate, the two calibrated adsorption maps are collapsed algebraically into feed-H2, external-product-H2, and external-impurity registers. Recycle scaling is folded into the policy-specific coefficients. The three registers feed the purity/recovery comparisons, a joint CZ phase mark, and exact uncomputation.

| quantity | result |
|---|---:|
| encoded input interface | 29 variables x 12 bits = 348 qubits |
| selected aggregate precision | 19 bits |
| candidate-policy quantized/integer labels | 96/96 / 96/96 |
| ledger-support labels versus actual | 32/32 |
| p95 purity/recovery quantization error | 1.132e-08 / 1.109e-05 |
| maximum clean policy oracle | 510 qubits; 1,286,021 CX; depth 2,481,760 |

| policy | coefficient bits | logical qubits | aggregation CX | forward compute CX | clean oracle CX | clean depth |
|---:|---:|---:|---:|---:|---:|---:|
| 0.420 | 13 | 510 | 492,868 | 641,262 | 1,282,525 | 2,473,631 |
| 0.427 | 13 | 510 | 492,858 | 643,010 | 1,286,021 | 2,481,760 |
| 0.430 | 13 | 510 | 492,871 | 642,999 | 1,285,999 | 2,481,742 |

This closes the arithmetic path from encoded adsorption phase-start states and shared parameters through policy-specific stream aggregation, recycle scaling, joint event marking, and exact uncomputation. It does not supply those phase-start states by a stable physical/reversible repeated-cycle CSS calculation, and it excludes loading, routing/noise, external H2 validation, and any end-to-end advantage claim.

Artifacts: `PSA_QAE_CCE_PRIMARY_POLICY_STREAM_EVENT_ORACLE.json`, `PSA_QAE_CCE_PRIMARY_POLICY_STREAM_EVENT_ORACLE.csv`, `PSA_QAE_CCE_PRIMARY_POLICY_STREAM_EVENT_ORACLE_FIGURE.png`, `PSA_QAE_CCE_PRIMARY_POLICY_STREAM_EVENT_ORACLE_FIGURE.pdf`.
