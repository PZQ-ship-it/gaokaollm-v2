"""Count Python lines under gaokaollm_bench.

The script reports two scopes:

1. All Python files under gaokaollm_bench.
2. Core Python files after excluding temporary/test code and plotting/diagram code.

For each scope it prints physical lines and a conservative source-line count
that excludes blank lines, comment-only lines, and docstring-only lines.
"""

from __future__ import annotations

import argparse
import ast
import io
import tokenize
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROOT = REPO_ROOT / "gaokaollm_bench"

TEST_FILE_PREFIXES = ("test_",)
TEST_FILE_SUFFIXES = ("_test.py",)
PLOTTING_NAME_TOKENS = ("diagram", "figure", "plot", "chart")
PLOTTING_FILE_NAMES = {"render_thesis_diagrams.py"}


@dataclass(frozen=True)
class FileStats:
    path: Path
    physical_lines: int
    source_lines: int


@dataclass(frozen=True)
class ExcludedFile:
    path: Path
    reason: str
    stats: FileStats


@dataclass(frozen=True)
class ScopeStats:
    files: int
    physical_lines: int
    source_lines: int


def iter_python_files(root: Path) -> list[Path]:
    return sorted(
        path
        for path in root.rglob("*.py")
        if path.is_file()
        and "__pycache__" not in path.parts
        and not any(part.startswith(".") for part in path.parts)
    )


def _docstring_line_numbers(tree: ast.AST) -> set[int]:
    lines: set[int] = set()

    for node in ast.walk(tree):
        if not isinstance(
            node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
        ):
            continue
        body = getattr(node, "body", [])
        if not body:
            continue
        first = body[0]
        if not (
            isinstance(first, ast.Expr)
            and isinstance(getattr(first, "value", None), ast.Constant)
            and isinstance(first.value.value, str)
        ):
            continue
        start = getattr(first, "lineno", None)
        end = getattr(first, "end_lineno", None)
        if start is not None and end is not None:
            lines.update(range(start, end + 1))

    return lines


def _comment_only_line_numbers(text: str) -> set[int]:
    lines: set[int] = set()
    source_lines = text.splitlines()
    reader = io.StringIO(text).readline
    try:
        tokens = tokenize.generate_tokens(reader)
        for token in tokens:
            if token.type != tokenize.COMMENT:
                continue
            line_no = token.start[0]
            prefix = source_lines[line_no - 1][: token.start[1]]
            if not prefix.strip():
                lines.add(token.start[0])
    except tokenize.TokenError:
        return set()
    return lines


def count_file(path: Path) -> FileStats:
    text = path.read_text(encoding="utf-8")
    physical_lines = len(text.splitlines())
    blank_lines = {
        line_no
        for line_no, line in enumerate(text.splitlines(), start=1)
        if not line.strip()
    }
    comment_lines = _comment_only_line_numbers(text)
    try:
        docstring_lines = _docstring_line_numbers(ast.parse(text, filename=str(path)))
    except SyntaxError:
        docstring_lines = set()

    ignored_lines = blank_lines | comment_lines | docstring_lines
    source_lines = sum(
        1 for line_no in range(1, physical_lines + 1) if line_no not in ignored_lines
    )
    return FileStats(
        path=path, physical_lines=physical_lines, source_lines=source_lines
    )


def exclusion_reason(path: Path, root: Path) -> str | None:
    rel = path.relative_to(root)
    rel_parts = rel.parts
    name = path.name.lower()

    if "tests" in rel_parts:
        return "test/temp code"
    if name.startswith(TEST_FILE_PREFIXES) or name.endswith(TEST_FILE_SUFFIXES):
        return "test/temp code"
    if name in PLOTTING_FILE_NAMES or any(
        token in name for token in PLOTTING_NAME_TOKENS
    ):
        return "plotting/diagram code"
    return None


def summarize(stats: Iterable[FileStats]) -> ScopeStats:
    items = list(stats)
    return ScopeStats(
        files=len(items),
        physical_lines=sum(item.physical_lines for item in items),
        source_lines=sum(item.source_lines for item in items),
    )


def print_scope(label: str, stats: ScopeStats) -> None:
    print(f"{label}:")
    print(f"  files          : {stats.files}")
    print(f"  physical lines : {stats.physical_lines}")
    print(f"  source lines   : {stats.source_lines}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Count all Python lines in gaokaollm_bench and core lines after "
            "excluding tests/temp scripts and plotting/diagram scripts."
        )
    )
    parser.add_argument(
        "root",
        nargs="?",
        type=Path,
        default=DEFAULT_ROOT,
        help=f"Python package directory to scan. Defaults to {DEFAULT_ROOT}.",
    )
    parser.add_argument(
        "--list-excluded",
        action="store_true",
        help="Print every excluded file and the exclusion reason.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.root.resolve()
    if not root.exists():
        raise SystemExit(f"Path does not exist: {root}")
    if not root.is_dir():
        raise SystemExit(f"Path is not a directory: {root}")

    files = iter_python_files(root)
    all_stats = [count_file(path) for path in files]

    excluded: list[ExcludedFile] = []
    core_stats: list[FileStats] = []
    for stats in all_stats:
        reason = exclusion_reason(stats.path, root)
        if reason is None:
            core_stats.append(stats)
        else:
            excluded.append(ExcludedFile(stats.path, reason, stats))

    print(f"Scan root: {root}")
    print_scope("All Python code", summarize(all_stats))
    print()
    print_scope(
        "Core code, excluding tests/temp and plotting/diagram code",
        summarize(core_stats),
    )
    print()
    print_scope("Excluded code", summarize(item.stats for item in excluded))

    if args.list_excluded and excluded:
        print()
        print("Excluded files:")
        for item in excluded:
            rel = item.path.relative_to(root)
            print(
                f"  {rel} [{item.reason}; "
                f"{item.stats.physical_lines} physical, {item.stats.source_lines} source]"
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
