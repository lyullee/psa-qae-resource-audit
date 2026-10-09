# IBM QPU PSA-breakthrough MLAE result

- Job ID: `db4mlsqmb58s7389dmvg`
- Backend: `ibm_kingston`
- Plan: `open`
- Submitted (UTC): `2026-10-09T22:30:11.901934+00:00`
- Backend calibration: `2026-10-10T06:45:45+09:00`
- QPU charge time: `5 s`
- Resource usage: `0.0823 resource_units`
- Exact event probability: `0.625000`
- Hardware MLAE estimate: `0.590625`
- Absolute error: `0.034375`
- Likelihood interval: `[0.588130, 0.593095]`
- Oracle-query count: `36864`

| m | shots | good | observed | ideal amplified | depth | 2Q gates | initial layout |
|---:|---:|---:|---:|---:|---:|---:|:---|
| 0 | 4096 | 2647 | 0.646240 | 0.625000 | 4 | 0 | `[11, 21, 148]` |
| 1 | 4096 | 855 | 0.208740 | 0.156250 | 67 | 17 | `[138, 152, 151]` |
| 2 | 4096 | 3583 | 0.874756 | 0.976563 | 135 | 37 | `[74, 59, 75]` |

The shallow m=0 circuit reproduces the event probability closely, while the deeper amplified circuits show gate-noise distortion. The likelihood interval is conditional on the ideal MLAE observation model and therefore does not include hardware bias.

This is a hardware-feasibility and noise-boundary result; it is not evidence of quantum computational advantage or industrial PSA validation.
