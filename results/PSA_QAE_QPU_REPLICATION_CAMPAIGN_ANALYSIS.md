# IBM QPU replication-campaign analysis

Status: **complete_9_of_9**. Completed planned cells: **9/9**.

This analysis inventories only completed real-QPU artifacts that match the frozen three-backend × three-seed design. It never submits or retrieves a workload.

| backend | seed | job | estimate | abs. error | QPU s |
|---|---:|---|---:|---:|---:|
| ibm_marrakesh | 20261009 | `db4mldamb58s7389dmd0` | 0.598320 | 0.026680 | 5.0 |
| ibm_marrakesh | 20261010 | `db4mlj2mb58s7389dmjg` | 0.599740 | 0.025260 | 5.0 |
| ibm_marrakesh | 20261011 | `db4mll04qg6s73c2cvvg` | 0.598305 | 0.026695 | 5.0 |
| ibm_fez | 20261009 | `db4mln84qg6s73c2d01g` | 0.603000 | 0.022000 | 5.0 |
| ibm_fez | 20261010 | `db4mlp04qg6s73c2d04g` | 0.603845 | 0.021155 | 5.0 |
| ibm_fez | 20261011 | `db4mlr4lf4us73c2v4ug` | 0.600110 | 0.024890 | 5.0 |
| ibm_kingston | 20261009 | `db4mlsqmb58s7389dmvg` | 0.590625 | 0.034375 | 5.0 |
| ibm_kingston | 20261010 | `db4mlvcvf2bc73cuqnkg` | 0.599405 | 0.025595 | 5.0 |
| ibm_kingston | 20261011 | `db4mm1kvf2bc73cuqnn0` | 0.599390 | 0.025610 | 5.0 |

The current mean estimate is `0.599193` with mean absolute error `0.025807`. These values describe the completed cells only.

Across the complete design, the between-job SD is `0.003747` and the crossed-design bootstrap interval for the sampled backend/seed mean is `[0.595136, 0.602318]`. This is a descriptive design-variability interval, not a universal noise-calibrated confidence interval.
The backend-mean range is `0.005845`, the seed-mean range is `0.003682`, and the unreplicated backend-by-seed interaction/job-noise RMSE is `0.002108`.

The hardware campaign remains a three-qubit event-kernel boundary. It does not establish end-to-end quantum advantage or industrial PSA validation.
