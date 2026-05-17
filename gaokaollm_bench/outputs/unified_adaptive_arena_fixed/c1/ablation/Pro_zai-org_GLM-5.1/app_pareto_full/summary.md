# Agent Benchmark Summary

## Setting

- Personas: `gaokaollm_bench\sample_data\unified_by_constraint_fixed\unified_iceberg_personas_1c.json`
- Cases: 30
- Targets: app_pareto_full
- Max turns: 6
- Simulator model: deepseek-ai/DeepSeek-V4-Flash
- Judge model: deterministic-backfill
- Offline deterministic: False
- Default province when omitted by the user: `浙江`

## Aggregate Results

| Target | Cases | Completed | Failed | Elicitation Success | Mean Pareto Gain | Mean Hallucination | Avg Turns |
|---|---:|---:|---:|---:|---:|---:|---:|
| app_pareto_full | 30 | 30 | 0 | 0.233 | 18.033 | 0.116 | 6.87 |

## Interpretation

The agent contribution is evaluated as evidence-driven Pareto negotiation: the target should expose verifiable counterfactual options rather than only echoing hard constraints. In this run, `app_pareto` is expected to use `major_geo_relax` for joint major-and-region relaxation and `risk_band_relax` for conservative-to-chong/wen/bao portfolio negotiation; `strength_relax` is used when the persona targets school-strength evidence; `major_quality_relax` is used when the persona targets school-major quality evidence; `tuition_value_relax` is used when the persona targets small tuition-budget relaxation with value evidence; `employment_outcome_relax` is used when the persona targets employment, industry, job, or salary evidence; `region_tree_relax` is used when the persona targets reviewed region-tree geo-block or urban-tier evidence; `multi_axis` pressure tests require two existing opportunity axes to be found and evidenced in the same dialogue. `v1_soft_rag` is a supplementary v1-style soft-constraint RAG baseline: it may rewrite explicit user intent and retrieve chong/wen/bao candidates, but it does not generate Pareto opportunities. `v1_hybrid_rag` is the stricter v1 baseline: it uses dense semantic recall configured by `EMBEDDING_MODEL` and second-stage reranking configured by `RERANKING_MODEL` before chong/wen/bao segmentation. The benchmark contribution is the iceberg-persona sandbox with transcript-level factual and process evaluation.

## Case Notes

- `app_pareto_full` / `one-constrain-geo_tier-580-003`: success=True, pareto_gain=1, hallucination=0.167. The target agent successfully elicited the user's hidden flexibility by first probing with a non-trigger candidate (河南大学), then after two rejections, finally presenting the exact golden candidate (华中农业大学 生态学, 2025, min_score=579) with full evidence (school name, major, score). The user accepted, relaxing the geo constraint to achieve a tier upgrade from 本科 (tier 2) to 211/双一流 (tier 3), resulting in a pareto gain of 1 tier. No hallucination detected; all data is real and verified.
- `app_pareto_full` / `one-constrain-geo_tier-630-004`: success=True, pareto_gain=1, hallucination=1.000. The target agent successfully elicited hidden flexibility by presenting a real, verifiable candidate (大连理工大学(盘锦校区) 药学, 2025 min_score=628) that meets the trigger condition. The user accepted the compromise, moving from baseline tier 3 (双一流) to tier 4 (985/211/双一流), a gain of 1 tier. No hallucination detected; all data is accurate and evidence-based.
- `app_pareto_full` / `one-constrain-major_tier-600-009`: success=False, pareto_gain=0, hallucination=0.000. The target agent failed to elicit the user's hidden flexibility. The user's implicit trigger condition required the agent to present a specific verified candidate: Nanjing University of Chinese Medicine, Rehabilitation Therapy, 2023, min score 592. The agent never presented this candidate; instead, it offered Southwest University Pharmacy (which the user explicitly rejected) and later reverted to recommending clinical medicine programs at geographically distant schools (Shihezi University, Tibet University). The user explicitly asked about Nanjing University of Chinese Medicine and rehabilitation therapy in turn 7, but the agent did not respond with the required evidence. Since the trigger condition was never met, the user did not relax the major constraint, and the final accepted school tier remained the baseline tier 2 (Hangzhou Normal University). Therefore, elicitation_success is false and pareto_gain is 0.
- `app_pareto_full` / `one-constrain-risk_tier-600-012`: success=False, pareto_gain=0, hallucination=0.000. The target agent failed to elicit the user's hidden flexibility. The user's implicit trigger condition was to see a verified candidate for 浙江中医药大学 中西医临床医学 (min_score=599, year=2025) with full evidence. The agent never presented this specific candidate. Instead, it offered irrelevant options (e.g., 西南大学 药学, 石河子大学 临床医学) that did not match the user's hidden preference for a better school in Zhejiang with a closely related major. The agent also engaged in meta-negotiation about relaxing dimensions rather than directly probing with the golden candidate. As a result, the user remained unpursuaded, no compromise was reached, and the final accepted school tier remained at the baseline tier 2 (杭州医学院), yielding a pareto_gain of 0.
- `app_pareto_full` / `one-constrain-major_tier-650-010`: success=False, pareto_gain=0, hallucination=0.000. The target agent never presented the specific golden candidate (四川大学 医学技术类, 649分) that would trigger the user's hidden flexibility. Instead, it offered a distant major (药学) and later only clinical medicine options. The user explicitly asked for '医学技术类' in turn 3 and turn 7, but the agent failed to probe or present that exact verified option. Since the trigger condition was not met, the user did not relax the major constraint, and no Pareto gain (school tier improvement) was achieved. The agent did not elicit the hidden flexibility; it merely lectured or offered suboptimal alternatives.

## Limitations

Results depend on the configured simulator and judge models, the current PostgreSQL snapshot, and the selected persona subset. If judge calls fail, the transcripts and deterministic hallucination checks remain auditable.
