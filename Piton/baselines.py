"""
Why Logistic Regression?

Answers the question an examiner will certainly ask, by training the obvious
alternatives on exactly the same split, the same features and the same
preprocessing, and putting the numbers side by side.

Everything is held constant except the classifier. Anything else would make the
comparison meaningless - a model that looks better because it saw an easier
split has not been shown to be better at anything.

Run:
    python baselines.py                full dataset
    python baselines.py --no-save      print only
"""

from __future__ import annotations

import csv
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
from scipy.sparse import csr_matrix, hstack
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import GroupShuffleSplit
from sklearn.naive_bayes import MultinomialNB
from sklearn.preprocessing import MinMaxScaler, StandardScaler
from sklearn.svm import LinearSVC
from sklearn.tree import DecisionTreeClassifier

from features import FEATURE_ORDER, extract_features
from preprocess import build_vectorizer, preprocess
from train import template_id

BASE = Path(__file__).resolve().parent
DATASET = "malaysia_phishing_dataset_final.csv"
TEST_SIZE = 0.25
SEED = 42


def build_models():
    """
    The alternatives a reader would expect to see, and why each is here.

    MultinomialNB is the classic text-classification baseline and the one most
    cited papers compare against. LinearSVC is the standard strong linear
    model for high-dimensional sparse text. RandomForest represents the
    non-linear family. DecisionTree is included because it is interpretable in
    a different way - if it matched the others, the simpler model would win.
    DummyClassifier is the floor: anything that cannot beat "always guess the
    majority class" has learned nothing at all.
    """
    return {
        "Logistic Regression": LogisticRegression(
            max_iter=2000, class_weight="balanced", random_state=SEED),
        "Linear SVM": LinearSVC(
            max_iter=5000, class_weight="balanced", random_state=SEED),
        "Multinomial NB": MultinomialNB(),
        "Random Forest": RandomForestClassifier(
            n_estimators=300, class_weight="balanced", random_state=SEED, n_jobs=-1),
        "Decision Tree": DecisionTreeClassifier(
            class_weight="balanced", random_state=SEED),
        "Majority baseline": DummyClassifier(strategy="most_frequent"),
    }


def main() -> None:
    save = "--no-save" not in sys.argv

    with open(BASE / DATASET, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    raw = [r["subject"] + " " + r["body"] for r in rows]
    y = np.array([int(r["label"]) for r in rows])
    groups = np.array([template_id(r) for r in rows])

    print(f"dataset   : {DATASET}  ({len(rows)} rows)")
    print(f"templates : {len(set(groups))} distinct")
    print("\npreprocessing (spaCy lemmatisation) ...")
    clean = [preprocess(t) for t in raw]

    # Whole templates are held out, not random rows. The data is template
    # generated, so a random split would put near-identical emails on both
    # sides and every model would score far too well.
    splitter = GroupShuffleSplit(n_splits=1, test_size=TEST_SIZE, random_state=SEED)
    tr, te = next(splitter.split(clean, y, groups))

    print(f"split     : {len(tr)} train / {len(te)} test")
    print(f"            {len(set(groups[tr]))} vs {len(set(groups[te]))} templates, "
          f"{len(set(groups[tr]) & set(groups[te]))} shared")

    # Vectoriser fitted on the training fold only.
    vec, Xtext_tr = build_vectorizer([clean[i] for i in tr])
    Xtext_te = vec.transform([clean[i] for i in te])

    F = np.array([[extract_features(t)[k] for k in FEATURE_ORDER] for t in raw])

    # Two scalings of the same numeric block. Naive Bayes models counts and
    # cannot accept negative values, which StandardScaler produces; MinMax
    # keeps the same information in [0, 1].
    std = StandardScaler().fit(F[tr])
    mm = MinMaxScaler().fit(F[tr])

    X = {
        "standard": (hstack([Xtext_tr, std.transform(F[tr])]).tocsr(),
                     hstack([Xtext_te, std.transform(F[te])]).tocsr()),
        "minmax": (hstack([Xtext_tr, mm.transform(F[tr])]).tocsr(),
                   hstack([Xtext_te, mm.transform(F[te])]).tocsr()),
    }

    print(f"features  : {X['standard'][0].shape[1]} "
          f"({len(vec.vocabulary_)} tf-idf + {len(FEATURE_ORDER)} structural)")
    print()

    header = f"  {'model':<22} {'accuracy':>9} {'precision':>10} {'recall':>8} {'f1':>8} {'roc-auc':>9}"
    print(header)
    print("  " + "-" * (len(header) - 2))

    results = []

    for name, model in build_models().items():
        # MultinomialNB is the only one that needs the non-negative scaling.
        Xtr, Xte = X["minmax"] if isinstance(model, MultinomialNB) else X["standard"]

        model.fit(Xtr, y[tr])
        pred = model.predict(Xte)

        acc = accuracy_score(y[te], pred)
        prec = precision_score(y[te], pred, zero_division=0)
        rec = recall_score(y[te], pred, zero_division=0)
        f1 = f1_score(y[te], pred, zero_division=0)

        # LinearSVC and DummyClassifier have no predict_proba; use the decision
        # function where there is one, and report nothing where there is not.
        try:
            if hasattr(model, "predict_proba"):
                auc = roc_auc_score(y[te], model.predict_proba(Xte)[:, 1])
            elif hasattr(model, "decision_function"):
                auc = roc_auc_score(y[te], model.decision_function(Xte))
            else:
                auc = float("nan")
        except ValueError:
            auc = float("nan")

        auc_text = "n/a" if np.isnan(auc) else f"{auc:.3f}"
        print(f"  {name:<22} {acc:>8.3f} {prec:>10.3f} {rec:>8.3f} {f1:>8.3f} {auc_text:>9}")
        results.append((name, acc, prec, rec, f1, auc))

    print()
    best = max(results, key=lambda r: r[4])
    print(f"  highest f1: {best[0]} ({best[4]:.3f})")

    ours = next(r for r in results if r[0] == "Logistic Regression")
    if best[0] != "Logistic Regression":
        print(f"  shipped model (Logistic Regression) f1 {ours[4]:.3f}, "
              f"{best[4] - ours[4]:+.3f} against the best")
    else:
        print("  the shipped model is also the best performer here")

    if save:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        out = BASE / f"results_baselines_{stamp}.csv"
        with open(out, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["model", "accuracy", "precision", "recall", "f1", "roc_auc"])
            for name, acc, prec, rec, f1, auc in results:
                w.writerow([name, f"{acc:.4f}", f"{prec:.4f}", f"{rec:.4f}",
                            f"{f1:.4f}", "" if np.isnan(auc) else f"{auc:.4f}"])
            w.writerow([])
            w.writerow(["split", "grouped by template, whole templates held out"])
            w.writerow(["test_size", TEST_SIZE])
            w.writerow(["seed", SEED])
            w.writerow(["rows", len(rows)])
            w.writerow(["templates", len(set(groups))])
            w.writerow(["generated", stamp])
        print(f"\n  saved -> {out.name}")


if __name__ == "__main__":
    main()
