# constrains

This package centralizes shared constants and enum values.

Use it for stable values that appear across modules: conversation roles,
probe model kinds, class-weight modes, default artifact paths, metric names,
promotion thresholds, and LLM environment variable names.

Avoid putting task-specific local variables here. If a value is used by only
one function or one script, keep it local.

