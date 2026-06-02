---
stage: asset_layout_plan
stage_status: unconfirmed
requires_confirmed:
  - ppt_production_brief
  - fact_ledger
  - defense_narrative
  - storyboard
  - speaker_notes_rehearsal
  - defense_qa_backup
blocked_next_stage: academic-figure-prompt
previously_confirmed_by: user, 2026-05-31
reset_by: user, 2026-06-01
reset_reason: Figure 1 chart/trend mismatch, Figure 2 density, and formula-vs-flow storyboard feedback require replanning.
created_at: 2026-05-31
source_template_inventory: align/template_inventory_v0.md
source_visual_plan: align/visual_enrichment_plan_v0.md
---

# PPT asset audit v0

## 0. 2026-06-01 reset note

Status reset to `unconfirmed` after user visual review. The current V-AI01 route is not approved for continued deck production:

- Chart-like line/threshold visuals must be rebuilt with real data or deterministic code/editable objects, not AI image generation.
- The dense full-loop recommendation-decision figure must be split into several visuals or slides.
- Some sections may need formulas instead of flow diagrams; wait for detailed storyboard feedback before final asset decisions.
- The split strategy is marked as a focused discussion item before another deck build.

## 1. Asset source roots

| Root | Path | Use |
| --- | --- | --- |
| Final thesis figures | `D:\毕设\latex-for-zju-master\latex-for-zju-master\figure\thesis_figures` | Highest priority for thesis figures and charts. |
| Project thesis figures | `D:\gaokaollm-v2\gaokaollm_bench\outputs\thesis_figures` | Secondary source for SVGs and project-generated diagram assets. |
| Thesis diagram renderer | `D:\gaokaollm-v2\gaokaollm_bench\tests\manual\render_thesis_diagrams.py` | Source-derived redraws for framework / workflow figures. |
| Chapter 4 plotting code | `D:\gaokaollm-v2\app\evaluation\chapter4_c1_figures.py` | Reproducible source for C1 baseline and ablation charts. |
| PPT template | `D:\毕设\latex-for-zju-master\latex-for-zju-master\zjuslides.pptx` | Template style, layouts, footer, school visual language. |

## 2. Main-deck asset decisions

| Slide | Primary asset decision | Preferred source asset | Route | Evidence status | Notes / risk |
| --- | --- | --- | --- | --- | --- |
| S01 Cover | template reuse | `zjuslides.pptx` layout 0/1 + thesis cover fields | no_generation | source metadata | No English subtitle. |
| S02 Existing products | confirm source later | verified 阳光高考 / 夸克高考 pages or abstract 3-column table | source_capture_or_editable_table | contextual illustration | Product facts are temporally unstable; verify before deck build. |
| S03 Problem definition | editable diagram | new simple funnel / iceberg diagram | local_editable_diagram | source-derived explanation | No real student case. |
| S04 Overall approach | editable process | fact feasible set -> A/B clarification -> recommendation | local_editable_diagram | source-derived explanation | Keep as transition, not dense. |
| S05 Architecture overview | redraw | `fig_4_1_system_architecture` + `render_system_architecture()` | source_redraw | source-derived explanation | Create horizontal PPT version; do not use vertical figure directly. |
| S06 Fact boundary | reuse/redraw | `fig_4_6_database_physical_schema` or simplified evidence-layer diagram | source_reuse_or_redraw | source evidence | Must show LLM not generating facts. |
| S07 Data coverage | editable table + optional thumbnails | `fig_4_4_major_tree_partial`, `fig_4_5_region_hierarchy_partial` | source_reuse_or_editable_table | source evidence | Coverage not semantic perfection. |
| S08 Static retrieval gap | reuse/redraw | `fig_3_1_v1_hybrid_rag_flow` or `agent_workflow_2` after source check | source_reuse_or_redraw | source-derived explanation | Use only if consistent with final thesis. |
| S09 Method overview | local code/editable split plan required | V-AI01 is rejected for current deck; use source-derived split visuals or `fig_5_1_mas_workflow` | local_code_plotting_or_editable_diagram | source-derived explanation | Must discuss split plan; chart-like visuals should not be AI-generated. |
| S10 SAVF | editable mechanism diagram | non-compensatory value curve | local_editable_diagram | source-derived explanation | Formula backup only. |
| S11 UCB | reuse/redraw | `fig_5_3_ucb_dispatch` | source_reuse_or_redraw | source-derived explanation | Explicitly label heuristic. |
| S12 Pareto/BT | editable mockup | A/B cards + posterior weight bar | local_editable_diagram | source-derived explanation | No unverified school names. |
| S13 Runtime state | reuse/redraw | `fig_5_2_runtime_state_machine` | source_reuse_or_redraw | source-derived explanation | Simplify for projection. |
| S14 UI evidence | reuse/crop | `fig_3_5_elicitation_console`, `fig_3_6_final_decision_report` | source_reuse | source evidence | Crop for legibility; avoid full-page screenshots. |
| S15 Benchmark design | reuse/redraw | `fig_4_2_benchmark_flow` | source_reuse_or_redraw | source evidence | Highlight hidden persona boundary. |
| S16 Baseline results | reuse | `fig_4_5_c1_baseline_model_target` | source_reuse | source evidence | Do not regenerate chart with image tools. |
| S17 Ablation results | reuse | `fig_4_6_c1_ablation_core_metrics` | source_reuse | source evidence | Add conclusion callout only. |
| S18 Process metrics | optional reuse/redraw | `fig_4_8_1/2/3_c1_*` | source_reuse_or_redraw | source evidence | Candidate to skip or backup if timing tight. |
| S19 Contribution close | editable summary | closed-loop contribution diagram | local_editable_diagram | source-derived explanation | No new claims. |
| S20 Limitations | editable text/table | limitation matrix | local_editable_table | source-derived explanation | Use “initially supports”, not “production proven”. |
| S21 Q&A | template reuse | template Q&A / thank-you style | no_generation | not applicable | Minimal. |

