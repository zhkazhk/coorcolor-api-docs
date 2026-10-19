#!/usr/bin/env python3
"""Create the publishable source snapshot under contracts/source/.

The published documentation cites `server/index.js:<line>` and
`server/wxpay-utils.js:<line>`. Those citations are only useful if a reader can
open the exact lines, so the snapshot has to ship with the site. The snapshot is
therefore redacted: every credential is replaced **in place**, on the same line,
so line numbers and the contract hash stay stable while no secret is published.

Rules are expressed as patterns, never as literal secrets, so this file is safe
to commit. `main()` refuses to write the snapshot if anything that looks like a
credential survives.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

RULES: list[tuple[str, str, str]] = [
    # (file glob, pattern, replacement) — replacement keeps the line shape.
    ("index.js", r"(const\s+JWT_SECRET\s*=\s*)'[^']*'", r"\1'<REDACTED:jwt-secret>'"),
    ("index.js", r"(const\s+appId\s*=\s*)'[^']*'", r"\1'<REDACTED:wx-appid>'"),
    ("index.js", r"(const\s+appSecret\s*=\s*)'[^']*'", r"\1'<REDACTED:wx-appsecret>'"),
    ("wxpay-config.js", r"(appId:\s*)'[^']*'", r"\1'<REDACTED:wx-appid>'"),
    ("wxpay-config.js", r"(mchId:\s*)'[^']*'", r"\1'<REDACTED:wxpay-mchid>'"),
    ("wxpay-config.js", r"(apiKey:\s*)'[^']*'", r"\1'<REDACTED:wxpay-apikey>'"),
    ("wxpay-config.js", r"(notifyUrl:\s*)'[^']*'", r"\1'<REDACTED:notify-url>'"),
]

FILES = ["index.js", "wxpay-utils.js", "wxpay-config.js"]

# A credential shape we never want to publish, whatever its variable name.
SUSPICIOUS = [
    re.compile(r"\b[0-9a-f]{32}\b"),          # 32 hex chars (WeChat appsecret / API key shape)
    re.compile(r"\bwx[0-9a-f]{16}\b"),        # WeChat appid shape
    re.compile(r"\b1[1-9]\d{9}\b"),           # a real mainland mobile number
]


def redact(text: str, filename: str) -> tuple[str, int]:
    count = 0
    for glob, pattern, replacement in RULES:
        if glob != filename:
            continue
        text, n = re.subn(pattern, replacement, text)
        count += n
    return text, count


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: redact_snapshot.py <path-to-server-dir> [-o <out-dir>]", file=sys.stderr)
        return 2
    src = Path(argv[1])
    if "-o" in argv:
        out = Path(argv[argv.index("-o") + 1])
    else:
        out = ROOT / "contracts" / "source"
    if not src.is_dir():
        print(f"source directory not found: {src}", file=sys.stderr)
        return 3

    out.mkdir(parents=True, exist_ok=True)
    total = 0
    for name in FILES:
        path = src / name
        if not path.exists():
            print(f"skip (missing): {name}", file=sys.stderr)
            continue
        original = path.read_text(encoding="utf-8")
        text, n = redact(original, name)
        assert text.count("\n") == original.count("\n"), f"{name}: redaction changed line count"
        (out / name).write_text(text, encoding="utf-8", newline="\n")
        total += n
        print(f"redacted {n:>2} literal(s) in {name} -> {out / name}")

    # guard: make sure nothing credential-shaped survived in the publishable copy
    leftovers = []
    for name in FILES:
        target = out / name
        if not target.exists():
            continue
        for lineno, line in enumerate(target.read_text(encoding="utf-8").splitlines(), 1):
            if "REDACTED" in line:
                continue
            for pattern in SUSPICIOUS:
                if pattern.search(line):
                    leftovers.append(f"{name}:{lineno}: {line.strip()[:90]}")
    if leftovers:
        print("\nREFUSING TO PUBLISH — suspicious literals survived:", file=sys.stderr)
        for item in leftovers:
            print(f"  {item}", file=sys.stderr)
        return 1

    print(f"\n{total} literal(s) redacted; no credential-shaped strings remain.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
