# IBM QPU PSA-breakthrough MLAE result

- Job ID: `db4mlp04qg6s73c2d04g`
- Backend: `ibm_fez`
- Plan: `open`
- Submitted (UTC): `2026-10-09T22:29:56.757349+00:00`
- Backend calibration: `2026-10-10T06:50:51+09:00`
- QPU charge time: `5 s`
- Resource usage: `0.0818 resource_units`
- Exact event probability: `0.625000`
- Hardware MLAE estimate: `0.603845`
- Absolute error: `0.021155`
- Likelihood interval: `[0.601325, 0.606330]`
- Oracle-query count: `36864`

| m | shots | good | observed | ideal amplified | depth | 2Q gates | initial layout |
|---:|---:|---:|---:|---:|---:|---:|:---|
| 0 | 4096 | 2580 | 0.629883 | 0.625000 | 4 | 0 | `[86, 132, 4]` |
| 1 | 4096 | 817 | 0.199463 | 0.156250 | 72 | 19 | `[144, 142, 143]` |
| 2 | 4096 | 3799 | 0.927490 | 0.976563 | 134 | 37 | `[142, 140, 141]` |

The shallow m=0 circuit reproduces the event probability closely, while the deeper amplified circuits show gate-noise distortion. The likelihood interval is conditional on the ideal MLAE observation model and therefore does not include hardware bias.

This is a hardware-feasibility and noise-boundary result; it is not evidence of quantum computational advantage or industrial PSA validation.
