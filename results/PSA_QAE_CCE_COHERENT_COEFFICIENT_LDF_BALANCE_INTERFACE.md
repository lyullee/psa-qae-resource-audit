# Coherent coefficient-to-LDF/loading/balance interface

Status: **coherent_run_coefficients_consumed_in_five_schedule_gated_component_ldf_loading_balance_paths_dynamic_denominator_open**

The five-qubit run address and three-qubit schedule address generate the run-specific equilibrium/LDF coefficients. A bed selector masks LDF uptake outside adsorption. Each component path consumes a supplied 20-bit Langmuir response, produces q*, updates loading, converts the loading change to a signed gas term, accumulates one conservative gas balance, and reverses all controller and arithmetic workspace.

| component | response bits | loading bits | q* p95/max | LDF-next p95/max | next-gas p95/max | pass |
|---|---:|---:|---:|---:|---:|---|
| H2 | 20 | 26 | 3.033e-05/4.324e-05 | 2.042e-05/3.165e-05 | 7.815e-05/1.792e-04 | True |
| CO2 | 20 | 26 | 4.278e-07/2.628e-06 | 2.577e-08/1.101e-07 | 6.933e-06/7.681e-05 | True |
| CH4 | 20 | 38 | 4.027e-07/5.745e-07 | 7.925e-08/1.111e-07 | 3.938e-05/7.812e-05 | True |
| CO | 20 | 36 | 4.038e-07/4.705e-07 | 6.064e-08/7.159e-08 | 1.486e-04/3.997e-04 | True |
| N2 | 20 | 36 | 4.014e-07/4.796e-07 | 1.050e-07/1.241e-07 | 5.974e-05/1.306e-04 | True |

| compiled component path | logical qubits | depth | CX |
|---|---:|---:|---:|
| H2 | 1,297 | 1,612,437 | 1,855,912 |
| CO2 | 1,298 | 1,681,455 | 1,883,094 |
| CH4 | 1,486 | 3,143,800 | 2,807,252 |
| CO | 1,477 | 2,937,203 | 2,690,244 |
| N2 | 1,472 | 3,012,190 | 2,674,550 |

The componentwise repeated-controller upper bound is **1,486 peak logical qubits**, depth **12,387,085**, and **11,911,052 additive CX**. It is not a monolithic five-component transpilation.

The competitive-Langmuir response is supplied. Dynamic affinity-denominator/reciprocal construction, gas normalization, face generation, off-ledger tank demand, and phase/cycle integration remain open.

No QPU job was submitted.
