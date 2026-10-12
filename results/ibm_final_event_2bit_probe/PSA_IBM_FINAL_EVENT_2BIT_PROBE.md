# IBM QPU probe of the final pressure-consistent PSA event

The exact two-bit event has `50/64` marked states. Its failing complement is represented by three disjoint cubes and the resulting seven-qubit reversible circuit passed all `128` input/flag basis checks locally.

Backend: `ibm_kingston`. Routed CZ range: `80–179`; depth range: `244–456`.

## QPU result

- job: `db6emt04qg6s73c4lja0`
- majority-correct truth-table states: `64/64`
- mean expected-label probability: `0.8389`
- minimum expected-label probability: `0.6523`
- reported QPU usage: `7`
- free Open Plan seconds remaining: `405`

## Claim limits

- This exhaustively tests the reversible truth mapping of the exact final-model two-bit event, not coherent amplitude estimation.
- The compact Boolean circuit is truth-table equivalent at two-bit resolution; it is not the 42-qubit arithmetic implementation or the 66-qubit ten-bit implementation.
- The two-bit uniform-grid event fraction is a coarse-discretization diagnostic and is not used as the reported process probability.
- Basis-state classification on one IBM QPU does not establish quantum advantage or validate the dynamic PSA equations.
