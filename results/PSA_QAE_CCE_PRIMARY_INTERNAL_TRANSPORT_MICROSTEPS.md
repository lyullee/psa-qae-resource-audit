# Pressure reconstruction and oriented internal-face transport

The physical cache contains **25,856 cell states** and **19,392 internal faces**. In the source model's local flow coordinate, 19,200 faces are positive, 192 are zero, and no face is negative.

The first combined precision tier uses **18-bit component gas inventories**, a **20-bit pressure output**, **24 effective flow bits**, and **20-bit upwind composition**. Pressure p95 scale-normalized error is **3.012e-06**. The face-flow p95 relative error is **3.540e-03**; the largest component-flux p95 flow-scale-normalized error is **4.858e-05**, with zero active-label mismatch, pressure-difference underflow, and nonzero-flux erasure.

The clean pressure circuit uses **152 logical qubits**, depth **158,331**, and **93,764 CX**. The clean oriented-face circuit uses **404 logical qubits**, depth **2,237,277**, and **1,340,390 CX**.

Sequential modular accounting for two pressure calculations followed by one face transfer is **584 qubits** and **1,527,918 additive CX**. Composition is still supplied as a separate encoded input; normalization from gas inventories, next-state accumulation, adsorption coupling, adaptive integration, routing, and a complete phase/cycle remain open.

No QPU job was submitted.
