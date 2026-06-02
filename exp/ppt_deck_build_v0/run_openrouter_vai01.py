# -*- coding: utf-8 -*-
"""Generate the confirmed V-AI01 figure through the OpenRouter ICU skill."""

from __future__ import annotations

import pathlib
import re
import subprocess
import sys


ROOT = pathlib.Path(__file__).resolve().parents[2]
PROMPT_ARTIFACT = ROOT / "align" / "academic_figure_prompt_v0.md"
OUTPUT = (
    ROOT
    / "exp"
    / "ppt_deck_build_v0"
    / "generated_assets"
    / "v_ai01_openrouter_icu.png"
)
SKILL_SCRIPT = pathlib.Path(
    r"C:\Users\Administrator\.codex\skills\openrouter-icu-image\scripts\openrouter_icu_image.py"
)


def extract_confirmed_prompt() -> str:
    text = PROMPT_ARTIFACT.read_text(encoding="utf-8")
    if "stage_status: confirmed" not in text:
        raise RuntimeError(f"Prompt artifact is not confirmed: {PROMPT_ARTIFACT}")
    match = re.search(r"```text\s*\r?\n(?P<prompt>.*?)\r?\n```", text, re.S)
    if not match:
        raise RuntimeError(f"Could not extract prompt text block: {PROMPT_ARTIFACT}")
    return match.group("prompt").strip()


def main() -> int:
    prompt = extract_confirmed_prompt()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        str(SKILL_SCRIPT),
        "generate",
        "--prompt",
        prompt,
        "--output",
        str(OUTPUT),
        "--size",
        "1536x1152",
        "--quality",
        "medium",
        "--output-format",
        "png",
        "--stream",
        "true",
        "--partial-images",
        "2",
        "--save-partials",
        "--retries",
        "2",
    ]
    return subprocess.run(cmd).returncode


if __name__ == "__main__":
    raise SystemExit(main())
