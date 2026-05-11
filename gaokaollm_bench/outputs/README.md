# gaokaollm_bench outputs

This directory stores benchmark outputs, thesis drafts, evidence appendices, data artifacts, and historical reports.

For graduation-thesis work, start here:

- `thesis_document_hub.md`: human-readable entrypoint and maintenance index.
- `thesis_claims_manifest.json`: machine-readable source of high-frequency thesis claims.
- `thesis_full_draft_v1.md`: continuous dissertation draft assembled from chapter masters, figures, metrics, and evidence.
- `thesis_diagrams_with_diagrams.md`: Diagrams-based figure rendering guide.
- `thesis_figures/`: generated SVG/PNG figure assets for dissertation and PPT use.

Current thesis framing:

- Contribution structure: 数据 + Agent + Benchmark.
- Agent architecture: lightweight MAS / multi-role Agent, `gatekeeper -> radar -> negotiator`.
- Main experiments: `major_geo_v1 + risk_band_v1`.
- Extension experiments: `school_strength_v1`, `tuition_value_v1`, `major_quality_v1`, `employment_outcome_v1`, `region_tree_v1`.

## Document Groups

| Group | Examples | Use |
| --- | --- | --- |
| Thesis body drafts | `thesis_full_draft_v1.md`, `thesis_intro_related_work_chapters.md`, `thesis_method_experiment_chapters.md`, `thesis_conclusion_future_work_chapter.md` | Continuous draft and chapter-level text that can be migrated into the dissertation. |
| Contribution and roadmap | `thesis_agent_benchmark_contribution.md`, `dynamic_decision_considerations_roadmap.md`, `thesis_v1_v2_integration_plan.md` | High-level positioning and maintenance of the data + Agent + Benchmark storyline. |
| Architecture and figures | `thesis_system_architecture_algorithms.md`, `thesis_figures_tables_pack.md`, `thesis_diagrams_with_diagrams.md`, `thesis_figures/` | MAS architecture, algorithms, generated SVG/PNG figures, Mermaid drafts, tables, and pseudocode. |
| Methodology | `benchmark_methodology.md`, `major_tree_methodology.md`, `thesis_hierarchical_relaxation_methodology.md` | Benchmark, major-tree, and hierarchical-relaxation methodology. |
| Summaries | `agent_benchmark_*_summary.md` | Aggregate experiment results. |
| Evidence appendices | `agent_benchmark_*_evidence.md`, `thesis_data_agent_benchmark_extension_evidence.md` | Per-case transcript evidence and baseline comparisons. |
| Historical/data-quality reports | `region_tree_coverage_report.md`, `region_tree_v1_coverage_report.md`, `thesis_artifact_audit.md` | Traceability and data-quality history, not the current thesis claim source. |

## Maintenance Rule

When an experiment metric or thesis claim changes, update `thesis_claims_manifest.json` and `thesis_document_hub.md` first, then follow the hub's synchronization checklist.

Coverage reports and the thesis audit are historical or data-quality materials. Do not treat them as the current source of thesis claims unless a new audit pass is explicitly requested.
