# Reference layout study v0

Date: 2026-05-31

Reference deck: `应雨轩-毕业答辩V1.pptx`

Current draft: `generated_pptx_test/gaokaollm_defense_deck_v0.pptx`

## Render evidence

- Reference deck export: `exp/ppt_deck_build_v0/reference_yingyuxuan/`
- Reference contact sheet: `exp/ppt_deck_build_v0/reference_yingyuxuan/contact_sheet.png`
- Current main-slide export: `exp/ppt_deck_build_v0/current_v0_export/`
- Current main-slide contact sheet: `exp/ppt_deck_build_v0/current_v0_export/contact_main_1_21.png`

## Reference deck layout logic

- The reference deck is 16:9, 24 slides, while the current defense deck is 4:3. The layout language can be borrowed, but the exact geometry cannot be copied directly.
- The reference deck uses one stable visual system across the talk: light blue title band, large pale university watermark, bottom college band, and generous white body space.
- Section divider pages are almost empty: one section title, large watermark, and bottom band. They create rhythm and make the defense feel less like a continuous wall of diagrams.
- Most content pages use one dominant visual region. Explanatory text is either a short top-level claim, a side note, or a lower summary box.
- Dense pages still have a clear hierarchy: title claim first, then one large figure/table/chart, then a small explanation box. The page rarely contains many unrelated floating cards.
- Result pages are built around visible evidence: large screenshots, diagrams, or charts; text explains the meaning of the evidence instead of competing with it.

## What transfers to the 4:3 deck

- Use a lighter, thinner header area so the slide body gets more vertical space.
- Keep the school identity, but shift from a heavy dark banner to a watermark/band style where possible.
- Replace scattered callout groups with a repeated page grammar: one main visual plus one compact evidence/takeaway strip.
- Add or restore section divider pages for pacing: problem, system/method, experiment, conclusion, backup.
- Enforce a small set of content templates instead of page-by-page custom placement.

## Current draft gaps seen from the comparison

- The deep blue header consumes too much visual weight on 4:3 slides and makes body figures feel smaller.
- Several pages still read as generated diagrams placed into empty space, especially when the diagram is centered with detached callout cards on the right.
- Experiment slides have chart grids plus vertical side notes, but the notes look like reviewer comments rather than designed figure captions.
- Slide 18 has visible right-side content running off the rendered slide area, so it needs layout repair before any formal render QA.
- The current deck still lacks the reference deck's pacing: there are few quiet divider/transition pages, so dense diagrams and charts arrive back-to-back.

## Proposed improvement direction

1. Establish a revised 4:3 master grammar:
   - thin title band or compact school header;
   - optional pale watermark;
   - fixed body grid with one main visual zone;
   - one short takeaway strip or side explanation box.
2. Rebuild the main talk around page types:
   - cover and agenda;
   - section dividers;
   - problem framing;
   - system/process visual;
   - mechanism explanation;
   - experiment evidence;
   - conclusion and Q&A.
3. Prioritize visual repair before wording polish:
   - enlarge paper-derived figures and charts;
   - remove floating note-card clutter;
   - convert internal notes into audience-facing claims;
   - keep generated V-AI01 as explanatory visual only, not as new evidence.
4. Postpone backup-slide polish unless the main 21-slide talk is visually stable.

