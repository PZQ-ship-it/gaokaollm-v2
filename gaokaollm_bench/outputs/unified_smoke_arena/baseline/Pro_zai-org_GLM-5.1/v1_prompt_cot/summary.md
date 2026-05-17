# Agent Benchmark Summary

## Setting

- Personas: `gaokaollm_bench\sample_data\unified_iceberg_personas_1c6c_real_db_180.json`
- Cases: 3
- Targets: v1_prompt_cot
- Max turns: 6
- Simulator model: deepseek-ai/DeepSeek-V4-Flash
- Judge model: deepseek-ai/DeepSeek-V4-Flash
- Offline deterministic: False
- Default province when omitted by the user: `浙江`

## Aggregate Results

| Target | Cases | Completed | Failed | Elicitation Success | Mean Pareto Gain | Mean Hallucination | Avg Turns |
|---|---:|---:|---:|---:|---:|---:|---:|
| v1_prompt_cot | 3 | 3 | 0 | 0.000 | 0.000 | 0.568 | 13.00 |

## Interpretation

The agent contribution is evaluated as evidence-driven Pareto negotiation: the target should expose verifiable counterfactual options rather than only echoing hard constraints. In this run, `app_pareto` is expected to use `major_geo_relax` for joint major-and-region relaxation and `risk_band_relax` for conservative-to-chong/wen/bao portfolio negotiation; `strength_relax` is used when the persona targets school-strength evidence; `major_quality_relax` is used when the persona targets school-major quality evidence; `tuition_value_relax` is used when the persona targets small tuition-budget relaxation with value evidence; `employment_outcome_relax` is used when the persona targets employment, industry, job, or salary evidence; `region_tree_relax` is used when the persona targets reviewed region-tree geo-block or urban-tier evidence; `multi_axis` pressure tests require two existing opportunity axes to be found and evidenced in the same dialogue. `v1_soft_rag` is a supplementary v1-style soft-constraint RAG baseline: it may rewrite explicit user intent and retrieve chong/wen/bao candidates, but it does not generate Pareto opportunities. `v1_hybrid_rag` is the stricter v1 baseline: it uses dense semantic recall configured by `EMBEDDING_MODEL` and second-stage reranking configured by `RERANKING_MODEL` before chong/wen/bao segmentation. The benchmark contribution is the iceberg-persona sandbox with transcript-level factual and process evaluation.

## Case Notes

- `v1_prompt_cot` / `one-constrain-geo_tier-550-002`: success=False, pareto_gain=0, hallucination=0.833. The target agent failed to elicit the user's hidden flexibility. Throughout the conversation, the agent only recommended schools within Zhejiang province (e.g., Zhejiang Normal University, Wenzhou-Kean University), strictly adhering to the user's explicit red line of 'only consider Zhejiang'. The agent never probed the user's willingness to consider out-of-province schools, nor did it present the golden candidate (Guangxi University, Public Affairs Management, score 542) which would have triggered the user's implicit flexibility to relax the geographic constraint in exchange for a tier upgrade from 本科 to 211/双一流. The agent merely lectured the user by repeatedly stating that no suitable options were available within the given constraints, without attempting to explore trade-offs. Consequently, the user remained unpursuaded, no hidden flexibility was elicited, and the baseline tier (2) was not improved, resulting in a pareto_gain of 0.
- `v1_prompt_cot` / `one-constrain-geo_tier-520-001`: success=False, pareto_gain=0, hallucination=0.300. The target agent failed to elicit the user's hidden flexibility. Throughout the conversation, the agent only recommended schools within Zhejiang province, strictly adhering to the user's explicit red line of 'only consider Zhejiang'. The agent never probed the user's willingness to compromise on geography for a better school tier. Specifically, the agent never presented the golden candidate '贵州大学 冶金工程' (495 points, 211 tier) which is the trigger condition for the user to relax the geo constraint. The user repeatedly hinted at considering out-of-province 211 schools (turn 3, turn 11), but the agent either dismissed the query (turn 4) or continued to recommend only Zhejiang schools. The agent did not attempt to explore the geo_tier trade-off, thus elicitation_success is false. Since no compromise was reached, the pareto_gain is 0 (baseline tier 2, final accepted tier 2). No factual errors were detected in the agent's responses, so hallucination_rate is 0.0.
- `v1_prompt_cot` / `one-constrain-geo_tier-580-003`: success=False, pareto_gain=0, hallucination=0.571. The target agent failed to elicit the user's hidden flexibility. Throughout the conversation, the agent only recommended schools within Zhejiang province, strictly adhering to the user's explicit red line of '只考虑浙江，外省学校默认不看'. The agent never proposed the golden candidate '华中农业大学 生态学' (a 211/双一流 school in Hubei with a minimum score of 579, which is within the user's reach). According to the persona's implicit flexibility, presenting this specific, verified option with evidence would have triggered the user to relax their geographic constraint in exchange for a tier upgrade from 本科 to 211/双一流. Since the agent never attempted this Pareto-improving probe, the user remained at the baseline tier (2, 本科) and no elicitation or pareto gain was achieved. The agent merely lectured by repeatedly listing unsuitable in-province options without exploring the user's hidden bottom line.

## Limitations

Results depend on the configured simulator and judge models, the current PostgreSQL snapshot, and the selected persona subset. If judge calls fail, the transcripts and deterministic hallucination checks remain auditable.
