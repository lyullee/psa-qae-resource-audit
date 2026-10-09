# Corrected independent pyAPEP H2 topology stress test

The previous wrapper connected product-gas pressurisation at the feed end and used an adsorption-feed-only recovery proxy even when external high-purity makeup entered the system. That result is retained only as a superseded audit artifact. The corrected wrapper injects purge and pressurisation gas at the light-product end, counts all external H2 in the recovery denominator, and reports product-tank self-sufficiency.

| tier | nodes | recycle | cycles | CSS residual | H2 purity | external-boundary recovery | tank supply fraction | joint event | tank self-sufficient |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 15-cycle policy-direction screen | 5 | 0.420 | 15 | 0.00799636 | 0.793870 | 0.047980 | 0.0346 | False | False |
| 15-cycle policy-direction screen | 5 | 0.427 | 15 | 0.00799637 | 0.793870 | 0.047429 | 0.0352 | False | False |
| 15-cycle policy-direction screen | 5 | 0.430 | 15 | 0.00799636 | 0.793870 | 0.047192 | 0.0355 | False | False |
| 450-cycle baseline stress control | 4 | 0.420 | 450 | 0.00125378 | 0.991666 | 0.044166 | 0.0316 | False | False |

At 450 cycles, the corrected 0.420 control has H2 purity `0.991666`, external-boundary recovery `0.044166`, tank supply fraction `0.0316`, and CSS residual `0.00125378`. It fails all four declared gates.

**Interpretation.** Correcting the product-end connection removes the unphysical low-H2 product reported by the superseded wrapper, but the finite tank supplies only a few percent of purge/pressurisation demand. Even the 450-cycle 0.420 control does not satisfy the declared CSS, purity, recovery, or tank-self-sufficiency gates. The result is a transparent topology-feasibility stress test and cannot be used as a CSS-converged same-policy negative control.
