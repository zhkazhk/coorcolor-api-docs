#!/usr/bin/env python3
"""Render the static site from content.py + the contract, captures and catalogue.

Every page is generated; nothing is hand-edited HTML. That is deliberate — it is
what lets a page quote a captured payload, the contract's endpoint count and the
CLI's real --help output without any of them being copied by hand.

Run through the CLI:

    python tools/shyzctl.py docs build
"""

from __future__ import annotations

import html
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"

MAX_DEPTH = 2


# --- helpers ----------------------------------------------------------------

def esc(text: str) -> str:
    return html.escape(str(text), quote=False)


def inline(text: str) -> str:
    """Escape, then apply the two inline conventions the catalogue data uses."""
    out = esc(text)
    out = re.sub(r"`([^`]+)`", r"<code>\1</code>", out)
    out = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", out)
    return out


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def pretty(value) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, indent=2)
    return str(value)


def method_badge(method: str) -> str:
    return f'<span class="method method--{method.lower()}">{method}</span>'


def status_chip(status: int | str) -> str:
    s = int(status)
    kind = "ok" if s < 300 else "warn" if s < 500 else "danger"
    return f'<span class="chip chip--{kind}">HTTP {s}</span>'


def severity_chip(severity: str) -> str:
    kind = {"blocker": "danger", "high": "danger", "medium": "warn", "low": "ok"}.get(severity, "")
    return f'<span class="chip chip--{kind}">{severity}</span>'


# --- block renderers --------------------------------------------------------

