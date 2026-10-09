# Fixed-point screen for the parameter-only CSS initializer

The p95 quantization budgets are 10% of nested-held-out p95 errors: CSS state L1 `7.011e-05`, purity `9.811e-08`, and recovery `7.728e-05`. Every configuration is propagated through the full-fit aggregate one-cycle maps and must retain 32/32 event labels.

The minimum accuracy-feasible configuration is `{'bits_per_input': 9, 'sum_bits_per_scalar_output': 14, 'p95_css_state_quantization_relative_l1': 5.6166720276712904e-05, 'p95_purity_quantization_abs_error': 8.93392267831139e-08, 'p95_recovery_quantization_abs_error': 5.021376441052827e-05, 'css_state_budget_10pct_nested_holdout_p95': 7.011052905378725e-05, 'purity_budget_10pct_nested_holdout_p95': 9.810908041418817e-08, 'recovery_budget_10pct_nested_holdout_p95': 7.72813668314426e-05, 'within_css_state_budget': True, 'within_purity_budget': True, 'within_recovery_budget': True, 'event_matches_vs_actual': 32, 'event_matches_vs_float_map': 32, 'max_active_inputs': 10, 'median_nonzero_bit_weights': 78.0, 'negative_state_entries': 0, 'within_all_budgets': True, 'all_event_labels_match': True, 'sequential_scalar_register_proxy_qubits': 104}`.

This screens the 20 scalar affine CSS-state outputs. Reversible state injection/update, tank and spatial states, physical CSS iteration, final event arithmetic, loading, routing, and hardware execution remain separate.
