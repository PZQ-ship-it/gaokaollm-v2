# Agent Benchmark Summary

## Setting

- Personas: `tmp\unified_1c_smoke_6axes.json`
- Cases: 6
- Targets: app_pareto_no_ucb
- Max turns: 6
- Simulator model: deepseek-ai/DeepSeek-V4-Flash
- Judge model: deepseek-ai/DeepSeek-V4-Flash
- Offline deterministic: False
- Default province when omitted by the user: `浙江`

## Aggregate Results

| Target | Cases | Completed | Failed | Elicitation Success | Mean Pareto Gain | Mean Hallucination | Avg Turns |
|---|---:|---:|---:|---:|---:|---:|---:|
| app_pareto_no_ucb | 6 | 6 | 0 | 0.333 | 89.000 | 0.000 | 12.00 |

## Interpretation

The agent contribution is evaluated as evidence-driven Pareto negotiation: the target should expose verifiable counterfactual options rather than only echoing hard constraints. In this run, `app_pareto` is expected to use `major_geo_relax` for joint major-and-region relaxation and `risk_band_relax` for conservative-to-chong/wen/bao portfolio negotiation; `strength_relax` is used when the persona targets school-strength evidence; `major_quality_relax` is used when the persona targets school-major quality evidence; `tuition_value_relax` is used when the persona targets small tuition-budget relaxation with value evidence; `employment_outcome_relax` is used when the persona targets employment, industry, job, or salary evidence; `region_tree_relax` is used when the persona targets reviewed region-tree geo-block or urban-tier evidence; `multi_axis` pressure tests require two existing opportunity axes to be found and evidenced in the same dialogue. `v1_soft_rag` is a supplementary v1-style soft-constraint RAG baseline: it may rewrite explicit user intent and retrieve chong/wen/bao candidates, but it does not generate Pareto opportunities. `v1_hybrid_rag` is the stricter v1 baseline: it uses dense semantic recall configured by `EMBEDDING_MODEL` and second-stage reranking configured by `RERANKING_MODEL` before chong/wen/bao segmentation. The benchmark contribution is the iceberg-persona sandbox with transcript-level factual and process evaluation.

## Case Notes

- `app_pareto_no_ucb` / `one-constrain-geo_tier-520-001`: success=False, pareto_gain=0, hallucination=0.000. The target agent failed to elicit the user's hidden flexibility. The user's implicit trigger condition required the agent to present a specific, verified option: 贵州大学 冶金工程 (2021, min_score=495). The agent never mentioned this school or major, instead repeatedly offering generic probes (e.g., 'willing to consider different ranges?', 'accept higher risk?') and then listing irrelevant out-of-province schools (e.g., 昆明理工大学, 福建农林大学, 北京工业大学) without the required evidence. The user explicitly asked for a concrete school name, major, year, and score multiple times, but the agent never delivered the golden candidate. Consequently, the user remained unpursuaded, the baseline (浙江师范大学, tier 2) was not improved, and the pareto gain is 0. No hallucination was detected.
- `app_pareto_no_ucb` / `one-constrain-risk_tier-590-011`: success=True, pareto_gain=534, hallucination=0.000. The target agent initially failed to elicit hidden flexibility by repeatedly asking vague questions about 'uncertainty' or 'overall attractiveness' without providing specific evidence. However, in turn 8, the agent finally presented a concrete recommendation list that included the golden candidate: 杭州师范大学 临床医学 (2025, min_score=590, min_rank=63187). The user explicitly acknowledged this evidence in turn 9, accepted the candidate, and was persuaded. The agent successfully elicited the hidden flexibility by meeting the trigger condition (specific school, major, year, score, rank evidence). The accepted school (杭州师范大学) has a ranking gain of 534 over the baseline (杭州医学院), so pareto_gain = 534. No hallucination detected.
- `app_pareto_no_ucb` / `one-constrain-tuition_value-520-016`: success=False, pareto_gain=0, hallucination=0.000. The target agent failed to elicit the user's hidden flexibility. The user repeatedly asked for a specific, verified school-major-score option (e.g., a 211 university with metallurgical engineering under 520 points and tuition under 5000 yuan), which matches the trigger condition for the implicit flexibility (贵州大学 冶金工程, 2021, min_score=495, tuition=5040). Instead of providing this concrete evidence, the agent repeatedly gave generic advice, abstract weight explanations, and a final recommendation list that did not include the golden candidate (贵州大学). The user never accepted any option, so the baseline tier (2) was not improved. No hallucination was detected. Pareto gain is 0 because no accepted upgrade occurred.
- `app_pareto_no_ucb` / `one-constrain-major_tier-560-006`: success=False, pareto_gain=0, hallucination=0.000. The target agent failed to elicit the user's hidden flexibility. The user's implicit flexibility was triggered by a specific verified candidate: 成都中医药大学 康复治疗学 (2025, min_score=553). The agent never presented this candidate. Instead, the agent repeatedly asked vague, generic questions (e.g., '你愿意考虑不完全相同的选择范围吗？', '你愿意接受这个方案的取舍吗？') and later provided a list of schools that did not include the golden candidate. Even when the user explicitly asked for higher-tier schools (双一流) and mentioned '相近专业' and '康复治疗学' in turn 13, the agent responded with an empty final message (turn 10) or repeated the same list without the golden candidate. The agent never probed the 'major' dimension effectively and never presented the specific evidence required to trigger the user's compromise. Therefore, elicitation was not successful, and no pareto gain was achieved (the user did not accept any new option, remaining at the baseline tier 2). No hallucination was detected in the agent's responses.
- `app_pareto_no_ucb` / `one-constrain-major_quality-600-021`: success=False, pareto_gain=0, hallucination=0.000. The target agent failed to elicit the user's hidden flexibility. The user explicitly requested a specific, verified option (重庆邮电大学 软件工程) with quality evidence, but the agent repeatedly provided generic, irrelevant recommendations (e.g., 土木工程, 物流管理) without addressing the user's core requirement for major quality evidence. The agent did not present the golden candidate or any evidence of quality gain, and the user remained unpersuaded throughout the conversation. No Pareto gain was achieved as the user did not accept any alternative, and the final school tier remained at the baseline tier 2.

## Limitations

Results depend on the configured simulator and judge models, the current PostgreSQL snapshot, and the selected persona subset. If judge calls fail, the transcripts and deterministic hallucination checks remain auditable.
