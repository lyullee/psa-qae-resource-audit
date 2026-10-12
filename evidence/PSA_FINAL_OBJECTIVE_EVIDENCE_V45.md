# Pressure-consistent PSA/QAE evidence V45

The corrected process uses passive fill from the 6.2 bar product manifold to a 6.0 bar regeneration tank and a booster from the tank to the 6.5 bar purge/repressurization header.

- Selected operating policy: 6.0 bar tank, 4 s active purge, 540 s adsorption.
- Selected direct cases: 8/8 corners and 8/8 predeclared holdouts.
- Qualified H2 improvement: 6.785-7.341%.
- Corrected 20% loss guard: 0.554 m2; 50% actual-syngas stress guard: 0.887 m2.
- Chance-area conservative probability: 0.951210; 10-bit discrete probability: 0.950629.
- Portable OpenQASM 3 oracle: 66 logical qubits, 24,042 CX gates, all-to-all depth 36,163; zero phase or restoration errors in the reported exhaustive/direct/random checks.
- Corrected DWSIM 8.7.1 Peng-Robinson cross-check: 16/16 cases solved at a 6.2 bar inlet; maximum component-balance error 8.945e-19 mol/s; compression 3.091-3.183 kWh/kg H2.
- Current external-execution boundary: device-specific Qiskit optimization/routing and hardware execution remain optional future steps; the portable QASM and corrected DWSIM process cross-check are complete.