"""
Every classifier scores 1.000 on the clean test set, so accuracy cannot tell
them apart. This asks whether they differ where it matters: under attack.

Same models, same split, same features as baselines.py. The only change is that
the test set is obfuscated before it is scored.

If the models separate here, the argument writes itself: on a saturated
benchmark, adversarial robustness is not an optional extra - it is the only
measurement left that distinguishes anything.

Run:  python baselines_attacked.py [--no-save]
"""

from __future__ import annotations

import csv
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
from scipy.sparse import hstack
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score, recall_score
from sklearn.model_selection import GroupShuffleSplit
from sklearn.naive_bayes import MultinomialNB
from sklearn.preprocessing import MinMaxScaler, StandardScaler
from sklearn.svm import LinearSVC
from sklearn.tree import DecisionTreeClassifier

from attack_whitebox import clean_links
from defence import normalise
from evasion import homoglyph, leetspeak
from features import FEATURE_ORDER, extract_features
from preprocess import build_vectorizer, preprocess
from train import template_id

BASE = Path(__file__).resolve().parent
DATASET = "malaysia_phishing_dataset_final.csv"
SEED = 42


def attacked(text: str) -> str:
    """The strongest attack found: mangled wording plus a clean-looking link."""
    return clean_links(leetspeak(homoglyph(text)))


def models():
    return {
        "Logistic Regression": LogisticRegression(
            max_iter=2000, class_weight="balanced", random_state=SEED),
        "Linear SVM": LinearSVC(max_iter=5000, class_weight="balanced", random_state=SEED),
        "Multinomial NB": MultinomialNB(),
        "Random Forest": RandomForestClassifier(
            n_estimators=300, class_weight="balanced", random_state=SEED, n_jobs=-1),
        "Decision Tree": DecisionTreeClassifier(class_weight="balanced", random_state=SEED),
    }


def main() -> None:
    save = "--no-save" not in sys.argv

    with open(BASE / DATASET, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    raw = [r["subject"] + " " + r["body"] for r in rows]
    y = np.array([int(r["label"]) for r in rows])
    groups = np.array([template_id(r) for r in rows])

    tr, te = next(GroupShuffleSplit(n_splits=1, test_size=0.25, random_state=SEED)
                  .split(raw, y, groups))

    print(f"rows {len(rows)}   train {len(tr)}   test {len(te)}")
    print("preprocessing three versions of the test set ...")

    clean_tr = [preprocess(raw[i]) for i in tr]

    # Three views of the same held-out emails.
    te_plain = [raw[i] for i in te]
    te_attacked = [attacked(t) for t in te_plain]
    te_defended = [normalise(t) for t in te_attacked]

    vec, Xtext_tr = build_vectorizer(clean_tr)
    Ftr_raw = np.array([[extract_features(raw[i])[k] for k in FEATURE_ORDER] for i in tr])
    std = StandardScaler().fit(Ftr_raw)
    mm = MinMaxScaler().fit(Ftr_raw)

    def build(texts, scaler):
        Xt = vec.transform([preprocess(t) for t in texts])
        F = np.array([[extract_features(t)[k] for k in FEATURE_ORDER] for t in texts])
        return hstack([Xt, scaler.transform(F)]).tocsr()

    views = {}
    for scaler_name, scaler in (("standard", std), ("minmax", mm)):
        views[scaler_name] = {
            "train": hstack([Xtext_tr, scaler.transform(Ftr_raw)]).tocsr(),
            "plain": build(te_plain, scaler),
            "attacked": build(te_attacked, scaler),
            "defended": build(te_defended, scaler),
        }

    yte = y[te]

    header = (f"  {'model':<22} {'clean f1':>9} {'attacked':>9} {'defended':>9} "
              f"{'lost':>7} {'regained':>9}")
    print()
    print(header)
    print("  " + "-" * (len(header) - 2))

    results = []
    for name, model in models().items():
        v = views["minmax" if isinstance(model, MultinomialNB) else "standard"]

        model.fit(v["train"], y[tr])

        f1_plain = f1_score(yte, model.predict(v["plain"]), zero_division=0)
        f1_att = f1_score(yte, model.predict(v["attacked"]), zero_division=0)
        f1_def = f1_score(yte, model.predict(v["defended"]), zero_division=0)

        print(f"  {name:<22} {f1_plain:>9.3f} {f1_att:>9.3f} {f1_def:>9.3f} "
              f"{f1_att - f1_plain:>7.3f} {f1_def - f1_att:>9.3f}")
        results.append((name, f1_plain, f1_att, f1_def))

    print()
    spread_clean = max(r[1] for r in results) - min(r[1] for r in results)
    spread_att = max(r[2] for r in results) - min(r[2] for r in results)
    print(f"  spread between models, clean test set : {spread_clean:.3f}")
    print(f"  spread between models, under attack   : {spread_att:.3f}")

    if spread_att > spread_clean:
        print("\n  The clean benchmark cannot separate these models. The attacked one can.")

    if save:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        out = BASE / f"results_baselines_attacked_{stamp}.csv"
        with open(out, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["model", "f1_clean", "f1_attacked", "f1_defended",
                        "lost_to_attack", "regained_by_defence"])
            for name, p, a, d in results:
                w.writerow([name, f"{p:.4f}", f"{a:.4f}", f"{d:.4f}",
                            f"{a - p:.4f}", f"{d - a:.4f}"])
            w.writerow([])
            w.writerow(["spread_clean", f"{spread_clean:.4f}"])
            w.writerow(["spread_attacked", f"{spread_att:.4f}"])
            w.writerow(["generated", stamp])
        print(f"\n  saved -> {out.name}")


if __name__ == "__main__":
    main()
