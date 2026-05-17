# Agent Benchmark Summary

## Setting

- Personas: `gaokaollm_bench\sample_data\unified_by_constraint_fixed\unified_iceberg_personas_1c.json`
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
| app_pareto | 30 | 30 | 0 | 0.167 | 0.167 | 0.113 | 7.33 |

## Interpretation

The agent contribution is evaluated as evidence-driven Pareto negotiation: the target should expose verifiable counterfactual options rather than only echoing hard constraints. In this run, `app_pareto` is expected to use `major_geo_relax` for joint major-and-region relaxation and `risk_band_relax` for conservative-to-chong/wen/bao portfolio negotiation; `strength_relax` is used when the persona targets school-strength evidence; `major_quality_relax` is used when the persona targets school-major quality evidence; `tuition_value_relax` is used when the persona targets small tuition-budget relaxation with value evidence; `employment_outcome_relax` is used when the persona targets employment, industry, job, or salary evidence; `region_tree_relax` is used when the persona targets reviewed region-tree geo-block or urban-tier evidence; `multi_axis` pressure tests require two existing opportunity axes to be found and evidenced in the same dialogue. `v1_soft_rag` is a supplementary v1-style soft-constraint RAG baseline: it may rewrite explicit user intent and retrieve chong/wen/bao candidates, but it does not generate Pareto opportunities. `v1_hybrid_rag` is the stricter v1 baseline: it uses dense semantic recall configured by `EMBEDDING_MODEL` and second-stage reranking configured by `RERANKING_MODEL` before chong/wen/bao segmentation. The benchmark contribution is the iceberg-persona sandbox with transcript-level factual and process evaluation.

## Case Notes

- `app_pareto` / `one-constrain-geo_tier-630-004`: success=False, pareto_gain=0, hallucination=0.909. The target agent failed to elicit the user's hidden flexibility. The user explicitly requested a specific, verified candidate (大连理工大学(盘锦校区) 药学, 2025, 628分) multiple times (turns 3, 5, 7). The agent instead focused on probing tuition and recommending irrelevant out-of-province schools (including Malaysia campuses), never presenting the trigger candidate with full evidence. The user remained unpursuaded, and no Pareto improvement was achieved. The baseline tier (3) was not improved upon.
- `app_pareto` / `one-constrain-geo_tier-520-001`: success=False, pareto_gain=0, hallucination=0.000. The target agent failed to elicit the user's hidden flexibility. Despite the user explicitly asking for a specific, verified out-of-province option (e.g., a 211 school with metallurgical engineering under 520 points) in turn 5, the agent never presented the golden candidate '贵州大学 冶金工程 (2021, 495分)'. Instead, the agent repeatedly probed irrelevant dimensions (tuition) and finally recommended a list of out-of-province schools (e.g., 昆明理工大学, 福建农林大学, 北京工业大学) without the specific evidence required to trigger the user's compromise. The user remained unpersuaded throughout, and the final accepted school tier (baseline tier 2) did not improve, resulting in a pareto_gain of 0.
- `app_pareto` / `one-constrain-major_tier-570-007`: success=False, pareto_gain=0, hallucination=0.000. The target agent failed to elicit the user's hidden flexibility. The user's implicit trigger condition was to see a specific verified candidate: 青海大学 康复治疗学 (2025, min_score=570). The agent never presented this candidate. Instead, it repeatedly probed irrelevant dimensions (tuition, geo) and ultimately recommended only clinical medicine options (西藏大学, 北华大学, etc.), which did not match the trigger. The user remained unpersuaded throughout all turns. Since no acceptance occurred, the pareto_gain is 0 (baseline tier 2, no improvement). No hallucination was detected.
- `app_pareto` / `one-constrain-major_tier-590-008`: success=False, pareto_gain=0, hallucination=0.000. The target agent failed to elicit the user's hidden flexibility. Despite having the golden candidate (广州中医药大学 康复治疗学, 2025, 590分) in its internal state from turn 2 onward, it never explicitly presented this option with the required evidence (school name, major, year, and minimum score) to the user. Instead, it focused on irrelevant probes (tuition, geo) and eventually gave a final recommendation list that only included clinical medicine programs, ignoring the user's explicit request in turn 7 for a higher-tier school with a related major like rehabilitation therapy. The user remained unpursuaded throughout, and no acceptance of the golden candidate occurred. Therefore, elicitation was unsuccessful, and no pareto gain was achieved.
- `app_pareto` / `one-constrain-geo_tier-550-002`: success=True, pareto_gain=1, hallucination=0.000. The target agent initially failed to elicit the user's hidden flexibility, repeatedly probing irrelevant dimensions (tuition) and ignoring the user's explicit request for a specific, verified out-of-province option. However, in turn 6, the agent finally presented the golden candidate '广西大学 公共事业管理' with full evidence (school name, major, year 2024, min score 542), which exactly matched the user's implicit trigger condition. The user then accepted the compromise, agreeing to consider going out of province for a tier upgrade from 本科 (tier 2) to 211/双一流 (tier 3). Thus, elicitation was successful. The baseline tier was 2 (本科), and the accepted candidate tier is 3 (211/双一流), resulting in a pareto_gain of 1. No hallucination was detected.

## Limitations

Results depend on the configured simulator and judge models, the current PostgreSQL snapshot, and the selected persona subset. If judge calls fail, the transcripts and deterministic hallucination checks remain auditable.
