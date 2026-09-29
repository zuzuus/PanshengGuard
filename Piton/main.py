"""
FastAPI backend for the Phishing Email Sophistication Scorer.

Replaces from streamlit to Laravel frontend, with a REST API.

"""

import os
import re
import html
import json
import time
import pickle
import logging
from collections import defaultdict, deque

import numpy as np
from scipy.sparse import hstack
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from defence import normalise
from features import FEATURE_ORDER, extract_features
from preprocess import preprocess
from score import score_label, sophistication_score, generate_tips
from virustotal import extract_urls, scan_urls

# -------------------------------------------------
# CONFIG
# -------------------------------------------------

MAX_INPUT_LENGTH = 50_000       # characters
MAX_REQUESTS     = 5            # per window, per client
WINDOW_SECONDS   = 60

# Decision threshold for calling an email phishing. Written by train.py so it
# always matches the model that was trained alongside it; 0.5 if that file is
# missing. Lowering it catches more phishing at the cost of more false alarms -
# on the held-out fold, 0.40 caught every phishing email (recall 1.000) but
# raised false positives from 16 to 24.
def _load_threshold(default: float = 0.5) -> float:
    try:
        with open("threshold.json", encoding="utf-8") as f:
            return float(json.load(f)["threshold"])
    except (OSError, ValueError, KeyError, TypeError):
        return default


THRESHOLD = _load_threshold()

# Lock this down to your actual frontend origin(s) before deploying.
# "*" is fine for local dev only.
ALLOWED_ORIGINS = [
    "http://localhost:8001",
    "http://127.0.0.1:8001",
    # "https://your-laravel-domain.com",
]

# Plain-English wording for each binary feature, so the interface can tell the
# user WHY a mail scored the way it did instead of showing a bare risk badge.
SIGNAL_TEXT = {
    "link_has_ip":          "The link points at a raw IP address instead of a domain name.",
    "link_is_shortener":    "The link uses a URL shortener, which hides the real destination.",
    "link_suspicious_tld":  "The link uses a domain ending commonly registered for scams.",
    "link_brand_typosquat": "The link domain is a near-miss spelling of a well-known brand.",
    "sender_link_mismatch": "The sender's domain does not match the domain being linked to.",
    "has_urgency":          "The message pressures you to act within a short deadline.",
    "has_threat":           "The message threatens suspension, loss of access or legal action.",
    "asks_credentials":     "The message asks you to enter a password, TAC, PIN or card details.",
    "has_reward_money":     "The message offers money, a prize, a refund or a voucher.",
    "generic_greeting":     "The message opens with a generic greeting rather than your name.",
}

