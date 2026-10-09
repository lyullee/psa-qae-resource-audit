# Primary parameter-to-CSS initializer event bridge

The held run supplies only its 11 frozen uncertainty/decision parameters. A nested-held-out ridge map predicts the 20 aggregate cycle-start state coordinates, after which independently held-out phase and equalization maps generate one cycle and the event streams.

Event labels match **32/32** runs (false positives=0, false negatives=0). Purity/recovery MAE are **3.641e-07/3.221e-04**.

CSS-initializer median/p95 state L1 are **2.709e-04/7.011e-04**. Predicted-cycle closure median/p95 are **2.108e-06/1.394e-05**. No-held-state initialization causes 0 initial-state clips, 0 cycle-state clips, and 0 stream clips.

This removes all held dynamic-state inputs, but the initializer is a fitted surrogate of already converged rows. It is not an iterative physical CSS solver, tank/profile propagation, or a reversible circuit.
