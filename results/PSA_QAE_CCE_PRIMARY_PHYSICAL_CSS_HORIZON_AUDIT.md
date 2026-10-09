# Physical tank/spatial CSS horizon and reversible register accounting

The frozen 32 primary rows were rerun for 100 cycles with all 85 cycle-boundary physical state scalars retained: 40 gas/adsorbed coordinates per bed and five finite-tank component inventories. Per-cycle product and feed streams were retained for the frozen purity/recovery event.

All 32 rows pass both final strict and L1 CSS gates `1e-04`. The latest tail-stable strict-CSS horizon is cycle **68**, the latest event-label horizon is cycle **33**, and the latest joint physical horizon is cycle **68**.

The first fixed-point precision satisfying the final CSS/event conditions and p95 state-error budget `1e-05` is **16 bits per scalar**. Conservatively combining the physical and quantized horizons gives a fixed horizon of **85 cycles**.

At 16 bits, one 85-scalar physical state occupies **1,360 data qubits**. An explicit clean out-of-place layout with separate current/next states uses **2,720**, and retaining all ten raw feed/product stream scalars raises that accounting point to **2,880 qubits** before nonlinear transport or workspace. These are architectural data-register counts, not universal circuit lower bounds. A clean fixed-horizon probability oracle calls an eventual reversible cycle unitary **85** times forward and **85** times in reverse.

This closes the physical-horizon and data-register accounting gap. The nonlinear pressure/flow/equilibrium/kinetic cycle unitary is not synthesized, so stable physical/reversible CSS remains an open implementation gate rather than a completed circuit.
