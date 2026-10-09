# Independent same-chemistry H2 equalization control

Thelen's automated four-column H2 PSA experiment VA-10 contains a matched pair whose only reported change was equalization pressure: 4.50 bara at BP1 and 4.75 bara at BP2. This is a same-chemistry mechanism control, not a replication of the local product-gas recycle policy.

| operating point | equalization, bara | H2 purity, % | recovery: direct BGZ, % | recovery: pulse, % | productivity, slm/kg | frozen joint event |
|---|---:|---:|---:|---:|---:|---|
| BP1 | 4.50 | 99.95 | 81.45 | 80.78 | 1.36 | False |
| BP2 | 4.75 | 99.93 | 79.15 | 79.47 | 1.33 | False |

For BP2 minus BP1, purity changes by `-0.02` percentage point, direct-meter recovery by `-2.30` percentage points, pulse-derived recovery by `-1.31` percentage points, and the two-method mean recovery by `-1.805` percentage points. The recovery sign is therefore measurement-method robust within the reported pair.

Both recovery estimates remain above the frozen local recovery threshold of `78.9%`, but both reported purities are below the frozen `99.98%` purity threshold. The literature pair therefore cannot validate the frozen joint event. The source also warns that a 1% feed-flow deviation causes a recovery deviation of similar order, so the paired effect should be interpreted as a direction control rather than a precise transferable effect size.

**Claim boundary.** Supported: matched same-chemistry evidence for the sign of the equalization-pressure/recovery response. Unsupported: the local recycle candidates, the local chance probabilities, the 0.420 selection, a synchronized historian claim, or industrial H2 validation.

Source: F. Thelen, TU Wien (2023), DOI `10.34726/hss.2023.101204`; Section 6.2.2 and Tables 19 and 24.
