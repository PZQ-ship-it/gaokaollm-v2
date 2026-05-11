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

Graduation-thesis materials live under `outputs/`. The current thesis framing is
数据 + Agent + Benchmark, with a lightweight MAS / multi-role Agent architecture: lightweight MAS / multi-role Agent, `前置语义归一层 -> 约束解析器 -> LLM 引导的机会规划器 -> 确定性证据探针 -> 证据谈判器`.
`gatekeeper -> radar -> negotiator`.

Start from:

- `outputs/thesis_document_hub.md`: document entrypoint and maintenance index.
- `outputs/thesis_claims_manifest.json`: machine-readable thesis claim facts.
- `outputs/thesis_method_experiment_chapters.md`: method and experiment chapter draft.
- `outputs/thesis_system_architecture_algorithms.md`: system architecture and algorithm draft.
- `outputs/thesis_figures_tables_pack.md`: figures, tables, and pseudocode pack.
- `outputs/thesis_diagrams_with_diagrams.md`: current hand-authored SVG/PNG rendering guide for thesis figures; Diagrams is retained as historical context.
- `outputs/thesis_figure_visual_acceptance.md`: PDF-page visual acceptance report for thesis figures.
- `outputs/thesis_figures/`: generated SVG/PNG figures for dissertation and PPT use.
- `outputs/thesis_mas_architecture_acceptance.md`: acceptance note for semantic normalization and LLM-guided opportunity planning.


Graduation-thesis materials live under `outputs/`. The current thesis framing is
?? + Agent + Benchmark, with a lightweight MAS / multi-role Agent architecture: lightweight MAS / multi-role Agent, `前置语义归一层 -> 约束解析器 -> LLM 引导的机会规划器 -> 确定性证据探针 -> 证据谈判器`.
`??????? -> ????? -> LLM ???????? -> ??????? -> ?????`.

Implementation roles remain traceable as `semantic_normalizer -> gatekeeper -> llm-guided radar planner -> deterministic probes -> negotiator`; LLM planning never generates factual candidates.
