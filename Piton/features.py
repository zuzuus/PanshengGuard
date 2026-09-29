"""
Feature extraction shared by train.py and main.py.

Both the training script and the live API import FEATURE_ORDER and
extract_features() from here, so the feature vector can never drift between the
two. If you add a feature, add it once in this file and retrain - nothing in
main.py needs editing.

Two feature groups are deliberately NOT model inputs:

  * sender_is_official  - in the dataset this is 0.999 accurate on its own. It
    is the label wearing a disguise: every legitimate mail comes from an
    official sender and every phishing mail does not. Feed it in and the
    classifier stops reading anything else.

  * link_is_official    - same problem, softer. Whether a domain is on a
    whitelist is genuinely useful in production, but here it separates the
    classes by construction. It is computed and REPORTED (main.py returns it as
    link_trusted) rather than trained on, so the text and structure features
    have to do real work.

Dropped entirely: url_count and link_has_at, which are constant across all 1060
rows in the dataset and therefore carry no information.
"""

from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Lookup tables
# ---------------------------------------------------------------------------

SHORTENERS = {
    "bit.ly", "cutt.ly", "tinyurl.com", "shorturl.at", "is.gd", "t.ly",
    "rebrand.ly", "goo.gl", "ow.ly", "buff.ly", "tiny.cc", "rb.gy", "shorte.st",
    "t.co", "s.id", "linktr.ee",
}

# TLDs that are cheap, weakly policed and heavily abused for phishing.
SUSPICIOUS_TLDS = {
    "xyz", "top", "live", "club", "icu", "buzz", "monster", "cyou", "online",
    "site", "info", "shop", "work", "click", "link", "rest", "fit", "gq", "cf",
    "tk", "ml", "ga", "quest", "sbs", "lol",
}

URGENCY = [
    "immediately", "urgent", "within 24 hours", "within 12 hours", "24 hours",
    "48 hours", "72 hours", "before midnight", "act now", "right away",
    "as soon as possible", "expires tonight", "expire in", "closing soon",
    "limited slots", "last chance", "final warning", "segera", "serta-merta",
    "dalam masa", "sekarang", "tamat tempoh", "hari ini",
]

THREAT = [
    "suspended", "suspension", "terminated", "disabled", "locked", "restricted",
    "blocked", "permanent", "legal action", "court", "warrant", "forfeited",
    "data loss", "returned to sender", "cancelled", "barred", "disconnection",
    "digantung", "mahkamah", "waran tangkap", "diputuskan", "digugurkan",
    "tindakan undang", "dikenakan tindakan",
]

REWARD = [
    "congratulations", "you have won", "you've won", "reward", "cashback",
    "voucher", "prize", "lucky draw", "bonus", "grant", "refund", "free",
    "guaranteed profit", "daily returns", "passive income", "tahniah",
    "bayaran balik", "hadiah", "percuma", "pinjaman", "diluluskan",
]

DEADLINE = [
    "expires", "expire", "deadline", "due", "before", "within", "by midnight",
    "closing", "last day", "valid until", "tempoh", "sebelum", "dalam tempoh",
]

GENERIC_GREETINGS = [
    "dear customer", "dear valued customer", "dear user", "dear sir/madam",
    "dear sir", "dear madam", "dear account holder", "dear account owner",
    "attention: account owner", "dear taxpayer", "dear colleague",
    "dear member", "hi valued shopper", "valued shopper", "dear client",
    "hello,", "tuan/puan,", "kepada pelanggan",
]

# Verbs that indicate the mail wants the reader to HAND OVER a secret, as
# opposed to merely mentioning one. "Log in to view your statement" is normal;
# "you will be asked to enter your Password and TAC" is not.
CRED_NOUNS = [
    "password", "kata laluan", "tac", "otp", "pin", "cvv", "card number",
    "nombor kad", "username", "user id", "login credentials", "banking credentials",
    "nombor ic", "mykad", "bank account details", "maklumat perbankan",
    "billing details", "card details",
]
CRED_VERBS = [
    "enter", "re-enter", "confirm", "provide", "submit", "verify your identity",
    "asked to", "sign in with", "log in with", "login with", "update your",
    "kemas kini", "memasukkan", "sahkan", "lengkapkan",
]
# Legitimate mail often says "we will never ask for your password" - that must
# not count as asking for credentials.
NEGATIONS = [
    "never ask", "will not ask", "do not share", "jangan kongsi",
    "tidak akan meminta", "tidak akan bertanya", "staff will never",
]

