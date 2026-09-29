from __future__ import annotations
 
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
        hits = [w for w in words if w in text_lower]
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
 
