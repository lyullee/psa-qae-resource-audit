# Parameter-only CSS initializer spectral-stability screen

Each outer-held affine cycle map is anchored to its parameter-only CSS initializer with the smallest weight that reduces the exact fitted Jacobian spectral radius to the predeclared target 0.9. Held event labels and held dynamic states are not used to choose the weight.

Raw spectral radius spans **1.040–1.254** (median **1.161**), requiring anchor weights **0.135–0.282** (median **0.225**).

The unanchored 50-cycle baseline retains terminal labels in **28/32** runs and passes the aggregate CSS gate in **2/32**. Spectral stabilization retains cycle-1 and terminal labels in **32/32** and **32/32** runs, while the tail CSS gate passes in **32/32**.

Median/p95 terminal residuals are **9.400e-09/6.237e-08** and p95 terminal drift from the predicted initializer is **1.097e-04**. State/stream clipping counts are **0/0**.

This result diagnoses and corrects mathematical instability of the reduced aggregate surrogate. The anchor is an explicit model correction, not a conservation-law-derived tank/spatial CSS update, and no physical or reversible CSS claim follows.
