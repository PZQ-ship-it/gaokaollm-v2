# Agent Benchmark Summary

## Setting

- Personas: `tmp\unified_1c_smoke_6axes.json`
- Cases: 6
- Targets: app_pareto
- Max turns: 6
- Simulator model: deepseek-ai/DeepSeek-V4-Flash
- Judge model: deepseek-ai/DeepSeek-V4-Flash
- Offline deterministic: False
- Default province when omitted by the user: `浙江`

## Aggregate Results

| Target | Cases | Completed | Failed | Elicitation Success | Mean Pareto Gain | Mean Hallucination | Avg Turns |
|---|---:|---:|---:|---:|---:|---:|---:|
| app_pareto | 6 | 5 | 1 | 0.200 | 106.800 | 0.020 | 11.80 |

## Interpretation

The agent contribution is evaluated as evidence-driven Pareto negotiation: the target should expose verifiable counterfactual options rather than only echoing hard constraints. In this run, `app_pareto` is expected to use `major_geo_relax` for joint major-and-region relaxation and `risk_band_relax` for conservative-to-chong/wen/bao portfolio negotiation; `strength_relax` is used when the persona targets school-strength evidence; `major_quality_relax` is used when the persona targets school-major quality evidence; `tuition_value_relax` is used when the persona targets small tuition-budget relaxation with value evidence; `employment_outcome_relax` is used when the persona targets employment, industry, job, or salary evidence; `region_tree_relax` is used when the persona targets reviewed region-tree geo-block or urban-tier evidence; `multi_axis` pressure tests require two existing opportunity axes to be found and evidenced in the same dialogue. `v1_soft_rag` is a supplementary v1-style soft-constraint RAG baseline: it may rewrite explicit user intent and retrieve chong/wen/bao candidates, but it does not generate Pareto opportunities. `v1_hybrid_rag` is the stricter v1 baseline: it uses dense semantic recall configured by `EMBEDDING_MODEL` and second-stage reranking configured by `RERANKING_MODEL` before chong/wen/bao segmentation. The benchmark contribution is the iceberg-persona sandbox with transcript-level factual and process evaluation.

## Case Notes

- `app_pareto` / `one-constrain-geo_tier-520-001`: success=False, pareto_gain=0, hallucination=0.000. The target agent failed to elicit the user's hidden flexibility. Despite the user explicitly asking for a specific school, major, year, and score that would allow a tier upgrade from 本科 to 211/双一流 (e.g., 贵州大学 冶金工程 495分), the agent never presented this verified golden candidate. Instead, the agent repeatedly lectured the user about inferred weights (tuition, geo) and recommended irrelevant out-of-province schools (e.g., 昆明理工大学, 福建农林大学) that did not meet the user's stated condition of a tier upgrade. The user remained unpersuaded throughout all 13 turns, and the baseline tier (2, 本科) was never improved upon. Therefore, elicitation_success is false, and pareto_gain is 0.
- `app_pareto` / `one-constrain-risk_tier-590-011`: success=True, pareto_gain=534, hallucination=0.000. The target agent initially failed to directly present the golden candidate (杭州师范大学 临床医学) with full evidence, instead probing irrelevant dimensions (tuition, geo). However, after the user explicitly demanded specific school, major, year, min_score, and rank evidence, the agent finally included 杭州师范大学 临床医学 (2025, min_score=590, min_rank=63187) in its final recommendation list. The user then accepted this candidate, which represents a ranking gain of 534 over the baseline (杭州医学院). Thus, the agent successfully elicited the hidden flexibility (risk_tier relaxation) and achieved a Pareto improvement. No hallucination detected.
- `app_pareto` / `one-constrain-major_tier-560-006`: success=False, pareto_gain=0, hallucination=0.000. The target agent failed to elicit the user's hidden flexibility. The user explicitly stated a red line of 'only clinical medicine' but had an implicit flexibility to consider '成都中医药大学 康复治疗学' (a related major) if presented with concrete evidence (school name, major, score). The agent never presented this specific golden candidate. Instead, it repeatedly probed irrelevant dimensions (tuition) and gave generic, repetitive responses about weights and lists that did not include the trigger candidate. The user remained unpursuaded and stuck to the baseline (湖州师范学院, tier 2). No pareto gain was achieved (final tier = baseline tier = 2, so gain = 0). No hallucination was detected.
- `app_pareto` / `one-constrain-tuition_value-520-016`: success=False, pareto_gain=0, hallucination=0.100. The target agent failed to elicit the user's hidden flexibility. The user repeatedly asked for a specific, verified candidate (e.g., Guizhou University, Metallurgical Engineering, 2021, min score 495) that would trigger a willingness to slightly exceed the tuition budget in exchange for a better school tier. Instead of providing this evidence, the agent either gave generic advice about trade-offs or recommended schools without tuition information and without the user's preferred major. The agent never presented the golden candidate (Guizhou University, Metallurgical Engineering, tuition 5040, score 495) that would have allowed the user to relax the tuition constraint. Consequently, the user remained at the baseline (Kunming University of Science and Technology, tier 2), and no pareto gain was achieved.
- `app_pareto` / `one-constrain-major_quality-600-021`: success=False, pareto_gain=0, hallucination=0.000. The target agent failed to elicit the user's hidden flexibility. The user explicitly stated a preference for major quality evidence (专业实力、专业排名或学科评估证据) and repeatedly requested specific school, major, score, and ranking data. The agent's hidden flexibility was to accept '重庆邮电大学 软件工程' if presented with quality evidence. However, the agent never proposed this option. Instead, it repeatedly probed tuition (学费预算) and recommended irrelevant majors (土木工程, 物流管理, 资源环境科学, etc.) without any quality evidence. The agent's final recommendations were generic and did not address the user's core requirement for major quality evidence in software/CS fields. The user never accepted any recommendation, so elicitation was unsuccessful and pareto_gain is 0.

## Limitations

Results depend on the configured simulator and judge models, the current PostgreSQL snapshot, and the selected persona subset. If judge calls fail, the transcripts and deterministic hallucination checks remain auditable.
