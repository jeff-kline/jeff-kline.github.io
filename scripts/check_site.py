#!/usr/bin/env python3
"""Validate the shared landing-page structure and HTML formatting contract."""

from __future__ import annotations

import argparse
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


class LandingPageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.doctype = False
        self.html_lang = ""
        self.h1_count = 0
        self.h1_text: list[str] = []
        self.in_h1 = False
        self.main_count = 0
        self.title_text: list[str] = []
        self.in_title = False
        self.charset = ""
        self.viewport = ""

    def handle_decl(self, declaration: str) -> None:
        if declaration.lower() == "doctype html":
            self.doctype = True

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "html":
            self.html_lang = attributes.get("lang") or ""
        elif tag == "main":
            self.main_count += 1
        elif tag == "h1":
            self.h1_count += 1
            self.in_h1 = True
        elif tag == "title":
            self.in_title = True
        elif tag == "meta":
            if "charset" in attributes:
                self.charset = (attributes["charset"] or "").lower()
            if (attributes.get("name") or "").lower() == "viewport":
                self.viewport = attributes.get("content") or ""

    def handle_endtag(self, tag: str) -> None:
        if tag == "h1":
            self.in_h1 = False
        elif tag == "title":
            self.in_title = False

    def handle_data(self, data: str) -> None:
        if self.in_h1:
            self.h1_text.append(data)
        if self.in_title:
            self.title_text.append(data)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root",
        default=str(ROOT),
        help="site root to validate; defaults to this public repository",
    )
    source = parser.add_mutually_exclusive_group()
    source.add_argument(
        "--revision",
        help="inspect the landing page at this Git revision",
    )
    source.add_argument(
        "--path",
        action="append",
        default=[],
        help="only check when index.html is among the selected current paths",
    )
    parser.add_argument(
        "--all-html",
        action="store_true",
        help="validate every HTML file in the selected site root",
    )
    return parser.parse_args()


def sources_for(args: argparse.Namespace, root: Path) -> list[tuple[str, str]]:
    if args.revision:
        if args.all_html:
            names = [
                item.decode()
                for item in subprocess.run(
                    ["git", "ls-tree", "-r", "-z", "--name-only", args.revision],
                    cwd=root,
                    check=True,
                    capture_output=True,
                ).stdout.split(b"\0")
                if item and item.decode().lower().endswith(".html")
            ]
        else:
            names = ["index.html"]
        return [
            (
                name,
                subprocess.run(
                    ["git", "show", f"{args.revision}:{name}"],
                    cwd=root,
                    check=True,
                    capture_output=True,
                    text=True,
                ).stdout,
            )
            for name in names
        ]

    if args.all_html:
        names = [path.relative_to(root).as_posix() for path in root.rglob("*.html")]
    elif args.path:
        names = ["index.html"] if "index.html" in args.path else []
    else:
        names = ["index.html"]
    return [(name, (root / name).read_text(encoding="utf-8")) for name in names]


def validate_source(name: str, source: str) -> list[str]:
    findings: list[str] = []
    for line_number, line in enumerate(source.splitlines(), start=1):
        if line.rstrip() != line:
            findings.append(f"{name}:{line_number}: trailing whitespace")
        if "\t" in line:
            findings.append(f"{name}:{line_number}: use spaces, not tabs")
        indentation = len(line) - len(line.lstrip(" "))
        if line.strip() and indentation % 4:
            findings.append(
                f"{name}:{line_number}: indentation must use multiples of four spaces"
            )

    parser = LandingPageParser()
    try:
        parser.feed(source)
        parser.close()
    except Exception as error:
        findings.append(f"{name}: invalid HTML: {error}")

    if not parser.doctype:
        findings.append(f"{name}: missing <!DOCTYPE html>")
    if not parser.html_lang:
        findings.append(f"{name}: <html> must declare a language")
    if parser.charset != "utf-8":
        findings.append(f"{name}: missing UTF-8 charset metadata")
    if "width=device-width" not in parser.viewport:
        findings.append(f"{name}: missing responsive viewport metadata")
    if not "".join(parser.title_text).strip():
        findings.append(f"{name}: missing a non-empty <title>")
    if parser.main_count != 1:
        findings.append(f"{name}: landing page must contain exactly one <main>")
    if parser.h1_count != 1 or not "".join(parser.h1_text).strip():
        findings.append(f"{name}: landing page must contain one non-empty <h1>")
    return findings


def main() -> int:
    args = parse_args()
    root = Path(args.root).resolve()
    if not root.is_dir():
        print("Site format check failed: site root does not exist.", file=sys.stderr)
        return 1

    try:
        sources = sources_for(args, root)
    except (OSError, subprocess.CalledProcessError) as error:
        print(f"Site format check failed: {error}", file=sys.stderr)
        return 1

    if not sources:
        print("Site format check skipped: no HTML files were selected.")
        return 0

    findings = [finding for name, source in sources for finding in validate_source(name, source)]

    if findings:
        print("Site format check failed:", file=sys.stderr)
        for finding in findings:
            print(f"  - {finding}", file=sys.stderr)
        return 1

    print("Site format check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
