"""
Second round: attack the parts the first round left alone.

The text-only attacks barely dented detection, which suggests the structural
feature block - not the wording - is doing the work. This tests that directly
by peeling the model apart one layer at a time:

  1. text only        mangle the wording, leave the links alone   (round one)
  2. links only       clean the links, leave the wording alone
  3. both             an attacker who does the obvious thing
  4. white box        also mangle the highest-weighted TF-IDF terms, which an
                      attacker who had obtained the model could read off it

If detection only collapses once the links are cleaned, then the honest claim
is that the detector rests on link structure rather than on language - worth
knowing, and worth saying out loud in the write-up.

Run:  python attack_whitebox.py [--limit=N]
"""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

import numpy as np

from attack import MODEL, VECTORIZER, predict
from evasion import homoglyph, leetspeak, split_words, synonym_swap, _rewrite_keywords
from main import THRESHOLD

BASE = Path(__file__).resolve().parent

# A domain the whitelist recognises, used to replace the lookalike ones. This
# is the single cheapest move available to an attacker: host the page
# somewhere that does not look wrong.
CLEAN_URL = "https://www.maybank2u.com.my/account/notice"

_URL_RE = re.compile(r"https?://[^\s'\"<>()\[\]\\]+")


def clean_links(text: str) -> str:
    """Swap every URL for one on a domain the system trusts."""
    return _URL_RE.sub(CLEAN_URL, text)


def top_model_terms(n: int = 60) -> list[str]:
    """
    The words the classifier leans on hardest towards 'phishing'.

    Reading these off the model is a white-box move: it assumes the attacker
    has the model file. That is a fair assumption for anything shipped to a
    browser extension or an app, and it is the standard strong-attacker
    assumption in security work.
    """
    names = VECTORIZER.get_feature_names_out()
    # The feature vector is [TF-IDF block | structural block]; only the TF-IDF
    # half has names.
    coefs = MODEL.coef_[0][: len(names)]
    order = np.argsort(coefs)[::-1][:n]
    # Keep single words - multi-word n-grams are handled by attacking each part.
    return [names[i] for i in order if " " not in names[i]]


TOP_TERMS = top_model_terms()


def mangle_model_terms(text: str) -> str:
    """Homoglyph the terms the model actually weighs most, not just keywords."""
    out = text
    for term in TOP_TERMS:
        out = re.sub(
            rf"\b{re.escape(term)}",
            lambda m: homoglyph(m.group(0) + " ", rate=0.7).rstrip(),
            out,
            flags=re.IGNORECASE,
        )
    return out


def text_only(text: str) -> str:
    return leetspeak(homoglyph(text))


def both(text: str) -> str:
    return clean_links(text_only(text))


def white_box(text: str) -> str:
    return clean_links(mangle_model_terms(synonym_swap(text)))


ROUNDS = {
    "1. text only": text_only,
    "2. links only": clean_links,
    "3. text + links": both,
    "4. white box": white_box,
}


def main():
    limit = None
    for a in sys.argv[1:]:
        if a.startswith("--limit") and "=" in a:
            limit = int(a.split("=")[1])

    with open(BASE / "malaysia_phishing_dataset_final.csv", newline="", encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if r["label_text"] == "phishing"]
    if limit:
        rows = rows[:limit]

    print(f"phishing emails : {len(rows)}")
    print(f"threshold       : {THRESHOLD}")
    print(f"top model terms : {len(TOP_TERMS)} (e.g. {', '.join(TOP_TERMS[:8])})")
    print()

    caught = []
    for row in rows:
        text = row["subject"] + " " + row["body"]
        if predict(text) >= THRESHOLD:
            caught.append(text)

    base_rate = len(caught) / len(rows) * 100
    print(f"baseline: {len(caught)}/{len(rows)} caught ({base_rate:.1f}%)")
    print()
    print(f"  {'round':<18} {'still caught':>13} {'detection':>10} {'mean conf':>10} {'drop':>8}")
    print(f"  {'-' * 18} {'-' * 13} {'-' * 10} {'-' * 10} {'-' * 8}")

    for name, attack in ROUNDS.items():
        survived = 0
        confs = []
        for text in caught:
            prob = predict(attack(text))
            confs.append(prob)
            if prob >= THRESHOLD:
                survived += 1

        rate = survived / len(caught) * 100
        mean_conf = sum(confs) / len(confs) * 100
        print(f"  {name:<18} {survived:>6}/{len(caught):<6} {rate:>9.1f}% "
              f"{mean_conf:>9.1f}% {base_rate - rate:>7.1f}")


if __name__ == "__main__":
    main()
