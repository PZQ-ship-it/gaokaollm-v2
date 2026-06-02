---
stage: user_feedback
stage_status: unconfirmed
created_at: 2026-06-01
source: post_full_workflow_visual_review
blocked_next_stage: ppt-render-qa-loop
supersedes_confirmation_for:
  - storyboard
  - speaker_notes_rehearsal
  - defense_qa_backup
  - asset_layout_plan
  - template_design_rules
  - academic_figure_prompt
  - content_fidelity_qa
  - deck_visual_refactor_plan
  - deck_build
---

# PPT user feedback v1

## 1. Feedback items

| ID | Target | User feedback | Required action | Discussion priority |
| --- | --- | --- | --- | --- |
| UFB-001 | Figure 1 / algorithm mechanism chart insets | The line-chart overlay and trends do not align. Chart-like mechanism visuals should be plotted from real data or deterministic code, not produced by AI image generation. | Reject the current AI-generated chart-like visual route. Rebuild the affected curve/threshold/trend visuals with local code or editable PPT objects grounded in real or explicitly synthetic-but-deterministic data. | High |
| UFB-002 | Figure 2 / full recommendation-decision loop visual | The current single-page figure is too crowded. It should be split into several figures or slides. The exact split needs focused discussion before rebuild. | Route back to asset/layout planning. Decide how to split SAVF, UCB, Pareto/BT feedback, posterior state, and final explanation across multiple visuals. | Focus discussion |
| UFB-003 | Storyboard / exhibit form decisions | Some current storyboard sections should use formulas instead of relying almost entirely on flow diagrams. More detailed feedback will follow later. | Route back to storyboard. Reconsider which method and evidence slides should use formulas, formula-plus-diagram layouts, or flow diagrams. | Pending detailed user feedback |

## 2. Status reset scope

This feedback invalidates the current visual-production chain and, after UFB-003, the storyboard exhibit-form decisions. Keep upstream brief, facts, and defense narrative confirmed, but do not continue speaker notes, Q&A/backup, asset/layout, image generation, deck build, or render QA until the revised storyboard is confirmed.

Reset to `unconfirmed`:

- `align/PPT_storyboard_v0.md`
- `align/ppt_speaker_notes_rehearsal_v0.md`
- `align/ppt_defense_qa_backup_v0.md`
- `align/PPT_asset_audit_v0.md`
- `align/template_design_rules_v0.md`
- `align/visual_enrichment_plan_v0.md`
- `align/ppt_layout_plan_v0.json`
- `align/academic_figure_prompt_v0.md`
- `align/ppt_content_fidelity_qa_v0.md`
- `align/ppt_deck_visual_refactor_plan_v0.md`
- `align/ppt_deck_build_manifest_v0.md`

Still confirmed as upstream sources:

- `align/ppt_production_brief_v0.md`
- `align/material_inventory_v0.md`
- `align/fact_ledger_v0.md`
- `align/ppt_defense_narrative_v0.md`
- `align/template_inventory_v0.md`

## 3. Next required discussion

1. Wait for detailed user feedback on which storyboard sections should use formulas.
2. Decide whether each method section should be formula-first, formula-plus-diagram, or flow-diagram-first.
3. Decide whether the method overview remains one high-level slide plus several mechanism slides, or whether the dense figure becomes backup-only.
4. Decide the split granularity: SAVF bottom-line protection, UCB probing-axis selection, Pareto A/B tradeoff, BT posterior update, and final recommendation explanation.
5. Identify which curve/trend visuals can be regenerated from local scripts or real experiment data, and which should be editable schematic diagrams with explicit non-evidence labels.
6. Re-run speaker notes, Q&A/backup planning, asset/layout planning, and content fidelity QA only after the revised storyboard is confirmed.
