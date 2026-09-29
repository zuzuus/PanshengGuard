# PanshengGuard browser extension

Checks the email you are reading in Gmail against the PanshengGuard detector,
without copying it into the website. Scans made here are saved to your account
and appear in the same history and dashboard as scans made on the site.

## Loading it

1. Start both servers:

   ```powershell
   # Terminal 1 — detection service
   cd C:\FYP\Piton
   python -m uvicorn main:app --port 8000

   # Terminal 2 — web app
   cd C:\FYP\Laravel\phishing-frontend
   php artisan serve --port=8001
   ```

2. Open `chrome://extensions` and turn on **Developer mode** (top right).
3. Click **Load unpacked** and pick this folder (`C:\FYP\extension`).
4. Sign in at <http://127.0.0.1:8001>, open **Profile → Browser Extension**, and
   click **Generate token**. Copy it — it is shown once.
5. Click the extension icon, paste the token, press **Save**, then
   **Test connection**. It should say `Connected as <your name>`.

## Using it

Open a message in Gmail. A **Scan with PanshengGuard** button appears above the
message body; the verdict banner is drawn in place underneath it.

Scanning is manual, not automatic. Checking every message as it opens would send
the whole mailbox to the server and exhaust the per-user rate limit within
seconds of scrolling.

### What gets highlighted

After a scan, the phrases that produced the verdict are marked up **inside the
message**, colour-coded by manipulation technique:

| Colour | Technique |
|---|---|
| Amber | Urgency — deadlines, "act now" |
| Blue | False authority — banks, security teams, IT helpdesk |
| Red | Fear — suspension, loss of access, legal threats |
| Purple | Scarcity — final warning, one attempt, limited time |

The banner lists how many phrases were marked and which techniques appeared.

Matching is on **whole words**. The scoring service matches substrings, so it
counts "bank" inside "Maybank2u" and "now" inside "know"; highlighting those
would draw a box round the wrong word in front of the reader. Where the two
disagree the phrase is left unmarked, which is the safer direction to be wrong
in — the banner may name a technique the highlights do not show.

### How loud the banner gets

Verdicts are not all the same size. A **Critical Risk** result gets a thick
rail, a larger heading and a shadow; **Low Risk** collapses to a quiet strip
with its reasoning tucked behind a summary line. A single banner weight for
every outcome trains people to stop reading it.

## If the in-page button does not appear

The extension reads Gmail's DOM using class names (`div.a3s` for the body,
`h2.hP` for the subject). These are not a public API and Google can change them
at any time.

The popup has a **paste box** for exactly this case. It talks to the same
endpoint and does not touch Gmail's DOM, so it keeps working whatever Google
changes. Use it if the button is missing.

## How it is wired

```
Gmail page  ──►  content.js   (reads the message, draws the banner)
                     │  chrome.runtime.sendMessage
                     ▼
                background.js  (holds the token, makes the request)
                     │  POST /api/extension/analyze
                     ▼
                  Laravel      (validates the token, saves the scan)
                     │  POST /api/analyze
                     ▼
                  FastAPI      (TF-IDF + features, VirusTotal)
```

The fetch happens in the service worker rather than the content script for two
reasons: a request from inside `mail.google.com` would be cross-origin and
blocked, and the API token never has to be exposed to page scripts.

## Authentication

Session cookies cannot be used — the extension calls from a `chrome-extension://`
origin and does not carry the site's cookies. Making them work cross-origin would
need `SameSite=None; Secure`, which needs HTTPS the local setup does not have.

So the extension authenticates with a bearer token. Only its SHA-256 hash is
stored in the database, which is why the plain value is shown once and cannot be
retrieved later. Generating a new token revokes the old one.

## Files

| File | Purpose |
|---|---|
| `manifest.json` | Manifest V3 declaration, permissions, content script registration |
| `background.js` | Service worker — the only place that holds the token or calls the API |
| `content.js` | Injected into Gmail; extracts the message, draws the banner |
| `content.css` | Banner styling, scoped under `.pg-` so it cannot inherit Gmail's CSS |
| `popup.html` / `popup.js` | Settings, connection test, and the paste-box fallback |

## Known limits

- Gmail only. Outlook and Yahoo use entirely different markup.
- URL scanning is off by default for extension calls, because VirusTotal's free
  tier allows four requests a minute and an email can contain several links.
- The server address defaults to `http://127.0.0.1:8001`; change it in the popup
  if you run Laravel on a different port.
