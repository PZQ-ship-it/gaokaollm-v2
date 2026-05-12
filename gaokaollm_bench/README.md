# gaokaollm_bench

`gaokaollm_bench` is the benchmark package for counterfactual probing and multi-turn preference-compromise evaluation.

The package is organized by dependency direction:

- `schemas/` and `schemas.py` define stable data contracts.
- `constrains/` centralizes shared constants, enums, default paths, metric names, and thresholds.
- `contracts/` stores cross-layer Pydantic contracts for LLM I/O and other typed boundaries.
- `prompts/` owns prompt builders and nothing else.
- `graphs/` owns LangGraph wiring for JSON repair and validation pipelines.
- `llm/` adapts external model providers behind small interfaces.
- `chains/` composes prompts, graphs, repair, and Pydantic validation into typed LLM tasks.
- `flows/` coordinates batching, concurrency, diagnosis, and job-level orchestration.
- `data_gen/` builds personas, major trees, probe data, and CLI experiments.
- `simulator/`, `sandbox/`, and `evaluator/` run conversations and score transcripts.
- `tests/` contains regression tests; `tests/manual/` contains one-off experiments and diagnostic scripts.

Business code should depend on `chains`, `flows`, and `llm` abstractions, not directly on provider SDKs.

## Thesis / 论文材料

Graduation-thesis materials live under `outputs/`. The current thesis framing is 数据贡献 + Agent 贡献 + Benchmark 贡献, abbreviated as 数据 + Agent + Benchmark.

The business Agent is described in the thesis as a lightweight MAS / multi-role Agent:

```text
前置语义归一层 -> 约束解析器 -> LLM 引导的机会规划器 -> 确定性证据探针 -> 证据谈判器
```

Implementation roles remain traceable as:

```text
semantic_normalizer -> gatekeeper -> llm-guided radar planner -> deterministic probes -> negotiator
```

The LLM plans, orders evidence, normalizes user intent, and suggests clarifications. It does not generate factual school, major, score, rank, tuition, employment, or region candidates; those candidates come from deterministic probes over PostgreSQL and standardized evidence layers.

Start from:

- `outputs/thesis_document_hub.md`: document entrypoint and maintenance index.
- `outputs/thesis_claims_manifest.json`: machine-readable thesis claim facts.
- `outputs/thesis_term_mapping.json`: terminology mapping for de-engineering thesis prose.
- `outputs/major_tree_annotation_summary.md`: major-tree annotation, DeepSeek-R1 low-confidence review, and full-coverage v2 data-contribution facts.
- `outputs/region_urban_tier_tree_full_coverage_v2_report.md`: regional urban-tier full-coverage v2 data-contribution facts for all 414 province-city pairs.
- `outputs/agent_benchmark_v1_hybrid_rag_pilot_evidence.md`: pilot evidence for the v1-style hybrid RAG baseline; it is a supplementary soft-constraint RAG comparison, not part of the seven-experiment thesis table.
- `outputs/thesis_method_experiment_chapters.md`: method and experiment chapter draft.
- `outputs/thesis_system_architecture_algorithms.md`: system architecture and algorithm draft.
- `outputs/thesis_figures_tables_pack.md`: figures, tables, and pseudocode pack.
- `outputs/thesis_diagrams_with_diagrams.md`: current hand-authored SVG/PNG rendering guide; Diagrams is retained as historical context.
- `outputs/thesis_figure_visual_acceptance.md`: PDF-page visual acceptance report for thesis figures.
- `outputs/thesis_figures/`: generated SVG/PNG figures for dissertation and PPT use.
- `outputs/thesis_mas_architecture_acceptance.md`: acceptance note for semantic normalization and LLM-guided opportunity planning.

Current thesis experiments:

- Main experiments: `major_geo_v1 + risk_band_v1`.
- Extension experiments: `school_strength_v1`, `tuition_value_v1`, `major_quality_v1`, `employment_outcome_v1`, `region_tree_v1`.
- Benchmark pressure tests: `multi_axis_v1` is the historical version, and `multi_axis_v2` is the coherent-axis revision. They are not part of the seven-experiment thesis table.
- Supplementary baseline pilot: `v1_hybrid_rag` uses query normalization, relational filtering, semantic recall, reranking, and chong/wen/bao segmentation as a v1-style soft-constraint RAG comparison. It does not enter the seven-experiment thesis table.

Major-tree data contribution: full-coverage v2 auditable mounting covers `22,759 / 22,759` raw distinct major names and `140,995 / 140,995` admission rows, with `remaining_unassigned = 0`. This is a traceable coverage claim, not a claim that every semantic boundary has been manually confirmed.

Hidden fields such as `implicit_flexibilities`, `volunteer_set`, and `axis_flexibilities` are evaluator-side ground truth only and must not enter target Agent input.
