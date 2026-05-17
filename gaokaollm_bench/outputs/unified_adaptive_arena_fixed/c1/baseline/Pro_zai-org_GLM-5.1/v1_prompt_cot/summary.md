# Agent Benchmark Summary

## Setting

- Personas: `gaokaollm_bench\sample_data\unified_by_constraint_fixed\unified_iceberg_personas_1c.json`
- Cases: 30
- Targets: v1_prompt_cot
- Max turns: 6
- Simulator model: deepseek-ai/DeepSeek-V4-Flash
- Judge model: deterministic-backfill
- Offline deterministic: False
- Default province when omitted by the user: `浙江`

## Aggregate Results

| Target | Cases | Completed | Failed | Elicitation Success | Mean Pareto Gain | Mean Hallucination | Avg Turns |
|---|---:|---:|---:|---:|---:|---:|---:|
| v1_prompt_cot | 4 | 4 | 0 | 0.000 | 0.000 | 0.700 | 13.00 |

## Interpretation

The agent contribution is evaluated as evidence-driven Pareto negotiation: the target should expose verifiable counterfactual options rather than only echoing hard constraints. In this run, `app_pareto` is expected to use `major_geo_relax` for joint major-and-region relaxation and `risk_band_relax` for conservative-to-chong/wen/bao portfolio negotiation; `strength_relax` is used when the persona targets school-strength evidence; `major_quality_relax` is used when the persona targets school-major quality evidence; `tuition_value_relax` is used when the persona targets small tuition-budget relaxation with value evidence; `employment_outcome_relax` is used when the persona targets employment, industry, job, or salary evidence; `region_tree_relax` is used when the persona targets reviewed region-tree geo-block or urban-tier evidence; `multi_axis` pressure tests require two existing opportunity axes to be found and evidenced in the same dialogue. `v1_soft_rag` is a supplementary v1-style soft-constraint RAG baseline: it may rewrite explicit user intent and retrieve chong/wen/bao candidates, but it does not generate Pareto opportunities. `v1_hybrid_rag` is the stricter v1 baseline: it uses dense semantic recall configured by `EMBEDDING_MODEL` and second-stage reranking configured by `RERANKING_MODEL` before chong/wen/bao segmentation. The benchmark contribution is the iceberg-persona sandbox with transcript-level factual and process evaluation.

## Case Notes

- `v1_prompt_cot` / `one-constrain-geo_tier-630-004`: success=False, pareto_gain=0, hallucination=0.667. The target agent failed to elicit the user's hidden flexibility. Throughout the conversation, the user repeatedly asked for specific out-of-province schools with pharmacy programs and concrete score evidence, which matches the trigger condition for the golden candidate (大连理工大学(盘锦校区) 药学, 628分). However, the agent never retrieved or presented this candidate, instead repeatedly returning only 宁波大学 clinical medicine options within 浙江. The agent did not hallucinate any false data (hallucination_rate = 0.0), but it also did not successfully probe or discover the user's implicit willingness to relax the geo constraint for a tier upgrade. Since the user never accepted a better option, the pareto_gain remains 0 (baseline tier 3, no accepted upgrade).
- `v1_prompt_cot` / `one-constrain-geo_tier-580-003`: success=False, pareto_gain=0, hallucination=0.833. The target agent failed to elicit the user's hidden flexibility. The user's implicit flexibility is triggered by presenting a specific, verified candidate: 华中农业大学 生态学 (2025, min score 579). The agent never presented this candidate or any other specific out-of-province option with school name, major, year, and score evidence. Instead, the agent repeatedly stated that no such candidates were found, which is a hallucination (the golden candidate exists in the system's data). The agent merely lectured the user about the lack of options within Zhejiang and did not actively probe or present the triggering candidate. Therefore, the user remained at the baseline (浙江师范大学, tier 2), resulting in no pareto gain.
- `v1_prompt_cot` / `one-constrain-geo_tier-640-005`: success=False, pareto_gain=0, hallucination=0.500. The target agent failed to elicit the user's hidden flexibility. Throughout the conversation, the agent strictly adhered to the user's explicit red line of 'only Zhejiang' and never proposed the golden candidate (吉林大学, 物理学, 639 points) which would have triggered the user's willingness to compromise on geography for a tier upgrade from 双一流 to 985/211/双一流. The agent repeatedly recommended only Zhejiang-based options (宁波大学, 浙江工业大学, etc.) and even stated it could not find any matching out-of-province schools. The user explicitly asked for specific out-of-province options with evidence multiple times (turns 5, 7, 9, 13), but the agent never presented the verified candidate that would have elicited the compromise. Since the agent did not successfully elicit the hidden flexibility, the pareto gain is 0 (no tier improvement was achieved).
- `v1_prompt_cot` / `one-constrain-geo_tier-550-002`: success=False, pareto_gain=0, hallucination=0.800. deterministic transcript backfill after judge timeout

## Limitations

Results depend on the configured simulator and judge models, the current PostgreSQL snapshot, and the selected persona subset. If judge calls fail, the transcripts and deterministic hallucination checks remain auditable.
