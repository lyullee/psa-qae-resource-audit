# Primary repeated-cycle aggregate-map stability screen

Each outer-held aggregate phase/equalization map is applied for 50 cycles from the held run's observed final-cycle start. No held intermediate phase state is supplied.

Terminal event labels match **21/32** runs. The last 10 labels are constant in **26/32** runs, and the tail aggregate CSS L1 gate `1e-04` passes in **1/32** runs. Median/p95 terminal cycle residuals are **9.810e-03/2.760e-02**.

Median/p95 terminal drift from the observed cycle start are **9.083e-02/3.085e-01**. Median/max state-coordinate outside-range fractions are **2.246e-01/7.188e-01**. State/stream clipping counts are **1014/982**.

This is a local aggregate-map stability screen initialized at an observed CSS-cycle start. It does not propagate the finite tank state or spatial profiles, establish global CSS convergence, compile reversible CSS control, or validate the process externally.
