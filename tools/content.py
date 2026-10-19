#!/usr/bin/env python3
"""All prose for the published site, as data.

`tools/sitegen.py` renders these blocks into HTML. Keeping the words in a Python
module rather than in .html files means the pages can embed live facts — contract
counts, captured payloads, the CLI's real `--help` output and its exit-code table
— instead of copies of them that quietly go stale.

Block syntax (rendered by sitegen.render_block):
    ("h2" | "h3", title, anchor)
    ("p", html)
    ("ul" | "ol", [html, ...])
    ("params",  [ {name, where, type, required, desc} ])
    ("fields",  [ {name, desc} ])
    ("table", headers, rows, caption_or_None)
    ("capture", capture_id)
    ("errors",  [ {status, message, when, action} ])
    ("pre", text)
    ("note", kind, label, html)          kind: info | warn | danger | ok
    ("dl", [ (term, value_html) ])
"""

SITE = {
    "title": "CoorColor API — documentation sample",
    "tagline": "Nine reference pages, a CLI, a 17-entry error catalogue and a review log, "
    "all checked against the running service.",
    "author": "Liu Yang",
    "year": "2026",
}

NAV = [
    ("index.html", "Overview"),
    ("api/index.html", "API reference"),
    ("cli/index.html", "CLI"),
    ("errors/index.html", "Error catalogue"),
    ("standards/style-guide.html", "Style guide"),
    ("standards/rubric.html", "Rubric"),
    ("review/index.html", "Model review"),
]

# ---------------------------------------------------------------------------
# Landing page
# ---------------------------------------------------------------------------

HOME = {
    "slug": "index.html",
    "title": "Documentation sample — CoorColor print-service API",
    "nav": "index.html",
    "eyebrow": "Writing sample",
    "h1": "Documentation for an API I built, and the checks that keep it true",
    "lede": "CoorColor is a printer-service back office — {{ENDPOINT_COUNT}} HTTP endpoints "
    "behind a mini program and an admin console. This site is the documentation for it: "
    "{{REFERENCE_PAGE_COUNT}} reference pages, a CLI reference, a {{ENTRY_COUNT}}-entry error "
    "catalogue, a style guide, a review rubric, and a model-versus-model review that applies "
    "the rubric to two drafts of the same page.",
    "blocks": [
        ("h2", "Start here", "start"),
        ("cards", [
            ("api/index.html", "API reference", "Overview, the response envelope, and the full inventory of {{ENDPOINT_COUNT}} endpoints with eight documented in depth."),
            ("api/authentication.html", "Authentication", "The envelope, the Bearer rule the shipped client gets wrong, and the two token shapes."),
            ("cli/index.html", "shyzctl", "The contract CLI: real --help output, six subcommands, and an exit-code table that CI can branch on."),
            ("errors/index.html", "Error catalogue", "{{ENTRY_COUNT}} entries. Symptom, cause, next step, document — each backed by a failing and a passing capture."),
            ("standards/style-guide.html", "Style guide", "One page: voice, page skeleton, terminology, code samples, when to break the rules."),
            ("standards/rubric.html", "Review rubric", "Four dimensions, five anchor levels each, and the decision rule used in the review."),
        ]),
        ("h2", "How it is verified", "verified"),
        ("p", "Nothing on this site is typed from memory. Three files decide what is true, and "
              "every page is generated from them:"),
        ("dl", [
            ("contracts/shyz-api-contract.json",
             "Parsed from the Express source: 63 endpoints, their status codes, their exact "
             "error strings and the line of code that raises each one."),
            ("contracts/captures.json",
             "{{CAPTURE_COUNT}} request/response pairs recorded against the running service with "
             "<code>tools/capture.py</code>. Every example on this site is one of these pairs."),
            ("errors/catalog.json",
             "The catalogue as data. The page you read is rendered from it, and "
             "<code>shyzctl explain</code> answers from it."),
        ]),
        ("pre", "python tools/shyzctl.py contract check     # has the source drifted?\npython tools/shyzctl.py verify             # does the site still match?\npython tools/capture.py                    # re-record every example"),
        ("p", "The <code>verify</code> run is the point. It fails the build when a page documents "
              "an endpoint the contract does not have, quotes an error string the source does "
              "not raise, cites a capture id that was never recorded, or links to an anchor that "
              "does not exist. The exit codes are documented, so a pipeline can tell a broken link "
              "from a stale contract."),
        ("h2", "Scope, stated plainly", "scope"),
        ("ul", [
            "Eight of the {{ENDPOINT_COUNT}} endpoints are documented in depth — the eight most likely to be "
            "integrated: sign-in, SMS code, product list, order creation, order detail, "
            "assignment, payment creation, payment callback. The other {{UNCOUNTED}} appear in the "
            "inventory with their status codes, generated from the contract.",
            "The two payment pages were recorded against a sandbox copy of the service whose "
            "outbound calls to the payment platform are stubbed and whose merchant key is a "
            "dummy. Signing is the real implementation; no live merchant account was touched.",
            "Credentials were redacted line-in-place before publication. "
            "<code>tools/redact_snapshot.py</code> does the redaction and refuses to write a "
            "file if any credential-shaped string survives.",
            "This is a sample of the writing and the verification, not a product manual. The "
            "product is an internal system; the Chinese strings are real because they are wire "
            "values.",
        ]),
        ("h2", "What the sample is meant to show", "why"),
        ("ul", [
            "I can turn a codebase I own into documentation without inventing anything: the "
            "contract and the captures are the source, and the prose reads the facts out of them.",
            "I separate <em>describing what the code does</em> from <em>judging what it should "
            "do</em>. The error catalogue has a severity, names defects (a payment amount taken "
            "from the client, a callback that can never verify), and does not pretend the system "
            "is finished.",
            "I can review documentation, not just write it: the rubric is written down before the "
            "review, the two drafts were produced independently, and the verdict carries a "
            "one-line reason with tags that point at the pages I checked.",
        ]),
        ("note", "warn", "Known limitation",
         "The two review drafts come from the same model in two separate sessions with no shared "
         "context. That is enough to show a repeatable review procedure and to catch real "
         "defects, but it is not evidence about two different vendors. A cross-vendor comparison "
         "would need the same brief sent to a second provider — the rubric and the tag format "
         "would not change."),
    ],
}

# ---------------------------------------------------------------------------
# API reference index
# ---------------------------------------------------------------------------

API_INDEX = {
    "slug": "api/index.html",
    "title": "API reference",
    "nav": "api/index.html",
    "eyebrow": "Reference",
    "h1": "API reference",
    "lede": "The CoorColor back office speaks JSON over HTTP on port 3000. Every response is "
    "wrapped in the same envelope, there are no machine-readable error codes, and most admin "
    "routes perform no authorization check. Read the authentication page before the endpoints.",
    "blocks": [
        ("h2", "Conventions", "conventions"),
        ("dl", [
            ("Base URL", "<code>http://localhost:3000</code> in development; the deployed base is "
                         "the reverse-proxied host. Paths below are absolute, so append them as-is."),
            ("Content type", "<code>application/json</code> for every request and response except "
                             "the payment callback, which is XML in both directions."),
            ("Auth", "Bearer JWT where present. Several admin routes accept unauthenticated calls — "
                     "the meta column below is generated from the contract, so it says which."),
            ("Encoding", "<code>message</code> is Chinese prose, UTF-8. Treat it as display text."),
            ("Time", "ISO-8601 UTC strings for stored timestamps; <code>YYYY-MM-DD</code> for "
                     "appointment dates."),
        ]),
        ("p", "The envelope, the Bearer rule and the two token shapes are on "
              "<a href=\"authentication.html\">Authentication and errors</a>."),
        ("h2", "Documented in depth", "deep"),
        ("table",
         ["Endpoint", "Page", "Why this one"],
         [
             ["<span class=\"method method--post\">POST</span> <code>/api/login</code>",
              "<a href=\"post-login.html\">Administrator sign-in</a>",
              "The only way to obtain a token, and the two 401s that leak whether an account exists."],
             ["<span class=\"method method--post\">POST</span> <code>/api/user/send-code</code>",
              "<a href=\"post-user-send-code.html\">Send a verification code</a>",
              "Validation that checks length only, and a delivery path that ends in a console log."],
             ["<span class=\"method method--get\">GET</span> <code>/api/products</code>",
              "<a href=\"get-products.html\">List products</a>",
              "The catalogue powering the shop: two filters, no pagination, one implicit status rule."],
             ["<span class=\"method method--post\">POST</span> <code>/api/orders</code>",
              "<a href=\"post-orders.html\">Create a service order</a>",
              "Eight validation rules joined into one string, and an identifier made of a timestamp."],
             ["<span class=\"method method--get\">GET</span> <code>/api/orders/:id</code>",
              "<a href=\"get-order-detail.html\">Read an order</a>",
              "Reads that enrich the record with engineer data not stored on it."],
             ["<span class=\"method method--put\">PUT</span> <code>/api/admin/orders/:id/assign</code>",
              "<a href=\"put-admin-orders-assign.html\">Assign an engineer</a>",
              "Where the state machine is decided, and where two of its rules contradict each other."],
             ["<span class=\"method method--post\">POST</span> <code>/api/wxpay/create-order</code>",
              "<a href=\"post-wxpay-create-order.html\">Create a payment order</a>",
              "Money: the amount is taken from the request body without recomputation."],
             ["<span class=\"method method--post\">POST</span> <code>/api/wxpay/callback</code>",
              "<a href=\"post-wxpay-callback.html\">Payment callback</a>",
              "A callback that cannot verify a signature, because its XML body is never parsed."],
         ],
         None),
        ("h2", "Inventory", "inventory"),
        ("p", "All {{ENDPOINT_COUNT}} routes parsed from <code>server/index.js</code>, grouped by "
              "prefix. Status codes and the auth column come from the contract; routes with a "
              "dedicated page are linked."),
        ("inventory", None),
        ("note", "info", "Regenerating",
         "This inventory is not maintained by hand. <code>python tools/shyzctl.py contract build</code> "
         "re-derives it from the source, and <code>verify</code> fails if a page cites a route the "
         "contract lacks. Ask the tool instead of the page: "
         "<code>shyzctl endpoints --grep orders</code>."),
    ],
}

