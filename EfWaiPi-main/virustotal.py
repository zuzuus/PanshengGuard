import os
import re
import base64
import time
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.environ.get("VIRUSTOTAL_API_KEY", "")
BASE    = "https://www.virustotal.com/api/v3"
HEADERS = {"x-apikey": API_KEY}
MAX_URLS = 2

_URL_RE = re.compile(r'https?://[^\s\'"<>()\[\]\\]+')


def extract_urls(text: str) -> list[str]:
    seen = dict.fromkeys(_URL_RE.findall(text))
    return list(seen)[:MAX_URLS]


def _url_id(url: str) -> str:
    return base64.urlsafe_b64encode(url.encode()).decode().rstrip("=")


def _lookup(url: str) -> dict | None:
    r = requests.get(f"{BASE}/urls/{_url_id(url)}", headers=HEADERS, timeout=10)
    return r.json() if r.status_code == 200 else None


def _submit(url: str) -> dict | None:
    r = requests.post(f"{BASE}/urls", headers=HEADERS, data={"url": url}, timeout=10)
    if r.status_code != 200:
        return None
    analysis_id = r.json()["data"]["id"]
    time.sleep(4)
    r2 = requests.get(f"{BASE}/analyses/{analysis_id}", headers=HEADERS, timeout=10)
    return r2.json() if r2.status_code == 200 else None


def scan_urls(urls: list[str]) -> list[dict]:
    results = []
    for url in urls:
        data = _lookup(url) or _submit(url)

        if data is None:
            results.append({"url": url, "status": "error", "malicious": 0, "suspicious": 0, "total": 0})
            continue

        attrs = data.get("data", {}).get("attributes", {})
        stats = attrs.get("last_analysis_stats") or attrs.get("stats") or {}

        malicious  = stats.get("malicious", 0)
        suspicious = stats.get("suspicious", 0)
        total      = sum(stats.values()) if stats else 0

        status = "malicious" if malicious > 0 else "suspicious" if suspicious > 0 else "clean"

        results.append({
            "url":        url,
            "status":     status,
            "malicious":  malicious,
            "suspicious": suspicious,
            "total":      total,
        })

        time.sleep(0.5)

    return results
