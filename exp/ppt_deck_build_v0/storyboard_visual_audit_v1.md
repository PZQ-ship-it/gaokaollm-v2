# Storyboard visual audit v1

Date: 2026-05-31

Scope: deck-build draft repair for `generated_pptx_test/gaokaollm_defense_deck_v0.pptx`.

## Checks

- Compared main talk slides against `align/PPT_storyboard_v0.md` intent and `align/ppt_speaker_notes_rehearsal_v0.md` talk-track role.
- Rendered representative slides through PowerPoint export under `exp/ppt_deck_build_v0/storyboard_visual_audit/`.
- Scanned PPT text for producer-facing phrases that should not be visible on slides.

## Fixed

| Area | Issue | Fix |
| --- | --- | --- |
| Producer-facing text | Several subtitles and callouts were copied from storyboard or notes as instructions, such as how to speak, what to avoid, or whether details go to backup. | Rewrote them into audience-facing claims and removed visible internal source/footer text. |
| Slide 4 | Used sparse boxes instead of an existing workflow visual. | Replaced with `crop_fig_5_1_mas_workflow.png` and a short audience-facing takeaway. |
| Slide 8 | Static baseline figure required by storyboard/QA was missing from the main talk. | Inserted `crop_fig_3_1_v1_hybrid_rag_flow.png` as the main visual. |
| Slide 10 | SAVF page looked like scattered draft boxes. | Added local deterministic visual `savf_mechanism_ppt.png` showing linear-weight trap, SAVF protection, and value curves. |
| Figure scale | Source diagrams had large white margins, making figures look small. | Added non-destructive cropped source copies `generated_assets/crop_*.png`; original thesis figures are unchanged. |
| Visual evidence | V-AI01, static baseline, workflow, and SAVF mechanism visuals needed proof of insertion. | Verified these images are embedded in the PPTX media package. |

## Current Evidence

- Screenshot contact sheet: `exp/ppt_deck_build_v0/storyboard_visual_audit/contact_storyboard_audit.png`
- PPTX output: `generated_pptx_test/gaokaollm_defense_deck_v0.pptx`
- Text scan: no visible `fallback`, `image not generated`, `Source:`, `deferred`, or producer-instruction phrases from the audit list.

## Remaining Judgment

- This is still a deck-build draft, not a confirmed deck.
- Backup slides remain utilitarian and may need a separate appendix-polish pass or hiding policy.
- Full formal render QA is still gated on deck-build confirmation.
