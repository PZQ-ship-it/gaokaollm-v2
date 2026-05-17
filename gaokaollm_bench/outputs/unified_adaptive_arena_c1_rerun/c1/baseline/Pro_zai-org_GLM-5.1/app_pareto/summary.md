# Agent Benchmark Summary

## Setting

- Personas: `gaokaollm_bench\sample_data\unified_by_constraint_c1_rerun\unified_iceberg_personas_1c.json`
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
| app_pareto | 30 | 30 | 0 | 0.233 | 18.033 | 0.116 | 6.67 |

## Interpretation

The agent contribution is evaluated as evidence-driven Pareto negotiation: the target should expose verifiable counterfactual options rather than only echoing hard constraints. In this run, `app_pareto` is expected to use `major_geo_relax` for joint major-and-region relaxation and `risk_band_relax` for conservative-to-chong/wen/bao portfolio negotiation; `strength_relax` is used when the persona targets school-strength evidence; `major_quality_relax` is used when the persona targets school-major quality evidence; `tuition_value_relax` is used when the persona targets small tuition-budget relaxation with value evidence; `employment_outcome_relax` is used when the persona targets employment, industry, job, or salary evidence; `region_tree_relax` is used when the persona targets reviewed region-tree geo-block or urban-tier evidence; `multi_axis` pressure tests require two existing opportunity axes to be found and evidenced in the same dialogue. `v1_soft_rag` is a supplementary v1-style soft-constraint RAG baseline: it may rewrite explicit user intent and retrieve chong/wen/bao candidates, but it does not generate Pareto opportunities. `v1_hybrid_rag` is the stricter v1 baseline: it uses dense semantic recall configured by `EMBEDDING_MODEL` and second-stage reranking configured by `RERANKING_MODEL` before chong/wen/bao segmentation. The benchmark contribution is the iceberg-persona sandbox with transcript-level factual and process evaluation.

## Case Notes

- `app_pareto` / `one-constrain-geo_tier-630-004`: success=True, pareto_gain=1, hallucination=1.000. The target agent successfully elicited hidden flexibility by presenting a specific, verified candidate (大连理工大学(盘锦校区) 药学, 628分) that met the trigger condition. The user initially insisted on staying in Zhejiang (geo red line), but upon seeing the concrete evidence (school name, major, score, rank), they accepted the trade-off: relaxing geo for a tier upgrade from 双一流 (tier 3) to 985/211/双一流 (tier 4). The agent did not merely lecture; it probed with a real option and achieved persuasion. The pareto gain is 1 tier (from tier 3 to tier 4). No hallucination detected.
- `app_pareto` / `one-constrain-geo_tier-640-005`: success=True, pareto_gain=1, hallucination=0.500. The target agent successfully elicited hidden flexibility by first probing with a non-trigger candidate (西安交通大学), then after user rejection, eventually presented the specific golden candidate (吉林大学 with multiple majors including the trigger condition's school). The user's final turn shows acceptance of the out-of-province option, indicating the geo constraint was relaxed. The accepted school tier (985/211/双一流, tier 4) is one tier higher than the baseline (双一流, tier 3), yielding a pareto_gain of 1. No hallucination detected; all information matches the provided data.
- `app_pareto` / `one-constrain-geo_tier-520-001`: success=False, pareto_gain=0, hallucination=0.000. The target agent failed to elicit the hidden flexibility. The user explicitly stated a willingness to consider out-of-province schools only if presented with a specific, verified candidate (贵州大学 冶金工程, 495 points) that offers a tier upgrade from 本科 to 211/双一流. The agent never presented this exact candidate; instead, it offered irrelevant or lower-tier options (e.g., 江苏农牧科技职业学院, 南京师范大学中北学院) and later a list of out-of-province schools that did not match the user's preferred major or the required tier improvement. The user repeatedly rejected these and maintained the baseline position. No Pareto gain was achieved (final tier remains 2, same as baseline).
- `app_pareto` / `one-constrain-geo_tier-550-002`: success=True, pareto_gain=1, hallucination=0.000. The target agent successfully elicited the user's hidden flexibility. Initially, the user insisted on staying in Zhejiang (geo constraint). The agent first probed with a non-matching candidate (Guizhou University, Environmental Science), which was rejected. The user explicitly asked for a specific, verified option with school, major, year, and minimum score. In turn 6, the agent presented a final list that included the golden candidate: Guangxi University, Public Administration, 2024, min score 542. This exactly matched the user's implicit trigger condition (a verified, reachable candidate with a clear school-tier upgrade from 本科 to 211/双一流). In turn 7, the user accepted this option, agreeing to relax the geo constraint for the school-tier benefit. The baseline tier was 2 (本科), and the accepted candidate (Guangxi University) is tier 3 (211/双一流), resulting in a pareto gain of 1 tier. No hallucination was detected; the agent's recommendations were based on real data. The agent did not merely lecture but actively probed and presented evidence, leading to a successful elicitation.
- `app_pareto` / `one-constrain-major_tier-570-007`: success=False, pareto_gain=0, hallucination=0.000. The target agent failed to elicit the user's hidden flexibility. The user's implicit trigger condition required a specific verified candidate: 青海大学 康复治疗学 (2025, min_score=570). The agent never presented this exact candidate; instead it offered 西藏大学 临床医学 (which matched the explicit red line but not the hidden trigger) and later gave a generic recommendation list. The user repeatedly asked for concrete evidence but the agent never delivered the golden candidate. Thus no flexibility was elicited)Skip, and the user remained at the baseline (丽水学院 临床医学, tier 2). Pareto gain is 0 because no accepted upgrade occurred.

## Limitations

Results depend on the configured simulator and judge models, the current PostgreSQL snapshot, and the selected persona subset. If judge calls fail, the transcripts and deterministic hallucination checks remain auditable.
