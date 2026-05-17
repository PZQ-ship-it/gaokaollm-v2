# Unified Iceberg Experiment Summary

Baseline rows: 9.
Ablation rows: 9.

## Baseline By Model And Target

| model | target | n | completed | failed | elicitation_success_mean | pareto_gain_mean | hallucination_rate_mean | turns_mean |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Pro/zai-org/GLM-5.1 | app_pareto | 3 | 2 | 1 | 0.000 | 0.000 | 0.333 | 8.667 |
| Pro/zai-org/GLM-5.1 | v1_prompt_cot | 3 | 3 | 0 | 0.000 | 0.000 | 0.568 | 13.000 |
| Pro/zai-org/GLM-5.1 | v1_prompt_direct | 3 | 3 | 0 | 0.000 | 0.000 | 0.437 | 13.000 |

## Baseline Constraint Gradient

| target | constraint_count | n | completed | failed | elicitation_success_mean | pareto_gain_mean | turns_mean |
| --- | --- | --- | --- | --- | --- | --- | --- |
| app_pareto | 1 | 3 | 2 | 1 | 0.000 | 0.000 | 8.667 |
| v1_prompt_cot | 1 | 3 | 3 | 0 | 0.000 | 0.000 | 13.000 |
| v1_prompt_direct | 1 | 3 | 3 | 0 | 0.000 | 0.000 | 13.000 |

## Ablation By Mode

| ablation_mode | n | completed | failed | mae_mean | topk_f1_mean | boi_mean | eudr_slope_mean | pcg_final_coverage_mean | msti_mean_mean | cardinal_trigger_rate_mean | kbv_rate_mean |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| full | 3 | 3 | 0 | 0.140 | 0.000 | 0.000 | 0.000 | 0.000 | 0.615 | 1.000 | 0.333 |
| no_tracker | 3 | 1 | 2 | 0.180 | 0.000 | 0.000 | 0.000 | 0.000 | 0.615 | 0.333 | 0.333 |
| no_ucb | 3 | 2 | 1 | 0.160 | 0.000 | 0.000 | 0.000 | 0.000 | 0.615 | 0.667 | 0.333 |

## Ablation Constraint Gradient

| ablation_mode | constraint_count | n | completed | failed | mae_mean | topk_f1_mean | eudr_slope_mean | pcg_final_coverage_mean |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| full | 1 | 3 | 3 | 0 | 0.140 | 0.000 | 0.000 | 0.000 |
| no_tracker | 1 | 3 | 1 | 2 | 0.180 | 0.000 | 0.000 | 0.000 |
| no_ucb | 1 | 3 | 2 | 1 | 0.160 | 0.000 | 0.000 | 0.000 |