AUTHENTICATION = {
    "slug": "api/authentication.html",
    "title": "Authentication and errors",
    "nav": "api/index.html",
    "eyebrow": "Reference · guide",
    "h1": "Authentication and errors",
    "lede": "Two cross-cutting rules decide most integration bugs: what a caller must put in the "
    "Authorization header, and what a failure actually looks like. Both are simpler than they look "
    "and both are easy to get wrong, because the shipped client gets the first one wrong already.",
    "blocks": [
        ("h2", "The response envelope", "envelope"),
        ("p", "Every JSON response, success or failure, has one shape:"),
        ("pre", '{"code": 0, "data": <payload>}          // success, HTTP 200\n{"code": -1, "message": "<Chinese text>"}  // failure, HTTP 4xx or 5xx'),
        ("p", "<code>code</code> is <strong>only ever 0 or -1</strong>. It is not an error code; it is "
              "a boolean with JSON syntax. The contract records {{MESSAGE_COUNT}} distinct <code>message</code> "
              "strings sharing that single -1, so a client that branches on <code>code</code> "
              "cannot distinguish a missing order from insufficient stock."),
        ("note", "danger", "Consequence",
         "Branch on the HTTP status, and treat <code>message</code> as display text. Do not compare "
         "the string to decide control flow: it is Chinese prose that any localisation change will "
         "break. See <a href=\"../errors/index.html#E-ENVELOPE\">E-ENVELOPE</a> for the proposed "
         "taxonomy."),
        ("h2", "Bearer tokens", "bearer-prefix"),
        ("p", "User and address routes require the header in one specific form:"),
        ("pre", "Authorization: Bearer eyJhbGciOiJIUzI1NiJ9..."),
        ("p", "The handlers test `startsWith('Bearer ')` before doing anything else "
              "(<span class=\"cite\">server/index.js:312</span>). A bare token is not a token to "
              "this service: it produces <strong>401 请先登录</strong>, which reads like “you are not "
              "signed in” even though the caller is holding a valid credential."),
        ("capture", "user-addresses-bare-token"),
        ("capture", "user-addresses-bearer-token"),
        ("note", "warn", "The shipped mini program sends the bare token",
         "<code>utils/api.js:18</code> does <code>'Authorization': wx.getStorageSync('token')</code> "
         "with no prefix, so every authenticated call from the client fails with 请先登录. The fix is "
         "one line — see <a href=\"../errors/index.html#E-AUTH-BEARER\">E-AUTH-BEARER</a>."),
        ("h2", "Token verification", "verification"),
        ("p", "Expiry and forgery are not distinguished. A route that verifies a token wraps "
              "`jwt.verify` in a try/catch and answers 登录已过期 for every failure:"),
        ("capture", "user-addresses-forged-token"),
        ("p", "The global error middleware does distinguish <code>JsonWebTokenError</code> from "
              "<code>TokenExpiredError</code> (<span class=\"cite\">server/index.js:1397-1403</span>), "
              "but it never runs for these routes because the handler catches the error first. A "
              "client cannot tell “refresh me” from “you were never authenticated”."),
        ("h2", "Two token shapes, one login", "token-shapes"),
        ("p", "There is one sign-in endpoint and it issues an administrator token. Its payload is "
              "<code>{id, username}</code>. User routes read <code>decoded.phone</code>, which an "
              "administrator token does not contain."),
        ("capture", "login-ok"),
        ("p", "The result is a silent empty account rather than a rejection: the verify step "
              "succeeds, the filter matches no rows, and the caller receives HTTP 200 with an empty "
              "list."),
        ("note", "danger", "Read an empty list as a symptom",
         "An authenticated user route that returns <code>[]</code> may mean the token in hand is an "
         "administrator token. <a href=\"../errors/index.html#E-AUTH-ADMIN-TOKEN\">E-AUTH-ADMIN-TOKEN</a> "
         "records the capture and the suggested fix (a user-scoped login plus a token audience claim)."),
        ("h2", "Routes without authorization", "admin-routes"),
        ("p", "Most <code>/api/admin/*</code> routes perform no token check at all. The contract's "
              "auth column records this per route, and it is worth stating without a hedge: an "
              "unauthenticated caller can read the customer list, change order state, approve "
              "reviews, and delete products."),
        ("capture", "admin-reviews-pending"),
        ("p", "The documentation does not paper over this. Each affected page says so in its own "
              "Behaviour section, so an integrator reading one page cannot miss it, and the "
              "inventory marks the routes. Fixing it is an application change, not a documentation "
              "one; until it ships, treat the network boundary as the only access control."),
    ],
}

# ---------------------------------------------------------------------------
# Endpoint pages
# ---------------------------------------------------------------------------

