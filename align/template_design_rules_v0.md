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
reset_reason: Formula-vs-flow design rule is under review after user feedback.
created_at: 2026-05-31
source_template: align/template_inventory_v0.md
---

# Template design rules v0

## 0. 2026-06-01 reset note

Status reset to `unconfirmed`. The previous rule that formulas should stay minimal in the main deck is under review. Some storyboard sections may need formula-first or formula-plus-diagram slides; detailed user feedback is pending.

## 1. Deck-level rules

- Aspect ratio: 4:3, `10.0 × 7.5 in`, matching `zjuslides.pptx`.
- Visual style: formal thesis defense, restrained academic design, not marketing/landing-page style.
- Layout principle: strict assertion-evidence. One action-title claim per slide; one dominant exhibit per evidence slide.
- Editability: titles, bullets, tables, callouts, arrows, legends, and source lines should be editable PowerPoint objects when feasible. Existing paper figures may be inserted as high-resolution images or converted from SVG/PDF.
- Main deck density: main slides should avoid dense appendix-level tables. Backup slides may be denser but still readable.

## 2. Typography

- Use the template theme fonts when possible. If missing during automation, use safe CJK fallbacks such as `Microsoft YaHei` for UI text and `SimSun` / `宋体` for formal academic body text.
- Suggested title size: 24-30 pt depending on title length.
- Suggested body size: 16-20 pt; avoid below 14 pt on main slides.
- Suggested chart label minimum: 10-11 pt; if labels fall below this, redraw or simplify.
- Source/citation line: 8-9 pt, bottom-left or bottom-right above footer; never compete with the main claim.
- Formula text: keep only minimal formulas in main deck; detailed formulas go to backup.

## 3. Color and branding

- Prefer template-derived colors and Zhejiang University / thesis style elements over new decorative palettes.
- For editable diagrams, use white or near-white fills, dark text, grey dividers, and one or two accent colors.
- Avoid saturated full-panel fills, gradient backgrounds, decorative orbs, and dark stock-photo backgrounds.
- For the optional generated academic algorithm visual, use a restrained academic palette compatible with the template. Draft recommendation for later prompt stage: Okabe-Ito style with steel blue, warm orange, and green accents, unless the template palette is sampled and used directly.

## 4. Slide archetypes

| Archetype | Preferred layout | Content rule |
| --- | --- | --- |
| Cover | layout 0 or 1 | Use thesis cover fields; no English subtitle. |
| One-exhibit evidence | layout 3 or 4 | Title + one figure/table + one short callout. |
| Comparison | layout 5 | Two or three columns; no dense paragraphs. |
| Method mechanism | layout 4 or custom on layout 6 | Diagram dominates; formula only as small inset. |
| Results chart | layout 3 | Chart large; one conclusion annotation; no table reading. |
| UI evidence | layout 5 | Pair cropped screenshots; avoid full-page screenshots. |
| Backup | layout 3 or 5 | May be denser, but must answer a real Q&A question. |
| Q&A separator | layout 6 or 7 | Minimal text. |

## 5. Forbidden patterns

- Do not place complete PDF pages as full-slide screenshots.
- Do not use generated images for numeric result charts, baselines, ablations, or screenshots.
- Do not imply that illustrative visuals are experimental evidence.
- Do not directly use the paper's vertical architecture figure on a wide content area; redraw or re-export a horizontal PPT version.
- Do not include old experiment figures in the main deck unless the confirmed fact ledger marks them as current.
- Do not claim product-specific capabilities for 阳光高考 / 夸克高考 without later source capture and verification.

## 6. Render QA expectations

- Check that all title text fits within the top safe area.
- Check that source lines do not overlap footers.
- Check that screenshots are legible at 100% slideshow size.
- Check that SVG/PDF converted assets do not lose fonts or thin lines.
- Check representative main and backup slides: cover, Slide 5 architecture, Slide 9 method overview, Slide 16-17 results, B01 fact boundary, B10 experiment backup, and Q&A separator.
