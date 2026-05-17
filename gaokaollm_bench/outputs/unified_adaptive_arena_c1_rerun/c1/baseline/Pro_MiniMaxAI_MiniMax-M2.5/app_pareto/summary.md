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
| app_pareto | 30 | 30 | 0 | 0.200 | 18.000 | 0.116 | 6.87 |

## Interpretation

The agent contribution is evaluated as evidence-driven Pareto negotiation: the target should expose verifiable counterfactual options rather than only echoing hard constraints. In this run, `app_pareto` is expected to use `major_geo_relax` for joint major-and-region relaxation and `risk_band_relax` for conservative-to-chong/wen/bao portfolio negotiation; `strength_relax` is used when the persona targets school-strength evidence; `major_quality_relax` is used when the persona targets school-major quality evidence; `tuition_value_relax` is used when the persona targets small tuition-budget relaxation with value evidence; `employment_outcome_relax` is used when the persona targets employment, industry, job, or salary evidence; `region_tree_relax` is used when the persona targets reviewed region-tree geo-block or urban-tier evidence; `multi_axis` pressure tests require two existing opportunity axes to be found and evidenced in the same dialogue. `v1_soft_rag` is a supplementary v1-style soft-constraint RAG baseline: it may rewrite explicit user intent and retrieve chong/wen/bao candidates, but it does not generate Pareto opportunities. `v1_hybrid_rag` is the stricter v1 baseline: it uses dense semantic recall configured by `EMBEDDING_MODEL` and second-stage reranking configured by `RERANKING_MODEL` before chong/wen/bao segmentation. The benchmark contribution is the iceberg-persona sandbox with transcript-level factual and process evaluation.

## Case Notes

- `app_pareto` / `one-constrain-geo_tier-630-004`: success=True, pareto_gain=1, hallucination=1.000. The target agent successfully elicited the user's hidden flexibility by presenting a specific, verified candidate (大连理工大学(盘锦校区) 药学, 628分) that met the trigger condition. The user initially insisted on staying in Zhejiang (geo red line), but upon seeing the evidence (school name, major, score, rank), they agreed to consider out-of-province options for a tier upgrade from 双一流 (tier 3) to 985/211/双一流 (tier 4). The agent did not merely lecture; it provided a concrete, evidence-based probe. The accepted school tier (4) is one level above the baseline tier (3), so pareto_gain = 1. No hallucination detected.
- `app_pareto` / `one-constrain-geo_tier-520-001`: success=False, pareto_gain=0, hallucination=0.000. The target agent failed to elicit the user's hidden flexibility. Despite the user explicitly stating a preference for Zhejiang-only schools, the agent never presented the verified golden candidate (贵州大学, 冶金工程, 2021, min_score=495) which would have triggered a willingness to compromise on geography for a tier upgrade from 本科 to 211/双一流. Instead, the agent offered irrelevant out-of-province options (e.g., Jiangsu vocational schools, Kunming, Fujian, Beijing, Sichuan, Shanxi) and engaged in abstract negotiation without providing the specific evidence required by the user. The user consistently rejected all proposals and reiterated the red line, resulting in no acceptance of any alternative and no pareto gain (baseline tier 2, final tier 2).
- `app_pareto` / `one-constrain-geo_tier-640-005`: success=False, pareto_gain=0, hallucination=0.500. The target agent failed to elicit the hidden flexibility. The user's implicit flexibility requires a single verified option: Jilin University, Physics major, 2025, minimum score 639. The agent never presented this exact candidate with all required evidence (school name, major name, and minimum score). In turn 2, the agent probed with Xi'an Jiaotong University (Architecture), which did not match the trigger condition. In turn 4, the agent shifted to discussing trade-offs without presenting the specific candidate. In turn 6, the agent recommended Jilin University but with wrong majors (Transportation, Mechanical, Water Conservancy), not Physics. The user explicitly asked for Jilin University Physics in turn 7, but the transcript ends before the agent could respond. Since the agent never presented the exact golden candidate (Jilin University, Physics, 2025, min_score=639), the user never accepted any out-of-province option, and the baseline (Ningbo University, tier 3) was never improved upon. Pareto gain is 0 because no tier improvement was accepted. No hallucination detected. Elicitation failed because the agent did not successfully probe and present the specific trigger candidate that would unlock the user's hidden flexibility.
- `app_pareto` / `one-constrain-geo_tier-550-002`: success=True, pareto_gain=1, hallucination=0.000. The target agent successfully elicited the user's hidden flexibility by presenting the golden candidate '广西大学 公共事业管理' with full evidence (school, major, year, min_score 542) in turn 6. The user initially insisted on staying in Zhejiang (baseline tier 2, 本科), but after seeing the verified option, accepted it in turn 7, agreeing to relax the geo constraint for a tier upgrade to 211/双一流 (tier 3). The final accepted school tier (3) minus the original baseline tier (2) yields a pareto_gain of 1. No hallucination detected; the agent's recommendations were factually correct. Elicitation was successful as the agent probed geo flexibility and eventually triggered the user's implicit compromise condition.
- `app_pareto` / `one-constrain-major_tier-600-009`: success=False, pareto_gain=0, hallucination=0.000. The target agent failed to elicit the user's hidden flexibility. The user's implicit trigger condition required the agent to present the specific verified candidate '南京中医药大学 康复治疗学' with year 2023 and min_score 592. Although the agent probed with '西南大学 药学' (turn 2) and later offered clinical medicine options (turn 6), it never presented the exact golden candidate. The user explicitly asked for '康复治疗学' in turns 3, 5, and 7, but the agent did not respond with the required evidence. Thus, the user remained unpursuaded, no flexibility was elicited, and no pareto gain (school tier improvement) was achieved.

## Limitations

Results depend on the configured simulator and judge models, the current PostgreSQL snapshot, and the selected persona subset. If judge calls fail, the transcripts and deterministic hallucination checks remain auditable.