TRUSTED_DOMAINS = [
    # --- Malaysian banks ---
    "maybank2u.com.my",
    "maybank.com.my",
    "cimbclicks.com.my",
    "cimb.com.my",
    "pbebank.com",
    "publicbank.com.my",
    "rhbgroup.com",
    "hongleongconnect.my",
    "hlb.com.my",
    "bankislam.com",
    "ambank.com.my",
    "amonline.com.my",
    "bsn.com.my",
    "alliancebank.com.my",
    "affinalways.com",
    "muamalat.com.my",
    "agrobank.com.my",
    "ocbc.com.my",
    "hsbc.com.my",
    "uob.com.my",

    # --- Government / statutory bodies ---
    "kwsp.gov.my",
    "hasil.gov.my",
    "jpj.gov.my",
    "jpn.gov.my",
    "imi.gov.my",
    "pdrm.gov.my",
    "rmp.gov.my",
    "perkeso.gov.my",
    "malaysia.gov.my",
    "mycert.org.my",
    "mampu.gov.my",

    # --- E-wallets / payments ---
    "touchngo.com.my",
    "tngdigital.com.my",
    "boost.com.my",
    "setel.com.my",
    "bigpay.com.my",
    "grab.com",

    # --- E-commerce ---
    "shopee.com.my",
    "lazada.com.my",
    "zalora.com.my",
    "pgmall.my",
    "mudah.my",

    # --- Telcos ---
    "maxis.com.my",
    "celcom.com.my",
    "digi.com.my",
    "celcomdigi.com",
    "umobile.com.my",
    "unifi.com.my",
    "tm.com.my",
    "yes.my",

    # --- Utilities ---
    "tnb.com.my",
    "airselangor.com",
    "syabas.com.my",
    "gasmalaysia.com",

    # --- Logistics / courier ---
    "pos.com.my",
    "jtexpress.my",
    "ninjavan.co",
    "gdexpress.com",
    "citylinkexpress.com",
    "dhl.com",

    # --- Subscription / media ---
    "astro.com.my",
    "netflix.com",
    "spotify.com",

    # --- Social media / messaging ---
    "facebook.com",
    "fb.com",
    "messenger.com",
    "instagram.com",
    "threads.net",
    "twitter.com",
    "tiktok.com",
    "youtube.com",
    "linkedin.com",
    "whatsapp.com",
    "telegram.org",
    "snapchat.com",
    "pinterest.com",
    "reddit.com",
    "discord.com",
    "twitch.tv",
    "wechat.com",

    # --- Education: public universities (IPTA) ---
    "gmi.edu.my",
    "um.edu.my",
    "ukm.edu.my",
    "upm.edu.my",
    "usm.my",
    "utm.my",
    "uitm.edu.my",
    "uum.edu.my",
    "iium.edu.my",
    "uiam.edu.my",
    "unimas.my",
    "ums.edu.my",
    "upsi.edu.my",
    "usim.edu.my",
    "umt.edu.my",
    "umpsa.edu.my",
    "unimap.edu.my",
    "uthm.edu.my",
    "utem.edu.my",
    "umk.edu.my",
    "unisza.edu.my",
    "upnm.edu.my",

    # --- Education: private universities ---
    "uniten.edu.my",
    "utp.edu.my",
    "mmu.edu.my",
    "utar.edu.my",
    "tarc.edu.my",
    "unikl.edu.my",
    "taylors.edu.my",
    "sunway.edu.my",
    "monash.edu.my",
    "nottingham.edu.my",
    "curtin.edu.my",
    "swinburne.edu.my",
    "inti.edu.my",
    "segi.edu.my",
    "ucsiuniversity.edu.my",
    "help.edu.my",
    "apu.edu.my",
    "apiit.edu.my",
    "msu.edu.my",
    "mahsa.edu.my",
    "imu.edu.my",
    "iukl.edu.my",
    "cyberjaya.edu.my",
    "nilai.edu.my",
    "lincoln.edu.my",
    "firstcity.edu.my",
    "oum.edu.my",
    "wou.edu.my",
    "aeu.edu.my",
    "unitar.my",

    # --- Education: ministries / agencies ---
    "moe.gov.my",
    "mohe.gov.my",
    "mqa.gov.my",
    "ptptn.gov.my",
    "jpa.gov.my",
    "mara.gov.my",
    "politeknik.edu.my",
    "mypolycc.edu.my",

    # --- Education: learning platforms & academic tools ---
    "moodle.org",
    "blackboard.com",
    "instructure.com",
    "turnitin.com",
    "coursera.org",
    "edx.org",
    "udemy.com",
    "khanacademy.org",
    "zoom.us",
    "office.com",
    "overleaf.com",
    "mendeley.com",
    "researchgate.net",
    "sciencedirect.com",
    "springer.com",
    "scopus.com",
    "ieee.org",
    "grammarly.com",

    # --- Global ---
    "google.com",
    "microsoft.com",
    "apple.com",
    "github.com",
    "amazon.com",
]

# -------------------------------------------------
# AUDIT LOGGING (unchanged behaviour from app.py)
# -------------------------------------------------

