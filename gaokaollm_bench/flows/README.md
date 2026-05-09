# flows

This package contains orchestration logic for benchmark jobs.

Flows are allowed to coordinate concurrency, batch work, and file outputs, but they should not own prompt text, provider-specific APIs, or validation schemas.

