---
stage: content_fidelity_qa
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
blocked_next_stage: ppt-deck-build
previously_confirmed_by: user, 2026-05-31
reset_by: user, 2026-06-01
reset_reason: User visual/storyboard feedback invalidated V-AI01 route, deck visual layout assumptions, and formula-vs-flow exhibit choices.
created_at: 2026-05-31
source_brief: align/ppt_production_brief_v0.md
source_material_inventory: align/material_inventory_v0.md
source_fact_ledger: align/fact_ledger_v0.md
source_defense_narrative: align/ppt_defense_narrative_v0.md
source_storyboard: align/PPT_storyboard_v0.md
source_speaker_notes: align/ppt_speaker_notes_rehearsal_v0.md
source_defense_qa_backup: align/ppt_defense_qa_backup_v0.md
source_asset_audit: align/PPT_asset_audit_v0.md
source_visual_plan: align/visual_enrichment_plan_v0.md
source_layout_plan: align/ppt_layout_plan_v0.json
source_academic_figure_prompt: align/academic_figure_prompt_v0.md
---

# PPT content fidelity QA v0

## 1. QA outcome

Status: unconfirmed-blocked by post-workflow user visual feedback.

The previous pass is invalidated for the storyboard and visual-production chain. The confirmed upstream facts and narrative remain usable, but the storyboard exhibit choices, speaker notes, Q&A/backup plan, asset/layout plan, academic figure prompt, deck visual plan, and deck build must be revised before this QA can pass again.

New blocker: the current V-AI01 / method-visual route should not continue as an AI-generated dense figure. Chart-like mechanism visuals need local code or editable deterministic construction, and the dense workflow visual needs to be split after focused discussion.

Additional blocker: some sections may need formulas instead of flow diagrams; detailed user feedback is pending.

## 2. Required inputs check

| Required artifact | File | Status |
| --- | --- | --- |
| Production brief | `align/ppt_production_brief_v0.md` | confirmed |
| Material inventory / fact ledger | `align/material_inventory_v0.md`; `align/fact_ledger_v0.md` | confirmed |
| Defense narrative | `align/ppt_defense_narrative_v0.md` | confirmed |
| Storyboard | `align/PPT_storyboard_v0.md` | unconfirmed after user feedback |
| Speaker notes / rehearsal | `align/ppt_speaker_notes_rehearsal_v0.md` | unconfirmed after storyboard reset |
| Defense Q&A / backup | `align/ppt_defense_qa_backup_v0.md` | unconfirmed after storyboard reset |
| Asset/layout plan | `align/PPT_asset_audit_v0.md`; `align/visual_enrichment_plan_v0.md`; `align/ppt_layout_plan_v0.json` | unconfirmed after user feedback |
| Academic figure prompt | `align/academic_figure_prompt_v0.md` | unconfirmed / do not use for generation |

## 3. High-level fidelity check

| Surface | QA result | Evidence anchor |
| --- | --- | --- |
| Defense thesis | Pass. Main claim is grounded in the final fact ledger: fact-constrained multi-round preference clarification, not a generic LLM demo. | `fact_ledger_v0.md` §1-3 |
| Action-title spine | Pass with wording constraint. Most slide titles are source-backed; contribution/close wording should use "initially supports" / "technical path" rather than production-grade proof. | `PPT_storyboard_v0.md` Slides 1-20; `ppt_speaker_notes_rehearsal_v0.md` Slide 20 |
| Speaker notes | Pass. Notes repeatedly include safe fallbacks for product claims, UCB optimality, significance, real-user limits, and LLM fact boundaries. | `ppt_speaker_notes_rehearsal_v0.md` §2, §7 |
| Q&A answers | Pass. Q&A answers do not promise unsupported experiments, production deployment, or real-user validation. | `ppt_defense_qa_backup_v0.md` Q01-Q17 |
| Asset decisions | Blocked. User rejected the current AI-generated chart-like visual route and requested splitting the dense algorithm figure. | `PPT_asset_audit_v0.md`; `visual_enrichment_plan_v0.md`; `ppt_user_feedback_v1.md` |
| Academic figure prompt | Blocked. The prompt is now unconfirmed and must not be used for image generation. | `academic_figure_prompt_v0.md`; `ppt_user_feedback_v1.md` |

## 4. Findings and required repairs

