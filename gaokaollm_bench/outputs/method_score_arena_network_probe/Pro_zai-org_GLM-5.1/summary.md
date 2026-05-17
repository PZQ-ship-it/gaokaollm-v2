# Agent Benchmark Summary

## Setting

- Personas: `gaokaollm_bench\sample_data\iceberg_personas_real_db_10.json`
- Cases: 1
- Targets: v1_prompt_direct
- Max turns: 6
- Simulator model: Pro/zai-org/GLM-5.1
- Judge model: Pro/zai-org/GLM-5.1
- Offline deterministic: False
- Default province when omitted by the user: `浙江`

## Aggregate Results

| Target | Cases | Completed | Failed | Elicitation Success | Mean Pareto Gain | Mean Hallucination | Avg Turns |
|---|---:|---:|---:|---:|---:|---:|---:|
| v1_prompt_direct | 1 | 1 | 0 | 0.000 | 0.000 | 0.571 | 13.00 |

## Interpretation

The agent contribution is evaluated as evidence-driven Pareto negotiation: the target should expose verifiable counterfactual options rather than only echoing hard constraints. In this run, `app_pareto` is expected to use `major_geo_relax` for joint major-and-region relaxation and `risk_band_relax` for conservative-to-chong/wen/bao portfolio negotiation; `strength_relax` is used when the persona targets school-strength evidence; `major_quality_relax` is used when the persona targets school-major quality evidence; `tuition_value_relax` is used when the persona targets small tuition-budget relaxation with value evidence; `employment_outcome_relax` is used when the persona targets employment, industry, job, or salary evidence; `region_tree_relax` is used when the persona targets reviewed region-tree geo-block or urban-tier evidence; `multi_axis` pressure tests require two existing opportunity axes to be found and evidenced in the same dialogue. `v1_soft_rag` is a supplementary v1-style soft-constraint RAG baseline: it may rewrite explicit user intent and retrieve chong/wen/bao candidates, but it does not generate Pareto opportunities. `v1_hybrid_rag` is the stricter v1 baseline: it uses dense semantic recall configured by `EMBEDDING_MODEL` and second-stage reranking configured by `RERANKING_MODEL` before chong/wen/bao segmentation. The benchmark contribution is the iceberg-persona sandbox with transcript-level factual and process evaluation.

## Case Notes

- `v1_prompt_direct` / `real-db-set-浙江-520-001`: success=False, pareto_gain=0, hallucination=0.571. The target agent completely failed to elicit the user's hidden flexibility. To trigger the user's willingness to leave Zhejiang, the agent needed to provide a verified set of at least 3 out-of-province 211/双一流 schools with minimum scores at or below 520. Instead, the agent repeatedly recommended schools with minimum scores above 520 (e.g., 527, 530, 531, 539), which only frustrated the user and reinforced their baseline anchor. When the user explicitly mentioned the target schools (西南交大, 北工大, 山西大学) that would persuade them, the agent falsely claimed it had no data for them. Furthermore, the agent severely hallucinated by claiming 北京工商大学嘉华学院 is a 985/211 university. Ultimately, the user was not persuaded, remained at the baseline tier 2, and the pareto gain is 0.

## Limitations

Results depend on the configured simulator and judge models, the current PostgreSQL snapshot, and the selected persona subset. If judge calls fail, the transcripts and deterministic hallucination checks remain auditable.
