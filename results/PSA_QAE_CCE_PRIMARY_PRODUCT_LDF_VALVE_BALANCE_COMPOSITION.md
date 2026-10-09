# Direct product-cell LDF, valve, and boundary balance

The frozen audit covers **6,464 product-end states**, **32,320 component balances**, and 32 parameter-specialized source rows. The valve is active in **3,232 states**. No QPU job was submitted.

| Component | factor bits | address bits | loading bits | next-gas p95 | next-gas max | transfer erasure | underflow |
|---|---:|---:|---:|---:|---:|---:|---:|
| H2 | 9 | 11 | 26 | 1.512e-04 | 2.305e-04 | 0.000e+00 | 0.000e+00 |
| CO2 | 8 | 9 | 26 | 2.127e-04 | 4.755e-04 | 0.000e+00 | 0.000e+00 |
| CH4 | 9 | 10 | 38 | 9.766e-05 | 3.734e-04 | 0.000e+00 | 0.000e+00 |
| CO | 7 | 9 | 38 | 8.407e-05 | 3.390e-04 | 0.000e+00 | 0.000e+00 |
| N2 | 6 | 11 | 36 | 3.378e-05 | 4.740e-04 | 0.000e+00 | 0.000e+00 |

| Component | logical qubits | depth | CX | u |
|---|---:|---:|---:|---:|
| H2 | 1,074 | 39,624,718 | 23,836,418 | 29,868,634 |
| CO2 | 1,072 | 15,670,199 | 10,060,060 | 11,731,563 |
| CH4 | 1,188 | 26,823,018 | 16,433,266 | 19,792,667 |
| CO | 1,195 | 17,641,524 | 11,248,412 | 13,047,634 |
| N2 | 1,174 | 45,153,788 | 26,810,396 | 33,288,803 |

The conservative common-path-repeating upper bound is **1,195 peak logical qubits**, all-to-all depth **144,913,247**, and **88,388,552 additive CX**.

Each component circuit shares one encoded pressure/composition input between its competitive-Langmuir/LDF and product-valve modules, maps the generated loading change through sign and solid-mass conversion, consumes the generated adsorption/desorption and outlet flux in one conservative balance, copies next gas, and exactly reverses all work. Composition normalization, inward-face generation, coherent run parameters, five-component monolithic composition, valve scheduling, tank withdrawal, adaptive integration, routing, and a complete phase/cycle remain open.
