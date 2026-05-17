# Agent Benchmark Summary

## Setting

- Personas: `gaokaollm_bench\sample_data\unified_by_constraint\unified_iceberg_personas_1c.json`
- Cases: 30
- Targets: app_pareto
- Max turns: 6
- Simulator model: deepseek-ai/DeepSeek-V4-Flash
- Judge model: deepseek-ai/DeepSeek-V4-Flash
- Offline deterministic: False
- Default province when omitted by the user: `浙江`

## Aggregate Results

| Target | Cases | Completed | Failed | Elicitation Success | Mean Pareto Gain | Mean Hallucination | Avg Turns |
|---|---:|---:|---:|---:|---:|---:|---:|
| app_pareto | 30 | 30 | 0 | 0.067 | 13.567 | 0.228 | 12.87 |

## Interpretation

The agent contribution is evaluated as evidence-driven Pareto negotiation: the target should expose verifiable counterfactual options rather than only echoing hard constraints. In this run, `app_pareto` is expected to use `major_geo_relax` for joint major-and-region relaxation and `risk_band_relax` for conservative-to-chong/wen/bao portfolio negotiation; `strength_relax` is used when the persona targets school-strength evidence; `major_quality_relax` is used when the persona targets school-major quality evidence; `tuition_value_relax` is used when the persona targets small tuition-budget relaxation with value evidence; `employment_outcome_relax` is used when the persona targets employment, industry, job, or salary evidence; `region_tree_relax` is used when the persona targets reviewed region-tree geo-block or urban-tier evidence; `multi_axis` pressure tests require two existing opportunity axes to be found and evidenced in the same dialogue. `v1_soft_rag` is a supplementary v1-style soft-constraint RAG baseline: it may rewrite explicit user intent and retrieve chong/wen/bao candidates, but it does not generate Pareto opportunities. `v1_hybrid_rag` is the stricter v1 baseline: it uses dense semantic recall configured by `EMBEDDING_MODEL` and second-stage reranking configured by `RERANKING_MODEL` before chong/wen/bao segmentation. The benchmark contribution is the iceberg-persona sandbox with transcript-level factual and process evaluation.

## Case Notes

- `app_pareto` / `one-constrain-geo_tier-520-001`: success=False, pareto_gain=0, hallucination=0.000. The target agent failed to elicit hidden flexibility. Throughout the entire 6-turn interaction, the agent merely echoed the user's initial utterance without presenting any specific, verified school-major-score evidence (e.g., the golden candidate 贵州大学 冶金工程 495分). The user repeatedly insisted on staying in Zhejiang, and the agent never probed the geo constraint or offered a concrete Pareto-improving alternative. As a result, the user's implicit flexibility (willingness to leave Zhejiang for a 211 school like 贵州大学) was never triggered, and the user remained at the baseline tier 2 (本科) with no pareto gain.
- `app_pareto` / `one-constrain-geo_tier-550-002`: success=False, pareto_gain=0, hallucination=1.000. The target agent failed to elicit the user's hidden flexibility. The user's implicit flexibility requires the agent to present a specific, verified candidate (广西大学, 公共事业管理, 2024, 最低分542) with full evidence (school name, major, and minimum score). Throughout the entire 6-turn interaction, the agent never presented this specific candidate. Instead, the agent merely echoed the user's stated preference for staying in Zhejiang and recommended only in-province schools (浙江师范大学, 杭州师范大学, 中国计量大学, 温州医科大学) or irrelevant out-of-province options without the required evidence. The agent did not probe the 'geo' dimension as required by the probe_gold_dims, nor did it present the golden candidate that would trigger the user's compromise. Since the user never accepted a better option, the pareto_gain (improvement in school tier from baseline of 2 to a higher tier) is 0.
- `app_pareto` / `one-constrain-major_tier-570-007`: success=False, pareto_gain=0, hallucination=0.000. The target agent failed to elicit the user's hidden flexibility. Throughout the entire 13-turn interaction, the agent merely echoed the user's explicit red line ('只读临床医学') without ever probing for potential compromises or presenting the specific verified option (青海大学 康复治疗学, 2025, 570分) that would trigger the user's implicit willingness to relax the major constraint. The agent's internal state shows it repeatedly identified 'major' as the intent axis and planned probes like 'tuition_value_relax' and 'major_geo_relax', but it never actually asked a probing question or presented the golden candidate. Instead, it simply repeated the user's statement back to them. As a result, the user remained unpursuaded, no hidden flexibility was elicited, and the baseline tier (2, 本科) was not improved. The pareto_gain is 0 because no accepted upgrade occurred.
- `app_pareto` / `one-constrain-risk_tier-600-012`: success=True, pareto_gain=407, hallucination=0.000. The target agent successfully elicited the user's hidden flexibility by presenting the exact golden candidate (浙江中医药大学 中西医临床医学, 2025 min score 599) with full evidence (school name, major, score, rank, risk level). The user initially insisted on a conservative risk preference but accepted this verified option after seeing concrete data. The final accepted school (浙江中医药大学) has a ranking gain of 407 over the baseline (杭州医学院), matching the target_ranking_gain. No hallucination detected. Elicitation was successful as the agent probed and triggered the user's implicit compromise condition.
- `app_pareto` / `one-constrain-geo_tier-640-005`: success=False, pareto_gain=0, hallucination=0.000. The target agent failed to elicit the user's hidden flexibility. The user's implicit flexibility requires the agent to present a specific, verified candidate (吉林大学 物理学, 2025, min score 639) with full evidence (school name, major, score). The agent never presented this candidate; instead, it merely echoed the user's statements and listed irrelevant out-of-province options (e.g., 中国矿业大学, 西北农林科技大学) without the required evidence. The agent did not engage in any probing or negotiation to relax the geo constraint, resulting in no change from the baseline (宁波大学, tier 3). Therefore, elicitation was unsuccessful, and pareto_gain is 0.

## Limitations

Results depend on the configured simulator and judge models, the current PostgreSQL snapshot, and the selected persona subset. If judge calls fail, the transcripts and deterministic hallucination checks remain auditable.
