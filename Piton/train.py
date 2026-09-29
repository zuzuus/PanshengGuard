"""
Train the phishing classifier on malaysia_phishing_dataset_final.csv.

The model sees two blocks of input, in this exact order:

    hstack([ TF-IDF(cleaned text) , scaled numeric features ])

main.py builds the identical vector at request time by importing the same
features.py, so the two cannot drift. Three artefacts are written and all three
must be loaded together: vectorizer.pkl, scaler.pkl, model.pkl.

Three things this script reports that a plain accuracy number would hide:

  1. A rule baseline. The engineered features are strong enough that a
     hand-written if-statement already separates this corpus almost perfectly.
     If the ML model cannot beat that, the honest conclusion is that the
     features are doing the work, not the learning - and that belongs in the
     report rather than being quietly omitted.

  2. A grouped split. The data is template-generated, so a random split puts
     near-identical mail on both sides and reports memorisation as skill. Whole
     templates are held out instead.

  3. A feature ablation, so it is visible how much the text and the numeric
     features each contribute on their own.

Usage:  python train.py [dataset.csv]
"""

import csv
import json
import pickle
import re
import shutil
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from scipy.sparse import hstack, csr_matrix
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, classification_report,
                             confusion_matrix, f1_score, recall_score, roc_auc_score)
from sklearn.model_selection import (GroupShuffleSplit, StratifiedGroupKFold,
                                     cross_val_score)
from sklearn.preprocessing import StandardScaler

from features import FEATURE_ORDER
from preprocess import preprocess, build_vectorizer

DATASET = sys.argv[1] if len(sys.argv) > 1 else "malaysia_phishing_dataset_final.csv"
TEST_SIZE = 0.25
SEED = 42

# Flags that never fire on legitimate mail in this corpus. Used only for the
# baseline comparison below, never as a shortcut inside the model.
HARD_FLAGS = ["link_has_ip", "link_is_shortener", "link_suspicious_tld",
              "link_brand_typosquat", "has_threat", "asks_credentials",
              "has_reward_money", "generic_greeting"]


def template_id(row):
    t = row["subject"] + " " + row["body"]
    t = re.sub(r"\d+", "", t)
    t = re.sub(r"\b[A-Z0-9]{6,}\b", "", t)
    t = re.sub(r"(Dear|Hi|Kepada|Tuan/Puan|Hello|Attention)[^,\n]*,", "", t)
    t = re.sub(r"https?://\S+", "", t)
    return re.sub(r"\s+", " ", t).strip().lower()[:160]


def rule_baseline(rows, y):
    """Any hard flag fired, or the link domain contains a hyphen."""
    pred = np.array([
        int(any(r[f] == "1" for f in HARD_FLAGS) or float(r["link_num_hyphens"]) > 0)
        for r in rows
    ])
    cm = confusion_matrix(y, pred)
    print("rule baseline (no machine learning at all):")
    print(f"  accuracy {accuracy_score(y, pred):.3f}   f1 {f1_score(y, pred):.3f}"
          f"   FP {cm[0][1]}   FN {cm[1][0]}")
    return accuracy_score(y, pred)


def evaluate(name, Xtr, ytr, Xte, yte):
    clf = LogisticRegression(max_iter=3000, class_weight="balanced", random_state=SEED)
    clf.fit(Xtr, ytr)
    pred = clf.predict(Xte)
    try:
        auc = roc_auc_score(yte, clf.predict_proba(Xte)[:, 1])
    except ValueError:
        auc = float("nan")
    print(f"  {name:26} accuracy {accuracy_score(yte, pred):.3f}   roc-auc {auc:.3f}")
    return clf


