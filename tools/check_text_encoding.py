from __future__ import annotations

import argparse
import sys
from pathlib import Path


TEXT_SUFFIXES = {
    ".css",
    ".html",
    ".js",
    ".json",
    ".jsx",
    ".md",
    ".ps1",
    ".py",
    ".ts",
    ".tsx",
    ".txt",
    ".yaml",
    ".yml",
}

SKIP_DIRS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "dist",
    "node_modules",
}


def should_check(path: Path) -> bool:
    if any(part in SKIP_DIRS for part in path.parts):
        return False
    return path.suffix.lower() in TEXT_SUFFIXES or path.name in {".editorconfig"}


def has_utf8_bom(data: bytes) -> bool:
    return data.startswith(b"\xef\xbb\xbf")


def check_file(path: Path) -> str | None:
    data = path.read_bytes()
    try:
        data.decode("utf-8")
    except UnicodeDecodeError as exc:
        return f"{path}: not valid UTF-8 ({exc})"

    if path.suffix.lower() != ".csv" and has_utf8_bom(data):
        return f"{path}: UTF-8 BOM is only allowed for CSV files"

    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Check TeamTools text files use UTF-8.")
    parser.add_argument("--root", default=".", help="Project root directory.")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    failures: list[str] = []

    for path in sorted(root.rglob("*")):
        if not path.is_file() or not should_check(path.relative_to(root)):
            continue
        failure = check_file(path)
        if failure:
            failures.append(failure)

    if failures:
        print("Encoding check failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("Encoding check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

