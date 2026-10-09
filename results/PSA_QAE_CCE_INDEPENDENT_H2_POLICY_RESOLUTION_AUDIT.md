# Independent H2 policy-spacing resolution audit

The public Voigt H2/CH4 table provides a purge/feed-ratio recovery coefficient and group-held-out error. The frozen recycle candidate spacings are applied numerically to that coefficient only to test resolution. Purge/feed ratio is not asserted to be product-gas recycle.

| numeric pair | implied recovery effect, %-point | group-CV RMSE, %-point | effect/RMSE | RMSE reduction needed for 5x gate | pass |
|---|---:|---:|---:|---:|---|
| 0.420–0.427 | -0.546 | 5.854 | 0.0932 | 53.6× | False |
| 0.420–0.430 | -0.780 | 5.854 | 0.1332 | 37.5× | False |
| 0.427–0.430 | -0.234 | 5.854 | 0.0400 | 125.1× | False |

The widest pair resolves only `0.1332` of the held-out RMSE and would require a `37.5×` RMSE reduction to satisfy the declared 5× gate. Reported recovery uncertainty spans `1.7–3.7` percentage points. Continuous purity is not identifiable because only one Type-2 run exists and the analyser is detection-limit censored.

This is a stronger quantified negative control, not external validation of recycle 0.420. It shows that the available independent H2 table cannot distinguish the frozen 0.007–0.010 candidate spacing even before control-semantic mismatch is considered.
