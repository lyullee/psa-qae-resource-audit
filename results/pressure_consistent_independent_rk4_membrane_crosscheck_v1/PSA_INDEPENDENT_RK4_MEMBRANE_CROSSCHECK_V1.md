# Independent fixed-area RK4 membrane cross-check v1

A separately coded classical RK4 area integrator was refined through 48, 96, and 192 sections per membrane stage.
It re-evaluated the 0.554-m2/80%-retention and 0.887-m2/50%-retention designs over all 16 frozen cases.

- `base_20pct_loss`: **16/16 pass**, maximum recovery difference from DOP853 9.062e-08 percentage point.
- DWSIM horizon comparison was not used in this rerun because the host blocked the DWSIM DLL.
- `public_syngas_50pct_loss`: **16/16 pass**, maximum recovery difference from DOP853 9.330e-08 percentage point.
- DWSIM horizon comparison was not used in this rerun because the host blocked the DWSIM DLL.

All **32/32** design/case event labels agree with DOP853.

This closes a numerical-method sensitivity check only. External Aspen transport or matched membrane measurements remain open.
