"""Count Python lines in this repository.

By default the script scans the repository root and reports:

1. Physical lines for every tracked-looking Python source file.
2. Source lines after excluding blank lines, comment-only lines, and docstrings.
3. A breakdown by top-level directory.
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
DEFAULT_EXCLUDED_DIRS = {
    ".cache",
    ".git",
    ".mypy_cache",
    ".omx",
    ".playwright-cli",
    ".qodo",
    ".ruff_cache",
    ".runtime",
    ".venv",
    "__pycache__",
    "venv",
}


@dataclass(frozen=True)
class FileStats:
    path: Path
    physical_lines: int
    source_lines: int


@dataclass(frozen=True)
class Summary:
    files: int
    physical_lines: int
    source_lines: int


def is_excluded(path: Path, root: Path, excluded_dirs: set[str]) -> bool:
    try:
        relative = path.relative_to(root)
    except ValueError:
        return True
    return any(part in excluded_dirs for part in relative.parts)


def iter_python_files(root: Path, excluded_dirs: set[str]) -> list[Path]:
    return sorted(
        path
        for path in root.rglob("*.py")
        if path.is_file() and not is_excluded(path, root, excluded_dirs)
    )


def read_python_source(path: Path) -> str:
    with tokenize.open(path) as handle:
        return handle.read()


def docstring_line_numbers(text: str, path: Path) -> set[int]:
    lines: set[int] = set()
    try:
        tree = ast.parse(text, filename=str(path))
    except SyntaxError:
        return lines

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


def comment_only_line_numbers(text: str) -> set[int]:
    lines: set[int] = set()
    source_lines = text.splitlines()
    reader = io.StringIO(text).readline
    try:
        for token in tokenize.generate_tokens(reader):
            if token.type != tokenize.COMMENT:
                continue
            line_no = token.start[0]
            prefix = source_lines[line_no - 1][: token.start[1]]
            if not prefix.strip():
                lines.add(line_no)
    except tokenize.TokenError:
        return set()
    return lines


def count_file(path: Path) -> FileStats:
    text = read_python_source(path)
    split_lines = text.splitlines()
    physical_lines = len(split_lines)
    blank_lines = {
        line_no for line_no, line in enumerate(split_lines, start=1) if not line.strip()
    }
    ignored_lines = (
        blank_lines
        | comment_only_line_numbers(text)
        | docstring_line_numbers(text, path)
    )
    source_lines = sum(
        1 for line_no in range(1, physical_lines + 1) if line_no not in ignored_lines
    )
    return FileStats(
        path=path, physical_lines=physical_lines, source_lines=source_lines
    )


def summarize(stats: Iterable[FileStats]) -> Summary:
    items = list(stats)
    return Summary(
        files=len(items),
        physical_lines=sum(item.physical_lines for item in items),
        source_lines=sum(item.source_lines for item in items),
    )


def top_level_name(path: Path, root: Path) -> str:
    relative = path.relative_to(root)
    return relative.parts[0] if len(relative.parts) > 1 else "."


def print_summary(label: str, summary: Summary) -> None:
    print(f"{label}:")
    print(f"  files          : {summary.files}")
    print(f"  physical lines : {summary.physical_lines}")
    print(f"  source lines   : {summary.source_lines}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Count Python lines in the repository."
    )
    parser.add_argument(
        "root",
        nargs="?",
        type=Path,
        default=REPO_ROOT,
        help=f"Directory to scan. Defaults to repository root: {REPO_ROOT}",
    )
    parser.add_argument(
        "--include-cache",
        action="store_true",
        help="Do not exclude cache/runtime directories such as __pycache__.",
    )
    parser.add_argument(
        "--list-files",
        action="store_true",
        help="Print per-file line counts after the summary.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.root.resolve()
    if not root.exists():
        raise SystemExit(f"Path does not exist: {root}")
    if not root.is_dir():
        raise SystemExit(f"Path is not a directory: {root}")

    excluded_dirs = set() if args.include_cache else DEFAULT_EXCLUDED_DIRS
    stats = [count_file(path) for path in iter_python_files(root, excluded_dirs)]

    print(f"Scan root: {root}")
    if excluded_dirs:
        print(f"Excluded dirs: {', '.join(sorted(excluded_dirs))}")
    print_summary("All Python code", summarize(stats))

    by_top_level: dict[str, list[FileStats]] = {}
    for item in stats:
        by_top_level.setdefault(top_level_name(item.path, root), []).append(item)

    print()
    print("By top-level path:")
    for name in sorted(by_top_level):
        summary = summarize(by_top_level[name])
        print(
            f"  {name:<18} files={summary.files:>3} "
            f"physical={summary.physical_lines:>6} source={summary.source_lines:>6}"
        )

    if args.list_files:
        print()
        print("Files:")
        for item in stats:
            rel = item.path.relative_to(root)
            print(
                f"  {rel}: physical={item.physical_lines}, source={item.source_lines}"
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
