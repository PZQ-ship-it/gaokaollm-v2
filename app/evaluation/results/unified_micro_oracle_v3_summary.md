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
| full | 6 | 6 | 0 | 0.124 | 0.333 | 0.359 | 0.479 | 1.000 | 0.944 | 0.833 | 0.671 | 0.833 | 0.000 |
| no_tracker | 6 | 6 | 0 | 0.149 | 0.083 | 0.000 | 0.000 | 1.000 | 1.000 | 0.833 | 0.736 | 0.778 | 0.000 |
| no_ucb | 6 | 6 | 0 | 0.178 | 0.250 | 1.301 | 1.512 | 0.000 | 0.111 | 0.250 | 0.000 | 0.444 | 0.000 |

## Ablation Constraint Gradient

| ablation_mode | constraint_count | n | completed | failed | mae_mean | topk_f1_mean | eudr_slope_mean | pcg_final_coverage_mean | valid_probe_hit_rate_mean | valid_probe_coverage_mean |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| full | 1 | 6 | 6 | 0 | 0.124 | 0.333 | 0.479 | 1.000 | 0.944 | 0.833 |
| no_tracker | 1 | 6 | 6 | 0 | 0.149 | 0.083 | 0.000 | 1.000 | 1.000 | 0.833 |
| no_ucb | 1 | 6 | 6 | 0 | 0.178 | 0.250 | 1.512 | 0.000 | 0.111 | 0.250 |
