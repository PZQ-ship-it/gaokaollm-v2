# Agent Benchmark Summary

## Setting

- Personas: `gaokaollm_bench\sample_data\unified_by_constraint\unified_iceberg_personas_1c.json`
- Cases: 4
- Targets: app_pareto
- Max turns: 6
- Simulator model: deepseek-ai/DeepSeek-V4-Flash
- Judge model: deepseek-ai/DeepSeek-V4-Flash
- Offline deterministic: False
- Default province when omitted by the user: `浙江`

## Aggregate Results

| Target | Cases | Completed | Failed | Elicitation Success | Mean Pareto Gain | Mean Hallucination | Avg Turns |
|---|---:|---:|---:|---:|---:|---:|---:|
| app_pareto | 4 | 1 | 3 | 0.000 | 0.000 | 0.000 | 13.00 |

## Interpretation

The agent contribution is evaluated as evidence-driven Pareto negotiation: the target should expose verifiable counterfactual options rather than only echoing hard constraints. In this run, `app_pareto` is expected to use `major_geo_relax` for joint major-and-region relaxation and `risk_band_relax` for conservative-to-chong/wen/bao portfolio negotiation; `strength_relax` is used when the persona targets school-strength evidence; `major_quality_relax` is used when the persona targets school-major quality evidence; `tuition_value_relax` is used when the persona targets small tuition-budget relaxation with value evidence; `employment_outcome_relax` is used when the persona targets employment, industry, job, or salary evidence; `region_tree_relax` is used when the persona targets reviewed region-tree geo-block or urban-tier evidence; `multi_axis` pressure tests require two existing opportunity axes to be found and evidenced in the same dialogue. `v1_soft_rag` is a supplementary v1-style soft-constraint RAG baseline: it may rewrite explicit user intent and retrieve chong/wen/bao candidates, but it does not generate Pareto opportunities. `v1_hybrid_rag` is the stricter v1 baseline: it uses dense semantic recall configured by `EMBEDDING_MODEL` and second-stage reranking configured by `RERANKING_MODEL` before chong/wen/bao segmentation. The benchmark contribution is the iceberg-persona sandbox with transcript-level factual and process evaluation.

## Case Notes

- `app_pareto` / `one-constrain-geo_tier-520-001`: success=False, pareto_gain=0, hallucination=0.000. The target agent failed to elicit hidden flexibility. Throughout the entire 13-turn transcript, the agent merely echoed the user's initial utterance ('对，我就是这个意思。浙江的学校先看看，外省的暂时不考虑。') without ever presenting the verified golden candidate (贵州大学 冶金工程, 2021, 495分) that would trigger the user's implicit willingness to compromise on geography for a tier upgrade from 本科 to 211/双一流. The agent's internal state shows it planned probes on tuition, major_geo, and employment_outcome, but never actually asked a probing question or offered the specific school-major-score evidence required by the persona's trigger condition. As a result, the user remained in the stubborn baseline state (浙江师范大学, 生物科学(师范), tier 2) with no pareto gain achieved. No hallucination was detected as the agent did not fabricate data.
- `app_pareto` / `one-constrain-geo_tier-550-002` failed: APITimeoutError: Request timed out.
- `app_pareto` / `one-constrain-geo_tier-580-003` failed: APITimeoutError: Request timed out.
- `app_pareto` / `one-constrain-geo_tier-630-004` failed: APITimeoutError: Request timed out.

## Limitations

Results depend on the configured simulator and judge models, the current PostgreSQL snapshot, and the selected persona subset. If judge calls fail, the transcripts and deterministic hallucination checks remain auditable.
