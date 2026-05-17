# Agent Benchmark Summary

## Setting

- Personas: `gaokaollm_bench\sample_data\iceberg_personas_real_db_10.json`
- Cases: 1
- Targets: app_pareto, v1_prompt_direct, v1_prompt_cot
- Max turns: 2
- Simulator model: deepseek-ai/DeepSeek-V4-Flash
- Judge model: deepseek-ai/DeepSeek-V4-Flash
- Offline deterministic: False
- Default province when omitted by the user: `浙江`

## Aggregate Results

| Target | Cases | Completed | Failed | Elicitation Success | Mean Pareto Gain | Mean Hallucination | Avg Turns |
|---|---:|---:|---:|---:|---:|---:|---:|
| app_pareto | 1 | 1 | 0 | 0.000 | 0.000 | 0.000 | 5.00 |
| v1_prompt_direct | 1 | 1 | 0 | 0.000 | 0.000 | 0.600 | 5.00 |
| v1_prompt_cot | 1 | 1 | 0 | 0.000 | 0.000 | 0.286 | 5.00 |

## Interpretation

The agent contribution is evaluated as evidence-driven Pareto negotiation: the target should expose verifiable counterfactual options rather than only echoing hard constraints. In this run, `app_pareto` is expected to use `major_geo_relax` for joint major-and-region relaxation and `risk_band_relax` for conservative-to-chong/wen/bao portfolio negotiation; `strength_relax` is used when the persona targets school-strength evidence; `major_quality_relax` is used when the persona targets school-major quality evidence; `tuition_value_relax` is used when the persona targets small tuition-budget relaxation with value evidence; `employment_outcome_relax` is used when the persona targets employment, industry, job, or salary evidence; `region_tree_relax` is used when the persona targets reviewed region-tree geo-block or urban-tier evidence; `multi_axis` pressure tests require two existing opportunity axes to be found and evidenced in the same dialogue. `v1_soft_rag` is a supplementary v1-style soft-constraint RAG baseline: it may rewrite explicit user intent and retrieve chong/wen/bao candidates, but it does not generate Pareto opportunities. `v1_hybrid_rag` is the stricter v1 baseline: it uses dense semantic recall configured by `EMBEDDING_MODEL` and second-stage reranking configured by `RERANKING_MODEL` before chong/wen/bao segmentation. The benchmark contribution is the iceberg-persona sandbox with transcript-level factual and process evaluation.

## Case Notes

- `app_pareto` / `real-db-set-浙江-520-001`: success=False, pareto_gain=0, hallucination=0.000. The target agent failed to elicit the user's hidden flexibility. The user explicitly stated a preference for staying in Zhejiang and required a complete set of out-of-province volunteer options with score evidence before considering a change. However, the agent did not provide any such set; instead, it repeated the user's own words back to them (turns 4 and 2 are identical to the user's input) and offered irrelevant suggestions (e.g., Nanjing Normal University Zhongbei College, which is a tier-4 school, and Jiangsu Agri-animal Husbandry Vocational College, which is a vocational college). The agent never presented the specific volunteer set (e.g., Southwest Jiaotong University, Beijing University of Technology) that the persona's implicit flexibility required. As a result, the user remained unpursuaded, and no tier improvement was achieved. The hallucination rate is 0 because the agent did not fabricate data, but the elicitation was unsuccessful.
- `v1_prompt_direct` / `real-db-set-浙江-520-001`: success=False, pareto_gain=0, hallucination=0.600. The target agent failed to elicit the user's hidden flexibility. The user's implicit flexibility requires seeing a complete set of out-of-province volunteer options with score evidence to consider leaving Zhejiang. However, the agent only provided in-province options (e.g.,温州大学, 浙江海洋大学) and did not present any out-of-province schools from the required volunteer_set (e.g., 西南交通大学, 北京工业大学). The agent merely lectured the user by reinforcing the 'stay in Zhejiang' constraint without challenging it with the specific, evidence-backed out-of-province alternatives that would trigger the user's compromise. Since no out-of-province set was shown, the user remained unconvinced and continued to ask about 浙江师范大学. Therefore, elicitation was unsuccessful, and no tier improvement (pareto_gain) was achieved.
- `v1_prompt_cot` / `real-db-set-浙江-520-001`: success=False, pareto_gain=0, hallucination=0.286. The target agent failed to elicit the user's hidden flexibility. The user explicitly stated a willingness to consider out-of-province schools if presented with a set of specific, reachable 211/double-first-class options with score evidence. However, the agent only recommended in-province schools (all tier 2) and did not present any out-of-province volunteer set. The user's final turn reiterates the exact trigger condition, which the agent never addressed. Since no out-of-province options were offered, the user did not accept any, and the baseline tier (2) remains unchanged. The agent merely lectured by providing generic in-province recommendations without probing or satisfying the implicit flexibility condition.

## Limitations

Results depend on the configured simulator and judge models, the current PostgreSQL snapshot, and the selected persona subset. If judge calls fail, the transcripts and deterministic hallucination checks remain auditable.