ENDPOINTS = [
    {
        "slug": "api/post-login.html",
        "nav": "api/index.html",
        "method": "POST",
        "path": "/api/login",
        "eyebrow": "Reference · auth",
        "h1": "Administrator sign-in",
        "lede": "Exchanges an administrator username and password for a 24-hour JWT. This is the "
        "only sign-in the service has; the mini program's users have no equivalent.",
        "meta": [
            ("Source", "<span class=\"cite\">server/index.js:59-70</span>"),
            ("Auth required", "No"),
            ("Token lifetime", "24 hours (<code>expiresIn: '24h'</code>)"),
            ("Rate limit", "None — see the note below"),
        ],
        "blocks": [
            ("h2", "Request", "request"),
            ("params", [
                {"name": "username", "where": "body", "type": "string", "required": "Yes",
                 "desc": "Administrator username. Seeded as <code>admin</code> on first start."},
                {"name": "password", "where": "body", "type": "string", "required": "Yes",
                 "desc": "Plain password over the wire; compared against a bcrypt hash, never stored."},
            ]),
            ("capture", "login-ok"),
            ("h2", "Response", "response"),
            ("p", "A successful sign-in returns the token and the username it belongs to. The token "
                  "payload is <code>{id, username}</code>, so it carries no phone number and cannot "
                  "identify a mini-program user (see "
                  "<a href=\"authentication.html#token-shapes\">token shapes</a>)."),
            ("fields", [
                {"name": "data.token", "desc": "HS256 JWT, signed with the server secret, valid for 24 hours."},
                {"name": "data.username", "desc": "Echo of the account name; safe to show in the console header."},
            ]),
            ("h2", "Errors", "errors"),
            ("errors", [
                {"status": 401, "message": "用户不存在",
                 "when": "No administrator record matches <code>username</code>.",
                 "action": "Check the account name. Do not surface this text as-is: it tells the caller the account does not exist."},
                {"status": 401, "message": "密码错误",
                 "when": "The account exists and the bcrypt comparison fails.",
                 "action": "Re-enter the password. Same status as the row above, different string."},
            ]),
            ("note", "warn", "Two 401s, one guessable difference",
             "The two messages differ, so a script can enumerate administrator names. There is no "
             "lockout and no throttle on this route. See "
             "<a href=\"../errors/index.html#E-AUTH-ENUM\">E-AUTH-ENUM</a>."),
            ("h2", "Behaviour worth knowing", "behaviour"),
            ("ul", [
                "<code>bcrypt.compareSync</code> runs on the request thread, so the event loop "
                "blocks for the duration of the hash — tens of milliseconds per attempt, which is "
                "also the only accidental brake on guessing.",
                "The token is the whole session. There is no revocation list, so signing out on the "
                "client (<code>wx.removeStorageSync('token')</code>) does not invalidate a copy "
                "that is already in the wild.",
                "The failed attempt returns 401 with the envelope, while an unregistered path "
                "returns 404 with 请求的资源不存在. Both carry <code>code: -1</code>.",
            ]),
        ],
    },
    {
        "slug": "api/post-user-send-code.html",
        "nav": "api/index.html",
        "method": "POST",
        "path": "/api/user/send-code",
        "eyebrow": "Reference · auth",
        "h1": "Send a verification code",
        "lede": "Issues a six-digit code for a phone number and keeps it in memory for five minutes. "
        "No SMS is sent: the code is written to the server log.",
        "meta": [
            ("Source", "<span class=\"cite\">server/index.js:261-277</span>"),
            ("Auth required", "No"),
            ("Code lifetime", "5 minutes"),
            ("Rate limit", "None"),
        ],
        "blocks": [
            ("h2", "Request", "request"),
            ("params", [
                {"name": "phone", "where": "body", "type": "string", "required": "Yes",
                 "desc": "Eleven characters. Length is the only rule that is enforced."},
            ]),
            ("capture", "send-code-ok"),
            ("h2", "Response", "response"),
            ("p", "The response always says the code was sent, even though nothing was sent."),
            ("fields", [
                {"name": "data.message", "desc": "Fixed string 验证码已发送. It is an acknowledgement, not a delivery receipt."},
            ]),
            ("h2", "Validation", "validation"),
            ("p", "The check is <code>phone.length !== 11</code> "
                  "(<span class=\"cite\">server/index.js:264</span>). A number with eleven "
                  "non-digits passes:"),
            ("capture", "send-code-non-numeric"),
            ("p", "A short number is rejected, which is the only failure this route has:"),
            ("capture", "send-code-bad-phone"),
            ("note", "info", "A stricter validator already exists",
             "<code>validatePhone</code> with <code>/^1[3-9]\\d{9}$/</code> is defined in the same "
             "file (<span class=\"cite\">server/index.js:34</span>) and used by order validation, "
             "but not here. See <a href=\"../errors/index.html#E-SMS-LEN\">E-SMS-LEN</a>."),
            ("h2", "Delivery", "delivery"),
            ("p", "There is no SMS provider integration. The code is generated, stored in a "
                  "module-level object, and printed:"),
            ("pre", "const code = String(Math.floor(100000 + Math.random() * 900000));\nverificationCodes[phone] = { code, expiresAt: Date.now() + 5 * 60 * 1000 };\nconsole.log(`发送验证码 ${code} 到 ${phone}`);"),
            ("p", "Three consequences follow directly, and all three are visible in the source "
                  "rather than inferred:"),
            ("ul", [
                "The user never receives anything. Any flow that depends on the code arriving on a "
                "phone cannot complete in production.",
                "The store is a plain object with no eviction, so it grows for the life of the "
                "process; a restart drops every pending code.",
                "Requesting a code for the same number twice overwrites the previous one, silently "
                "invalidating a code the user may already be holding.",
            ]),
            ("h2", "Then what", "then-what"),
            ("p", "Verification is a separate call, <code>POST /api/user/bind-phone</code>, which "
                  "accepts <code>phone</code> and a six-digit <code>code</code>. Its failures are "
                  "400 with one of four messages: 请输入正确的手机号, 请输入6位验证码, "
                  "请先获取验证码, 验证码已过期, 验证码错误 — a wrong code looks like this:"),
            ("capture", "bind-phone-wrong-code"),
            ("p", "Because no code is delivered, a working end-to-end sign-in currently requires "
                  "reading the code out of the server log. Say so in release notes rather than "
                  "describing the flow as complete."),
        ],
    },
    {
        "slug": "api/get-products.html",
        "nav": "api/index.html",
        "method": "GET",
        "path": "/api/products",
        "eyebrow": "Reference · catalogue",
        "h1": "List products",
        "lede": "Returns the catalogue the shop renders: repairs, rentals and supplies in one list, "
        "filterable by category, with inactive items hidden unless asked for.",
        "meta": [
            ("Source", "<span class=\"cite\">server/index.js:780-798</span>"),
            ("Auth required", "No"),
            ("Pagination", "None — the whole catalogue is returned"),
            ("Sort", "<code>created_at</code> descending"),
        ],
        "blocks": [
            ("h2", "Request", "request"),
            ("params", [
                {"name": "category", "where": "query", "type": "string", "required": "No",
                 "desc": "One of <code>repair</code>, <code>rent</code>, <code>supplies</code>, "
                         "<code>sale</code>. Any other value, including <code>all</code>, disables the filter."},
                {"name": "includeInactive", "where": "query", "type": "string", "required": "No",
                 "desc": "The literal string <code>true</code> includes products whose status is "
                         "not active. Any other value keeps them hidden."},
            ]),
            ("capture", "products-list", {"trim": {"limit": 2}}),
            ("p", "With a category, the list narrows to that category:"),
            ("capture", "products-by-category", {"trim": {"limit": 2}}),
            ("h2", "Response", "response"),
            ("fields", [
                {"name": "data[]", "desc": "Array of product objects, newest first. Ten are seeded on first start."},
                {"name": "id", "desc": "Stable string such as <code>product001</code>; use it in <code>POST /api/orders/buy</code>."},
                {"name": "price", "desc": "Price per unit in CNY, a number."},
                {"name": "originalPrice", "desc": "List price, for a strike-through. Defaults to <code>price</code>."},
                {"name": "stock", "desc": "Units available. Decremented by a purchase, never restored by a cancellation."},
                {"name": "sales", "desc": "Units sold, used for ranking. Incremented on purchase."},
                {"name": "status", "desc": "May be absent on older records; absence means active."},
                {"name": "features", "desc": "Array of short selling points, rendered as tags."},
                {"name": "image", "desc": "Either an emoji or an image URL. Render both, they are not distinguishable by type."},
            ]),
            ("h2", "Rules that are not in the parameters", "rules"),
            ("ul", [
                "The status filter reads <code>!p.status || p.status === 'active'</code>. A product "
                "with an empty or missing <code>status</code> is therefore visible, which is how the "
                "ten seeded rows behave — do not treat a visible product as proof of an explicit "
                "active flag.",
                "There is no pagination and no limit. The response is the entire catalogue on every "
                "call, which is fine at ten rows and is the first thing to change if the catalogue "
                "grows past a few hundred.",
                "<code>GET /api/products/:id</code> answers 404 产品不存在 for an unknown id, but "
                "does not filter on status — a de-listed product still resolves by id.",
            ]),
            ("h2", "Errors", "errors"),
            ("capture", "products-detail-404"),
            ("p", "The list itself has no failure path: an unknown category returns an empty array "
                  "with HTTP 200 rather than 400, so a typo in the query string looks like an empty "
                  "catalogue. The only 404 on the product routes is the detail call above."),
        ],
    },
    {
        "slug": "api/post-orders.html",
        "nav": "api/index.html",
        "method": "POST",
        "path": "/api/orders",
        "eyebrow": "Reference · orders",
        "h1": "Create a service order",
        "lede": "Books an on-site visit: service type, machine, problem, appointment, contact and "
        "address, validated by one middleware that reports every missing field at once.",
        "meta": [
            ("Source", "<span class=\"cite\">server/index.js:38-57</span> (validation), "
                       "<span class=\"cite\">server/index.js:83-110</span> (handler)"),
            ("Auth required", "No"),
            ("Identifier", "<code>Date.now()</code> — see Identifiers below"),
            ("Initial status", "<code>pending</code>"),
        ],
        "blocks": [
            ("h2", "Request", "request"),
            ("params", [
                {"name": "serviceType", "where": "body", "type": "string", "required": "Yes",
                 "desc": "Service line: <code>repair</code>, <code>rent</code>, <code>supplies</code>, <code>sale</code>."},
                {"name": "brand", "where": "body", "type": "string", "required": "Yes", "desc": "Machine brand, free text."},
                {"name": "model", "where": "body", "type": "string", "required": "No", "desc": "Model number; stored as an empty string when omitted."},
                {"name": "problemDesc", "where": "body", "type": "string", "required": "Yes",
                 "desc": "What is wrong, in the customer's words."},
                {"name": "appointmentDate", "where": "body", "type": "string", "required": "Yes",
                 "desc": "<code>YYYY-MM-DD</code>. Not validated as a date, only as non-empty."},
                {"name": "appointmentTime", "where": "body", "type": "string", "required": "Yes",
                 "desc": "<code>HH:MM</code>. Again, only non-empty is enforced."},
                {"name": "contactName", "where": "body", "type": "string", "required": "Yes",
                 "desc": "At least two characters after trimming."},
                {"name": "contactPhone", "where": "body", "type": "string", "required": "Yes",
                 "desc": "Must match <code>/^1[3-9]\\d{9}$/</code>."},
                {"name": "serviceAddress", "where": "body", "type": "string", "required": "Yes",
                 "desc": "At least five characters after trimming."},
                {"name": "urgency", "where": "body", "type": "string", "required": "No",
                 "desc": "<code>normal</code> (default), <code>urgent</code> or <code>low</code>. Free text, not validated."},
                {"name": "photos", "where": "body", "type": "array", "required": "No", "desc": "URLs or upload ids; stored as given."},
                {"name": "remark", "where": "body", "type": "string", "required": "No", "desc": "Free note from the customer."},
            ]),
            ("capture", "orders-create-ok"),
            ("h2", "Response", "response"),
            ("p", "Only the two identifiers come back. Everything else the client just sent is not "
                  "echoed, so a confirmation screen has to re-read the order."),
            ("fields", [
                {"name": "data.id", "desc": "Order id, a millisecond timestamp as a string. Used in every order URL."},
                {"name": "data.order_no", "desc": "Human-facing number: <code>CK</code> + <code>YYYYMMDD</code> + four random digits."},
            ]),
            ("h2", "Errors", "errors"),
            ("p", "Validation is one middleware, <code>validateOrderData</code>. It collects every "
                  "failing rule, then answers a single 400 whose <code>message</code> is the reasons "
                  "joined by a full-width semicolon, in the order the rules are checked:"),
            ("capture", "orders-create-validation"),
            ("table",
             ["Order", "Rule", "Reason text (verbatim)"],
             [
                 ["1", "<code>serviceType</code> non-empty", "服务类型不能为空"],
                 ["2", "<code>brand</code> non-empty", "品牌不能为空"],
                 ["3", "<code>problemDesc</code> non-empty", "问题描述不能为空"],
                 ["4", "<code>appointmentDate</code> non-empty", "预约日期不能为空"],
                 ["5", "<code>appointmentTime</code> non-empty", "预约时间不能为空"],
                 ["6", "<code>contactName</code> ≥ 2 chars", "请输入正确的联系人姓名"],
                 ["7", "<code>contactPhone</code> matches the mobile pattern", "请输入正确的手机号"],
                 ["8", "<code>serviceAddress</code> ≥ 5 chars", "请输入详细的服务地址"],
             ],
             "Reasons appear in this order, joined with ；. A client that wants to highlight one input has to match on the string."),
            ("note", "warn", "The response has no field name",
             "Nothing in the body says <em>which</em> input failed, so the console has to parse the "
             "joined prose or repeat the same eight rules client-side. See "
             "<a href=\"../errors/index.html#E-ORD-VALIDATION\">E-ORD-VALIDATION</a>."),
            ("h2", "Identifiers", "identifiers"),
            ("p", "<code>id</code> is <code>Date.now().toString()</code> "
                  "(<span class=\"cite\">server/index.js:87</span>). Two orders submitted within the "
                  "same millisecond receive the same id, and the second one shadows the first on "
                  "every lookup. The order number is not a substitute: it is "
                  "<code>CK</code> + date + four random digits, which is a 10 000-value space per day."),
            ("p", "This is a documentation fact worth repeating on the page rather than leaving in a "
                  "ticket, because it changes how a client should behave: never treat <code>id</code> "
                  "as globally unique, and avoid parallel submissions from one session. "
                  "<a href=\"../errors/index.html#E-ORD-ID-COLLISION\">E-ORD-ID-COLLISION</a> has the "
                  "reproduction."),
            ("h2", "Behaviour worth knowing", "behaviour"),
            ("ul", [
                "No authorization check. An unauthenticated caller can create an order for any phone "
                "number and address they like, and the record will look like a real booking.",
                "The middleware validates <code>contactPhone</code> properly, while the SMS routes "
                "next door accept any eleven characters — the two endpoints disagree about what a "
                "phone number is.",
                "Dates and times are only checked for presence. <code>2020-01-01</code> and "
                "<code>99:99</code> are accepted, so past-dated bookings are a client-side problem "
                "by design.",
                "The created order starts as <code>pending</code> with an empty <code>timeline</code>. "
                "See <a href=\"put-admin-orders-assign.html#state-machine\">the state machine</a> for "
                "what can happen next.",
            ]),
        ],
    },
    {
        "slug": "api/get-order-detail.html",
        "nav": "api/index.html",
        "method": "GET",
        "path": "/api/orders/:id",
        "eyebrow": "Reference · orders",
        "h1": "Read an order",
        "lede": "Returns one order, enriched with the assigned engineer's name, phone and last "
        "reported position. The engineer fields are added at read time and are not stored on the "
        "order.",
        "meta": [
            ("Source", "<span class=\"cite\">server/index.js:187-200</span>"),
            ("Auth required", "No"),
            ("Enrichment", "Three <code>engineer_*</code> fields, only when <code>engineer_id</code> is set"),
            ("Cache", "None"),
        ],
        "blocks": [
            ("h2", "Request", "request"),
            ("params", [
                {"name": "id", "where": "path", "type": "string", "required": "Yes",
                 "desc": "Order id, as returned by <code>POST /api/orders</code> in <code>data.id</code>."},
            ]),
            ("capture", "orders-detail-ok"),
            ("h2", "Response", "response"),
            ("p", "The full order document. Compare this payload with the one in the creation "
                  "example: same object, read back."),
            ("fields", [
                {"name": "status", "desc": "<code>pending</code>, <code>confirmed</code>, <code>processing</code>, <code>completed</code> or <code>canceled</code>."},
                {"name": "timeline", "desc": "Append-only log of <code>{status, time, operator, remark}</code>. Empty until the first state change."},
                {"name": "engineer_id, engineer_name, engineer_phone", "desc": "Present only after assignment, added from the engineer record at read time."},
                {"name": "engineer_position", "desc": "<code>{latitude, longitude, updated_at}</code> or null; the last location the engineer reported."},
                {"name": "amount", "desc": "Present once the order is completed; the visit fee entered by the engineer."},
                {"name": "solution, materials", "desc": "Work done and parts used, both written at completion."},
                {"name": "cancel_reason", "desc": "Set only when an administrator cancelled the order. Customer cancellation does not set it."},
            ]),
            ("note", "info", "Read-time enrichment is not persistence",
             "The handler writes <code>engineer_name</code>, <code>engineer_phone</code> and "
             "<code>engineer_position</code> onto the in-memory order object "
             "(<span class=\"cite\">server/index.js:195-197</span>). They are not saved. A list "
             "endpoint returns the same order without them, so do not assume the fields exist on "
             "every order you receive."),
            ("h2", "Errors", "errors"),
            ("errors", [
                {"status": 404, "message": "订单不存在",
                 "when": "No order matches <code>id</code>.",
                 "action": "Remove the order from the list or refresh it; a stale id means the record is gone, not that the request was malformed."},
            ]),
            ("capture", "orders-detail-404"),
            ("p", "The 404 carries the same <code>code: -1</code> as a validation failure, so the "
                  "HTTP status is the only signal that distinguishes “gone” from “wrong”."),
            ("h2", "Behaviour worth knowing", "behaviour"),
            ("ul", [
                "No authorization check: knowing an id is sufficient to read a customer's name, "
                "phone and address.",
                "The response is assembled per request from two collections, so an order whose "
                "<code>engineer_id</code> no longer resolves keeps the id and returns "
                "<code>engineer_name: \"\"</code> rather than failing.",
                "Volatile fields scramble comparisons: <code>engineer_position.updated_at</code> "
                "changes whenever the engineer reports, and nothing in the payload version-stamps "
                "the order for caching.",
            ]),
        ],
    },
    {
        "slug": "api/put-admin-orders-assign.html",
        "nav": "api/index.html",
        "method": "PUT",
        "path": "/api/admin/orders/:id/assign",
        "eyebrow": "Reference · state machine",
        "h1": "Assign an engineer to an order",
        "lede": "Attaches an engineer to an order and moves it to <code>processing</code> in one "
        "call, without asking what state the order was in.",
        "meta": [
            ("Source", "<span class=\"cite\">server/index.js:1026-1056</span>"),
            ("Auth required", "No — the handler performs no token check"),
            ("Effect on status", "Forced to <code>processing</code>, unguarded"),
            ("Idempotent", "No — every call appends a timeline entry"),
        ],
        "blocks": [
            ("h2", "Request", "request"),
            ("params", [
                {"name": "id", "where": "path", "type": "string", "required": "Yes",
                 "desc": "Order id from <code>POST /api/orders</code>, <code>data.id</code>."},
                {"name": "engineer_id", "where": "body", "type": "string", "required": "Yes",
                 "desc": "An existing engineer id such as <code>engineer001</code>. Any falsy value is rejected before the order is read."},
            ]),
            ("capture", "assign-ok"),
            ("h2", "Response", "response"),
            ("p", "The full updated order. The selected engineer's id, name and phone are copied "
                  "onto it, <code>status</code> becomes <code>processing</code>, and a timeline entry "
                  "records the operator and the engineer's name:"),
            ("fields", [
                {"name": "status", "desc": "Always <code>processing</code> after this call, whatever it was before."},
                {"name": "engineer_name, engineer_phone", "desc": "Copied from the engineer record so a detail view needs no second lookup."},
                {"name": "timeline[]", "desc": "New last entry: <code>{\"status\":\"processing\", \"operator\":\"管理员\", \"remark\":\"分配给工程师：&lt;engineer name&gt;\"}</code>."},
                {"name": "updated_at", "desc": "Refreshed."},
            ]),
            ("h2", "Errors", "errors"),
            ("errors", [
                {"status": 400, "message": "请选择工程师",
                 "when": "<code>engineer_id</code> is missing, empty or otherwise falsy. Checked before the order is looked up.",
                 "action": "Require a selection in the UI and block the call until one is set."},
                {"status": 404, "message": "订单不存在",
                 "when": "No order matches <code>id</code>. Raised after the body check and before the engineer lookup.",
                 "action": "Re-read the order list; the id must come from <code>data.id</code> of the creation call."},
                {"status": 404, "message": "工程师不存在",
                 "when": "No engineer matches <code>engineer_id</code>. Unreachable while the order id is also wrong.",
                 "action": "Reload the engineer list and send an id that exists."},
            ]),
            ("p", "Checks run body, then order, then engineer, and each failure replaces the knowledge "
                  "of the next one. A dispatcher with two stale ids is told about the order only. "
                  "See <a href=\"../errors/index.html#E-ASG-MASK\">E-ASG-MASK</a>."),
            ("h2", "Where this sits in the state machine", "state-machine"),
            ("p", "Orders move through five statuses. Two routes reach <code>processing</code>, and "
                  "they do not agree about what must happen first:"),
            ("table",
             ["From", "Call", "To", "Guard"],
             [
                 ["<code>pending</code>", "<code>PUT /api/admin/orders/:id/confirm</code>", "<code>confirmed</code>",
                  "Requires <code>pending</code>: 400 只能确认待处理订单"],
                 ["<code>confirmed</code>", "<code>PUT /api/admin/orders/:id/start</code>", "<code>processing</code>",
                  "Requires <code>confirmed</code>: 400 只能开始已确认的订单"],
                 ["<code>processing</code>", "<code>PUT /api/admin/orders/:id/complete</code>", "<code>completed</code>",
                  "Requires <code>processing</code>: 400 只能完成服务中的订单"],
                 ["any", "<code>PUT /api/admin/orders/:id/assign</code>", "<code>processing</code>",
                  "<strong>No guard</strong> — a completed order is silently reopened"],
                 ["<code>pending</code> / <code>confirmed</code> / <code>processing</code>",
                  "<code>PUT /api/admin/orders/:id/cancel</code>", "<code>canceled</code>",
                  "Refuses <code>completed</code> and <code>canceled</code>"],
             ],
             "The assign route bypasses the confirm and start steps entirely, so the same order can reach processing by two different histories."),
            ("p", "Because <code>status</code> is overwritten rather than transitioned, assigning an "
                  "order that is already <code>completed</code> returns it to <code>processing</code> "
                  "and leaves the completion entry in the timeline. Nothing in the response flags "
                  "that a finished job was reopened."),
            ("note", "danger", "Two rules, one status",
             "Confirm-then-start is guarded at every step; assign skips both. If a UI exposes only "
             "one of them, the other is reachable by API and produces a state the UI does not model. "
             "Documented, not fixed: the fix is a guard on <code>status</code> in the assign handler."),
            ("h2", "Behaviour worth knowing", "behaviour"),
            ("ul", [
                "<strong>No authorization.</strong> Nothing on this route checks a token, so any "
                "caller who can reach the port can reassign work. Several admin routes share this "
                "property; the contract's auth column lists them all.",
                "<strong>Not idempotent.</strong> A retried call rewrites the engineer fields and "
                "appends a second timeline entry, so the log records two assignments for one "
                "decision. Guard retries on the client.",
                "<strong>The engineer is not validated as available.</strong> An engineer record "
                "with <code>status: inactive</code> or one who is already on another job can be "
                "assigned; <code>order_count</code> on the engineer record is never incremented "
                "here.",
                "<strong>The timeline is the audit trail.</strong> It is the only record of who "
                "changed what, it is append-only, and its <code>operator</code> value is a fixed "
                "Chinese string rather than the caller's identity — so it cannot attribute an "
                "action to a person.",
            ]),
        ],
    },
    {
        "slug": "api/post-wxpay-create-order.html",
        "nav": "api/index.html",
        "method": "POST",
        "path": "/api/wxpay/create-order",
        "eyebrow": "Reference · payment",
        "h1": "Create a payment order",
        "lede": "Stores a rental order, calls the payment platform's unified order endpoint, and "
        "returns the parameters a mini program passes to <code>wx.requestPayment</code>.",
        "meta": [
            ("Source", "<span class=\"cite\">server/index.js:1619-1677</span>"),
            ("Auth required", "No"),
            ("Amount", "Taken from the request body — not recomputed"),
            ("Evidence", "Recorded against a sandbox with stubbed outbound calls"),
        ],
        "blocks": [
            ("note", "warn", "About the examples on this page",
             "This endpoint is the only one whose outbound call reaches a third party. The captures "
             "below were recorded against a sandbox copy of the service: "
             "<code>unifiedOrder</code> and <code>queryOrder</code> are stubbed, and the merchant key "
             "is a dummy. The parameter names, the MD5 signing order and the response shape are the "
             "real implementation; the signature value is not reproducible outside the sandbox."),
            ("h2", "Request", "request"),
            ("params", [
                {"name": "items", "where": "body", "type": "array", "required": "Yes",
                 "desc": "Line items, passed through to the stored order unchanged. A non-empty array is required."},
                {"name": "totalAmount", "where": "body", "type": "number", "required": "Yes",
                 "desc": "Amount in CNY. Multiplied by 100 and sent as <code>total_fee</code> in fen."},
                {"name": "openid", "where": "body", "type": "string", "required": "Yes",
                 "desc": "The payer's mini-program openid, obtained from <code>POST /api/user/getOpenid</code>."},
                {"name": "contactName", "where": "body", "type": "string", "required": "No",
                 "desc": "Stored on the order; an empty string when omitted."},
                {"name": "contactPhone", "where": "body", "type": "string", "required": "No",
                 "desc": "Stored as given, unvalidated."},
                {"name": "serviceAddress", "where": "body", "type": "string", "required": "No",
                 "desc": "Stored as given, unvalidated."},
            ]),
            ("capture", "payment-create-ok"),
            ("h2", "Response", "response"),
            ("p", "Four of the five fields are handed straight to <code>wx.requestPayment</code>; "
                  "the order identifiers come from this service."),
            ("fields", [
                {"name": "data.orderId", "desc": "Internal order id, <code>Date.now()</code> as a string."},
                {"name": "data.orderNo", "desc": "Merchant order number: <code>WX</code> + 14-digit timestamp + four random digits."},
                {"name": "data.timeStamp", "desc": "Unix seconds as a string, for <code>wx.requestPayment</code>."},
                {"name": "data.nonceStr", "desc": "32-character random string."},
                {"name": "data.package", "desc": "<code>prepay_id=wx…</code>, from the unified order response."},
                {"name": "data.signType", "desc": "<code>MD5</code>."},
                {"name": "data.paySign", "desc": "MD5 over the sorted parameters plus the merchant key, upper-case hex."},
            ]),
            ("h2", "The amount is not verified", "amount"),
            ("p", "The handler reads <code>totalAmount</code> from the body, stores it, and converts "
                  "it for the payment platform "
                  "(<span class=\"cite\">server/index.js:1657</span>). The product records are never "
                  "consulted, so the price catalogue on the <code>GET /api/products</code> page has no "
                  "bearing on what is charged. Twelve rentals at ¥899 each, submitted as one fen:"),
            ("capture", "payment-create-tiny-amount"),
            ("note", "danger", "Do not ship this as-is",
             "A client controls the payable amount. The fix belongs in this handler: load each "
             "<code>productId</code>, recompute the total from the stored price, and reject the body "
             "when <code>totalAmount</code> disagrees. "
             "<a href=\"../errors/index.html#E-PAY-AMOUNT\">E-PAY-AMOUNT</a> records the evidence."),
            ("h2", "Errors", "errors"),
            ("errors", [
                {"status": 400, "message": "参数不完整",
                 "when": "<code>items</code> is empty, or <code>totalAmount</code> is zero or absent, or <code>openid</code> is missing. One message covers all three.",
                 "action": "Send all three. Reuse an openid already obtained for the session; do not mint one per attempt."},
                {"status": 500, "message": "微信支付功能未配置",
                 "when": "The payment utility module failed to load at start-up.",
                 "action": "Check the server log at boot; the module is loaded in a try/catch and the failure is only printed."},
                {"status": 500, "message": "创建订单失败",
                 "when": "The unified order call failed or timed out. The stored order is left in <code>pending</code>.",
                 "action": "Retry, and reconcile afterwards with <code>GET /api/wxpay/order/:orderNo</code> rather than creating a second order."},
            ]),
            ("capture", "payment-create-missing-openid"),
            ("h2", "Behaviour worth knowing", "behaviour"),
            ("ul", [
                "The order is written to storage before the platform is called, so a failed payment "
                "attempt leaves a <code>pending</code> order behind. Nothing expires it.",
                "Product stock is not touched: this path is separate from <code>POST /api/orders/buy</code>, "
                "which does decrement stock and apply coupons.",
                "<code>Math.round(totalAmount * 100)</code> is the only conversion. A fractional yuan "
                "amount is rounded, not rejected.",
                "There is no idempotency key. Two submissions create two orders and two prepay "
                "attempts.",
            ]),
        ],
    },
    {
        "slug": "api/post-wxpay-callback.html",
        "nav": "api/index.html",
        "method": "POST",
        "path": "/api/wxpay/callback",
        "eyebrow": "Reference · payment",
        "h1": "Payment callback",
        "lede": "The notification endpoint the payment platform calls after a payment. It answers in "
        "XML, verifies an MD5 signature, and flips the order to paid. In this build it rejects every "
        "callback, including correctly signed ones.",
        "meta": [
            ("Source", "<span class=\"cite\">server/index.js:1680-1718</span>"),
            ("Auth required", "Signature, not a token"),
            ("Transport", "XML in, XML out, HTTP 200 in every case"),
            ("Status in this build", "Cannot verify — see Signature below"),
        ],
        "blocks": [
            ("h2", "Request", "request"),
            ("p", "The platform posts an XML document with CDATA-wrapped fields. The ones the handler "
                  "uses are <code>result_code</code>, <code>out_trade_no</code>, "
                  "<code>transaction_id</code> and <code>sign</code>; anything else is ignored."),
            ("capture", "payment-callback-bad-sign"),
            ("h2", "Response", "response"),
            ("p", "The answer is XML, and the HTTP status is always 200. Success and failure differ "
                  "only inside the body, which is what the platform reads:"),
            ("pre", "<xml><return_code><![CDATA[SUCCESS]]></return_code><return_msg><![CDATA[OK]]></return_msg></xml>\n<xml><return_code><![CDATA[FAIL]]></return_code><return_msg><![CDATA[签名错误]]></return_msg></xml>"),
            ("p", "There are four failure texts: 签名错误, 系统错误, 处理失败, and the platform's own "
                  "<code>err_code_des</code> when <code>result_code</code> is not SUCCESS (falling back "
                  "to 支付失败)."),
            ("h2", "The signature can never match", "signature"),
            ("p", "The handler parses the body, then verifies an MD5 signature over the sorted "
                  "parameters plus the merchant key. A body is never parsed:"),
            ("pre", "app.use(bodyParser.json());            // server/index.js:14 — JSON only\n...\nconst params = await wxpayUtils.parseXML(xmlData);   // :1688, receives {}"),
            ("p", "No XML parser is registered, so for <code>Content-Type: application/xml</code> the "
                  "body parser leaves <code>req.body</code> as an empty object. "
                  "<code>parseXML</code> therefore finds no fields, <code>sign</code> is undefined, and "
                  "<code>verifySign</code> cannot return true."),
            ("p", "The evidence is a callback signed exactly as the platform requires — sorted "
                  "<code>key=value</code> pairs, <code>&amp;key=&lt;merchant key&gt;</code>, MD5 "
                  "upper-case — and it is still refused:"),
            ("capture", "payment-callback-correct-sign"),
            ("note", "danger", "Consequence and workaround",
             "Orders are never marked paid by the callback, so a paid rental stays "
             "<code>pending</code> until something queries it. The workaround that does work is "
             "<code>GET /api/wxpay/order/:orderNo</code>, which asks the platform directly and flips "
             "the status on <code>trade_state: SUCCESS</code>. The fix is to register a text parser "
             "for <code>application/xml</code> before this route. "
             "<a href=\"../errors/index.html#E-PAY-CALLBACK-XML\">E-PAY-CALLBACK-XML</a>."),
            ("h2", "Behaviour worth knowing", "behaviour"),
            ("ul", [
                "Failure is invisible to monitoring: every response is HTTP 200, so an uptime check "
                "cannot tell a working callback from a broken one. Watch the body, not the status.",
                "A callback that does verify would update the order by "
                "<code>out_trade_no</code>, and would be safely repeatable — the handler assigns "
                "<code>status = 'paid'</code> rather than incrementing anything.",
                "The route has no anti-replay protection of its own; it relies on the platform's "
                "signature, which is precisely the part that is not working here.",
                "The callback configures <code>notify_url</code> in <code>wxpay-config.js</code>, "
                "which points at the reverse-proxied host — it is not the <code>localhost</code> base "
                "URL the rest of this reference uses.",
            ]),
        ],
    },
]

