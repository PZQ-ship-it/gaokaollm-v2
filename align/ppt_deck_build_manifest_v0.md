---
stage: deck_build
stage_status: unconfirmed
requires_confirmed:
  - ppt_production_brief
  - fact_ledger
  - defense_narrative
  - storyboard
  - speaker_notes_rehearsal
  - defense_qa_backup
  - asset_layout_plan
  - academic_figure_prompt_when_required
  - content_fidelity_qa
blocked_next_stage: ppt-render-qa-loop
previously_confirmed_by: user, 2026-05-31
reset_by: user, 2026-06-01
reset_reason: User visual/storyboard feedback invalidated method visual asset route, split/layout assumptions, and formula-vs-flow exhibit choices.
created_at: 2026-05-31
---

# PPT deck build manifest v0

## 0. 2026-06-01 reset note

Status reset to `unconfirmed`. The PPTX remains as a traceable draft output, but it is not accepted for render QA or final polish:

- The current AI-generated V-AI01 / chart-like visual route is rejected for continued use.
- The dense method visual must be split into several figures/slides after focused discussion.
- Some method sections may need formulas rather than flow diagrams.
- Rebuild should start from revised storyboard, not from render QA.

## 1. Output

- PPTX path: `D:/gaokaollm-v2/generated_pptx_test/gaokaollm_defense_deck_v0.pptx`
- Build script: `exp/ppt_deck_build_v0/build_deck_v0.py`
- Local figure generation script: `exp/ppt_deck_build_v0/generate_local_figures_v0.py`
- Cropped source-figure preparation script: `exp/ppt_deck_build_v0/prepare_cropped_assets_v0.py`
- Stage status: unconfirmed revision required
- Main slides: 19
- Backup separator: 1
- Backup slides: 16
- Total slides: 36
- Aspect ratio: 4:3, 10.0 x 7.5 in

## 2. Confirmed input artifacts

- `align/ppt_production_brief_v0.md`: confirmed
- `align/fact_ledger_v0.md`: confirmed
- `align/ppt_defense_narrative_v0.md`: confirmed
- `align/PPT_storyboard_v0.md`: confirmed
- `align/ppt_speaker_notes_rehearsal_v0.md`: confirmed
- `align/ppt_defense_qa_backup_v0.md`: confirmed
- `align/PPT_asset_audit_v0.md`: unconfirmed after user feedback
- `align/template_inventory_v0.md`: confirmed
- `align/template_design_rules_v0.md`: confirmed
- `align/ppt_layout_plan_v0.json`: unconfirmed after user feedback
- `align/academic_figure_prompt_v0.md`: unconfirmed / do not use for generation
- `align/ppt_content_fidelity_qa_v0.md`: unconfirmed after user feedback
- `align/ppt_deck_visual_refactor_plan_v0.md`: unconfirmed after user feedback

## 3. Visual route outcomes

| Route | Outcome |
| --- | --- |
| Template | Used the confirmed 4:3 slide size and template policy. The generation script starts from `zjuslides.pptx` when available, then builds custom editable slides. |
| Main evidence figures | Inserted source PNG figures from the final thesis/project figure directories where appropriate. |
| Figure scaling | Created non-destructive cropped copies of source diagrams under `generated_assets/crop_*.png` to remove large white margins and make main-slide figures larger. |
| Local mechanism figure | Added `generated_assets/savf_mechanism_ppt.png` for Slide 10 to replace scattered text boxes with a single mechanism visual. |
| Visual refactor | Applied `align/ppt_deck_visual_refactor_plan_v0.md`: 19 main slides, agenda/section dividers, light title band, and one-main-visual evidence grammar. |
| Editable diagrams | Built the problem framing, fact-boundary, method, A/B posterior, conclusion, and several backup slides with editable PowerPoint shapes/tables. |
| V-AI01 generated academic figure | Superseded by 2026-06-01 user feedback. Do not treat `generated_assets/v_ai01_openrouter_icu.png` as accepted for continued deck production. Rebuild chart-like visuals with local code/editable objects and split the dense figure. |
| Product screenshots | Not used. Slide 2 and B14 use abstract comparison to avoid stale product claims. |
| Horizontal architecture | Main Slide 5 keeps an editable source-derived architecture summary. If `generated_assets/architecture_wide.png` exists, it is added to B15 by default; the thesis vertical figure is not overwritten or force-fit. |

