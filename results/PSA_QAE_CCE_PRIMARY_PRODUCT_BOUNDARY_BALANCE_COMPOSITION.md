# Direct product-valve-to-boundary-cell composition

The frozen precision screen covers **6,464 product-end states** and **32,320 component balances**. The valve is active in **3,232 states**. No QPU job was submitted.

| Component | nonvalve input bits | valve flux bits | next-gas bits | p95 scaled error | max scaled error | minimum next gas (mol) |
|---|---:|---:|---:|---:|---:|---:|
| H2 | 16 | 20 | 20 | 6.529e-05 | 8.247e-05 | 1.105e-02 |
| CO2 | 16 | 20 | 20 | 8.366e-06 | 1.129e-04 | 5.136e-04 |
| CH4 | 16 | 20 | 20 | 8.462e-06 | 1.139e-04 | 1.677e-05 |
| CO | 16 | 20 | 20 | 2.103e-05 | 1.299e-04 | 2.226e-05 |
| N2 | 16 | 20 | 20 | 8.862e-06 | 1.139e-04 | 5.594e-05 |

The clean five-component direct circuit uses **842 logical qubits**, all-to-all depth **3,285,605**, and **2,348,388 CX** in the `u/CX` basis. It retains **528** input/output qubits and clears **314** work qubits.

The circuit computes all five product-valve component fluxes, consumes those exact temporary registers in the product-end material balances, copies five next-gas inventories, and reverses all valve/flux work. Composition normalization, direct product-cell LDF coupling, valve scheduling, adaptive phase integration, tank withdrawal, routing, and a complete cycle remain open.