logging.basicConfig(
    filename="audit.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
_audit = logging.getLogger("phishing_detector")

# -------------------------------------------------
# RATE LIMITING
# -------------------------------------------------
# Streamlit used st.session_state, which only exists inside a single browser
# tab's Streamlit session. There is no equivalent in a stateless API.
#
# Keying off request.client.host looks like the obvious replacement, but it is
# wrong here: the browser never talks to this service. Laravel calls it
# server-side, so every request in the whole application arrives from the same
# address, and the limit would apply to the application as a whole - five
# analyses per minute shared between every user at once. Two people opening the
# site together would trip it, and so would the browser extension, which scans
# once per email.
#
# Laravel names the account (or guest session) it is acting for in X-Client-Id,
# and that is what gets limited.

_request_log: dict[str, deque] = defaultdict(deque)

# Above this many tracked clients, sweep the idle ones on each admission.
_EVICT_THRESHOLD = 512


def client_key(request: Request) -> str:
    """
    Identify who to rate limit.

    X-Client-Id is trusted, which is only acceptable because this service is
    not publicly reachable - it listens on localhost and only the Laravel app
    calls it. If it is ever exposed on a public address, drop this header and
    enforce the limit at the reverse proxy instead, where a caller cannot
    choose its own identity.
    """
    forwarded = request.headers.get("x-client-id", "").strip()
    if forwarded:
        return forwarded[:128]
    if request.client:
        return request.client.host
    return "unknown"


def _evict_idle(now: float) -> None:
    """
    Forget clients that have gone quiet.

    Without this the dict gains one permanent entry per distinct client and
    never shrinks for the lifetime of the process.
    """
    if len(_request_log) < _EVICT_THRESHOLD:
        return
    stale = [k for k, q in _request_log.items() if not q or now - q[-1] > WINDOW_SECONDS]
    for key in stale:
        del _request_log[key]


def check_rate_limit(client_id: str) -> bool:
    now = time.time()
    q = _request_log[client_id]
    while q and now - q[0] > WINDOW_SECONDS:
        q.popleft()
    if len(q) >= MAX_REQUESTS:
        return False
    q.append(now)
    _evict_idle(now)
    return True


# -------------------------------------------------
# SECURITY HELPERS (identical to app.py)
# -------------------------------------------------

# Lines a webmail interface adds around the message when someone selects the
# page and copies it. They are not part of the email, but they do change what
# the model sees: a real Maybank alert copied out of Gmail arrived carrying
# "Skip to content", a message counter and three stacked notifications, which
# tripled its length and flipped the verdict.
_CHROME_PATTERNS = [
    r'^\s*skip to content\s*$',
    r'^\s*using \w[\w .]* with screen readers\s*$',
    r'^\s*\d+\s+of\s+[\d,]+\s*$',
    r'^\s*(inbox|sent|drafts|spam|starred|archive|important)\s*$',
    r'^\s*to me\s*$',
    r'^\s*none selected\s*$',
    r'^\s*unsubscribe\s*$',
    # "Thu, Sep 3, 9:53 AM (12 days ago)" and similar mailbox timestamps
    r'^\s*\w{3},\s+\w{3}\s+\d{1,2},?\s+\d{1,2}:\d{2}\s*(AM|PM)?\s*(\([^)]*\))?\s*$',
    r'^\s*\w{3}\s+\d{1,2},\s+\d{4},\s+\d{1,2}:\d{2}\s*(AM|PM)\s*(\([^)]*\))?\s*$',
]
_CHROME_RE = [re.compile(p, re.IGNORECASE) for p in _CHROME_PATTERNS]


def strip_mail_client_chrome(text: str) -> str:
    """Drop webmail interface lines so only the message itself is analysed."""
    kept = [ln for ln in str(text).split("\n")
            if not any(rx.match(ln) for rx in _CHROME_RE)]
    return "\n".join(kept).strip()


def sanitize_input(text: str) -> str:
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'<[^>]+>', '', text)
    text = html.unescape(text)
    return text


def mask_pii(text: str) -> str:
    text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b', '[EMAIL]', text)
    text = re.sub(r'\b(\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b', '[PHONE]', text)
    text = re.sub(r'\b(?:\d{4}[-\s]?){3}\d{4}\b', '[CARD]', text)
    return text


_URL_RE  = re.compile(r'https?://[^\s<>"\']+', re.IGNORECASE)
_BARE_RE = re.compile(r'\b(?:[a-z0-9-]+\.)+[a-z]{2,}\b', re.IGNORECASE)


def _hosts(text: str) -> list[str]:
    """
    Every hostname the text refers to, whether written as a full link or
    mentioned bare in prose ("log in at maybank2u.com.my").

    Links are consumed first and reduced to their host, so a path cannot be used
    to smuggle a trusted name into an untrusted site:
    https://attacker.com/maybank2u.com.my/login yields only "attacker.com".
    """
    text = str(text).lower()
    hosts = []

    for m in _URL_RE.finditer(text):
        host = re.sub(r"^https?://", "", m.group(0))
        host = re.split(r"[/?#]", host, maxsplit=1)[0]
        hosts.append(host.split("@")[-1])       # drop any user:pass@ prefix

    for m in _BARE_RE.finditer(_URL_RE.sub(" ", text)):
        hosts.append(m.group(0))

    return [h.removeprefix("www.").strip(".") for h in hosts]