_URL_RE = re.compile(r'https?://[^\s<>"\')\]]+', re.IGNORECASE)
_IPV4_RE = re.compile(r'^\d{1,3}(\.\d{1,3}){3}$')

# Brand names as they appear in a domain's first label. A lookalike is a host
# whose first label is one or two edits away from one of these without being an
# exact match - maybannk2u, bannkislam, applle, microssoft, gogle, c1mbcl1cks.
# Only names of 5+ characters are compared, so short ones (pos, dhl, yes, u)
# cannot collide with each other by accident.
BRAND_STEMS = {
    "maybank2u", "cimbclicks", "pbebank", "publicbank", "rhbgroup", "rhbnow",
    "bankislam", "hongleongconnect", "hlbconnect", "ambank", "alliancebank",
    "affinbank", "muamalat", "bankmuamalat", "bankrakyat", "mybsn",
    "maybank", "cimbbank",
    "kwsp", "hasil", "perkeso", "ptptn", "lhdnmytax", "myinvois",
    "shopee", "lazada", "zalora", "carousell", "pgmall", "tiktok", "shopeepay",
    "netflix", "spotify", "youtube", "hotstar", "astro", "iqiyi",
    "apple", "microsoft", "google",
    "maxis", "celcom", "celcomdigi", "umobile", "unifi", "tmunifi",
    "gasmalaysia", "airselangor", "tenaga",
    "jtexpress", "ninjavan", "citylink", "flashexpress", "gdexpress", "poslaju",
    "touchngo", "touchngoewallet", "grabpay", "bigpay", "setel", "myboost",
    "malaysiaairlines", "batikair", "airasia", "booking", "agoda",
    "jobstreet", "ptptnmy", "petronas", "genting",
}
_MIN_STEM = 5


def _edit_distance(a: str, b: str, cap: int = 3) -> int:
    """Levenshtein distance, giving up once it exceeds `cap`."""
    if abs(len(a) - len(b)) > cap:
        return cap + 1
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        if min(cur) > cap:
            return cap + 1
        prev = cur
    return prev[-1]


def looks_like_typosquat(host: str) -> int:
    """
    1 when the host impersonates a known brand by misspelling it.

    This is the one signal that catches the hardest rows in the dataset:
    maybannk2u.net, bannkislam.net and banislam.my carry no other tell at all -
    no hyphen, no odd TLD, no threat, polite named greeting - so every other
    flag stays silent on them.
    """
    if not host or _IPV4_RE.match(host):
        return 0
    stem = host.split(".")[0].removeprefix("www.")
    if len(stem) < _MIN_STEM or stem in BRAND_STEMS:
        return 0
    for brand in BRAND_STEMS:
        if len(brand) < _MIN_STEM:
            continue
        d = _edit_distance(stem, brand, cap=2)
        if d and d <= 2:
            return 1
    return 0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def extract_links(text: str) -> list[str]:
    return _URL_RE.findall(str(text))


def host_of(url: str) -> str:
    host = re.sub(r"^https?://", "", str(url).strip().lower())
    host = re.split(r"[/?#]", host, maxsplit=1)[0]
    host = host.split("@")[-1].split(":")[0]
    return host.removeprefix("www.").strip(".")


def _any(text: str, needles) -> int:
    return int(any(n in text for n in needles))


def _strip_negated(text: str) -> str:
    """Drop sentences that disclaim asking for credentials."""
    keep = []
    for sentence in re.split(r"(?<=[.!?\n])", text):
        if not any(n in sentence for n in NEGATIONS):
            keep.append(sentence)
    return "".join(keep)


def asks_for_credentials(text_lower: str) -> int:
    """
    True only when a credential noun appears near an action verb, after
    disclaimers have been removed. The original dataset's version of this flag
    fired on any mention of logging in and scored 49.4% precision - a coin
    flip - because "log in to view your statement" looks the same to it as
    "enter your Password and TAC".
    """
    body = _strip_negated(text_lower)
    for noun in CRED_NOUNS:
        for m in re.finditer(re.escape(noun), body):
            window = body[max(0, m.start() - 90): m.end() + 40]
            if any(v in window for v in CRED_VERBS):
                return 1
    return 0


