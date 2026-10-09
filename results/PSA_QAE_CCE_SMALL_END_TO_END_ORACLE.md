# Small coherent end-to-end PSA-oracle connection control

Two three-bit inventory registers undergo reversible constant updates, a one-unit conservative equalization with retained direction ancillas, two integer threshold comparisons, a joint-event phase mark, and exact uncomputation. All 64 data basis states are verified simultaneously in coherent superposition.

| layer | logical qubits | depth | CX | u |
|---|---:|---:|---:|---:|
| forward compute | 15 | 198 | 148 | 240 |
| clean phase oracle | 15 | 405 | 304 | 465 |

The proxy joint event holds for `16/64 = 0.250000` basis states. The forward mapping maximum amplitude error is `1.700e-16` and the compute–phase–uncompute oracle error is `2.776e-16`. All nine work/event qubits return to zero and all 64 phase labels match.

This is a structural circuit control. It demonstrates coherent connection of the previously separate modules but does not replace the calibrated 11/16-bit affine resource estimate, repeated CSS, or the primary H2 purity/recovery event.

Artifacts: `PSA_QAE_CCE_SMALL_END_TO_END_ORACLE.json`, `PSA_QAE_CCE_SMALL_END_TO_END_ORACLE.csv`, `PSA_QAE_CCE_SMALL_END_TO_END_ORACLE_FIGURE.png`.
