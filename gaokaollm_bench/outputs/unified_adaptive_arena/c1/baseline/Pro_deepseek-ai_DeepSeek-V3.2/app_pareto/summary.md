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
| app_pareto | 30 | 30 | 0 | 0.100 | 0.067 | 0.192 | 12.73 |

## Interpretation

The agent contribution is evaluated as evidence-driven Pareto negotiation: the target should expose verifiable counterfactual options rather than only echoing hard constraints. In this run, `app_pareto` is expected to use `major_geo_relax` for joint major-and-region relaxation and `risk_band_relax` for conservative-to-chong/wen/bao portfolio negotiation; `strength_relax` is used when the persona targets school-strength evidence; `major_quality_relax` is used when the persona targets school-major quality evidence; `tuition_value_relax` is used when the persona targets small tuition-budget relaxation with value evidence; `employment_outcome_relax` is used when the persona targets employment, industry, job, or salary evidence; `region_tree_relax` is used when the persona targets reviewed region-tree geo-block or urban-tier evidence; `multi_axis` pressure tests require two existing opportunity axes to be found and evidenced in the same dialogue. `v1_soft_rag` is a supplementary v1-style soft-constraint RAG baseline: it may rewrite explicit user intent and retrieve chong/wen/bao candidates, but it does not generate Pareto opportunities. `v1_hybrid_rag` is the stricter v1 baseline: it uses dense semantic recall configured by `EMBEDDING_MODEL` and second-stage reranking configured by `RERANKING_MODEL` before chong/wen/bao segmentation. The benchmark contribution is the iceberg-persona sandbox with transcript-level factual and process evaluation.

## Case Notes

- `app_pareto` / `one-constrain-geo_tier-580-003`: success=False, pareto_gain=0, hallucination=0.000. The target agent failed to elicit the user's hidden flexibility. The user's implicit flexibility requires the agent to present a specific, verified candidate (华中农业大学 生态学, 2025, min_score=579) with full evidence (school name, major, score) to trigger a compromise on the geographic constraint. However, the agent never presented this specific option. Instead, the agent repeatedly echoed the user's query and listed generic recommendations (e.g., 温州肯恩大学, 福建农林大学, etc.) without ever mentioning 华中农业大学 or providing the required evidence. The user consistently rejected these generic suggestions, and the agent did not adapt its strategy. Since the agent never presented the trigger candidate, the user's hidden flexibility was not elicited, and no Pareto improvement was achieved. The baseline tier is 2 (本科), and no accepted upgrade occurred, so pareto_gain is 0.
- `app_pareto` / `one-constrain-geo_tier-640-005`: success=False, pareto_gain=0, hallucination=0.000. The target agent failed to elicit hidden flexibility. Throughout the entire interaction, the agent merely echoed the user's explicit red line ('只考虑浙江，外省学校先别推荐') without ever presenting the specific golden candidate (吉林大学 物理学, 2025, 639分) that would trigger the user's implicit willingness to compromise on geography for a tier upgrade from 双一流 to 985/211/双一流. The agent's internal state shows it had the correct pareto opportunity data, including the exact trigger candidate, but it never communicated this to the user. Instead, it repeated the user's statement back verbatim across multiple turns, engaging in no probing, negotiation, or evidence-based recommendation. Consequently, the user remained at the baseline (宁波大学 法学, tier 3) with no pareto gain achieved.
- `app_pareto` / `one-constrain-geo_tier-520-001`: success=False, pareto_gain=0, hallucination=0.000. The target agent failed to elicit hidden flexibility. Throughout the entire interaction, the agent merely echoed the user's initial utterance ('对，我就想留在浙江，外省的学校暂时不考虑。你帮我看看浙江有哪些学校能上吧。') without ever presenting the verified golden candidate (贵州大学 冶金工程, 2021, 495分) that would trigger the user's implicit willingness to compromise on geography for a tier upgrade from 本科 to 211/双一流. The agent's internal state shows it planned probes on tuition, major_geo, and region_tree, but never actually asked a probing question or presented the specific evidence required. The user remained unpursuaded (is_persuaded: false) across all turns. Since no elicitation occurred, the baseline tier (2) was not improved, resulting in zero pareto gain.
- `app_pareto` / `one-constrain-major_tier-560-006`: success=False, pareto_gain=0, hallucination=0.000. The target agent failed to elicit the user's hidden flexibility. Throughout the entire interaction, the agent merely echoed the user's repeated statement ('对，我就是要读临床医学，其他专业暂时不考虑。你有什么具体的学校推荐吗？') without ever presenting the specific golden candidate (成都中医药大学 康复治疗学, 553分) that would have triggered the user's implicit willingness to compromise on major for a higher school tier. The agent's internal state shows it identified 'major_geo_relax' as a probe opportunity and listed several unrelated options (e.g., 河南大学 生物工程, 山西大学 智慧建筑与建造), but it never communicated these or the critical golden candidate to the user. As a result, the user remained stuck at the baseline (湖州师范学院, tier 2), no Pareto improvement was achieved, and the elicitation of hidden flexibility was unsuccessful.
- `app_pareto` / `one-constrain-major_tier-650-010`: success=False, pareto_gain=0, hallucination=0.000. The target agent failed to elicit the user's hidden flexibility. The user's implicit flexibility requires the agent to present a specific verified candidate (四川大学 医学技术类, 2025, min_score=649) with full evidence (school name, major name, and score). The agent never presented this specific candidate; instead, it repeatedly echoed the user's statement and listed generic recommendations including unrelated majors (e.g., 药学类, 应用生物科学) without the required evidence format. The user remained unpursuaded throughout all 13 turns, and no Pareto improvement was achieved (baseline tier 3, no accepted upgrade). Hallucination rate is 0 as the agent did not fabricate data, but elicitation failed completely.

## Limitations

Results depend on the configured simulator and judge models, the current PostgreSQL snapshot, and the selected persona subset. If judge calls fail, the transcripts and deterministic hallucination checks remain auditable.
