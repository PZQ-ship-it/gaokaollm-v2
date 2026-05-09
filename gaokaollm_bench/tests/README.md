# tests

This package contains pytest coverage for benchmark schemas, data generation, probe tooling, chains, and CLI behavior.

Tests should prefer small in-memory fixtures and mock LLM clients. External API calls belong in explicit manual experiments, not default regression tests.

`tests/manual/` contains reproducible but non-default experiment scripts such as architecture sweeps, FR-KAN trials, ablation summaries, and validation benchmarks.
