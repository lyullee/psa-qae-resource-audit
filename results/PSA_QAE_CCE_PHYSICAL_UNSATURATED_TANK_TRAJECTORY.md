# Model-derived physical unsaturated tank trajectory control

The source spatial/tank ODE model was integrated for **500 cycles** at frozen sample 0 and recycle fraction **0.419749**. Adsorption remains 10 s, while the declared schedule counterfactual shortens non-adsorption phases from 10 s to **0.02 s**. The final max/L1 CSS residuals are **9.949e-07/5.637e-07**.

Replaying the last 32 cycles produces **128 tank calls**: **128 unsaturated**, **0 saturated**, and **128 zero-makeup** calls. Tank starts span **99.958144–100.000000 mol** and integrated withdrawals span **0.009138–0.036580 mol**. Replay maximum state error is **0.000e+00**.

Using only the phase-end pressure gives p95/max relative demand errors **9.718%/9.718%**. The retained start/end-pressure trapezoid reduces them to **0.853%/0.853%**; the circuit therefore computes and uncomputes the componentwise average of the two gas words before pressure reconstruction.

The selected 18-bit common/3-bit address/16-bit reciprocal design has withdrawal/next-tank p95/max component-scale errors **8.320e-06/9.241e-06**. The clean all-to-all compilation uses **845 qubits**, depth **1,634,701**, and **1,078,054 CX**.

This is a physically integrated source-model schedule control at the same recycle fraction, not evidence for the frozen 10-s schedule or plant validation. It does not close monolithic quantum phase integration, external H2 validation, or quantum advantage.

No QPU job was submitted.
