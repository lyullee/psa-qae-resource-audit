# Pressure-consistent regeneration-reserve-aware hydrogen PSA and QAE event

This is the **v0.2.3** reproducibility package for a Separation and
Purification Technology-oriented study. It contains the corrected process
model, public-data checks, process-simulator cross-check, portable probability
oracle, and the final-event IBM QPU probe.

## Current engineering result

- Corrected topology: 6.2 bar product manifold -> 6.0 bar regulated tank ->
  discharge booster -> 6.5 bar purge/repressurization header.
- The selected 4 s purge and 540 s adsorption policy passes 8/8 uncertainty
  corners and 8/8 predeclared hold-outs; the 6 s/480 s comparison passes 0/8.
- Qualified H2 shipment improves by 6.785-7.341%, with regeneration-booster
  duty no greater than 0.197 kWh kg-1 qualified H2.
- The 0.554 m2 20%-permeance-loss guard and 0.887 m2 public actual-syngas
  50%-retention guard each pass all 16 direct cases.
- Independent fixed-area RK4 reproduces all 32 DOP853 design-case labels.
- Two post-freeze public experimental hold-outs were added without fitting:
  the Chen 13-run two-bed H2/CO2 VPSA table passes 12/12 directional endpoint
  checks, and the Voigt 13-run four-bed H2/CH4 PSA table gives 6/13
  source-event passes with at least one pass in every transient feed stage.
- Corrected DWSIM 8.7.1 Peng-Robinson calculations solve all 16 cases at the
  physical 6.2 bar inlet. Compression is 3.091-3.183 kWh kg-1 H2.
- The 0.440 m2 chance design has continuous affine probability 0.951210 and
  10-bit probability 0.950629, an absolute discretization error of 0.000581.
- The complete portable arithmetic oracle requires 66 logical qubits and has
  24,042 CX gates, 61,269 primitive gates, and all-to-all depth 36,163 before
  device optimization or routing.
- The exact two-bit reduction of the **same final event** was compiled to a
  seven-qubit Boolean circuit and executed on IBM Kingston as job
  `db6emt04qg6s73c4lja0`. All 64 inputs were majority-correct at 256 shots per
  state; mean expected-label probability was 0.8389, minimum was 0.6523, and
  usage was 7 QPU s. Read-only retrieval reproduced all 64 count dictionaries.

## Quantum claim boundary

The IBM result is an exhaustive basis-state truth-mapping test at two-bit
resolution. It connects the final engineering inequality to real-device
compilation, routing, and measurement. It is not coherent amplitude
estimation, execution of the 42-qubit two-bit arithmetic oracle or the
66-qubit ten-bit arithmetic oracle, and it is not evidence of quantum
advantage. RQMC remains the practical estimator for the present three-variable
event.

## Contents

- `manuscript/`: render-checked Word, PDF, Markdown, and reference audit.
- `evidence/`: V46 consolidated evidence, gates, progress, and hashes.
- `results/ibm_final_event_2bit_probe/`: routed resources, all 64 raw count
  dictionaries, QASM, figure, and read-only job verification.
- `results/`: corrected machine-readable calculations and public-data audits.
- `results/spt_external_experimental_holdouts_v1/`: digitized Chen and Voigt
  tables, acceptance contract, statistics, figure, and hashes.
- `source/`: rerun scripts, including guarded free-Open-Plan IBM execution and
  read-only verification.
- `dwsim_crosscheck/`: corrected DWSIM inputs, outputs, saved cases, and build
  provenance.
- `figures/`: 19 manuscript figures.
- `checksums/sha256.txt`: file-level SHA-256 ledger.

The remaining principal external check is a synchronized component-resolved
experiment on the final integrated PSA and membrane apparatus.
