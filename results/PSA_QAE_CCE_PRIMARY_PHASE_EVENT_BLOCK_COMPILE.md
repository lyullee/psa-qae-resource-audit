# Primitive-gate compilation of primary event-active phase-stream blocks

The fixed-point screen selects 12 bits per active input and a 16-bit scalar accumulator. The six event-active stream outputs for each of the two adsorption phases are compiled independently to `u`/`cx` with all-to-all connectivity and optimization level 0.

| phase | scalar blocks | max logical qubits | forward CX | clean compute-uncompute CX | forward serial depth |
|---|---:|---:|---:|---:|---:|
| A_adsorption | 6 | 272 | 540,731 | 1,081,462 | 1,068,277 |
| B_adsorption | 6 | 272 | 560,502 | 1,121,004 | 1,107,608 |

Across both adsorption phases, the 12 event-active blocks require up to 272 logical qubits with scalar-workspace reuse, 1,101,233 forward CX, and 2,202,466 clean compute-uncompute CX under serial composition.

This is a measured process-to-event arithmetic layer conditional on observed phase-start states. Stream summation, fixed-policy recycle scaling, joint purity/recovery comparison, CSS repetition, loading, routing, and fault tolerance remain open.
