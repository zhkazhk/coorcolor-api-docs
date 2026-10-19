# CoorColor API — documentation sample

A working sample of how I write **and verify** API documentation, built from a real
service I wrote: a printer-service back office (63 HTTP endpoints behind a WeChat
mini program and an admin console).

Published as a static site, ready for GitHub Pages.

| Path | What it is |
| --- | --- |
| `index.html` | Landing page: what the sample contains and how it is checked |
| `api/` | Reference: overview, authentication guide, and eight endpoints documented in depth |
| `cli/` | `shyzctl` — real `--help` output, subcommands, exit-code table |
| `errors/` | Error catalogue: symptom → cause → next step → document, each with a failing and a working capture |
| `standards/` | One-page style guide, four-dimension review rubric |
| `review/` | Two independent drafts of the same page, scored, with a verdict and support tags |
| `contracts/` | The parsed API contract, the recorded request/response pairs, and the redacted source snapshot |
| `tools/` | `shyzctl.py` (contract + verify), `sitegen.py` (build), `capture.py` (recording), `audit_site.py` (HTML audit), `redact_snapshot.py` |

## The idea in one paragraph

Documentation that is written next to code decays. This one is generated from three
machine-readable sources — a contract parsed out of the Express source, 39 recorded
request/response pairs, and the error catalogue as JSON — and `shyzctl verify` fails
when a published page disagrees with any of them. Every example on the site is a pair
that was actually executed, not JSON typed from memory.

## Build and check

Python 3.9+, standard library only. No dependencies, no node, no build chain.

```bash
python tools/shyzctl.py docs build      # render every page from tools/content.py
python tools/shyzctl.py verify          # pages vs contract, links, anchors, support tags
python tools/audit_site.py              # tag balance, CSS coverage, leftovers
```

Preview locally:

```bash
python -m http.server 8080
# open http://127.0.0.1:8080/
```

Exit codes are documented in `cli/index.html` and mirrored by `EXIT_CODES` in
`tools/shyzctl.py` (0 OK, 1 findings, 2 usage, 3 missing input, 4 drift, 5 internal).

## Re-deriving the contract

`contracts/shyz-api-contract.json` is generated, never hand-edited:

```bash
python tools/shyzctl.py contract build --source path/to/server/index.js
python tools/shyzctl.py contract check      # fails with exit 4 if the source moved
```

## Re-recording the examples

`tools/capture.py` needs the service running (`http://127.0.0.1:3000`) and, for the two
payment pages, a sandbox copy whose outbound WeChat Pay calls are stubbed:

```bash
python tools/capture.py --prepare-sandbox path/to/server
# start the sandbox on 3101 with the real node_modules on NODE_PATH, then:
python tools/capture.py --core http://127.0.0.1:3000 --pay http://127.0.0.1:3101
```

Recording is **byte-stable**: volatile values (JWTs, order ids, timestamps, nonces,
signatures) are replaced with placeholders, so re-running produces the same file and a
diff means something real changed.

## Redaction

`contracts/source/` ships the exact lines the documentation cites, with every credential
replaced in place so line numbers survive. `tools/redact_snapshot.py` performs the
redaction and refuses to write a file if any credential-shaped string survives. No
merchant key, app secret or JWT secret is published, and the payment examples were
recorded against a dummy key.

## Deploy to GitHub Pages

```bash
git init
git add .
git commit -m "Documentation sample: API reference, CLI, error catalogue, review"
git branch -M main
git remote add origin git@github.com:zhkazhk/coorcolor-api-docs.git
git push -u origin main
```

Then in the repository: **Settings → Pages → Source: Deploy from a branch → main / (root)**.
`.nojekyll` is included, so no Jekyll processing is applied and `assets/` and `tools/`
are served as-is.

The deployed site is served from `main` at
<https://zhkazhk.github.io/coorcolor-api-docs/>. Nothing is built server-side: the HTML in
the repository is the HTML that ships, which is why the check that pages match the
generator belongs in CI rather than in a habit.

## Honesty notes
- Eight of the 63 endpoints are documented in depth; the other 55 are listed in the
  inventory with their status codes, generated from the contract. That is a sample of the
  method, not a complete manual.
- The payment pages use a sandboxed payment gateway. Parameter names, the MD5 signing
  order and the response shape are the real implementation; the signature value is not.
- The two review drafts come from the same model in separate sessions. That shows a
  repeatable review procedure; it is not a comparison of two vendors, and the review page
  says so.
- Defects found while writing this (a payment amount taken from the client, a callback
  whose XML body is never parsed, admin routes without authorization) are recorded as
  catalogue entries with evidence. They are application bugs, documented rather than
  hidden.
