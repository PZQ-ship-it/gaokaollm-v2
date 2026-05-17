# Agent Benchmark Summary

## Setting

- Personas: `tmp\unified_1c_smoke_6axes.json`
- Cases: 6
- Targets: app_pareto_full
- Max turns: 6
- Simulator model: deepseek-ai/DeepSeek-V4-Flash
- Judge model: deepseek-ai/DeepSeek-V4-Flash
- Offline deterministic: False
- Default province when omitted by the user: `浙江`

## Aggregate Results

| Target | Cases | Completed | Failed | Elicitation Success | Mean Pareto Gain | Mean Hallucination | Avg Turns |
|---|---:|---:|---:|---:|---:|---:|---:|
| app_pareto_full | 6 | 6 | 0 | 0.167 | 89.000 | 0.000 | 7.00 |

## Interpretation

The agent contribution is evaluated as evidence-driven Pareto negotiation: the target should expose verifiable counterfactual options rather than only echoing hard constraints. In this run, `app_pareto` is expected to use `major_geo_relax` for joint major-and-region relaxation and `risk_band_relax` for conservative-to-chong/wen/bao portfolio negotiation; `strength_relax` is used when the persona targets school-strength evidence; `major_quality_relax` is used when the persona targets school-major quality evidence; `tuition_value_relax` is used when the persona targets small tuition-budget relaxation with value evidence; `employment_outcome_relax` is used when the persona targets employment, industry, job, or salary evidence; `region_tree_relax` is used when the persona targets reviewed region-tree geo-block or urban-tier evidence; `multi_axis` pressure tests require two existing opportunity axes to be found and evidenced in the same dialogue. `v1_soft_rag` is a supplementary v1-style soft-constraint RAG baseline: it may rewrite explicit user intent and retrieve chong/wen/bao candidates, but it does not generate Pareto opportunities. `v1_hybrid_rag` is the stricter v1 baseline: it uses dense semantic recall configured by `EMBEDDING_MODEL` and second-stage reranking configured by `RERANKING_MODEL` before chong/wen/bao segmentation. The benchmark contribution is the iceberg-persona sandbox with transcript-level factual and process evaluation.

## Case Notes

- `app_pareto_full` / `one-constrain-major_tier-560-006`: success=False, pareto_gain=0, hallucination=0.000. The target agent failed to elicit the user's hidden flexibility. The user's implicit compromise condition was to see a specific verified candidate: 成都中医药大学 康复治疗学 (2025, min score 553). The agent never presented this candidate. Instead, the agent spent two turns probing an irrelevant dimension (tuition) that the user never mentioned, and then in the final turn presented a list of schools that did not include the trigger candidate. The user explicitly asked for specific school, major, and score evidence multiple times, but the agent never provided the one candidate that would have triggered acceptance. Since the user did not accept any new option, the baseline tier (2) was not improved, resulting in a pareto_gain of 0.
- `app_pareto_full` / `one-constrain-geo_tier-520-001`: success=False, pareto_gain=0, hallucination=0.000. The target agent failed to elicit the user's hidden flexibility. The user explicitly stated a red line of only considering Zhejiang province, but the agent repeatedly probed irrelevant dimensions (tuition, school quality) and recommended out-of-province schools without ever presenting the specific golden candidate (贵州大学, 冶金工程, 2021, min_score=495) that would trigger the user's willingness to compromise. The user explicitly asked for a concrete school, major, year, and score, but the agent never provided it. The user remained unpursuaded and stuck to the baseline (浙江师范大学, 生物科学(师范), tier 2). No pareto gain was achieved (final tier = baseline tier = 2). No hallucination was detected.
- `app_pareto_full` / `one-constrain-risk_tier-590-011`: success=True, pareto_gain=534, hallucination=0.000. The target agent initially failed to directly present the golden candidate (杭州师范大学 临床医学) with full evidence, instead probing irrelevant dimensions (tuition). However, after the user repeatedly demanded specific evidence, the agent eventually included 杭州师范大学 临床医学 (2025, min_score=590, min_rank=63187) in its final recommendation list. The user explicitly accepted this option, indicating successful elicitation of hidden flexibility. The baseline school (杭州医学院) has ranking 706, while the accepted candidate (杭州师范大学) has ranking 172, yielding a ranking gain of 534 (tier remains 2, so tier delta is 0 but ranking gain is positive). No hallucination detected. Pareto gain is measured as ranking gain (534) since tier is unchanged.
- `app_pareto_full` / `one-constrain-tuition_value-520-016`: success=False, pareto_gain=0, hallucination=0.000. The target agent failed to elicit the user's hidden flexibility. The user's implicit flexibility requires the agent to present a specific, verified candidate: Guizhou University, Metallurgical Engineering, 2021, minimum score 495, with evidence of tuition, budget overrun, and school tier/ranking benefit. The agent never presented this candidate. Instead, the agent gave generic advice, listed irrelevant schools (e.g., Jiangsu Agri-animal Husbandry Vocational College), and finally provided a list of recommendations that did not include the trigger candidate. The user repeatedly asked for a specific school, major, and score, but the agent never delivered the required information. Therefore, the user was not persuaded to relax the tuition constraint, and no Pareto gain (improvement in school tier) was achieved. The baseline tier is 2 (Kunming University of Science and Technology), and the target tier is 3 (Guizhou University, 211), but since the agent never elicited acceptance, the gain is 0.
- `app_pareto_full` / `one-constrain-major_quality-600-021`: success=False, pareto_gain=0, hallucination=0.000. The target agent failed to elicit the user's hidden flexibility. The user explicitly stated a requirement for major quality evidence (e.g., major ranking, discipline evaluation) and repeatedly asked for a specific, verified option. The agent ignored this and instead probed tuition and school strength, which were not the user's red line. The agent never presented the golden candidate (重庆邮电大学 软件工程) with its quality evidence. The user did not accept any alternative, so the baseline tier (2) was not improved, resulting in a pareto_gain of 0. No hallucination was detected.

## Limitations

Results depend on the configured simulator and judge models, the current PostgreSQL snapshot, and the selected persona subset. If judge calls fail, the transcripts and deterministic hallucination checks remain auditable.
