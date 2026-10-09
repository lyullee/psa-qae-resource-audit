# Gas-inventory-generated product-cell LDF, valve, and balance

The frozen audit covers **6,464 product-end states** and **32,320 component balances**. Each path starts from two encoded five-component gas inventories and one current loading; both compositions and pressures, the inward face, product LDF transfer, and valve withdrawal are generated inside the reversible path. No QPU job was submitted.

| Component | factor bits | address bits | loading bits | next-gas p95 | next-gas max | erasure | underflow |
|---|---:|---:|---:|---:|---:|---:|---:|
| H2 | 9 | 11 | 26 | 1.614e-04 | 2.194e-04 | 0.000e+00 | 0.000e+00 |
| CO2 | 8 | 9 | 26 | 2.114e-04 | 3.858e-04 | 0.000e+00 | 0.000e+00 |
| CH4 | 9 | 10 | 38 | 1.117e-04 | 4.400e-04 | 0.000e+00 | 0.000e+00 |
| CO | 7 | 9 | 38 | 1.504e-04 | 3.400e-04 | 0.000e+00 | 0.000e+00 |
| N2 | 6 | 11 | 36 | 7.580e-05 | 4.980e-04 | 0.000e+00 | 0.000e+00 |

| Component | logical qubits | depth | CX | u |
|---|---:|---:|---:|---:|
| H2 | 1,803 | 55,305,763 | 33,998,962 | 40,788,534 |
| CO2 | 1,813 | 31,377,808 | 20,253,112 | 22,687,808 |
| CH4 | 1,937 | 42,577,283 | 26,660,122 | 30,787,620 |
| CO | 1,952 | 33,385,169 | 21,480,812 | 24,069,085 |
| N2 | 1,929 | 60,835,766 | 37,020,740 | 44,276,078 |

The conservative common-path-repeating upper bound is **1,952 peak logical qubits**, all-to-all depth **223,481,789**, and **139,413,748 additive CX**.

This closes the previous product-path gap in which product composition and inward-face flux were supplied. Coherent run parameters, a monolithic five-component transpilation, valve scheduling, tank withdrawal, adaptive integration, full phase/cycle control, routing, hardware feasibility, and quantum advantage remain open.
