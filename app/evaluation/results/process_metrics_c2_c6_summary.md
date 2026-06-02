# Process Metrics Diagnostic Summary

This offline summary treats candidate discovery as a negotiator sub-metric (ECDR), not as the main end-to-end score.

## By Mode

| ablation_mode | n | state_update_count_mean | eudr_valid_n | eudr_slope_mean | pcg_hit_rate_mean | pcg_coverage_mean | msti_mean | ctr_mean | boi_valid_n | boi_mean | kbv_valid_n | kbv_rate_mean | ecdr_mean | mae_mean | recommendation_f1_at_1_mean | recommendation_f1_at_3_mean | recommendation_f1_at_5_mean | recommendation_f1_at_10_mean |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| full | 150 | 1.673 | 120 | 1.449 | 0.741 | 0.858 | 0.961 | 0.411 | 120 | 1.158 | 150 | 0.147 | 0.213 | 0.142 | 0.627 | 0.647 | 0.684 | 0.819 |
| no_ucb | 150 | 1.940 | 135 | 1.363 | 0.143 | 0.226 | 0.024 | 0.360 | 135 | 1.326 | 150 | 0.077 | 0.200 | 0.180 | 0.560 | 0.569 | 0.627 | 0.794 |
| no_tracker | 150 | 0.000 | 0 | 0.000 | 0.775 | 0.856 | 0.961 | 0.387 | 0 | 0.000 | 150 | 0.138 | 0.213 | 0.149 | 0.580 | 0.613 | 0.665 | 0.807 |

## Interpretation Notes

- UCB planner: full PCG hit rate=0.741, no-UCB=0.143; candidate discovery ECDR is 0.213 vs 0.200.
- Tracker: full has MAE=0.142, F1@1/3/5/10=0.627/0.647/0.684/0.819; no-tracker has MAE=0.149, F1@1/3/5/10=0.580/0.613/0.665/0.807.
- BOI/EUDR validity: no-tracker frozen-state count=135; frozen zeros are marked not applicable and excluded from BOI/EUDR means.
- KBV: rates are reported only when a rejection creates later violation opportunities; otherwise the case is marked no_kbv_opportunity.
- ECDR/elicitation success are auxiliary evidence-negotiation outcomes, not the primary tracker metric.

## Case-Level Failures

