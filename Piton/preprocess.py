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

# Function words only: pronouns, prepositions, conjunctions, particles and
# auxiliaries. Semantically loaded words a phishing email actually leans on
# (segera, sahkan, bayaran, akaun, baki, tertunggak, amaran) are deliberately
# NOT here - those are the signal we want to keep.
MALAY_STOPWORDS = {
    # pronouns / determiners
    'anda', 'awak', 'saya', 'aku', 'kami', 'kita', 'mereka', 'dia', 'beliau',
    'ia', 'ianya', 'nya', 'ini', 'itu', 'tersebut', 'sendiri', 'masing',
    # prepositions
    'di', 'ke', 'dari', 'daripada', 'kepada', 'pada', 'dalam', 'untuk', 'bagi',
    'oleh', 'dengan', 'atas', 'bawah', 'antara', 'terhadap', 'tentang',
    'mengenai', 'melalui', 'sejak', 'hingga', 'sehingga', 'selepas', 'sebelum',
    # conjunctions
    'dan', 'atau', 'tetapi', 'tapi', 'kerana', 'sebab', 'jika', 'kalau',
    'jikalau', 'supaya', 'agar', 'walaupun', 'namun', 'manakala', 'serta',
    'apabila', 'bila', 'ketika', 'semasa', 'lalu', 'maka', 'sambil',
    # auxiliaries / aspect markers
    'adalah', 'ialah', 'iaitu', 'akan', 'telah', 'sudah', 'sedang', 'masih',
    'belum', 'pernah', 'boleh', 'dapat', 'mesti', 'perlu', 'harus', 'ada',
    'adanya', 'merupakan', 'mempunyai',
    # particles / quantifiers / fillers
    'yang', 'juga', 'pula', 'pun', 'saja', 'sahaja', 'lagi', 'lain', 'semua',
    'setiap', 'para', 'banyak', 'beberapa', 'segala', 'seperti', 'macam',
    'begitu', 'sangat', 'amat', 'paling', 'lebih', 'kurang', 'cuma', 'hanya',
    'tidak', 'bukan', 'tiada', 'tanpa', 'sila', 'kepada', 'berikut', 'bahawa',
    'sini', 'situ', 'mana', 'apa', 'siapa', 'bagaimana', 'kini', 'kemudian',
}

STOPWORDS = NLTK_STOPWORDS | MALAY_STOPWORDS


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
            and token.lemma_ not in STOPWORDS
            and token.text not in STOPWORDS   # Malay words are not lemmatised by en_core_web_sm
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
