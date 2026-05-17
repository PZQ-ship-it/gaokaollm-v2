# Unified Iceberg Experiment Summary

Baseline rows: 450.
Ablation rows: 90.

## Baseline By Model And Target

| model | target | n | completed | failed | elicitation_success_mean | pareto_gain_mean | hallucination_rate_mean | turns_mean |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Pro/MiniMaxAI/MiniMax-M2.5 | app_pareto | 30 | 30 | 0 | 0.067 | 0.000 | 0.175 | 12.600 |
| Pro/MiniMaxAI/MiniMax-M2.5 | v1_prompt_cot | 30 | 30 | 0 | 0.133 | 0.033 | 0.585 | 12.000 |
| Pro/MiniMaxAI/MiniMax-M2.5 | v1_prompt_direct | 30 | 30 | 0 | 0.133 | 0.067 | 0.630 | 12.733 |
| Pro/deepseek-ai/DeepSeek-V3.2 | app_pareto | 30 | 30 | 0 | 0.100 | 0.067 | 0.192 | 12.733 |
| Pro/deepseek-ai/DeepSeek-V3.2 | v1_prompt_cot | 30 | 30 | 0 | 0.067 | 0.000 | 0.616 | 12.267 |
| Pro/deepseek-ai/DeepSeek-V3.2 | v1_prompt_direct | 30 | 30 | 0 | 0.100 | 17.900 | 0.617 | 12.533 |
| Pro/moonshotai/Kimi-K2.6 | app_pareto | 30 | 30 | 0 | 0.033 | 0.033 | 0.208 | 12.667 |
| Pro/moonshotai/Kimi-K2.6 | v1_prompt_cot | 30 | 30 | 0 | 0.033 | 0.000 | 0.573 | 12.667 |
| Pro/moonshotai/Kimi-K2.6 | v1_prompt_direct | 30 | 30 | 0 | 0.100 | 17.867 | 0.582 | 12.267 |
| Pro/zai-org/GLM-5.1 | app_pareto | 30 | 30 | 0 | 0.067 | 0.033 | 0.150 | 12.800 |
| Pro/zai-org/GLM-5.1 | v1_prompt_cot | 30 | 30 | 0 | 0.067 | 0.033 | 0.479 | 12.800 |
| Pro/zai-org/GLM-5.1 | v1_prompt_direct | 30 | 30 | 0 | 0.033 | 13.567 | 0.580 | 12.467 |
| Qwen/Qwen3.6-35B-A3B | app_pareto | 30 | 30 | 0 | 0.067 | 13.567 | 0.228 | 12.867 |
| Qwen/Qwen3.6-35B-A3B | v1_prompt_cot | 30 | 30 | 0 | 0.000 | 0.000 | 0.569 | 12.800 |
| Qwen/Qwen3.6-35B-A3B | v1_prompt_direct | 30 | 30 | 0 | 0.033 | 0.033 | 0.543 | 12.667 |

## Baseline Constraint Gradient

| target | constraint_count | n | completed | failed | elicitation_success_mean | pareto_gain_mean | turns_mean |
| --- | --- | --- | --- | --- | --- | --- | --- |
| app_pareto | 1 | 150 | 150 | 0 | 0.067 | 2.740 | 12.733 |
| v1_prompt_cot | 1 | 150 | 150 | 0 | 0.060 | 0.013 | 12.507 |
| v1_prompt_direct | 1 | 150 | 150 | 0 | 0.080 | 9.887 | 12.533 |

## Ablation By Mode

| ablation_mode | n | completed | failed | mae_mean | topk_f1_mean | boi_mean | eudr_slope_mean | pcg_final_coverage_mean | msti_mean_mean | cardinal_trigger_rate_mean | kbv_rate_mean |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| full | 30 | 30 | 0 | 0.149 | 0.083 | 0.000 | 0.000 | 0.167 | 0.514 | 0.494 | 0.183 |
| no_tracker | 30 | 30 | 0 | 0.149 | 0.083 | 0.000 | 0.000 | 0.167 | 0.514 | 0.428 | 0.113 |
| no_ucb | 30 | 30 | 0 | 0.149 | 0.083 | 0.000 | 0.000 | 0.000 | 0.514 | 0.397 | 0.119 |

## Ablation Constraint Gradient

| ablation_mode | constraint_count | n | completed | failed | mae_mean | topk_f1_mean | eudr_slope_mean | pcg_final_coverage_mean |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| full | 1 | 30 | 30 | 0 | 0.149 | 0.083 | 0.000 | 0.167 |
| no_tracker | 1 | 30 | 30 | 0 | 0.149 | 0.083 | 0.000 | 0.167 |
| no_ucb | 1 | 30 | 30 | 0 | 0.149 | 0.083 | 0.000 | 0.000 |
