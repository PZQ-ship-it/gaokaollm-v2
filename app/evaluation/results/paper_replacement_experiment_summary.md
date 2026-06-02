# Unified Iceberg Experiment Summary

Baseline rows: 450.
Ablation rows: 90.

## Baseline By Model And Target

| model_alias | target | n | completed | failed | elicitation_success_mean | pareto_gain_mean | hallucination_rate_mean | turns_mean | recommendation_f1_at_1_mean | recommendation_f1_at_3_mean | recommendation_f1_at_5_mean | recommendation_f1_at_10_mean | retrieval_f1_at_1_mean | retrieval_f1_at_3_mean | retrieval_f1_at_5_mean | retrieval_f1_at_10_mean |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| DeepSeek-V3.2 | app_pareto | 30 | 30 | 0 | 0.200 | 18.000 | 0.116 | 6.800 | 0.733 | 0.644 | 0.687 | 0.777 | 0.033 | 0.133 | 0.228 | 0.394 |
| DeepSeek-V3.2 | v1_prompt_cot | 30 | 30 | 0 | 0.067 | 0.033 | 0.602 | 12.733 | 0.700 | 0.600 | 0.673 | 0.780 | 0.067 | 0.100 | 0.135 | 0.208 |
| DeepSeek-V3.2 | v1_prompt_direct | 30 | 30 | 0 | 0.067 | 0.033 | 0.606 | 12.667 | 0.700 | 0.600 | 0.673 | 0.787 | 0.067 | 0.100 | 0.135 | 0.208 |
| GLM-5.1 | app_pareto | 30 | 30 | 0 | 0.167 | 17.933 | 0.116 | 6.667 | 0.733 | 0.633 | 0.680 | 0.777 | 0.033 | 0.133 | 0.228 | 0.394 |
| GLM-5.1 | v1_prompt_cot | 30 | 30 | 0 | 0.000 | 0.000 | 0.310 | 13.000 | 0.700 | 0.600 | 0.673 | 0.787 | 0.067 | 0.100 | 0.135 | 0.208 |
| GLM-5.1 | v1_prompt_direct | 30 | 30 | 0 | 0.033 | 0.033 | 0.470 | 12.733 | 0.700 | 0.600 | 0.673 | 0.783 | 0.067 | 0.100 | 0.135 | 0.208 |
| Kimi-K2.6 | app_pareto | 30 | 30 | 0 | 0.200 | 0.200 | 0.116 | 6.733 | 0.733 | 0.633 | 0.687 | 0.820 | 0.033 | 0.133 | 0.228 | 0.394 |
| Kimi-K2.6 | v1_prompt_cot | 30 | 30 | 0 | 0.000 | 0.000 | 0.539 | 13.000 | 0.700 | 0.600 | 0.673 | 0.783 | 0.067 | 0.100 | 0.135 | 0.208 |
| Kimi-K2.6 | v1_prompt_direct | 30 | 30 | 0 | 0.000 | 0.000 | 0.456 | 13.000 | 0.700 | 0.600 | 0.673 | 0.787 | 0.067 | 0.100 | 0.135 | 0.208 |
| MiniMax-M2.5 | app_pareto | 30 | 30 | 0 | 0.200 | 18.000 | 0.116 | 6.600 | 0.733 | 0.644 | 0.707 | 0.777 | 0.033 | 0.133 | 0.228 | 0.394 |
| MiniMax-M2.5 | v1_prompt_cot | 30 | 30 | 0 | 0.033 | 0.033 | 0.494 | 12.733 | 0.667 | 0.600 | 0.667 | 0.787 | 0.067 | 0.100 | 0.135 | 0.208 |
| MiniMax-M2.5 | v1_prompt_direct | 30 | 30 | 0 | 0.000 | 0.000 | 0.513 | 12.800 | 0.700 | 0.600 | 0.673 | 0.787 | 0.067 | 0.100 | 0.135 | 0.208 |
| Qwen3.6 | app_pareto | 30 | 30 | 0 | 0.200 | 18.000 | 0.116 | 6.800 | 0.733 | 0.644 | 0.707 | 0.777 | 0.033 | 0.133 | 0.228 | 0.394 |
| Qwen3.6 | v1_prompt_cot | 30 | 30 | 0 | 0.000 | 0.000 | 0.536 | 13.000 | 0.700 | 0.589 | 0.667 | 0.783 | 0.067 | 0.100 | 0.135 | 0.208 |
| Qwen3.6 | v1_prompt_direct | 30 | 30 | 0 | 0.033 | 0.033 | 0.485 | 12.800 | 0.700 | 0.600 | 0.673 | 0.787 | 0.067 | 0.100 | 0.135 | 0.208 |

