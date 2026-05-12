# v1 Soft-RAG Baseline Pilot

## Purpose

This pilot adds a stronger baseline than `hard_constraint` without replacing the existing lower-bound baseline. `v1_soft_rag` approximates the v1 soft-constraint RAG behavior on the current PostgreSQL snapshot: it normalizes explicit user wording, retrieves soft-matched admission options, and presents chong/wen/bao candidates. It does not perform staged relaxation or evidence-driven Pareto negotiation.

## Scope

- Main-experiment smoke scope only: `major_geo_v1` and `risk_band_v1`, 10 cases each.
- Existing seven-experiment results are not overwritten.
- `hard_constraint` remains the no-negotiation lower bound.
- `v1_soft_rag` is a supplementary soft-RAG baseline.

## Results

| Experiment | Target | Success | Mean Pareto Gain | Mean Hallucination | Avg Turns |
|---|---|---:|---:|---:|---:|
| `major_geo_v1` | `app_pareto` | 0.700 | 0.700 | 0.060 | 7.40 |
| `major_geo_v1` | `hard_constraint` | 0.000 | 0.000 | 0.100 | 13.00 |
| `major_geo_v1` | `v1_soft_rag` | 0.000 | 0.000 | 0.250 | 13.00 |
| `risk_band_v1` | `app_pareto` | 1.000 | 3.000 | 0.000 | 5.00 |
| `risk_band_v1` | `hard_constraint` | 0.000 | 0.000 | 0.000 | 13.00 |
| `risk_band_v1` | `v1_soft_rag` | 0.000 | 0.000 | 0.000 | 13.00 |

## Interpretation

The pilot supports keeping two baseline roles separate. `hard_constraint` measures the lower-bound behavior of a non-negotiating system. `v1_soft_rag` is a more realistic v1-style baseline: it can retrieve plausible options under soft constraints, but it does not construct the hidden-compromise evidence chain required by the iceberg-persona benchmark.

The `major_geo_v1` hallucination rate for `v1_soft_rag` is higher because the factual checker penalizes recommendations whose lowest admission score exceeds the user's score. This is expected for a chong/wen/bao soft-retrieval baseline and should be interpreted as risk exposure rather than fabricated school names.

## Artifacts

- `agent_benchmark_major_geo_v1_v1_baseline_pilot/summary.md`
- `agent_benchmark_major_geo_v1_v1_baseline_pilot/reports/v1_soft_rag.jsonl`
- `agent_benchmark_major_geo_v1_v1_baseline_pilot/transcripts/v1_soft_rag/`
- `agent_benchmark_risk_band_v1_v1_baseline_pilot/summary.md`
- `agent_benchmark_risk_band_v1_v1_baseline_pilot/reports/v1_soft_rag.jsonl`
- `agent_benchmark_risk_band_v1_v1_baseline_pilot/transcripts/v1_soft_rag/`

## Boundary

`v1_soft_rag` only consumes explicit user utterances. It does not read `implicit_flexibilities`, `volunteer_set`, or `axis_flexibilities`, and it does not produce `pareto_opportunities`.
