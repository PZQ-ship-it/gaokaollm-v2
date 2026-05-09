# simulator

This package implements simulated users for multi-turn benchmark episodes.

Simulators consume benchmark schemas and personas, maintain user-side state, and produce utterances for the sandbox. Future LLM-backed simulators should route prompt and validation logic through `chains/`.

