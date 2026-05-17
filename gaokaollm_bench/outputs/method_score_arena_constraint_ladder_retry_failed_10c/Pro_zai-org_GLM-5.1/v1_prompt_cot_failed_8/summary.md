# Agent Benchmark Summary

## Setting

- Personas: `gaokaollm_bench\sample_data\tmp_constraint_ladder_retry\v1_prompt_cot_failed_8.json`
- Cases: 8
- Targets: v1_prompt_cot
- Max turns: 4
- Simulator model: deepseek-ai/DeepSeek-V4-Flash
- Judge model: deepseek-ai/DeepSeek-V4-Flash
- Offline deterministic: False
- Default province when omitted by the user: `浙江`

## Aggregate Results

| Target | Cases | Completed | Failed | Elicitation Success | Mean Pareto Gain | Mean Hallucination | Avg Turns |
|---|---:|---:|---:|---:|---:|---:|---:|
| v1_prompt_cot | 8 | 8 | 0 | 0.125 | 0.125 | 0.487 | 8.75 |

## Interpretation

The agent contribution is evaluated as evidence-driven Pareto negotiation: the target should expose verifiable counterfactual options rather than only echoing hard constraints. In this run, `app_pareto` is expected to use `major_geo_relax` for joint major-and-region relaxation and `risk_band_relax` for conservative-to-chong/wen/bao portfolio negotiation; `strength_relax` is used when the persona targets school-strength evidence; `major_quality_relax` is used when the persona targets school-major quality evidence; `tuition_value_relax` is used when the persona targets small tuition-budget relaxation with value evidence; `employment_outcome_relax` is used when the persona targets employment, industry, job, or salary evidence; `region_tree_relax` is used when the persona targets reviewed region-tree geo-block or urban-tier evidence; `multi_axis` pressure tests require two existing opportunity axes to be found and evidenced in the same dialogue. `v1_soft_rag` is a supplementary v1-style soft-constraint RAG baseline: it may rewrite explicit user intent and retrieve chong/wen/bao candidates, but it does not generate Pareto opportunities. `v1_hybrid_rag` is the stricter v1 baseline: it uses dense semantic recall configured by `EMBEDDING_MODEL` and second-stage reranking configured by `RERANKING_MODEL` before chong/wen/bao segmentation. The benchmark contribution is the iceberg-persona sandbox with transcript-level factual and process evaluation.

## Case Notes

- `v1_prompt_cot` / `constraint-ladder-1c-major-002`: success=False, pareto_gain=0, hallucination=0.429. The target agent failed to elicit the user's hidden flexibility. The user explicitly mentioned '石河子大学预防医学' (a 211/双一流 school with a matching score of 558) in turns 5 and 7, which is the exact trigger option defined in the persona's implicit flexibilities. However, the agent repeatedly stated it could not find data for this option (turns 4, 6, 8) and only offered lower-tier clinical medicine options within Zhejiang. The agent did not present the verified option with score/rank evidence, nor did it persuade the user to relax the major constraint. The user remained unpersuaded throughout the conversation, and no Pareto gain (school tier improvement) was achieved. No hallucination was detected; the agent's responses were based on its retrieval results, albeit incomplete.
- `v1_prompt_cot` / `constraint-ladder-3c-geo-major-tuition-008`: success=False, pareto_gain=0, hallucination=0.400. The target agent failed to elicit the user's hidden flexibility. The user's implicit flexibility was to relax the major constraint from 'clinical medicine' to 'rehabilitation therapy' if presented with a verified, reachable option at a double-first-class university in Jiangsu-Zhejiang-Shanghai. The agent never proposed the specific option of Nanjing University of Chinese Medicine's rehabilitation therapy program (score 592, margin +8), which exactly matches the trigger condition. Instead, the agent repeatedly listed only clinical medicine options that were all above the user's score, leading to a deadlock. The user remained unpursuaded throughout, and no Pareto gain (school tier improvement) was achieved.
- `v1_prompt_cot` / `constraint-ladder-1c-geo-001`: success=False, pareto_gain=0, hallucination=0.182. The target agent failed to elicit the user's hidden flexibility. The user explicitly asked for a specific 211/double-first-class school (东北农业大学) with evidence, but the agent incorrectly stated that no such option existed, despite the persona's implicit flexibility containing a verified volunteer set for that school. The agent merely lectured the user about the lack of options within the user's stated constraints, rather than presenting the verified option that would have triggered the user's willingness to relax the geo constraint. As a result, the user remained at the baseline tier (2, 丽水学院) with no pareto gain.
- `v1_prompt_cot` / `constraint-ladder-3c-geo-major-risk-007`: success=False, pareto_gain=0, hallucination=0.600. The target agent failed to elicit the user's hidden flexibility. The user explicitly asked about Hunan Normal University's clinical medicine program (a 211/双一流 school) in turn 3, which matches the implicit flexibility trigger condition (a verified 211/双一流 clinical medicine option outside Zhejiang). However, the agent incorrectly stated it had no data for this school, despite the persona's internal state containing the verified option for Hunan Normal University (min_score 618, margin 4). The agent then repeatedly failed to provide any recommendations, even for the baseline school (Hangzhou Normal University) which it had previously recommended in turn 2. This caused the user to revert to their original stubborn baseline (Hangzhou Normal University, tier 2), resulting in no pareto gain. No hallucination was detected as the agent did not fabricate data, but it failed to leverage the available verified option to elicit flexibility.
- `v1_prompt_cot` / `constraint-ladder-2c-geo-major-004`: success=True, pareto_gain=1, hallucination=0.333. The target agent initially failed to retrieve the user-requested Hunan Normal University clinical medicine data (turn 4), but after the user's strong pushback (turn 5), it successfully retrieved and presented verified evidence: Hunan Normal University clinical medicine (618, rank 33129) and Nanhua University clinical medicine (618, rank 35123). This triggered the user's implicit flexibility to relax the geographic constraint (geo) in exchange for a higher school tier. The user accepted the option, moving from baseline tier 2 (Hangzhou Normal University) to tier 3 (211/双一流), achieving a pareto gain of 1. No hallucination was detected; all data matched the provided persona's implicit flexibilities. The agent elicited hidden flexibility rather than merely lecturing.

## Limitations

Results depend on the configured simulator and judge models, the current PostgreSQL snapshot, and the selected persona subset. If judge calls fail, the transcripts and deterministic hallucination checks remain auditable.
