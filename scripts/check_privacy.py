#!/usr/bin/env python3
"""Fail when tracked files contain likely secrets or private information."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parent.parent
MAX_TEXT_BYTES = 2_000_000

FORBIDDEN_NAMES = {
    ".env",
    ".env.local",
    ".env.production",
    "id_dsa",
    "id_ecdsa",
    "id_ed25519",
    "id_rsa",
}
FORBIDDEN_SUFFIXES = {".key", ".p12", ".pfx", ".pem"}
DRAFT_PATH_COMPONENTS = {
    ".private",
    ".scratch",
    ".wip",
    "draft",
    "drafts",
    "notes-private",
    "private",
    "scratch",
    "wip",
}
DRAFT_PATH_PREFIXES = ("draft-", "private-", "scratch-", "wip-")

# Build a few signatures in pieces so this checker does not flag its own source.
PATTERNS = [
    (
        "private key material",
        re.compile("-----BEGIN " + r"(?:[A-Z0-9]+ )?PRIVATE KEY-----"),
    ),
    (
        "GitHub access token",
        re.compile(r"\bgh(?:p|o|u|s|r)_[A-Za-z0-9]{30,}\b"),
    ),
    (
        "AWS access key",
        re.compile(r"\bA(?:KIA|SIA)[A-Z0-9]{16}\b"),
    ),
    (
        "Google API key",
        re.compile(r"\bAIza[0-9A-Za-z_-]{30,}\b"),
    ),
    (
        "Slack token",
        re.compile(r"\bxox[baprs]-[0-9A-Za-z-]{10,}\b"),
    ),
    (
        "assigned credential",
        re.compile(
            r"(?i)\b(?:password|passwd|secret|api[_-]?key|access[_-]?token)"
            r"\s*[:=]\s*['\"]?([A-Za-z0-9_./+=-]{12,})"
        ),
    ),
    (
        "email address or other contact detail",
        re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I),
    ),
    (
        "US Social Security number",
        re.compile(r"(?<!\d)\d{3}-\d{2}-\d{4}(?!\d)"),
    ),
    (
        "local home-directory path",
        re.compile(
            r"(?:/" + "Users/" + r"|/" + "home/" + r")[^\s'\"<>]+"
        ),
    ),
]

PLACEHOLDERS = (
    "changeme",
    "example",
    "placeholder",
    "redacted",
    "replace_me",
    "sample",
    "test",
    "your_",
)


def repository_files(
    revision: str | None, paths: list[str], root: Path
) -> list[tuple[PurePosixPath, bytes]]:
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
            entries.append((PurePosixPath(relative.as_posix()), path.read_bytes()))
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
            name = raw_name.decode()
            content = subprocess.run(
                ["git", "show", f"{revision}:{name}"],
                cwd=root,
                check=True,
                capture_output=True,
            ).stdout
            entries.append((PurePosixPath(name), content))
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
        if path.is_file():
            entries.append((relative, path.read_bytes()))
    return entries


def read_text(data: bytes) -> str | None:
    if len(data) > MAX_TEXT_BYTES or b"\0" in data:
        return None
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root",
        default=str(ROOT),
        help="repository root to inspect; defaults to this public repository",
    )
    parser.add_argument(
        "--allow-draft-paths",
        action="store_true",
        help="do not reject draft-like paths (for the separate private workspace)",
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
        print("Privacy check failed: repository root does not exist.", file=sys.stderr)
        return 1

    for relative, data in repository_files(args.revision, args.path, root):
        lowered_name = relative.name.lower()
        if (
            lowered_name in FORBIDDEN_NAMES
            or relative.suffix.lower() in FORBIDDEN_SUFFIXES
        ):
            findings.append(f"{relative}: sensitive filename")

        lowered_parts = [part.lower() for part in relative.parts]
        if not args.allow_draft_paths and (
            any(part in DRAFT_PATH_COMPONENTS for part in lowered_parts)
            or any(part.startswith(DRAFT_PATH_PREFIXES) for part in lowered_parts)
        ):
            findings.append(f"{relative}: draft or private-workspace path")

        text = read_text(data)
        if text is None:
            continue

        for line_number, line in enumerate(text.splitlines(), start=1):
            for label, pattern in PATTERNS:
                match = pattern.search(line)
                if not match:
                    continue
                matched = match.group(0).lower()
                if label == "assigned credential" and any(
                    marker in matched for marker in PLACEHOLDERS
                ):
                    continue
                # Do not print the matching content: CI logs may also be public.
                findings.append(f"{relative}:{line_number}: possible {label}")

    if findings:
        print("Privacy check failed:", file=sys.stderr)
        for finding in findings:
            print(f"  - {finding}", file=sys.stderr)
        print(
            "Review each item. Remove private data; only adjust the checker when "
            "the content is deliberately public.",
            file=sys.stderr,
        )
        return 1

    print("Privacy check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
