# Clean five-component competitive-Langmuir/LDF microsteps

The precision screen covers **25,856** physical cell states from the 32-run, 100-cycle cache. Each component uses the shared five-component competitive-Langmuir denominator and a component-specific numerator and LDF coefficient.

| Component | bits | reciprocal segments | q* p95 rel. | q* p95 / register scale | LDF p95 rel. | LDF p95 / register scale | qubits | CX |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| H2 | 20 | 256 | 0.2521% | 0.2312% | 0.1762% | 0.1604% | 494 | 1,965,308 |
| CO2 | 24 | 32 | 4.0855% | 0.0077% | 0.0726% | 0.0003% | 515 | 1,225,138 |
| CH4 | 20 | 16 | 29.4796% | 0.0005% | 11.0339% | 0.0001% | 490 | 1,118,920 |
| CO | 20 | 16 | 41.7569% | 0.0002% | 6.8583% | 0.0001% | 490 | 1,118,920 |
| N2 | 20 | 16 | 18.8231% | 0.0003% | 5.9765% | 0.0001% | 490 | 1,119,076 |

The all-component gate requires q* and LDF-next p95 absolute errors below **0.25% of the component loading-register range**, zero loading overflow, and zero erasure of nonzero q*. CO2 additionally retains the original 5%/0.1% relative-error gates. Raw relative errors are reported because they become large for trace loadings near zero.

With component arithmetic workspace reused sequentially and all current/next loading registers retained, the modular accounting is **675 logical qubits**, **6,547,362 CX**, and additive all-to-all depth **10,337,687**.

This closes the five-component equilibrium/loading microstep item only. Gas transport, pressure evolution, valves, product tank balances, adaptive phase integration, routing, and the complete cyclic oracle remain outside the compiled circuit.
