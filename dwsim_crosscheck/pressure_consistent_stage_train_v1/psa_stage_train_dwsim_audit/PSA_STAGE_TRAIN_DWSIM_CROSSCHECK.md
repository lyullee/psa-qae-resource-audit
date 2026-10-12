# DWSIM cross-check of the PSA membrane polishing train

## Result

All **16/16** predeclared uncertainty and hold-out cases solved in DWSIM 8.7.1 with the Peng–Robinson property package. The largest component material-balance residual was **8.945e-19 mol/s**, and the largest difference between the DWSIM product stream and the supplied packet-model split was **1.301e-18 mol/s**.

The process uses a **0.1892-m² polymer stage**, a **0.554-m² Pd stage at 80% permeance retention**, one 6.2→20 bar compressor before the polymer stage, and three equal-pressure-ratio, intercooled compressor stages between the 1 bar polymer permeate and the 20 bar Pd feed. The maximum first-stage discharge temperature was **460.03 K**; the maximum recompression-stage discharge temperature was **433.64 K**.

The DWSIM adiabatic shaft-power range was **53.133–56.114 W**, equal to **3.091–3.183 kWh/kg H2**. This is **16.94–16.98%** above the earlier isothermal lower bound. The total intercooling duty was **53.316–56.293 W**.

## Meaning

The cross-check confirms that the pressure levels, stream states, compressor duties, cooling duties, and material closure are internally consistent in a general process simulator for the horizon-averaged cases. It also changes the engineering conclusion: 1→20 bar recompression should be represented as a multistage, intercooled system, and the isothermal calculation should be reported only as a lower bound.

## Claim boundary

DWSIM does not independently calculate the polymer or Pd transport laws here. Each Component Separator receives the component split fractions from the packet-resolved Python membrane model. The calculation also does not replace the dynamic surge/receiver model, compressor maps, pressure-drop calculations, or measurements from a real membrane module.

## Reproduction

1. Run `make_psa_stage_train_dwsim_deck.py` to rebuild the 16-case input deck.
2. Run `run_psa_stage_train_dwsim_crosscheck.ps1` with Windows PowerShell 5.1 and the included DWSIM 8.7.1 portable directory.
3. Run `finalize_psa_stage_train_dwsim_crosscheck.py` to audit the outputs and regenerate this report and figure.
