# IBM Open multi-backend QPU replication campaign plan

Status: **PREFLIGHT ONLY**. No sampler job was submitted and no QPU quota was consumed.

The frozen experiment uses the exact three-qubit `p=0.625` phase oracle, Grover powers `[0, 1, 2]`, and `4,096` shots per circuit. The matrix contains `3` backends × `3` fixed transpiler seeds = `9` planned jobs and `27` circuits.

If future jobs were charged like the existing 5 s Open-plan job, the matrix would use about `45 s` of QPU allowance. This is an extrapolation, not a guarantee. The campaign has not been executed so the quota remains available to other sessions.

At this preflight, the verified Open instance reported `531 s` remaining of `600 s`; the usage limit was not reached. Usage must be queried again immediately before execution.

| backend | seed | m | depth | 2Q gates | initial layout |
|---|---:|---:|---:|---:|---|
| ibm_marrakesh | 20261009 | 0 | 4 | 0 | `[54, 12, 6]` |
| ibm_marrakesh | 20261009 | 1 | 67 | 17 | `[55, 53, 54]` |
| ibm_marrakesh | 20261009 | 2 | 135 | 37 | `[55, 53, 54]` |
| ibm_marrakesh | 20261010 | 0 | 4 | 0 | `[54, 12, 6]` |
| ibm_marrakesh | 20261010 | 1 | 73 | 19 | `[55, 53, 54]` |
| ibm_marrakesh | 20261010 | 2 | 135 | 37 | `[55, 53, 54]` |
| ibm_marrakesh | 20261011 | 0 | 4 | 0 | `[54, 12, 6]` |
| ibm_marrakesh | 20261011 | 1 | 73 | 19 | `[55, 53, 54]` |
| ibm_marrakesh | 20261011 | 2 | 135 | 37 | `[55, 53, 54]` |
| ibm_fez | 20261009 | 0 | 4 | 0 | `[86, 132, 4]` |
| ibm_fez | 20261009 | 1 | 66 | 17 | `[144, 142, 143]` |
| ibm_fez | 20261009 | 2 | 134 | 37 | `[142, 140, 141]` |
| ibm_fez | 20261010 | 0 | 4 | 0 | `[86, 132, 4]` |
| ibm_fez | 20261010 | 1 | 72 | 19 | `[144, 142, 143]` |
| ibm_fez | 20261010 | 2 | 134 | 37 | `[142, 140, 141]` |
| ibm_fez | 20261011 | 0 | 4 | 0 | `[86, 132, 4]` |
| ibm_fez | 20261011 | 1 | 72 | 19 | `[144, 142, 143]` |
| ibm_fez | 20261011 | 2 | 134 | 37 | `[142, 140, 141]` |
| ibm_kingston | 20261009 | 0 | 4 | 0 | `[11, 21, 148]` |
| ibm_kingston | 20261009 | 1 | 67 | 17 | `[138, 152, 151]` |
| ibm_kingston | 20261009 | 2 | 135 | 37 | `[74, 59, 75]` |
| ibm_kingston | 20261010 | 0 | 4 | 0 | `[11, 21, 148]` |
| ibm_kingston | 20261010 | 1 | 73 | 19 | `[138, 152, 151]` |
| ibm_kingston | 20261010 | 2 | 135 | 37 | `[74, 59, 75]` |
| ibm_kingston | 20261011 | 0 | 4 | 0 | `[11, 21, 148]` |
| ibm_kingston | 20261011 | 1 | 73 | 19 | `[138, 152, 151]` |
| ibm_kingston | 20261011 | 2 | 135 | 37 | `[74, 59, 75]` |

Each future job must be submitted separately with its recorded backend and transpiler seed. Calibration time, runtime metrics, counts, and Open-plan verification are recorded at execution/retrieval time; preflight calibration is not substituted for execution calibration.

The primary analysis treats backend and seed as crossed variability sources. Ideal likelihood intervals remain conditional diagnostics and are not used as hardware-aware confidence intervals.
