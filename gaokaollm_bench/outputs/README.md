# gaokaollm_bench outputs

This directory stores benchmark outputs, thesis drafts, evidence appendices, data artifacts, and historical reports.

For graduation-thesis work, start here:

- `thesis_document_hub.md`: human-readable entrypoint and maintenance index.
- `thesis_claims_manifest.json`: machine-readable source of high-frequency thesis claims.
- `thesis_term_mapping.json`: terminology source for replacing implementation names with thesis terms.
- `thesis_full_draft_v1.md`: continuous dissertation draft assembled from chapter masters, figures, metrics, and evidence.
- `thesis_diagrams_with_diagrams.md`: hand-authored SVG/PNG figure rendering guide; Diagrams is historical context only.
- `thesis_figure_visual_acceptance.md`: PDF-page visual acceptance report for the current thesis figures.
- `thesis_mas_architecture_acceptance.md`: acceptance note for the v1 semantic-normalization and v2 LLM-guided planning integration.
- `thesis_figures/`: generated SVG/PNG figure assets for dissertation and PPT use.
- `thesis_figures_pdf_snapshots/`: rendered PDF pages for quick figure-layout review.

Current thesis framing:

- Contribution structure: 数据 + Agent + Benchmark.
- Agent architecture: lightweight MAS / multi-role Agent, `前置语义归一层 -> 约束解析器 -> LLM 引导的机会规划器 -> 确定性证据探针 -> 证据谈判器`.
- Main experiments: `major_geo_v1 + risk_band_v1`.
- Extension experiments: `school_strength_v1`, `tuition_value_v1`, `major_quality_v1`, `employment_outcome_v1`, `region_tree_v1`.
- Benchmark pressure tests: `multi_axis_v1` is the historical 30-persona two-axis test; `multi_axis_v2` is the coherent-axis revision. They are not part of the seven-experiment thesis table and do not replace the main experiments.

## Document Groups

| Group | Examples | Use |
| --- | --- | --- |
| Thesis body drafts | `thesis_full_draft_v1.md`, `thesis_intro_related_work_chapters.md`, `thesis_method_experiment_chapters.md`, `thesis_conclusion_future_work_chapter.md` | Continuous draft and chapter-level text that can be migrated into the dissertation. |
| Contribution and roadmap | `thesis_agent_benchmark_contribution.md`, `dynamic_decision_considerations_roadmap.md`, `thesis_v1_v2_integration_plan.md` | High-level positioning and maintenance of the data + Agent + Benchmark storyline. |
| Architecture and figures | `thesis_system_architecture_algorithms.md`, `thesis_figures_tables_pack.md`, `thesis_diagrams_with_diagrams.md`, `thesis_figure_visual_acceptance.md`, `thesis_figures/`, `thesis_figures_pdf_snapshots/` | MAS architecture, algorithms, generated SVG/PNG figures, PDF visual acceptance snapshots, Mermaid drafts, tables, and pseudocode. |
| Methodology | `benchmark_methodology.md`, `major_tree_methodology.md`, `thesis_hierarchical_relaxation_methodology.md` | Benchmark, major-tree, and hierarchical-relaxation methodology. |
| Summaries | `agent_benchmark_*_summary.md` | Aggregate experiment results, plus `agent_benchmark_multi_axis_v1_summary.md` and `agent_benchmark_multi_axis_v2_summary.md` for multi-axis pressure tests. |
| Evidence appendices | `agent_benchmark_*_evidence.md`, `thesis_data_agent_benchmark_extension_evidence.md` | Per-case transcript evidence and baseline comparisons, including `agent_benchmark_multi_axis_v1_evidence.md` and `agent_benchmark_multi_axis_v2_evidence.md` for pressure tests. |
| Historical/data-quality reports | `region_tree_coverage_report.md`, `region_tree_v1_coverage_report.md`, `thesis_artifact_audit.md` | Traceability and data-quality history, not the current thesis claim source. |

## Maintenance Rule

When an experiment metric or thesis claim changes, update `thesis_claims_manifest.json` and `thesis_document_hub.md` first, then follow the hub's synchronization checklist.

Coverage reports and the thesis audit are historical or data-quality materials. Do not treat them as the current source of thesis claims unless a new audit pass is explicitly requested.

When revising thesis prose, use `thesis_term_mapping.json` before editing chapter drafts. Engineering identifiers such as experiment ids, output paths, and internal fields should stay in result tables, appendices, or reproducibility notes, not in the main thesis narrative.

Implementation trace: `semantic_normalizer -> gatekeeper -> llm-guided radar planner -> deterministic probes -> negotiator`. LLM 不生成学校、专业、分数、位次等事实候选，只输出 `probe_plan`、`opportunity_rankings` 和 `clarification_hint`；Agent 不读取 `implicit_flexibilities`、`volunteer_set` 或 `axis_flexibilities`。
