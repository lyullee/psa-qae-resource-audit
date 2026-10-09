# Parameter-only CSS initializer repeated-cycle screen

For each outer held run, 11 frozen parameters generate both aggregate bed states and the held-out phase/equalization map is iterated for 50 cycles. No held dynamic state is supplied.

Terminal labels match **28/32** runs. The final 10 labels are constant in **30/32**, and the tail aggregate CSS gate `1e-04` passes in **2/32**. Median/p95 terminal cycle residuals are **1.400e-03/4.145e-02**.

Median/p95 terminal drift from the predicted initializer are **1.043e-02/2.549e-01**. State/stream clipping counts are **179/138**.

This is a local stability test of fitted aggregate maps. The finite tank state and spatial profiles are absent, and no global physical or reversible CSS claim follows.
