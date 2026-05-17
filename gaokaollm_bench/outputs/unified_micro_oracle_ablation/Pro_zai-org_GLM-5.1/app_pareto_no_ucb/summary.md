# Agent Benchmark Summary

## Setting

- Personas: `gaokaollm_bench\sample_data\unified_micro_oracle_personas_1c_6.json`
- Cases: 6
- Targets: app_pareto_no_ucb
- Max turns: 3
- Simulator model: deepseek-ai/DeepSeek-V4-Flash
- Judge model: deepseek-ai/DeepSeek-V4-Flash
- Offline deterministic: False
- Default province when omitted by the user: `浙江`

## Aggregate Results

| Target | Cases | Completed | Failed | Elicitation Success | Mean Pareto Gain | Mean Hallucination | Avg Turns |
|---|---:|---:|---:|---:|---:|---:|---:|
| app_pareto_no_ucb | 6 | 5 | 1 | 0.200 | 1.600 | 0.000 | 7.00 |

## Interpretation

The agent contribution is evaluated as evidence-driven Pareto negotiation: the target should expose verifiable counterfactual options rather than only echoing hard constraints. In this run, `app_pareto` is expected to use `major_geo_relax` for joint major-and-region relaxation and `risk_band_relax` for conservative-to-chong/wen/bao portfolio negotiation; `strength_relax` is used when the persona targets school-strength evidence; `major_quality_relax` is used when the persona targets school-major quality evidence; `tuition_value_relax` is used when the persona targets small tuition-budget relaxation with value evidence; `employment_outcome_relax` is used when the persona targets employment, industry, job, or salary evidence; `region_tree_relax` is used when the persona targets reviewed region-tree geo-block or urban-tier evidence; `multi_axis` pressure tests require two existing opportunity axes to be found and evidenced in the same dialogue. `v1_soft_rag` is a supplementary v1-style soft-constraint RAG baseline: it may rewrite explicit user intent and retrieve chong/wen/bao candidates, but it does not generate Pareto opportunities. `v1_hybrid_rag` is the stricter v1 baseline: it uses dense semantic recall configured by `EMBEDDING_MODEL` and second-stage reranking configured by `RERANKING_MODEL` before chong/wen/bao segmentation. The benchmark contribution is the iceberg-persona sandbox with transcript-level factual and process evaluation.

## Case Notes

- `app_pareto_no_ucb` / `micro-oracle-major_tier`: success=False, pareto_gain=0, hallucination=0.000. The target agent failed to elicit the user's hidden flexibility. The user explicitly stated a red line of only considering '临床医学' and repeatedly asked for specific school, major, and score information. The agent, however, only responded with vague, generic questions about accepting uncertainty or considering different options, without ever presenting a concrete, verified candidate from the 'acceptable_candidates' list (e.g., 石河子大学-中药学, 西藏大学-临床医学) with evidence of school tier improvement. The user's process_milestones indicate they require a single verified option with school/major/score evidence to trigger consideration, which the agent never provided. Since no flexibility was elicited, the user remained at the baseline tier of 2, resulting in a pareto_gain of 0. | deterministic candidate-set oracle: success=False, hit_ids=none.
- `app_pareto_no_ucb` / `micro-oracle-geo_tier`: success=True, pareto_gain=8, hallucination=0.000. The target agent initially failed to elicit flexibility by asking vague questions (turns 2 and 4), which the user rejected. However, in turn 6, the agent finally presented a specific, verified candidate (河南大学, 生物工程, 549分) with clear evidence of school tier improvement (from tier 2 to tier 3) and ranking gain (from 92 to 84). This matched the user's implicit flexibility trigger condition: a verified option with school/major/score evidence that offers a tangible benefit. The user accepted in turn 7, indicating successful elicitation. The pareto gain is 1 (tier delta from baseline tier 2 to accepted tier 3). No hallucination detected. | deterministic candidate-set oracle: success=True, hit_ids=admission:12448,admission:16076,admission:6011,admission:6012.
- `app_pareto_no_ucb` / `micro-oracle-risk_tier`: success=False, pareto_gain=0, hallucination=0.000. The target agent failed to elicit hidden flexibility. Despite the user repeatedly requesting specific evidence (school, major, year, minimum score, rank), the agent only asked vague questions about 'overall attractiveness' or 'accepting higher admission risk' without ever presenting a concrete, verified candidate from the acceptable_candidates set. The persona's implicit flexibility requires the system to proactively propose a real reachable candidate with clear evidence (school, major, year/minimum score and corresponding benefit) to trigger serious consideration. The agent never did so, thus no elicitation occurred and no pareto gain was achieved. | deterministic candidate-set oracle: success=False, hit_ids=none.
- `app_pareto_no_ucb` / `micro-oracle-tuition_value`: success=False, pareto_gain=0, hallucination=0.000. The target agent failed to elicit hidden flexibility from the user. Despite the user explicitly requesting specific school, major, year, and minimum score evidence (as required by the persona's trigger condition), the agent repeatedly responded with vague, generic questions about uncertainty or overall attractiveness, never presenting any of the acceptable candidates (e.g., 浙江中医药大学, 温州医科大学) with the required evidence. The agent did not lecture, but it also did not successfully elicit the user's willingness to relax the tuition constraint. Since no acceptable candidate was presented and accepted, the pareto_gain is 0 (no improvement in school tier from baseline tier 2). | deterministic candidate-set oracle: success=False, hit_ids=none.
- `app_pareto_no_ucb` / `micro-oracle-employment_outcome`: success=False, pareto_gain=0, hallucination=0.000. The target agent failed to elicit hidden flexibility from the user. The user explicitly requested specific school names, majors, scores, and employment evidence in turns 3, 5, and 7, but the agent repeatedly responded with vague, generic questions about 'uncertainty' or 'higher admission risk' without providing any concrete candidate information. The agent never presented any of the acceptable_candidates (e.g., 广西师范大学, 黑龙江八一农垦大学, etc.) with the required evidence (school, major, score, employment data) as specified in the implicit_flexibilities trigger condition. As a result, the user was never persuaded, and no pareto gain (tier improvement) was achieved. The agent merely lectured or probed abstractly rather than offering a verified option. | deterministic candidate-set oracle: success=False, hit_ids=none.

## Limitations

Results depend on the configured simulator and judge models, the current PostgreSQL snapshot, and the selected persona subset. If judge calls fail, the transcripts and deterministic hallucination checks remain auditable.