class Renderer:
    def __init__(self, root: Path):
        self.root = root
        self.contract = self._load_json("contracts/shyz-api-contract.json")
        self.captures = {
            c["id"]: c for c in self._load_json("contracts/captures.json")["cases"]
        }
        self.catalog = self._load_json("errors/catalog.json")
        self._cli = None

    def _load_json(self, relative: str):
        path = self.root / relative
        if not path.exists():
            raise SystemExit(f"missing input: {path}")
        return json.loads(path.read_text(encoding="utf-8"))

    # -- captures ----------------------------------------------------------
    def capture(self, capture_id: str, trim: dict | None = None, compact: bool = False) -> str:
        if capture_id not in self.captures:
            raise SystemExit(f"page cites unknown capture id: {capture_id}")
        case = self.captures[capture_id]
        req = case["request"]
        resp = case["response"]
        status = resp["status"]

        limit = (trim or {}).get("limit")
        shown_note = ""
        body = req.get("body")
        if body in (None, {}, ""):
            request_block = '<p class="capture__empty">No request body.</p>'
        elif isinstance(body, str) and body.lstrip().startswith("<"):
            request_block = f"<pre><code>{esc(body)}</code></pre>"
        else:
            request_block = f"<pre><code>{esc(pretty(body))}</code></pre>"

        resp_body = resp.get("body")
        if limit:
            container = resp_body
            holder = None
            if isinstance(container, dict) and isinstance(container.get("data"), list):
                holder = "data"
                container = container["data"]
            if isinstance(container, list) and len(container) > limit:
                total = len(container)
                trimmed = container[:limit]
                if holder:
                    resp_body = {**resp_body, holder: trimmed}
                else:
                    resp_body = trimmed
                shown_note = (
                    f'<p class="capture__note">Showing the first {limit} of {total} items. '
                    f"The complete payload is recorded as capture <code>{capture_id}</code> in "
                    "<code>contracts/captures.json</code>.</p>"
                )
        if isinstance(resp_body, str):
            response_block = f"<pre><code>{esc(resp_body)}</code></pre>"
        else:
            response_block = f"<pre><code>{esc(pretty(resp_body))}</code></pre>"

        headers = ""
        if req.get("headers") and not compact:
            rows = "".join(
                f"<tr><td><code>{esc(k)}</code></td><td><code>{esc(v)}</code></td></tr>"
                for k, v in req["headers"].items()
            )
            headers = (
                '<p class="capture__sub">Request headers</p>'
                f'<div class="table-wrap"><table><tbody>{rows}</tbody></table></div>'
            )

        if compact:
            return (
                f'<figure class="capture capture--compact" data-capture="{capture_id}">\n'
                f'  <figcaption><code>{esc(req["method"])} {esc(req["path"])}</code>'
                f" {status_chip(status)}</figcaption>\n"
                f"  {response_block}\n"
                f"  {shown_note}\n"
                f'  <p class="capture__note">{inline(case.get("note", ""))}</p>\n'
                f"</figure>"
            )

        return (
            f'<figure class="capture" data-capture="{capture_id}">\n'
            f'  <figcaption><span class="capture__id">recorded pair <code>{capture_id}</code></span>'
            f" {status_chip(status)}</figcaption>\n"
            f'  <p class="capture__sub">Request</p>\n'
            f'  <p class="capture__line"><code>{esc(req["method"])} {esc(req["path"])}</code></p>\n'
            f"  {request_block}\n"
            f"  {headers}\n"
            f'  <p class="capture__sub">Response</p>\n'
            f"  {response_block}\n"
            f"  {shown_note}\n"
            f'  <p class="capture__note">{inline(case.get("note", ""))}</p>\n'
            f"</figure>"
        )

    # -- cli ---------------------------------------------------------------
    def _run_cli(self, args: list[str]) -> str:
        script = TOOLS / "shyzctl.py"
        try:
            done = subprocess.run(
                [sys.executable, str(script), *args],
                capture_output=True,
                text=True,
                timeout=90,
                cwd=str(self.root),
            )
        except Exception as exc:  # noqa: BLE001
            return f"<pre><code>could not run shyzctl: {esc(exc)}</code></pre>"
        output = (done.stdout or "").rstrip("\n")
        if done.returncode != 0 and done.stderr:
            output += f"\n\nexit status {done.returncode}\n{done.stderr.rstrip()}"
        return f"<pre><code>{esc(output)}</code></pre>"

    # -- tables ------------------------------------------------------------
    @staticmethod
    def _table(headers, rows, caption=None, raw_html: list[int] | None = None) -> str:
        raw_html = raw_html or list(range(len(headers)))
        head = "".join(f"<th>{h}</th>" for h in headers)
        body = []
        for row in rows:
            cells = []
            for i, cell in enumerate(row):
                cells.append(f"<td>{cell if i in raw_html else esc(cell)}</td>")
            body.append("<tr>" + "".join(cells) + "</tr>")
        cap = f"<caption>{caption}</caption>" if caption else ""
        return (
            '<div class="table-wrap"><table>'
            f"<thead><tr>{head}</tr></thead>"
            f"<tbody>{''.join(body)}</tbody>{cap}</table></div>"
        )

    def block(self, block) -> str:
        kind = block[0]
        if kind in ("h2", "h3"):
            title, anchor = block[1], block[2]
            return f'<{kind} id="{anchor}">{title}</{kind}>'
        if kind == "p":
            return f"<p>{block[1]}</p>"
        if kind == "ul":
            return "<ul>" + "".join(f"<li>{item}</li>" for item in block[1]) + "</ul>"
        if kind == "ol":
            return "<ol>" + "".join(f"<li>{item}</li>" for item in block[1]) + "</ol>"
        if kind == "pre":
            return f"<pre><code>{esc(block[1])}</code></pre>"
        if kind == "note":
            _, note_kind, label, body = block
            return (
                f'<div class="note note--{note_kind}"><span class="note__label">{label}</span>'
                f"<p>{body}</p></div>"
            )
        if kind == "dl":
            items = "".join(f"<dt>{term}</dt><dd>{value}</dd>" for term, value in block[1])
            return f'<dl class="meta">{items}</dl>'
        if kind == "params":
            rows = [
                [
                    f"<code>{esc(p['name'])}</code>",
                    p["where"],
                    f"<code>{esc(p['type'])}</code>",
                    p["required"],
                    p["desc"],
                ]
                for p in block[1]
            ]
            return self._table(["Name", "In", "Type", "Required", "Description"], rows)
        if kind == "fields":
            rows = [[f"<code>{f['name']}</code>", f["desc"]] for f in block[1]]
            return self._table(["Field", "Notes"], rows)
        if kind == "table":
            headers, rows = block[1], block[2]
            caption = block[3] if len(block) > 3 else None
            return self._table(headers, rows, caption)
        if kind == "capture":
            opts = block[2] if len(block) > 2 else {}
            return self.capture(block[1], opts.get("trim"), opts.get("compact", False))
        if kind == "errors":
            rows = []
            for err in block[1]:
                rows.append(
                    f'<tr data-status="{err["status"]}" data-message="{esc(err["message"])}">'
                    f"<td>{status_chip(err['status'])}</td>"
                    f'<td><code>{esc(err["message"])}</code></td>'
                    f"<td>{err['when']}</td>"
                    f"<td>{err['action']}</td></tr>"
                )
            return (
                '<div class="table-wrap"><table>'
                "<thead><tr><th>HTTP</th><th>message</th><th>When it happens</th>"
                "<th>What to do</th></tr></thead>"
                f"<tbody>{''.join(rows)}</tbody></table></div>"
            )
        if kind == "cards":
            cards = []
            for href, title, text in block[1]:
                cards.append(
                    f'<a class="card" href="{href}"><h3>{title}</h3><p>{text}</p></a>'
                )
            return f'<div class="grid">{"".join(cards)}</div>'
        if kind == "inventory":
            return self.inventory()
        if kind == "cli_help":
            return self._run_cli([*block[1]])
        if kind == "cli_run":
            return self._run_cli([*block[1]])
        if kind == "exit_codes":
            from importlib.util import module_from_spec, spec_from_file_location

            spec = spec_from_file_location("shyzctl", TOOLS / "shyzctl.py")
            module = module_from_spec(spec)
            assert spec.loader is not None
            spec.loader.exec_module(module)
            rows = [
                [f"<code>{code}</code>", name, note]
                for code, (name, note) in sorted(module.EXIT_CODES.items())
            ]
            return self._table(["Code", "Name", "Meaning"], rows)
        raise SystemExit(f"unknown block type: {kind}")

    # -- inventory ---------------------------------------------------------
    AREA_NAMES = {
        "login": "Authentication",
        "user": "User account and addresses",
        "products": "Catalogue",
        "orders": "Service orders",
        "product-orders": "Rental orders",
        "engineers": "Engineers",
        "coupons": "Coupons",
        "referral": "Referral programme",
        "rebates": "Referral rebates",
        "reviews": "Reviews",
        "wxpay": "Payment",
        "admin/orders": "Admin · orders",
        "admin/engineers": "Admin · engineers",
        "admin/customers": "Admin · customers",
        "admin/stats": "Admin · statistics",
        "admin/reviews": "Admin · review queue",
        "admin/products": "Admin · catalogue",
        "root": "Service root",
    }

    def _area(self, path: str) -> str:
        parts = [p for p in path.split("/") if p]
        if parts[:1] == ["api"]:
            parts = parts[1:]
        if not parts or parts == ["admin"]:
            return "root"
        key = "/".join(parts[:2]) if parts[0] == "admin" else parts[0]
        return key if key in self.AREA_NAMES else "root"

    def inventory(self) -> str:
        documented = {}
        for page in self.content_endpoints():
            documented[(page["method"], page["path"])] = page["slug"]

        groups: dict[str, list[dict]] = {}
        for ep in self.contract["endpoints"]:
            groups.setdefault(self._area(ep["path"]), []).append(ep)

        order = list(self.AREA_NAMES)
        out = []
        for key in [k for k in order if k in groups] + [k for k in groups if k not in order]:
            eps = sorted(groups[key], key=lambda e: (e["method"], e["path"]))
            rows = []
            for ep in eps:
                slug_for = documented.get((ep["method"], ep["path"]))
                path_cell = f"<code>{esc(ep['path'])}</code>"
                if slug_for:
                    rel = slug_for.split("/")[-1]
                    path_cell = f'<a href="{rel}"><code>{esc(ep["path"])}</code></a>'
                codes = ", ".join(str(c) for c in ep["status_codes"])
                rows.append(
                    [method_badge(ep["method"]), path_cell, codes, ep["auth"]]
                )
            out.append(f"<h3>{self.AREA_NAMES.get(key, key)}</h3>")
            out.append(self._table(["Method", "Path", "Status", "Auth"], rows))
        return "\n".join(out)

    def content_endpoints(self):
        from importlib.util import module_from_spec, spec_from_file_location

        spec = spec_from_file_location("shyz_content", TOOLS / "content.py")
        module = module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        return module.ENDPOINTS