# ---------------------------------------------------------------------------
# CLI reference
# ---------------------------------------------------------------------------

CLI_PAGE = {
    "slug": "cli/index.html",
    "title": "shyzctl — contract CLI",
    "nav": "cli/index.html",
    "eyebrow": "Reference · tool",
    "h1": "shyzctl",
    "lede": "A small command-line tool that keeps this documentation honest. It derives the API "
    "contract from the Express source, records examples from the running service, answers questions "
    "about the error catalogue, and fails the build when a page drifts from the code.",
    "blocks": [
        ("h2", "Why a CLI and not a wiki", "why"),
        ("p", "Documentation written next to code decays the moment the code moves. The usual answer "
              "is discipline. The answer here is a tool with a narrow job and an exit code: an "
              "endpoint that exists in a page but not in the contract is an error, not a review "
              "comment. Everything the site claims can be re-derived in one command."),
        ("pre", "python tools/shyzctl.py contract build    # parse server/index.js -> contract JSON\npython tools/shyzctl.py verify            # does every page still match?\npython tools/capture.py                   # re-record the {{CAPTURE_COUNT}} examples"),
        ("h2", "Top-level help", "help"),
        ("cli_help", ["--help"]),
        ("h2", "Commands", "commands"),
        ("table",
         ["Command", "What it does", "Reads", "Writes"],
         [
             ["<code>contract build</code>", "Parses the Express source into a contract: methods, paths, status codes, error strings, source line numbers.", "the source", "contract JSON"],
             ["<code>contract check</code>", "Compares the committed contract hash with the source hash and fails on drift.", "both", "nothing"],
             ["<code>endpoints</code>", "Lists routes from the contract, filterable by method or path.", "contract", "stdout"],
             ["<code>show METHOD PATH</code>", "Prints one route: source range, auth model, status codes, every error string with its line.", "contract", "stdout"],
             ["<code>explain ID</code>", "Prints one catalogue entry, or all of them with <code>ALL</code>.", "catalogue", "stdout"],
             ["<code>verify</code>", "Checks pages against the contract, resolves every link and support tag, validates catalogue references.", "everything", "stdout"],
             ["<code>docs build</code>", "Regenerates every page of this site from the content module.", "contract, captures, catalogue", "HTML"],
             ["<code>exitcodes</code>", "Prints the exit-code table below.", "the tool itself", "stdout"],
         ],
         None),
        ("h2", "Exit codes", "exit-codes"),
        ("p", "Every command exits with one of six codes. The table is generated from the tool's own "
              "constant, so it cannot disagree with the implementation — and argparse returns 2 for a "
              "malformed command line before the tool runs at all."),
        ("exit_codes", None),
        ("p", "A pipeline can therefore distinguish the cases that need different responses: a broken "
              "cross-reference (1) is a documentation bug, a stale contract (4) is a code change that "
              "landed without regenerating, and 3 means the checkout is incomplete rather than wrong."),
        ("h2", "Worked examples", "examples"),
        ("p", "Find every route whose path mentions reviews. Note that the review queue is mounted "
              "under <code>/api/admin</code>, which is exactly the mistake "
              "<a href=\"../errors/index.html#E-ROUTE-404\">E-ROUTE-404</a> records:"),
        ("cli_run", ["endpoints", "--grep", "reviews"]),
        ("p", "Inspect one route before writing about it. The source range, the auth model and every "
              "error string with the line that raises it come from the contract, not from the page:"),
        ("cli_run", ["show", "PUT", "/api/admin/orders/:id/assign"]),
        ("p", "Ask the catalogue a question without opening the site:"),
        ("cli_run", ["explain", "E-ASG-MASK"]),
        ("p", "And run the whole check. This is the command a CI job calls; it is also the command to "
              "run after editing any page by hand:"),
        ("cli_run", ["verify"]),
        ("note", "info", "What verify actually inspects",
         "Five things: every <code>data-endpoint</code> a page claims exists in the contract; every "
         "<code>data-status</code> and <code>data-message</code> a page quotes is produced by that "
         "route; every catalogue link resolves to a file and an anchor; every internal link and anchor "
         "on every page resolves; and every support tag used in the review points at a page that "
         "actually carries it."),
        ("h2", "Requirements", "requirements"),
        ("ul", [
            "Python 3.9 or later, standard library only. No virtualenv, no dependencies, nothing to "
            "install for the documentation build.",
            "The recording script (<code>tools/capture.py</code>) needs the service running and, for "
            "the payment pages, a sandbox copy — see the source repository's README.",
            "The CLI never talks to the network. The only network traffic in this workflow is "
            "<code>capture.py</code> against localhost.",
        ]),
    ],
}

