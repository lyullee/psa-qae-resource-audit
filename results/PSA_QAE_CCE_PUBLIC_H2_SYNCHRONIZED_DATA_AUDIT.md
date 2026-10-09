# Public H2 PSA synchronized-data availability audit

This audit separates public availability from scientific quality. A strict pass requires H2 chemistry, a public synchronized raw file with all declared channels, the same product-gas-recycle policy, and the same frozen purity/recovery event. Coverage codes are **Y** (present), **P** (partial/table/figure), **N** (absent), and **R** (restricted).

| source | type | cycle | valve/step | P | feed F | product F | product y | clock | raw | same policy | same event |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Thelen 2023 VA-10 | PSA | P | P | P | P | P | P | P | N | N | N |
| Voigt 2022 H2/CH4 four-bed campaign | PSA | P | P | P | P | P | N | N | N | N | N |
| Schell et al. 2013 laboratory H2/CO2 PSA | PSA | P | P | P | P | P | P | P | N | N | N |
| Yang 1997 experiment with public toPSAil case | PSA | P | Y | P | P | P | N | P | N | N | N |
| Gubin et al. 2025 integrated pilot | PSA | P | P | P | P | P | P | P | N | N | N |
| Windbacher 2026 H2 breakthrough archive | single-bed adsorption | N | P | R | P | N | R | R | R | N | N |
| Anese et al. 2026 refinery H2 PSA | PSA | Y | Y | Y | P | P | N | Y | N | N | N |
| Lee et al. 2022 industrial monitoring | PSA | Y | P | Y | N | N | N | Y | N | N | N |
| Golmakani et al. 2019 Cranfield PVSA record | PVSA simulation | N | P | N | N | N | N | N | N | N | N |
| Otway field CO2 PSA historian | PSA | Y | Y | Y | Y | Y | N | Y | Y | N | N |

**Strict gate result:** `0/10` sources pass. The closest public H2 experiment is Thelen VA-10, but its historian is not downloadable and its control is equalization pressure. The only fully public synchronized historian in this set is Otway, which has different chemistry and lacks a continuous H2 product-composition channel.

The Schell H2/CO2 study supplies a useful cyclic experimental database with pressure, product-flow, and mass-spectrometer evidence, but the public supplement exposes plots/tables rather than a joined raw archive and varies adsorption pressure/time instead of the frozen product-recycle coordinate. The Cranfield record exposes only `disclaimer.txt` in the scoped access and accompanies a simulation study.

Accordingly, the manuscript may claim public H2 performance and mechanism anchors plus cross-chemistry hydraulic validation. It may not claim independent industrial H2 validation of the frozen policy or event.

Machine-readable outputs: `PSA_QAE_CCE_PUBLIC_H2_SYNCHRONIZED_DATA_AUDIT.json` and `PSA_QAE_CCE_PUBLIC_H2_SYNCHRONIZED_DATA_AUDIT.csv`.
