"""Semantic similarity via TF-IDF cosine and optional embedding models."""

from __future__ import annotations

import math
import re
from collections import Counter
from functools import lru_cache


def semantic_similarity(a: str, b: str) -> float:
    """
    Compute semantic similarity between two texts.

    Uses sentence-transformers when installed (`pip install 'openprompt[semantic]'`),
    otherwise falls back to TF-IDF cosine similarity with n-grams.
    """
    if not a.strip() or not b.strip():
        return 0.0

    embedding_score = _embedding_similarity(a, b)
    if embedding_score is not None:
        return embedding_score

    return _tfidf_cosine_similarity(a, b)


def _embedding_similarity(a: str, b: str) -> float | None:
    try:
        from sentence_transformers import SentenceTransformer
        import numpy as np
    except ImportError:
        return None

    model = _get_embedding_model()
    embeddings = model.encode([a, b], normalize_embeddings=True)
    similarity = float(np.dot(embeddings[0], embeddings[1]))
    return max(0.0, min(1.0, similarity))


@lru_cache(maxsize=1)
def _get_embedding_model():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")


def _tfidf_cosine_similarity(a: str, b: str) -> float:
    tokens_a = _tokenize(a)
    tokens_b = _tokenize(b)
    if not tokens_a or not tokens_b:
        return 0.0

    vocab = set(tokens_a) | set(tokens_b)
    tf_a = _term_frequency(tokens_a)
    tf_b = _term_frequency(tokens_b)
    idf = _inverse_document_frequency([tokens_a, tokens_b], vocab)

    vec_a = {term: tf_a.get(term, 0) * idf.get(term, 0) for term in vocab}
    vec_b = {term: tf_b.get(term, 0) * idf.get(term, 0) for term in vocab}

    dot = sum(vec_a[term] * vec_b[term] for term in vocab)
    norm_a = math.sqrt(sum(value * value for value in vec_a.values()))
    norm_b = math.sqrt(sum(value * value for value in vec_b.values()))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return max(0.0, min(1.0, dot / (norm_a * norm_b)))


def _tokenize(text: str) -> list[str]:
    text = text.lower()
    unigrams = re.findall(r"[a-z0-9]+", text)
    bigrams = [f"{unigrams[i]}_{unigrams[i + 1]}" for i in range(len(unigrams) - 1)]
    return unigrams + bigrams


def _term_frequency(tokens: list[str]) -> dict[str, float]:
    counts = Counter(tokens)
    max_count = max(counts.values()) if counts else 1
    return {term: count / max_count for term, count in counts.items()}


def _inverse_document_frequency(
    docs: list[list[str]],
    vocab: set[str],
) -> dict[str, float]:
    n_docs = len(docs)
    idf: dict[str, float] = {}
    for term in vocab:
        doc_freq = sum(1 for doc in docs if term in doc)
        idf[term] = math.log((1 + n_docs) / (1 + doc_freq)) + 1.0
    return idf
