# Pressure-consistent regeneration-reserve-aware hydrogen PSA and QAE event

This is the **v0.2.1** reproducibility package for a Separation and
Purification Technology-oriented study. It supersedes v0.1.0 because the former
7.0 bar regeneration tank could not be passively filled from the 6.2 bar
product manifold.

## Current engineering result

- Corrected topology: 6.2 bar product manifold -> 6.0 bar regulated tank ->
  discharge booster -> 6.5 bar purge/repressurization header.
- Selected policy: 4 s active purge and 540 s adsorption; comparison: 6 s and
  480 s. Both use the same 6.0 bar tank set point.
- Direct decisions: 8/8 uncertainty corners and 8/8 predeclared hold-outs pass;
  the comparison passes 0/8 corners.
- Qualified H2 shipment improves by 6.785-7.341%; conservative regeneration
  booster duty is at most 0.197 kWh kg-1 qualified H2.
- The ideal stage-resolved train uses 0.1892 m2 polymer and 0.4799 m2 dense Pd.
- The 20%-permeance-loss guard is 0.554 m2 and passes 16/16 direct cases.
- A public 50%-retention actual-syngas stress requires 0.887 m2 and passes 16/16.
- Corrected module selectivity guards are H2/CO >=5,660, H2/CO2 >=168,660,
  H2/N2 >=540, and H2/CH4 >=40; the simultaneous rounded vector passes 16/16.
- Independent fixed-area RK4 reproduces all 32 DOP853 design-case labels.
- The 0.440 m2 chance design has conservative continuous probability 0.951210
  and 10-bit probability 0.950629 with zero direct label errors.
- Reversible register allocation requires 66 logical qubits.
- The included OpenQASM 3 oracle has 24,042 CX gates, 61,269 primitive gates,
  and all-to-all depth 36,163 before device optimization or routing. Its
  reported basis-state tests have zero phase-label or work-qubit-restoration
  errors.
- A corrected DWSIM 8.7.1 Peng-Robinson cross-check solved all 16 cases at the
  physical 6.2 bar inlet with component-balance error below 8.95e-19 mol s-1.
  Adiabatic compression is 3.091-3.183 kWh kg-1 H2, 16.94-16.98% above the
  matched isothermal lower bound.

## Execution boundary

The corrected integer specification, portable OpenQASM 3 oracle, corrected
DWSIM input deck, DWSIM outputs, saved cases, and audit are included. Windows
Application Control rejected only the distributed DWSIM.FileStorage assembly;
an assembly-identical local build from the official DWSIM 8.7.1 source enabled
the run. The exact source, rebuilt assembly, hashes, and execution provenance
are included. Device-specific Qiskit optimization/routing remains external.

## Contents

- `manuscript/`: render-checked Word, PDF, Markdown, and reference audit.
- `evidence/`: V45 consolidated evidence, gates, progress, and hashes.
- `results/`: corrected machine-readable calculation records and public-data audits.
- `source/`: scripts needed to rerun the corrected analyses and rebuild artifacts.
- `dwsim_crosscheck/`: corrected input, 16-case outputs, saved cases, figures,
  official-source rebuild provenance, and runner/finalizer tools.
- `figures/`: 19 manuscript figures.
- `checksums/sha256.txt`: file-level SHA-256 ledger.

The package does not claim current quantum advantage or matched experimental
certification of the final integrated apparatus. The remaining external checks
are stated in `EXECUTION_BOUNDARIES.md`.
