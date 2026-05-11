"""Lightweight terminology regression check for thesis prose.

This script is intentionally read-only: it scans thesis-facing prose for
implementation terms that should be replaced by academic terminology. It does
not connect to PostgreSQL, call an LLM, or modify files.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_MAPPING = REPO_ROOT / "gaokaollm_bench" / "outputs" / "thesis_term_mapping.json"

# Contexts where verbatim ids are acceptable because they are tables,
# appendices, paths, or machine-readable manifests.
ALLOWED_PATH_PARTS = {
    "3-appendix.tex",
    "term_mapping.json",
    "thesis_claims_manifest.json",
    "thesis_term_mapping.json",
}
ENTRYPOINT_WARNING_PATH_PARTS = {
    "CODEX.md",
    "README.md",
    "thesis_document_hub.md",
}

# Terms that are acceptable as broad academic/technical vocabulary in this
# thesis. The mapping still documents them, but they should not fail checks.
ACADEMIC_ALLOWED_TERMS = {
    "PostgreSQL",
    "SQL",
    "Agent",
    "Benchmark",
    "MAS",
    "evidence",
}


@dataclass(frozen=True)
class Finding:
    severity: str
    path: Path
    line_no: int
    term: str
    suggestion: str
    line: str


def _read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _default_latex_root() -> Path | None:
    candidate = Path(r"D:\毕设\latex-for-zju-master\latex-for-zju-master")
    return candidate if candidate.exists() else None


def _scan_files(latex_root: Path | None) -> list[Path]:
    files: list[Path] = [
        REPO_ROOT / "CODEX.md",
        REPO_ROOT / "gaokaollm_bench" / "README.md",
        REPO_ROOT / "gaokaollm_bench" / "outputs" / "README.md",
        REPO_ROOT / "gaokaollm_bench" / "outputs" / "thesis_document_hub.md",
        REPO_ROOT / "gaokaollm_bench" / "outputs" / "thesis_claims_manifest.json",
    ]
    if latex_root is not None:
        final = latex_root / "body" / "undergraduate" / "final"
        files.extend(
            [
                final / "abstract.tex",
                final / "3-appendix.tex",
                final / "term_mapping.json",
            ]
        )
        files.extend(sorted((final / "chapters").glob("*.tex")))
    return [p for p in files if p.exists()]


def _line_allows_term(path: Path, line: str, term: str) -> bool:
    name = path.name
    if name in ALLOWED_PATH_PARTS:
        return True
    if "\\texttt{" in line or "\\path{" in line:
        return True
    if "\\includegraphics" in line or "\\label{" in line or "\\ref{" in line:
        return True
    if term in ACADEMIC_ALLOWED_TERMS:
        return True
    # Result-table rows may retain experiment ids in parentheses.
    if "\\texttt{" in line and term.endswith("_v1"):
        return True
    return False


def _terms_from_mapping(mapping: dict[str, object]) -> dict[str, str]:
    terms: dict[str, str] = {}
    for section in ("implementation_terms", "experiment_ids", "internal_fields"):
        values = mapping.get(section, {})
        if isinstance(values, dict):
            for key, value in values.items():
                if isinstance(key, str) and isinstance(value, str):
                    terms[key] = value
    # Explicit high-risk phrases found during prior thesis cleanups.
    terms.update(
        {
            "reviewed v1": "经人工审校的地域层级画像",
            "reviewed region-tree": "经人工审校的地域层级证据",
            "DB gap": "真实数据差距",
            "hidden flexibility": "潜在偏好弹性",
            "offline deterministic": "离线确定性",
            "outputs/": "复现材料说明中的路径",
            "sample_data/": "复现材料说明中的路径",
            "reports/": "复现材料说明中的路径",
            "transcripts/": "复现材料说明中的路径",
        }
    )
    return dict(sorted(terms.items(), key=lambda item: len(item[0]), reverse=True))


def scan(
    mapping: dict[str, object], files: Iterable[Path], strict: bool
) -> list[Finding]:
    terms = _terms_from_mapping(mapping)
    findings: list[Finding] = []
    for path in files:
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = path.read_text(encoding="utf-8-sig")
        for line_no, line in enumerate(text.splitlines(), 1):
            for term, suggestion in terms.items():
                if term not in line:
                    continue
                if _line_allows_term(path, line, term):
                    continue
                severity = "error"
                if path.name in ENTRYPOINT_WARNING_PATH_PARTS and not strict:
                    severity = "warning"
                findings.append(
                    Finding(
                        severity=severity,
                        path=path,
                        line_no=line_no,
                        term=term,
                        suggestion=suggestion,
                        line=line.strip(),
                    )
                )
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description="Check thesis terminology usage.")
    parser.add_argument("--mapping", type=Path, default=DEFAULT_MAPPING)
    parser.add_argument("--latex-root", type=Path, default=_default_latex_root())
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    mapping = _read_json(args.mapping)
    files = _scan_files(args.latex_root)
    findings = scan(mapping, files, args.strict)

    errors = [f for f in findings if f.severity == "error"]
    warnings = [f for f in findings if f.severity == "warning"]
    for finding in findings:
        rel = finding.path
        try:
            rel = finding.path.relative_to(REPO_ROOT)
        except ValueError:
            pass
        print(
            f"{finding.severity.upper()}: {rel}:{finding.line_no}: "
            f"{finding.term!r} -> {finding.suggestion}"
        )
        print(f"  {finding.line}")
    print(
        f"Checked {len(files)} files. errors={len(errors)} warnings={len(warnings)} "
        f"strict={args.strict}"
    )
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
