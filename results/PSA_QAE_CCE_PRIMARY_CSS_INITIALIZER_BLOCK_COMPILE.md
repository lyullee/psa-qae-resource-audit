# Primitive-gate compilation of parameter-only CSS initializer blocks

The accuracy-feasible configuration uses 9 bits per active parameter and a 14-bit scalar accumulator. Twenty aggregate A/B gas and adsorbed-state outputs are compiled independently to `u`/`cx` with all-to-all connectivity and optimization level 0.

With scalar-workspace reuse, the maximum block requires **118 logical qubits**. The 20-block serial total is **578,702 forward CX** and **1,157,404 clean compute-uncompute CX**.

These are affine variable weighted sums only. Constant injection, reversible state-register update, physical CSS iteration, tank/profile propagation, final event arithmetic, loading, routing, and hardware execution remain open.
