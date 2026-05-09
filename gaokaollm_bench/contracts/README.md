# contracts

This package contains Pydantic models and typed data contracts shared across
layers.

Contracts are intentionally independent from LLM providers, prompt text,
LangGraph wiring, and CLI orchestration. Import these models from `contracts/`
when a schema crosses module boundaries.

