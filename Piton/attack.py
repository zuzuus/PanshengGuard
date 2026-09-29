"""
Attack our own detector and measure what survives.

Reported accuracy is measured on emails that behave themselves. This asks a
different question: how much does an attacker have to change before the
detector stops seeing it?

Run:  python attack.py [dataset.csv] [--limit N]

Nothing is modified. The model, vectoriser and scaler are loaded read-only and
every prediction goes through the exact same pipeline as /api/analyze, so the
numbers describe the deployed system rather than an approximation of it.
"""

from __future__ import annotations

import csv
import pickle
import sys
from pathlib import Path

import numpy as np
from scipy.sparse import hstack

from evasion import ATTACKS
from features import FEATURE_ORDER, extract_features
from preprocess import preprocess

# Reuse the live pre-processing rather than reimplementing it. If these ever
# diverge the experiment stops describing the real system.
from main import mask_pii, sanitize_input, strip_mail_client_chrome, THRESHOLD

BASE = Path(__file__).resolve().parent


def load_artifacts():
    with open(BASE / "model.pkl", "rb") as f:
        model = pickle.load(f)
    with open(BASE / "vectorizer.pkl", "rb") as f:
        vectorizer = pickle.load(f)
    with open(BASE / "scaler.pkl", "rb") as f:
        scaler = pickle.load(f)
    return model, vectorizer, scaler


MODEL, VECTORIZER, SCALER = load_artifacts()


def predict(raw_text: str) -> float:
    """Probability this email is phishing, exactly as the API computes it."""
    mail_text = strip_mail_client_chrome(raw_text)
    safe_input = mask_pii(sanitize_input(mail_text))
    clean_text = preprocess(safe_input)

    if not clean_text.strip():
        return 0.0

    vec_text = VECTORIZER.transform([clean_text])
    feats = extract_features(mail_text)
    vec_feats = SCALER.transform(np.array([[feats[k] for k in FEATURE_ORDER]]))
    vec = hstack([vec_text, vec_feats]).tocsr()

    return float(MODEL.predict_proba(vec)[0][1])


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dataset = args[0] if args else "malaysia_phishing_dataset_final.csv"

    limit = None
    for a in sys.argv[1:]:
        if a.startswith("--limit"):
            limit = int(a.split("=")[1]) if "=" in a else None

    with open(BASE / dataset, newline="", encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if r["label_text"] == "phishing"]

    if limit:
        rows = rows[:limit]

    print(f"dataset   : {dataset}")
    print(f"phishing  : {len(rows)} emails")
    print(f"threshold : {THRESHOLD}")
    print()
    print("Measuring the baseline (no attack) ...")

    # Only attack the ones it currently gets right. Evasion against an email
    # the detector already misses would flatter the result.
    caught = []
    for row in rows:
        text = row["subject"] + " " + row["body"]
        prob = predict(text)
        if prob >= THRESHOLD:
            caught.append((text, prob))

    baseline_rate = len(caught) / len(rows) * 100
    baseline_conf = sum(p for _, p in caught) / len(caught) * 100 if caught else 0

    print(f"  caught {len(caught)}/{len(rows)}  ({baseline_rate:.1f}%)")
    print(f"  mean confidence on those: {baseline_conf:.1f}%")
    print()
    print(f"Attacking the {len(caught)} it caught ...")
    print()
    print(f"  {'attack':<14} {'still caught':>13} {'detection':>10} {'mean conf':>10} {'drop':>8}")
    print(f"  {'-' * 14} {'-' * 13} {'-' * 10} {'-' * 10} {'-' * 8}")
    print(f"  {'(none)':<14} {len(caught):>6}/{len(caught):<6} {baseline_rate:>9.1f}% {baseline_conf:>9.1f}% {'-':>8}")

    results = {}

    for name, attack in ATTACKS.items():
        survived = 0
        confidences = []

        for text, _ in caught:
            attacked = attack(text)
            prob = predict(attacked)
            confidences.append(prob)
            if prob >= THRESHOLD:
                survived += 1

        rate = survived / len(caught) * 100
        mean_conf = sum(confidences) / len(confidences) * 100
        drop = baseline_rate - rate
        results[name] = (survived, rate, mean_conf, drop)

        print(f"  {name:<14} {survived:>6}/{len(caught):<6} {rate:>9.1f}% {mean_conf:>9.1f}% {drop:>7.1f}")

    print()
    worst = min(results.items(), key=lambda kv: kv[1][1])
    print(f"  most effective attack: {worst[0]} "
          f"({worst[1][1]:.1f}% still caught, a {worst[1][3]:.1f} point drop)")


if __name__ == "__main__":
    main()
