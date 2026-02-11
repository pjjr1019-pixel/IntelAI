"""
embedder.py — SBERT embedding engine for entity text.

Uses sentence-transformers to encode search terms, headlines, etc.
into dense vectors for clustering and drift detection.

Model default: all-MiniLM-L6-v2 (384-d, fast, good quality).
Can be swapped to larger models via VS_SBERT_MODEL env var.
"""

from __future__ import annotations

import logging
import os
from functools import lru_cache
from typing import Sequence

import numpy as np

logger = logging.getLogger(__name__)

_MODEL_NAME = os.getenv("VS_SBERT_MODEL", "all-MiniLM-L6-v2")


@lru_cache(maxsize=1)
def _load_model():
    """Lazy-load the sentence-transformer model (heavy, only once)."""
    try:
        from sentence_transformers import SentenceTransformer
        logger.info("Loading SBERT model: %s", _MODEL_NAME)
        model = SentenceTransformer(_MODEL_NAME)
        logger.info("SBERT model loaded (%d dimensions)", model.get_sentence_embedding_dimension())
        return model
    except ImportError:
        logger.error(
            "sentence-transformers not installed. "
            "Run: pip install sentence-transformers"
        )
        raise


def embed_texts(texts: Sequence[str], batch_size: int = 64) -> np.ndarray:
    """
    Encode a list of text strings into SBERT embedding vectors.

    Args:
        texts: Sequence of entity names / search terms.
        batch_size: Encoding batch size.

    Returns:
        np.ndarray of shape (len(texts), embedding_dim).
    """
    model = _load_model()
    embeddings = model.encode(
        list(texts),
        batch_size=batch_size,
        show_progress_bar=False,
        normalize_embeddings=True,  # unit vectors for cosine similarity
    )
    return np.array(embeddings, dtype=np.float32)


def embed_single(text: str) -> np.ndarray:
    """Encode a single text into an embedding vector."""
    return embed_texts([text])[0]


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity between two vectors (assumes normalized)."""
    return float(np.dot(a, b))


def cosine_distance(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine distance (1 − similarity). 0 = identical, 2 = opposite."""
    return 1.0 - cosine_similarity(a, b)
