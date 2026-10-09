# Direct gas-normalized internal-face cell balance

The frozen screen covers **25,856 normalization states**, **12,928 interior-cell states**, and **64,640 component balances**. No QPU job was submitted.

The first end-to-end passing design uses **22-bit common amounts**, **22-bit reciprocals**, **8 address bits (256 support-adaptive segments)**, and five **20-bit** composition outputs. The largest component p95 absolute composition error is **2.071e-04** and the largest maximum error is **3.105e-04**, with zero nonzero-value erasure and zero output overflow.

| Component | composition p95 abs. | face-flux p95 / flow scale | next-gas p95 / next scale |
|---|---:|---:|---:|
| H2 | 2.071e-04 | 1.766e-04 | 1.358e-04 |
| CO2 | 2.784e-06 | 1.435e-06 | 1.145e-05 |
| CH4 | 1.138e-06 | 9.932e-07 | 2.205e-05 |
| CO | 8.869e-07 | 7.881e-07 | 1.622e-04 |
| N2 | 1.146e-06 | 1.139e-06 | 5.419e-05 |

The clean standalone normalizer uses **333 logical qubits**, all-to-all depth **2,153,892**, and **1,340,232 CX**. The clean direct normalized transport-balance circuit uses **1,651 logical qubits**, all-to-all depth **22,143,683**, and **14,667,150 CX**. It retains **610** input/output qubits and clears **1,041** work qubits.

The circuit no longer accepts independently supplied upwind composition. Its reciprocal thresholds and table are calibrated to the frozen left/centre-cell support. Out-of-support normalization, direct centre-cell LDF/loading coupling, run-specific parameters, boundary/tank withdrawal, adaptive phase integration, routing, and a complete cycle remain open.
