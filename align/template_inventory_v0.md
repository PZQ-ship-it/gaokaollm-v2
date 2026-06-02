---
stage: asset_layout_plan
stage_status: confirmed
requires_confirmed:
  - ppt_production_brief
  - fact_ledger
  - defense_narrative
  - storyboard
  - speaker_notes_rehearsal
  - defense_qa_backup
allowed_next_stage: academic-figure-prompt
confirmed_by: user, 2026-05-31
created_at: 2026-05-31
source_template: D:\毕设\latex-for-zju-master\latex-for-zju-master\zjuslides.pptx
---

# PPT template inventory v0

## 1. Template source

- Template file: `D:\毕设\latex-for-zju-master\latex-for-zju-master\zjuslides.pptx`
- Use policy: not strict reuse of original page sequence; reuse template visual language, school style, page bounds, footers, and restrained academic composition.
- Slide size: `10.0 in × 7.5 in`, 4:3.
- Recommendation: keep the deck template-native 4:3. Rebuilding as 16:9 would require recreating the template style and more render QA; wide diagrams should be made as horizontal visuals inside 4:3 pages.
- Detected structure: 9 slides, 1 slide master, 9 layouts, 8 embedded media files, 3 theme XML files.

## 2. Layout inventory

Layout names are partially garbled under the Windows console encoding, so build should identify them by index and placeholder pattern.

| Layout index | Detected pattern | Best use in this deck | Notes |
| --- | --- | --- | --- |
| 0 | title / cover placeholders | Cover page | Use for Slide 1 if template cover style remains readable; no English subtitle. |
| 1 | title cover variant with several body placeholders | Alternative cover / title-with-metadata | Use only if cover metadata needs more fields. |
| 2 | title cover variant with several body placeholders | Section divider or title variant | Optional; avoid if too decorative. |
| 3 | title + full content placeholder + footer/date/page number | Standard evidence slide | Default for diagrams, charts, tables, screenshots. |
| 4 | title + subtitle/body strip + full content placeholder | Assertion-evidence slide with one-line setup | Useful for Slides 5, 6, 9, 15 where a short evidence cue sits above a figure. |
| 5 | title + subtitle/body strip + two equal content placeholders | Two-column comparison | Useful for Slide 2 product comparison, Slide 14 UI pair, selected backup comparisons. |
| 6 | title-only + footer/date/page number | Section divider / conclusion | Useful for concise transition or Q&A separator. |
| 7 | centered body placeholder + footer/date/page number | Quote / thesis statement / thank-you | Useful for Slide 4 or Slide 21 if minimal. |
| 8 | split placeholders, one text block and one large body/media area | Text-plus-visual | Useful for limitation, contribution, or summary slide. |

## 3. Placeholder geometry summary

Approximate coordinate system: 10.0 in wide, 7.5 in high.

| Layout | Safe content estimate | Use constraint |
| --- | --- | --- |
| 3 | title at top; main content about x=0.44, y=1.02, w=9.12, h=5.91 | Best for one large figure or table. |
| 4 | title; subtitle strip around y=1.03; main content about x=0.44, y=1.75, w=9.12, h=5.19 | Best for assertion + evidence. |
| 5 | title; subtitle strip; two panels about w=4.38 each | Best for A/B, product comparison, before/after. |
| 6 | title-only, no body placeholder | Use with custom drawn shapes. |
| 8 | split text/media body | Use for limitation or final contribution. |

Footer/date/page-number placeholders sit near the bottom edge. Keep charts and diagrams above y≈6.85 in, unless intentionally using a full-bleed figure.

## 4. Template risks

- The template is 4:3, while many generated or modern web visuals default to 16:9. Any generated academic visual should either be 4:3 or have a 4:3-safe crop.
- Console output does not preserve CJK layout names; use layout indices in automation.
- Source/citation lines must not collide with footer placeholders.
- Complex screenshots may be too small in 4:3; prefer cropping, paired panels, or backup-only placement.
- The template has enough layout variants for this deck; no Figma route is needed unless explicitly requested.