## 3. Backup asset decisions

| Backup | Asset decision | Route | Key source | Risk |
| --- | --- | --- | --- | --- |
| B01 LLM fact boundary | editable diagram | local_editable_diagram | `fact_ledger_v0.md` §1, §2, §5, §8 | Must not imply LLM generates candidates. |
| B02 Major tree coverage | table + optional source figure | source_reuse_or_editable_table | `major_tree_annotation_summary.md`; `fig_4_4_major_tree_partial` | Coverage vs correctness. |
| B03 Region tree boundary | table + hierarchy figure | source_reuse_or_editable_table | region report; `fig_4_5_region_hierarchy_partial` | Do not imply city benefits. |
| B04 Static retrieval baseline | flow comparison | source_reuse_or_redraw | `fig_3_1_v1_hybrid_rag_flow` / `agent_workflow_2` | Source consistency check needed. |
| B05 SAVF details | value curve | local_editable_diagram | `02-problem-algorithm.tex:119-152` | Keep formula readable. |
| B06 UCB details | dispatch flow | source_reuse_or_redraw | `fig_5_3_ucb_dispatch` | Heuristic label required. |
| B07 Pareto/BT details | A/B + posterior | local_editable_diagram | `03-system-design.tex:317-339` | No SQL/query overclaim. |
| B08 State machine | simplified state diagram | source_reuse_or_redraw | `fig_5_2_runtime_state_machine` | Avoid code density. |
| B09 Benchmark boundary | three-lane flow | local_editable_diagram | production brief §4; fact ledger §7 | Hidden fields must be evaluator-only. |
| B10 Results table | compact chart/table | source_reuse | `fig_4_5`, `fig_4_6` | No significance overclaim. |
| B11 Process diagnostics | one selected process figure | source_reuse_or_redraw | `fig_4_8_*` | Choose one, not three, if cramped. |
| B12 Old vs final experiment scope | editable comparison table | local_editable_table | fact ledger §6.2, §10 | Mark old/pilot clearly. |
| B13 Limitations | limitation matrix | local_editable_table | `07-conclusion.tex:28-38` | Keep confident but not overstated. |
| B14 Product comparison | source-captured or abstract comparison | source_capture_or_editable_table | public pages later + speaker notes Slide 2 | Requires current page verification. |
| B15 Engineering implementation path | architecture local redraw | source_redraw | system architecture script | Do not overwrite paper vertical figure. |
| B16 Algorithm visual boundary | split-plan discussion / local redraw boundary | local_code_plotting_or_editable_diagram | visual plan V-AI01 plus user feedback v1 | Current AI-generated visual route is unconfirmed; exact split is a focus discussion item. |

## 4. Asset availability findings

- Confirmed thesis figure directory contains PDF/PNG/SVG triples for core diagrams: `fig_4_1_system_architecture`, `fig_4_2_benchmark_flow`, `fig_4_4_major_tree_partial`, `fig_4_5_region_hierarchy_partial`, `fig_4_6_database_physical_schema`, `fig_5_1_mas_workflow`, `fig_5_2_runtime_state_machine`, `fig_5_3_ucb_dispatch`.
- Confirmed thesis figure directory contains PNG/PDF for key experiment charts: `fig_4_5_c1_baseline_model_target`, `fig_4_6_c1_ablation_core_metrics`, and `fig_4_8_*` process diagnostics.
- Project output figure directory contains useful SVG versions for some diagrams, including `agent_workflow_2.svg`; source consistency must be checked before use.
- `render_thesis_diagrams.py` includes renderers for `fig_4_1_system_architecture`, `fig_4_2_benchmark_flow`, `fig_5_1_mas_workflow`, `fig_5_2_runtime_state_machine`, and `fig_5_3_ucb_dispatch`.
- Current `render_system_architecture()` uses `SvgCanvas(width=1400, height=1800)` and should be adapted into a PPT-horizontal version.

## 5. Production routing decisions

- Default evidence figures: source reuse or source redraw.
- Default method diagrams: editable PowerPoint shapes or source-derived SVG redraw.
- Default results charts: source reuse; local plotting only if final thesis chart resolution is insufficient.
- Generated academic visual: current V-AI01 AI route is unconfirmed after user feedback; chart-like mechanism visuals should be rebuilt with local code or editable deterministic diagrams.
- Product comparison: source-capture later or abstract editable comparison; no generated product UI.

## 6. Open asset decisions

- How to split the current dense V-AI01 concept into several figures/slides.
- Which curve/trend visuals can be plotted from real data or deterministic code.
- Whether any non-chart illustrative AI visual remains useful after the split; default is no AI for chart-like figures.
- Whether Slide 2 uses real product screenshots or an abstract comparison table.
- Whether Slide 18 stays in main deck or becomes backup-only.
- Whether B01-B16 all enter hidden appendix or A-level backup pages only.
- Whether deck remains 4:3 template-native; draft recommendation is yes.
