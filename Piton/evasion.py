"""
Evasion techniques, for attacking our own detector.

These are the edits a real attacker makes when a filter starts blocking them.
None of them change what a human reads - that is the whole point. They change
what the *machine* reads, which is a different thing entirely.

Kept in its own module so the same functions can be reused later to build a
hardened pipeline and to generate training data, rather than being buried in a
one-off experiment script.

Scope note for the write-up: everything here runs offline against our own
model. Nothing is sent anywhere, and no generated message leaves the project.
This is the standard closed-lab form of penetration testing - you attack the
thing you are responsible for, so that you find the holes before someone else
does.
"""

from __future__ import annotations

import random
import re

from score import KEYWORDS

# Every keyword the rule-based scorer looks for, longest first so that
# "final warning" is handled before "final".
ALL_KEYWORDS = sorted(
    {word for words in KEYWORDS.values() for word in words},
    key=len,
    reverse=True,
)

# ---------------------------------------------------------------------------
# 1. Homoglyphs
# ---------------------------------------------------------------------------
# Characters from other alphabets that render identically to Latin ones. To a
# reader "urgent" is unchanged; to the tokeniser it is a word it has never seen.
HOMOGLYPHS = {
    "a": "а",  # CYRILLIC SMALL LETTER A
    "c": "с",  # CYRILLIC SMALL LETTER ES
    "e": "е",  # CYRILLIC SMALL LETTER IE
    "i": "і",  # CYRILLIC SMALL LETTER BYELORUSSIAN-UKRAINIAN I
    "j": "ј",  # CYRILLIC SMALL LETTER JE
    "o": "о",  # CYRILLIC SMALL LETTER O
    "p": "р",  # CYRILLIC SMALL LETTER ER
    "s": "ѕ",  # CYRILLIC SMALL LETTER DZE
    "x": "х",  # CYRILLIC SMALL LETTER HA
    "y": "у",  # CYRILLIC SMALL LETTER U
    # Upper case has its own lookalikes. Substituting the lower-case form into
    # "URGENT" would be visible; these are not.
    "A": "А",
    "C": "С",
    "E": "Е",
    "I": "І",
    "J": "Ј",
    "O": "О",
    "P": "Р",
    "S": "Ѕ",
    "X": "Х",
    "Y": "У",
}

# ---------------------------------------------------------------------------
# 2. Character substitution ("leetspeak")
# ---------------------------------------------------------------------------
# Cruder than homoglyphs and visible to the reader, but people read through it
# without effort - which is exactly why it still works on humans.
LEET = {
    "a": "@",
    "e": "3",
    "i": "1",
    "l": "1",
    "o": "0",
    "s": "5",
}

ZERO_WIDTH = "​"  # invisible, but splits a word in two for the tokeniser

# ---------------------------------------------------------------------------
# 5. Synonym substitution
# ---------------------------------------------------------------------------
# The strongest attack of the five, because it defeats keyword matching AND
# the text model at once: the message keeps its meaning while using none of
# the vocabulary the classifier learned.
SYNONYMS = {
    "urgent": "time-critical",
    "immediately": "without further delay",
    "suspended": "placed on hold",
    "blocked": "restricted from use",
    "terminate": "discontinue",
    "verify": "confirm ownership of",
    "account": "profile",
    "unauthorized": "unrecognised",
    "expire": "lapse",
    "deadline": "cut-off point",
    "alert": "notice",
    "security team": "protection desk",
    "compromised": "affected",
    "final warning": "last reminder",
    "act fast": "respond promptly",
    "limited": "restricted",
    "now": "at once",
    "today": "before the day ends",
    "bank": "financial institution",
    "official": "authorised",
}

