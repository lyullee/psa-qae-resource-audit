# Joint normalized transport, LDF, and interior-cell balance

The frozen audit covers **12,928 interior-cell states**, **64,640 component balances**, and 32 parameter-specialized source rows. No QPU job was submitted.

| Component | factor bits | loading bits | affinity bits | reciprocal address bits | LDF coefficient bits | segments | next-gas p95 | next-gas max | branch mismatch |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| H2 | 9 | 26 | 8 | 11 | 8 | 2,048 | 1.869e-04 | 3.461e-04 | 6.033e-03 |
| CO2 | 8 | 26 | 8 | 9 | 8 | 512 | 1.182e-04 | 4.850e-04 | 1.052e-02 |
| CH4 | 9 | 38 | 8 | 10 | 8 | 1,024 | 7.346e-05 | 3.723e-04 | 1.181e-01 |
| CO | 7 | 36 | 8 | 8 | 8 | 256 | 1.716e-04 | 3.887e-04 | 1.327e-01 |
| N2 | 6 | 36 | 8 | 8 | 8 | 256 | 7.401e-05 | 4.340e-04 | 1.675e-01 |

The centre-cell current gas is taken directly from the same 18-bit gas inventories used for normalization and pressure reconstruction. The LDF path consumes the full 20-bit reconstructed pressure and normalized composition outputs. Generated face fluxes and generated adsorption/desorption terms enter the same balance; no independent current-gas, composition, face, or uptake registers are supplied.

The passing precision panel uses factor-quantized, run-specialized constants. It demonstrates the arithmetic interface and quantifies its precision/resource cost, but 32 specialized circuits are not one coherent scenario oracle. A reversible scenario-parameter register and its variable-coefficient arithmetic remain open.

| Direct compiled path | logical qubits | depth | CX |
|---|---:|---:|---:|
| H2 | 1,944 | 59,186,552 | 35,947,274 |
| CO2 | 1,960 | 35,145,371 | 22,128,076 |
| CH4 | 2,033 | 46,501,180 | 28,558,642 |
| CO | 2,039 | 32,668,327 | 20,709,266 |
| N2 | 2,033 | 32,612,294 | 20,670,468 |

The conservative serial additive upper bound has peak **2,039 logical qubits**, depth **206,113,724**, and **128,013,726 CX**. It repeats the common normalized-transport path five times and is therefore an upper bound, not a monolithic five-component transpilation.
