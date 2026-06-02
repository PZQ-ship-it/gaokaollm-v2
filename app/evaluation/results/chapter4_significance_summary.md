# Chapter 4 Paired Significance Statistics

- Bootstrap repeats: 10000
- Bootstrap seed: 20260518
- Baseline pairing key: `case_id + model_alias`
- Ablation pairing key: `case_id`
- Difference column is always `full - comparator`; lower is better only for MAE.

| Suite | Comparison | Metric | n | Full | Comparator | Diff | 95% CI | Holm p | Significant |
|---|---|---:|---:|---:|---:|---:|---|---:|---|
| baseline | 完整系统 vs 静态检索-直接提示 | F1@1 | 150 | 0.733 | 0.700 | 0.033 | [0.007, 0.067] | 0.0276 | yes |
| baseline | 完整系统 vs 静态检索-直接提示 | F1@3 | 150 | 0.640 | 0.600 | 0.040 | [0.009, 0.071] | 0.0148 | yes |
| baseline | 完整系统 vs 静态检索-直接提示 | F1@5 | 150 | 0.693 | 0.673 | 0.020 | [-0.004, 0.047] | 0.1493 | no |
| baseline | 完整系统 vs 静态检索-思维链提示 | F1@1 | 150 | 0.733 | 0.693 | 0.040 | [0.013, 0.073] | 0.0276 | yes |
| baseline | 完整系统 vs 静态检索-思维链提示 | F1@3 | 150 | 0.640 | 0.598 | 0.042 | [0.013, 0.073] | 0.0148 | yes |
| baseline | 完整系统 vs 静态检索-思维链提示 | F1@5 | 150 | 0.693 | 0.671 | 0.023 | [-0.001, 0.048] | 0.1493 | no |
| ablation | 完整系统 vs 去除主动探测 | MAE | 30 | 0.144 | 0.178 | -0.034 | [-0.057, -0.012] | 0.0107 | yes |
| ablation | 完整系统 vs 去除主动探测 | F1@1 | 30 | 0.767 | 0.733 | 0.033 | [0.000, 0.100] | 0.3256 | no |
| ablation | 完整系统 vs 去除主动探测 | F1@3 | 30 | 0.667 | 0.611 | 0.056 | [-0.022, 0.133] | 0.2720 | no |
| ablation | 完整系统 vs 去除主动探测 | F1@5 | 30 | 0.700 | 0.680 | 0.020 | [-0.040, 0.093] | 0.8842 | no |
| ablation | 完整系统 vs 去除后验追踪 | MAE | 30 | 0.144 | 0.149 | -0.005 | [-0.025, 0.016] | 0.6562 | no |
| ablation | 完整系统 vs 去除后验追踪 | F1@1 | 30 | 0.767 | 0.700 | 0.067 | [0.000, 0.167] | 0.3216 | no |
| ablation | 完整系统 vs 去除后验追踪 | F1@3 | 30 | 0.667 | 0.600 | 0.067 | [-0.011, 0.156] | 0.2720 | no |
| ablation | 完整系统 vs 去除后验追踪 | F1@5 | 30 | 0.700 | 0.673 | 0.027 | [-0.033, 0.100] | 0.8842 | no |
