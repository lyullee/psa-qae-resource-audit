# Frozen recycle-policy engineering and decision margin

The primary rule chooses the largest recycle candidate whose joint-event probability is at least 0.50. Product-split quantities are exact bookkeeping identities. They are reported to give the outer decision a concrete process interpretation without inventing compressor or economic data.

| recycle | event probability | margin to 0.50 | feasible | external product / gross | recycle / external product | |margin| / RQMC RMSE | |margin| / residual-stress half-width |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.420 | 0.927431 | +0.427431 | True | 0.580 | 0.7241 | 172.18 | 109.42 |
| 0.427 | 0.470440 | -0.029560 | False | 0.573 | 0.7452 | 11.91 | 7.57 |
| 0.430 | 0.283597 | -0.216403 | False | 0.570 | 0.7544 | 87.17 | 55.40 |

The nearest failed candidate is `0.427`. Its probability shortfall is `0.029560`, or `11.91` RQMC RMSE, `10.22` noiseless-MLAE RMSE, and `7.57` residual-stress half-widths. Estimator-scale refinement therefore does not change the frozen surrogate decision.

Within the frozen surrogate, estimator uncertainty is small relative to the nearest chance-constraint classification margin. The outer decision therefore does not benefit from estimator precision below the present RQMC scale. This is a product-split allocation and decision-margin calculation, not compressor duty, operating cost, plant profit, or global optimization.
