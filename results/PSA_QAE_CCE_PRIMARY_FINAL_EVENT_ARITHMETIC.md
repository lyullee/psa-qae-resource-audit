# Primary final purity/recovery event arithmetic

The final-cycle ledger is reduced to three aggregate stream registers: adsorption-feed H2, external-product H2, and external-product impurity. Separate physical scales are used for the three unsigned registers. The purity and recovery divisions are replaced by integer cross-multiplications, two retained flags are joined by a controlled phase, and the complete flag computation is uncomputed.

| quantity | result |
|---|---:|
| selected bits per aggregate stream | 16 |
| p95 purity quantization error | 1.638e-09 |
| p95 recovery quantization error | 9.881e-06 |
| coefficient fractional bits | 8 |
| quantized/integer event matches | 32/32 / 32/32 |
| forward flag compute | 125 qubits; 91,490 CX; depth 177,727 |
| clean joint phase oracle | 125 qubits; 182,981 CX; depth 355,454 |

The precision rule is stricter than label retention: p95 quantization error must stay below 10% of the nested-held-out phase-stream p95 error for both purity and recovery. The selected 16-bit registers satisfy both budgets and retain all 32 labels. Six coefficient bits are sufficient to keep the rationalized cross-multiplication error below 10% of the closest normalized decision margin while preserving both comparator flags on every row.

This closes the calibrated final event-arithmetic block from three aggregate stream registers through clean phase marking. It does not yet synthesize the upstream per-phase stream sums, constant recycle scaling, or the repeated spatial/tank CSS update into the same reversible circuit.

Artifacts: `PSA_QAE_CCE_PRIMARY_FINAL_EVENT_ARITHMETIC.json`, `PSA_QAE_CCE_PRIMARY_FINAL_EVENT_ARITHMETIC.csv`, `PSA_QAE_CCE_PRIMARY_FINAL_EVENT_ARITHMETIC_FIGURE.png`, `PSA_QAE_CCE_PRIMARY_FINAL_EVENT_ARITHMETIC_FIGURE.pdf`.