def main():
    with open(DATASET, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    print(f"dataset: {DATASET}")
    print(f"  rows   : {len(rows)}")
    print(f"  classes: {dict(Counter(r['label_text'] for r in rows))}")

    y = np.array([int(r["label"]) for r in rows])
    groups = np.array([template_id(r) for r in rows])
    print(f"  templates: {len(set(groups))}")

    print()
    rule_acc = rule_baseline(rows, y)

    raw = [r["subject"] + " " + r["body"] for r in rows]
    print("\npreprocessing (spaCy lemmatisation, takes a minute) ...")
    clean = [preprocess(t) for t in raw]
    print(f"  {sum(1 for c in clean if c.strip())}/{len(clean)} rows produced usable text")

    # numeric block, read straight from the CSV that features.py generated
    F = np.array([[float(r[k]) for k in FEATURE_ORDER] for r in rows])

    splitter = GroupShuffleSplit(n_splits=1, test_size=TEST_SIZE, random_state=SEED)
    tr, te = next(splitter.split(clean, y, groups))
    print(f"\nsplit grouped by template: {len(tr)} train / {len(te)} test")
    print(f"  overlap between the two: {len(set(groups[tr]) & set(groups[te]))} templates")

    vec, Xtext_tr = build_vectorizer([clean[i] for i in tr])
    Xtext_te = vec.transform([clean[i] for i in te])
    print(f"  tf-idf vocabulary: {len(vec.vocabulary_)} terms")

    scaler = StandardScaler().fit(F[tr])
    Ftr, Fte = scaler.transform(F[tr]), scaler.transform(F[te])

    print("\nfeature ablation:")
    evaluate("text only", Xtext_tr, y[tr], Xtext_te, y[te])
    evaluate("numeric features only", csr_matrix(Ftr), y[tr], csr_matrix(Fte), y[te])
    Xtr = hstack([Xtext_tr, Ftr]).tocsr()
    Xte = hstack([Xtext_te, Fte]).tocsr()
    clf = evaluate("text + features (shipped)", Xtr, y[tr], Xte, y[te])

    probs = clf.predict_proba(Xte)[:, 1]
    pred = (probs >= 0.5).astype(int)
    print("\n" + "=" * 64)
    print("SHIPPED MODEL - held-out templates")
    print("=" * 64)
    print(classification_report(y[te], pred, target_names=["legitimate", "phishing"],
                                digits=3))
    cm = confusion_matrix(y[te], pred)
    print("confusion matrix")
    print("                 pred legit  pred phish")
    print(f"  true legit   {cm[0][0]:10} {cm[0][1]:11}")
    print(f"  true phish   {cm[1][0]:10} {cm[1][1]:11}")
    print(f"\n  vs rule baseline: {accuracy_score(y[te], pred):.3f} model"
          f"  /  {rule_acc:.3f} rules")

    print("\ncross-validation (5-fold, stratified + grouped):")
    Xall = hstack([vec.transform(clean), scaler.transform(F)]).tocsr()
    cv = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=SEED)
    scores = cross_val_score(
        LogisticRegression(max_iter=3000, class_weight="balanced", random_state=SEED),
        Xall, y, groups=groups, cv=cv, scoring="f1")
    print(f"  f1 per fold: {np.round(scores, 3).tolist()}")
    print(f"  mean f1    : {scores.mean():.3f} (+/- {scores.std():.3f})")

    # --- refit on everything and save ---
    print("\nrefitting on the full dataset ...")
    vec_f, Xtext_all = build_vectorizer(clean)
    scaler_f = StandardScaler().fit(F)
    Xfinal = hstack([Xtext_all, scaler_f.transform(F)]).tocsr()
    final = LogisticRegression(max_iter=3000, class_weight="balanced", random_state=SEED)
    final.fit(Xfinal, y)

    for name in ("model.pkl", "vectorizer.pkl", "scaler.pkl"):
        if Path(name).exists():
            shutil.copy2(name, name + ".bak")

    with open("model.pkl", "wb") as f:
        pickle.dump(final, f)
    with open("vectorizer.pkl", "wb") as f:
        pickle.dump(vec_f, f)
    with open("scaler.pkl", "wb") as f:
        pickle.dump(scaler_f, f)
    with open("threshold.json", "w", encoding="utf-8") as f:
        json.dump({"threshold": 0.5, "dataset": DATASET,
                   "n_text_features": Xtext_all.shape[1],
                   "feature_order": FEATURE_ORDER}, f, indent=2)
    print(f"  saved model.pkl / vectorizer.pkl / scaler.pkl")
    print(f"  {Xfinal.shape[1]} features = {Xtext_all.shape[1]} tf-idf"
          f" + {len(FEATURE_ORDER)} engineered")

    names = list(vec_f.get_feature_names_out()) + FEATURE_ORDER
    coefs = final.coef_[0]
    order = np.argsort(coefs)
    print("\ntop phishing indicators:")
    for i in order[-14:][::-1]:
        tag = "  [feature]" if i >= len(vec_f.vocabulary_) else ""
        print(f"  {coefs[i]:+.3f}  {names[i]}{tag}")
    print("\ntop legitimate indicators:")
    for i in order[:14]:
        tag = "  [feature]" if i >= len(vec_f.vocabulary_) else ""
        print(f"  {coefs[i]:+.3f}  {names[i]}{tag}")


if __name__ == "__main__":
    main()
