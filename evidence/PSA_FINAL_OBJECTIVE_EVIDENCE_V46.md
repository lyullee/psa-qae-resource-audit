# Pressure-consistent PSA/QAE evidence V46

The corrected process uses passive fill from the 6.2 bar product manifold to a 6.0 bar regeneration tank and a booster from the tank to the 6.5 bar purge/repressurization header.

- Selected operating policy: 6.0 bar tank, 4 s active purge, 540 s adsorption.
- Selected direct cases: 8/8 corners and 8/8 predeclared holdouts.
- Qualified H2 improvement: 6.785-7.341%.
- Corrected 20% loss guard: 0.554 m2; 50% actual-syngas stress guard: 0.887 m2.
- Chance-area conservative probability: 0.951210; 10-bit discrete probability: 0.950629.
- Portable OpenQASM 3 oracle: 66 logical qubits, 24,042 CX gates, all-to-all depth 36,163; zero phase or restoration errors in the reported exhaustive/direct/random checks.
- Actual IBM QPU final-event check: job `db6emt04qg6s73c4lja0` on `ibm_kingston`, 64/64 majority-correct two-bit states at 256 shots/state, mean expected-label fraction 0.839, and 7 s QPU usage; live retrieval reproduced all 64/64 archived count dictionaries.
- Corrected DWSIM 8.7.1 Peng-Robinson cross-check: 16/16 cases solved at a 6.2 bar inlet; maximum component-balance error 8.945e-19 mol/s; compression 3.091-3.183 kWh/kg H2.
- Current execution boundary: the exact seven-qubit Boolean compilation of the final event at two-bit resolution has device-specific routing and IBM hardware evidence; coherent QAE, execution of the 42-qubit two-bit arithmetic oracle or complete 66-logical-qubit ten-bit oracle, and a matched integrated process experiment remain external.