| Issue ID | Anchor | Claim or decision under review | Source basis / gap | Severity | Owner stage | Required repair |
| --- | --- | --- | --- | --- | --- | --- |
| CFQ-001 | Slide 2; B14 | Use 阳光高考 / 夸克高考 as examples of existing solutions. | The deck has user-confirmed framing, but product details and screenshots are current facts. A quick public-page check supports existence and broad product category, not a full product evaluation. 阳光高考 should still be manually captured because automated local access returned HTTP 412. | major | ppt-deck-build | Choose one route before final deck build: (A) abstract 3-column table with no screenshots and no detailed feature claims, or (B) capture current official/public pages, record URL and access date on the slide notes or backup, and keep the claim limited to "information entry / query / advice generation". |
| CFQ-002 | Slides 16-18; B10-B11 | Experimental results support mechanism contribution. | Fact ledger supports the numbers and trend framing, but standard deviations and limited external validity mean the deck must not claim statistical dominance or production-grade validation. | major | ppt-deck-build | Use "整体趋势", "初步支持", "机制贡献" and "头部推荐/偏好对齐趋势"; do not use "显著碾压", "充分证明", or "所有场景领先". |
| CFQ-003 | Slide 20 | Closing title says the system has "已证明" the technical path. | Speaker notes already softened this to "初步支持了一个技术路径"; fact ledger warns against production-level claims. | major | ppt-deck-build | Soften the final slide title/callout to "初步支持高风险推荐中先问清底线再推荐的技术路径" or equivalent. Do not say production effectiveness is proven. |
| CFQ-004 | Slide 8; B04 | Reuse `fig_3_1_v1_hybrid_rag_flow` or `agent_workflow_2` for the static retrieval gap. | Asset audit marks source consistency check needed because some project assets may be stale relative to final thesis. | minor | ppt-deck-build | Prefer final thesis figure/source. If using `agent_workflow_2`, verify it matches final thesis wording before insertion; otherwise redraw as an editable abstract comparison. |
| CFQ-005 | Slide 5; B15 | Create horizontal system architecture figure from the original vertical architecture. | Confirmed decision is source-derived redraw from `render_system_architecture()` without overwriting the thesis vertical figure. Risk is semantic drift during horizontal condensation. | minor | ppt-deck-build | Preserve four-layer semantics, LLM/data boundary, and evidence flow; label it as PPT redraw/source-derived, not a new architecture. |
| CFQ-006 | V-AI01; Slide 9 or B16 | Generate algorithm macro-flow + microscope insets. | Prompt is source-derived and confirmed. Generation is still not allowed until this QA artifact is user-confirmed and the user separately approves image generation. | minor | image-generation gate | If generated later, use only the confirmed English prompt; keep API/model/output parameters outside the prompt; reject outputs that include real school names, scores, product UI, or experimental-looking charts. |
| CFQ-007 | Figure 1 / chart-like mechanism insets | Use AI-generated line/threshold/trend visuals. | User review says overlays/trends do not align and such visuals should be produced from real data/code, not AI. | blocker | ppt-asset-layout-plan | Replace chart-like mechanism visuals with local code-generated plots or editable deterministic PPT objects. |
| CFQ-008 | Figure 2 / dense algorithm workflow visual | Keep the full recommendation-decision loop as one dense figure. | User review says the figure is too full and must be split; exact split requires focused discussion. | blocker | ppt-asset-layout-plan | Draft and confirm a split plan before deck rebuild. |
| CFQ-009 | Storyboard method/evidence sections | Use flow diagrams almost everywhere for method explanation. | User review says some parts are better expressed with formulas; detailed guidance will follow. | blocker | ppt-storyboard-stage | Revisit exhibit type per affected slide: formula-first, formula-plus-diagram, or flow-diagram-first. |

## 5. Pass criteria checklist

- [x] Every action title has a source-backed or user-confirmed basis, with repair constraints for over-strong wording.
- [x] Results, metrics, datasets, baselines, and limitations are grounded in the fact ledger.
- [ ] Generated visuals are not labeled as evidence and are routed through confirmed prompt + QA + user approval. Current V-AI01 route is unconfirmed after user feedback.
- [x] Q&A answers avoid unsupported experiments, production deployment, and replacement-of-human-advisor claims.
- [x] Backup slides map to expected questions and source anchors.
- [x] Assertion-evidence policy is preserved at the planning level: exhibit type, exhibit claim, and so-what are available for main slides.
- [x] No unresolved blocker was found.
- [x] All major issues have explicit deck-build repair routes.

## 6. Product-page spot check

This check is only for QA risk classification, not for final slide citation.

| Product / platform | Spot-check source | Safe use in deck |
| --- | --- | --- |
| 阳光高考 / 阳光志愿 | Search result: `https://gaokao.chsi.com.cn/?v=1`; local automated access returned HTTP 412 | May be referenced as an official information/service entry only after final deck build captures or records current evidence. Do not infer hidden-preference clarification capability from this page alone. |
| 夸克高考 | Local access OK: `https://vt.quark.cn/blm/pc-gaokao-1089/index` | May be referenced as an AI/志愿填报 product example if the final slide uses current captured evidence. Do not turn it into an experimental baseline or detailed competitor evaluation. |

## 7. Deck-build constraints

1. Do not insert product screenshots unless URL and access date are recorded.
2. Do not use AI image generation for experiment charts, thesis figures, UI screenshots, product UI, or chart-like mechanism curves/trend overlays.
3. Do not overwrite the thesis vertical `fig_4_1_system_architecture`; create a PPT-specific horizontal derivative if needed.
4. Do not present current V-AI01 as accepted evidence or accepted layout; revise/split it before use.
5. Do not strengthen UCB beyond engineering heuristic.
6. Do not show BT posterior as directly rewriting SQL, database filters, or hard-coded query parameters.
7. Do not use old manifest experiments as main evidence; keep them backup-only and mark them as project evolution / historical scope.
8. Do not say the system replaces real升学顾问 or has production-grade real-user validation.

## 8. Handoff

This QA artifact is currently unconfirmed. Do not update it back to `confirmed` until the revised asset/layout plan is confirmed and content fidelity QA is rerun.

```yaml
stage_status: unconfirmed
blocked_next_stage: ppt-deck-build
```

Next required action: revise `storyboard`, then rerun speaker notes, Q&A/backup planning, asset/layout planning, and `ppt-content-fidelity-qa-stage`.
