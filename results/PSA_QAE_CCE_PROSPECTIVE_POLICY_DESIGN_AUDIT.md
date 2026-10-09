# Prospective recycle-policy design audit

The frozen primary candidates remain unchanged. This audit asks what spacing and validation precision a future confirmatory H2 study would need.

- Observed recycle support: `0.3508–0.4481` (span `0.0973`).
- Conditional-surrogate p=0.50 crossing: recycle `0.42659`; local slope `-71.56` probability per recycle unit.
- Independent H2 recovery error: `5.854` percentage points.
- Spacing for an effect equal to 1×/5× that error: `0.0751` / `0.3754`.
- The full observed support gives effect/RMSE `1.296`, so even the widest in-support contrast fails the 5× gate.
- A full-support confirmatory campaign would require recovery group-CV RMSE `<= 1.517` percentage points; the current primary 0.010 span would require `<= 0.156` percentage point.

The correct next experiment is therefore a broader, same-control H2 campaign with continuous purity and substantially lower held-out recovery error. Expanding the present surrogate beyond its observed support or relabeling purge/feed as product recycle would not close the validation gate.