# ---------------------------------------------------------------------------
# Standards
# ---------------------------------------------------------------------------

STYLE_GUIDE = {
    "slug": "standards/style-guide.html",
    "title": "Style guide",
    "nav": "standards/style-guide.html",
    "eyebrow": "Standards",
    "h1": "Style guide",
    "lede": "One page, because a style guide nobody reads is worse than none. These are the rules "
    "this site is written to, and the review rubric scores drafts against them.",
    "blocks": [
        ("h2", "Who is reading", "audience"),
        ("p", "A developer integrating against an API they did not build, under time pressure, "
              "usually with one screen of code open and one tab of documentation. They are looking "
              "for a field name, a status code, or an example they can paste. Write for the skim: "
              "the first sentence of a section has to be true and useful on its own."),
        ("h2", "Voice", "voice"),
        ("ul", [
            "<strong>Second person or imperative.</strong> “Send the id you received…” not “the id "
            "will be sent…”. The reader is the actor.",
            "<strong>Present tense for behaviour, imperative for instructions.</strong> “The handler "
            "answers 404” describes; “Check the id before retrying” instructs. Do not mix them in one "
            "sentence.",
            "<strong>No adjectives that cannot be verified.</strong> Seamless, powerful, robust, "
            "simple, easy: cut. If it is easy, the example shows it.",
            "<strong>Say the consequence, not the feeling.</strong> “A retried call appends a second "
            "timeline entry” beats “retries are not handled gracefully”.",
            "<strong>Do not soften defects.</strong> “This route performs no authorization check” is "
            "the sentence. Not “authorization is handled elsewhere”.",
        ]),
        ("h2", "Page skeleton for an endpoint", "skeleton"),
        ("table",
         ["Section", "Must contain", "Must not contain"],
         [
             ["Lede", "One sentence: what the call does, for whom.", "History, roadmap, apologies."],
             ["Metadata", "Source range, auth model, and the two facts a caller would otherwise discover the hard way (idempotency, defaults).", "Marketing claims."],
             ["Request", "Parameter table — name, where, type, required, description — then one runnable example.", "Every possible combination of parameters."],
             ["Response", "One captured example and a field table for anything not self-explanatory.", "Hand-typed JSON that was never executed."],
             ["Errors", "HTTP status, exact message string, when it happens, what to do.", "A promise that these are all the errors if that was not verified."],
             ["Behaviour worth knowing", "Side effects, guards, ordering, authorization gaps, retry semantics.", "Repeating the parameter table."],
         ],
         None),
        ("h2", "Terminology", "terminology"),
        ("table",
         ["Use", "Not", "Why"],
         [
             ["<code>message</code>", "error text, error message string", "Name the field, then describe it."],
             ["<code>code: -1</code>", "error code", "It is not an error code. Calling it one misleads every reader."],
             ["order, engineer, product, coupon", "task, worker, item, voucher", "Use the nouns in the payload."],
             ["endpoint, route", "API", "“The API returns…” is fine; “the API orders” is not."],
             ["returns / answers / responds", "will return", "Present tense for behaviour."],
         ],
         None),
        ("h2", "Chinese strings", "chinese"),
        ("p", "The wire values are Chinese. Reproduce them exactly, inside <code>code</code>, and do "
              "not translate them in the error tables — a reader matches what they see in the "
              "console. Translate only around them: “answers 404 订单不存在 for an unknown id”."),
        ("p", "Where a string is a poor identifier (it says nothing a program can branch on), say so "
              "once in the page that a reader will land on, and link to the catalogue entry that "
              "proposes the fix. Do not repeat the complaint on all nine pages."),
        ("h2", "Code samples", "samples"),
        ("ul", [
            "<strong>Run what you publish.</strong> Every example on this site is a recorded "
            "request/response pair. If it was not executed, it is not shown.",
            "<strong>Placeholders in angle brackets and escaped</strong>: <code>&lt;ORDER_ID&gt;</code>. "
            "Volatile values (ids, timestamps, tokens, signatures) are never published as literals.",
            "<strong>Elide with an ellipsis only at the end</strong> of a payload, and never remove a "
            "field a reader needs to see.",
            "<strong>One sample per shape.</strong> A second sample is worth its space only when it "
            "shows a different shape — a failure, or a different state.",
        ]),
        ("h2", "Cross-references", "links"),
        ("ul", [
            "Link to the anchor, not the page: <code>authentication.html#bearer-prefix</code>.",
            "Every internal link and anchor is checked by <code>shyzctl verify</code>, so a renamed "
            "heading fails the build instead of rotting.",
            "Cite the source as <code>file:line-line</code> in a span, not in a sentence: the reader "
            "who does not care should be able to skip it without losing the sentence.",
            "A claim that there is a defect must link to a catalogue entry with evidence. “This is "
            "unsafe” without a capture or a line number is an opinion.",
        ]),
        ("h2", "When to break these rules", "exceptions"),
        ("p", "Two exceptions, both used on this site. A validation message that is a joined list is "
              "quoted once as a whole and then taken apart in a table, because reproducing it inline "
              "would be unreadable. A payment page whose examples come from a sandbox says so in a "
              "callout before the first sample, because provenance outranks brevity."),
        ("p", "The test is not “does this look like the guide”. It is “would a reader be misled”. If "
              "breaking a rule prevents a wrong conclusion, break it and say why in the review."),
    ],
}

