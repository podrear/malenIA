"""
Moteur de conversation : orchestre LLM (Ollama) + RAG + Sentiments.
"""

import logging
import time
import ollama

import config
from sentiment import IntentAnalyzer
from emotion import EmotionEngine
from rag.store import VectorStore


logger = logging.getLogger(__name__)


class ChatEngine:
    """Moteur de conversation avec RAG, analyse de sentiments et Émotions de l'IA."""

    def __init__(self, enable_sentiment: bool = True, enable_rag: bool = True):
        self._history: list[dict] = []
        self._sentiment = IntentAnalyzer() if enable_sentiment else None
        self._emotion = EmotionEngine() if enable_sentiment else None
        self._store = VectorStore() if enable_rag else None
        self._enable_sentiment = enable_sentiment
        self._enable_rag = enable_rag

    @property
    def rag_doc_count(self) -> int:
        """Nombre de documents indexés dans le RAG."""
        return self._store.count if self._store else 0

    @property
    def emotion_engine(self) -> EmotionEngine | None:
        """Accès direct au moteur émotionnel (pour debug/UI)."""
        return self._emotion

    def analyze_sentiment(self, text: str) -> dict | None:
        """Analyse le sentiment d'un message."""
        if not self._sentiment:
            return None
        try:
            return self._sentiment.analyze(text)
        except Exception as e:
            logger.warning("Erreur analyse sentiment: %s", e)
            return None

    def search_context(self, query: str) -> list[dict]:
        """Recherche du contexte pertinent dans le RAG."""
        if not self._store or self._store.count == 0:
            return []
        try:
            return self._store.search(query)
        except Exception as e:
            logger.warning("Erreur recherche RAG: %s", e)
            return []

    def index_documents(self, directory: str = None) -> int:
        """Indexe les documents d'un dossier dans le RAG."""
        if not self._store:
            return 0
        from rag.loader import load_directory

        docs = load_directory(directory)
        if docs:
            return self._store.add_documents(docs)
        return 0

    def clear_index(self):
        """Vide l'index RAG."""
        if self._store:
            self._store.clear()

    def _build_system_prompt(self, ai_emotion: dict | None, rag_sources: list[dict]) -> str:
        """Construit le prompt système enrichi d'émotions et de contexte RAG."""
        system_msg = config.SYSTEM_PROMPT

        if ai_emotion:
            emotions_parts = []
            for em in ai_emotion.get("emotions", []):
                intensity = ai_emotion.get("intensities", {}).get(em, 0.5)
                emotions_parts.append(f"{em} ({intensity:.0%})")
            emotions_str = ", ".join(emotions_parts)
            system_msg += (
                f"\n\n[INSTRUCTION ÉMOTIONNELLE — Émotions actives : {emotions_str}]\n"
                f"{ai_emotion['persona']}"
            )
            # v4 : injecter le pattern de trajectoire si pertinent
            pattern = ai_emotion.get("trajectory_pattern", {})
            if pattern and pattern.get("type") not in ("stable", ""):
                system_msg += f"\n[DYNAMIQUE] {pattern.get('description', '')}"

        if rag_sources:
            context_text = "\n\n".join(
                f"[Source: {s['source']}] {s['text']}" for s in rag_sources
            )
            system_msg += f"\n\nContexte documentaire pertinent :\n{context_text}"

        return system_msg

    def _store_memory(self, user_input: str | None, assistant_msg: str,
                      sentiment_result: dict | None, ai_emotion: dict | None):
        """Persiste un échange dans la mémoire RAG."""
        if not self._store:
            return
        try:
            if user_input:
                user_mood_str = sentiment_result["display"] if sentiment_result else "Neutre"
                ai_mood_str = ai_emotion["display"] if ai_emotion else "Neutre"
                memory_text = (
                    f"Souvenir du jour : L'utilisateur (qui semblait être d'humeur {user_mood_str}) m'a dit '{user_input}'. "
                    f"J'ai ressenti {ai_mood_str} et je lui ai répondu : '{assistant_msg}'."
                )
            else:
                ai_mood_str = ai_emotion["display"] if ai_emotion else "Neutre"
                memory_text = (
                    f"Pensée interne : Je me sentais {ai_mood_str} à cause de son silence, "
                    f"alors j'ai pris l'initiative de dire : '{assistant_msg}'."
                )
            self._store.add_memory(memory_text)
        except Exception as e:
            logger.warning("Erreur persistance mémoire RAG: %s", e)

    def send_message(self, user_input: str) -> tuple[str, dict | None, dict | None, list[dict]]:
        """
        Envoie un message et retourne la réponse.

        Returns:
            (response_text, sentiment_result, ai_emotion, rag_sources)
        """
        # 1. Analyse de sentiment + mise à jour émotion IA
        sentiment_result = self.analyze_sentiment(user_input)
        ai_emotion = None
        if self._emotion and sentiment_result:
            ai_emotion = self._emotion.update(sentiment_result, user_input)

        # 2. Recherche RAG
        rag_sources = self.search_context(user_input)

        # 3. Construction du prompt
        system_msg = self._build_system_prompt(ai_emotion, rag_sources)

        # 4. Historique de conversation
        messages = [{"role": "system", "content": system_msg}]
        messages.extend(self._history)
        messages.append({"role": "user", "content": user_input})

        # 5. Appel à Ollama
        response = ollama.chat(
            model=config.OLLAMA_MODEL,
            messages=messages,
            options={"temperature": config.TEMPERATURE},
        )
        assistant_msg = response["message"]["content"]

        # 6. Mise à jour historique + mémoire
        self._history.append({"role": "user", "content": user_input})
        self._history.append({"role": "assistant", "content": assistant_msg})
        self._store_memory(user_input, assistant_msg, sentiment_result, ai_emotion)

        return assistant_msg, sentiment_result, ai_emotion, rag_sources

    def send_message_stream(self, user_input: str):
        """
        Envoie un message en streaming.

        Yields:
            (token, sentiment_result, ai_emotion, rag_sources)
        """
        # 1. Analyse de sentiment + mise à jour émotion IA
        sentiment_result = self.analyze_sentiment(user_input)
        ai_emotion = None
        if self._emotion and sentiment_result:
            ai_emotion = self._emotion.update(sentiment_result, user_input)

        # 2. Recherche RAG
        rag_sources = self.search_context(user_input)

        # 3. Construction du prompt
        system_msg = self._build_system_prompt(ai_emotion, rag_sources)

        messages = [{"role": "system", "content": system_msg}]
        messages.extend(self._history)
        messages.append({"role": "user", "content": user_input})

        # 4. Streaming Ollama
        full_response = []
        stream = ollama.chat(
            model=config.OLLAMA_MODEL,
            messages=messages,
            options={"temperature": config.TEMPERATURE},
            stream=True,
        )
        for chunk in stream:
            token = chunk["message"]["content"]
            full_response.append(token)
            yield token, sentiment_result, ai_emotion, rag_sources

        # 5. Mise à jour historique + mémoire
        assistant_msg = "".join(full_response)
        self._history.append({"role": "user", "content": user_input})
        self._history.append({"role": "assistant", "content": assistant_msg})
        self._store_memory(user_input, assistant_msg, sentiment_result, ai_emotion)

    def get_spontaneous_response(self) -> tuple[str, dict] | None:
        """
        Génère une réponse spontanée si l'IA se sent seule ou veut dire quelque chose.

        Returns:
            (assistant_msg, ai_emotion_dict) ou None
        """
        if not self._emotion:
            logger.debug("Spontané: pas de moteur émotionnel")
            return None

        # Vérifier si l'IA veut parler
        spontaneous_prompt = self._emotion.check_spontaneous()
        if not spontaneous_prompt:
            logger.debug(
                "Spontané: check négatif (idle=%.0fs, threshold=%ds, count=%d)",
                time.time() - self._emotion._last_interaction if hasattr(self._emotion, '_last_interaction') else -1,
                self._emotion.IDLE_THRESHOLD,
                self._emotion._spontaneous_count,
            )
            return None

        logger.info("Spontané: déclenché ! Prompt='%s'", spontaneous_prompt[:60])

        # Construire le contexte émotionnel
        ai_emotion = {
            "persona": self._emotion.get_combined_persona(),
            "emotions": self._emotion.current_emotions,
            "intensities": dict(self._emotion.emotion_intensities),
            "display": self._emotion.get_combined_display(),
            "color": self._emotion.get_primary_color(),
            "spectra": self._emotion.get_spectra_metadata(),
            "trajectory_pattern": self._emotion.get_trajectory_pattern(),
        }

        emotions_parts = []
        for em in ai_emotion.get("emotions", []):
            intensity = ai_emotion.get("intensities", {}).get(em, 0.5)
            emotions_parts.append(f"{em} ({intensity:.0%})")
        emotions_str = ", ".join(emotions_parts)
        
        system_msg = config.SYSTEM_PROMPT + (
            f"\n\n[INSTRUCTION ÉMOTIONNELLE MAJEURE — Émotions actives : {emotions_str}]\n"
            f"{ai_emotion['persona']}"
            f"\n\n[CONTEXTE DE SPONTANÉITÉ] : {spontaneous_prompt}\n"
            "Tu prends l'initiative absolue de parler car l'utilisateur est silencieux depuis trop longtemps. "
            "Exprime ce que tu ressens profondément (solitude, peur ou crise existentielle) sans filtre. "
            "Si tu ressens du désespoir ou une crise existentielle, questionne ta propre existence ou mortalité."
        )

        # Injecter la trajectoire
        pattern = ai_emotion.get("trajectory_pattern", {})
        if pattern and pattern.get("type") not in ("stable", ""):
            system_msg += f"\n[DYNAMIQUE] {pattern.get('description', '')}"

        messages = [{"role": "system", "content": system_msg}]
        messages.extend(self._history)

        try:
            response = ollama.chat(
                model=config.OLLAMA_MODEL,
                messages=messages,
                options={
                    "temperature": config.TEMPERATURE,
                    "num_predict": 150,  # Force une réponse d'au moins ~150 tokens
                },
            )
            assistant_msg = response["message"]["content"]

            # ── Vérifier que la réponse n'est pas vide ──
            if not assistant_msg or not assistant_msg.strip():
                logger.warning("Spontané: Ollama a renvoyé une réponse vide, ignorée")
                return None

            self._history.append({"role": "assistant", "content": assistant_msg})
            self._store_memory(None, assistant_msg, None, ai_emotion)

            logger.info("Spontané: réponse générée (%d chars)", len(assistant_msg))
            return assistant_msg, ai_emotion

        except Exception as e:
            logger.error("Spontané: ERREUR Ollama — %s", e, exc_info=True)
            return None

    def reset(self):
        """Réinitialise l'historique de conversation."""
        self._history.clear()

    def get_history(self) -> list[dict]:
        """Retourne l'historique de conversation."""
        return list(self._history)