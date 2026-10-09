# Direct pressure-to-two-face-to-interior-cell composition

The frozen precision screen covers **12,928 interior-cell states** and **64,640 component balances**. No QPU job was submitted.

| Component | non-face input bits | face-flux bits | next bits | propagated p95 / next scale | propagated max / next scale | arithmetic-only p95 |
|---|---:|---:|---:|---:|---:|---:|
| H2 | 16 | 28 | 20 | 9.994e-05 | 1.936e-04 | 8.928e-06 |
| CO2 | 16 | 28 | 20 | 8.480e-06 | 7.402e-05 | 7.543e-06 |
| CH4 | 16 | 28 | 20 | 2.029e-05 | 4.861e-05 | 7.557e-06 |
| CO | 16 | 28 | 20 | 1.204e-04 | 1.728e-04 | 1.254e-05 |
| N2 | 16 | 28 | 20 | 5.671e-05 | 8.707e-05 | 8.548e-06 |

The clean direct circuit uses **1,508 logical qubits**, all-to-all depth **12,250,291**, and **8,328,622 CX** in the `u/CX` basis. It retains **810** input/output qubits and clears **698** work qubits.

The circuit computes three pressures and both five-component internal-face transfers, consumes those exact temporary flux registers in the centre-cell balances, copies five next-gas inventories, and reverses all pressure/face work. Composition normalization, direct centre-cell LDF/loading coupling, run-specific parameters, boundary/tank withdrawal, adaptive phase integration, routing, and a complete cycle remain open.
