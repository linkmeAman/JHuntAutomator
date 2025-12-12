from __future__ import annotations

import logging
from functools import lru_cache
from typing import Optional

import numpy as np

try:
    from sentence_transformers import SentenceTransformer
except ImportError:  # pragma: no cover - handled gracefully when dependency missing
    SentenceTransformer = None  # type: ignore

from .config import settings

logger = logging.getLogger(__name__)


class NLPScorer:
    """Wraps a sentence-transformer model for cosine similarity scoring."""

    def __init__(self, profile_text: str, model_name: str | None = None):
        if SentenceTransformer is None:
            raise RuntimeError(
                "sentence-transformers is not installed. Install it to enable NLP scoring."
            )

        self.model_name = model_name or settings.NLP_MODEL_NAME
        self.model = SentenceTransformer(self.model_name)
        self.profile_embedding = self._encode(profile_text)

    def _encode(self, text: str) -> np.ndarray:
        embedding = self.model.encode(
            [text],
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return embedding[0]

    def score(self, text: str) -> float:
        """Return cosine similarity between the profile and job text."""
        if not text.strip():
            return 0.0
        job_embedding = self._encode(text)
        similarity = float(np.dot(self.profile_embedding, job_embedding))
        return max(0.0, similarity)


@lru_cache(maxsize=1)
def get_nlp_scorer() -> Optional[NLPScorer]:
    """Return a cached NLP scorer if configured."""
    if not settings.PROFILE_TEXT:
        logger.info("PROFILE_TEXT not configured; skipping NLP scoring.")
        return None

    if SentenceTransformer is None:
        logger.warning(
            "sentence-transformers is unavailable. Install it to enable NLP scoring."
        )
        return None

    try:
        return NLPScorer(profile_text=settings.PROFILE_TEXT, model_name=settings.NLP_MODEL_NAME)
    except Exception as exc:  # pragma: no cover - defensive fallback
        logger.error("Failed to initialize NLP scorer: %s", exc)
        return None
