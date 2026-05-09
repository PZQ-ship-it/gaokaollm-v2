# data_gen

This package builds benchmark data and reusable probe-training artifacts.

It owns DB probing, major-tree construction, persona generation, embeddings,
probe training/prediction, and durable data builders.

It should not own prompt text, provider SDK calls, LangGraph wiring, or one-off
research experiments:

- prompt builders live in `prompts/`
- graph wiring lives in `graphs/`
- provider calls go through `llm/`
- batch orchestration should reuse `flows/`
- one-off sweeps, ablations, and diagnostics live in `tests/manual/`

Experiment commands should use `python -m gaokaollm_bench.tests.manual...`
directly. This package intentionally does not keep compatibility wrappers for
manual scripts.
