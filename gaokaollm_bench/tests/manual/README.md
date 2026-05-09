# manual

This package contains one-off or research-facing experiment scripts.

These modules may run long sweeps, call external APIs, or write experiment
artifacts. They are useful for reproducing methodological evidence, but they are
not part of the production benchmark pipeline. Keep reusable logic in
`data_gen/`, `flows/`, `chains/`, `graphs/`, or `llm/`; keep manual experiment
entrypoints here.

