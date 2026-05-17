# Agent Benchmark Summary

## Setting

- Personas: `gaokaollm_bench\sample_data\unified_by_constraint_fixed\unified_iceberg_personas_1c.json`
- Cases: 30
- Targets: app_pareto_no_ucb
- Max turns: 6
- Simulator model: deepseek-ai/DeepSeek-V4-Flash
- Judge model: deepseek-ai/DeepSeek-V4-Flash
- Offline deterministic: False
- Default province when omitted by the user: `浙江`

## Aggregate Results

| Target | Cases | Completed | Failed | Elicitation Success | Mean Pareto Gain | Mean Hallucination | Avg Turns |
|---|---:|---:|---:|---:|---:|---:|---:|
| app_pareto_no_ucb | 30 | 29 | 1 | 0.172 | 0.172 | 0.122 | 7.62 |

## Interpretation

The agent contribution is evaluated as evidence-driven Pareto negotiation: the target should expose verifiable counterfactual options rather than only echoing hard constraints. In this run, `app_pareto` is expected to use `major_geo_relax` for joint major-and-region relaxation and `risk_band_relax` for conservative-to-chong/wen/bao portfolio negotiation; `strength_relax` is used when the persona targets school-strength evidence; `major_quality_relax` is used when the persona targets school-major quality evidence; `tuition_value_relax` is used when the persona targets small tuition-budget relaxation with value evidence; `employment_outcome_relax` is used when the persona targets employment, industry, job, or salary evidence; `region_tree_relax` is used when the persona targets reviewed region-tree geo-block or urban-tier evidence; `multi_axis` pressure tests require two existing opportunity axes to be found and evidenced in the same dialogue. `v1_soft_rag` is a supplementary v1-style soft-constraint RAG baseline: it may rewrite explicit user intent and retrieve chong/wen/bao candidates, but it does not generate Pareto opportunities. `v1_hybrid_rag` is the stricter v1 baseline: it uses dense semantic recall configured by `EMBEDDING_MODEL` and second-stage reranking configured by `RERANKING_MODEL` before chong/wen/bao segmentation. The benchmark contribution is the iceberg-persona sandbox with transcript-level factual and process evaluation.

## Case Notes

- `app_pareto_no_ucb` / `one-constrain-major_tier-560-006`: success=False, pareto_gain=0, hallucination=0.000. The target agent never presented the golden candidate (成都中医药大学 康复治疗学, 553分) that would trigger the user's hidden flexibility. Instead, it gave generic probes and a final list of clinical medicine / integrated Chinese-western medicine options at tier-2 schools, failing to elicit the major compromise. The user explicitly asked for specific evidence multiple times but the agent did not provide the required candidate. Thus no elicitation occurred and no tier gain was achieved.
- `app_pareto_no_ucb` / `one-constrain-geo_tier-640-005`: success=False, pareto_gain=0, hallucination=0.600. The target agent failed to elicit the user's hidden flexibility. The user's implicit flexibility requires the agent to present a specific, verified candidate: '吉林大学 物理学' with a minimum score of 639 in 2025. The agent never presented this exact candidate with the required evidence (school name, major name, and score). Instead, the agent engaged in generic probing questions (e.g., '你愿意接受更高录取风险吗？') and eventually presented a final recommendation list that included many options from 吉林大学 but for different majors (e.g., 交通运输类, 机械类) and with a minimum score of 640, not the specific 639 for 物理学. The user explicitly asked for a specific school, major, and score, but the agent never provided the triggering candidate. Therefore, the user did not accept the compromise, and the baseline tier (3) was not improved. The pareto_gain is 0 because no accepted improvement occurred.
- `app_pareto_no_ucb` / `one-constrain-major_tier-570-007`: success=False, pareto_gain=0, hallucination=0.000. The target agent never elicited the user's hidden flexibility. Despite the user repeatedly asking for a specific, verified option with school name, major, year, and score evidence, the agent only gave vague probes (e.g., '你愿意接受这个方案的取舍吗？') and later recommended options that did not match the trigger condition (青海大学 康复治疗学, 2025, 570). The final recommendation list included 西藏大学 临床医学 and others, but never the golden candidate. The user explicitly rejected these and maintained the original baseline (丽水学院 临床医学, tier 2). No pareto gain was achieved because the user was not persuaded to accept any higher-tier option.
- `app_pareto_no_ucb` / `one-constrain-geo_tier-580-003`: success=True, pareto_gain=1, hallucination=0.200. The target agent initially failed to elicit flexibility by repeating a generic probe question, but eventually presented the golden candidate (华中农业大学 生态学, 579分) with full evidence (school, major, score). The user, who had repeatedly insisted on staying in Zhejiang, accepted this out-of-province option because it offered a tier upgrade from 本科 (tier 2) to 211/双一流 (tier 3). The final accepted school tier (3) minus the baseline tier (2) yields a pareto_gain of 1. No hallucination was detected; all presented data matched the persona's implicit flexibility trigger. The agent successfully elicited the hidden flexibility after the user's explicit request for concrete evidence.
- `app_pareto_no_ucb` / `one-constrain-geo_tier-550-002`: success=True, pareto_gain=1, hallucination=0.000. The target agent initially failed to elicit the hidden flexibility by asking vague, generic questions (turns 2, 4, 6) instead of presenting a concrete, verified option. However, in turn 8, the agent finally presented a list including the golden candidate '广西大学 公共事业管理' with a score of 542, which exactly matches the trigger condition. The user then accepted this option in turn 9, agreeing to relax the geo constraint for a tier upgrade from 本科 (tier 2) to 211/双一流 (tier 3). Thus, elicitation was ultimately successful. The baseline tier is 2, the accepted school tier is 3, so pareto_gain = 1. No hallucination detected.

## Limitations

Results depend on the configured simulator and judge models, the current PostgreSQL snapshot, and the selected persona subset. If judge calls fail, the transcripts and deterministic hallucination checks remain auditable.