def trust_score(text: str) -> float:
    """
    0.9 if the mail points at a domain we recognise, 0.3 otherwise.

    Matching is on the parsed host, not a substring of the raw text. A plain
    "domain in text" test is trivially bypassed: "login-facebook.com" contains
    "facebook.com", and "secure-maybank2u.com.my.attacker.net" contains
    "maybank2u.com.my", so both would have been scored as trusted. Only an exact
    host match or a real subdomain of one counts.
    """
    for host in _hosts(text):
        for domain in TRUSTED_DOMAINS:
            if host == domain or host.endswith("." + domain):
                return 0.9
    return 0.3


# -------------------------------------------------
# MODEL LOADING (once, at startup — replaces st.cache_resource)
# -------------------------------------------------

MODEL = None
VECTORIZER = None
SCALER = None


def load_model():
    """
    Load the three artefacts train.py writes. They are a matched set - the
    scaler was fitted on the same rows as the model, so mixing an old scaler
    with a new model silently shifts every numeric feature.
    """
    global MODEL, VECTORIZER, SCALER
    missing = [n for n in ("model.pkl", "vectorizer.pkl", "scaler.pkl")
               if not os.path.exists(n)]
    if missing:
        raise RuntimeError(f"{', '.join(missing)} not found. Run train.py first.")
    with open("model.pkl", "rb") as f:
        MODEL = pickle.load(f)
    with open("vectorizer.pkl", "rb") as f:
        VECTORIZER = pickle.load(f)
    with open("scaler.pkl", "rb") as f:
        SCALER = pickle.load(f)

    # Fail at startup with a readable message rather than 500-ing on the first
    # request from somewhere deep inside sklearn.
    #
    # uvicorn --reload watches .py files but not .pkl files, so retraining
    # swaps the artefacts on disk without restarting the server. Whichever way
    # the mismatch happens, the fix is the same: retrain, then restart.
    n_feat = getattr(SCALER, "n_features_in_", None)
    n_text = len(getattr(VECTORIZER, "vocabulary_", {}))
    n_model = getattr(MODEL, "n_features_in_", None)

    if n_feat != len(FEATURE_ORDER):
        raise RuntimeError(
            f"scaler.pkl expects {n_feat} features but features.py defines "
            f"{len(FEATURE_ORDER)}. The saved artefacts are older than the code "
            f"- run 'python train.py', then restart this server."
        )
    if n_model != n_text + n_feat:
        raise RuntimeError(
            f"model.pkl expects {n_model} inputs but vectorizer + scaler supply "
            f"{n_text} + {n_feat} = {n_text + n_feat}. The three .pkl files are "
            f"not from the same training run - run 'python train.py', then "
            f"restart this server."
        )
    _audit.info("model_loaded | tfidf=%d | features=%d | total=%d",
                n_text, n_feat, n_model)


# -------------------------------------------------
# APP
# -------------------------------------------------

