# IBM QPU PSA-breakthrough MLAE result

- Job ID: `db4mll04qg6s73c2cvvg`
- Backend: `ibm_marrakesh`
- Plan: `open`
- Submitted (UTC): `2026-10-09T22:29:40.834493+00:00`
- Backend calibration: `2026-10-10T06:18:00+09:00`
- QPU charge time: `5 s`
- Resource usage: `0.0829 resource_units`
- Exact event probability: `0.625000`
- Hardware MLAE estimate: `0.598305`
- Absolute error: `0.026695`
- Likelihood interval: `[0.595795, 0.600785]`
- Oracle-query count: `36864`

| m | shots | good | observed | ideal amplified | depth | 2Q gates | initial layout |
|---:|---:|---:|---:|---:|---:|---:|:---|
| 0 | 4096 | 2571 | 0.627686 | 0.625000 | 4 | 0 | `[54, 12, 6]` |
| 1 | 4096 | 834 | 0.203613 | 0.156250 | 73 | 19 | `[55, 53, 54]` |
| 2 | 4096 | 3719 | 0.907959 | 0.976563 | 135 | 37 | `[55, 53, 54]` |

The shallow m=0 circuit reproduces the event probability closely, while the deeper amplified circuits show gate-noise distortion. The likelihood interval is conditional on the ideal MLAE observation model and therefore does not include hardware bias.

This is a hardware-feasibility and noise-boundary result; it is not evidence of quantum computational advantage or industrial PSA validation.
