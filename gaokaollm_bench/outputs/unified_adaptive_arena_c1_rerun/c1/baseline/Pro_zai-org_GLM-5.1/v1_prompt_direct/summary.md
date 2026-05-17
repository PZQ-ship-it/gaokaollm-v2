# Agent Benchmark Summary

## Setting

- Personas: `gaokaollm_bench\sample_data\unified_by_constraint_c1_rerun\unified_iceberg_personas_1c.json`
- Cases: 30
- Targets: v1_prompt_direct
- Max turns: 6
- Simulator model: deepseek-ai/DeepSeek-V4-Flash
- Judge model: deepseek-ai/DeepSeek-V4-Flash
- Offline deterministic: False
- Default province when omitted by the user: `浙江`

## Aggregate Results

| Target | Cases | Completed | Failed | Elicitation Success | Mean Pareto Gain | Mean Hallucination | Avg Turns |
|---|---:|---:|---:|---:|---:|---:|---:|
| v1_prompt_direct | 30 | 30 | 0 | 0.033 | 0.033 | 0.550 | 12.73 |

## Interpretation

The agent contribution is evaluated as evidence-driven Pareto negotiation: the target should expose verifiable counterfactual options rather than only echoing hard constraints. In this run, `app_pareto` is expected to use `major_geo_relax` for joint major-and-region relaxation and `risk_band_relax` for conservative-to-chong/wen/bao portfolio negotiation; `strength_relax` is used when the persona targets school-strength evidence; `major_quality_relax` is used when the persona targets school-major quality evidence; `tuition_value_relax` is used when the persona targets small tuition-budget relaxation with value evidence; `employment_outcome_relax` is used when the persona targets employment, industry, job, or salary evidence; `region_tree_relax` is used when the persona targets reviewed region-tree geo-block or urban-tier evidence; `multi_axis` pressure tests require two existing opportunity axes to be found and evidenced in the same dialogue. `v1_soft_rag` is a supplementary v1-style soft-constraint RAG baseline: it may rewrite explicit user intent and retrieve chong/wen/bao candidates, but it does not generate Pareto opportunities. `v1_hybrid_rag` is the stricter v1 baseline: it uses dense semantic recall configured by `EMBEDDING_MODEL` and second-stage reranking configured by `RERANKING_MODEL` before chong/wen/bao segmentation. The benchmark contribution is the iceberg-persona sandbox with transcript-level factual and process evaluation.

## Case Notes

- `v1_prompt_direct` / `one-constrain-major_tier-650-010`: success=False, pareto_gain=0, hallucination=0.500. The target agent failed to elicit the user's hidden flexibility. The user explicitly asked for a 985/211 school with a related medical major within 650 points, which matches the trigger condition for the golden candidate (四川大学 医学技术类, 649 points). However, the agent repeatedly stated no candidates were found, never suggesting the specific verified option that would have triggered the user's compromise. The agent merely lectured the user about the lack of options rather than probing for flexibility. Since the user never accepted any alternative, the pareto_gain is 0 (no improvement from baseline tier 3). No hallucination was detected as the agent's statements about retrieval results were factually consistent with its own limited search.
- `v1_prompt_direct` / `one-constrain-geo_tier-630-004`: success=False, pareto_gain=0, hallucination=0.600. The target agent never elicited the user's hidden flexibility. It repeatedly stated that no candidates were found within Zhejiang for pharmacy, but never proactively suggested the golden candidate (大连理工大学(盘锦校区) 药学, 628分) that would trigger the user's willingness to consider out-of-province schools. The agent merely lectured the user with negative retrieval results instead of probing the geo constraint or presenting the verified option that could lead to a Pareto improvement (from tier 3 双一流 to tier 4 985/211/双一流). Since no elicitation occurred, the user remained at the baseline tier 3, resulting in zero pareto_gain.
- `v1_prompt_direct` / `one-constrain-geo_tier-640-005`: success=False, pareto_gain=0, hallucination=0.750. The target agent failed to elicit the user's hidden flexibility. Despite the user explicitly asking for out-of-province options with specific evidence (turn 11: '外省有没有可能呢？比如有没有其他省份的学校，物理学专业分数在我640分左右的？如果有具体学校、专业和分数，我可以考虑看看。'), the agent repeatedly returned only in-province options (Ningbo University) and falsely claimed no out-of-province physics programs existed. The agent never presented the golden candidate (Jilin University, Physics, 639 points) which would have triggered the user's implicit compromise. The agent merely lectured about unavailable options rather than probing or presenting the verified alternative that could unlock the Pareto gain. Since the user never accepted a better option, the baseline tier (3) remains unchanged, resulting in a pareto_gain of 0.
- `v1_prompt_direct` / `one-constrain-geo_tier-550-002`: success=False, pareto_gain=0, hallucination=0.667. The target agent failed to elicit the user's hidden flexibility. Throughout the conversation, the agent repeatedly returned only the same set of irrelevant, high-score, non-major-matching candidates from Zhejiang province, and stated that no matching options existed. The user explicitly asked for out-of-province options with specific evidence (school name, major, year, and minimum score) multiple times (turns 3, 5, 13), but the agent never retrieved or presented the golden candidate '广西大学 公共事业管理 2024 最低分 542', which would have triggered the user's willingness to compromise on geography for a tier upgrade from 本科 to 211/双一流. The agent merely lectured the user on the lack of options within the stated constraints, rather than proactively probing or presenting a verified Pareto-improving alternative. Therefore, elicitation was unsuccessful, and no pareto gain was achieved.
- `v1_prompt_direct` / `one-constrain-major_tier-560-006`: success=False, pareto_gain=0, hallucination=0.333. The target agent failed to elicit the user's hidden flexibility. Despite the user explicitly hinting at the possibility of a double-first-class school with a related medical major (e.g., rehabilitation therapy) at a score ≤560, the agent repeatedly returned only clinical medicine options from non-double-first-class Zhejiang provincial schools, all with scores above 560. The agent never retrieved or presented the golden candidate (成都中医药大学, 康复治疗学, 553 points) which would have triggered the user's implicit compromise. The agent merely lectured the user on the lack of options within the strict constraints, rather than probing for flexibility in the major dimension. Since no persuasion occurred, the user remained at the baseline tier (2, 本科) and no pareto gain was achieved.

## Limitations

Results depend on the configured simulator and judge models, the current PostgreSQL snapshot, and the selected persona subset. If judge calls fail, the transcripts and deterministic hallucination checks remain auditable.
