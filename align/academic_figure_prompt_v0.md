---
stage: academic_figure_prompt
stage_status: unconfirmed
requires_confirmed:
  - ppt_production_brief
  - fact_ledger
  - storyboard
  - asset_layout_plan
blocked_next_stage: ppt-content-fidelity-qa-stage
previously_confirmed_by: user, 2026-05-31
reset_by: user, 2026-06-01
reset_reason: Current AI-figure route rejected for chart-like mechanism visuals and dense layout.
created_at: 2026-05-31
source_skill: https://github.com/LigphiDonk/academic-figure-generator/tree/main/academic-figure-prompt
source_visual_plan: align/visual_enrichment_plan_v0.md
source_asset_layout_plan: align/ppt_layout_plan_v0.json
---

# Academic figure prompt v0

## 0. 2026-06-01 reset note

Status reset to `unconfirmed`. This prompt must not be used for further image generation or deck insertion without a revised, confirmed asset/layout plan.

User feedback:

- The chart-like line overlays/trends in the generated visual are not aligned; if such visuals are needed, they should be created with real data or deterministic code/editable PPT objects, not AI image generation.
- The full pipeline visual is too crowded; it should be split into several figures/slides. The exact split is a focus discussion item.

## Figure V-AI01 - Algorithm macro flow with algorithm microscopes

Figure type: framework / module detail hybrid.

Source anchors:

- `fact_ledger_v0.md` §5: SAVF, UCB, Pareto candidate pairs, Bradley-Terry posterior, runtime state.
- `PPT_storyboard_v0.md` Slides 9-12: method overview and mechanism pages.
- `ppt_speaker_notes_rehearsal_v0.md` §6-7: candidate explanatory visual and risk constraints.
- `visual_enrichment_plan_v0.md` V-AI01: generated academic visual boundary.

Palette: Okabe-Ito academic standard, compatible with template style.

- Steel Blue `#0072B2`
- Warm Orange `#E69F00`
- Bluish Green `#009E73`
- Charcoal text `#263238`
- Light grey dividers `#CFD8DC`
- Off-white background `#FAFAFA`

Recommended aspect ratio: 4:3, slide-safe for a `10.0 × 7.5 in` thesis-defense PPT.

Generation boundary:

- May visualize abstract mechanism representations: vectors, candidate cards, curves, uncertainty bars, posterior weights, feedback arrows.
- Must not invent real school names, real majors, real scores, product screenshots, experiment numbers, or new claims.
- Must not show language model output as factual school/score generation.
- Must not show BT posterior as directly rewriting SQL/query/filter parameters; it may influence next probing axis, candidate scoring, and final explanation.
- Must not be treated as experimental evidence. It is an explanatory, source-derived academic visual.
- Must keep text minimal because final Chinese labels may be overlaid in PowerPoint.

