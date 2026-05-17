# Unified Iceberg Experiment Summary

Baseline rows: 450.
Ablation rows: 90.

## Baseline By Model And Target

| model | target | n | completed | failed | elicitation_success_mean | pareto_gain_mean | hallucination_rate_mean | turns_mean | recommendation_f1_at_1_mean | recommendation_f1_at_3_mean | recommendation_f1_at_5_mean | recommendation_f1_at_10_mean | retrieval_f1_at_1_mean | retrieval_f1_at_3_mean | retrieval_f1_at_5_mean | retrieval_f1_at_10_mean |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Pro/MiniMaxAI/MiniMax-M2.5 | app_pareto | 30 | 30 | 0 | 0.200 | 18.000 | 0.116 | 6.867 | 0.700 | 0.644 | 0.707 | 0.827 | 0.033 | 0.144 | 0.225 | 0.426 |
| Pro/MiniMaxAI/MiniMax-M2.5 | v1_prompt_cot | 30 | 30 | 0 | 0.100 | 17.867 | 0.542 | 12.733 | 0.633 | 0.578 | 0.667 | 0.810 | 0.067 | 0.078 | 0.100 | 0.186 |
| Pro/MiniMaxAI/MiniMax-M2.5 | v1_prompt_direct | 30 | 30 | 0 | 0.033 | 0.033 | 0.593 | 12.933 | 0.633 | 0.578 | 0.667 | 0.810 | 0.067 | 0.078 | 0.100 | 0.186 |
| Pro/deepseek-ai/DeepSeek-V3.2 | app_pareto | 30 | 30 | 0 | 0.200 | 18.000 | 0.116 | 6.800 | 0.667 | 0.633 | 0.700 | 0.837 | 0.033 | 0.144 | 0.225 | 0.426 |
| Pro/deepseek-ai/DeepSeek-V3.2 | v1_prompt_cot | 30 | 30 | 0 | 0.033 | 0.033 | 0.618 | 12.667 | 0.633 | 0.578 | 0.673 | 0.810 | 0.067 | 0.078 | 0.100 | 0.186 |
| Pro/deepseek-ai/DeepSeek-V3.2 | v1_prompt_direct | 30 | 30 | 0 | 0.033 | 0.033 | 0.590 | 13.000 | 0.633 | 0.578 | 0.667 | 0.810 | 0.067 | 0.078 | 0.100 | 0.186 |
| Pro/moonshotai/Kimi-K2.6 | app_pareto | 30 | 30 | 0 | 0.200 | 18.000 | 0.116 | 7.067 | 0.700 | 0.700 | 0.727 | 0.813 | 0.033 | 0.144 | 0.225 | 0.426 |
| Pro/moonshotai/Kimi-K2.6 | v1_prompt_cot | 30 | 30 | 0 | 0.000 | 0.000 | 0.493 | 13.000 | 0.633 | 0.578 | 0.673 | 0.810 | 0.067 | 0.078 | 0.100 | 0.186 |
| Pro/moonshotai/Kimi-K2.6 | v1_prompt_direct | 30 | 30 | 0 | 0.000 | 0.000 | 0.519 | 13.000 | 0.633 | 0.578 | 0.667 | 0.813 | 0.067 | 0.078 | 0.100 | 0.186 |
| Pro/zai-org/GLM-5.1 | app_pareto | 30 | 30 | 0 | 0.233 | 18.033 | 0.116 | 6.667 | 0.700 | 0.644 | 0.687 | 0.793 | 0.033 | 0.144 | 0.225 | 0.426 |
| Pro/zai-org/GLM-5.1 | v1_prompt_cot | 30 | 30 | 0 | 0.000 | 0.000 | 0.477 | 13.000 | 0.633 | 0.578 | 0.667 | 0.813 | 0.067 | 0.078 | 0.100 | 0.186 |
| Pro/zai-org/GLM-5.1 | v1_prompt_direct | 30 | 30 | 0 | 0.033 | 0.033 | 0.550 | 12.733 | 0.633 | 0.578 | 0.673 | 0.810 | 0.067 | 0.078 | 0.100 | 0.186 |
| Qwen/Qwen3.6-35B-A3B | app_pareto | 30 | 30 | 0 | 0.200 | 18.000 | 0.116 | 6.933 | 0.700 | 0.667 | 0.700 | 0.810 | 0.033 | 0.144 | 0.225 | 0.426 |
| Qwen/Qwen3.6-35B-A3B | v1_prompt_cot | 30 | 30 | 0 | 0.000 | 0.000 | 0.514 | 13.000 | 0.633 | 0.567 | 0.660 | 0.810 | 0.067 | 0.078 | 0.100 | 0.186 |
| Qwen/Qwen3.6-35B-A3B | v1_prompt_direct | 30 | 30 | 0 | 0.033 | 0.033 | 0.582 | 12.800 | 0.633 | 0.578 | 0.660 | 0.807 | 0.067 | 0.078 | 0.100 | 0.186 |

