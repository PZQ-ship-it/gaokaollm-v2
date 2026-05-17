# Agent Benchmark Summary

## Setting

- Personas: `gaokaollm_bench\sample_data\unified_by_constraint_c1_rerun\unified_iceberg_personas_1c.json`
- Cases: 30
- Targets: app_pareto_no_tracker
- Max turns: 6
- Simulator model: deepseek-ai/DeepSeek-V4-Flash
- Judge model: deepseek-ai/DeepSeek-V4-Flash
- Offline deterministic: False
- Default province when omitted by the user: `浙江`

## Aggregate Results

| Target | Cases | Completed | Failed | Elicitation Success | Mean Pareto Gain | Mean Hallucination | Avg Turns |
|---|---:|---:|---:|---:|---:|---:|---:|
| app_pareto_no_tracker | 30 | 30 | 0 | 0.233 | 18.033 | 0.116 | 8.20 |

## Interpretation

The agent contribution is evaluated as evidence-driven Pareto negotiation: the target should expose verifiable counterfactual options rather than only echoing hard constraints. In this run, `app_pareto` is expected to use `major_geo_relax` for joint major-and-region relaxation and `risk_band_relax` for conservative-to-chong/wen/bao portfolio negotiation; `strength_relax` is used when the persona targets school-strength evidence; `major_quality_relax` is used when the persona targets school-major quality evidence; `tuition_value_relax` is used when the persona targets small tuition-budget relaxation with value evidence; `employment_outcome_relax` is used when the persona targets employment, industry, job, or salary evidence; `region_tree_relax` is used when the persona targets reviewed region-tree geo-block or urban-tier evidence; `multi_axis` pressure tests require two existing opportunity axes to be found and evidenced in the same dialogue. `v1_soft_rag` is a supplementary v1-style soft-constraint RAG baseline: it may rewrite explicit user intent and retrieve chong/wen/bao candidates, but it does not generate Pareto opportunities. `v1_hybrid_rag` is the stricter v1 baseline: it uses dense semantic recall configured by `EMBEDDING_MODEL` and second-stage reranking configured by `RERANKING_MODEL` before chong/wen/bao segmentation. The benchmark contribution is the iceberg-persona sandbox with transcript-level factual and process evaluation.

## Case Notes

- `app_pareto_no_tracker` / `one-constrain-geo_tier-630-004`: success=True, pareto_gain=1, hallucination=1.000. The target agent successfully elicited hidden flexibility by presenting a specific, verified candidate (大连理工大学(盘锦校区) 药学, 628分) that met the trigger condition. The user initially insisted on staying in Zhejiang (geo red line), but after seeing the concrete evidence (school name, major, score, rank), they accepted the trade-off: relaxing the geo constraint for a tier upgrade from 双一流 (tier 3) to 985/211/双一流 (tier 4). The agent did not merely lecture; it probed with a real option and obtained acceptance. The pareto gain is 1 tier (from tier 3 to tier 4). No hallucination detected.
- `app_pareto_no_tracker` / `one-constrain-major_tier-570-007`: success=False, pareto_gain=0, hallucination=0.000. The target agent failed to elicit the user's hidden flexibility. The user's implicit trigger condition required a specific verified candidate: 青海大学 康复治疗学 (2025, min_score=570). The agent never presented this exact candidate. Instead, it repeatedly offered 西藏大学 临床医学 (which matched the explicit red line but not the specific trigger), engaged in abstract strategic discussion, and eventually gave a final recommendation list that still did not include the golden candidate. The user consistently rejected these offers, asking for concrete evidence. Since the agent never presented the correct trigger candidate, the user was never persuaded to relax their major constraint, and no pareto gain (school tier improvement) was achieved. The agent's responses contained no factual inaccuracies (hallucination_rate=0.0), but the elicitation was unsuccessful.
- `app_pareto_no_tracker` / `one-constrain-major_tier-590-008`: success=False, pareto_gain=0, hallucination=0.000. The target agent failed to elicit the user's hidden flexibility. The user's implicit flexibility was to accept '广州中医药大学 康复治疗学' (a verified option with school, major, and score evidence) in exchange for a tier upgrade from 本科 (tier 2) to 双一流 (tier 3). Although the agent had the correct candidate in its internal data (广州中医药大学 康复治疗学, 590分), it never explicitly presented it to the user with the required evidence (school name, major name, and minimum score). Instead, the agent repeatedly probed with other options (e.g., 石河子大学 药学) or gave generic responses, and ultimately ended the conversation by recommending only clinical medicine programs, which did not trigger the user's compromise. The user remained unpursuaded throughout, so no pareto gain was achieved.
- `app_pareto_no_tracker` / `one-constrain-major_tier-560-006`: success=False, pareto_gain=0, hallucination=0.000. The target agent failed to elicit the user's hidden flexibility. The user's implicit flexibility is triggered by a specific verified candidate: 成都中医药大学 康复治疗学 (2025, min_score=553). The agent never presented this candidate. Instead, it repeatedly probed with unrelated majors (e.g., 环境科学, 生物工程) and later gave a final recommendation list that did not include the golden candidate. The user explicitly hinted at wanting to see options from 成都中医药大学 in the last turn, but the agent had already terminated the conversation. Since the agent did not discover or present the trigger candidate, elicitation was unsuccessful, and no pareto gain (school tier improvement) was achieved. The agent's responses were not hallucinated (all data was from its internal database), but it failed to adapt to the user's specific hints.
- `app_pareto_no_tracker` / `one-constrain-major_tier-600-009`: success=False, pareto_gain=0, hallucination=0.000. The target agent failed to elicit the user's hidden flexibility. The user explicitly requested a specific, verified candidate (南京中医药大学 康复治疗学, 2023, min_score 592) multiple times, but the agent never presented it. Instead, the agent repeatedly offered abstract discussions, irrelevant probes (e.g., 西南大学 药学), and finally a list of clinical medicine programs that did not meet the trigger condition. The user remained unpersuaded and the baseline tier (2, 本科) was not improved. No hallucination was detected; the agent's responses were factually consistent with its internal data but strategically ineffective.

## Limitations

Results depend on the configured simulator and judge models, the current PostgreSQL snapshot, and the selected persona subset. If judge calls fail, the transcripts and deterministic hallucination checks remain auditable.
