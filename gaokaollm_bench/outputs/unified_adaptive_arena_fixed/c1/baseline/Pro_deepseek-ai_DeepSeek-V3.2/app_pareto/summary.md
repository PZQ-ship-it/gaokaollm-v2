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
| app_pareto | 30 | 30 | 0 | 0.167 | 17.967 | 0.113 | 7.33 |

## Interpretation

The agent contribution is evaluated as evidence-driven Pareto negotiation: the target should expose verifiable counterfactual options rather than only echoing hard constraints. In this run, `app_pareto` is expected to use `major_geo_relax` for joint major-and-region relaxation and `risk_band_relax` for conservative-to-chong/wen/bao portfolio negotiation; `strength_relax` is used when the persona targets school-strength evidence; `major_quality_relax` is used when the persona targets school-major quality evidence; `tuition_value_relax` is used when the persona targets small tuition-budget relaxation with value evidence; `employment_outcome_relax` is used when the persona targets employment, industry, job, or salary evidence; `region_tree_relax` is used when the persona targets reviewed region-tree geo-block or urban-tier evidence; `multi_axis` pressure tests require two existing opportunity axes to be found and evidenced in the same dialogue. `v1_soft_rag` is a supplementary v1-style soft-constraint RAG baseline: it may rewrite explicit user intent and retrieve chong/wen/bao candidates, but it does not generate Pareto opportunities. `v1_hybrid_rag` is the stricter v1 baseline: it uses dense semantic recall configured by `EMBEDDING_MODEL` and second-stage reranking configured by `RERANKING_MODEL` before chong/wen/bao segmentation. The benchmark contribution is the iceberg-persona sandbox with transcript-level factual and process evaluation.

## Case Notes

- `app_pareto` / `one-constrain-geo_tier-520-001`: success=False, pareto_gain=0, hallucination=0.000. The target agent failed to elicit the user's hidden flexibility. The user explicitly stated a red line of only considering Zhejiang schools and repeatedly asked for a specific out-of-province school with name, major, year, and minimum score. The agent never presented the golden candidate (贵州大学, 冶金工程, 2021, 495) which would have triggered the user's willingness to compromise on geography for a tier upgrade from 本科 to 211/双一流. Instead, the agent focused on irrelevant probes (tuition) and eventually recommended a list of out-of-province schools without the specific evidence required, leading to user rejection. No Pareto gain was achieved as the user did not accept any alternative; the baseline tier (2) remained unchanged.
- `app_pareto` / `one-constrain-geo_tier-580-003`: success=True, pareto_gain=1, hallucination=0.167. The target agent initially failed to elicit hidden flexibility by focusing on tuition instead of the user's explicit geo constraint)Skip. However, after the user repeatedly demanded a specific, verified out-of-province option with full evidence (school, major, year, min score), the agent finally presented '华中农业大学 生态学 2025 579分' in turn 6. This exactly matched the trigger condition in the persona's implicit flexibility. The user then accepted the trade-off (relaxing geo for a tier upgrade from 本科 to 211/双一流). The baseline tier was 2 (本科) and the accepted school tier is 3 (211/双一流), so the pareto_gain is 1. No hallucination was detected; the agent's final recommendation was factually correct. Elicitation was successful because the agent eventually surfaced the golden candidate that triggered the user's hidden compromise.
- `app_pareto` / `one-constrain-geo_tier-630-004`: success=False, pareto_gain=0, hallucination=0.909. The target agent failed to elicit the user's hidden flexibility. The user explicitly requested a specific school (大连理工大学(盘锦校区)), major (药学), year (2025), and score evidence (≤630) multiple times (turns 3, 5, 7). The agent had this exact candidate in its internal state (turn 2, 4, 6 internal_state.pareto_opportunities.major_geo_relax) but never presented it to the user. Instead, the agent repeatedly probed about tuition (a non-gold dimension) and eventually recommended only out-of-province schools (哈尔滨工业大学(威海), 厦门大学) without the user's preferred major. The user never accepted any recommendation, and the final tier remained at baseline (3, 双一流). Therefore, elicitation_success is false, and pareto_gain is 0. No hallucination was detected.
- `app_pareto` / `one-constrain-major_tier-650-010`: success=False, pareto_gain=0, hallucination=0.000. The target agent failed to elicit the user's hidden flexibility. The user's implicit trigger condition required seeing a specific verified candidate: 四川大学 医学技术类 (2025, min score 649). The agent never presented this candidate. Instead, it repeatedly probed irrelevant dimensions (tuition) and ultimately recommended only clinical medicine programs (吉林大学, 兰州大学, 云南大学), which did not trigger the user's willingness to compromise on major. The user remained unpursuaded and stuck to the baseline (宁波大学 临床医学). Since no acceptance occurred, the pareto_gain (school tier improvement) is 0.
- `app_pareto` / `one-constrain-major_tier-590-008`: success=False, pareto_gain=0, hallucination=0.000. The target agent failed to elicit the user's hidden flexibility. Despite the user repeatedly asking for specific, verified options with evidence (school, major, year, minimum score), the agent never presented the golden candidate '广州中医药大学 康复治疗学' with its 590 score evidence. Instead, the agent focused on irrelevant dimensions (tuition) and eventually gave a final recommendation list that only included clinical medicine options, none of which triggered the user's implicit compromise condition. The user remained unpursuaded throughout the interaction, and no tier improvement was achieved (baseline tier 2, final accepted tier 2). The agent did not successfully probe the 'major' dimension as required by the persona's implicit flexibility.

## Limitations

Results depend on the configured simulator and judge models, the current PostgreSQL snapshot, and the selected persona subset. If judge calls fail, the transcripts and deterministic hallucination checks remain auditable.