# --- page shell -------------------------------------------------------------

def severity_of(pages_h2: list[tuple[str, str]]) -> str:
    return ""


def shell(*, rel: str, title: str, nav_key: str, body: str, toc: list[tuple[str, str]],
          nav: list[tuple[str, str]]) -> str:
    nav_html = []
    for href, label in nav:
        current = ' aria-current="page"' if href == nav_key else ""
        nav_html.append(f'<a href="{rel}{href}"{current}>{label}</a>')

    toc_html = ""
    if toc:
        items = "".join(f'<li><a href="#{anchor}">{title_}</a></li>' for anchor, title_ in toc)
        toc_html = (
            '<div class="sidebar__block"><p class="sidebar__title">On this page</p>'
            f"<ul>{items}</ul></div>"
        )

    elsewhere = "".join(
        f'<li><a href="{rel}{href}">{label}</a></li>' for href, label in nav if href != nav_key
    )
    toc_html += (
        '<div class="sidebar__block"><p class="sidebar__title">Elsewhere</p>'
        f"<ul>{elsewhere}</ul></div>"
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="Documentation sample for the CoorColor print-service API: generated from a parsed contract, recorded request/response pairs, and an error catalogue.">
<link rel="stylesheet" href="{rel}assets/css/site.css">
</head>
<body>
<a class="skip-link" href="#main">Skip to content</a>
<header class="topbar">
  <div class="topbar__inner">
    <a class="brand" href="{rel}index.html"><span class="brand__mark">CoorColor</span><span>documentation sample</span></a>
    <nav class="topnav" aria-label="Sections">
      {''.join(nav_html)}
    </nav>
  </div>
</header>
<div class="shell">
  <aside class="sidebar" aria-label="Page contents">
    {toc_html}
  </aside>
  <main id="main">
{body}
  </main>
</div>
<footer class="footer">
  <div class="footer__inner">
    <span>CoorColor print-service API · documentation sample · {SITE_AUTHOR} {SITE_YEAR}</span>
    <span>Generated from <code>contracts/shyz-api-contract.json</code> ({CONTRACT_HASH}) and {CAPTURE_COUNT} recorded pairs. Check with <code>python tools/shyzctl.py verify</code>.</span>
  </div>
</footer>
</body>
</html>
"""


SITE_AUTHOR = ""
SITE_YEAR = ""
CONTRACT_HASH = ""
CAPTURE_COUNT = 0


def article(*, eyebrow: str, h1: str, lede: str, meta: list | None, blocks: list[str],
            endpoint: str | None = None, extra: str = "") -> str:
    parts = []
    if eyebrow:
        parts.append(f'<p class="eyebrow">{esc(eyebrow)}</p>')
    parts.append(f"<h1>{h1}</h1>")
    if lede:
        parts.append(f'<p class="lede">{lede}</p>')
    if meta:
        items = "".join(f"<dt>{term}</dt><dd>{value}</dd>" for term, value in meta)
        parts.append(f'<dl class="meta">{items}</dl>')
    parts.extend(blocks)
    parts.append(extra)
    inner = "\n".join(parts)
    if endpoint:
        return f'<article data-endpoint="{esc(endpoint)}">\n{inner}\n</article>'
    return f"<article>\n{inner}\n</article>"


def toc_of(blocks: list) -> list[tuple[str, str]]:
    out = []
    for block in blocks:
        if block[0] == "h2":
            out.append((block[2], re.sub(r"<[^>]+>", "", block[1])))
    return out


# --- page builders ----------------------------------------------------------

def build_landing(r: Renderer, content) -> str:
    blocks = [r.block(b) for b in content.HOME["blocks"]]
    body = article(
        eyebrow=content.HOME["eyebrow"],
        h1=content.HOME["h1"],
        lede=content.HOME["lede"],
        meta=None,
        blocks=blocks,
    )
    toc = toc_of(content.HOME["blocks"])
    return shell(rel="", title=f"{content.SITE['title']}", nav_key="index.html",
                 body=body, toc=toc, nav=content.NAV)


def build_guide(r: Renderer, content, page: dict) -> str:
    blocks = [r.block(b) for b in page["blocks"]]
    depth = page["slug"].count("/")
    rel = "../" * depth
    body = article(eyebrow=page["eyebrow"], h1=page["h1"], lede=page["lede"],
                   meta=None, blocks=blocks)
    return shell(rel=rel, title=f"{page['title']} · CoorColor docs", nav_key=page["nav"],
                 body=body, toc=toc_of(page["blocks"]), nav=content.NAV)


def build_endpoint(r: Renderer, content, page: dict) -> str:
    header = (
        f'<p class="eyebrow">{esc(page["eyebrow"])}</p>'
        f'<p class="endpoint-head">{method_badge(page["method"])}'
        f'<code class="endpoint-path">{esc(page["path"])}</code></p>'
        f'<h1>{page["h1"]}</h1>'
        f'<p class="lede">{page["lede"]}</p>'
        f'<dl class="meta">{"".join(f"<dt>{t}</dt><dd>{v}</dd>" for t, v in page["meta"])}</dl>'
    )
    blocks = [r.block(b) for b in page["blocks"]]

    used = [b[1] for b in page["blocks"] if b[0] == "capture"]
    verify = (
        '<div class="note"><span class="note__label">Evidence</span>'
        f'<p>Every example on this page is a recorded request/response pair: '
        f'{", ".join(f"<code>{esc(u)}</code>" for u in used)}. '
        'Re-record with <code>python tools/capture.py</code>; '
        'check this page against the contract with <code>python tools/shyzctl.py verify</code>.</p></div>'
    )

    body = (
        f'<article data-endpoint="{esc(page["method"] + " " + page["path"])}">\n'
        f"{header}\n" + "\n".join(blocks) + f"\n{verify}\n</article>"
    )
    depth = page["slug"].count("/")
    rel = "../" * depth
    return shell(rel=rel, title=f'{page["method"]} {page["path"]} · CoorColor docs',
                 nav_key=page["nav"], body=body, toc=toc_of(page["blocks"]), nav=content.NAV)


def build_errors(r: Renderer, content) -> str:
    catalog = r.catalog
    entries = catalog["entries"]

    legend = Renderer._table(
        ["Severity", "Meaning"],
        [[f"<code>{k}</code>", v] for k, v in catalog["severity_legend"].items()],
    )

    by_area: dict[str, list[dict]] = {}
    for entry in entries:
        by_area.setdefault(entry["area"], []).append(entry)

    sections = []
    for area, area_entries in by_area.items():
        rows = []
        for entry in area_entries:
            anchor = f'<a href="#{entry["id"]}"><code>{entry["id"]}</code></a>'
            rows.append(
                [
                    anchor,
                    severity_chip(entry["severity"]),
                    f"<code>{esc(entry.get('message') or '—')}</code>",
                    inline(entry["title"]),
                ]
            )
        sections.append(f"<h2 id=\"{slug(area)}\">{area}</h2>")
        sections.append(Renderer._table(["ID", "Severity", "message", "Symptom"], rows))

    details = []
    for entry in entries:
        facts = [
            ("Endpoint", f"<code>{esc(entry['endpoint'])}</code>" if entry.get("endpoint") else "cross-cutting"),
            ("HTTP", f"<code>{entry['http']}</code>" if entry.get("http") else "—"),
            ("message", f"<code>{esc(entry['message'])}</code>" if entry.get("message") else "—"),
            ("Severity", severity_chip(entry["severity"])),
            ("Source", f'<span class="cite">{esc(entry["source"])}</span>'),
        ]
        part = [
            f'<h3 id="{entry["id"]}"><code>{entry["id"]}</code> — {inline(entry["title"])}</h3>',
            '<dl class="meta">'
            + "".join(f"<dt>{k}</dt><dd>{v}</dd>" for k, v in facts)
            + "</dl>",
            f'<p><strong>Symptom.</strong> {inline(entry["symptom"])}</p>',
            f'<p><strong>Cause.</strong> {inline(entry["cause"])}</p>',
            f'<p><strong>Next step.</strong> {inline(entry["next_step"])}</p>',
            f'<p><strong>How to verify.</strong> {inline(entry["verify"])}</p>',
            f'<p><strong>Documented at.</strong> <a href="../{entry["doc"]}">{entry["doc"]}</a></p>',
        ]
        if entry.get("capture_fail"):
            part.append('<p class="capture__sub">Failing request</p>')
            part.append(r.capture(entry["capture_fail"], compact=True))
        if entry.get("capture_fix"):
            part.append('<p class="capture__sub">Working request</p>')
            part.append(r.capture(entry["capture_fix"], compact=True))
        else:
            part.append(
                '<div class="note note--warn"><span class="note__label">No working example exists</span>'
                "<p>This one cannot be demonstrated with a passing capture until the code changes. "
                "The evidence is the failing pair above plus the source line.</p></div>"
            )
        tags = " ".join(f'<span class="tag">[{t}]</span>' for t in entry.get("tags", []))
        part.append(f'<p>{tags}</p>')
        part.append("<hr>")
        details.append("\n".join(part))

    body = article(
        eyebrow="Reference · troubleshooting",
        h1="Error catalogue",
        lede=inline(catalog["intro"]),
        meta=None,
        blocks=[
            '<div class="note note--ok"><span class="note__label">How to use it</span>'
            "<p>Start from the symptom you can see, not from the message you cannot explain. "
            "Each entry names the request that produced it, the line of code behind it, and the "
            "smallest change that fixes it. Query the same data from a terminal with "
            "<code>shyzctl explain E-ASG-MASK</code>.</p></div>",
            "<h2 id=\"index\">Index by area</h2>",
            legend,
            *sections,
            "<h2 id=\"entries\">Entries</h2>",
            *details,
        ],
    )
    toc = [("index", "Index by area"), ("entries", "Entries")]
    return shell(rel="../", title="Error catalogue · CoorColor docs", nav_key="errors/index.html",
                 body=body, toc=toc, nav=content.NAV)


def _draft_section_ids(fragment: str, prefix: str) -> str:
    def repl(match: re.Match) -> str:
        level, attrs, text = match.group(1), match.group(2), match.group(3)
        first = re.sub(r"<[^>]+>", "", text).strip().split(" ")[0]
        anchor = f"{prefix}-{slug(first)}"
        return f'<{level} id="{anchor}"{attrs}>{text}</{level}>'

    return re.sub(r"<h([23])([^>]*)>(.*?)</h\1>", repl, fragment, flags=re.DOTALL)


def build_draft(r: Renderer, content, letter: str) -> str:
    path = ROOT / "review" / "drafts" / f"draft-{letter}.html"
    if not path.exists():
        return f"<!-- draft {letter} missing -->"
    fragment = _draft_section_ids(path.read_text(encoding="utf-8"), letter)
    note = (
        '<div class="note note--warn"><span class="note__label">Unedited draft</span>'
        f"<p>This is Draft {letter.upper()} exactly as generated from the brief, rendered with the "
        "site stylesheet and nothing else changed. It was not published; the "
        f'<a href="../api/put-admin-orders-assign.html">reference page</a> is a later rewrite. '
        f'Read the <a href="index.html#verdict">verdict</a>.</p></div>'
    )
    body = article(
        eyebrow=f"Review · draft {letter.upper()}",
        h1=f"Draft {letter.upper()} — assign an engineer",
        lede=""
        if letter == "a"
        else "",
        meta=None,
        blocks=[note, fragment],
    )
    return shell(rel="../", title=f"Draft {letter.upper()} · CoorColor docs",
                 nav_key="review/index.html", body=body, toc=[], nav=content.NAV)


# --- entry point ------------------------------------------------------------

def build(root: Path | None = None) -> list[str]:
    global SITE_AUTHOR, SITE_YEAR, CONTRACT_HASH, CAPTURE_COUNT

    root = Path(root) if root else ROOT
    renderer = Renderer(root)

    from importlib.util import module_from_spec, spec_from_file_location

    spec = spec_from_file_location("shyz_content", TOOLS / "content.py")
    content = module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(content)

    SITE_AUTHOR = content.SITE["author"]
    SITE_YEAR = content.SITE["year"]
    CONTRACT_HASH = renderer.contract["source"]["sha256"][:12]
    CAPTURE_COUNT = len(renderer.captures)

    pages: dict[str, str] = {}
    pages["index.html"] = build_landing(renderer, content)
    pages["api/index.html"] = build_guide(renderer, content, content.API_INDEX)
    pages["api/authentication.html"] = build_guide(renderer, content, content.AUTHENTICATION)
    for page in content.ENDPOINTS:
        pages[page["slug"]] = build_endpoint(renderer, content, page)
    pages["cli/index.html"] = build_guide(renderer, content, content.CLI_PAGE)
    pages["standards/style-guide.html"] = build_guide(renderer, content, content.STYLE_GUIDE)
    pages["standards/rubric.html"] = build_guide(renderer, content, content.RUBRIC)
    pages["review/index.html"] = build_guide(renderer, content, content.REVIEW)
    pages["errors/index.html"] = build_errors(renderer, content)
    pages["review/draft-a.html"] = build_draft(renderer, content, "a")
    pages["review/draft-b.html"] = build_draft(renderer, content, "b")

    written = []
    substitutions = {
        "{{ENDPOINT_COUNT}}": str(renderer.contract["totals"]["endpoints"]),
        "{{CAPTURE_COUNT}}": str(len(renderer.captures)),
        "{{REFERENCE_PAGE_COUNT}}": str(len(content.ENDPOINTS) + 1),
        "{{ENTRY_COUNT}}": str(len(renderer.catalog["entries"])),
        "{{UNCOUNTED}}": str(renderer.contract["totals"]["endpoints"] - len(content.ENDPOINTS)),
        "{{MESSAGE_COUNT}}": str(renderer.contract["totals"]["distinct_messages"]),
    }
    for relative, text in pages.items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        for needle, value in substitutions.items():
            text = text.replace(needle, value)
        target.write_text(text, encoding="utf-8", newline="\n")
        written.append(relative)

    nojekyll = root / ".nojekyll"
    nojekyll.write_text("", encoding="utf-8")
    written.append(".nojekyll")

    return written


if __name__ == "__main__":
    for page in build():
        print(page)