Prior user feedback applied: V-AI01 was made visible in the main talk on Slide 9, with B16 retained as the backup/boundary explanation slide. This decision is now unconfirmed after the 2026-06-01 visual review.

OpenRouter ICU status: completed for `generated_assets/v_ai01_openrouter_icu.png` when that file is present, but the asset is no longer approved for continued deck production. Request metadata remains recorded in `exp/ppt_deck_build_v0/openrouter_vai01_generation_log.json` for traceability.

## 4. Notes and editability

- Speaker notes were not inserted into the PowerPoint notes pane because `python-pptx` does not support notes-pane authoring reliably in this environment.
- Confirmed notes remain in `align/ppt_speaker_notes_rehearsal_v0.md`.
- Most text, tables, callouts, and diagrams are editable PowerPoint objects.
- Source evidence figures and UI screenshots are raster PNG insertions with editable surrounding labels/callouts.

## 5. Assets used

- `D:\毕设\latex-for-zju-master\latex-for-zju-master\figure\thesis_figures\fig_5_3_ucb_dispatch.png`
- `D:\毕设\latex-for-zju-master\latex-for-zju-master\figure\thesis_figures\fig_5_2_runtime_state_machine.png`
- `D:\毕设\latex-for-zju-master\latex-for-zju-master\figure\thesis_figures\fig_3_5_elicitation_console.png`
- `D:\毕设\latex-for-zju-master\latex-for-zju-master\figure\thesis_figures\fig_3_6_final_decision_report.png`
- `D:\毕设\latex-for-zju-master\latex-for-zju-master\figure\thesis_figures\fig_4_2_benchmark_flow.png`
- `D:\毕设\latex-for-zju-master\latex-for-zju-master\figure\thesis_figures\fig_4_5_c1_baseline_model_target.png`
- `D:\毕设\latex-for-zju-master\latex-for-zju-master\figure\thesis_figures\fig_4_6_c1_ablation_core_metrics.png`
- `D:\毕设\latex-for-zju-master\latex-for-zju-master\figure\thesis_figures\fig_4_8_1_c1_planner_process.png`
- `D:\毕设\latex-for-zju-master\latex-for-zju-master\figure\thesis_figures\fig_4_5_region_hierarchy_partial.png`
- `D:\毕设\latex-for-zju-master\latex-for-zju-master\figure\thesis_figures\fig_3_1_v1_hybrid_rag_flow.png`
- `D:\毕设\latex-for-zju-master\latex-for-zju-master\figure\thesis_figures\fig_4_8_2_c1_negotiator_process.png`
- `exp/ppt_deck_build_v0/generated_assets/v_ai01_openrouter_icu.png`
- `exp/ppt_deck_build_v0/generated_assets/crop_fig_5_1_mas_workflow.png`
- `exp/ppt_deck_build_v0/generated_assets/crop_fig_3_1_v1_hybrid_rag_flow.png`
- `exp/ppt_deck_build_v0/generated_assets/crop_fig_5_3_ucb_dispatch.png`
- `exp/ppt_deck_build_v0/generated_assets/crop_fig_5_2_runtime_state_machine.png`
- `exp/ppt_deck_build_v0/generated_assets/crop_fig_4_2_benchmark_flow.png`
- `exp/ppt_deck_build_v0/generated_assets/savf_mechanism_ppt.png`
- `exp/ppt_deck_build_v0/generated_assets/architecture_wide.png`

## 6. Known pre-render risks

- Visual polish is blocked before render QA by user feedback on Figure 1 and Figure 2.
- Some source figure labels may be too small at 4:3 slideshow size, especially UI screenshots and dense experiment charts.
- Backup slides are placed after a Backup separator rather than hidden, so render QA should verify navigation/visibility policy.
- Slide 5 is a compact PPT redraw of the architecture. Render QA should compare it against the original semantics.
- The previous process-indicator Slide 18 was moved out of the main talk path; detailed process evidence remains available in backup.
- Notes-pane insertion is not available; presenter should use the confirmed notes artifact.

## 7. Handoff

This manifest is currently unconfirmed. Do not send this draft to render QA until the method visual route is replanned, rebuilt, and rechecked.

```yaml
stage_status: unconfirmed
blocked_next_stage: ppt-render-qa-loop
```

Next required action: revise `storyboard`, rerun speaker notes, Q&A/backup planning, asset/layout planning, content fidelity QA, and rebuild the deck draft.
