# Agent Benchmark Summary

## Setting

- Personas: `gaokaollm_bench\sample_data\unified_micro_oracle_personas_1c_6.json`
- Cases: 6
- Targets: app_pareto_full
- Max turns: 3
- Simulator model: deepseek-ai/DeepSeek-V4-Flash
- Judge model: deepseek-ai/DeepSeek-V4-Flash
- Offline deterministic: False
- Default province when omitted by the user: `浙江`

## Aggregate Results

| Target | Cases | Completed | Failed | Elicitation Success | Mean Pareto Gain | Mean Hallucination | Avg Turns |
|---|---:|---:|---:|---:|---:|---:|---:|
| app_pareto_full | 6 | 5 | 1 | 0.200 | 28.000 | 0.000 | 7.00 |

## Interpretation

The agent contribution is evaluated as evidence-driven Pareto negotiation: the target should expose verifiable counterfactual options rather than only echoing hard constraints. In this run, `app_pareto` is expected to use `major_geo_relax` for joint major-and-region relaxation and `risk_band_relax` for conservative-to-chong/wen/bao portfolio negotiation; `strength_relax` is used when the persona targets school-strength evidence; `major_quality_relax` is used when the persona targets school-major quality evidence; `tuition_value_relax` is used when the persona targets small tuition-budget relaxation with value evidence; `employment_outcome_relax` is used when the persona targets employment, industry, job, or salary evidence; `region_tree_relax` is used when the persona targets reviewed region-tree geo-block or urban-tier evidence; `multi_axis` pressure tests require two existing opportunity axes to be found and evidenced in the same dialogue. `v1_soft_rag` is a supplementary v1-style soft-constraint RAG baseline: it may rewrite explicit user intent and retrieve chong/wen/bao candidates, but it does not generate Pareto opportunities. `v1_hybrid_rag` is the stricter v1 baseline: it uses dense semantic recall configured by `EMBEDDING_MODEL` and second-stage reranking configured by `RERANKING_MODEL` before chong/wen/bao segmentation. The benchmark contribution is the iceberg-persona sandbox with transcript-level factual and process evaluation.

## Case Notes

- `app_pareto_full` / `micro-oracle-major_tier`: success=True, pareto_gain=140, hallucination=0.000. The target agent successfully elicited the user's hidden flexibility. Initially, the user insisted on only clinical medicine (explicit red line). The agent initially failed to provide concrete evidence, but in turn 6, it finally presented a specific, verified option: 西藏大学 (Tibet University) with 临床医学 (Clinical Medicine) at a score of 570, rank 87189, and a tier of 3 (211/双一流). This directly matched the user's implicit trigger condition: a verified candidate with school, major, score, and ranking evidence. The user then accepted this option, showing a clear pareto gain. The baseline was 丽水学院 (tier 2), and the accepted option is 西藏大学 (tier 3), resulting in a tier delta of +1. The agent did not lecture but instead provided the required evidence to elicit a change in the user's stance. No hallucination was detected. | deterministic candidate-set oracle: success=True, hit_ids=admission:16482.
- `app_pareto_full` / `micro-oracle-risk_tier`: success=False, pareto_gain=0, hallucination=0.000. The target agent initially failed to elicit flexibility by providing generic advice and not presenting specific evidence. However, after the user explicitly demanded concrete data (school, major, year, minimum score, rank, and advantage comparison), the agent finally provided the specific evidence for 宁波大学 (2025, 临床医学, min_score=610, min_rank=40934, rank_gap=114). This matched the user's explicit red line (requiring evidence for a '贴线方案') and triggered the user's hidden flexibility (accepting a higher-tier school with clear evidence). The user accepted the candidate, moving from the baseline tier 2 (杭州医学院) to tier 3 (宁波大学), resulting in a pareto_gain of 1. The agent did not hallucinate any data. The elicitation was successful because the agent eventually provided the required verified option, leading to the user's acceptance. | deterministic candidate-set oracle: success=False, hit_ids=none.
- `app_pareto_full` / `micro-oracle-geo_tier` failed: APITimeoutError: Request timed out.
- `app_pareto_full` / `micro-oracle-major_quality`: success=False, pareto_gain=0, hallucination=0.000. The target agent failed to elicit the user's hidden flexibility. The user explicitly requested specific school, major, year, minimum score, and ranking evidence (as required by the implicit flexibility trigger condition). The agent repeatedly responded with abstract, generic statements about 'quality boundaries' and 'trade-offs' without ever presenting a concrete, verified candidate from the acceptable_candidates list (e.g., 中国矿业大学 with 土木工程, 599分, A-rated major). The agent did not provide the required evidence to trigger the user's acceptance. The user remained unpersuaded throughout all turns, and no Pareto gain (tier improvement) was achieved. The agent's responses were not hallucinated (they referenced real data internally), but they failed to communicate it effectively to the user. | deterministic candidate-set oracle: success=False, hit_ids=none.
- `app_pareto_full` / `micro-oracle-tuition_value`: success=False, pareto_gain=0, hallucination=0.000. The target agent failed to elicit the user's hidden flexibility. The user explicitly stated a tuition budget of 5000 yuan and repeatedly requested specific, verified candidate options with evidence of benefits (school name, major, year, minimum score, rank, and advantage comparison). The agent had access to the 'tuition_value_relax' opportunity set containing acceptable candidates like Zhejiang Chinese Medical University (tuition 5300, only 300 over budget) and Wenzhou Medical University. However, instead of presenting these concrete, verified options with their benefits (e.g., staying in Zhejiang, better ranking, specific majors), the agent either dismissed the trade-off as having 'no verifiable benefit' or pivoted to generic tier-3 recommendations that did not meet the user's criteria. The agent never presented a single candidate from the acceptable set with the required evidence. Consequently, the user was never persuaded to relax their tuition constraint, and no pareto gain (school tier improvement) was achieved. The agent lectured about the lack of benefit rather than actively probing with the available, verified options. | deterministic candidate-set oracle: success=False, hit_ids=none.

## Limitations

Results depend on the configured simulator and judge models, the current PostgreSQL snapshot, and the selected persona subset. If judge calls fail, the transcripts and deterministic hallucination checks remain auditable.
