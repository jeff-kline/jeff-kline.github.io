#!/usr/bin/env python3
"""Perform deterministic spelling, typography, and basic grammar checks."""

from __future__ import annotations

import argparse
import html
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parent.parent
PROSE_SUFFIXES = {".html", ".md", ".txt"}
COMMON_TYPOS = {
    "acommodate": "accommodate",
    "adress": "address",
    "alot": "a lot",
    "arguement": "argument",
    "beleive": "believe",
    "calender": "calendar",
    "definately": "definitely",
    "dependancy": "dependency",
    "enviroment": "environment",
    "goverment": "government",
    "grammer": "grammar",
    "independant": "independent",
    "occured": "occurred",
    "publically": "publicly",
    "recieve": "receive",
    "seperate": "separate",
    "succesful": "successful",
    "teh": "the",
    "untill": "until",
    "wierd": "weird",
}


def prose_files(
    revision: str | None, paths: list[str], root: Path
) -> list[tuple[PurePosixPath, str]]:
    if paths:
        root_resolved = root.resolve()
        entries = []
        for raw_path in paths:
            path = (root / raw_path).resolve()
            try:
                relative = path.relative_to(root_resolved)
            except ValueError as error:
                raise ValueError(f"path is outside the repository: {raw_path}") from error
            if not path.is_file():
                raise ValueError(f"path is not a file: {raw_path}")
            if relative.suffix.lower() in PROSE_SUFFIXES:
                entries.append(
                    (PurePosixPath(relative.as_posix()), path.read_text(encoding="utf-8"))
                )
        return entries

    if revision:
        result = subprocess.run(
            ["git", "ls-tree", "-r", "-z", "--name-only", revision],
            cwd=root,
            check=True,
            capture_output=True,
        )
        entries = []
        for raw_name in result.stdout.split(b"\0"):
            if not raw_name:
                continue
            relative = PurePosixPath(raw_name.decode())
            if relative.suffix.lower() not in PROSE_SUFFIXES:
                continue
            data = subprocess.run(
                ["git", "show", f"{revision}:{relative}"],
                cwd=root,
                check=True,
                capture_output=True,
            ).stdout
            entries.append((relative, data.decode("utf-8")))
        return entries

    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=root,
        check=True,
        capture_output=True,
    )
    entries = []
    for raw_name in result.stdout.split(b"\0"):
        if not raw_name:
            continue
        relative = PurePosixPath(raw_name.decode())
        path = root / relative
        if relative.suffix.lower() in PROSE_SUFFIXES and path.is_file():
            entries.append((relative, path.read_text(encoding="utf-8")))
    return entries


def prose_only(text: str, suffix: str) -> str:
    if suffix == ".html":
        text = re.sub(r"(?is)<(?:script|style)\b.*?</(?:script|style)>", " ", text)
        text = re.sub(r"(?s)<!--.*?-->", " ", text)
        text = re.sub(r"(?s)<[^>]+>", " ", text)
        return html.unescape(text)

    if suffix == ".md":
        text = re.sub(r"(?s)```.*?```", " ", text)
        text = re.sub(r"`[^`]*`", "code", text)
        text = re.sub(r"\]\([^)]+\)", "]", text)
        text = re.sub(r"https?://\S+", "url", text)
    return text


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root",
        default=str(ROOT),
        help="repository root to inspect; defaults to this public repository",
    )
    source = parser.add_mutually_exclusive_group()
    source.add_argument(
        "--revision",
        help="inspect the exact repository snapshot at this Git revision",
    )
    source.add_argument(
        "--path",
        action="append",
        default=[],
        help="inspect this current repository file; may be specified more than once",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    findings: list[str] = []
    root = Path(args.root).resolve()
    if not root.is_dir():
        print("Writing check failed: repository root does not exist.", file=sys.stderr)
        return 1
    typo_pattern = re.compile(
        r"\b(" + "|".join(map(re.escape, COMMON_TYPOS)) + r")\b", re.I
    )

    for relative, source in prose_files(args.revision, args.path, root):
        prose = prose_only(source, relative.suffix.lower())

        for line_number, line in enumerate(prose.splitlines(), start=1):
            for match in typo_pattern.finditer(line):
                typo = match.group(0).lower()
                findings.append(
                    f"{relative}:{line_number}: '{match.group(0)}' may be a typo; "
                    f"use '{COMMON_TYPOS[typo]}'"
                )

            repeated = re.search(r"(?i)\b([a-z][a-z'-]{1,})\s+\1\b", line)
            if repeated:
                findings.append(
                    f"{relative}:{line_number}: repeated word '{repeated.group(1)}'"
                )

            if re.search(r"\s+[,.!?;:]", line):
                findings.append(
                    f"{relative}:{line_number}: unexpected space before punctuation"
                )

    if findings:
        print("Writing check failed:", file=sys.stderr)
        for finding in findings:
            print(f"  - {finding}", file=sys.stderr)
        return 1

    print("Writing check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
