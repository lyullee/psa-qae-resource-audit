# Pressure-derived saturated/unsaturated proportional tank allocation

Status: **pressure_derived_saturated_and_bounded_unsaturated_proportional_tank_allocation_compiled**

The domain retains **128 observed frozen final-cycle calls** and adds **224 explicitly labelled pressure counterfactuals** over the 32 nonzero observed tank compositions. The counterfactuals cover demand fractions `0.050, 0.125, 0.250, 0.500, 0.750, 0.875, 0.950` and test arithmetic only; they are not physical trajectories or plant validation.

The clean circuit reconstructs pressure from five endpoint gas inventories, forms the demand proxy, compares it with tank total, copies the whole tank on saturation, and otherwise evaluates `demand*tank_i/sum(tank)` with a support-adaptive reciprocal and reversible multipliers. It then subtracts the selected five-component withdrawal and reverses all work registers.

The selected design uses **18 common bits**, **5 reciprocal-address bits** (32 segments), and **16 reciprocal bits**. It preserves **128 saturated** and **224 unsaturated** labels with zero mismatch, fraction overflow, underflow, or meaningful erasure. Withdrawal/next-tank component-scale error is p95 **1.687e-04** and maximum **3.872e-04**.

The all-to-all `u`/`CX` compilation uses **647 logical qubits**, depth **1,127,046**, and **705,194 CX**, with no measurement or reset.

This closes the proportional-allocation arithmetic branch over a declared bounded domain. A physically generated unsaturated trajectory, monolithic five-component phase/cycle construction, adaptive integration, routing, external H2 validation, and quantum advantage remain open.

No QPU job was submitted.
