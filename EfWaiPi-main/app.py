# app.py

import os
import re
import html
import time
import logging
import pickle
import numpy as np
import streamlit as st

from scipy.sparse import hstack

from preprocess import preprocess
from score import score_label, sophistication_score
from virustotal import extract_urls, scan_urls

# -------------------------------------------------
# SECURITY CONSTANTS
# -------------------------------------------------

MAX_INPUT_LENGTH = 50_000   # characters
MAX_REQUESTS     = 5        # per session window
WINDOW_SECONDS   = 60

# -------------------------------------------------
# AUDIT LOGGING  (#10)
# -------------------------------------------------

logging.basicConfig(
    filename="audit.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
_audit = logging.getLogger("phishing_detector")

# -------------------------------------------------
# TRUSTED DOMAINS
# -------------------------------------------------

TRUSTED_DOMAINS = [
    "google.com",
    "microsoft.com",
    "apple.com",
    "github.com",
    "amazon.com",
]

def trust_score(text: str) -> float:
    text = str(text).lower()
    for domain in TRUSTED_DOMAINS:
        if domain in text:
            return 0.9
    return 0.3


# -------------------------------------------------
# SECURITY HELPERS
# -------------------------------------------------

def sanitize_input(text: str) -> str:
    """XSS prevention (#8) + data-layer sanitization (#4): strip scripts and HTML tags."""
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'<[^>]+>', '', text)
    text = html.unescape(text)
    return text


def mask_pii(text: str) -> str:
    """PII masking (#7): redact emails, phone numbers, and card numbers before processing."""
    text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b', '[EMAIL]', text)
    text = re.sub(r'\b(\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b', '[PHONE]', text)
    text = re.sub(r'\b(?:\d{4}[-\s]?){3}\d{4}\b', '[CARD]', text)
    return text


def check_rate_limit() -> bool:
    """Rate limiting (#6): allow at most MAX_REQUESTS analyses per WINDOW_SECONDS."""
    now = time.time()
    if "request_timestamps" not in st.session_state:
        st.session_state.request_timestamps = []
    st.session_state.request_timestamps = [
        t for t in st.session_state.request_timestamps
        if now - t < WINDOW_SECONDS
    ]
    if len(st.session_state.request_timestamps) >= MAX_REQUESTS:
        return False
    st.session_state.request_timestamps.append(now)
    return True


# -------------------------------------------------
# PAGE CONFIG
# -------------------------------------------------

st.set_page_config(
    page_title="Phishing Detector",
    page_icon="🎣",
    layout="centered"
)

# -------------------------------------------------
# STYLE
# -------------------------------------------------

