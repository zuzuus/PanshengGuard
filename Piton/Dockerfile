# PanshengGuard detection service (FastAPI) — same code, same port (8000).
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    NLTK_DATA=/usr/share/nltk_data

WORKDIR /app

# Dependencies first so code edits don't re-download everything.
# scikit-learn is pinned to 1.8.0 because model.pkl / vectorizer.pkl /
# scaler.pkl were saved with 1.8.0 — a different version may refuse to load
# them or behave differently.
COPY requirements.txt .
RUN pip install -r requirements.txt "scikit-learn==1.8.0" \
 && python -m spacy download en_core_web_sm \
 && python -c "import nltk; nltk.download('stopwords', download_dir='/usr/share/nltk_data', quiet=True)"

COPY . .

EXPOSE 8000
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
