# Pressure-consistent PSA/QAE evidence V44

The corrected process uses passive fill from the 6.2 bar product manifold to a 6.0 bar regeneration tank and a booster from the tank to the 6.5 bar purge/repressurization header.

- Selected operating policy: 6.0 bar tank, 4 s active purge, 540 s adsorption.
- Selected direct cases: 8/8 corners and 8/8 predeclared holdouts.
- Qualified H2 improvement: 6.785-7.341%.
- Corrected 20% loss guard: 0.554 m2; 50% actual-syngas stress guard: 0.887 m2.
- Chance-area conservative probability: 0.951210; 10-bit discrete probability: 0.950629.
- Portable OpenQASM 3 oracle: 66 logical qubits, 24,042 CX gates, all-to-all depth 36,163; zero phase or restoration errors in the reported exhaustive/direct/random checks.
- Current external-execution boundary: device-specific Qiskit optimization/routing and corrected DWSIM execution require a host that does not block their native DLLs; neither is needed to reproduce the included portable QASM.