# Execution and claim boundaries

## Completed on the corrected pressure topology

- Six-cell, 60-cycle eight-corner operating-policy cube and eight predeclared hold-outs.
- Pressure and booster audit for the 6.2/6.0/6.5 bar routing.
- Stage-resolved polymer/Pd train, adaptive DOP853 guards, and independent RK4 replay.
- Continuous, affine, and 10-bit discrete probability calculations.
- Corrected 16-case DWSIM 8.7.1 Peng-Robinson pressure, duty, temperature, and closure audit.

## Portable arithmetic oracle completed

- The frozen integer event is serialized as exact OpenQASM 3.
- Exhaustive 2-, 3-, and 4-bit checks, all 16 direct 10-bit engineering states,
  and 4,096 seeded random 10-bit states give zero phase-label or restoration errors.
- The 10-bit construction requires 66 logical qubits and 24,042 CX gates before routing.

## IBM QPU final-event probe completed

- The exact final affine event at two bits per uncertainty variable was reduced
  to six input qubits and one flag through an exact three-cube complement cover.
- All 128 reversible input/flag mappings pass local statevector verification.
- All 64 zero-flag input states were run on IBM Kingston at 256 shots per state.
- Job `db6emt04qg6s73c4lja0` used 7 QPU s; 64/64 states were majority-correct.
- A separate read-only retrieval exactly matched all 64 archived count dictionaries.

## Quantum work that remains external

- Coherent state preparation and amplitude-estimation iterations.
- Hardware execution of the 42-logical-qubit two-bit arithmetic oracle or the
  66-logical-qubit ten-bit arithmetic oracle.
- Any claim of quantum speedup, cost advantage, or fault-tolerant resource sufficiency.

## Experimental boundary

Public studies support model family, concentration polarization, pressure and
temperature feasibility, recovery scale, aging stress, and rejection controls.
The Chen and Voigt tables additionally support the purity-recovery trade-off,
purge-allocation cost, and feed-dependent cycle settings without local refitting.
No public experiment synchronously measures the final five-component product
at the declared ppm limits for this exact integrated PSA/membrane topology.