## Baseline Constraint Gradient

| target | constraint_count | n | completed | failed | elicitation_success_mean | pareto_gain_mean | turns_mean | recommendation_f1_at_1_mean | recommendation_f1_at_3_mean | recommendation_f1_at_5_mean | recommendation_f1_at_10_mean | retrieval_f1_at_1_mean | retrieval_f1_at_3_mean | retrieval_f1_at_5_mean | retrieval_f1_at_10_mean |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| app_pareto | 1 | 150 | 150 | 0 | 0.207 | 18.007 | 6.867 | 0.693 | 0.658 | 0.704 | 0.816 | 0.033 | 0.144 | 0.225 | 0.426 |
| v1_prompt_cot | 1 | 150 | 150 | 0 | 0.027 | 3.580 | 12.880 | 0.633 | 0.576 | 0.668 | 0.811 | 0.067 | 0.078 | 0.100 | 0.186 |
| v1_prompt_direct | 1 | 150 | 150 | 0 | 0.027 | 0.027 | 12.893 | 0.633 | 0.578 | 0.667 | 0.810 | 0.067 | 0.078 | 0.100 | 0.186 |

## Ablation By Mode

| ablation_mode | n | completed | failed | mae_mean | topk_f1_mean | recommendation_f1_at_1_mean | recommendation_f1_at_3_mean | recommendation_f1_at_5_mean | recommendation_f1_at_10_mean | retrieval_f1_at_1_mean | retrieval_f1_at_3_mean | retrieval_f1_at_5_mean | retrieval_f1_at_10_mean | boi_mean | eudr_slope_mean | pcg_final_coverage_mean | valid_probe_hit_rate_mean | valid_probe_coverage_mean | msti_mean_mean | cardinal_trigger_rate_mean | kbv_rate_mean |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| full | 30 | 30 | 0 | 0.134 | 0.350 | 0.700 | 0.633 | 0.693 | 0.797 | 0.033 | 0.144 | 0.225 | 0.426 | 1.092 | 1.447 | 1.000 | 0.728 | 0.856 | 0.945 | 0.564 | 0.044 |
| no_tracker | 30 | 30 | 0 | 0.149 | 0.083 | 0.633 | 0.578 | 0.667 | 0.810 | 0.033 | 0.144 | 0.225 | 0.426 | 0.000 | 0.000 | 1.000 | 0.783 | 0.833 | 0.945 | 0.633 | 0.044 |
| no_ucb | 30 | 30 | 0 | 0.172 | 0.183 | 0.633 | 0.578 | 0.660 | 0.780 | 0.033 | 0.144 | 0.225 | 0.426 | 1.288 | 1.353 | 0.000 | 0.197 | 0.256 | 0.024 | 0.394 | 0.067 |

## Ablation Constraint Gradient

| ablation_mode | constraint_count | n | completed | failed | mae_mean | topk_f1_mean | recommendation_f1_at_1_mean | recommendation_f1_at_3_mean | recommendation_f1_at_5_mean | recommendation_f1_at_10_mean | retrieval_f1_at_1_mean | retrieval_f1_at_3_mean | retrieval_f1_at_5_mean | retrieval_f1_at_10_mean | eudr_slope_mean | pcg_final_coverage_mean | valid_probe_hit_rate_mean | valid_probe_coverage_mean |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| full | 1 | 30 | 30 | 0 | 0.134 | 0.350 | 0.700 | 0.633 | 0.693 | 0.797 | 0.033 | 0.144 | 0.225 | 0.426 | 1.447 | 1.000 | 0.728 | 0.856 |
| no_tracker | 1 | 30 | 30 | 0 | 0.149 | 0.083 | 0.633 | 0.578 | 0.667 | 0.810 | 0.033 | 0.144 | 0.225 | 0.426 | 0.000 | 1.000 | 0.783 | 0.833 |
| no_ucb | 1 | 30 | 30 | 0 | 0.172 | 0.183 | 0.633 | 0.578 | 0.660 | 0.780 | 0.033 | 0.144 | 0.225 | 0.426 | 1.353 | 0.000 | 0.197 | 0.256 |
