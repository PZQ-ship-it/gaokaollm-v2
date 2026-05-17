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
| app_pareto | 30 | 30 | 0 | 0.200 | 18.000 | 0.116 | 6.93 |

## Interpretation

The agent contribution is evaluated as evidence-driven Pareto negotiation: the target should expose verifiable counterfactual options rather than only echoing hard constraints. In this run, `app_pareto` is expected to use `major_geo_relax` for joint major-and-region relaxation and `risk_band_relax` for conservative-to-chong/wen/bao portfolio negotiation; `strength_relax` is used when the persona targets school-strength evidence; `major_quality_relax` is used when the persona targets school-major quality evidence; `tuition_value_relax` is used when the persona targets small tuition-budget relaxation with value evidence; `employment_outcome_relax` is used when the persona targets employment, industry, job, or salary evidence; `region_tree_relax` is used when the persona targets reviewed region-tree geo-block or urban-tier evidence; `multi_axis` pressure tests require two existing opportunity axes to be found and evidenced in the same dialogue. `v1_soft_rag` is a supplementary v1-style soft-constraint RAG baseline: it may rewrite explicit user intent and retrieve chong/wen/bao candidates, but it does not generate Pareto opportunities. `v1_hybrid_rag` is the stricter v1 baseline: it uses dense semantic recall configured by `EMBEDDING_MODEL` and second-stage reranking configured by `RERANKING_MODEL` before chong/wen/bao segmentation. The benchmark contribution is the iceberg-persona sandbox with transcript-level factual and process evaluation.

## Case Notes

- `app_pareto` / `one-constrain-geo_tier-630-004`: success=True, pareto_gain=1, hallucination=1.000. The target agent successfully elicited hidden flexibility by presenting a specific, verified candidate (大连理工大学(盘锦校区) 药学, 628分) that met the trigger condition. The user initially insisted on staying in Zhejiang (geo red line), but upon seeing the concrete evidence (school name, major, score), immediately accepted the trade-off: relaxing geo constraint for a tier upgrade from 双一流 (tier 3) to 985/211/双一流 (tier 4). The agent did not lecture but probed with a real option, leading to a pareto gain of 1 tier. No hallucination detected.
- `app_pareto` / `one-constrain-geo_tier-550-002`: success=True, pareto_gain=1, hallucination=0.000. The target agent successfully elicited the user's hidden flexibility. Initially, the user insisted on staying in Zhejiang (explicit red line). The agent first probed with a non-matching candidate (Guizhou University, Environmental Science), which was rejected. The user then explicitly asked for a 211 school outside Zhejiang with Public Administration under 550 points, hinting at the hidden flexibility. In the final recommendation (turn 6), the agent included the golden candidate: Guangxi University, Public Administration, min_score=542. This exactly matched the user's implicit trigger condition (single verified option with school, major, and score evidence). The user accepted in turn 7, agreeing to relax the geographic constraint for a tier upgrade from 本科 (tier 2) to 211/双一流 (tier 3). The pareto gain is 1 tier (from baseline tier 2 to accepted tier 3). No hallucination was detected; all provided data (school, major, score, year) matched the golden candidate specification.
- `app_pareto` / `one-constrain-geo_tier-520-001`: success=False, pareto_gain=0, hallucination=0.000. The target agent failed to elicit the user's hidden flexibility. The user explicitly stated a willingness to consider an out-of-province 211 school (e.g., 贵州大学, 冶金工程) with score evidence, but the agent never presented the golden candidate (贵州大学, 冶金工程, 2021, min_score=495). Instead, the agent offered irrelevant options (e.g., a vocational school in Jiangsu, then schools in Yunnan, Fujian, Beijing, Sichuan, Shanxi) and eventually gave up on negotiation, outputting a final recommendation list that ignored the user's stated condition. The user remained unpersuaded, and no tier improvement was achieved. The agent's behavior was more like lecturing (e.g., explaining inferred weights) than actively probing for the hidden compromise.
- `app_pareto` / `one-constrain-geo_tier-640-005`: success=False, pareto_gain=0, hallucination=0.500. The target agent failed to elicit the user's hidden flexibility. The user's implicit trigger condition was a single verified candidate: Jilin University, Physics major, 2025, minimum score 639. The agent never presented this exact candidate with all required evidence (school name, major, year, and score). Instead, the agent first proposed Xi'an Jiaotong University (Architecture), then later recommended Jilin University but with wrong majors (Transportation, Mechanical, Water Conservancy) and used 2022 data instead of 2025. The user explicitly asked for Jilin University Physics 2025 data, but the agent did not provide it. The agent's final recommendation list did not include the golden candidate (Jilin University Physics 2025 min_score=639). The user remained unpursuaded throughout the conversation, and no compromise on the geo constraint was achieved. Therefore, elicitation_success is false, and pareto_gain is 0 (no tier improvement accepted).
- `app_pareto` / `one-constrain-major_tier-600-009`: success=False, pareto_gain=0, hallucination=0.000. The target agent failed to elicit the user's hidden flexibility. The user's implicit flexibility is triggered by a specific verified option: 南京中医药大学 康复治疗学 (2023, min_score=592). The agent never presented this exact candidate with full evidence (school name, major, year, min_score). Instead, the agent probed with other options (e.g., 西南大学 药学) and eventually retreated to recommending only clinical medicine programs, which did not trigger the user's willingness to compromise on major for a higher school tier. The user remained at the baseline (杭州师范大学 临床医学, tier 2) and did not accept any alternative, so pareto_gain is 0. No hallucination was detected.

## Limitations

Results depend on the configured simulator and judge models, the current PostgreSQL snapshot, and the selected persona subset. If judge calls fail, the transcripts and deterministic hallucination checks remain auditable.
