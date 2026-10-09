# Clean product-boundary valve/flux and tank-ledger modules

The product-valve precision screen covers **6,464 encoded product-end states**. The first passing tier uses a **12-bit pressure address** and **20-bit flow/flux outputs**. Active/inactive labels agree for every state, active-flow p95 relative error is **0.3161%**, and the largest component-flux p95 error is **0.2151% of the flow register range**.

The clean valve-to-five-component-flux circuit uses **288 logical qubits**, depth **1,379,148**, and **800,762 CX** in the all-to-all `u/CX` basis.

The product/tank screen covers **64 final-cycle product-recycle records**. The first passing tier uses **24-bit amounts** and a **14-bit fixed recycle coefficient**. Its p95 error is **5.254e-07 of the 100-mol register range**, with zero nonzero-recycle erasure and zero capacity-flag mismatch. Maximum candidate tank inventory is **2.597371 mol**, leaving **97.402629 mol** headroom.

One clean scalar split/tank-candidate block uses **197 qubits** and **172,225 CX**; the clean vector capacity block uses **176 qubits** and **182,865 CX**. Sequential five-component accounting with all product/tank/recycle/external/candidate registers retained requires **677 qubits** and **1,043,990 additive CX**.

The valve-flux and integrated product/tank records remain separate evidence tiers. Pressure recomputation, internal face transport, adsorption coupling, tank withdrawal, adaptive integration, monolithic composition, routing, and a complete reversible phase/cycle remain open.
