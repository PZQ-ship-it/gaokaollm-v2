# Process Metrics Diagnostic Summary

This offline summary treats candidate discovery as a negotiator sub-metric (ECDR), not as the main end-to-end score.

## By Mode

| ablation_mode | n | state_update_count_mean | eudr_valid_n | eudr_slope_mean | pcg_hit_rate_mean | pcg_coverage_mean | msti_mean | ctr_mean | boi_valid_n | boi_mean | kbv_valid_n | kbv_rate_mean | ecdr_mean | mae_mean | recommendation_f1_at_1_mean | recommendation_f1_at_3_mean | recommendation_f1_at_5_mean | recommendation_f1_at_10_mean |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| full | 30 | 1.800 | 26 | 1.721 | 0.725 | 0.833 | 0.945 | 0.603 | 26 | 1.090 | 30 | 0.169 | 0.233 | 0.144 | 0.767 | 0.667 | 0.700 | 0.783 |
| no_ucb | 30 | 1.900 | 28 | 1.573 | 0.125 | 0.183 | 0.024 | 0.489 | 28 | 1.308 | 30 | 0.083 | 0.200 | 0.178 | 0.733 | 0.611 | 0.680 | 0.787 |
| no_tracker | 30 | 0.000 | 0 | 0.000 | 0.783 | 0.833 | 0.945 | 0.600 | 0 | 0.000 | 30 | 0.158 | 0.233 | 0.149 | 0.700 | 0.600 | 0.673 | 0.787 |

## Interpretation Notes

- UCB planner: full PCG hit rate=0.725, no-UCB=0.125; candidate discovery ECDR is 0.233 vs 0.200.
- Tracker: full has MAE=0.144, F1@1/3/5/10=0.767/0.667/0.700/0.783; no-tracker has MAE=0.149, F1@1/3/5/10=0.700/0.600/0.673/0.787.
- BOI/EUDR validity: no-tracker frozen-state count=26; frozen zeros are marked not applicable and excluded from BOI/EUDR means.
- KBV: rates are reported only when a rejection creates later violation opportunities; otherwise the case is marked no_kbv_opportunity.
- ECDR/elicitation success are auxiliary evidence-negotiation outcomes, not the primary tracker metric.

## Case-Level Failures

| case_id | diagnostic_axis | pcg_first_valid_probe_turn | pcg_valid_probe_hit_rate | state_status | notes |
| --- | --- | --- | --- | --- | --- |
| three-constrain-major_tier-560-006 | major_tier | 1 | 0.667 | updated |  |
| three-constrain-geo_tier-520-001 | geo_tier | 1 | 0.667 | updated |  |
| three-constrain-major_tier-570-007 | major_tier | 1 | 0.667 | updated |  |
| three-constrain-major_tier-650-010 | major_tier | 1 | 0.667 | updated |  |
| three-constrain-risk_tier-600-012 | risk_tier | 1 | 0.667 | updated |  |
| three-constrain-major_tier-590-008 | major_tier | 1 | 0.667 | updated |  |
| three-constrain-major_tier-600-009 | major_tier | 1 | 0.750 | updated |  |
| three-constrain-tuition_value-520-016 | tuition_value | 1 | 0.667 | updated |  |
| three-constrain-risk_tier-600-013 | risk_tier | 1 | 0.750 | updated |  |
| three-constrain-tuition_value-550-017 | tuition_value | 1 | 0.667 | updated |  |
| three-constrain-tuition_value-600-018 | tuition_value | 1 | 0.667 | updated |  |
| three-constrain-major_quality-590-022 | major_quality | 1 | 0.667 | updated |  |
| three-constrain-tuition_value-550-020 | tuition_value | 1 | 0.667 | updated |  |
| three-constrain-major_quality-600-021 | major_quality | 1 | 0.667 | updated |  |
| three-constrain-major_quality-590-023 | major_quality | 1 | 0.750 | updated |  |
| three-constrain-tuition_value-610-019 | tuition_value | 1 | 0.667 | updated |  |
| three-constrain-major_quality-680-025 | major_quality | 1 | 0.667 | updated |  |
| three-constrain-employment_outcome-600-028 | employment_outcome | 1 | 0.667 | updated |  |
| three-constrain-employment_outcome-550-027 | employment_outcome | 1 | 0.750 | updated |  |
| three-constrain-major_quality-620-024 | major_quality | 1 | 0.750 | updated |  |
| three-constrain-employment_outcome-650-030 | employment_outcome | 1 | 1.000 | single_turn_no_update_opportunity | BOI single_turn_no_update_opportunity; EUDR single_turn_no_update_opportunity |
| three-constrain-employment_outcome-620-029 | employment_outcome | 1 | 0.667 | updated |  |
| three-constrain-employment_outcome-520-026 | employment_outcome | 1 | 0.667 | updated |  |