```text
A highly detailed, information-dense academic presentation framework diagram explaining a fact-constrained multi-round preference elicitation algorithm for high-stakes college application recommendation. The diagram should be a 4:3 slide-safe horizontal workflow with a clean academic paper style, mostly white space, thin vector-like lines, and restrained color. The visual is explanatory, not experimental evidence.

Overall layout:
Use a left-to-right pipeline across the center of the slide, with six main stages connected by labeled arrows:
1. User request and explicit constraints
2. Evidence-grounded candidate set
3. SAVF bottom-line protection
4. UCB probing-axis selection
5. Pareto A/B tradeoff question and user feedback
6. Bradley-Terry posterior preference state and final recommendation explanation

Place three magnified "algorithm microscope" insets above or below the central pipeline: one for SAVF, one for UCB, and one for Pareto/BT feedback. Each inset must contain internal substructure, not an empty labeled box.

=== INPUT REPRESENTATION ===
Create a left panel labeled "USER REQUEST". Show a small speech bubble with abstract, non-real text tokens such as "region", "budget", "major fit", "risk". Next to it show a compact structured preference vector with four horizontal bars:
- region preference
- tuition/budget constraint
- major fit
- risk tolerance
Do not include real student data, real locations, real scores, or real universities.

=== EVIDENCE-GROUNDED CANDIDATES ===
Create a panel labeled "EVIDENCE CANDIDATES". Show a grid of 6 to 8 abstract candidate cards. Each card contains simple icons or miniature fields: school tier dot, major fit bar, tuition marker, region tag, risk band. Use neutral placeholder codes such as C1, C2, C3 instead of real school names. Add a small database cylinder behind the candidate grid labeled "verified facts" to indicate the candidate facts come from an evidence layer, not from language model generation.

Add a thin arrow from USER REQUEST to EVIDENCE CANDIDATES labeled "constraint parsing + evidence retrieval".

=== SAVF MICROSCOPE: BOTTOM-LINE PROTECTION ===
Create a magnified inset labeled "SAVF: bottom-line protection". Inside the inset, show three small single-attribute value curves:
- budget curve with a sharp drop after a threshold
- major-fit curve with a red/orange penalty zone for severe mismatch
- region curve with a soft decay zone
Below the curves, show three candidate cards before/after scoring. One card with severe violation is visibly suppressed or greyed out. Add a small formula-like annotation without exact math: "attribute value -> penalty -> protected score".
Use warm orange to highlight penalty zones and steel blue for safe value curves.

=== UCB MICROSCOPE: PROBING AXIS SELECTION ===
Create a magnified inset labeled "UCB: choose what to ask next". Show four vertical axis bars named generically:
- region
- major
- tuition
- risk
For each axis, show two stacked visual components: a benefit-signal segment and an uncertainty segment. The selected axis should be highlighted with a thin green outline and a small pointer labeled "next question axis". Add a tiny annotation: "benefit signal + uncertainty". Do not claim theoretical optimality; visually imply a heuristic ranking.

=== PARETO A/B TRADEOFF QUESTION ===
Create a central panel labeled "PARETO A/B TRADEOFF". Show two large candidate cards side by side, A and B. Card A should be safer but weaker on one attribute; Card B should be stronger on one attribute but requires relaxing another. Use small arrows and plus/minus markers to show marginal substitution:
- "safer risk" vs "better major fit"
- "closer region" vs "higher tuition"
Do not use any real school names, real majors, or scores. Use abstract labels and icons only.

Place a user feedback widget below the A/B cards with three simple options: prefer A, prefer B, uncertain. Use minimal text and icon-like check marks. Add a thin arrow from feedback to the posterior state panel.

=== BT POSTERIOR AND STATE UPDATE ===
Create a right-side panel labeled "POSTERIOR STATE". Show a row of preference weight bars and uncertainty whiskers for region, major, tuition, and risk. The bars should update from pale grey to steel blue / green. Add a curved feedback arrow from POSTERIOR STATE back to UCB MICROSCOPE labeled "next round state". Also add a forward arrow to a small final report card labeled "explainable recommendation".

Important: show the posterior state as influencing the next probing axis, candidate scoring, and explanation. Do not show it directly rewriting SQL, database filters, or hard-coded query parameters.

=== FINAL OUTPUT ===
Create a small final panel labeled "RECOMMENDATION EXPLANATION". Show three abstract recommendation bands: safe, balanced, aspirational. Each band has one or two candidate placeholders and a short explanation strip. The explanation strip should visually connect back to evidence candidates and posterior preferences with thin arrows.

=== GLOBAL ANNOTATIONS ===
Use thin arrows with semantic labels:
- "evidence facts"
- "protected scoring"
- "probe axis"
- "tradeoff feedback"
- "posterior update"
- "next round"
Use dashed grey arrows only for feedback loops. Use solid arrows for forward algorithm flow.

Include a small legend in the lower-right corner:
- blue: evidence-grounded scoring
- orange: bottom-line penalty
- green: selected probing or updated preference
- grey: feedback or uncertainty

=== STYLE SPECIFICATIONS ===
Use a clean academic figure style suitable for a thesis defense slide. Keep at least 70 percent of the background white or near-white. Use white module fills with colored borders, not saturated colored panels. Use charcoal text, thin grey dividers, and consistent rounded rectangles with small radius. Typography should be sans-serif, large and legible, with short labels only. Avoid long paragraphs inside the image.

Palette:
- background #FAFAFA
- text #263238
- divider #CFD8DC
- steel blue #0072B2
- warm orange #E69F00
- bluish green #009E73
- muted grey #90A4AE

Line weights:
- main arrows 2 px
- module borders 1.5 px
- inset borders 2 px
- feedback arrows dashed 1.5 px

Composition rules:
- no real people
- no decorative stock imagery
- no university logos
- no product screenshots
- no real school names
- no real scores or ranks
- no experimental result numbers
- no hallucinated data tables
- no API parameters or runtime instructions
- no file paths
- no model names
- no dense unreadable text
- no empty placeholder boxes
- no ellipses or vague "etc." labels
```

## Self-check

- [x] Information density: the figure has a full pipeline and three detailed insets.
- [x] Source-fact constraints: all mechanisms trace to the confirmed fact ledger and storyboard.
- [x] Restrained palette: Okabe-Ito academic colors with mostly white background.
- [x] Grayscale readability: modules use borders, arrows, bars, and line styles in addition to color.
- [x] No API/path/model parameters mixed into the prompt.
- [x] No generated evidence: prompt forbids real scores, school names, result charts, screenshots, and new claims.

## Handoff

- This prompt is currently unconfirmed and superseded by user feedback.
- Do not call `openrouter-icu-image` from this prompt.
- Route back to `ppt-asset-layout-plan` to replace V-AI01 with a split local-code/editable visual plan.
