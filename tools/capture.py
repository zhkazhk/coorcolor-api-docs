#!/usr/bin/env python3
"""Record real request/response pairs for every example published on the site.

The API reference does not contain hand-typed JSON. Each example carries a
`data-capture` id that points at a pair recorded by this script against the
running Express service, so a reader can diff the page against
`contracts/captures.json` and see that nothing is invented.

Two things make the recording safe to publish:

* **scrubbing** — volatile values (JWTs, order ids, timestamps, nonces,
  signatures) are replaced with stable placeholders, so re-running the capture
  produces a byte-identical file.
* **no live merchant calls** — the payment cases run against a sandbox copy of
  the server whose `unifiedOrder`/`queryOrder` are stubbed and whose merchant
  key is a dummy. Signing itself is still the real implementation, so the
  documented parameter names and the MD5 order are the real ones.

Usage:
    python tools/capture.py --prepare-sandbox <server-dir>   # once, then start it
    python tools/capture.py --core http://127.0.0.1:3000 --pay http://127.0.0.1:3101
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "contracts" / "captures.json"

ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z?$")
# Generated identifiers carry the recording date and four random digits, so they
# are scrubbed too; otherwise two runs never agree.
GENERATED_ID_RES = [
    (re.compile(r"^CK\d{12}$"), "<ORDER_NO>"),
    (re.compile(r"^WX\d{16,18}$"), "<PAY_ORDER_NO>"),
    (re.compile(r"^RC\d{12}$"), "<REFERRAL_CODE>"),
    (re.compile(r"^review\d{13}$"), "<REVIEW_ID>"),
    (re.compile(r"^ENG\d{6}$"), "<ENGINEER_ID>"),
    (re.compile(r"^product\d{6}$"), "<PRODUCT_ID>"),
]
SECRET_KEYS = {"token", "session_key", "paySign", "nonceStr", "sign", "apiKey", "appSecret"}
PLACEHOLDER_KEYS = {
    "token": "<TOKEN>",
    "session_key": "<SESSION_KEY>",
    "paySign": "<PAY_SIGN>",
    "nonceStr": "<NONCE_STR>",
    "sign": "<SIGN>",
}

# Cases are executed in order; later cases may reference earlier results with
# <NAME> in their path or body.
CASES: list[dict] = [
    # --- auth -------------------------------------------------------------
    {
        "id": "login-ok",
        "base": "core",
        "group": "auth",
        "method": "POST",
        "path": "/api/login",
        "json": {"username": "admin", "password": "admin123"},
        "expect": 200,
        "note": "Correct administrator credentials. The token is a 24 h HS256 JWT.",
        "chain": {"TOKEN": "data.token"},
    },
    {
        "id": "login-bad-password",
        "base": "core",
        "group": "auth",
        "method": "POST",
        "path": "/api/login",
        "json": {"username": "admin", "password": "wrong-password"},
        "expect": 401,
        "note": "Existing account, wrong password.",
    },
    {
        "id": "login-unknown-user",
        "base": "core",
        "group": "auth",
        "method": "POST",
        "path": "/api/login",
        "json": {"username": "nobody", "password": "admin123"},
        "expect": 401,
        "note": "No such account. Returns 401 as well, so the client cannot tell the two apart.",
    },
    # --- user / auth transport -------------------------------------------
    {
        "id": "user-info-anonymous",
        "base": "core",
        "group": "auth",
        "method": "GET",
        "path": "/api/user/info",
        "expect": 200,
        "note": "Soft auth: with no Authorization header the endpoint still answers 200 with a guest profile.",
    },
    {
        "id": "user-addresses-bare-token",
        "base": "core",
        "group": "auth",
        "method": "GET",
        "path": "/api/user/addresses",
        "headers": {"Authorization": "<TOKEN>"},
        "expect": 401,
        "note": "The shipped mini program sends the raw token here. The server requires the `Bearer ` prefix, so the request is rejected.",
    },
    {
        "id": "user-addresses-bearer-token",
        "base": "core",
        "group": "auth",
        "method": "GET",
        "path": "/api/user/addresses",
        "headers": {"Authorization": "Bearer <TOKEN>"},
        "expect": 200,
        "note": "Same token with the required prefix.",
    },
    {
        "id": "user-addresses-forged-token",
        "base": "core",
        "group": "auth",
        "method": "GET",
        "path": "/api/user/addresses",
        "headers": {
            "Authorization": "Bearer eyJhbGciOiJIUzI1NiJ9.eyJwaG9uZSI6IjEzOTAwMDAwMDAyIn0.invalid-signature"
        },
        "expect": 401,
        "note": "Well-formed JWT with a bad signature. The handler catches the verify error and reports it as an expired session.",
    },
    # --- sms --------------------------------------------------------------
    {
        "id": "send-code-ok",
        "base": "core",
        "group": "sms",
        "method": "POST",
        "path": "/api/user/send-code",
        "json": {"phone": "13900000001"},
        "expect": 200,
        "note": "Any 11-character string passes validation; no SMS is actually sent.",
    },
    {
        "id": "send-code-bad-phone",
        "base": "core",
        "group": "sms",
        "method": "POST",
        "path": "/api/user/send-code",
        "json": {"phone": "1390000"},
        "expect": 400,
        "note": "Seven characters are rejected by the length check. There is no separate format check to fail afterwards.",
    },
    {
        "id": "send-code-non-numeric",
        "base": "core",
        "group": "sms",
        "method": "POST",
        "path": "/api/user/send-code",
        "json": {"phone": "abcdefghijk"},
        "expect": 200,
        "note": "Eleven non-digit characters are accepted. `phone.length !== 11` is the whole validation, so this defect is reproducible.",
    },
    {
        "id": "bind-phone-wrong-code",
        "base": "core",
        "group": "sms",
        "method": "POST",
        "path": "/api/user/bind-phone",
        "json": {"phone": "13900000001", "code": "000000"},
        "expect": 400,
        "note": "A code was requested for this number in the previous case, so the failure is the value, not the request.",
    },
    # --- products ---------------------------------------------------------
    {
        "id": "products-list",
        "base": "core",
        "group": "products",
        "method": "GET",
        "path": "/api/products",
        "expect": 200,
        "note": "Every active product, newest first.",
    },
    {
        "id": "products-by-category",
        "base": "core",
        "group": "products",
        "method": "GET",
        "path": "/api/products",
        "query": {"category": "rent"},
        "expect": 200,
        "note": "`category=rent` narrows the list; `all` (or omitting it) does not filter at all.",
    },
    {
        "id": "products-detail",
        "base": "core",
        "group": "products",
        "method": "GET",
        "path": "/api/products/product001",
        "expect": 200,
        "note": "Seeded product. `price` is CNY per unit, `stock` is units available.",
    },
    {
        "id": "products-detail-404",
        "base": "core",
        "group": "products",
        "method": "GET",
        "path": "/api/products/product999",
        "expect": 404,
        "note": "Unknown id. Status is 404 but `code` is still only -1.",
    },
    # --- orders -----------------------------------------------------------
    {
        "id": "orders-create-ok",
        "base": "core",
        "group": "orders",
        "method": "POST",
        "path": "/api/orders",
        "json": {
            "serviceType": "repair",
            "brand": "Canon",
            "model": "iRC3322L",
            "problemDesc": "Paper jam in tray 2, red light flashing",
            "appointmentDate": "2026-11-03",
            "appointmentTime": "14:00",
            "contactName": "Liu Yang",
            "contactPhone": "13900000002",
            "serviceAddress": "Room 1802, Building A, 818 Zhangjiang Road, Pudong, Shanghai",
            "urgency": "urgent",
        },
        "expect": 200,
        "note": "Only the two identifiers come back. Everything else is echoed by GET /api/orders/:id.",
        "chain": {"ORDER_ID": "data.id", "ORDER_NO": "data.order_no"},
    },
    {
        "id": "orders-create-validation",
        "base": "core",
        "group": "orders",
        "method": "POST",
        "path": "/api/orders",
        "json": {
            "serviceType": "",
            "brand": "Canon",
            "problemDesc": "",
            "appointmentDate": "",
            "appointmentTime": "",
            "contactName": "L",
            "contactPhone": "1390000",
            "serviceAddress": "Here",
        },
        "expect": 400,
        "note": "All eight field checks run before the response, and the reasons are joined into one string.",
    },
    {
        "id": "orders-detail-ok",
        "base": "core",
        "group": "orders",
        "method": "GET",
        "path": "/api/orders/<ORDER_ID>",
        "expect": 200,
        "note": "The order created above, with `engineer_*` fields present only after assignment.",
        "chain": {"ORDER_ID": "data.id"},
    },
    {
        "id": "orders-detail-404",
        "base": "core",
        "group": "orders",
        "method": "GET",
        "path": "/api/orders/1700000000000",
        "expect": 404,
        "note": "Unknown order id.",
    },
    {
        "id": "orders-cancel-ok",
        "base": "core",
        "group": "orders",
        "method": "PUT",
        "path": "/api/orders/<ORDER_ID>/cancel",
        "expect": 200,
        "note": "Customer cancellation. No status guard: a completed order is cancelled just as happily.",
        "chain": {"ORDER_ID": "data.id"},
    },
    # --- state machine ----------------------------------------------------
    {
        "id": "state-confirm-order",
        "base": "core",
        "group": "state",
        "method": "POST",
        "path": "/api/orders",
        "note": "Fixture for the state-machine cases below: a fresh pending order.",
        "json": {
            "serviceType": "repair",
            "brand": "HP",
            "problemDesc": "Drum unit replacement",
            "appointmentDate": "2026-11-04",
            "appointmentTime": "09:30",
            "contactName": "Wang Fang",
            "contactPhone": "13900000003",
            "serviceAddress": "Floor 6, 1000 Century Avenue, Pudong, Shanghai",
        },
        "expect": 200,
        "chain": {"ORDER_ID_2": "data.id"},
    },
    {
        "id": "assign-ok",
        "base": "core",
        "group": "state",
        "method": "PUT",
        "path": "/api/admin/orders/<ORDER_ID_2>/assign",
        "json": {"engineer_id": "engineer001"},
        "expect": 200,
        "note": "Assignment jumps straight to `processing` and appends a timeline entry.",
    },
    {
        "id": "assign-missing-engineer",
        "base": "core",
        "group": "state",
        "method": "PUT",
        "path": "/api/admin/orders/<ORDER_ID_2>/assign",
        "json": {},
        "expect": 400,
        "note": "The body is checked before the order is even looked up.",
    },
    {
        "id": "assign-unknown-order",
        "base": "core",
        "group": "state",
        "method": "PUT",
        "path": "/api/admin/orders/1700000000001/assign",
        "json": {"engineer_id": "engineer001"},
        "expect": 404,
        "note": "Order is resolved before the engineer, so an unknown order masks an unknown engineer.",
    },
    {
        "id": "assign-unknown-engineer",
        "base": "core",
        "group": "state",
        "method": "PUT",
        "path": "/api/admin/orders/<ORDER_ID_2>/assign",
        "json": {"engineer_id": "engineer999"},
        "expect": 404,
        "note": "Same 404 message shape as an unknown order — only the text differs.",
    },
    {
        "id": "complete-ok",
        "base": "core",
        "group": "state",
        "method": "PUT",
        "path": "/api/admin/orders/<ORDER_ID_2>/complete",
        "json": {"amount": 180, "solution": "Replaced drum unit", "materials": ["DR-2450 drum"]},
        "expect": 200,
        "note": "The assignment above left the order in `processing`, which is the only state `complete` accepts.",
    },
    {
        "id": "state-pending-order",
        "base": "core",
        "group": "state",
        "method": "POST",
        "path": "/api/orders",
        "json": {
            "serviceType": "supplies",
            "brand": "Brother",
            "problemDesc": "Toner cartridge low",
            "appointmentDate": "2026-11-05",
            "appointmentTime": "16:00",
            "contactName": "Chen Jie",
            "contactPhone": "13900000004",
            "serviceAddress": "Desk 12, 55 Anshan Road, Yangpu, Shanghai",
        },
        "expect": 200,
        "note": "A second fixture order, left `pending`, to show the state guards rejecting the wrong transition.",
        "chain": {"ORDER_ID_3": "data.id"},
    },
    {
        "id": "complete-wrong-state",
        "base": "core",
        "group": "state",
        "method": "PUT",
        "path": "/api/admin/orders/<ORDER_ID_3>/complete",
        "json": {"amount": 120},
        "expect": 400,
        "note": "`complete` only accepts `processing`; this order is still `pending`.",
    },
    {
        "id": "start-wrong-state",
        "base": "core",
        "group": "state",
        "method": "PUT",
        "path": "/api/admin/orders/<ORDER_ID_3>/start",
        "expect": 400,
        "note": "`start` only accepts `confirmed`; `pending` is rejected with its own message.",
    },
    {
        "id": "state-confirm-fourth",
        "base": "core",
        "group": "state",
        "method": "POST",
        "path": "/api/orders",
        "json": {
            "serviceType": "rent",
            "brand": "Konica Minolta",
            "problemDesc": "Monthly maintenance visit",
            "appointmentDate": "2026-11-06",
            "appointmentTime": "10:00",
            "contactName": "Zhao Lei",
            "contactPhone": "13900000005",
            "serviceAddress": "Floor 2, 66 Wuning Road, Putuo, Shanghai",
        },
        "expect": 200,
        "note": "Third fixture order, used to show the confirm → start transition succeeding in order.",
        "chain": {"ORDER_ID_4": "data.id"},
    },
    {
        "id": "confirm-ok",
        "base": "core",
        "group": "state",
        "method": "PUT",
        "path": "/api/admin/orders/<ORDER_ID_4>/confirm",
        "expect": 200,
        "note": "`pending` → `confirmed`. This is the transition `start` requires.",
    },
    {
        "id": "start-ok",
        "base": "core",
        "group": "state",
        "method": "PUT",
        "path": "/api/admin/orders/<ORDER_ID_4>/start",
        "expect": 200,
        "note": "`confirmed` → `processing`, with `service_started_at` stamped.",
    },
    {
        "id": "route-not-found",
        "base": "core",
        "group": "routing",
        "method": "GET",
        "path": "/api/reviews/pending",
        "expect": 404,
        "note": "This path is not unmounted: it matches GET /api/reviews/:id with id `pending`, so the 404 comes from the review lookup, not from the catch-all.",
    },
    {
        "id": "admin-reviews-pending",
        "base": "core",
        "group": "routing",
        "method": "GET",
        "path": "/api/admin/reviews/pending",
        "expect": 200,
        "note": "The mounted path. Note that the pending queue requires no token either.",
    },
    # --- payment (sandbox) ------------------------------------------------
    {
        "id": "payment-create-ok",
        "base": "pay",
        "group": "payment",
        "method": "POST",
        "path": "/api/wxpay/create-order",
        "json": {
            "items": [{"productId": "product006", "name": "Canon IR-ADV 4525 rental", "quantity": 1, "price": 899}],
            "totalAmount": 899,
            "contactName": "Liu Yang",
            "contactPhone": "13900000002",
            "serviceAddress": "Room 1802, Building A, 818 Zhangjiang Road, Pudong, Shanghai",
            "openid": "o0000000000000000000000000000000",
        },
        "expect": 200,
        "note": "Sandbox only: the outbound unified-order call is stubbed, so `package` holds a fixed prepay id and the signature is computed with a dummy merchant key.",
        "chain": {"PAY_ORDER_NO": "data.orderNo"},
    },
    {
        "id": "payment-create-missing-openid",
        "base": "pay",
        "group": "payment",
        "method": "POST",
        "path": "/api/wxpay/create-order",
        "json": {"items": [], "totalAmount": 0},
        "expect": 400,
        "note": "`items`, `totalAmount` and `openid` are all required, and one message covers all three.",
    },
    {
        "id": "payment-create-tiny-amount",
        "base": "pay",
        "group": "payment",
        "method": "POST",
        "path": "/api/wxpay/create-order",
        "json": {
            "items": [{"productId": "product006", "name": "Canon IR-ADV 4525 rental", "quantity": 12, "price": 899}],
            "totalAmount": 0.01,
            "contactName": "Liu Yang",
            "contactPhone": "13900000002",
            "serviceAddress": "Room 1802, Building A, 818 Zhangjiang Road, Pudong, Shanghai",
            "openid": "o0000000000000000000000000000000",
        },
        "expect": 200,
        "note": "Twelve rentals priced at 899 each, charged one fen. The amount comes from the client and is never recomputed from the product records.",
    },
    {
        "id": "payment-callback-bad-sign",
        "base": "pay",
        "group": "payment",
        "method": "POST",
        "path": "/api/wxpay/callback",
        "raw_xml": "<xml><return_code><![CDATA[SUCCESS]]></return_code><out_trade_no><![CDATA[<PAY_ORDER_NO>]]></out_trade_no><result_code><![CDATA[SUCCESS]]></result_code><sign><![CDATA[DEADBEEF]]></sign></xml>",
        "expect": 200,
        "note": "A callback with a wrong signature still returns HTTP 200; the failure is inside the XML body.",
    },
    {
        "id": "payment-callback-correct-sign",
        "base": "pay",
        "group": "payment",
        "method": "POST",
        "path": "/api/wxpay/callback",
        "sign_xml": {
            "return_code": "SUCCESS",
            "result_code": "SUCCESS",
            "out_trade_no": "<PAY_ORDER_NO>",
            "transaction_id": "4200000000202611010000000001",
        },
        "sign_key": "SANDBOX-DUMMY-KEY-0000000000000000",
        "expect": 200,
        "note": "A signature computed exactly as WeChat requires (sorted key=value, &key=<merchant key>, MD5 upper-case) is still rejected. The global JSON body parser never reads the XML, so `params` is empty and no signature can ever match.",
    },
]


def prepare_sandbox(server_dir: Path) -> int:
    """Copy the service, stub the two outbound WeChat calls, use a dummy key."""
    sandbox = ROOT / "capture-sandbox"
    if sandbox.exists():
        shutil.rmtree(sandbox)
    sandbox.mkdir(parents=True)
    for name in ("index.js", "database.js", "wxpay-utils.js", "wxpay-config.js", "package.json"):
        src = server_dir / name
        if src.exists():
            shutil.copy2(src, sandbox / name)

    real = sandbox / "wxpay-utils.js"
    real.rename(sandbox / "wxpay-utils-real.js")

    (sandbox / "wxpay-utils.js").write_text(
        "// Sandbox shim: the two outbound WeChat calls are stubbed so the capture\n"
        "// script never touches a live merchant account. Signing stays real.\n"
        "const real = require('./wxpay-utils-real');\n"
        "module.exports = {\n"
        "  ...real,\n"
        "  unifiedOrder: async () => ({ prepay_id: 'wxSTUBPREPAYID0000000000000000', return_code: 'SUCCESS', result_code: 'SUCCESS' }),\n"
        "  queryOrder: async () => ({ trade_state: 'NOTPAY', return_code: 'SUCCESS', result_code: 'SUCCESS' })\n"
        "};\n",
        encoding="utf-8",
    )

    config = (sandbox / "wxpay-config.js").read_text(encoding="utf-8")
    config = re.sub(r"apiKey:\s*'[^']*'", "apiKey: 'SANDBOX-DUMMY-KEY-0000000000000000'", config)
    config = re.sub(r"appId:\s*'[^']*'", "appId: 'wxSANDBOXAPPID0000'", config)
    config = re.sub(r"mchId:\s*'[^']*'", "mchId: 'SANDBOX-MERCHANT-ID'", config)
    config = re.sub(r"notifyUrl:\s*'[^']*'", "notifyUrl: 'http://127.0.0.1:3101/api/wxpay/callback'", config)
    (sandbox / "wxpay-config.js").write_text(config, encoding="utf-8")

    print(f"sandbox ready: {sandbox}")
    print("start it with:  PORT=3101 node capture-sandbox/index.js   (PowerShell: $env:PORT=3101)")
    return 0


# --- capture machinery ------------------------------------------------------

def _request(base: str, case: dict, scratch: dict) -> tuple[int, dict, str, object]:
    method = case["method"].upper()
    path = _subst(case["path"], scratch)
    query = case.get("query")
    if query:
        from urllib.parse import urlencode

        path = f"{path}?{urlencode({k: _subst(str(v), scratch) for k, v in query.items()})}"
    url = base.rstrip("/") + path

    headers = {"Content-Type": "application/json"}
    for key, value in case.get("headers", {}).items():
        headers[key] = _subst(value, scratch)

    data = None
    sent = case.get("json", case.get("raw_xml"))
    if "raw_xml" in case:
        headers["Content-Type"] = "application/xml"
        data = _subst(case["raw_xml"], scratch).encode("utf-8")
        sent = data.decode("utf-8")
    elif "sign_xml" in case:
        headers["Content-Type"] = "application/xml"
        params = {k: _subst(str(v), scratch) for k, v in case["sign_xml"].items()}
        string_a = "&".join(f"{k}={params[k]}" for k in sorted(params) if params[k] not in ("", "None"))
        sign = hashlib.md5(
            f"{string_a}&key={case['sign_key']}".encode("utf-8")
        ).hexdigest().upper()
        fields = {**params, "sign": sign}
        sent = "<xml>" + "".join(f"<{k}><![CDATA[{v}]]></{k}>" for k, v in fields.items()) + "</xml>"
        data = sent.encode("utf-8")
    elif "json" in case:
        data = json.dumps(case["json"], ensure_ascii=False).encode("utf-8")

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return resp.status, dict(resp.headers), body, sent
    except urllib.error.HTTPError as err:
        body = err.read().decode("utf-8", errors="replace")
        return err.code, dict(err.headers), body, sent


def _subst(text: str, scratch: dict) -> str:
    for key, value in scratch.items():
        text = text.replace(f"<{key}>", str(value))
    return text


def _placeholderize(text: str, scratch: dict) -> str:
    """Turn substituted literals back into <NAME>, longest first."""
    for key, value in sorted(scratch.items(), key=lambda kv: -len(str(kv[1]))):
        if isinstance(value, (str, int)):
            text = text.replace(str(value), f"<{key}>")
    return text


def _chain(scratch: dict, body, chain: dict) -> None:
    for name, dotted in chain.items():
        node = body
        for part in dotted.split("."):
            if isinstance(node, dict) and part in node:
                node = node[part]
            else:
                node = None
                break
        if node is not None:
            scratch[name] = node


def _scrub(value, scratch: dict):
    """Replace volatile values with stable placeholders, recursively."""
    reverse = {str(v): f"<{k}>" for k, v in scratch.items() if isinstance(v, (str, int))}
    if isinstance(value, dict):
        out = {}
        for key, item in value.items():
            if key in PLACEHOLDER_KEYS:
                out[key] = PLACEHOLDER_KEYS[key]
            elif key == "package" and isinstance(item, str) and item.startswith("prepay_id="):
                out[key] = "prepay_id=<PREPAY_ID>"
            elif key == "timeStamp" and isinstance(item, str) and item.isdigit() and len(item) == 10:
                out[key] = "<UNIX_SECONDS>"
            elif key == "data" and isinstance(item, dict):
                out[key] = _scrub(item, scratch)
            else:
                out[key] = _scrub(item, scratch)
        return out
    if isinstance(value, list):
        return [_scrub(v, scratch) for v in value]
    if isinstance(value, str):
        if value in reverse:
            return reverse[value]
        # Chained identifiers can also appear embedded in an XML envelope.
        for literal, placeholder in sorted(reverse.items(), key=lambda kv: -len(kv[0])):
            if literal:
                value = value.replace(literal, placeholder)
        # A 32-hex literal inside XML is an MD5 signature over volatile values.
        value = re.sub(r"<!\[CDATA\[([0-9a-fA-F]{32})\]\]>", "<![CDATA[<SIGN>]]>", value)
        if ISO_RE.match(value):
            return "<ISO-8601>"
        for pattern, placeholder in GENERATED_ID_RES:
            if pattern.match(value):
                return placeholder
        if value.isdigit() and len(value) in (13, 14):
            return "<EPOCH_MS>"
        return value
    return value


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="record published examples")
    parser.add_argument("--core", default="http://127.0.0.1:3000")
    parser.add_argument("--pay", default="http://127.0.0.1:3101")
    parser.add_argument("--prepare-sandbox", metavar="SERVER_DIR")
    parser.add_argument("--out", default=str(OUT))
    args = parser.parse_args(argv[1:])

    if args.prepare_sandbox:
        return prepare_sandbox(Path(args.prepare_sandbox))

    bases = {"core": args.core, "pay": args.pay}
    scratch: dict = {}
    records = []
    failures = 0

    for case in CASES:
        base = bases[case["base"]]
        try:
            status, headers, body, sent = _request(base, case, scratch)
        except Exception as exc:  # noqa: BLE001
            print(f"  {case['id']:<34} ERROR {exc}")
            failures += 1
            continue

        try:
            parsed = json.loads(body)
        except json.JSONDecodeError:
            parsed = body

        _chain(scratch, parsed, case.get("chain", {}))

        ok = status == case["expect"]
        failures += 0 if ok else 1
        mark = "ok  " if ok else f"FAIL(expected {case['expect']})"
        print(f"  {case['id']:<34} {status}  {mark}")

        records.append(
            {
                "id": case["id"],
                "group": case["group"],
                "note": case["note"],
                "base": case["base"],
                "request": {
                    "method": case["method"].upper(),
                    "path": _placeholderize(_subst(case["path"], scratch), scratch)
                    + (f"?{_subst(json.dumps(case['query']), scratch)}" if case.get("query") else ""),
                    "headers": {
                        k: _placeholderize(_subst(v, scratch), scratch)
                        for k, v in case.get("headers", {}).items()
                    },
                    "body": _scrub(sent, scratch),
                },
                "response": {
                    "status": status,
                    "content_type": headers.get("Content-Type", ""),
                    "body": _scrub(parsed, scratch),
                },
                "expected_status": case["expect"],
                "status_matches": ok,
            }
        )

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "capture_version": 1,
        "recorded_against": {
            "core": args.core,
            "pay": args.pay,
            "pay_note": "stubbed outbound WeChat calls, dummy merchant key",
        },
        "cases": records,
    }
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\n{len(records)} pair(s) written to {out}")
    if failures:
        print(f"{failures} unexpected status code(s) — the docs would be wrong, fix before publishing.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
