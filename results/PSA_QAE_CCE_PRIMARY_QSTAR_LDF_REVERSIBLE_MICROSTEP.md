# Clean competitive-Langmuir reciprocal and CO2 LDF microstep

The precision screen covers **25,856** physical cell states. The first passing tier uses **5 denominator-address bits** (32 QROM segments) and **24-bit reciprocal/loading arithmetic**.

At this tier the p95 relative error is **4.0855%** for CO2 equilibrium loading and **0.0726%** for the one-second LDF update. No nonzero equilibrium loading is erased.

The clean compute-copy-uncompute circuit uses **515 logical qubits**, depth **1,919,788**, and **1,225,138 CX** in the all-to-all `u/CX` basis. It includes the earlier 18-bit five-component numerator/denominator preparation and uncomputes all work registers after copying the updated CO2 loading.

This is a one-cell, one-component, one-second explicit kinetic microstep. The other four loadings, gas transport, valve/tank balances, adaptive integration, repeated phase/cycle execution, routing, and QPU execution remain open.
