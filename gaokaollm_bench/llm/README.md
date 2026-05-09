# llm

This package contains external LLM provider adapters.

Benchmark code should depend on `BaseLLMClient` rather than importing provider SDKs directly. The OpenAI-compatible adapter handles `.env` loading, SSL environment cleanup, request timeout, retry policy, and `response_format` forwarding.

`runnable.py` adapts OpenAI-compatible clients, LangChain chat models, and test doubles into LCEL-compatible runnables so chains can consistently use `ChatPromptTemplate | chat_model | StrOutputParser`.

`response_utils.py` contains provider-neutral helpers for simple legacy clients
that expose `ainvoke`, `acomplete`, or an async callable interface.
