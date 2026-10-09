# Coherent run, valve-schedule, and tank-withdrawal interface

The frozen 32-run primary ledger is compiled into a coherent finite-support interface. A five-qubit run address loads eleven 12-bit run-specific parameter words, a three-qubit stage address decodes the six synchronized two-bed stages and their local valve masks, and a seven-qubit run/slot address supplies five component withdrawals to a clean fixed-point tank subtraction.

| module | logical qubits | depth | CX | u |
|---|---:|---:|---:|---:|
| coherent run-parameter loader | 140 | 96,304 | 49,176 | 58,095 |
| six-stage valve-schedule decoder | 27 | 944 | 492 | 609 |
| clean five-component tank withdrawal | 282 | 227,249 | 116,521 | 135,719 |
| integrated run/schedule/tank interface | 440 | 324,495 | 166,189 | 194,419 |

All `352` run-parameter table values, `8` schedule addresses, and `640` run/slot/component withdrawal records pass the table-level checks. The selected tank width is `18` bits; p95 and maximum component-scale-normalized absolute errors are `1.362e-06` and `1.865e-06`, with zero meaningful erasures, zero modular underflow, and zero next-tank precision mismatches.

This closes the previously open finite-support interfaces for coherent run parameters, synchronized valve scheduling, and recorded final-cycle tank withdrawal. It does not synthesize a scalable off-ledger withdrawal law, adaptive time integration, or a complete nonlinear phase/cycle unitary; those remain the local implementation boundary.

Artifacts: `PSA_QAE_CCE_COHERENT_RUN_SCHEDULE_TANK_INTERFACE.json`, `PSA_QAE_CCE_COHERENT_RUN_SCHEDULE_TANK_INTERFACE.csv`. No QPU job was submitted.
