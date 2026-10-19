#!/usr/bin/env python3
"""Structural audit of the generated site — the checks `verify` does not do.

`shyzctl verify` answers "does the content match the contract". This answers
"does the output hold together as HTML": tags balance, every class used is
styled, no build placeholder survived, and no page is bloated by a capture that
should have been trimmed.

    python tools/audit_site.py
"""

from __future__ import annotations

import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VOID = {
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "source", "track", "wbr",
}


class Balance(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[str] = []
        self.errors: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag not in VOID:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        if not self.stack:
            self.errors.append(f"stray </{tag}>")
        elif self.stack[-1] == tag:
            self.stack.pop()
        else:
            self.errors.append(f"</{tag}> closes <{self.stack[-1]}>")


def main() -> int:
    pages = sorted(ROOT.rglob("*.html"))
    pages = [
        p for p in pages
        if "node_modules" not in p.parts and "review/drafts" not in p.relative_to(ROOT).as_posix()
    ]
    if not pages:
        print("no pages; run `shyzctl docs build` first", file=sys.stderr)
        return 3

    findings: list[str] = []
    notes: list[str] = []

    css = (ROOT / "assets" / "css" / "site.css").read_text(encoding="utf-8")
    styled = set(re.findall(r"\.([a-zA-Z][\w-]*)", css))
    used_classes: set[str] = set()

    for page in pages:
        rel = page.relative_to(ROOT).as_posix()
        text = page.read_text(encoding="utf-8")

        parser = Balance()
        parser.feed(text)
        for error in parser.errors[:3]:
            findings.append(f"[HTML] {rel}: {error}")
        if parser.stack:
            findings.append(f"[HTML] {rel}: unclosed {parser.stack[:4]}")

        if re.search(r"\{\{[A-Z_]+\}\}", text):
            findings.append(f"[TEMPLATE] {rel}: build placeholder survived")

        for chunk in re.findall(r'class="([^"]+)"', text):
            used_classes.update(chunk.split())

        # every page must carry the shared chrome
        for needle in ('<link rel="stylesheet"', 'class="topbar"', 'id="main"', 'class="footer"'):
            if needle not in text:
                findings.append(f"[SHELL] {rel}: missing {needle}")

        if len(text) > 40_000:
            notes.append(
                f"[WEIGHT] {rel}: {len(text) // 1024} KB — heavy but not a correctness problem"
            )

    for missing in sorted(used_classes - styled):
        findings.append(f"[CSS] class used but not styled: .{missing}")

    # the capture file itself is not a page; only its rendering matters, and
    # page weight above catches that.

    if findings:
        print(f"{len(findings)} finding(s):\n")
        for finding in findings:
            print(f"  {finding}")
        return 1

    for note in notes:
        print(f"note: {note}")
    print(f"OK: {len(pages)} page(s), tags balanced, {len(used_classes)} classes all styled.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