# ---------------------------------------------------------------------------
# Feature vector
# ---------------------------------------------------------------------------

# Upper bounds, so an unusual input saturates instead of scoring arbitrarily
# far past the decision boundary. A linear model extrapolates without limit:
# feed it a value ten standard deviations outside anything it trained on and it
# will happily return a confidence it has no basis for.
CLIP = {
    "link_domain_length":   45,
    "link_num_hyphens":      8,
    "link_subdomain_depth":  6,
}

# Deliberately NOT features: subject_length, body_length, num_exclamation and
# num_allcaps_words.
#
# They separate this corpus well - phishing templates average 333 characters
# against 243 for legitimate ones - but that is a property of the generator, not
# of phishing. Length is not evidence. Trained on them the model gave
# body_length a +1.144 coefficient, and a genuine Maybank credit alert copied
# out of Gmail (three stacked notifications, 1077 characters) was called
# phishing at 0.994 confidence without a single red flag firing. The same mail
# with the interface lines removed scored 0.010. A feature that turns a correct
# answer into a confident wrong one when the user pastes slightly more text is
# not measuring anything real, so it is gone.

FEATURE_ORDER = [
    # link structure - generalises to domains never seen in training
    "link_has_ip",
    "link_is_shortener",
    "link_suspicious_tld",
    "link_num_hyphens",
    "link_subdomain_depth",
    "link_domain_length",
    "link_uses_https",
    "link_brand_typosquat",
    "sender_link_mismatch",
    # social engineering levers
    "has_urgency",
    "has_threat",
    "asks_credentials",
    "has_reward_money",
    "has_deadline",
    "generic_greeting",
]


def split_subject_body(text: str) -> tuple[str, str]:
    """
    First non-empty line is the subject, the rest is the body.

    Training rows store subject and body in separate columns, but the API
    receives one pasted blob. Both paths call this, so subject_length and
    body_length mean the same thing in training and in production - otherwise
    every request would arrive with subject_length=0 against a training mean
    of ~45 and the model would be reading a feature it was never fitted on.
    """
    lines = str(text).split("\n")
    for i, line in enumerate(lines):
        if line.strip():
            return line.strip(), "\n".join(lines[i + 1:]).strip()
    return "", str(text)


def extract_features(text: str, sender: str = "") -> dict[str, float]:
    """Numeric features for one email. Keys match FEATURE_ORDER exactly."""
    subject, body = split_subject_body(text)
    sender = str(sender)
    blob = f"{subject}\n{body}"
    low = blob.lower()

    links = extract_links(blob)
    host = host_of(links[0]) if links else ""
    tld = host.rsplit(".", 1)[-1] if "." in host else ""
    sender_host = host_of(sender.split("@")[-1]) if "@" in sender else ""

    # a bare IP, a shortener, or a lookalike where the sender domain has nothing
    # to do with the link domain
    mismatch = 0
    if host and sender_host:
        mismatch = int(not (host == sender_host
                            or host.endswith("." + sender_host)
                            or sender_host.endswith("." + host)))

    out = {
        "link_has_ip":          float(bool(_IPV4_RE.match(host))),
        "link_is_shortener":    float(host in SHORTENERS),
        "link_suspicious_tld":  float(tld in SUSPICIOUS_TLDS),
        "link_num_hyphens":     float(host.count("-")),
        "link_subdomain_depth": float(host.count(".")),
        "link_domain_length":   float(len(host)),
        "link_uses_https":      float(bool(links) and links[0].lower().startswith("https")),
        "link_brand_typosquat": float(looks_like_typosquat(host)),
        "sender_link_mismatch": float(mismatch),

        "has_urgency":          float(_any(low, URGENCY)),
        "has_threat":           float(_any(low, THREAT)),
        "asks_credentials":     float(asks_for_credentials(low)),
        "has_reward_money":     float(_any(low, REWARD)),
        "has_deadline":         float(_any(low, DEADLINE)),
        "generic_greeting":     float(_any(low, GENERIC_GREETINGS)),
    }
    for k, hi in CLIP.items():
        out[k] = min(out[k], float(hi))
    return out


def feature_vector(text: str, sender: str = "") -> list[float]:
    """Same features, ordered as FEATURE_ORDER - this is what the model sees."""
    f = extract_features(text, sender)
    return [f[k] for k in FEATURE_ORDER]
