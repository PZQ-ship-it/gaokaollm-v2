# Unified Iceberg Experiment Summary

Baseline rows: 343.
Ablation rows: 90.

## Baseline By Model And Target

| model | target | n | completed | failed | elicitation_success_mean | pareto_gain_mean | hallucination_rate_mean | turns_mean |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Pro/MiniMaxAI/MiniMax-M2.5 | app_pareto | 30 | 30 | 0 | 0.200 | 18.000 | 0.113 | 7.467 |
| Pro/MiniMaxAI/MiniMax-M2.5 | v1_prompt_cot | 16 | 16 | 0 | 0.125 | 0.125 | 0.513 | 12.250 |
| Pro/MiniMaxAI/MiniMax-M2.5 | v1_prompt_direct | 30 | 30 | 0 | 0.000 | 0.000 | 0.594 | 12.933 |
| Pro/deepseek-ai/DeepSeek-V3.2 | app_pareto | 30 | 30 | 0 | 0.167 | 17.967 | 0.113 | 7.333 |
| Pro/deepseek-ai/DeepSeek-V3.2 | v1_prompt_cot | 9 | 8 | 1 | 0.000 | 0.000 | 0.672 | 11.556 |
| Pro/deepseek-ai/DeepSeek-V3.2 | v1_prompt_direct | 30 | 30 | 0 | 0.067 | 0.100 | 0.556 | 12.400 |
| Pro/moonshotai/Kimi-K2.6 | app_pareto | 30 | 30 | 0 | 0.167 | 17.967 | 0.113 | 7.467 |
| Pro/moonshotai/Kimi-K2.6 | v1_prompt_cot | 4 | 4 | 0 | 0.000 | 0.000 | 0.721 | 13.000 |
| Pro/moonshotai/Kimi-K2.6 | v1_prompt_direct | 30 | 30 | 0 | 0.033 | 0.033 | 0.517 | 12.800 |
| Pro/zai-org/GLM-5.1 | app_pareto | 30 | 30 | 0 | 0.200 | 18.000 | 0.113 | 7.667 |
| Pro/zai-org/GLM-5.1 | v1_prompt_cot | 8 | 8 | 0 | 0.000 | 0.000 | 0.631 | 13.000 |
| Pro/zai-org/GLM-5.1 | v1_prompt_direct | 30 | 30 | 0 | 0.000 | 0.000 | 0.519 | 13.000 |
| Qwen/Qwen3.6-35B-A3B | app_pareto | 30 | 30 | 0 | 0.167 | 0.167 | 0.113 | 7.333 |
| Qwen/Qwen3.6-35B-A3B | v1_prompt_cot | 6 | 6 | 0 | 0.000 | 0.000 | 0.648 | 13.000 |
| Qwen/Qwen3.6-35B-A3B | v1_prompt_direct | 30 | 30 | 0 | 0.000 | 0.000 | 0.565 | 13.000 |

## Baseline Constraint Gradient

| target | constraint_count | n | completed | failed | elicitation_success_mean | pareto_gain_mean | turns_mean |
| --- | --- | --- | --- | --- | --- | --- | --- |
| app_pareto | 1 | 150 | 150 | 0 | 0.180 | 14.420 | 7.453 |
| v1_prompt_cot | 1 | 43 | 42 | 1 | 0.047 | 0.047 | 12.419 |
| v1_prompt_direct | 1 | 150 | 150 | 0 | 0.020 | 0.027 | 12.827 |

## Ablation By Mode

| ablation_mode | n | completed | failed | mae_mean | topk_f1_mean | boi_mean | eudr_slope_mean | pcg_final_coverage_mean | valid_probe_hit_rate_mean | valid_probe_coverage_mean | msti_mean_mean | cardinal_trigger_rate_mean | kbv_rate_mean |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| full | 30 | 30 | 0 | 0.136 | 0.383 | 1.200 | 1.414 | 1.000 | 0.728 | 0.833 | 0.945 | 0.531 | 0.061 |
| no_tracker | 30 | 30 | 0 | 0.149 | 0.083 | 0.000 | 0.000 | 1.000 | 0.783 | 0.833 | 0.945 | 0.592 | 0.056 |
| no_ucb | 30 | 29 | 1 | 0.171 | 0.167 | 1.262 | 1.392 | 0.000 | 0.197 | 0.294 | 0.032 | 0.503 | 0.078 |

## Ablation Constraint Gradient

| ablation_mode | constraint_count | n | completed | failed | mae_mean | topk_f1_mean | eudr_slope_mean | pcg_final_coverage_mean | valid_probe_hit_rate_mean | valid_probe_coverage_mean |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| full | 1 | 30 | 30 | 0 | 0.136 | 0.383 | 1.414 | 1.000 | 0.728 | 0.833 |
| no_tracker | 1 | 30 | 30 | 0 | 0.149 | 0.083 | 0.000 | 1.000 | 0.783 | 0.833 |
| no_ucb | 1 | 30 | 29 | 1 | 0.171 | 0.167 | 1.392 | 0.000 | 0.197 | 0.294 |