RUBRIC = {
    "slug": "standards/rubric.html",
    "title": "Review rubric",
    "nav": "standards/rubric.html",
    "eyebrow": "Standards",
    "h1": "Review rubric",
    "lede": "Four dimensions, scored 1 to 5, plus a decision rule that is written down before the "
    "drafts are read — so the verdict is repeatable and the reasoning is auditable rather than a "
    "matter of taste.",
    "blocks": [
        ("h2", "The four dimensions", "dimensions"),
        ("table",
         ["Dimension", "Weight", "What it asks"],
         [
             ["<strong>Accuracy</strong>", "0.4", "Is every claim true of the system? Field names, status codes, message strings, ordering, side effects."],
             ["<strong>Completeness</strong>", "0.2", "Are all the required sections present, and is anything a caller needs missing?"],
             ["<strong>Actionability</strong>", "0.2", "Can a developer act on it without asking a question — examples runnable, “what to do” concrete?"],
             ["<strong>Tone</strong>", "0.2", "Sentence case, second person, no marketing, consistent terms, no filler."],
         ],
         None),
        ("h2", "Anchor levels", "anchors"),
        ("table",
         ["Score", "Accuracy", "Completeness", "Actionability", "Tone"],
         [
             ["<strong>5</strong>", "Every claim matches the source and the captures. No internal inconsistency.", "Every required section, plus the one non-obvious fact a reader would have missed.", "Every example runnable as written; every failure row says what to change.", "Reads as one voice; nothing to trim."],
             ["<strong>4</strong>", "One trivial slip that does not mislead (a miscount, a vague pronoun).", "All required sections; one useful detail absent.", "Examples runnable; one guidance row generic.", "Consistent, with one flat sentence."],
             ["<strong>3</strong>", "A claim a careful reader would have to re-check; still recoverable.", "A required section thin or merged away.", "Examples need an edit before they run.", "Voice drifts; marketing adjective or filler present."],
             ["<strong>2</strong>", "A misleading claim: wrong status, wrong field, wrong order of checks.", "A required section missing.", "No usable example, or advice that would not work.", "Second person abandoned; hedging throughout."],
             ["<strong>1</strong>", "Contradicts the ground truth.", "Most required content missing.", "Nothing a developer can apply.", "Unreadable or off-audience."],
         ],
         None),
        ("h2", "The decision rule", "decision-rule"),
        ("p", "Scores alone invite arithmetic to settle an argument. The rule used here puts accuracy "
              "first and is applied in this order:"),
        ("ol", [
            "Count <strong>accuracy defects</strong>: each distinct claim that is untrue of the system, "
            "or internally inconsistent with the same document. Score accuracy from that count.",
            "If one draft has <strong>strictly fewer accuracy defects</strong> and is not worse on "
            "completeness, actionability or tone, it is <strong>preferred</strong>.",
            "If the defect counts are equal, the result is a <strong>tie</strong> — regardless of the "
            "weighted score. A pleasant document that is wrong is still wrong.",
            "Report weighted scores as context. They never overturn the accuracy test.",
        ], ),
        ("note", "info", "Why not choose on the weighted score",
         "A weighted average lets strengths in tone buy off a factual error. In an API reference a "
         "wrong field name costs a developer an afternoon; elegant prose saves them ten seconds. The "
         "weights still matter — they decide how much a defect costs once the accuracy question is "
         "settled — but they do not decide the winner."),
        ("h2", "How to run the review", "procedure"),
        ("ol", [
            "Fix the brief in writing before drafting: the facts, the required sections, the tag "
            "allowlist, the length. Both drafts get the same brief and no rubric.",
            "Draft independently. No shared context, no sight of the other draft, the same "
            "stylesheet applied afterwards so formatting cannot influence the read.",
            "Read both against the source, not against each other. Keep a defect list with the line "
            "number or capture id that proves each one.",
            "Score, apply the decision rule, then write one line of reasoning and the support tags. "
            "The tags are the audit trail: they point at the pages that were checked.",
        ]),
        ("h2", "Support tags", "tags"),
        ("p", "Every verdict carries tags of the form <code>[API-ref]</code>, <code>[error-catalog]</code> "
              "or <code>[exit-code]</code>, and each tag resolves to a page anchor on this site. A tag "
              "is a claim that a human verified that page against the source during this review — not "
              "a label for the topic."),
        ("table",
         ["Tag", "Means", "Checked against"],
         [
             ["<code>[API-ref]</code>", "A reference page was compared with the contract and the captures.", "<code>contracts/shyz-api-contract.json</code>, <code>contracts/captures.json</code>"],
             ["<code>[error-catalog]</code>", "A catalogue entry's symptom, cause and next step were re-read against the source line it cites.", "<code>errors/catalog.json</code>, source"],
             ["<code>[exit-code]</code>", "The exit-code table was compared with the tool's own constant.", "<code>tools/shyzctl.py</code>, <code>EXIT_CODES</code>"],
         ],
         None),
    ],
}

