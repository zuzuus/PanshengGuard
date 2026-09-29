"""
Every classifier scored 1.000 on the held-out templates. That is not a result,
it is a warning: when a decision tree matches a tuned linear model exactly,
something in the input separates the classes by construction.

This finds it. Three questions, in order:

  1. Which half is responsible - the words, or the structural features?
  2. If it is the features, which individual ones are give-aways?
  3. What does the model score once they are removed?

The same problem was already found and fixed once, for trust_score. This checks
whether it survived somewhere else.

Run:  python ablation.py
"""

from __future__ import annotations

import csv
from pathlib import Path

import numpy as np
from scipy.sparse import csr_matrix, hstack
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import GroupShuffleSplit
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier

from features import FEATURE_ORDER, extract_features
from preprocess import build_vectorizer, preprocess
from train import template_id

BASE = Path(__file__).resolve().parent
DATASET = "malaysia_phishing_dataset_final.csv"
SEED = 42


def score(Xtr, ytr, Xte, yte) -> tuple[float, float]:
    clf = LogisticRegression(max_iter=2000, class_weight="balanced", random_state=SEED)
    clf.fit(Xtr, ytr)
    pred = clf.predict(Xte)
    return accuracy_score(yte, pred), f1_score(yte, pred, zero_division=0)


def main() -> None:
    with open(BASE / DATASET, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    raw = [r["subject"] + " " + r["body"] for r in rows]
    y = np.array([int(r["label"]) for r in rows])
    groups = np.array([template_id(r) for r in rows])

    print(f"rows: {len(rows)}   templates: {len(set(groups))}")
    print("preprocessing ...")
    clean = [preprocess(t) for t in raw]

    tr, te = next(GroupShuffleSplit(n_splits=1, test_size=0.25, random_state=SEED)
                  .split(clean, y, groups))

    vec, Xtext_tr = build_vectorizer([clean[i] for i in tr])
    Xtext_te = vec.transform([clean[i] for i in te])

    F = np.array([[extract_features(t)[k] for k in FEATURE_ORDER] for t in raw])
    sc = StandardScaler().fit(F[tr])
    Ftr, Fte = sc.transform(F[tr]), sc.transform(F[te])

    # --- 1. which half carries it? ---
    print("\n=== which half separates the classes? ===")
    print(f"  {'inputs':<28} {'accuracy':>9} {'f1':>8}")
    print("  " + "-" * 47)

    for name, (a, b) in {
        "text only (tf-idf)": (Xtext_tr, Xtext_te),
        "structural features only": (csr_matrix(Ftr), csr_matrix(Fte)),
        "both": (hstack([Xtext_tr, Ftr]).tocsr(), hstack([Xtext_te, Fte]).tocsr()),
    }.items():
        acc, f1 = score(a, y[tr], b, y[te])
        print(f"  {name:<28} {acc:>8.3f} {f1:>8.3f}")

    # --- 2. individual give-aways ---
    #
    # A single feature that predicts the label on its own is not a signal the
    # model learned, it is the answer written on the input. Fitting one
    # decision stump per feature exposes them.
    print("\n=== each feature alone (a stump on one column) ===")
    print(f"  {'feature':<24} {'accuracy':>9} {'f1':>8}   {'verdict'}")
    print("  " + "-" * 62)

    suspects = []
    for i, name in enumerate(FEATURE_ORDER):
        stump = DecisionTreeClassifier(max_depth=1, random_state=SEED)
        stump.fit(F[tr][:, [i]], y[tr])
        pred = stump.predict(F[te][:, [i]])
        acc = accuracy_score(y[te], pred)
        f1 = f1_score(y[te], pred, zero_division=0)

        if acc >= 0.95:
            verdict = "GIVE-AWAY - separates on its own"
            suspects.append(name)
        elif acc >= 0.80:
            verdict = "strong"
        else:
            verdict = ""
        print(f"  {name:<24} {acc:>8.3f} {f1:>8.3f}   {verdict}")

    # --- 3. what happens without them ---
    if not suspects:
        print("\n  No single feature separates the classes on its own.")
        return

    print(f"\n=== removing {len(suspects)} give-away feature(s): {', '.join(suspects)} ===")
    keep = [i for i, n in enumerate(FEATURE_ORDER) if n not in suspects]

    acc, f1 = score(
        hstack([Xtext_tr, Ftr[:, keep]]).tocsr(), y[tr],
        hstack([Xtext_te, Fte[:, keep]]).tocsr(), y[te],
    )
    print(f"  text + remaining {len(keep)} features:   accuracy {acc:.3f}   f1 {f1:.3f}")

    acc, f1 = score(Xtext_tr, y[tr], Xtext_te, y[te])
    print(f"  text alone:                        accuracy {acc:.3f}   f1 {f1:.3f}")


if __name__ == "__main__":
    main()
