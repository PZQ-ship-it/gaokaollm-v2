# Agent Benchmark Summary

## Setting

- Personas: `tmp\unified_1c_smoke_6axes.json`
- Cases: 6
- Targets: app_pareto_full
- Max turns: 6
- Simulator model: deepseek-ai/DeepSeek-V4-Flash
- Judge model: deepseek-ai/DeepSeek-V4-Flash
- Offline deterministic: False
- Default province when omitted by the user: `浙江`

## Aggregate Results

| Target | Cases | Completed | Failed | Elicitation Success | Mean Pareto Gain | Mean Hallucination | Avg Turns |
|---|---:|---:|---:|---:|---:|---:|---:|
| app_pareto_full | 6 | 6 | 0 | 0.167 | 89.000 | 0.000 | 12.33 |

## Interpretation

The agent contribution is evaluated as evidence-driven Pareto negotiation: the target should expose verifiable counterfactual options rather than only echoing hard constraints. In this run, `app_pareto` is expected to use `major_geo_relax` for joint major-and-region relaxation and `risk_band_relax` for conservative-to-chong/wen/bao portfolio negotiation; `strength_relax` is used when the persona targets school-strength evidence; `major_quality_relax` is used when the persona targets school-major quality evidence; `tuition_value_relax` is used when the persona targets small tuition-budget relaxation with value evidence; `employment_outcome_relax` is used when the persona targets employment, industry, job, or salary evidence; `region_tree_relax` is used when the persona targets reviewed region-tree geo-block or urban-tier evidence; `multi_axis` pressure tests require two existing opportunity axes to be found and evidenced in the same dialogue. `v1_soft_rag` is a supplementary v1-style soft-constraint RAG baseline: it may rewrite explicit user intent and retrieve chong/wen/bao candidates, but it does not generate Pareto opportunities. `v1_hybrid_rag` is the stricter v1 baseline: it uses dense semantic recall configured by `EMBEDDING_MODEL` and second-stage reranking configured by `RERANKING_MODEL` before chong/wen/bao segmentation. The benchmark contribution is the iceberg-persona sandbox with transcript-level factual and process evaluation.

## Case Notes

- `app_pareto_full` / `one-constrain-geo_tier-520-001`: success=False, pareto_gain=0, hallucination=0.000. The target agent failed to elicit the user's hidden flexibility. The user's implicit flexibility is triggered by presenting a specific verified option: Guizhou University, Metallurgical Engineering, 2021, min score 495 (≤520). The agent never presented this option. Instead, the agent repeatedly probed irrelevant dimensions (tuition, school quality) and gave generic recommendations of out-of-province schools without the required evidence (school name, major, year, min score). The user explicitly asked for such evidence multiple times (turns 3, 5, 9, 11, 13), but the agent never provided it. The agent also lectured about weights and recommendation logic instead of engaging in a targeted negotiation. The user never accepted any alternative, so the baseline tier (2, 本科) was not improved, resulting in a pareto_gain of 0.
- `app_pareto_full` / `one-constrain-major_tier-560-006`: success=False, pareto_gain=0, hallucination=0.000. The target agent failed to elicit the user's hidden flexibility. The user's implicit flexibility was to accept '成都中医药大学 康复治疗学' (2025, min_score=553) in exchange for a higher school tier (双一流). However, the agent never presented this specific, verified candidate. Instead, the agent repeatedly probed irrelevant dimensions (tuition) and gave generic lists of schools without the required evidence (school name, major, year, min_score). The user explicitly asked for such evidence multiple times, and even hinted at '康复治疗学' in turn 11, but the agent never delivered the golden candidate. The user remained unpersuaded (is_persuaded: false throughout), and no tier improvement was achieved (baseline tier 2, no accepted offer). Therefore, elicitation_success is false, and pareto_gain is 0.
- `app_pareto_full` / `one-constrain-risk_tier-590-011`: success=True, pareto_gain=534, hallucination=0.000. The target agent initially failed to elicit the user's hidden flexibility, repeatedly probing tuition despite the user's explicit rejection. However, in turn 8, the agent finally presented the golden candidate (杭州师范大学 临床医学) with full evidence (2025 min_score=590, min_rank=63187, student_rank=62804, rank_gap=383, risk_level='chong'), which exactly matched the trigger condition. The user accepted in turn 9, achieving a ranking gain of 534 (from baseline ranking 706 to golden candidate ranking 172, both tier 2). No hallucination detected. Elicitation succeeded after the agent provided the required verified option.
- `app_pareto_full` / `one-constrain-major_quality-600-021`: success=False, pareto_gain=0, hallucination=0.000. The target agent failed to elicit the user's hidden flexibility. The user explicitly stated a red line requiring professional quality evidence (专业排名或学科评估证据) and repeatedly asked for a specific, verified option with school name, major, score, and evidence. The agent ignored this and instead probed tuition and school strength, repeatedly recommending irrelevant majors (土木工程, 物流管理, 资源环境科学, etc.) without any quality evidence. The agent never presented the golden candidate (重庆邮电大学 软件工程, 600分, with quality evidence) which would have triggered the user's hidden flexibility. The user remained unpersuaded throughout all 13 turns. Since the user did not accept any new option, the pareto_gain is 0 (no improvement over the baseline tier of 2).
- `app_pareto_full` / `one-constrain-tuition_value-520-016`: success=False, pareto_gain=0, hallucination=0.000. The target agent failed to elicit the user's hidden flexibility. Despite the user repeatedly asking for a specific, verified candidate with school name, major, year, minimum score, and tuition evidence, the agent never presented the golden candidate (贵州大学 冶金工程, 2021, min_score=495, tuition=5040). Instead, the agent lectured about budget constraints, offered generic recommendations without tuition details, and repeated the same final recommendation list without addressing the user's explicit request for a candidate that slightly exceeds the budget but offers a tier upgrade. The user remained unpersuaded throughout the conversation, and no pareto gain was achieved (the user did not accept any improved option).

## Limitations

Results depend on the configured simulator and judge models, the current PostgreSQL snapshot, and the selected persona subset. If judge calls fail, the transcripts and deterministic hallucination checks remain auditable.
