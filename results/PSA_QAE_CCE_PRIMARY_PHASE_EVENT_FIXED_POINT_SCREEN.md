# Fixed-point screen for the primary phase-stream event bridge

The fixed-point budget is 10% of nested-holdout p95 event-observable error: purity 1.199e-08, recovery 1.459e-05. A configuration must also retain all 32 frozen event labels.

| input bits | output bits | p95 purity q-error | p95 recovery q-error | both budgets | labels | register proxy |
|---:|---:|---:|---:|---|---:|---:|
| 2 | 12 | 1.037e-05 | 6.461e-03 | False | 32/32 | 52 |
| 3 | 12 | 3.992e-06 | 3.278e-03 | False | 32/32 | 72 |
| 4 | 12 | 2.056e-06 | 1.376e-03 | False | 32/32 | 92 |
| 5 | 12 | 9.524e-07 | 6.120e-04 | False | 32/32 | 112 |
| 6 | 12 | 3.807e-07 | 3.314e-04 | False | 32/32 | 132 |
| 7 | 12 | 3.119e-07 | 1.800e-04 | False | 32/32 | 152 |
| 8 | 12 | 1.439e-07 | 8.929e-05 | False | 32/32 | 172 |
| 9 | 12 | 1.339e-07 | 7.904e-05 | False | 32/32 | 192 |
| 10 | 12 | 1.165e-07 | 7.124e-05 | False | 32/32 | 212 |
| 11 | 12 | 1.478e-07 | 7.554e-05 | False | 32/32 | 232 |
| 12 | 12 | 1.350e-07 | 8.291e-05 | False | 32/32 | 252 |
| 13 | 12 | 1.378e-07 | 8.853e-05 | False | 32/32 | 272 |
| 14 | 12 | 1.378e-07 | 8.853e-05 | False | 32/32 | 292 |
| 15 | 12 | 1.378e-07 | 8.853e-05 | False | 32/32 | 312 |
| 16 | 12 | 1.378e-07 | 8.829e-05 | False | 32/32 | 332 |
| 17 | 12 | 1.378e-07 | 8.829e-05 | False | 32/32 | 352 |
| 18 | 12 | 1.378e-07 | 8.829e-05 | False | 32/32 | 372 |
| 2 | 14 | 1.033e-05 | 6.483e-03 | False | 32/32 | 54 |
| 3 | 14 | 3.991e-06 | 3.264e-03 | False | 32/32 | 74 |
| 4 | 14 | 2.068e-06 | 1.364e-03 | False | 32/32 | 94 |
| 5 | 14 | 9.383e-07 | 5.778e-04 | False | 32/32 | 114 |
| 6 | 14 | 3.851e-07 | 2.981e-04 | False | 32/32 | 134 |
| 7 | 14 | 2.436e-07 | 1.713e-04 | False | 32/32 | 154 |
| 8 | 14 | 1.251e-07 | 7.937e-05 | False | 32/32 | 174 |
| 9 | 14 | 8.013e-08 | 3.901e-05 | False | 32/32 | 194 |
| 10 | 14 | 5.938e-08 | 3.027e-05 | False | 32/32 | 214 |
| 11 | 14 | 2.316e-08 | 1.726e-05 | False | 32/32 | 234 |
| 12 | 14 | 2.850e-08 | 2.075e-05 | False | 32/32 | 254 |
| 13 | 14 | 2.950e-08 | 1.911e-05 | False | 32/32 | 274 |
| 14 | 14 | 3.399e-08 | 1.673e-05 | False | 32/32 | 294 |
| 15 | 14 | 3.450e-08 | 1.760e-05 | False | 32/32 | 314 |
| 16 | 14 | 3.184e-08 | 1.774e-05 | False | 32/32 | 334 |
| 17 | 14 | 3.205e-08 | 1.853e-05 | False | 32/32 | 354 |
| 18 | 14 | 3.205e-08 | 1.676e-05 | False | 32/32 | 374 |
| 2 | 16 | 1.033e-05 | 6.486e-03 | False | 32/32 | 56 |
| 3 | 16 | 4.002e-06 | 3.261e-03 | False | 32/32 | 76 |
| 4 | 16 | 2.079e-06 | 1.362e-03 | False | 32/32 | 96 |
| 5 | 16 | 9.425e-07 | 5.812e-04 | False | 32/32 | 116 |
| 6 | 16 | 3.878e-07 | 2.941e-04 | False | 32/32 | 136 |
| 7 | 16 | 2.431e-07 | 1.743e-04 | False | 32/32 | 156 |
| 8 | 16 | 1.219e-07 | 7.653e-05 | False | 32/32 | 176 |
| 9 | 16 | 7.358e-08 | 3.296e-05 | False | 32/32 | 196 |
| 10 | 16 | 3.057e-08 | 2.377e-05 | False | 32/32 | 216 |
| 11 | 16 | 1.509e-08 | 1.225e-05 | False | 32/32 | 236 |
| 12 | 16 | 1.021e-08 | 6.876e-06 | True | 32/32 | 256 |
| 13 | 16 | 7.853e-09 | 4.933e-06 | True | 32/32 | 276 |
| 14 | 16 | 6.646e-09 | 3.720e-06 | True | 32/32 | 296 |
| 15 | 16 | 6.653e-09 | 4.409e-06 | True | 32/32 | 316 |
| 16 | 16 | 8.081e-09 | 4.388e-06 | True | 32/32 | 336 |
| 17 | 16 | 8.904e-09 | 5.232e-06 | True | 32/32 | 356 |
| 18 | 16 | 8.144e-09 | 4.768e-06 | True | 32/32 | 376 |
| 2 | 18 | 1.033e-05 | 6.486e-03 | False | 32/32 | 58 |
| 3 | 18 | 4.002e-06 | 3.262e-03 | False | 32/32 | 78 |
| 4 | 18 | 2.076e-06 | 1.361e-03 | False | 32/32 | 98 |
| 5 | 18 | 9.427e-07 | 5.802e-04 | False | 32/32 | 118 |
| 6 | 18 | 3.875e-07 | 2.940e-04 | False | 32/32 | 138 |
| 7 | 18 | 2.421e-07 | 1.739e-04 | False | 32/32 | 158 |
| 8 | 18 | 1.265e-07 | 7.737e-05 | False | 32/32 | 178 |
| 9 | 18 | 7.287e-08 | 3.648e-05 | False | 32/32 | 198 |
| 10 | 18 | 3.555e-08 | 2.358e-05 | False | 32/32 | 218 |
| 11 | 18 | 1.338e-08 | 9.931e-06 | False | 32/32 | 238 |
| 12 | 18 | 7.930e-09 | 6.687e-06 | True | 32/32 | 258 |
| 13 | 18 | 3.306e-09 | 2.349e-06 | True | 32/32 | 278 |
| 14 | 18 | 2.623e-09 | 1.226e-06 | True | 32/32 | 298 |
| 15 | 18 | 2.175e-09 | 1.606e-06 | True | 32/32 | 318 |
| 16 | 18 | 2.489e-09 | 1.246e-06 | True | 32/32 | 338 |
| 17 | 18 | 2.328e-09 | 1.235e-06 | True | 32/32 | 358 |
| 18 | 18 | 2.504e-09 | 1.090e-06 | True | 32/32 | 378 |
| 2 | 20 | 1.033e-05 | 6.486e-03 | False | 32/32 | 60 |
| 3 | 20 | 4.001e-06 | 3.262e-03 | False | 32/32 | 80 |
| 4 | 20 | 2.075e-06 | 1.361e-03 | False | 32/32 | 100 |
| 5 | 20 | 9.423e-07 | 5.804e-04 | False | 32/32 | 120 |
| 6 | 20 | 3.873e-07 | 2.940e-04 | False | 32/32 | 140 |
| 7 | 20 | 2.416e-07 | 1.737e-04 | False | 32/32 | 160 |
| 8 | 20 | 1.252e-07 | 7.749e-05 | False | 32/32 | 180 |
| 9 | 20 | 7.300e-08 | 3.590e-05 | False | 32/32 | 200 |
| 10 | 20 | 3.505e-08 | 2.339e-05 | False | 32/32 | 220 |
| 11 | 20 | 1.428e-08 | 1.015e-05 | False | 32/32 | 240 |
| 12 | 20 | 7.736e-09 | 6.159e-06 | True | 32/32 | 260 |
| 13 | 20 | 3.218e-09 | 2.076e-06 | True | 32/32 | 280 |
| 14 | 20 | 1.572e-09 | 1.110e-06 | True | 32/32 | 300 |
| 15 | 20 | 8.088e-10 | 6.125e-07 | True | 32/32 | 320 |
| 16 | 20 | 6.695e-10 | 4.533e-07 | True | 32/32 | 340 |
| 17 | 20 | 6.430e-10 | 3.315e-07 | True | 32/32 | 360 |
| 18 | 20 | 4.978e-10 | 2.487e-07 | True | 32/32 | 380 |

The minimum configuration within both budgets while retaining every event label is `{'bits_per_input': 12, 'sum_bits_per_scalar_output': 16, 'p95_purity_quantization_abs_error': 1.0207365280789914e-08, 'p95_recovery_quantization_abs_error': 6.8762169873726185e-06, 'purity_budget_10pct_nested_holdout_p95': 1.1989325366945635e-08, 'recovery_budget_10pct_nested_holdout_p95': 1.458781506397111e-05, 'within_purity_budget': True, 'within_recovery_budget': True, 'event_matches_vs_actual': 32, 'event_matches_vs_float_map': 32, 'false_positives_vs_actual': 0, 'false_negatives_vs_actual': 0, 'max_active_inputs': 20, 'median_nonzero_bit_weights': 209.5, 'within_both_budgets': True, 'all_event_labels_match': True, 'sequential_scalar_register_proxy_qubits': 256}`.

This screen covers the two adsorption maps and the six event-active stream outputs per map. Reversible stream summation, constant recycle scaling, threshold cross-multiplication, phase marking, uncomputation, CSS iteration, and state loading remain separate modules.
