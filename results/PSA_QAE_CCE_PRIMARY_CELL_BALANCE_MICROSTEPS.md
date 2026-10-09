# Clean five-component interior-cell gas-balance accumulators

The physical screen contains **12,928 interior-cell states** and **64,640 component balances**. Every exact one-second next-gas value is positive.

| Component | input bits/term | next bits | p95 error / next scale | max error / next scale | qubits | CX |
|---|---:|---:|---:|---:|---:|---:|
| H2 | 16 | 20 | 1.707e-05 | 2.660e-05 | 204 | 70,584 |
| CO2 | 16 | 20 | 7.302e-06 | 1.052e-05 | 199 | 74,100 |
| CH4 | 16 | 20 | 7.563e-06 | 1.016e-05 | 199 | 72,642 |
| CO | 16 | 20 | 7.638e-06 | 1.004e-05 | 198 | 68,676 |
| N2 | 16 | 22 | 7.125e-06 | 8.008e-06 | 209 | 80,800 |

Sequential workspace-reuse accounting retains all sign-split balance inputs and next-gas outputs at **609 logical qubits** and **366,802 additive CX**.

This closes the clean interior-cell accumulation interface. Reversible sign extraction from loading differences, direct monolithic composition with the LDF/face modules, boundary-cell terms, adaptive integration, routing, and a complete phase/cycle remain open.

No QPU job was submitted.
