# Table 2. Matched estimator and policy-selection performance

| method | evaluations | rmse | mae | bias | classification error fraction | correct policy fraction | correct-policy Wilson 95% | median local seconds | interpretation |
|---|---:|---:|---:|---:|---:|---:|---|---:|---|
| MC | 3500 | 0.006794 | 0.005267 | -0.000115 | 0.000000 | 1.000 | [0.981, 1.000] | 0.002982 | reference classical sampling baseline |
| scrambled Sobol RQMC | 4096 | 0.002482 | 0.001934 | -0.000019 | 0.000000 | 1.000 | [0.981, 1.000] | 0.003733 | best observed RMSE and preferred present method |
| defensive-mixture IS | 3500 | 0.010170 | 0.007977 | -0.000200 | 0.001667 | 0.995 | [0.972, 0.999] | 0.004359 | proposal is inefficient for this broad non-rare event |
| noiseless MLAE | 3500 | 0.002892 | 0.002090 | -0.000578 | 0.000000 | 1.000 | [0.981, 1.000] | 0.004019 | improves on crude MC but remains behind RQMC |

Sources: PSA_QAE_CONTINUOUS_POLICY_SELECTION.json, PSA_QAE_CCE_PRIMARY_CASE_PROTOCOL.json.
