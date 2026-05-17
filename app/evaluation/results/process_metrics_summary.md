# Process Metrics Diagnostic Summary

This offline summary treats candidate discovery as a negotiator sub-metric (ECDR), not as the main end-to-end score.

## By Mode

| ablation_mode | n | state_update_count_mean | eudr_valid_n | eudr_slope_mean | pcg_hit_rate_mean | pcg_coverage_mean | msti_mean | ctr_mean | boi_valid_n | boi_mean | kbv_valid_n | kbv_rate_mean | ecdr_mean | mae_mean | topk_f1_mean |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| full | 6 | 0.667 | 2 | 1.438 | 0.944 | 0.833 | 0.671 | 0.833 | 2 | 1.078 | 1 | 0.000 | 0.667 | 0.124 | 0.333 |
| no_ucb | 6 | 1.833 | 6 | 1.512 | 0.111 | 0.250 | 0.000 | 0.444 | 6 | 1.301 | 1 | 0.000 | 0.333 | 0.178 | 0.250 |
| no_tracker | 6 | 0.000 | 0 | 0.000 | 1.000 | 0.833 | 0.736 | 0.778 | 0 | 0.000 | 1 | 0.000 | 0.667 | 0.149 | 0.083 |

## Interpretation Notes

- UCB planner: full PCG hit rate=0.944, no-UCB=0.111; candidate discovery ECDR is 0.667 vs 0.333.
- Tracker: full has MAE=0.124, Top-k F1=0.333; no-tracker has MAE=0.149, Top-k F1=0.083.
- BOI/EUDR validity: no-tracker frozen-state count=3; frozen zeros are marked not applicable and excluded from BOI/EUDR means.
- KBV: rates are reported only when a rejection creates later violation opportunities; otherwise the case is marked no_kbv_opportunity.
- ECDR/elicitation success are auxiliary evidence-negotiation outcomes, not the primary tracker metric.

## Case-Level Failures

| case_id | diagnostic_axis | pcg_first_valid_probe_turn | pcg_valid_probe_hit_rate | state_status | notes |
| --- | --- | --- | --- | --- | --- |
| micro-oracle-employment_outcome | employment_outcome | 1 | 0.667 | updated |  |
| micro-oracle-major_quality | major_quality | 1 | 1.000 | updated | KBV no opportunity |
