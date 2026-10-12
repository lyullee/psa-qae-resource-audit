# Two public H2 PSA experimental hold-outs

The local model, product thresholds, and event definition were frozen at release `v0.2.2` before these records were integrated. No parameter was refitted. Because both public rigs differ from the final integrated apparatus, the contract is limited to directional engineering behavior and joint-event structure.

## Chen et al. 2023 two-column H2/CO2 VPSA

All `12` endpoint direction checks passed. At each feed composition, increasing the reported pressure from 1 to 5 kgf cm-2 left purity unchanged or increased it and decreased recovery. At each pressure, increasing feed H2 from 25% to 75% left purity unchanged or increased it and decreased recovery. Across the 13 measured runs, the descriptive purity-recovery Spearman association was `-0.766` (`p=0.0023`). None of the 13 runs jointly met the frozen project floors of 99.97% H2 and 88.294% recovery. Five center repetitions gave purity `99.588 +/- 0.326` percentage points and recovery `17.386 +/- 0.591` percentage points (mean +/- sample SD).

## Voigt 2022 four-bed transient-feed H2/CH4 PSA

The source-defined event combines Type 1 purity, meaning CH4 did not exceed the 0.5 vol% analyzer limit, with recovery of at least 70%. `6/13` runs passed and every feed stage contained at least one passing run. Purge/feed ratio and recovery had a descriptive Spearman association of `-0.758` (`p=0.0027`). Duplicate breakthrough times differed by less than 3.3% according to the source. The thesis explicitly states that 99.97% fuel-cell purity could not be investigated with its analyzer, so these data do not certify the project's ppm gate.

## Claim boundary

These controls independently support the purity-recovery trade-off, the recovery cost of purge allocation, the need for feed-dependent cycle settings, and use of a joint event. They do not provide a pointwise error metric or certification for the final PSA-polymer-palladium apparatus.

Sources: [Chen et al. 2023](https://doi.org/10.1016/j.ecmx.2023.100459); [Voigt 2022](https://doi.org/10.34726/hss.2022.103430).
