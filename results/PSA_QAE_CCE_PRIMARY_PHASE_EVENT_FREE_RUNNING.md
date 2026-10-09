# Primary one-cycle free-running phase-stream event bridge

The held run supplies only the aggregate A/B bed states at the beginning of its final cycle and the frozen parameters. Eight phase maps and two equalization maps, fitted without that run, are composed in schedule order; every predicted phase/equalization state becomes the next map input.

The frozen event matches in **32/32** runs (false positives=0, false negatives=0). Purity/recovery MAE are **8.611e-08/6.428e-05**. Median/p95 final-cycle closure L1 are **4.016e-05/1.085e-04**.

| composed stage | median joint-state L1 | p95 joint-state L1 | max joint-state L1 |
|---|---:|---:|---:|
| phase_pair_1 | 7.39403e-06 | 2.36812e-05 | 2.71308e-05 |
| equalization_1 | 1.60372e-05 | 3.67043e-05 | 4.73123e-05 |
| phase_pair_2 | 4.12943e-05 | 9.56507e-05 | 1.06488e-04 |
| equalization_2 | 3.84508e-05 | 8.94038e-05 | 1.04075e-04 |
| phase_pair_3 | 1.02611e-04 | 1.99018e-04 | 2.22283e-04 |
| phase_pair_4 | 4.01555e-05 | 1.08509e-04 | 1.22084e-04 |

Nonnegative clipping affected 0 state entries and 0 stream entries over all held runs.

This removes the earlier use of actual intermediate held phase-start states. It remains a one-cycle aggregate-state bridge anchored at the actual final-cycle start; tank-state propagation, profile-resolved dynamics, repeated CSS, reversible event arithmetic, and external validation remain open.
