# IBM QPU PSA-breakthrough MLAE result

- Job ID: `db4mm1kvf2bc73cuqnn0`
- Backend: `ibm_kingston`
- Plan: `open`
- Submitted (UTC): `2026-10-09T22:30:30.250331+00:00`
- Backend calibration: `2026-10-10T06:45:45+09:00`
- QPU charge time: `5 s`
- Resource usage: `0.0824 resource_units`
- Exact event probability: `0.625000`
- Hardware MLAE estimate: `0.599390`
- Absolute error: `0.025610`
- Likelihood interval: `[0.596940, 0.601805]`
- Oracle-query count: `36864`

| m | shots | good | observed | ideal amplified | depth | 2Q gates | initial layout |
|---:|---:|---:|---:|---:|---:|---:|:---|
| 0 | 4096 | 2573 | 0.628174 | 0.625000 | 4 | 0 | `[11, 21, 148]` |
| 1 | 4096 | 639 | 0.156006 | 0.156250 | 73 | 19 | `[138, 152, 151]` |
| 2 | 4096 | 3660 | 0.893555 | 0.976563 | 135 | 37 | `[74, 59, 75]` |

The shallow m=0 circuit reproduces the event probability closely, while the deeper amplified circuits show gate-noise distortion. The likelihood interval is conditional on the ideal MLAE observation model and therefore does not include hardware bias.

This is a hardware-feasibility and noise-boundary result; it is not evidence of quantum computational advantage or industrial PSA validation.
