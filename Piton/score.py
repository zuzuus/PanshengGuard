from __future__ import annotations

import re
from functools import lru_cache

KEYWORDS: dict[str, list[str]] = {
    'urgency': [
        'urgent', 'immediately', 'now', 'today', 'expire', 'asap',
        'without delay', 'right away', 'no later than', 'deadline',
        'time sensitive', 'act fast', 'hurry', '24 hours', 'hours remaining',
    ],
    'authority': [
        'bank', 'official', 'government', 'verify', 'account', 'paypal',
        'security team', 'compliance', 'hr department', 'it helpdesk',
        'fraud prevention', 'executive', 'administration', 'head office',
        'customer support', 'account services',
    ],
    'fear': [
        'suspended', 'blocked', 'terminate', 'unauthorized', 'alert',
        'restricted', 'compromised', 'security risk', 'lose access',
        'permanently disabled', 'flagged', 'illegal activity', 'breach',
        'your data', 'will be closed',
    ],
    'scarcity': [
        'limited', 'last chance', 'only', 'exclusive', 'offer expires',
        'final warning', 'one attempt', 'expires soon', 'window closing',
        'last opportunity', 'running out', 'while stocks last',
    ],
}
 
WEIGHTS: dict[str, float] = {
    'urgency':   0.30,
    'authority': 0.28,
    'fear':      0.25,
    'scarcity':  0.17,
}
 
# ML vs technique blend
ML_WEIGHT = 0.65
TECHNIQUE_WEIGHT = 0.35


@lru_cache(maxsize=256)
def _pattern(word: str) -> re.Pattern:
    """
    Anchor a keyword to the start of a word, but let it run on at the end.

    A plain substring test counted "bank" inside "Maybank" and "now" inside
    "know" - 60 false hits across the 1042-row dataset, and worse, it made the
    interface claim a technique while the extension had nothing to highlight,
    because that highlighting matches whole words.

    Requiring a boundary at BOTH ends fixes those but breaks more than it
    mends: "expire" stops matching "expires" and "expired", dropping from 127
    real hits to 20, and "deadline" from 23 to 6. Those inflections are exactly
    the urgency the keyword exists to catch.

    Anchoring only the front keeps every inflection and still rejects the words
    that merely contain the keyword somewhere in the middle.
    """
    return re.compile(rf"\b{re.escape(word)}")


def _matches(word: str, text_lower: str) -> bool:
    return _pattern(word).search(text_lower) is not None
 
 
def sophistication_score(
    text: str,
    phishing_prob: float,
) -> tuple[float, dict[str, list[str]], list[str]]:
    """
    Parameters
    ----------
    text          : raw email text (subject + body)
    phishing_prob : float in [0, 1] from model.predict_proba()
 
    Returns
    -------
    score       : float 0.0–100.0 (percentage)
    found       : dict mapping technique name → list of matched keywords
    explanation : list of human-readable strings for the UI
    """
    text_lower = text.lower()
 
    # --- Technique scoring ---
    technique_score = 0.0
    found: dict[str, list[str]] = {}
 
    for technique, words in KEYWORDS.items():
        hits = [w for w in words if _matches(w, text_lower)]
        found[technique] = hits
        # normalise: cap at 1.0, require 2 hits for full weight
        normalised = min(len(hits) / 2.0, 1.0)
        technique_score += WEIGHTS[technique] * normalised
 
    # technique_score is now in [0, 1]
 
    # --- Blend ---
    raw = ML_WEIGHT * phishing_prob + TECHNIQUE_WEIGHT * technique_score
 
    # --- Map to 0–100% ---
    score = round(min(raw, 1.0) * 100, 1)
 
    # --- Explanation ---
    explanation: list[str] = []
    for technique, hits in found.items():
        if hits:
            explanation.append(
                f"{technique.capitalize()}: {', '.join(hits)}"
            )
 
    return score, found, explanation
 
 
def score_label(score: float) -> str:
    """Return a short risk label for a given 0–100 percentage score."""
    if score <= 30:
        return "Low Risk"
    if score <= 60:
        return "Moderate Risk"
    if score <= 80:
        return "High Risk"
    return "Critical Risk"

TIPS: dict[str, dict[str, str]] = {
    'urgency': {
        'warning': "This email pressures you to act fast, which is a common phishing tactic.",
        'advice': "Pause. Legitimate deadlines are almost always longer than a few hours — never let urgency stop you from verifying independently.",
    },
    'authority': {
        'warning': "This email claims to be from a bank, government body, or IT department.",
        'advice': "Contact the organization directly using a number or site you already trust — never one provided in the email.",
    },
    'fear': {
        'warning': "This email threatens account suspension, data loss, or legal consequences.",
        'advice': "Fear-based pressure is a manipulation tactic. Log into the actual service directly by typing the URL yourself, instead of clicking any link.",
    },
    'scarcity': {
        'warning': "This email claims limited time, one attempt, or an exclusive offer.",
        'advice': "A real offer will still exist tomorrow — sleep on it before clicking anything.",
    },
}

GENERAL_CHECKLIST = [
    "Don't click any links or download attachments in this email.",
    "Don't reply, even to unsubscribe — it confirms your email is active.",
    "Report it: forward to your email provider's phishing report address, then delete.",
    "If you already clicked a link or entered info, change that password immediately and monitor the account.",
]


def generate_tips(found: dict[str, list[str]], is_phishing: bool) -> dict:
    """Build plain-language warnings + advice based on detected techniques."""
    if not is_phishing:
        return {"tips": [], "checklist": []}

    tips = [
        {"technique": technique, **TIPS[technique]}
        for technique, hits in found.items()
        if hits and technique in TIPS
    ]

    return {"tips": tips, "checklist": GENERAL_CHECKLIST}
 