| case_id | diagnostic_axis | pcg_first_valid_probe_turn | pcg_valid_probe_hit_rate | state_status | notes |
| --- | --- | --- | --- | --- | --- |
| two-constrain-major_tier-590-008 | major_tier | 1 | 0.667 | updated |  |
| two-constrain-major_tier-600-009 | major_tier | 1 | 0.667 | updated |  |
| two-constrain-major_tier-650-010 | major_tier | 1 | 0.667 | updated |  |
| two-constrain-major_tier-570-007 | major_tier | 1 | 0.667 | updated |  |
| two-constrain-geo_tier-520-001 | geo_tier | 1 | 0.667 | updated |  |
| two-constrain-major_tier-560-006 | major_tier | 1 | 0.667 | updated |  |
| two-constrain-risk_tier-600-012 | risk_tier | 1 | 0.667 | updated |  |
| two-constrain-risk_tier-600-013 | risk_tier | 1 | 0.667 | updated |  |
| two-constrain-tuition_value-550-017 | tuition_value | 1 | 0.667 | updated |  |
| two-constrain-tuition_value-610-019 | tuition_value | 1 | 0.667 | updated |  |
| two-constrain-tuition_value-600-018 | tuition_value | 1 | 0.667 | updated |  |
| two-constrain-major_quality-600-021 | major_quality | 1 | 0.667 | updated |  |
| two-constrain-major_quality-590-023 | major_quality | 1 | 0.750 | updated |  |
| two-constrain-major_quality-620-024 | major_quality | 1 | 0.750 | updated |  |
| two-constrain-employment_outcome-550-027 | employment_outcome | 1 | 0.667 | updated |  |
| two-constrain-major_quality-590-022 | major_quality | 1 | 0.667 | updated |  |
| two-constrain-employment_outcome-520-026 | employment_outcome | 1 | 0.750 | updated |  |
| two-constrain-major_quality-680-025 | major_quality | 1 | 0.750 | updated |  |
| two-constrain-employment_outcome-600-028 | employment_outcome | 1 | 0.667 | updated |  |
| two-constrain-employment_outcome-650-030 | employment_outcome | 1 | 1.000 | single_turn_no_update_opportunity | BOI single_turn_no_update_opportunity; EUDR single_turn_no_update_opportunity |
| two-constrain-tuition_value-550-020 | tuition_value | 1 | 0.667 | updated |  |
| two-constrain-tuition_value-520-016 | tuition_value | 1 | 0.667 | updated |  |
| two-constrain-employment_outcome-620-029 | employment_outcome | 1 | 0.750 | updated |  |
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
| four-constrain-geo_tier-520-001 | geo_tier | 1 | 0.750 | frozen_state_no_observed_update | BOI frozen_state_no_observed_update; EUDR frozen_state_no_observed_update |
| four-constrain-geo_tier-630-004 | geo_tier | 1 | 0.750 | updated |  |
| four-constrain-major_tier-570-007 | major_tier | 1 | 0.750 | frozen_state_no_observed_update | BOI frozen_state_no_observed_update; EUDR frozen_state_no_observed_update |
| four-constrain-major_tier-560-006 | major_tier | 1 | 0.750 | frozen_state_no_observed_update | BOI frozen_state_no_observed_update; EUDR frozen_state_no_observed_update |
| four-constrain-major_tier-590-008 | major_tier | 1 | 0.750 | updated |  |
| four-constrain-major_tier-600-009 | major_tier | 1 | 0.750 | frozen_state_no_observed_update | BOI frozen_state_no_observed_update; EUDR frozen_state_no_observed_update |
| four-constrain-major_tier-650-010 | major_tier | 1 | 0.750 | frozen_state_no_observed_update | BOI frozen_state_no_observed_update; EUDR frozen_state_no_observed_update |
| four-constrain-risk_tier-600-012 | risk_tier | 1 | 0.750 | updated |  |
| four-constrain-tuition_value-520-016 | tuition_value | 1 | 0.750 | updated |  |
| four-constrain-tuition_value-550-017 | tuition_value | 1 | 0.750 | updated |  |
| four-constrain-tuition_value-600-018 | tuition_value | 1 | 0.750 | frozen_state_no_observed_update | BOI frozen_state_no_observed_update; EUDR frozen_state_no_observed_update |
| four-constrain-risk_tier-600-013 | risk_tier | 1 | 0.750 | updated |  |
| four-constrain-tuition_value-610-019 | tuition_value | 1 | 0.750 | updated |  |
| four-constrain-tuition_value-550-020 | tuition_value | 1 | 0.750 | updated |  |
| four-constrain-major_quality-600-021 | major_quality | 1 | 0.750 | updated |  |
| four-constrain-major_quality-590-022 | major_quality | 1 | 0.750 | frozen_state_no_observed_update | BOI frozen_state_no_observed_update; EUDR frozen_state_no_observed_update |
| four-constrain-major_quality-590-023 | major_quality | 1 | 0.750 | updated |  |
| four-constrain-major_quality-620-024 | major_quality | 1 | 0.750 | frozen_state_no_observed_update | BOI frozen_state_no_observed_update; EUDR frozen_state_no_observed_update |
| four-constrain-major_quality-680-025 | major_quality | 1 | 0.667 | updated |  |
| four-constrain-employment_outcome-520-026 | employment_outcome | 1 | 0.750 | frozen_state_no_observed_update | BOI frozen_state_no_observed_update; EUDR frozen_state_no_observed_update |
| four-constrain-employment_outcome-550-027 | employment_outcome | 1 | 0.750 | updated |  |
| four-constrain-employment_outcome-650-030 | employment_outcome | 1 | 1.000 | single_turn_no_update_opportunity | BOI single_turn_no_update_opportunity; EUDR single_turn_no_update_opportunity |
| four-constrain-employment_outcome-600-028 | employment_outcome | 1 | 0.750 | updated |  |
| four-constrain-employment_outcome-620-029 | employment_outcome | 1 | 0.750 | updated |  |
| five-constrain-geo_tier-520-001 | geo_tier | 1 | 0.750 | updated |  |
| five-constrain-geo_tier-630-004 | geo_tier | 1 | 0.750 | frozen_state_no_observed_update | BOI frozen_state_no_observed_update; EUDR frozen_state_no_observed_update |
| five-constrain-major_tier-560-006 | major_tier | 1 | 0.667 | updated |  |
| five-constrain-major_tier-570-007 | major_tier | 1 | 0.667 | updated |  |
| five-constrain-major_tier-650-010 | major_tier | 1 | 0.750 | updated |  |
| five-constrain-major_tier-590-008 | major_tier | 1 | 0.750 | updated |  |
| five-constrain-major_tier-600-009 | major_tier | 1 | 0.750 | updated |  |
| five-constrain-tuition_value-520-016 | tuition_value | 1 | 0.750 | updated |  |
| five-constrain-risk_tier-600-012 | risk_tier | 1 | 0.750 | updated |  |
| five-constrain-tuition_value-550-017 | tuition_value | 1 | 0.750 | updated |  |
| five-constrain-tuition_value-600-018 | tuition_value | 1 | 0.667 | updated |  |
| five-constrain-risk_tier-600-013 | risk_tier | 1 | 0.750 | updated |  |
| five-constrain-tuition_value-610-019 | tuition_value | 1 | 0.750 | updated |  |
| five-constrain-tuition_value-550-020 | tuition_value | 1 | 0.750 | updated |  |
| five-constrain-major_quality-600-021 | major_quality | 1 | 0.750 | updated |  |
| five-constrain-major_quality-590-022 | major_quality | 1 | 0.750 | updated |  |
| five-constrain-major_quality-590-023 | major_quality | 1 | 0.750 | updated |  |
| five-constrain-major_quality-620-024 | major_quality | 1 | 0.750 | updated |  |
| five-constrain-major_quality-680-025 | major_quality | 1 | 0.750 | updated |  |
| five-constrain-employment_outcome-520-026 | employment_outcome | 1 | 0.750 | updated |  |
| five-constrain-employment_outcome-550-027 | employment_outcome | 1 | 0.750 | updated |  |
| five-constrain-employment_outcome-650-030 | employment_outcome | 1 | 1.000 | single_turn_no_update_opportunity | BOI single_turn_no_update_opportunity; EUDR single_turn_no_update_opportunity |
| five-constrain-employment_outcome-600-028 | employment_outcome | 1 | 0.750 | updated |  |
| five-constrain-employment_outcome-620-029 | employment_outcome | 1 | 0.750 | updated |  |
| six-constrain-tuition_value-550-017 | tuition_value | 1 | 0.667 | updated |  |
| six-constrain-major_tier-600-009 | major_tier | 1 | 0.667 | updated |  |
| six-constrain-employment_outcome-620-029 | employment_outcome | 1 | 0.667 | updated |  |
| six-constrain-major_quality-680-025 | major_quality | 1 | 0.667 | updated |  |
| six-constrain-major_quality-600-021 | major_quality | 1 | 0.750 | updated |  |
| six-constrain-geo_tier-520-001 | geo_tier | 1 | 0.667 | updated |  |
| six-constrain-risk_tier-600-013 | risk_tier | 1 | 0.667 | updated |  |
| six-constrain-employment_outcome-650-030 | employment_outcome | 1 | 1.000 | single_turn_no_update_opportunity | BOI single_turn_no_update_opportunity; EUDR single_turn_no_update_opportunity |
| six-constrain-major_quality-590-022 | major_quality | 1 | 0.667 | updated |  |
| six-constrain-employment_outcome-520-026 | employment_outcome | 1 | 0.667 | updated |  |
| six-constrain-major_tier-650-010 | major_tier | 1 | 0.667 | updated |  |
| six-constrain-tuition_value-600-018 | tuition_value | 1 | 0.667 | updated |  |
| six-constrain-major_tier-560-006 | major_tier | 1 | 0.667 | updated |  |
| six-constrain-major_tier-570-007 | major_tier | 1 | 0.750 | updated |  |
| six-constrain-tuition_value-610-019 | tuition_value | 1 | 0.667 | updated |  |
| six-constrain-employment_outcome-550-027 | employment_outcome | 1 | 0.750 | updated |  |
| six-constrain-major_quality-590-023 | major_quality | 1 | 0.750 | updated |  |
| six-constrain-major_tier-590-008 | major_tier | 1 | 0.667 | updated |  |
| six-constrain-geo_tier-630-004 | geo_tier | 1 | 0.750 | updated |  |
| six-constrain-tuition_value-520-016 | tuition_value | 1 | 0.750 | updated |  |
| six-constrain-risk_tier-600-012 | risk_tier | 1 | 0.750 | updated |  |
| six-constrain-tuition_value-550-020 | tuition_value | 1 | 0.750 | updated |  |
| six-constrain-employment_outcome-600-028 | employment_outcome | 1 | 0.750 | frozen_state_no_observed_update | BOI frozen_state_no_observed_update; EUDR frozen_state_no_observed_update |
| six-constrain-major_quality-620-024 | major_quality | 1 | 0.750 | frozen_state_no_observed_update | BOI frozen_state_no_observed_update; EUDR frozen_state_no_observed_update |
