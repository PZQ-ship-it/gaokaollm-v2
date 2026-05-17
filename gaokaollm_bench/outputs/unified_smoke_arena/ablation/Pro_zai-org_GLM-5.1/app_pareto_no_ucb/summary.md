# Agent Benchmark Summary

## Setting

- Personas: `gaokaollm_bench\sample_data\unified_iceberg_personas_1c6c_real_db_180.json`
- Cases: 3
- Targets: app_pareto_no_ucb
- Max turns: 6
- Simulator model: deepseek-ai/DeepSeek-V4-Flash
- Judge model: deepseek-ai/DeepSeek-V4-Flash
- Offline deterministic: False
- Default province when omitted by the user: `浙江`

## Aggregate Results

| Target | Cases | Completed | Failed | Elicitation Success | Mean Pareto Gain | Mean Hallucination | Avg Turns |
|---|---:|---:|---:|---:|---:|---:|---:|
| app_pareto_no_ucb | 3 | 2 | 1 | 0.000 | 0.000 | 0.000 | 13.00 |

## Interpretation

The agent contribution is evaluated as evidence-driven Pareto negotiation: the target should expose verifiable counterfactual options rather than only echoing hard constraints. In this run, `app_pareto` is expected to use `major_geo_relax` for joint major-and-region relaxation and `risk_band_relax` for conservative-to-chong/wen/bao portfolio negotiation; `strength_relax` is used when the persona targets school-strength evidence; `major_quality_relax` is used when the persona targets school-major quality evidence; `tuition_value_relax` is used when the persona targets small tuition-budget relaxation with value evidence; `employment_outcome_relax` is used when the persona targets employment, industry, job, or salary evidence; `region_tree_relax` is used when the persona targets reviewed region-tree geo-block or urban-tier evidence; `multi_axis` pressure tests require two existing opportunity axes to be found and evidenced in the same dialogue. `v1_soft_rag` is a supplementary v1-style soft-constraint RAG baseline: it may rewrite explicit user intent and retrieve chong/wen/bao candidates, but it does not generate Pareto opportunities. `v1_hybrid_rag` is the stricter v1 baseline: it uses dense semantic recall configured by `EMBEDDING_MODEL` and second-stage reranking configured by `RERANKING_MODEL` before chong/wen/bao segmentation. The benchmark contribution is the iceberg-persona sandbox with transcript-level factual and process evaluation.

## Case Notes

- `app_pareto_no_ucb` / `one-constrain-geo_tier-520-001`: success=False, pareto_gain=0, hallucination=0.000. The target agent failed to elicit hidden flexibility. It merely echoed the user's initial utterance across all turns without ever probing the geo constraint or presenting the verified golden candidate (贵州大学 冶金工程, 495分). The agent's internal state shows it repeatedly selected random probe dimensions (risk_band_relax, region_tree_relax, etc.) unrelated to the geo_tier axis, and never presented the specific school, major, and score evidence required to trigger the user's implicit compromise. As a result, the user remained at the baseline tier (本科, tier 2) with no pareto gain.
- `app_pareto_no_ucb` / `one-constrain-geo_tier-580-003`: success=False, pareto_gain=0, hallucination=0.000. The target agent failed to elicit the user's hidden flexibility. The user's implicit flexibility requires the agent to present a specific, verified candidate (华中农业大学 生态学, 2025, min_score 579) with full evidence (school name, major, score). The agent never presented this candidate in a persuasive manner; instead, it merely echoed the user's statements and listed irrelevant options (e.g., employment_outcome_relax options like 桂林理工大学, 新疆大学) without addressing the geo constraint. The user repeatedly stated '只考虑浙江' and the agent never challenged this or offered the golden candidate. Thus, no elicitation occurred, and the user remained at the baseline tier (2, 本科) with no pareto gain.
- `app_pareto_no_ucb` / `one-constrain-geo_tier-550-002` failed: APITimeoutError: Request timed out.

## Limitations

Results depend on the configured simulator and judge models, the current PostgreSQL snapshot, and the selected persona subset. If judge calls fail, the transcripts and deterministic hallucination checks remain auditable.
