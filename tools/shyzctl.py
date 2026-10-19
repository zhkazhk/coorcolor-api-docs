#!/usr/bin/env python3
"""shyzctl — the documentation contract CLI for the CoorColor / SHYZ API docs.

Every published page on this site is checked by this tool. It has three jobs:

  1. `contract`  derive a machine-readable contract from the Express source and
                 keep it in lock-step with the committed snapshot.
  2. `verify`    prove that the published HTML still matches the contract and
                 that every cross-reference, error entry and support tag
                 resolves to a real page anchor.
  3. `explain`   let a reader (or a CI job) query the error catalogue without
                 opening the site.

Exit codes are documented in cli/index.html and are part of the tool contract.
They are mirrored by EXIT_CODES below, which the site generator imports, so the
table on the page cannot drift from the code.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path

VERSION = "1.3.0"

# --- exit codes -------------------------------------------------------------
# Single source of truth. sitegen.py imports this dict to render the table in
# cli/index.html, so the documentation and the implementation cannot diverge.
EXIT_CODES = {
    0: ("OK", "Every check passed, or the requested data was printed."),
    1: ("FINDINGS", "One or more documentation defects were found. Details on stdout."),
    2: ("USAGE", "The command line was wrong. argparse also exits 2 for unknown flags."),
    3: ("MISSING_INPUT", "A required file (source, contract or catalogue) does not exist."),
    4: ("DRIFT", "The committed contract no longer matches the Express source."),
    5: ("INTERNAL", "Unexpected crash. This is always a bug in shyzctl, never in the docs."),
}

EXIT_OK = 0
EXIT_FINDINGS = 1
EXIT_USAGE = 2
EXIT_MISSING_INPUT = 3
EXIT_DRIFT = 4
EXIT_INTERNAL = 5

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE = ROOT / "contracts" / "source" / "index.js"
DEFAULT_CONTRACT = ROOT / "contracts" / "shyz-api-contract.json"
DEFAULT_CATALOG = ROOT / "errors" / "catalog.json"
DEFAULT_DOCS = ROOT

# --- source extraction ------------------------------------------------------

ENDPOINT_RE = re.compile(
    r"^app\.(get|post|put|delete|patch)\(\s*'([^']+)'\s*,?", re.MULTILINE
)
MIDDLEWARE_DEF_RE = re.compile(
    r"^const\s+(\w+)\s*=\s*\(\s*req\s*,\s*res\s*,\s*next\s*\)\s*=>\s*\{", re.MULTILINE
)
ERROR_JSON_RE = re.compile(
    r"status\(\s*(\d{3})\s*\)\s*\.\s*json\(\s*\{\s*code\s*:\s*(-?\d+)\s*,\s*message\s*:\s*([^}]*)\}",
    re.DOTALL,
)
# WeChat pay callbacks answer in XML, not JSON. Capture that failure shape too so
# the contract covers every way a handler can say "no".
XML_FAILURE_RE = re.compile(
    r"return_code:\s*'([A-Z]+)'\s*,\s*return_msg:\s*([^}]*)\}", re.DOTALL
)
SUCCESS_JSON_RE = re.compile(r"res\.(?:json|send)\(\s*\{\s*code\s*:\s*0")
FIELD_ERROR_RE = re.compile(r"errors\.push\(\s*'([^']+)'")
MIDDLEWARE_END_RE = re.compile(r"^\};", re.MULTILINE)
STRING_RE = re.compile(r"'([^'\n]*)'")
# Only a real header read counts. A bare `authorization` substring also matches
# `grant_type=authorization_code` in the getOpenid URL, which is not auth.
AUTH_RE = re.compile(r"req\.headers\.authorization", re.IGNORECASE)


def _messages_from_expr(expr: str) -> list[str]:
    """Pull the human-readable strings out of a `message:` expression.

    Handles the three shapes the codebase actually uses:
      message: '订单不存在'                  -> ['订单不存在']
      message: errors.join('；')             -> every literal in the expression
      message: data.errmsg || '获取openid失败' -> ['获取openid失败'] plus literals
    """
    found = [s for s in STRING_RE.findall(expr) if s.strip()]
    if "message:" in expr:  # defensive: never leak the key itself
        found = [s for s in found if s != "message:"]
    return found or [expr.strip()[:60]]


def _handler_bodies(source: str) -> list[dict]:
    """Slice each `app.<verb>('<path>' ...)` registration off the source."""
    matches = list(ENDPOINT_RE.finditer(source))
    bodies = []
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(source)
        chunk = source[start:end]
        line = source.count("\n", 0, m.start()) + 1
        bodies.append(
            {
                "method": m.group(1).upper(),
                "path": m.group(2),
                "line": line,
                "start_offset": start,
                "body": chunk,
            }
        )
    return bodies


def _middlewares(source: str) -> dict[str, dict]:
    out: dict[str, dict] = {}
    defs = list(MIDDLEWARE_DEF_RE.finditer(source))
    for m in defs:
        start = m.end()
        end_match = MIDDLEWARE_END_RE.search(source, start)
        end = end_match.start() if end_match else len(source)
        body = source[start:end]
        errors = []
        for e in ERROR_JSON_RE.finditer(body):
            errors.append(
                {
                    "status": int(e.group(1)),
                    "code": int(e.group(2)),
                    "messages": _messages_from_expr(e.group(3)),
                    "line": source.count("\n", 0, start + e.start()) + 1,
                }
            )
        out[m.group(1)] = {
            "name": m.group(1),
            "line": source.count("\n", 0, m.start()) + 1,
            "errors": errors,
            "messages": [msg for e in errors for msg in e["messages"]],
            # Validation middleware accumulates per-field reasons and joins them,
            # so the envelope message (`；`) is not the useful text. Keep them.
            "field_messages": [
                {"message": mm.group(1), "line": source.count("\n", 0, start + mm.start()) + 1}
                for mm in FIELD_ERROR_RE.finditer(body)
            ],
            "status_codes": sorted({e["status"] for e in errors}),
        }
    return out


def build_contract(source_path: Path) -> dict:
    source = source_path.read_text(encoding="utf-8", errors="replace")
    middlewares = _middlewares(source)
    endpoints = []

    for raw in _handler_bodies(source):
        body = raw["body"]
        offset = raw["start_offset"]
        header = body.split("\n", 1)[0] if "\n" in body else body
        attached = [name for name in middlewares if re.search(rf"\b{name}\b", header)]

        errors = []
        for e in ERROR_JSON_RE.finditer(body):
            errors.append(
                {
                    "status": int(e.group(1)),
                    "code": int(e.group(2)),
                    "messages": _messages_from_expr(e.group(3)),
                    "line": source.count("\n", 0, offset + e.start()) + 1,
                }
            )
        for e in XML_FAILURE_RE.finditer(body):
            errors.append(
                {
                    "status": 200,
                    "code": -1,
                    "transport": "xml",
                    "return_code": e.group(1),
                    "messages": _messages_from_expr(e.group(2)),
                    "line": source.count("\n", 0, offset + e.start()) + 1,
                }
            )
        for name in attached:
            mw = middlewares[name]
            for err in mw["errors"]:
                errors.append({**err, "via": name})

        status_codes = sorted({e["status"] for e in errors} | {200})
        auth = "bearer" if AUTH_RE.search(body) else "none"
        # GET /api/user/info answers 200 with a guest profile when no token is
        # present; no other route does. Match on that branch, not on the generic
        # success shape (which PUT /api/user/info shares).
        if auth == "bearer" and "nickname: '用户'" in body:
            auth = "optional-bearer"

        significant = body.rstrip()
        field_messages = [
            field["message"]
            for name in attached
            for field in middlewares[name]["field_messages"]
        ]
        # Every human-readable literal the handler can put on the wire, error or
        # not. The error catalogue quotes success text too ("验证码已发送"), so it
        # is validated against this wider vocabulary while the reference pages
        # stay strict and must quote an actual error message.
        vocabulary = sorted(
            {s.strip() for s in STRING_RE.findall(body) if len(s.strip()) >= 2} | set(field_messages)
        )
        endpoints.append(
            {
                "id": _slug(raw["method"], raw["path"]),
                "method": raw["method"],
                "path": raw["path"],
                "line": raw["line"],
                "end_line": raw["line"] + significant.count("\n"),
                "auth": auth,
                "status_codes": status_codes,
                "errors": errors,
                "middleware": [
                    {
                        "name": name,
                        "line": middlewares[name]["line"],
                        "field_messages": middlewares[name]["field_messages"],
                    }
                    for name in attached
                ],
                "messages": sorted({m for e in errors for m in e["messages"]} | set(field_messages)),
                "strings": vocabulary,
            }
        )

    endpoints.sort(key=lambda e: (e["line"],))
    return {
        "contract_version": 1,
        "generator": f"shyzctl {VERSION} contract build",
        "source": {
            "file": "server/index.js",
            "lines": source.count("\n") + 1,
            "sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
        },
        "envelope": {
            "success": {"http": 200, "body": {"code": 0, "data": "<payload>"}},
            "failure": {"http": "4xx / 5xx", "body": {"code": -1, "message": "<reason>"}},
            "note": "There are no machine-readable error codes. Clients must match the `message` string.",
        },
        "middlewares": sorted(middlewares.values(), key=lambda m: m["line"]),
        "endpoints": endpoints,
        "totals": {
            "endpoints": len(endpoints),
            "methods": {m: sum(1 for e in endpoints if e["method"] == m)
                        for m in sorted({e["method"] for e in endpoints})},
            "distinct_messages": len({m for e in endpoints for m in e["messages"]}),
        },
    }


def _slug(method: str, path: str) -> str:
    cleaned = path.strip("/").replace("/", "-").replace(":", "").replace("_", "-")
    return f"{method.lower()}-{cleaned}" if cleaned else method.lower()


def load_contract(path: Path) -> dict:
    if not path.exists():
        raise SystemExit(_fail(EXIT_MISSING_INPUT, f"contract not found: {path}"))
    return json.loads(path.read_text(encoding="utf-8"))


def find_endpoint(contract: dict, method: str, path: str) -> dict | None:
    method = method.upper()
    for e in contract["endpoints"]:
        if e["method"] == method and e["path"] == path:
            return e
    return None


# --- verify -----------------------------------------------------------------

HTML_LINK_RE = re.compile(r'href="([^"]+)"')
ID_RE = re.compile(r'\bid="([^"]+)"')
SUPPORT_TAG_RE = re.compile(r"\[(API-ref|exit-code|error-catalog)\]")
# `server/index.js:1026-1056` and `server/index.js:312` are citations a reader is
# meant to open, so they have to point inside the published snapshot.
CITATION_RE = re.compile(r"server/([a-z-]+\.js):(\d+)(?:-(\d+))?")


def _iter_pages(docs: Path):
    for p in sorted(docs.rglob("*.html")):
        if any(part in {"node_modules", ".git"} for part in p.parts):
            continue
        yield p


def verify(docs: Path, contract_path: Path, catalog_path: Path) -> list[str]:
    findings: list[str] = []
    contract = load_contract(contract_path)

    if not docs.exists():
        return [f"docs directory not found: {docs}"]
    if not catalog_path.exists():
        return [f"error catalogue not found: {catalog_path}"]

    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))

    # index pages and their anchor ids, for link resolution
    anchors: dict[Path, set[str]] = {}
    pages: list[Path] = []
    for page in _iter_pages(docs):
        pages.append(page)
        anchors[page] = set(ID_RE.findall(page.read_text(encoding="utf-8", errors="replace")))

    if not pages:
        return ["no HTML pages found; run `shyzctl docs build` first"]

    rel = lambda p: p.relative_to(docs).as_posix()  # noqa: E731

    # 1. every documented endpoint must exist in the contract
    for page in pages:
        text = page.read_text(encoding="utf-8", errors="replace")
        for method, path in re.findall(r'data-endpoint="([A-Z]+)\s+([^"]+)"', text):
            if find_endpoint(contract, method, path) is None:
                findings.append(
                    f"[DRIFT] {rel(page)}: documents `{method} {path}` which is not in the contract"
                )

    # 2. every documented status code / message must exist for that endpoint
    for page in pages:
        text = page.read_text(encoding="utf-8", errors="replace")
        blocks = re.split(r'data-endpoint="', text)
        for block in blocks[1:]:
            head = block.split('"', 1)[0]
            try:
                method, path = head.split(" ", 1)
            except ValueError:
                continue
            ep = find_endpoint(contract, method, path)
            if ep is None:
                continue
            for status in re.findall(r"data-status=\"(\d{3})\"", block):
                if int(status) not in ep["status_codes"]:
                    findings.append(
                        f"[DRIFT] {rel(page)}: `{method} {path}` documents HTTP {status}, "
                        f"source only emits {ep['status_codes']}"
                    )
            for msg in re.findall(r'data-message="([^"]+)"', block):
                if msg not in ep["messages"]:
                    findings.append(
                        f"[DRIFT] {rel(page)}: `{method} {path}` documents message `{msg}` "
                        f"which does not occur in the source handler"
                    )

    # 3. error catalogue entries must point at real pages and real contract facts
    seen_ids: set[str] = set()
    for entry in catalog.get("entries", []):
        eid = entry.get("id", "<missing id>")
        if eid in seen_ids:
            findings.append(f"[CATALOG] duplicate entry id: {eid}")
        seen_ids.add(eid)

        for field in ("symptom", "cause", "next_step", "doc", "verify"):
            if not entry.get(field):
                findings.append(f"[CATALOG] {eid}: missing required field `{field}`")

        doc = entry.get("doc", "")
        if doc:
            target, _, anchor = doc.partition("#")
            target_path = (docs / target).resolve()
            if not target_path.exists():
                findings.append(f"[CATALOG] {eid}: doc link `{doc}` does not resolve to a file")
            elif anchor and anchor not in anchors.get(target_path, set()):
                findings.append(f"[CATALOG] {eid}: doc link `{doc}` anchor #{anchor} not found")

        endpoint = entry.get("endpoint")
        if endpoint:
            method, _, path = endpoint.partition(" ")
            ep = find_endpoint(contract, method, path)
            if ep is None:
                findings.append(f"[CATALOG] {eid}: endpoint `{endpoint}` is not in the contract")
            else:
                if entry.get("http") and int(entry["http"]) not in ep["status_codes"]:
                    findings.append(
                        f"[CATALOG] {eid}: HTTP {entry['http']} not emitted by `{endpoint}` "
                        f"({ep['status_codes']})"
                    )
                if entry.get("message") and entry["message"] not in ep.get("strings", []):
                    findings.append(
                        f"[CATALOG] {eid}: message `{entry['message']}` does not occur in `{endpoint}`"
                    )

    # 4. every relative link and every support tag must resolve
    tag_targets = {"[API-ref]": set(), "[exit-code]": set(), "[error-catalog]": set()}
    source_lines = {"index.js": contract["source"]["lines"]}
    for name in ("wxpay-utils.js", "wxpay-config.js"):
        snapshot = docs / "contracts" / "source" / name
        if snapshot.exists():
            source_lines[name] = len(snapshot.read_text(encoding="utf-8", errors="replace").splitlines())

    for page in pages:
        text = page.read_text(encoding="utf-8", errors="replace")
        text = text.replace("&amp;", "&")
        for href in HTML_LINK_RE.findall(text):
            if href.startswith(("http://", "https://", "mailto:", "#")) or href.endswith(".png"):
                continue
            target, _, anchor = href.partition("#")
            target_path = (page.parent / target).resolve() if target else page.resolve()
            if not target_path.exists():
                findings.append(f"[LINK] {rel(page)}: broken link `{href}`")
            elif anchor and anchor not in anchors.get(target_path, set()):
                findings.append(f"[LINK] {rel(page)}: missing anchor in `{href}`")
        for tag in SUPPORT_TAG_RE.findall(text):
            tag_targets[f"[{tag}]"] |= {rel(page)}

        # cited source lines must exist, and an endpoint page must cite its handler
        citations = CITATION_RE.findall(text)
        endpoint_head = re.search(r'data-endpoint="([A-Z]+)\s+([^"]+)"', text)
        if endpoint_head:
            method, path = endpoint_head.group(1), endpoint_head.group(2)
            ep = find_endpoint(contract, method, path)
            if ep and not any(int(start) == ep["line"] for _, start, _ in citations):
                findings.append(
                    f"[CITE] {rel(page)}: cites no source line for `{method} {path}` "
                    f"(handler starts at index.js:{ep['line']})"
                )
        for name, start, end in citations:
            total = source_lines.get(name)
            if total is None:
                findings.append(f"[CITE] {rel(page)}: cites `server/{name}`, which is not in the snapshot")
                continue
            for label, value in (("start", start), ("end", end)):
                if value and not 1 <= int(value) <= total:
                    findings.append(
                        f"[CITE] {rel(page)}: `server/{name}:{start}"
                        f"{'-' + end if end else ''}` {label} is outside 1-{total}"
                    )
            if end and int(end) < int(start):
                findings.append(f"[CITE] {rel(page)}: `server/{name}:{start}-{end}` is reversed")

    for entry in catalog.get("entries", []):
        for tag in entry.get("tags", []):
            key = f"[{tag}]" if not tag.startswith("[") else tag
            if key not in tag_targets:
                findings.append(f"[CATALOG] {entry.get('id')}: unknown support tag `{key}`")

    # 5. the review log must cite tags that exist somewhere on the site
    review = docs / "review" / "index.html"
    if not review.exists():
        findings.append("[REVIEW] review/index.html is missing")
    else:
        text = review.read_text(encoding="utf-8", errors="replace")
        for tag in SUPPORT_TAG_RE.findall(text):
            key = f"[{tag}]"
            if not tag_targets.get(key):
                findings.append(f"[REVIEW] support tag {key} is used but no page carries it")

    return findings


# --- output helpers ---------------------------------------------------------

def _fail(code: int, message: str) -> int:
    prefix = EXIT_CODES.get(code, ("ERROR", ""))[0]
    print(f"{prefix}: {message}", file=sys.stderr)
    return code


def _table(rows: list[list[str]], headers: list[str]) -> str:
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))
    line = "  ".join(h.ljust(widths[i]) for i, h in enumerate(headers))
    out = [line, "  ".join("-" * w for w in widths)]
    for row in rows:
        out.append("  ".join(cell.ljust(widths[i]) for i, cell in enumerate(row)))
    return "\n".join(out)


# --- commands ---------------------------------------------------------------

def cmd_contract_build(args) -> int:
    source = Path(args.source)
    if not source.exists():
        return _fail(EXIT_MISSING_INPUT, f"Express source not found: {source}")
    contract = build_contract(source)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(contract, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"contract written: {out}\n"
        f"  endpoints       {contract['totals']['endpoints']}\n"
        f"  methods         {contract['totals']['methods']}\n"
        f"  distinct msgs   {contract['totals']['distinct_messages']}\n"
        f"  source sha256   {contract['source']['sha256'][:16]}…"
    )
    return EXIT_OK


def cmd_contract_check(args) -> int:
    committed_path = Path(args.contract)
    if not committed_path.exists():
        return _fail(EXIT_MISSING_INPUT, f"contract not found: {committed_path}")
    committed = json.loads(committed_path.read_text(encoding="utf-8"))
    source = Path(args.source)
    if not source.exists():
        print(
            "DRIFT: cannot re-derive the contract, source snapshot is absent.\n"
            f"       expected at {source}",
            file=sys.stderr,
        )
        return EXIT_DRIFT
    fresh = build_contract(source)
    if fresh["source"]["sha256"] != committed["source"]["sha256"]:
        print("DRIFT: the source snapshot changed; regenerate the contract.", file=sys.stderr)
        return EXIT_DRIFT
    print(f"OK: contract matches source snapshot ({committed['source']['sha256'][:16]}…)")
    return EXIT_OK


def cmd_endpoints(args) -> int:
    contract = load_contract(Path(args.contract))
    rows = []
    for ep in contract["endpoints"]:
        if args.method and ep["method"] != args.method.upper():
            continue
        if args.grep and args.grep.lower() not in ep["path"].lower():
            continue
        rows.append(
            [
                ep["method"],
                ep["path"],
                ",".join(str(s) for s in ep["status_codes"]),
                ep["auth"],
                str(ep["line"]),
            ]
        )
    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return EXIT_OK
    print(_table(rows, ["METHOD", "PATH", "STATUS", "AUTH", "LINE"]))
    print(f"\n{len(rows)} endpoint(s)")
    return EXIT_OK


def cmd_show(args) -> int:
    contract = load_contract(Path(args.contract))
    ep = find_endpoint(contract, args.method, args.path)
    if ep is None:
        return _fail(EXIT_FINDINGS, f"no endpoint {args.method.upper()} {args.path} in the contract")
    print(f"{ep['method']} {ep['path']}")
    print(f"  source          server/index.js:{ep['line']}-{ep['end_line']}")
    print(f"  auth            {ep['auth']}")
    print(f"  status codes    {ep['status_codes']}")
    if ep["errors"]:
        print("  errors")
        for e in ep["errors"]:
            via = f" via {e['via']}" if e.get("via") else ""
            for msg in e["messages"]:
                print(f"    {e['status']}  {msg}{via}  (line {e['line']})")
    else:
        print("  errors          none")
    for mw in ep.get("middleware", []):
        print(f"  middleware      {mw['name']} (line {mw['line']}) rejects with:")
        for field in mw["field_messages"]:
            print(f"    field: {field['message']}  (line {field['line']})")
    return EXIT_OK


def cmd_explain(args) -> int:
    catalog_path = Path(args.catalog)
    if not catalog_path.exists():
        return _fail(EXIT_MISSING_INPUT, f"error catalogue not found: {catalog_path}")
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    wanted = args.id.upper()
    entries = catalog.get("entries", [])
    if wanted == "ALL":
        rows = [[e["id"], e.get("http", ""), e.get("endpoint", ""), e["symptom"][:60]] for e in entries]
        print(_table(rows, ["ID", "HTTP", "ENDPOINT", "SYMPTOM"]))
        print(f"\n{len(entries)} entries")
        return EXIT_OK
    for entry in entries:
        if entry["id"].upper() == wanted:
            print(f"{entry['id']}  {entry.get('title', '')}")
            print(f"  endpoint     {entry.get('endpoint', '-')}")
            print(f"  http         {entry.get('http', '-')}")
            print(f"  message      {entry.get('message', '-')}")
            print(f"  symptom      {entry['symptom']}")
            print(f"  cause        {entry['cause']}")
            print(f"  next step    {entry['next_step']}")
            print(f"  verify       {entry['verify']}")
            print(f"  doc          {entry['doc']}")
            return EXIT_OK
    return _fail(EXIT_FINDINGS, f"unknown catalogue id: {args.id}")


def cmd_verify(args) -> int:
    findings = verify(Path(args.docs), Path(args.contract), Path(args.catalog))
    if not findings:
        print("OK: contract, catalogue, links and support tags all resolve.")
        return EXIT_OK
    print(f"{len(findings)} finding(s):\n")
    for f in findings:
        print(f"  {f}")
    return EXIT_FINDINGS


def cmd_docs_build(args) -> int:
    sitegen_path = Path(__file__).with_name("sitegen.py")
    if not sitegen_path.exists():
        return _fail(EXIT_MISSING_INPUT, f"site generator not found: {sitegen_path}")
    spec = importlib.util.spec_from_file_location("sitegen", sitegen_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    written = module.build(root=Path(args.docs))
    print(f"generated {len(written)} page(s):")
    for p in written:
        print(f"  {p}")
    return EXIT_OK


def cmd_exitcodes(args) -> int:
    rows = [[str(code), name, note] for code, (name, note) in sorted(EXIT_CODES.items())]
    print(_table(rows, ["CODE", "NAME", "MEANING"]))
    return EXIT_OK


def cmd_version(args) -> int:
    print(f"shyzctl {VERSION}")
    return EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="shyzctl",
        description="Documentation contract CLI for the CoorColor / SHYZ API reference site.",
        epilog="Exit codes: "
        + ", ".join(f"{code}={name}" for code, (name, _) in sorted(EXIT_CODES.items())),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--version", action="version", version=f"shyzctl {VERSION}")
    sub = p.add_subparsers(dest="command", metavar="<command>")

    contract = sub.add_parser("contract", help="derive or re-check the API contract")
    contract_sub = contract.add_subparsers(dest="contract_command", metavar="<action>")

    cb = contract_sub.add_parser("build", help="parse the Express source into a contract")
    cb.add_argument("--source", default=str(DEFAULT_SOURCE), help="path to server/index.js")
    cb.add_argument("--out", default=str(DEFAULT_CONTRACT), help="where to write the contract JSON")
    cb.set_defaults(func=cmd_contract_build)

    cc = contract_sub.add_parser("check", help="fail if the committed contract is stale")
    cc.add_argument("--source", default=str(DEFAULT_SOURCE))
    cc.add_argument("--contract", default=str(DEFAULT_CONTRACT))
    cc.set_defaults(func=cmd_contract_check)

    endpoints = sub.add_parser("endpoints", help="list endpoints from the contract")
    endpoints.add_argument("action", nargs="?", default="list", choices=["list"])
    endpoints.add_argument("--contract", default=str(DEFAULT_CONTRACT))
    endpoints.add_argument("--method")
    endpoints.add_argument("--grep")
    endpoints.add_argument("--json", action="store_true")
    endpoints.set_defaults(func=cmd_endpoints)

    show = sub.add_parser("show", help="print one endpoint with its documented errors")
    show.add_argument("method")
    show.add_argument("path")
    show.add_argument("--contract", default=str(DEFAULT_CONTRACT))
    show.set_defaults(func=cmd_show)

    explain = sub.add_parser("explain", help="look up an error catalogue entry")
    explain.add_argument("id", help="catalogue id such as E-AUTH-401, or ALL")
    explain.add_argument("--catalog", default=str(DEFAULT_CATALOG))
    explain.set_defaults(func=cmd_explain)

    v = sub.add_parser("verify", help="check the published site against the contract")
    v.add_argument("--docs", default=str(DEFAULT_DOCS))
    v.add_argument("--contract", default=str(DEFAULT_CONTRACT))
    v.add_argument("--catalog", default=str(DEFAULT_CATALOG))
    v.set_defaults(func=cmd_verify)

    docs = sub.add_parser("docs", help="build the static site")
    docs_sub = docs.add_subparsers(dest="docs_command", metavar="<action>")
    db = docs_sub.add_parser("build", help="render every page from tools/content.py")
    db.add_argument("--docs", default=str(DEFAULT_DOCS))
    db.set_defaults(func=cmd_docs_build)

    ec = sub.add_parser("exitcodes", help="print the exit-code table")
    ec.set_defaults(func=cmd_exitcodes)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        parser.print_help()
        return EXIT_USAGE
    try:
        return int(args.func(args))
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001 - last-resort guard, code 5 means "bug"
        print(f"INTERNAL: {type(exc).__name__}: {exc}", file=sys.stderr)
        return EXIT_INTERNAL


if __name__ == "__main__":
    sys.exit(main())