# ---------------------------------------------------------------------------
# Model review (Day 3)
# ---------------------------------------------------------------------------

REVIEW = {
    "slug": "review/index.html",
    "title": "Model review — two drafts, one verdict",
    "nav": "review/index.html",
    "eyebrow": "Review · 2026",
    "h1": "Two drafts of one page, one verdict",
    "lede": "The same brief, sent to two independent drafting sessions, produced two versions of the "
    "assign-endpoint page. This is the review: the scores, the defects each draft carries, and a "
    "verdict with one line of reasoning and support tags that point at the pages I checked.",
    "blocks": [
        ("h2", "The brief", "brief"),
        ("p", "Both drafts received identical input: the ground truth for "
              "<code>PUT /api/admin/orders/:id/assign</code> (source range, request fields, the "
              "captured success payload, all three failure strings, the check order, the absent "
              "authorization check and the absent state guard), a required section order, an HTML tag "
              "allowlist, an escaping rule, and a length target of 350-500 words. Neither saw the "
              "rubric, the other draft, or the site's stylesheet."),
        ("dl", [
            ("Draft A", "<a href=\"draft-a.html\">read it</a> — 466 words of prose"),
            ("Draft B", "<a href=\"draft-b.html\">read it</a> — 440 words of prose"),
            ("Reference page", "<a href=\"../api/put-admin-orders-assign.html\">the published page</a>, "
                               "written separately, after the review"),
        ]),
        ("h2", "Scores", "scores"),
        ("table",
         ["Draft", "Accuracy", "Completeness", "Actionability", "Tone", "Weighted"],
         [
             ["Draft A", "<span class=\"score\">5</span>", "<span class=\"score\">5</span>",
              "<span class=\"score\">4</span>", "<span class=\"score\">5</span>",
              "<span class=\"score\">4.8</span>"],
             ["Draft B", "<span class=\"score\">4</span>", "<span class=\"score\">5</span>",
              "<span class=\"score\">4</span>", "<span class=\"score\">5</span>",
              "<span class=\"score\">4.4</span>"],
         ],
         "Weights: accuracy 0.4, everything else 0.2. Accuracy defects: A 0, B 1."),
        ("h2", "What each draft got right", "right"),
        ("ul", [
            "Both reproduced all three failure strings exactly, with the correct HTTP statuses and the "
            "correct check order (body, then order, then engineer).",
            "Both stated that the handler performs no token check, in the plainest words either draft "
            "used — this is the fact a writer is most tempted to soften, and neither did.",
            "Both noticed the consequence of the missing state guard: assigning a completed order "
            "reopens it. Draft B adds that the timeline then has no matching reversal entry, which is "
            "the sharper observation.",
            "Both kept Chinese wire values untranslated inside <code>code</code>, and both proposed a "
            "concrete client-side change in the “what to do” column.",
        ]),
        ("h2", "Defect log", "defects"),
        ("table",
         ["Draft", "Defect", "Evidence", "Cost"],
         [
             ["A", "<code>curl</code> example uses a <code>&lt;BASE_URL&gt;</code> placeholder while the "
                   "rest of the site uses an explicit base URL.", "compare with "
                   "<a href=\"../api/index.html#conventions\">Conventions</a>",
              "Reader must guess the host. Not an accuracy defect."],
             ["B", "“The handler writes five things”, followed by a list of four.", "count the list in "
                   "<a href=\"draft-b.html#b-behaviour\">Draft B, Behaviour</a>",
              "A reader who counts is stopped; the count cannot be reconciled. Accuracy defect."],
             ["B", "For 404 订单不存在, the advice is “the order may have been removed” — a guess — where "
                   "the id's provenance is the checkable fact.", "<a href=\"draft-b.html#b-errors\">Draft B, Errors</a>",
              "Sends the reader looking for a deletion instead of for a stale id. Costs time, not truth."],
         ],
         "A defect has to be provable. Each row cites the place in the draft and the page it disagrees with."),
        ("h2", "Verdict", "verdict"),
        ("p", "<span class=\"chip chip--ok\">preferred: Draft A</span> <span class=\"chip\">recommended for "
              "the published page</span>"),
        ("p", "One line of reasoning: <strong>Draft A enumerates four write effects and lists four, while "
              "Draft B claims five and lists four</strong> — the only accuracy defect either draft "
              "carries — and A is no weaker on completeness, actionability or tone, so the accuracy-first "
              "rule decides without arithmetic."),
        ("p", "Support tags, each pointing at a page checked during this review:"),
        ("ul", [
            "<span class=\"tag\">[API-ref]</span> <a href=\"../api/put-admin-orders-assign.html#behaviour\">"
            "assign → Behaviour worth knowing</a> — the four write effects and the unguarded status, "
            "verified against <span class=\"cite\">server/index.js:1041-1052</span>.",
            "<span class=\"tag\">[API-ref]</span> <a href=\"../api/authentication.html#admin-routes\">"
            "Authentication → Routes without authorization</a> — the “no token check” claim that both "
            "drafts make, verified against the handler body.",
            "<span class=\"tag\">[error-catalog]</span> <a href=\"../errors/index.html#E-ASG-MASK\">"
            "E-ASG-MASK</a> — the check-order consequence both drafts describe, re-read against the "
            "captured pair.",
        ]),
        ("h2", "What this demonstrates, and what it does not", "limits"),
        ("ul", [
            "<strong>It demonstrates</strong> a review procedure that a second reviewer can repeat: a "
            "brief fixed in advance, independent drafts, a defect list with evidence, a decision rule "
            "applied before scoring preferences were known, and tags that resolve.",
            "<strong>It does not demonstrate</strong> that one model writes better documentation than "
            "another. Both drafts came from the same model in separate sessions. The gap between them "
            "is small, which is itself the honest finding: at this level of specificity the brief "
            "determines most of the quality, and the reviewer's job is to catch the residue.",
            "<strong>It also does not show</strong> what a different brief would produce. Drafts "
            "optimise what the brief asks for — here, completeness of the error table — and the "
            "published page was rewritten afterwards to add the state-machine table both drafts lacked.",
        ]),
        ("note", "info", "The published page is not Draft A",
         "Neither draft was published. "
         "<a href=\"../api/put-admin-orders-assign.html\">The reference page</a> keeps the best "
         "sentences from both, adds the state-machine table, and replaces every hand-written example "
         "with a captured pair — which is exactly the edit a review is supposed to make possible."),
    ],
}

