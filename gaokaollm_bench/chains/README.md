# chains

This package is the single entry point for typed LLM tasks.

Each chain follows the same LCEL-style pipeline:

`ChatPromptTemplate -> chat model -> StrOutputParser -> JSON repair -> JsonOutputParser(Pydantic)`

Prompt text lives in `prompts/`, Pydantic contracts live in `contracts/`, graph wiring lives in `graphs/`, provider adapters live in `llm/`, and job-level batching lives in `flows/`.

The modules here should stay provider-neutral. Public wrappers accept either a LangChain chat model, an OpenAI-compatible adapter, or a lightweight async test double, then return typed, auditable results that include raw content, repaired JSON, validation flags, and errors.
