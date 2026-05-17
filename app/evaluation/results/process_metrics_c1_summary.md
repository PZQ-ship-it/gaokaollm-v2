# Process Metrics Diagnostic Summary

This offline summary treats candidate discovery as a negotiator sub-metric (ECDR), not as the main end-to-end score.

## By Mode

| ablation_mode | n | state_update_count_mean | eudr_valid_n | eudr_slope_mean | pcg_hit_rate_mean | pcg_coverage_mean | msti_mean | ctr_mean | boi_valid_n | boi_mean | kbv_valid_n | kbv_rate_mean | ecdr_mean | mae_mean | recommendation_f1_at_1_mean | recommendation_f1_at_3_mean | recommendation_f1_at_5_mean | recommendation_f1_at_10_mean |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| full | 30 | 1.933 | 26 | 1.670 | 0.728 | 0.856 | 0.945 | 0.564 | 26 | 1.260 | 15 | 0.089 | 0.233 | 0.134 | 0.700 | 0.633 | 0.693 | 0.797 |
| no_ucb | 30 | 2.067 | 28 | 1.450 | 0.197 | 0.256 | 0.024 | 0.394 | 28 | 1.380 | 12 | 0.167 | 0.200 | 0.172 | 0.633 | 0.578 | 0.660 | 0.780 |
| no_tracker | 30 | 0.000 | 0 | 0.000 | 0.783 | 0.833 | 0.945 | 0.633 | 0 | 0.000 | 18 | 0.074 | 0.233 | 0.149 | 0.633 | 0.578 | 0.667 | 0.810 |

## Interpretation Notes

- UCB planner: full PCG hit rate=0.728, no-UCB=0.197; candidate discovery ECDR is 0.233 vs 0.200.
- Tracker: full has MAE=0.134, F1@1/3/5/10=0.700/0.633/0.693/0.797; no-tracker has MAE=0.149, F1@1/3/5/10=0.633/0.578/0.667/0.810.
- BOI/EUDR validity: no-tracker frozen-state count=26; frozen zeros are marked not applicable and excluded from BOI/EUDR means.
- KBV: rates are reported only when a rejection creates later violation opportunities; otherwise the case is marked no_kbv_opportunity.
- ECDR/elicitation success are auxiliary evidence-negotiation outcomes, not the primary tracker metric.

## Case-Level Failures

| case_id | diagnostic_axis | pcg_first_valid_probe_turn | pcg_valid_probe_hit_rate | state_status | notes |
| --- | --- | --- | --- | --- | --- |
| one-constrain-major_tier-560-006 | major_tier | 1 | 0.667 | updated |  |
| one-constrain-geo_tier-520-001 | geo_tier | 1 | 0.750 | updated |  |
| one-constrain-major_tier-570-007 | major_tier | 1 | 0.667 | updated |  |
| one-constrain-major_tier-600-009 | major_tier | 1 | 0.750 | updated | KBV no opportunity |
| one-constrain-major_tier-650-010 | major_tier | 1 | 0.667 | updated |  |
| one-constrain-risk_tier-600-013 | risk_tier | 1 | 0.667 | updated |  |
| one-constrain-risk_tier-600-012 | risk_tier | 1 | 0.667 | updated |  |
| one-constrain-tuition_value-520-016 | tuition_value | 1 | 0.750 | updated | KBV no opportunity |
| one-constrain-tuition_value-600-018 | tuition_value | 1 | 0.750 | updated | KBV no opportunity |
| one-constrain-major_quality-590-023 | major_quality | 1 | 0.667 | updated | KBV no opportunity |
| one-constrain-major_quality-600-021 | major_quality | 1 | 0.667 | updated | KBV no opportunity |
| one-constrain-major_quality-590-022 | major_quality | 1 | 0.667 | updated |  |
| one-constrain-major_quality-620-024 | major_quality | 1 | 0.750 | updated |  |
| one-constrain-tuition_value-550-017 | tuition_value | 1 | 0.667 | updated |  |
| one-constrain-employment_outcome-550-027 | employment_outcome | 1 | 0.667 | updated |  |
| one-constrain-employment_outcome-650-030 | employment_outcome | 1 | 1.000 | single_turn_no_update_opportunity | BOI single_turn_no_update_opportunity; EUDR single_turn_no_update_opportunity; KBV no opportunity |
| one-constrain-employment_outcome-600-028 | employment_outcome | 1 | 0.667 | updated | KBV no opportunity |
| one-constrain-employment_outcome-520-026 | employment_outcome | 1 | 0.667 | updated | KBV no opportunity |
| one-constrain-major_quality-680-025 | major_quality | 1 | 0.667 | updated | KBV no opportunity |
| one-constrain-tuition_value-610-019 | tuition_value | 1 | 0.667 | updated |  |
| one-constrain-major_tier-590-008 | major_tier | 1 | 0.667 | updated |  |
| one-constrain-tuition_value-550-020 | tuition_value | 1 | 0.667 | updated |  |
| one-constrain-employment_outcome-620-029 | employment_outcome | 1 | 0.750 | updated |  |