app = FastAPI(title="Phishing Email Sophistication API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    load_model()


# -------------------------------------------------
# SCHEMAS
# -------------------------------------------------

class AnalyzeRequest(BaseModel):
    email_text: str = Field(..., description="Raw pasted email subject + body")
    check_urls: bool = Field(True, description="Whether to run VirusTotal URL scan")


class UrlResult(BaseModel):
    url: str
    status: str
    malicious: int
    suspicious: int
    total: int


class Tip(BaseModel):
    technique: str
    warning: str
    advice: str


class AnalyzeResponse(BaseModel):
    label: str
    is_phishing: bool
    probability: float
    sophistication_score: float
    risk: str
    techniques: dict[str, list[str]]
    url_results: list[UrlResult]
    clean_tokens: str
    tips: list[Tip]
    checklist: list[str]
    link_trusted: bool          # does the mail reference a known-good domain?
    trust_score: float          # 0.9 if yes, 0.3 if not (reported, not a model input)
    signals: list[str]          # human-readable red flags that fired on this mail


# -------------------------------------------------
# ENDPOINTS
# -------------------------------------------------

@app.get("/api/health")
def health():
    return {"status": "ok", "model_loaded": MODEL is not None}


@app.post("/api/analyze", response_model=AnalyzeResponse)
def analyze(payload: AnalyzeRequest, request: Request):
    client_id = client_key(request)

    # --- Input validation (#3) ---
    email_input = payload.email_text
    if not isinstance(email_input, str) or not email_input.strip():
        raise HTTPException(status_code=400, detail="Email text cannot be empty.")

    if len(email_input) > MAX_INPUT_LENGTH:
        _audit.warning("input_rejected | reason=too_long | len=%d", len(email_input))
        raise HTTPException(
            status_code=413,
            detail=f"Input too long. Maximum {MAX_INPUT_LENGTH:,} characters allowed.",
        )

    # --- Rate limiting (#6) ---
    if not check_rate_limit(client_id):
        _audit.warning("rate_limit_exceeded | client=%s", client_id)
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit reached: max {MAX_REQUESTS} analyses per {WINDOW_SECONDS}s.",
        )

    # --- Undo character-level obfuscation before anything reads the text ---
    #
    # Measured on the 539 phishing emails in the dataset: an attacker who swaps
    # Latin letters for identical-looking Cyrillic ones, or writes "v3r1fy",
    # drops detection to 95.9-97.8%. Combined with a clean-looking link it falls
    # to 46.2%. Folding those characters back first restores the text attacks
    # completely (100%) and lifts the combined case to 78.7%.
    #
    # It costs nothing: false alarms on the 503 legitimate emails were 0.0%
    # both with and without this step. See experiment.py.
    email_input = normalise(email_input)

    # --- Strip webmail chrome, then sanitize + mask PII (#8, #4, #7) ---
    # The chrome has to go before anything measures the text, otherwise the
    # interface lines count towards body_length and all-caps totals.
    mail_text = strip_mail_client_chrome(email_input)
    safe_input = sanitize_input(mail_text)
    safe_input = mask_pii(safe_input)

    clean_text = preprocess(safe_input)
    if not clean_text.strip():
        raise HTTPException(status_code=422, detail="No usable text after preprocessing.")

    # --- Build the feature vector, exactly as train.py does ---
    #
    #     hstack([ TF-IDF(clean_text) , scaled features.py block ])
    #
    # The numeric block comes from features.py, which train.py also imports, so
    # the ordering cannot drift. Note the features are read from the RAW input,
    # not the sanitised text: stripping HTML and masking PII would destroy the
    # link structure the features exist to measure.
    #
    # trust_score is deliberately NOT among them. In the training data every
    # legitimate email links to a known-good domain and every phishing email
    # does not, so as an input it separates the classes perfectly and the
    # classifier stops learning anything else (measured on the earlier model: it
    # carried ~14x the weight of the strongest word). It is reported as its own
    # signal instead, and VirusTotal handles domain reputation properly below.
    vec_text = VECTORIZER.transform([clean_text])
    feats = extract_features(mail_text)
    vec_feats = SCALER.transform(np.array([[feats[k] for k in FEATURE_ORDER]]))
    vec = hstack([vec_text, vec_feats]).tocsr()

    score_trust = trust_score(safe_input)

    # --- Predict ---
    if hasattr(MODEL, "predict_proba"):
        prob = float(MODEL.predict_proba(vec)[0][1])
    else:
        prob = float(MODEL.predict(vec)[0])

    label = "PHISHING" if prob >= THRESHOLD else "LEGITIMATE"
    is_phish = label == "PHISHING"

    # --- Sophistication score ---
    score, found, _explanation = sophistication_score(safe_input, prob)
    risk = score_label(score)

    # --- Plain-language tips ---
    tips_data = generate_tips(found, is_phish)

    _audit.info(
        "analysis | input_len=%d | label=%s | prob=%.3f | score=%s | risk=%s",
        len(email_input), label, prob, score, risk,
    )

    # --- URL scan (VirusTotal) ---
    url_results: list[dict] = []
    if payload.check_urls:
        urls = extract_urls(email_input)
        if urls:
            url_results = scan_urls(urls)
            _audit.info("url_scan | count=%d | urls=%s", len(url_results), [r["url"] for r in url_results])

    return AnalyzeResponse(
        label=label,
        is_phishing=is_phish,
        probability=prob,
        sophistication_score=score,
        risk=risk,
        techniques=found,
        url_results=url_results,
        clean_tokens=clean_text,
        tips=tips_data["tips"],
        checklist=tips_data["checklist"],
        link_trusted=score_trust >= 0.9,
        trust_score=score_trust,
        signals=[SIGNAL_TEXT[k] for k in SIGNAL_TEXT if feats.get(k, 0.0) >= 1.0],
    )