st.markdown("""
<style>
.risk-badge {
    display:inline-block;
    padding:4px 14px;
    border-radius:20px;
    font-weight:600;
    font-size:0.85rem;
}
.risk-low      { background:#d1fae5; color:#065f46; }
.risk-moderate { background:#fef3c7; color:#92400e; }
.risk-high     { background:#fee2e2; color:#991b1b; }
.risk-critical { background:#7f1d1d; color:#fef2f2; }

.technique-tag {
    display:inline-block;
    margin:3px 4px;
    padding:3px 10px;
    border-radius:12px;
    font-size:0.8rem;
    font-weight:500;
}

.tag-urgency   { background:#fef9c3; color:#713f12; }
.tag-authority { background:#dbeafe; color:#1e3a5f; }
.tag-fear      { background:#fce7f3; color:#831843; }
.tag-scarcity  { background:#ede9fe; color:#4c1d95; }
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------
# HEADER
# -------------------------------------------------

st.title("🎣 Phishing Email Detector")
st.caption("ML classifier with trust-domain context scoring")
st.divider()

# -------------------------------------------------
# LOAD MODEL
# -------------------------------------------------

@st.cache_resource
def load_model():
    if not os.path.exists("model.pkl") or not os.path.exists("vectorizer.pkl"):
        return None, None

    model = pickle.load(open("model.pkl", "rb"))
    vectorizer = pickle.load(open("vectorizer.pkl", "rb"))
    return model, vectorizer

model, vectorizer = load_model()

if model is None:
    st.error("Model files not found. Train first.")
    st.stop()

# -------------------------------------------------
# INPUT
# -------------------------------------------------

email_input = st.text_area(
    "Paste email content below:",
    height=220,
    placeholder="Paste subject + body here..."
)

vt_enabled = st.toggle("Check URLs with VirusTotal", value=True)
st.caption("URL analysis powered by VirusTotal (free tier — 500 checks/day)")

analyse_btn = st.button(
    "Analyse Email",
    type="primary",
    use_container_width=True
)

# -------------------------------------------------
# ANALYSIS
# -------------------------------------------------

if analyse_btn:

    # --- Input Validation (#3) ---
    if not isinstance(email_input, str) or not email_input.strip():
        st.warning("Paste an email first.")
        st.stop()

    if len(email_input) > MAX_INPUT_LENGTH:
        st.error(f"Input too long. Maximum {MAX_INPUT_LENGTH:,} characters allowed.")
        _audit.warning("input_rejected | reason=too_long | len=%d", len(email_input))
        st.stop()

    # --- Rate Limiting (#6) ---
    if not check_rate_limit():
        st.error(f"Rate limit reached: maximum {MAX_REQUESTS} analyses per {WINDOW_SECONDS} seconds. Please wait.")
        _audit.warning("rate_limit_exceeded")
        st.stop()

    with st.spinner("Analysing... because apparently trust issues need automation."):

        # --- XSS Prevention + Data Layer Sanitization (#8, #4) ---
        safe_input = sanitize_input(email_input)

        # --- PII Masking (#7) ---
        safe_input = mask_pii(safe_input)

        clean_text = preprocess(safe_input)

        if not clean_text.strip():
            st.error("No usable text after preprocessing.")
            st.stop()

        # -----------------------------------------
        # TEXT FEATURES
        # -----------------------------------------

        vec_text = vectorizer.transform([clean_text])

        # -----------------------------------------
        # TRUST FEATURE (MUST MATCH TRAINING)
        # -----------------------------------------

        score_trust = trust_score(safe_input)
        vec_trust = np.array([[score_trust]])

        vec = hstack([vec_text, vec_trust])

        # -----------------------------------------
        # PREDICT
        # -----------------------------------------

        if hasattr(model, "predict_proba"):
            prob = float(model.predict_proba(vec)[0][1])
        else:
            prob = float(model.predict(vec)[0])

        label = "PHISHING" if prob > 0.5 else "LEGITIMATE"
        is_phish = label == "PHISHING"

        # -----------------------------------------
        # SOPHISTICATION SCORE
        # -----------------------------------------

        score, found, explanation = sophistication_score(safe_input, prob)
        risk = score_label(score)

        # --- Audit Log (#10) ---
        _audit.info(
            "analysis | input_len=%d | label=%s | prob=%.3f | score=%s | risk=%s",
            len(email_input), label, prob, score, risk,
        )

# -------------------------------------------------
# RESULTS
# -------------------------------------------------

    st.divider()
    st.subheader("Results", anchor=False)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Classification", label)

        if is_phish:
            st.error("⚠️ Likely phishing")
        else:
            st.success("✅ Likely legitimate")

    with col2:
        st.metric("Phishing Probability", f"{prob:.1%}")
        st.progress(prob)

    with col3:
        st.metric("Sophistication Score", f"{score}%")

        badge_class = {
            "Low Risk": "risk-low",
            "Moderate Risk": "risk-moderate",
            "High Risk": "risk-high",
            "Critical Risk": "risk-critical"
        }.get(risk, "risk-low")

        st.markdown(
            f'<span class="risk-badge {badge_class}">{risk}</span>',
            unsafe_allow_html=True
        )

    st.divider()

# -------------------------------------------------
# TECHNIQUES
# -------------------------------------------------

    st.subheader("Manipulation Techniques Detected", anchor=False)

    tag_classes = {
        "urgency": "tag-urgency",
        "authority": "tag-authority",
        "fear": "tag-fear",
        "scarcity": "tag-scarcity"
    }

    any_found = any(v for v in found.values())

    if any_found:
        for technique, hits in found.items():
            if hits:
                cls = tag_classes.get(technique, "")
                tags = " ".join(
                    f'<span class="technique-tag {cls}">{x}</span>'
                    for x in hits
                )

                st.markdown(
                    f"**{technique.capitalize()}** &nbsp; {tags}",
                    unsafe_allow_html=True
                )
    else:
        st.info("No manipulation techniques detected.")

# -------------------------------------------------
# URL SCAN (VIRUSTOTAL)
# -------------------------------------------------

    st.divider()
    st.subheader("🔗 URL Scan (VirusTotal)", anchor=False)

    if not vt_enabled:
        st.info("URL scanning disabled.")
    else:
        urls = extract_urls(email_input)

        if not urls:
            st.info("No URLs found in this email.")
        else:
            st.caption(f"Scanning {len(urls)} URL(s) — this may take a few seconds...")

            vt_results = scan_urls(urls)

            for r in vt_results:
                url_display = f"`{r['url']}`"
                if r["status"] == "malicious":
                    st.error(f"🔴 **Malicious** — {r['malicious']}/{r['total']} engines flagged {url_display}")
                elif r["status"] == "suspicious":
                    st.warning(f"🟡 **Suspicious** — {r['suspicious']}/{r['total']} engines flagged {url_display}")
                elif r["status"] == "clean":
                    st.success(f"✅ **Clean** — 0/{r['total']} engines flagged {url_display}")
                else:
                    st.warning(f"⚠️ Could not scan {url_display}")

            _audit.info("url_scan | count=%d | urls=%s", len(vt_results), [r["url"] for r in vt_results])

# -------------------------------------------------
# DEBUG TOKENS
# -------------------------------------------------

    with st.expander("🔬 View preprocessed tokens"):
        st.code(clean_text)
