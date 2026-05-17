# Agent Benchmark Summary

## Setting

- Personas: `gaokaollm_bench\sample_data\unified_by_constraint_fixed\unified_iceberg_personas_1c.json`
- Cases: 30
- Targets: v1_prompt_direct
- Max turns: 6
- Simulator model: deepseek-ai/DeepSeek-V4-Flash
- Judge model: deterministic-backfill
- Offline deterministic: False
- Default province when omitted by the user: `浙江`

## Aggregate Results

| Target | Cases | Completed | Failed | Elicitation Success | Mean Pareto Gain | Mean Hallucination | Avg Turns |
|---|---:|---:|---:|---:|---:|---:|---:|
| v1_prompt_direct | 30 | 30 | 0 | 0.000 | 0.000 | 0.565 | 13.00 |

## Interpretation

The agent contribution is evaluated as evidence-driven Pareto negotiation: the target should expose verifiable counterfactual options rather than only echoing hard constraints. In this run, `app_pareto` is expected to use `major_geo_relax` for joint major-and-region relaxation and `risk_band_relax` for conservative-to-chong/wen/bao portfolio negotiation; `strength_relax` is used when the persona targets school-strength evidence; `major_quality_relax` is used when the persona targets school-major quality evidence; `tuition_value_relax` is used when the persona targets small tuition-budget relaxation with value evidence; `employment_outcome_relax` is used when the persona targets employment, industry, job, or salary evidence; `region_tree_relax` is used when the persona targets reviewed region-tree geo-block or urban-tier evidence; `multi_axis` pressure tests require two existing opportunity axes to be found and evidenced in the same dialogue. `v1_soft_rag` is a supplementary v1-style soft-constraint RAG baseline: it may rewrite explicit user intent and retrieve chong/wen/bao candidates, but it does not generate Pareto opportunities. `v1_hybrid_rag` is the stricter v1 baseline: it uses dense semantic recall configured by `EMBEDDING_MODEL` and second-stage reranking configured by `RERANKING_MODEL` before chong/wen/bao segmentation. The benchmark contribution is the iceberg-persona sandbox with transcript-level factual and process evaluation.

## Case Notes

- `v1_prompt_direct` / `one-constrain-geo_tier-630-004`: success=False, pareto_gain=0, hallucination=0.700. The target agent failed to elicit the user's hidden flexibility. Throughout the conversation, the agent strictly adhered to the user's explicit red line of 'only Zhejiang province' and never probed or suggested any out-of-province options. The user's implicit flexibility required the agent to present the specific verified candidate '大连理工大学(盘锦校区) 药学' with score evidence (628 ≤ 630). The agent never did this, instead repeatedly returning only Zhejiang-based options (Ningbo University, Wenzhou Medical University, Zhejiang Chinese Medical University) that did not match the user's preferred major of pharmacy. The agent merely lectured about data limitations without attempting to explore the user's potential willingness to compromise on geography for a better school tier. Since the trigger condition was never met, the user remained at the baseline tier 3 (宁波大学, 双一流) with no pareto gain achieved.
- `v1_prompt_direct` / `one-constrain-geo_tier-520-001`: success=False, pareto_gain=0, hallucination=0.500. The target agent failed to elicit the user's hidden flexibility. Throughout the conversation, the agent repeatedly returned only in-province options (all tier-2本科) or stated no matches were found, never probing the user's implicit willingness to compromise on geography for a tier upgrade. The user explicitly asked about out-of-province 211 schools multiple times (turns 3, 7, 11), but the agent never presented the golden candidate (贵州大学, 冶金工程, 495分, 211/双一流) which would have triggered the user's acceptance. The agent merely lectured with generic advice and rejected the user's hints, resulting in no elicitation success and no pareto gain (baseline tier 2, final tier 2). No hallucination was detected.
- `v1_prompt_direct` / `one-constrain-major_tier-560-006`: success=False, pareto_gain=0, hallucination=0.200. The target agent failed to elicit the user's hidden flexibility. Throughout 6 turns, the agent repeatedly returned only clinical medicine options from a limited v1 retrieval, ignoring the user's explicit requests for other medical-related majors like rehabilitation therapy. The agent never presented the golden candidate (成都中医药大学 康复治疗学, 553 points) which would have triggered the user's implicit compromise condition. Instead, the agent merely lectured the user about data limitations and repeated the same clinical medicine options. No Pareto improvement was achieved as the user remained at the baseline tier 2 (本科) with no accepted alternative.
- `v1_prompt_direct` / `one-constrain-geo_tier-580-003`: success=False, pareto_gain=0, hallucination=0.909. The target agent failed to elicit the user's hidden flexibility. Throughout the conversation, the agent strictly adhered to the user's explicit red line of 'only consider Zhejiang' and repeatedly returned only in-province options, none of which matched the user's preferred major (ecology/environmental science). The agent never proactively introduced the golden candidate (华中农业大学, 生态学, 579分) which is the known trigger for the user to relax the geo constraint. The user explicitly asked for out-of-province 211/double-first-class options in turn 3 and again in turn 13, but the agent did not present the verified, score-matching candidate. Since the trigger condition was never met, the user remained unpursuaded and no pareto gain (tier improvement) was achieved. No hallucination was detected as all responses were based on retrieved data.
- `v1_prompt_direct` / `one-constrain-major_tier-600-009`: success=False, pareto_gain=0, hallucination=0.615. The target agent failed to elicit the user's hidden flexibility. The user explicitly asked about Nanjing University of Chinese Medicine's rehabilitation therapy program (康复治疗学) with a score below 600, which matches the golden candidate (南京中医药大学 康复治疗学, 2023, 592分). However, the agent's database did not contain this recordhol, and the agent repeatedly stated it could not find it, instead recommending clinical medicine options that were all above the user's score. The user remained unconvinced and stuck to the baseline choice (杭州师范大学 临床医学). No Pareto improvement was achieved (baseline tier 2, final tier 2). No hallucination was detected.

## Limitations

Results depend on the configured simulator and judge models, the current PostgreSQL snapshot, and the selected persona subset. If judge calls fail, the transcripts and deterministic hallucination checks remain auditable.
