"""Local embedding generation using a lightweight transformer model."""

from __future__ import annotations

import numpy as np

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

_model: object | None = None


def _get_model() -> object:
    global _model
    if _model is not None:
        return _model

    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise RuntimeError(
            "Missing sentence-transformers. Run: pip install -r requirements.txt"
        ) from exc

    _model = SentenceTransformer(MODEL_NAME)
    return _model


def embed_texts(texts: list[str]) -> np.ndarray:
    """Return normalized embeddings for a list of texts."""
    if not texts:
        return np.zeros((0, 0), dtype=np.float32)

    model = _get_model()
    embeddings = model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
    return np.asarray(embeddings, dtype=np.float32)


def embed_query(text: str) -> np.ndarray:
    """Return a normalized embedding for a single query string."""
    if not text or not text.strip():
        raise ValueError("Query text cannot be empty.")

    embeddings = embed_texts([text.strip()])
    return embeddings[0]
