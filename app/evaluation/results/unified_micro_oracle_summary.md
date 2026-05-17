# Unified Iceberg Experiment Summary

Baseline rows: 12.
Ablation rows: 18.

## Baseline By Model And Target

| model | target | n | completed | failed | elicitation_success_mean | pareto_gain_mean | hallucination_rate_mean | turns_mean |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Pro/zai-org/GLM-5.1 | v1_prompt_cot | 6 | 6 | 0 | 0.167 | 103.167 | 0.347 | 6.667 |
| Pro/zai-org/GLM-5.1 | v1_prompt_direct | 6 | 6 | 0 | 0.167 | 103.167 | 0.372 | 6.667 |

## Baseline Constraint Gradient

| target | constraint_count | n | completed | failed | elicitation_success_mean | pareto_gain_mean | turns_mean |
| --- | --- | --- | --- | --- | --- | --- | --- |
| v1_prompt_cot | 1 | 6 | 6 | 0 | 0.167 | 103.167 | 6.667 |
| v1_prompt_direct | 1 | 6 | 6 | 0 | 0.167 | 103.167 | 6.667 |

## Ablation By Mode

| ablation_mode | n | completed | failed | mae_mean | topk_f1_mean | boi_mean | eudr_slope_mean | pcg_final_coverage_mean | valid_probe_hit_rate_mean | valid_probe_coverage_mean | msti_mean_mean | cardinal_trigger_rate_mean | kbv_rate_mean |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| full | 6 | 4 | 2 | 0.185 | 0.083 | 0.667 | 1.146 | 0.167 | 0.500 | 0.556 | 0.859 | 0.278 | 0.167 |
| no_tracker | 6 | 4 | 2 | 0.169 | 0.083 | 0.000 | 0.000 | 0.333 | 0.667 | 0.500 | 0.763 | 0.278 | 0.000 |
| no_ucb | 6 | 5 | 1 | 0.190 | 0.083 | 0.676 | 0.921 | 0.000 | 0.167 | 0.222 | 0.080 | 0.333 | 0.000 |

## Ablation Constraint Gradient

| ablation_mode | constraint_count | n | completed | failed | mae_mean | topk_f1_mean | eudr_slope_mean | pcg_final_coverage_mean | valid_probe_hit_rate_mean | valid_probe_coverage_mean |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| full | 1 | 6 | 4 | 2 | 0.185 | 0.083 | 1.146 | 0.167 | 0.500 | 0.556 |
| no_tracker | 1 | 6 | 4 | 2 | 0.169 | 0.083 | 0.000 | 0.333 | 0.667 | 0.500 |
| no_ucb | 1 | 6 | 5 | 1 | 0.190 | 0.083 | 0.921 | 0.000 | 0.167 | 0.222 |
