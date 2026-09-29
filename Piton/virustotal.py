"""
VirusTotal URL reputation lookup.

Design rule for this module: it never raises. The URL scan is a supplementary
signal layered on top of the classifier - if VirusTotal is unreachable, rate
limited, or returns something unparseable, the email classification is still
perfectly valid and must still reach the user. Previously any network error
propagated out of scan_urls, through /api/analyze, and surfaced in Laravel as
"Analysis service returned an error", losing a result that had already been
computed. Being offline should cost you the link check, not the whole verdict.
"""

import os
import re
import base64
import time
import logging

import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.environ.get("VIRUSTOTAL_API_KEY", "")
BASE = "https://www.virustotal.com/api/v3"
HEADERS = {"x-apikey": API_KEY}

MAX_URLS = 2
TIMEOUT = 8           # seconds per HTTP call
ANALYSIS_WAIT = 4     # seconds to let a fresh submission finish scanning

# Hard ceiling on everything scan_urls does, in seconds.
#
# Per-call timeouts alone are not enough. Two URLs can cost six HTTP calls plus
# two waits, so at 8s each a stalled VirusTotal would burn roughly a minute -
# past Laravel's own Http::timeout(30), which aborts the request and discards a
# classification that had already been computed. That is the same failure this
# module exists to prevent, so the whole scan is bounded and any URL that does
# not fit in the remaining budget is simply reported as unscanned.
TOTAL_BUDGET = 20

_log = logging.getLogger("phishing_detector")

_URL_RE = re.compile(r'https?://[^\s\'"<>()\[\]\\]+')


def extract_urls(text: str) -> list[str]:
    seen = dict.fromkeys(_URL_RE.findall(text))
    return list(seen)[:MAX_URLS]


def _url_id(url: str) -> str:
    return base64.urlsafe_b64encode(url.encode()).decode().rstrip("=")


def _unscanned(url: str) -> dict:
    """The shape the API returns when a link could not be checked."""
    return {"url": url, "status": "error", "malicious": 0, "suspicious": 0, "total": 0}


def _request_json(method: str, path: str, timeout: float, **kwargs) -> dict | None:
    """
    Make one call to VirusTotal and return parsed JSON, or None on any failure.

    Catches RequestException (covers timeouts, DNS failure, connection refused,
    TLS errors) and a non-200 status, and treats a body that is not valid JSON
    the same way. Nothing escapes.
    """
    if timeout <= 0:
        return None

    try:
        response = requests.request(
            method, f"{BASE}{path}", headers=HEADERS, timeout=timeout, **kwargs
        )
    except requests.RequestException as exc:
        _log.warning("virustotal_unreachable | %s %s | %s", method, path, exc)
        return None

    if response.status_code != 200:
        # 401 = bad key, 429 = quota exhausted (the free tier allows 4/min),
        # 404 = URL not in the database yet, which is normal and handled by
        # the caller falling through to _submit.
        _log.info("virustotal_http | %s %s | status=%d", method, path, response.status_code)
        return None

    try:
        return response.json()
    except ValueError:
        _log.warning("virustotal_bad_json | %s %s", method, path)
        return None


def _lookup(url: str, budget: float = TIMEOUT) -> dict | None:
    """Ask for an existing report. Returns None if VirusTotal has not seen it."""
    return _request_json("GET", f"/urls/{_url_id(url)}", timeout=min(TIMEOUT, budget))


def _submit(url: str, budget: float = TIMEOUT * 2 + ANALYSIS_WAIT) -> dict | None:
    """
    Submit an unseen URL for scanning, wait briefly, then read the analysis.

    Needs two calls plus a wait, so it is skipped entirely when the remaining
    budget cannot cover them - a half-finished submission tells us nothing.
    """
    if budget < ANALYSIS_WAIT + 2:
        return None

    submission = _request_json("POST", "/urls", timeout=min(TIMEOUT, budget), data={"url": url})
    if not submission:
        return None

    payload = submission.get("data")
    analysis_id = payload.get("id") if isinstance(payload, dict) else None
    if not analysis_id:
        _log.warning("virustotal_no_analysis_id | url=%s", url)
        return None

    time.sleep(ANALYSIS_WAIT)
    return _request_json("GET", f"/analyses/{analysis_id}", timeout=TIMEOUT)


def scan_urls(urls: list[str]) -> list[dict]:
    if not urls:
        return []

    # Fail loudly in the log but quietly in the response. Without this the
    # missing key showed up only as every link mysteriously erroring.
    if not API_KEY:
        _log.warning(
            "virustotal_no_api_key | set VIRUSTOTAL_API_KEY in .env | skipping %d url(s)",
            len(urls),
        )
        return [_unscanned(url) for url in urls]

    results = []
    deadline = time.monotonic() + TOTAL_BUDGET

    for url in urls:
        remaining = deadline - time.monotonic()
        if remaining <= 1:
            _log.info("virustotal_budget_spent | skipping %s", url)
            results.append(_unscanned(url))
            continue

        data = _lookup(url, remaining)
        if data is None:
            data = _submit(url, deadline - time.monotonic())

        if data is None:
            results.append(_unscanned(url))
            continue

        payload = data.get("data")
        attrs = payload.get("attributes", {}) if isinstance(payload, dict) else {}
        stats = attrs.get("last_analysis_stats") or attrs.get("stats") or {}

        # Keep only real integers - a malformed body must not make sum() raise,
        # and bool is a subclass of int so it has to be excluded explicitly.
        counts = {
            k: v for k, v in stats.items()
            if isinstance(v, int) and not isinstance(v, bool)
        }

        # No engine results at all is not a clean bill of health. Reporting it
        # as "0/0 engines flagged this link" would read as reassurance we have
        # not actually earned.
        if not counts:
            results.append(_unscanned(url))
            continue

        malicious = counts.get("malicious", 0)
        suspicious = counts.get("suspicious", 0)

        results.append({
            "url": url,
            "status": "malicious" if malicious > 0 else "suspicious" if suspicious > 0 else "clean",
            "malicious": malicious,
            "suspicious": suspicious,
            "total": sum(counts.values()),
        })

        time.sleep(0.5)

    return results
