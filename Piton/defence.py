"""
Undo the obfuscations before the model reads anything.

Each function here reverses one of the attacks in evasion.py. They run on the
incoming text, so the classifier sees a cleaned-up version even when the sender
mangled it.

Design rule throughout: a defence that damages ordinary mail is worse than the
attack it prevents. Every rule below is deliberately conservative and refuses to
act when it is not confident - an unchanged message is always an acceptable
outcome, a corrupted one is not.
"""

from __future__ import annotations

import re
import unicodedata

# ---------------------------------------------------------------------------
# 1. Homoglyphs
# ---------------------------------------------------------------------------
# The reverse of evasion.HOMOGLYPHS, plus a few more lookalikes attackers use.
# Folding these is safe: none of them belong in an English or Malay message, so
# rewriting them cannot damage legitimate text.
HOMOGLYPH_FOLD = {
    # Cyrillic
    "а": "a", "с": "c", "е": "e", "і": "i", "ј": "j",
    "о": "o", "р": "p", "ѕ": "s", "х": "x", "у": "y",
    "А": "A", "С": "C", "Е": "E", "І": "I", "Ј": "J",
    "О": "O", "Р": "P", "Ѕ": "S", "Х": "X", "У": "Y",
    "в": "b", "н": "h", "м": "m", "т": "t",
    # Greek
    "α": "a", "ο": "o", "ρ": "p", "υ": "u", "ν": "v",
    "Α": "A", "Β": "B", "Ε": "E", "Η": "H", "Ι": "I",
    "Κ": "K", "Μ": "M", "Ν": "N", "Ο": "O", "Ρ": "P",
    "Τ": "T", "Χ": "X",
}

# Characters with no visual presence at all. Their only purpose in a message is
# to break a word apart without the reader noticing.
INVISIBLE = "".join([
    "​",  # zero width space
    "‌",  # zero width non-joiner
    "‍",  # zero width joiner
    "⁠",  # word joiner
    "﻿",  # zero width no-break space
    "­",  # soft hyphen
])

_INVISIBLE_RE = re.compile(f"[{re.escape(INVISIBLE)}]")

# ---------------------------------------------------------------------------
# 2. Character substitution
# ---------------------------------------------------------------------------
# Only the unambiguous direction is listed. "1" could stand for either i or l;
# the commoner reading is used, and the guard in `unleet` throws the result away
# unless it produces a plain word.
LEET_FOLD = {
    "@": "a", "4": "a", "3": "e", "1": "i", "!": "i",
    "0": "o", "5": "s", "$": "s", "7": "t",
}

_LEET_CHARS = set(LEET_FOLD)


def fold_homoglyphs(text: str) -> str:
    """
    Replace lookalike characters with their Latin equivalents.

    NFKC first, which collapses the compatibility forms (fullwidth letters,
    ligatures, circled characters), then the explicit table for the Cyrillic and
    Greek letters NFKC deliberately leaves alone - those are real letters in
    their own scripts, so Unicode will not touch them.
    """
    text = unicodedata.normalize("NFKC", text)
    return "".join(HOMOGLYPH_FOLD.get(ch, ch) for ch in text)


def strip_invisible(text: str) -> str:
    """Remove characters that take up no space and carry no meaning."""
    return _INVISIBLE_RE.sub("", text)


def rejoin_split_words(text: str) -> str:
    """
    Put back together words that were broken with spaces: "u r g e n t".

    Only runs of four or more single characters are joined. Three would catch
    ordinary text - "a b c" in a list, initials, "I am o k" - and the cost of
    mangling real sentences is higher than the cost of missing a short split.
    """
    def join(match: re.Match) -> str:
        return match.group(0).replace(" ", "")

    return re.sub(r"\b(?:[A-Za-z] ){3,}[A-Za-z]\b", join, text)


def unleet(text: str) -> str:
    """
    Turn "v3r1fy" back into "verify", without touching "RM1,200.00".

    A token is only rewritten when it already contains letters, contains at
    least one substituted character, and comes out purely alphabetic. That last
    condition is what protects amounts, reference codes and dates: "24" has no
    letters, "RM1,200.00" keeps its punctuation, and both are left exactly as
    they were.
    """
    def fix(token: str) -> str:
        if not any(ch.isalpha() for ch in token):
            return token
        if not any(ch in _LEET_CHARS for ch in token):
            return token

        candidate = "".join(LEET_FOLD.get(ch, ch) for ch in token)
        return candidate if candidate.isalpha() else token

    return re.sub(r"\S+", lambda m: fix(m.group(0)), text)


def normalise(text: str) -> str:
    """
    The full defence, in the order the attacks have to be undone.

    Invisible characters go first, so that a word split with zero-width spaces
    is whole again before anything tries to read it. Homoglyphs next, because
    the leet check needs to know which characters are really letters. The
    space-rejoin runs last, once the rest is settled.
    """
    text = strip_invisible(text)
    text = fold_homoglyphs(text)
    text = rejoin_split_words(text)
    text = unleet(text)
    return text


if __name__ == "__main__":
    samples = [
        ("homoglyph", "Your ассount has been susреndеd"),
        ("leetspeak", "Please v3r1fy your @cc0unt n0w"),
        ("zero width", "U​R​G​E​N​T: act now"),
        ("space split", "This is u r g e n t business"),
        ("must not break", "Invoice RM1,200.00 due on 24 Sep 2026, ref A7X93K2P"),
        ("must not break", "Contact us at 03-7890 1234 or visit maybank2u.com.my"),
    ]

    print(f"{'case':<16} {'before':<46} after")
    print("-" * 110)
    for name, text in samples:
        print(f"{name:<16} {text!r:<46} {normalise(text)!r}")
