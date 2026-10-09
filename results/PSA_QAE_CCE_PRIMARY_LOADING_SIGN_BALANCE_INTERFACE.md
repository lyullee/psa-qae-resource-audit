# Reversible loading-sign extraction and interior-cell balance interface

The screen covers **12,928 interior-cell states** and **64,640 component balances**. A three-bit exhaustive control checks all **64** current/next loading pairs with zero branch, magnitude, or workspace mismatch.

| Component | earlier LDF bits | interface bits | added bits | p95 next error | max next error | integrated qubits | integrated CX |
|---|---:|---:|---:|---:|---:|---:|---:|
| H2 | 20 | 26 | 6 | 1.706e-05 | 2.660e-05 | 383 | 139,600 |
| CO2 | 24 | 26 | 2 | 7.449e-06 | 1.147e-05 | 394 | 269,948 |
| CH4 | 20 | 32 | 12 | 7.563e-06 | 1.016e-05 | 428 | 329,738 |
| CO | 20 | 32 | 12 | 7.735e-06 | 1.004e-05 | 431 | 343,680 |
| N2 | 20 | 30 | 10 | 7.125e-06 | 8.008e-06 | 430 | 328,916 |

Sequential workspace-reuse accounting retains all five component inputs and next-gas outputs at **934 logical qubits** and **1,411,882 additive CX**.

The widened register requirement is itself a resource result: precision adequate for q_next can erase the much smaller signed q_next-q_current transfer. The compiled interface closes sign extraction and solid-mass conversion from supplied current/next loading registers. Direct composition with the existing lower-width LDF outputs, face circuits, boundary terms, adaptive integration, routing, and a complete phase/cycle remain open.

No QPU job was submitted.
