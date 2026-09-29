"""
The full red-team experiment: attack, defend, measure both.

Produces the before/after table for the results chapter, and writes it to CSV
so the numbers can be quoted rather than retyped off a screen.

Run:
    python experiment.py                 full dataset
    python experiment.py --limit=100     quick pass while developing
    python experiment.py --no-save       print only

Three things are measured, not one:

  detection on attacked phishing   does the attack get through?
  detection after the defence      does the defence bring it back?
  false alarms on legitimate mail  does the defence break ordinary email?

That third column is the one people forget. A defence that fixes evasion by
flagging everything is not a defence, and without measuring it there is no way
to tell the difference.
"""

from __future__ import annotations

import csv
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
from scipy.sparse import hstack

from attack import MODEL, SCALER, VECTORIZER
from attack_whitebox import clean_links
from defence import normalise
from evasion import ATTACKS
from features import FEATURE_ORDER, extract_features
from main import THRESHOLD, mask_pii, sanitize_input, strip_mail_client_chrome
from preprocess import preprocess

BASE = Path(__file__).resolve().parent
DATASET = "malaysia_phishing_dataset_final.csv"


def predict(raw_text: str, defend: bool = False) -> float:
    """Phishing probability, optionally with the normalisation layer in front."""
    if defend:
        raw_text = normalise(raw_text)

    mail_text = strip_mail_client_chrome(raw_text)
    clean_text = preprocess(mask_pii(sanitize_input(mail_text)))

    if not clean_text.strip():
        return 0.0

    vec_text = VECTORIZER.transform([clean_text])
    feats = extract_features(mail_text)
    vec_feats = SCALER.transform(np.array([[feats[k] for k in FEATURE_ORDER]]))

    return float(MODEL.predict_proba(hstack([vec_text, vec_feats]).tocsr())[0][1])


def combined(text: str) -> str:
    """Mangle the wording and clean the link - the strongest attack found."""
    return clean_links(ATTACKS["leetspeak"](ATTACKS["homoglyph"](text)))


def rate(texts, defend: bool) -> float:
    """Percentage flagged as phishing."""
    if not texts:
        return 0.0
    hits = sum(1 for t in texts if predict(t, defend) >= THRESHOLD)
    return hits / len(texts) * 100


def main() -> None:
    limit = None
    save = "--no-save" not in sys.argv
    for arg in sys.argv[1:]:
        if arg.startswith("--limit") and "=" in arg:
            limit = int(arg.split("=")[1])

    with open(BASE / DATASET, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    phishing = [r["subject"] + " " + r["body"] for r in rows if r["label_text"] == "phishing"]
    legit = [r["subject"] + " " + r["body"] for r in rows if r["label_text"] == "legitimate"]

    if limit:
        phishing, legit = phishing[:limit], legit[:limit]

    print(f"dataset   : {DATASET}")
    print(f"phishing  : {len(phishing)}   legitimate: {len(legit)}")
    print(f"threshold : {THRESHOLD}")
    print()

    # Attack only what the detector currently gets right - evading something it
    # already misses would flatter the numbers.
    caught = [t for t in phishing if predict(t) >= THRESHOLD]
    base = len(caught) / len(phishing) * 100
    print(f"baseline  : {len(caught)}/{len(phishing)} caught ({base:.1f}%)")
    print()

    scenarios = [("no attack", lambda t: t)]
    scenarios += [(name, fn) for name, fn in ATTACKS.items()]
    scenarios += [("links cleaned", clean_links), ("text + links", combined)]

    header = f"  {'scenario':<16} {'attacked':>9} {'defended':>9} {'recovered':>10}"
    print(header)
    print("  " + "-" * (len(header) - 2))

    results = []
    for name, attack in scenarios:
        variants = [attack(t) for t in caught]
        without = rate(variants, defend=False)
        with_def = rate(variants, defend=True)
        results.append((name, without, with_def, with_def - without))
        print(f"  {name:<16} {without:>8.1f}% {with_def:>8.1f}% {with_def - without:>9.1f}")

    # --- the control: does the defence start flagging ordinary mail? ---
    print()
    fp_before = rate(legit, defend=False)
    fp_after = rate(legit, defend=True)
    print(f"  false alarms on {len(legit)} legitimate emails:")
    print(f"    without defence : {fp_before:.1f}%")
    print(f"    with defence    : {fp_after:.1f}%   (change {fp_after - fp_before:+.1f})")

    if save:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        out = BASE / f"results_attack_defence_{stamp}.csv"
        with open(out, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["scenario", "detection_attacked_pct", "detection_defended_pct", "recovered_pts"])
            for row in results:
                w.writerow([row[0], f"{row[1]:.1f}", f"{row[2]:.1f}", f"{row[3]:.1f}"])
            w.writerow([])
            w.writerow(["false_alarm_legitimate_without_defence_pct", f"{fp_before:.1f}"])
            w.writerow(["false_alarm_legitimate_with_defence_pct", f"{fp_after:.1f}"])
            w.writerow(["phishing_emails", len(phishing)])
            w.writerow(["legitimate_emails", len(legit)])
            w.writerow(["threshold", THRESHOLD])
            w.writerow(["generated", stamp])
        print(f"\n  saved -> {out.name}")


if __name__ == "__main__":
    main()
