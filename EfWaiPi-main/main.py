"""
FastAPI backend for the Phishing Email Sophistication Scorer.

This replaces app.py (Streamlit) as the *interface* layer, but reuses the
exact same core logic: preprocess.py, score.py, virustotal.py, model.pkl,
vectorizer.pkl. Nothing about the ML/NLP pipeline changes — only how
requests come in and results go out.

Run with:
    uvicorn main:app --reload --port 8000

Your Laravel (or any) frontend calls POST /api/analyze with JSON and
renders the JSON response however you like.
"""

import os
import re
import html
import time
import pickle
import logging
from collections import defaultdict, deque

import numpy as np
from scipy.sparse import hstack
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from preprocess import preprocess
from score import score_label, sophistication_score
from virustotal import extract_urls, scan_urls

# -------------------------------------------------
# CONFIG
# -------------------------------------------------

MAX_INPUT_LENGTH = 50_000       # characters
MAX_REQUESTS     = 5            # per window, per client
WINDOW_SECONDS   = 60

# Lock this down to your actual frontend origin(s) before deploying.
# "*" is fine for local dev only.
ALLOWED_ORIGINS = [
    "http://localhost",
    "http://localhost:8080",
    "http://127.0.0.1:8000",
    # "https://your-laravel-domain.com",
]

TRUSTED_DOMAINS = [
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
# Streamlit used st.session_state, which only exists inside a single
# browser tab's Streamlit session. There's no equivalent in a stateless
# API, so this keys off client IP instead. Good enough for a local FYP
# demo; for real deployment behind a reverse proxy, read the
# X-Forwarded-For header instead of request.client.host.

_request_log: dict[str, deque] = defaultdict(deque)


def check_rate_limit(client_id: str) -> bool:
    now = time.time()
    q = _request_log[client_id]
    while q and now - q[0] > WINDOW_SECONDS:
        q.popleft()
    if len(q) >= MAX_REQUESTS:
        return False
    q.append(now)
    return True


# -------------------------------------------------
# SECURITY HELPERS (identical to app.py)
# -------------------------------------------------

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


def trust_score(text: str) -> float:
    text = str(text).lower()
    for domain in TRUSTED_DOMAINS:
        if domain in text:
            return 0.9
    return 0.3


# -------------------------------------------------
# MODEL LOADING (once, at startup — replaces st.cache_resource)
# -------------------------------------------------

MODEL = None
VECTORIZER = None


def load_model():
    global MODEL, VECTORIZER
    if not os.path.exists("model.pkl") or not os.path.exists("vectorizer.pkl"):
        raise RuntimeError("model.pkl / vectorizer.pkl not found. Train first.")
    with open("model.pkl", "rb") as f:
        MODEL = pickle.load(f)
    with open("vectorizer.pkl", "rb") as f:
        VECTORIZER = pickle.load(f)


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


class AnalyzeResponse(BaseModel):
    label: str
    is_phishing: bool
    probability: float
    sophistication_score: float
    risk: str
    techniques: dict[str, list[str]]
    url_results: list[UrlResult]
    clean_tokens: str


# -------------------------------------------------
# ENDPOINTS
# -------------------------------------------------

@app.get("/api/health")
def health():
    return {"status": "ok", "model_loaded": MODEL is not None}


@app.post("/api/analyze", response_model=AnalyzeResponse)
def analyze(payload: AnalyzeRequest, request: Request):
    client_id = request.client.host if request.client else "unknown"

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

    # --- Sanitize + mask PII (#8, #4, #7) ---
    safe_input = sanitize_input(email_input)
    safe_input = mask_pii(safe_input)

    clean_text = preprocess(safe_input)
    if not clean_text.strip():
        raise HTTPException(status_code=422, detail="No usable text after preprocessing.")

    # --- Vectorize + trust feature (must match training) ---
    vec_text = VECTORIZER.transform([clean_text])
    score_trust = trust_score(safe_input)
    vec_trust = np.array([[score_trust]])
    vec = hstack([vec_text, vec_trust])

    # --- Predict ---
    if hasattr(MODEL, "predict_proba"):
        prob = float(MODEL.predict_proba(vec)[0][1])
    else:
        prob = float(MODEL.predict(vec)[0])

    label = "PHISHING" if prob > 0.5 else "LEGITIMATE"
    is_phish = label == "PHISHING"

    # --- Sophistication score ---
    score, found, _explanation = sophistication_score(safe_input, prob)
    risk = score_label(score)

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
    )
