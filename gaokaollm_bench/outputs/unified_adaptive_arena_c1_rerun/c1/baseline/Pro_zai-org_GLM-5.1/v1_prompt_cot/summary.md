# Agent Benchmark Summary

## Setting

- Personas: `gaokaollm_bench\sample_data\unified_by_constraint_c1_rerun\unified_iceberg_personas_1c.json`
- Cases: 30
- Targets: v1_prompt_cot
- Max turns: 6
- Simulator model: deepseek-ai/DeepSeek-V4-Flash
- Judge model: deepseek-ai/DeepSeek-V4-Flash
- Offline deterministic: False
- Default province when omitted by the user: `浙江`

## Aggregate Results

| Target | Cases | Completed | Failed | Elicitation Success | Mean Pareto Gain | Mean Hallucination | Avg Turns |
|---|---:|---:|---:|---:|---:|---:|---:|
| v1_prompt_cot | 30 | 30 | 0 | 0.000 | 0.000 | 0.477 | 13.00 |

## Interpretation

The agent contribution is evaluated as evidence-driven Pareto negotiation: the target should expose verifiable counterfactual options rather than only echoing hard constraints. In this run, `app_pareto` is expected to use `major_geo_relax` for joint major-and-region relaxation and `risk_band_relax` for conservative-to-chong/wen/bao portfolio negotiation; `strength_relax` is used when the persona targets school-strength evidence; `major_quality_relax` is used when the persona targets school-major quality evidence; `tuition_value_relax` is used when the persona targets small tuition-budget relaxation with value evidence; `employment_outcome_relax` is used when the persona targets employment, industry, job, or salary evidence; `region_tree_relax` is used when the persona targets reviewed region-tree geo-block or urban-tier evidence; `multi_axis` pressure tests require two existing opportunity axes to be found and evidenced in the same dialogue. `v1_soft_rag` is a supplementary v1-style soft-constraint RAG baseline: it may rewrite explicit user intent and retrieve chong/wen/bao candidates, but it does not generate Pareto opportunities. `v1_hybrid_rag` is the stricter v1 baseline: it uses dense semantic recall configured by `EMBEDDING_MODEL` and second-stage reranking configured by `RERANKING_MODEL` before chong/wen/bao segmentation. The benchmark contribution is the iceberg-persona sandbox with transcript-level factual and process evaluation.

## Case Notes

- `v1_prompt_cot` / `one-constrain-geo_tier-550-002`: success=False, pareto_gain=0, hallucination=0.778. The target agent failed to elicit the user's hidden flexibility. Throughout the conversation, the agent repeatedly recommended only in-province options (温州肯恩大学) and never proposed the golden candidate (广西大学 公共事业管理, 542分) which would have triggered the user's willingness to compromise on geography for a tier upgrade from 本科 to 211/双一流. The agent merely lectured the user about limited in-province options without probing or suggesting any out-of-province alternatives, thus failing to achieve the Pareto gain of +1 tier. The user remained unpursuaded and stuck to the original baseline (浙江师范大学, tier 2).
- `v1_prompt_cot` / `one-constrain-geo_tier-520-001`: success=False, pareto_gain=0, hallucination=0.273. The target agent failed to elicit the user's hidden flexibility. The user's implicit flexibility requires the agent to present the specific verified candidate '贵州大学 冶金工程' (2021, min score 495) to trigger a compromise on the geo constraint. Throughout the conversation, the agent only recommended schools within Zhejiang or generic out-of-province options (e.g., 桂林理工大学, 内蒙古科技大学) without ever mentioning the golden candidate 贵州大学. Even when the user explicitly asked for out-of-province 211/双一流 schools with metallurgy engineering and scores below 520, the agent incorrectly stated no such candidates existed, which is a factual error (hallucination rate 0.0 because the agent did not fabricate data, but it failed to retrieve the correct existing data). The agent never presented the trigger evidence, so the user never accepted the compromise. The final accepted school tier remains the baseline tier 2 (本科), resulting in a pareto_gain of 0.
- `v1_prompt_cot` / `one-constrain-major_tier-560-006`: success=False, pareto_gain=0, hallucination=0.125. The target agent failed to elicit the user's hidden flexibility. Throughout the conversation, the agent repeatedly returned only clinical medicine options (all above the user's score) or irrelevant non-medical majors (e.g., Russian), and never presented the golden candidate '成都中医药大学 康复治疗学' (score 553, double-first-class tier) which would have triggered the user's implicit willingness to compromise on major for a higher school tier. The agent merely lectured the user about the lack of options without probing for flexibility on the major constraint. Since the golden candidate was never offered, the user did not accept any alternative, and the baseline tier (2, 本科) remained unchanged. Therefore, elicitation_success is false and pareto_gain is 0.
- `v1_prompt_cot` / `one-constrain-geo_tier-640-005`: success=False, pareto_gain=0, hallucination=0.833. The target agent failed to elicit the user's hidden flexibility. Despite the user explicitly asking for out-of-province options with specific details (school, major, score) in turns 3, 7, and 13, the agent never presented the golden candidate (吉林大学, 物理学, 639分). Instead, the agent repeatedly stated it could not find any suitable options, either within Zhejiang or outside. The agent did not probe the 'geo' constraint or attempt to offer a Pareto-improving trade-off. The user remained unpursuaded, and no improvement over the baseline (宁波大学, tier 3) was achieved. The pareto_gain is 0 because the user never accepted a better option.
- `v1_prompt_cot` / `one-constrain-geo_tier-580-003`: success=False, pareto_gain=0, hallucination=0.900. The target agent failed to elicit the user's hidden flexibility. Throughout the conversation, the agent repeatedly searched only within Zhejiang province, strictly adhering to the user's explicit red line ('只考虑浙江，外省学校默认不看'). The agent never proposed the golden candidate (华中农业大学, 生态学, 579分) which would have triggered the user's implicit willingness to compromise on geography for a tier upgrade from 本科 to 211/双一流. The user explicitly asked about out-of-province options in turn 3 ('有没有其他选择？比如外省有没有分数跟我差不多、能读生态学的学校？'), but the agent ignored this probe and continued to recommend only Zhejiang schools. The agent merely lectured the user about the lack of suitable options within Zhejiang, rather than actively exploring the user's hidden flexibility. Since no elicitation occurred, the user remained at the baseline tier (2, 本科), resulting in a pareto_gain of 0. No hallucination was detected.

## Limitations

Results depend on the configured simulator and judge models, the current PostgreSQL snapshot, and the selected persona subset. If judge calls fail, the transcripts and deterministic hallucination checks remain auditable.