## Baseline Constraint Gradient

| target | constraint_count | n | completed | failed | elicitation_success_mean | pareto_gain_mean | turns_mean | recommendation_f1_at_1_mean | recommendation_f1_at_3_mean | recommendation_f1_at_5_mean | recommendation_f1_at_10_mean | retrieval_f1_at_1_mean | retrieval_f1_at_3_mean | retrieval_f1_at_5_mean | retrieval_f1_at_10_mean |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| app_pareto | 3 | 150 | 150 | 0 | 0.193 | 14.427 | 6.720 | 0.733 | 0.640 | 0.693 | 0.785 | 0.033 | 0.133 | 0.228 | 0.394 |
| v1_prompt_cot | 3 | 150 | 150 | 0 | 0.020 | 0.013 | 12.893 | 0.693 | 0.598 | 0.671 | 0.784 | 0.067 | 0.100 | 0.135 | 0.208 |
| v1_prompt_direct | 3 | 150 | 150 | 0 | 0.027 | 0.020 | 12.800 | 0.700 | 0.600 | 0.673 | 0.786 | 0.067 | 0.100 | 0.135 | 0.208 |

## Ablation By Mode

| ablation_mode | n | completed | failed | mae_mean | topk_f1_mean | recommendation_f1_at_1_mean | recommendation_f1_at_3_mean | recommendation_f1_at_5_mean | recommendation_f1_at_10_mean | retrieval_f1_at_1_mean | retrieval_f1_at_3_mean | retrieval_f1_at_5_mean | retrieval_f1_at_10_mean | boi_mean | eudr_slope_mean | pcg_final_coverage_mean | valid_probe_hit_rate_mean | valid_probe_coverage_mean | msti_mean_mean | cardinal_trigger_rate_mean | kbv_rate_mean |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| full | 30 | 30 | 0 | 0.144 | 0.233 | 0.767 | 0.667 | 0.700 | 0.783 | 0.033 | 0.133 | 0.228 | 0.394 | 0.945 | 1.492 | 1.000 | 0.725 | 0.833 | 0.945 | 0.603 | 0.169 |
| no_tracker | 30 | 30 | 0 | 0.149 | 0.083 | 0.700 | 0.600 | 0.673 | 0.787 | 0.033 | 0.133 | 0.228 | 0.394 | 0.000 | 0.000 | 1.000 | 0.783 | 0.833 | 0.945 | 0.600 | 0.158 |
| no_ucb | 30 | 30 | 0 | 0.178 | 0.150 | 0.733 | 0.611 | 0.680 | 0.787 | 0.033 | 0.133 | 0.228 | 0.394 | 1.221 | 1.468 | 0.000 | 0.125 | 0.183 | 0.024 | 0.489 | 0.083 |

## Ablation Constraint Gradient

| ablation_mode | constraint_count | n | completed | failed | mae_mean | topk_f1_mean | recommendation_f1_at_1_mean | recommendation_f1_at_3_mean | recommendation_f1_at_5_mean | recommendation_f1_at_10_mean | retrieval_f1_at_1_mean | retrieval_f1_at_3_mean | retrieval_f1_at_5_mean | retrieval_f1_at_10_mean | eudr_slope_mean | pcg_final_coverage_mean | valid_probe_hit_rate_mean | valid_probe_coverage_mean |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| full | 3 | 30 | 30 | 0 | 0.144 | 0.233 | 0.767 | 0.667 | 0.700 | 0.783 | 0.033 | 0.133 | 0.228 | 0.394 | 1.492 | 1.000 | 0.725 | 0.833 |
| no_tracker | 3 | 30 | 30 | 0 | 0.149 | 0.083 | 0.700 | 0.600 | 0.673 | 0.787 | 0.033 | 0.133 | 0.228 | 0.394 | 0.000 | 1.000 | 0.783 | 0.833 |
| no_ucb | 3 | 30 | 30 | 0 | 0.178 | 0.150 | 0.733 | 0.611 | 0.680 | 0.787 | 0.033 | 0.133 | 0.228 | 0.394 | 1.468 | 0.000 | 0.125 | 0.183 |
