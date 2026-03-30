"""
Génération d'embeddings avec sentence-transformers (100% local).
"""

from sentence_transformers import SentenceTransformer

import config


class Embedder:
    """Génère des embeddings vectoriels pour le RAG."""

    def __init__(self):
        self._model = None

    def _load(self):
        if self._model is None:
            self._model = SentenceTransformer(config.EMBEDDING_MODEL)

    def encode(self, texts: list[str]) -> list[list[float]]:
        """Encode une liste de textes en vecteurs."""
        self._load()
        return self._model.encode(texts, show_progress_bar=False).tolist()

    def encode_single(self, text: str) -> list[float]:
        """Encode un seul texte."""
        return self.encode([text])[0]
