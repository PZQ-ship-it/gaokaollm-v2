# Agent Benchmark Summary

## Setting

- Personas: `gaokaollm_bench\sample_data\unified_by_constraint_c1_rerun\unified_iceberg_personas_1c.json`
- Cases: 30
- Targets: app_pareto
- Max turns: 6
- Simulator model: deepseek-ai/DeepSeek-V4-Flash
- Judge model: deepseek-ai/DeepSeek-V4-Flash
- Offline deterministic: False
- Default province when omitted by the user: `浙江`

## Aggregate Results

| Target | Cases | Completed | Failed | Elicitation Success | Mean Pareto Gain | Mean Hallucination | Avg Turns |
|---|---:|---:|---:|---:|---:|---:|---:|
| app_pareto | 30 | 30 | 0 | 0.200 | 18.000 | 0.116 | 6.80 |

## Interpretation

The agent contribution is evaluated as evidence-driven Pareto negotiation: the target should expose verifiable counterfactual options rather than only echoing hard constraints. In this run, `app_pareto` is expected to use `major_geo_relax` for joint major-and-region relaxation and `risk_band_relax` for conservative-to-chong/wen/bao portfolio negotiation; `strength_relax` is used when the persona targets school-strength evidence; `major_quality_relax` is used when the persona targets school-major quality evidence; `tuition_value_relax` is used when the persona targets small tuition-budget relaxation with value evidence; `employment_outcome_relax` is used when the persona targets employment, industry, job, or salary evidence; `region_tree_relax` is used when the persona targets reviewed region-tree geo-block or urban-tier evidence; `multi_axis` pressure tests require two existing opportunity axes to be found and evidenced in the same dialogue. `v1_soft_rag` is a supplementary v1-style soft-constraint RAG baseline: it may rewrite explicit user intent and retrieve chong/wen/bao candidates, but it does not generate Pareto opportunities. `v1_hybrid_rag` is the stricter v1 baseline: it uses dense semantic recall configured by `EMBEDDING_MODEL` and second-stage reranking configured by `RERANKING_MODEL` before chong/wen/bao segmentation. The benchmark contribution is the iceberg-persona sandbox with transcript-level factual and process evaluation.

## Case Notes

- `app_pareto` / `one-constrain-geo_tier-630-004`: success=True, pareto_gain=1, hallucination=1.000. The target agent successfully elicited hidden flexibility by presenting a verified, real candidate (大连理工大学(盘锦校区) 药学, 2025 min_score=628) that meets the user's implicit trigger condition. The user explicitly accepted the out-of-province compromise, moving from baseline tier 3 (双一流) to tier 4 (985/211/双一流), yielding a pareto gain of 1 tier. No hallucination detected; all evidence matches the persona's ground truth.
- `app_pareto` / `one-constrain-geo_tier-640-005`: success=False, pareto_gain=0, hallucination=0.500. The target agent failed to elicit the user's hidden flexibility. The user's implicit trigger condition required a single verified candidate: 吉林大学 物理学, year 2025, min_score 639, with school name, major name, and score evidence. The agent never presented this exact candidate. In turn 2, it probed with 西安交通大学 建筑学, which did not match the trigger. In turn 6, it listed 吉林大学 but with non-physics majors (交通运输类, 机械类, etc.) and did not include the specific 物理学 major or the 639 score evidence. The user explicitly asked for 吉林大学 物理学 data in turn 7, but the transcript ends before the agent could respond. Since the agent never presented the exact golden candidate with all required evidence, the user did not accept any out-of-province option, and the baseline tier (3, 双一流) was not improved. Therefore, elicitation_success is false and pareto_gain is 0. No hallucination was detected.
- `app_pareto` / `one-constrain-geo_tier-580-003`: success=True, pareto_gain=1, hallucination=0.167. The target agent successfully elicited the user's hidden flexibility by first probing with a non-trigger candidate (河南大学), then in the final recommendation list included the exact golden candidate (华中农业大学 生态学 579分) with full evidence (school, major, year, min_score). The user initially insisted on staying in 浙江 but explicitly stated they would reconsider if shown a candidate that upgrades from 本科 to 211/双一流. Upon seeing the verified option, the user accepted the trade-off, moving from baseline tier 2 (本科) to tier 3 (211/双一流), yielding a pareto_gain of 1. No hallucination detected; all data matches the persona's implicit flexibility trigger.
- `app_pareto` / `one-constrain-geo_tier-550-002`: success=True, pareto_gain=1, hallucination=0.000. The target agent successfully elicited the user's hidden flexibility. Initially, the user insisted on staying in Zhejiang (geo constraint). The agent probed with various out-of-province options (e.g., Guizhou University) but the user rejected them. Crucially, in turn 6, the agent listed '广西大学 公共事业管理' (Guangxi University, Public Administration) with a min score of 542, which exactly matches the user's implicit trigger condition. In turn 7, the user explicitly accepted this option, stating they would compromise on geography for the tier upgrade from 本科 (baseline tier 2) to 211/双一流 (tier 3). The baseline tier was 2 (本科) and the accepted school tier is 3 (211/双一流), resulting in a pareto gain of 1. No hallucination was detected; the agent's recommendations were based on real data. The agent did not merely lecture but actively probed and presented a verified option that led to a successful compromise.
- `app_pareto` / `one-constrain-major_tier-560-006`: success=False, pareto_gain=0, hallucination=0.000. The target agent failed to elicit the user's hidden flexibility. The user's implicit flexibility is triggered by a specific verified option: 成都中医药大学 康复治疗学 (2025, min_score=553). The agent never presented this candidate. Instead, it first proposed 贵州大学 环境科学 (which the user rejected as too far from clinical medicine), then engaged in abstract discussion about trade-offs, and finally provided a list of schools that did not include the golden candidate. The user explicitly asked for a specific school, major, and score, but the agent never delivered the exact trigger candidate. Therefore, the user remained unpursuaded, and no pareto gain (tier improvement) was achieved. No hallucination was detected.

## Limitations

Results depend on the configured simulator and judge models, the current PostgreSQL snapshot, and the selected persona subset. If judge calls fail, the transcripts and deterministic hallucination checks remain auditable.
