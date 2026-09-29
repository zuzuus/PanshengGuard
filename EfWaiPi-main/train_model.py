import pandas as pd
import pickle
import numpy as np

from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import MultinomialNB
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score

from scipy.sparse import hstack

from preprocess import preprocess, build_vectorizer

# ---------------------------------
# TRUSTED DOMAINS (soft signal only)
# ---------------------------------

TRUSTED_DOMAINS = [
    "google.com",
    "microsoft.com",
    "apple.com",
    "github.com",
    "amazon.com"
]

def trust_score(sender: str) -> float:
    sender = str(sender).lower()

    for domain in TRUSTED_DOMAINS:
        if domain in sender:
            return 0.9   # high trust, NOT absolute

    return 0.3  # unknown domain baseline


# ---------------------------------
# LOAD DATASETS
# ---------------------------------

df = pd.read_csv("data/phishing_dataset_final.csv")

required = ["subject", "body", "label"]

df = df[required]
df = df.dropna(subset=required)
df = df.sample(frac=1, random_state=42).reset_index(drop=True)

print("Total rows:", len(df))
print(df["label"].value_counts())


# ---------------------------------
# SOFT LABEL NOISE (REALISM INJECTION)
# ---------------------------------

np.random.seed(42)

for i in range(len(df)):

    sender = str(df.loc[i, "subject"]).lower() + " " + str(df.loc[i, "body"]).lower()
    label = df.loc[i, "label"]

    is_trusted = any(domain in sender for domain in TRUSTED_DOMAINS)

    # trusted emails can still be phishing (rare compromise cases)
    if is_trusted and label == 1:
        if np.random.rand() < 0.4:
            df.loc[i, "label"] = 0

    # unknown domains can still be legit emails
    if (not is_trusted) and label == 0:
        if np.random.rand() < 0.2:
            df.loc[i, "label"] = 1


# ---------------------------------
# COMBINE TEXT
# ---------------------------------

df["text_combined"] = (
    df["subject"].fillna("") + " " +
    df["body"].fillna("")
)


# ---------------------------------
# PREPROCESS
# ---------------------------------

print("Preprocessing...")

df["clean"] = df["text_combined"].apply(preprocess)


# ---------------------------------
# TRUST FEATURE
# ---------------------------------

df["trust_score"] = df["subject"].fillna("") + " " + df["body"].fillna("")
df["trust_score"] = df["trust_score"].apply(trust_score)


# ---------------------------------
# VECTORIZE TEXT
# ---------------------------------

vectorizer, X_text = build_vectorizer(df["clean"])
y = df["label"].values


# ---------------------------------
# COMBINE FEATURES (TEXT + TRUST)
# ---------------------------------

X_trust = df["trust_score"].values.reshape(-1, 1)
X = hstack([X_text, X_trust])


# ---------------------------------
# TRAIN / TEST SPLIT
# ---------------------------------

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=42,
    stratify=y
)


# ---------------------------------
# MODELS
# ---------------------------------

models = {
    "Logistic Regression": LogisticRegression(max_iter=1000),
    "Naive Bayes": MultinomialNB(),
    "Random Forest": RandomForestClassifier(
        n_estimators=100,
        random_state=42,
        n_jobs=-1
    )
}


best_model = None
best_acc = 0
best_name = ""


# ---------------------------------
# TRAINING LOOP
# ---------------------------------

for name, model in models.items():
    print(f"\nTraining {name}...")

    model.fit(X_train, y_train)
    preds = model.predict(X_test)

    acc = accuracy_score(y_test, preds)

    print(f"{name}: {acc:.4f}")
    print(classification_report(y_test, preds))

    if acc > best_acc:
        best_acc = acc
        best_model = model
        best_name = name


# ---------------------------------
# SAVE MODEL
# ---------------------------------

pickle.dump(best_model, open("model.pkl", "wb"))
pickle.dump(vectorizer, open("vectorizer.pkl", "wb"))

print("\nBest model:", best_name)
print("Accuracy:", best_acc)
