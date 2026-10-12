# Independent continuous-area ODE audit

## Numerical finding

The production membrane model uses 72 fixed area sections for the polymer stage and 144 sections for the Pd stage. An independent adaptive DOP853 integration over all 1,920 packets in each of the 16 predeclared cases lowers the polymer-stage H2 recovery by **0.175–0.155 percentage point** relative to the fixed-section result.

At the former **0.553 m²** Pd guard, only **15/16** direct cases pass because the minimum recovery falls to **88.1997%**, below the frozen **88.2940%** floor. That guard is therefore superseded.

## Revised guard

- minimum unrounded Pd area: **0.553770 m²**;
- selected rounded Pd area: **0.554 m²**;
- increase from 0.553 m²: **0.18%**;
- co-sized receiver: **1.232009 mol (30.541 L at 1 bar and 298.15 K)**;
- direct confirmation: **16/16 pass**;
- minimum recovery: **88.3221%**;
- minimum qualified H2 rate: **0.0023605 mol/s**;
- worst CO/CO2/N2/CH4: **0.120/4.000/48.828/25.069 ppm**;
- tight-tolerance replay recovery difference: **8.818e-11**.

The ODE audit verifies the numerical area integration using a different algorithm. It still uses the same literature membrane transport equations and does not replace Aspen, vendor-module, or experimental validation.
