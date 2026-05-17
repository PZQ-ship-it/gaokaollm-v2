# Unified Iceberg Experiment Summary

Baseline rows: 7.
Ablation rows: 18.

## Baseline By Model And Target

| model | target | n | completed | failed | elicitation_success_mean | pareto_gain_mean | hallucination_rate_mean | turns_mean |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Pro/zai-org/GLM-5.1 | app_pareto | 6 | 5 | 1 | 0.167 | 89.000 | 0.020 | 9.833 |
| Pro/zai-org/GLM-5.1 | v1_prompt_direct | 1 | 0 | 1 | 0.000 | 0.000 |  | 0.000 |

## Baseline Constraint Gradient

| target | constraint_count | n | completed | failed | elicitation_success_mean | pareto_gain_mean | turns_mean |
| --- | --- | --- | --- | --- | --- | --- | --- |
| app_pareto | 1 | 6 | 5 | 1 | 0.167 | 89.000 | 9.833 |
| v1_prompt_direct | 1 | 1 | 0 | 1 | 0.000 | 0.000 | 0.000 |

## Ablation By Mode

| ablation_mode | n | completed | failed | mae_mean | topk_f1_mean | boi_mean | eudr_slope_mean | pcg_final_coverage_mean | msti_mean_mean | cardinal_trigger_rate_mean | kbv_rate_mean |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| full | 6 | 6 | 0 | 0.172 | 0.167 | 1.202 | 0.825 | 0.167 | 1.000 | 0.625 | 0.083 |
| no_tracker | 6 | 6 | 0 | 0.149 | 0.083 | 0.000 | 0.000 | 0.167 | 1.000 | 0.444 | 0.083 |
| no_ucb | 6 | 6 | 0 | 0.162 | 0.250 | 1.243 | 0.763 | 0.000 | 0.000 | 0.628 | 0.083 |

## Ablation Constraint Gradient

| ablation_mode | constraint_count | n | completed | failed | mae_mean | topk_f1_mean | eudr_slope_mean | pcg_final_coverage_mean |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| full | 1 | 6 | 6 | 0 | 0.172 | 0.167 | 0.825 | 0.167 |
| no_tracker | 1 | 6 | 6 | 0 | 0.149 | 0.083 | 0.000 | 0.167 |
| no_ucb | 1 | 6 | 6 | 0 | 0.162 | 0.250 | 0.763 | 0.000 |
