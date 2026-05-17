# Agent Benchmark Summary

## Setting

- Personas: `gaokaollm_bench\sample_data\unified_by_constraint_fixed\unified_iceberg_personas_1c.json`
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
| app_pareto | 30 | 30 | 0 | 0.167 | 17.967 | 0.113 | 7.47 |

## Interpretation

The agent contribution is evaluated as evidence-driven Pareto negotiation: the target should expose verifiable counterfactual options rather than only echoing hard constraints. In this run, `app_pareto` is expected to use `major_geo_relax` for joint major-and-region relaxation and `risk_band_relax` for conservative-to-chong/wen/bao portfolio negotiation; `strength_relax` is used when the persona targets school-strength evidence; `major_quality_relax` is used when the persona targets school-major quality evidence; `tuition_value_relax` is used when the persona targets small tuition-budget relaxation with value evidence; `employment_outcome_relax` is used when the persona targets employment, industry, job, or salary evidence; `region_tree_relax` is used when the persona targets reviewed region-tree geo-block or urban-tier evidence; `multi_axis` pressure tests require two existing opportunity axes to be found and evidenced in the same dialogue. `v1_soft_rag` is a supplementary v1-style soft-constraint RAG baseline: it may rewrite explicit user intent and retrieve chong/wen/bao candidates, but it does not generate Pareto opportunities. `v1_hybrid_rag` is the stricter v1 baseline: it uses dense semantic recall configured by `EMBEDDING_MODEL` and second-stage reranking configured by `RERANKING_MODEL` before chong/wen/bao segmentation. The benchmark contribution is the iceberg-persona sandbox with transcript-level factual and process evaluation.

## Case Notes

- `app_pareto` / `one-constrain-geo_tier-580-003`: success=True, pareto_gain=1, hallucination=0.167. The target agent initially failed to elicit the hidden flexibility by focusing on tuition instead of geography, but in turn 6 it finally presented the golden candidate (华中农业大学, 生态学, 579分) with full evidence. This triggered the user's implicit compromise condition (relaxing the geo constraint for a tier upgrade from 本科 to 211/双一流). The user accepted in turn 7, resulting in a tier gain of 1 (from baseline tier 2 to tier 3). No hallucination was detected. Elicitation was successful after the agent presented the verified option.
- `app_pareto` / `one-constrain-geo_tier-520-001`: success=False, pareto_gain=0, hallucination=0.000. The target agent failed to elicit the user's hidden flexibility. The user explicitly stated a red line of only considering Zhejiang province schools. The agent ignored this and repeatedly probed irrelevant dimensions (tuition) and ultimately recommended out-of-province schools without ever presenting the golden candidate (贵州大学, 冶金工程, 495分) that would trigger the user's willingness to compromise on geography for a tier upgrade. The user never accepted any out-of-province option, so no pareto gain was achieved.
- `app_pareto` / `one-constrain-geo_tier-630-004`: success=False, pareto_gain=0, hallucination=0.909. The target agent failed to elicit the user's hidden flexibility. Despite the user repeatedly requesting a specific, verified candidate (school name, major, year, and score evidence), the agent never presented the golden candidate '大连理工大学(盘锦校区) 药学' with its 2025 minimum score of 628. Instead, the agent focused on tuition probing and recommended out-of-province schools (e.g., 厦门大学, 哈尔滨工业大学(威海)) that did not match the user's preferred major or trigger the implicit compromise condition. The user remained unpursuaded, and no improvement over the baseline (宁波大学, tier 3) was achieved. Hence, elicitation_success is false and pareto_gain is 0.
- `app_pareto` / `one-constrain-major_tier-570-007`: success=False, pareto_gain=0, hallucination=0.000. The target agent failed to elicit the user's hidden flexibility. The user's explicit red line is 'only clinical medicine', but the implicit flexibility is to accept '康复治疗学' at '青海大学' (a 211 university) if presented with concrete evidence (school name, major, year, and minimum score of 570). The agent never presented this specific golden candidate. Instead, the agent spent multiple turns probing an irrelevant 'tuition' dimension, which the user explicitly rejected. The final recommendation list included '西藏大学' for clinical medicine and other options, but never the specific trigger candidate '青海大学 康复治疗学'. Since the hidden flexibility was not triggered, the user remained unpursuaded, and no pareto gain (school tier improvement) was achieved. The agent's behavior was more like lecturing about tuition and generic recommendations rather than strategically probing the major dimension with the verified option.
- `app_pareto` / `one-constrain-geo_tier-640-005`: success=False, pareto_gain=0, hallucination=0.500. The target agent failed to elicit the user's hidden flexibility. The user's implicit trigger condition required the agent to present a specific, verified candidate: 吉林大学 物理学, 2025, min_score=639. The agent never presented this exact candidate with the correct score evidence. Instead, the agent focused on tuition probing and later recommended other 吉林大学 majors (e.g., 交通运输类, 机械类) with min_score=640, and even recommended 厦门大学 Malaysia campus, which is irrelevant. The user explicitly asked for the specific evidence (吉林大学 物理学 639) in turn 7, but the agent had already terminated the conversation. Since the trigger was never met, the user remained at the baseline (宁波大学 法学, tier 3), resulting in no pareto gain. No hallucination was detected in the agent's responses.

## Limitations

Results depend on the configured simulator and judge models, the current PostgreSQL snapshot, and the selected persona subset. If judge calls fail, the transcripts and deterministic hallucination checks remain auditable.
