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
