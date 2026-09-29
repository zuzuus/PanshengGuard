import spacy
import nltk
from nltk.corpus import stopwords
from sklearn.feature_extraction.text import TfidfVectorizer

nltk.download('stopwords', quiet=True)

# Load once at module level — avoids reloading on every call
try:
    nlp = spacy.load('en_core_web_sm', disable=['parser', 'ner'])  # faster: only need tagger/lemmatizer
except OSError:
    raise OSError(
        "spaCy model not found. Run: python -m spacy download en_core_web_sm"
    )

NLTK_STOPWORDS = set(stopwords.words('english'))


def preprocess(text: str) -> str:
    """
    Clean and normalise raw email text:
      1. Lowercase
      2. Tokenise via spaCy
      3. Remove stopwords (spaCy + NLTK), punctuation, non-alpha tokens, very short tokens
      4. Lemmatise
    Returns a single cleaned string ready for TF-IDF.
    """
    if not isinstance(text, str) or not text.strip():
        return ""

    doc = nlp(text.lower())

    tokens = [
        token.lemma_
        for token in doc
        if (
            not token.is_stop
            and token.lemma_ not in NLTK_STOPWORDS
            and not token.is_punct
            and token.is_alpha
            and len(token.text) > 2          # drop single/double char noise
        )
    ]

    return ' '.join(tokens)
 
 
def build_vectorizer(texts, max_features: int = 5000):
    """
    Fit a TF-IDF vectoriser on a list of pre-cleaned texts.
    Returns (fitted_vectorizer, sparse_matrix).
    """
    vectorizer = TfidfVectorizer(
        max_features=max_features,
        ngram_range=(1, 2),      # unigrams + bigrams catch "last chance", "act now" etc.
        sublinear_tf=True,       # apply log(tf) to dampen high-frequency term dominance
        min_df=2,                # ignore terms that appear in fewer than 2 docs
    )
    X = vectorizer.fit_transform(texts)
    return vectorizer, X