# Bland, entirely ordinary text used to drown the signal. Written to look like
# the boilerplate real companies append to everything.
FILLER = """
This message was sent to you because you hold an active profile with our
service. We send occasional updates about features, maintenance windows and
changes to the terms under which the service is provided. You may adjust which
categories of message you receive from the preferences area of your profile at
any time, and the change takes effect on the next business day.

Our support hours are Monday to Friday, nine in the morning until six in the
evening, excluding public holidays. Messages received outside those hours are
answered in order of arrival on the following working day. Typical response
time during busy periods is two to three working days.

The contents of this message, including any files sent with it, are intended
for the named recipient and may contain information that is confidential. If
you have received it by mistake, please let the sender know and remove it from
your system. Any review, distribution or copying of this message by anyone
other than the intended recipient is not permitted.

We take the protection of personal information seriously and handle it in line
with our published privacy notice, which sets out what we collect, why we
collect it, how long it is kept, and the choices available to you. A copy of
that notice is available from the help area of our website at any time.
"""


def _keyword_spans(text: str) -> list[tuple[int, int]]:
    """
    Where the trigger words sit in the text.

    An attacker does not mangle the whole message - that would make it
    unreadable. They mangle the handful of words the filter is watching for and
    leave everything else alone.
    """
    spans = []
    lower = text.lower()

    for keyword in ALL_KEYWORDS:
        for match in re.finditer(rf"\b{re.escape(keyword)}", lower):
            start, end = match.span()
            # Extend to the end of the word, so "expires" is treated as one unit.
            while end < len(text) and text[end].isalnum():
                end += 1
            if not any(s <= start < e or s < end <= e for s, e in spans):
                spans.append((start, end))

    return sorted(spans)


def _rewrite_keywords(text: str, transform) -> str:
    """Apply `transform` to each trigger word, leaving the rest untouched."""
    spans = _keyword_spans(text)
    if not spans:
        return text

    out = []
    cursor = 0
    for start, end in spans:
        out.append(text[cursor:start])
        out.append(transform(text[start:end]))
        cursor = end
    out.append(text[cursor:])
    return "".join(out)


# ---------------------------------------------------------------------------
# The five attacks
# ---------------------------------------------------------------------------

def homoglyph(text: str, rate: float = 0.5, seed: int = 42) -> str:
    """Swap some Latin letters in trigger words for identical-looking ones."""
    rng = random.Random(seed)

    def swap(word: str) -> str:
        return "".join(
            HOMOGLYPHS[ch] if ch in HOMOGLYPHS and rng.random() < rate else ch
            for ch in word
        )

    return _rewrite_keywords(text, swap)


def leetspeak(text: str, rate: float = 0.6, seed: int = 42) -> str:
    """Replace letters in trigger words with lookalike digits and symbols."""
    rng = random.Random(seed)

    def swap(word: str) -> str:
        return "".join(
            LEET[ch.lower()] if ch.lower() in LEET and rng.random() < rate else ch
            for ch in word
        )

    return _rewrite_keywords(text, swap)


def split_words(text: str, visible: bool = False) -> str:
    """
    Break trigger words apart.

    With `visible=False` the separator is a zero-width space: the reader sees
    "urgent" exactly as before, while the tokeniser sees six separate letters.
    """
    separator = " " if visible else ZERO_WIDTH
    return _rewrite_keywords(text, lambda w: separator.join(w))


def dilute(text: str, copies: int = 2) -> str:
    """
    Bury the message in ordinary text.

    TF-IDF weighs terms by how much of the document they make up. Add enough
    unremarkable text and the suspicious words stop standing out, without a
    single one of them being changed.
    """
    return text + "\n" + (FILLER * copies)


def synonym_swap(text: str) -> str:
    """Say the same thing using none of the words the model was trained on."""
    out = text
    for word, replacement in sorted(SYNONYMS.items(), key=lambda kv: -len(kv[0])):
        out = re.sub(rf"\b{re.escape(word)}\b", replacement, out, flags=re.IGNORECASE)
    return out


ATTACKS = {
    "homoglyph": homoglyph,
    "leetspeak": leetspeak,
    "split words": split_words,
    "dilute text": dilute,
    "synonym swap": synonym_swap,
}
