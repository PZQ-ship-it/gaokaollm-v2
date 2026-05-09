# chains

This package is the single entry point for typed LLM tasks.

Each chain follows the same pipeline:

`build prompt -> call LLM -> parse JSON -> repair JSON -> validate with Pydantic`

Prompt text lives in `prompts/`, Pydantic contracts live in `contracts/`, graph wiring lives in `graphs/`, provider adapters live in `llm/`, and job-level batching lives in `flows/`.

The modules here should stay provider-neutral. They receive an `llm.BaseLLMClient` and return typed, auditable results that include raw content, repaired JSON, validation flags, and errors.
