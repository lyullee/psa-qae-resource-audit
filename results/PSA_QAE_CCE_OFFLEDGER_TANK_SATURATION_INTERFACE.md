# Pressure-derived saturated tank-withdrawal interface

Status: **frozen_support_pressure_derived_saturated_tank_withdrawal_compiled**

The final-cycle support contains **128 tank calls**. Five encoded endpoint gas inventories reconstruct the source-end pressure, which generates the reversible end-pressure demand lower bound `k_in Δt max(P_high-P_end,0)`. The bound is compared with the five-component tank inventory; every cached call is saturated, so the clean withdrawal equals the current tank and the next tank is zero.

The exact integrated demand is at least **14.784303 mol**, the maximum starting tank is **2.675740 mol**, and the minimum pressure-bound margin is **1.624404 mol**. Saturation mismatches, lower-bound violations, underflows, and meaningful erasures are all zero.

The selected 20-bit common encoding has p95 aggregate normalized error **2.033e-06**. The clean all-to-all `u`/`CX` circuit uses **557 logical qubits**, depth **327,212**, and **195,276 CX**, with no measurements or resets.

This removes the recorded-withdrawal QROM on the frozen saturated branch. Unsaturated allocation, phase-end state generation inside a monolithic phase unitary, adaptive integration, routing, external H2 validation, and quantum advantage remain open.

No QPU job was submitted.
