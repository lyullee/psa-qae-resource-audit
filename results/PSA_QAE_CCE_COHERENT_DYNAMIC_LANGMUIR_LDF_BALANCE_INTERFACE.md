# Coherent dynamic-Langmuir-to-LDF/loading/balance interface

Status: **dynamic_run_affinity_langmuir_response_consumed_in_five_compiled_component_paths**

The controller's retained 12-bit run-affinity word and supplied 20-bit pressure/five-component composition now generate the competitive-Langmuir denominator and reciprocal inside each clean component path. The generated response is consumed directly by the run-specific equilibrium coefficient, LDF loading update, loading-sign conversion and conservative gas balance.

Selected design: **8 affinity bits**, **12 denominator-address bits** (4,096 reciprocal segments).

| component | response p95/max | q* p95/max | LDF-next p95/max | next-gas p95/max | pass |
|---|---:|---:|---:|---:|---|
| H2 | 1.710e-04/2.917e-04 | 1.588e-04/2.852e-04 | 1.119e-04/1.967e-04 | 8.753e-05/2.040e-04 | True |
| CO2 | 1.316e-06/1.744e-05 | 1.194e-06/1.676e-05 | 4.349e-08/6.163e-07 | 1.007e-05/1.116e-04 | True |
| CH4 | 1.063e-06/2.296e-06 | 9.540e-07/1.927e-06 | 1.888e-07/3.782e-07 | 8.467e-05/1.944e-04 | True |
| CO | 1.071e-06/1.408e-06 | 9.488e-07/1.341e-06 | 1.432e-07/1.939e-07 | 1.783e-04/3.997e-04 | True |
| N2 | 9.026e-07/1.515e-06 | 8.119e-07/1.287e-06 | 2.184e-07/3.328e-07 | 7.673e-05/1.329e-04 | True |

| compiled component path | logical qubits | depth | CX |
|---|---:|---:|---:|
| H2 | 1,771 | 67,700,348 | 41,440,216 |
| CO2 | 1,772 | 67,700,348 | 41,467,398 |
| CH4 | 1,960 | 67,700,348 | 42,391,556 |
| CO | 1,951 | 67,700,348 | 42,274,548 |
| N2 | 1,946 | 67,700,348 | 42,258,854 |

Gas normalization, face generation, off-ledger tank demand, monolithic five-component phase/cycle integration, routing, hardware feasibility, external H2 validation and quantum advantage remain open.

No QPU job was submitted.
