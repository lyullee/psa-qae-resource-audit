# Execution and claim boundaries

## Completed on the corrected pressure topology

- Six-cell, 60-cycle eight-corner operating-policy cube.
- Eight predeclared interior hold-outs.
- Pressure and booster audit for the 6.2/6.0/6.5 bar routing.
- Stage-resolved polymer/Pd train over all 16 cases.
- Adaptive DOP853 finite-selectivity, defect, and permeance-loss guards.
- Independent fixed-area RK4 mesh replay of both final guard designs.
- Continuous, affine, and 10-bit discrete probability calculations.
- Corrected component-specific module selectivity acceptance audit.

## Portable oracle completed

- The frozen integer event is serialized as OpenQASM 3 using an exact
  Clifford+T decomposition and verified by exhaustive small-register tests,
  all 16 direct 10-bit engineering states, and 4,096 seeded random 10-bit
  states.

## Requiring another execution host

- Device-specific Qiskit optimization, coupling-map routing, and hardware
  execution. The present Windows Application Control policy blocks the native
  rustworkx DLL.
- DWSIM execution of the corrected 16-case deck. The same policy blocks
  DWSIM.FileStorage.dll before a flowsheet can solve.

## Experimental boundary

Public studies support model family, concentration polarization, pressure and
temperature feasibility, recovery scale, aging stress, and rejection controls.
No public experiment synchronously measures the final five-component product
at the declared ppm limits for this exact integrated PSA/membrane topology.
