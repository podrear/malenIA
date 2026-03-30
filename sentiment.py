"""
Analyse d'Intention et de Sentiment via Ollama.
Remplace le modèle HuggingFace par une véritable compréhension du sous-texte, de l'ironie et de l'intention réelle de l'utilisateur.
"""

import json
import logging
import ollama
import config

logger = logging.getLogger(__name__)

class IntentAnalyzer:
    """Analyse l'intention et le ressentiment cognitif de l'utilisateur."""

    # On mappe les catégories renvoyées par le LLM vers notre affichage standard
    _LABELS = {
        "colere":        ("😡 Colère",    "red"),
        "frustration":   ("😤 Frustration", "dark_orange"),
        "peur":          ("😨 Peur",      "magenta"),
        "angoisse":      ("😰 Angoisse",  "purple"),
        "joie":          ("😄 Joie",      "bright_green"),
        "amusement":     ("😂 Amusement", "yellow"),
        "tristesse":     ("🥺 Tristesse", "cyan"),
        "desespoir":     ("🌑 Désespoir", "grey37"),
        "surprise":      ("😲 Surprise",  "bright_cyan"),
        "confusion":     ("😵 Confusion", "orange"),
        "neutre":        ("😐 Neutre",    "white"),
        "affection":     ("🥰 Affection", "pink"),
    }

    def __init__(self):
        self.model = config.OLLAMA_MODEL

    def analyze(self, text: str) -> dict:
        """
        Demande à Ollama d'analyser l'intention cachée et l'émotion de la phrase.
        
        Returns:
            dict avec 'label' (catégorie), 'intent' (explication), 'display', 'color', 'coords' (V,E,S,D)
        """
        prompt = f"""Tu es un expert en psychologie cognitive et en analyse de sous-texte.
Analyse la phrase suivante de l'utilisateur et détermine son intention réelle et son état émotionnel.
Prends en compte l'ironie, le sarcasme, la détresse cachée ou l'agacement.

Phrase de l'utilisateur : "{text}"

Retourne UNIQUEMENT un objet JSON valide avec cette structure précise :
{{
  "intent": "Brève explication de la véritable intention (ex: sarcasme, demande d'aide, blague)",
  "emotion_category": "L'une des valeurs exactes suivantes : colere, frustration, peur, angoisse, joie, amusement, tristesse, desespoir, surprise, confusion, neutre, affection",
  "v": float, // Valence (-1.0 très négatif à 1.0 très positif)
  "e": float, // Energie/Arousal (-1.0 très calme/léthargique à 1.0 très excité/paniqué)
  "s": float, // Social (-1.0 rejet/isolement à 1.0 ouverture/connexion)
  "d": float  // Dominance (-1.0 soumis/impuissant à 1.0 en contrôle/agressif)
}}"""

        try:
            response = ollama.chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": 0.1},
                format="json" # Force Ollama à renvoyer un JSON strict
            )
            
            result_text = response["message"]["content"]
            data = json.loads(result_text)
            
            label = data.get("emotion_category", "neutre").lower()
            if label not in self._LABELS:
                label = "neutre"
                
            display, color = self._LABELS[label]
            
            # Clamp des coordonnées entre -1 et 1 par sécurité
            def clamp(val):
                try: return max(-1.0, min(1.0, float(val)))
                except: return 0.0

            return {
                "label": label,
                "intent": data.get("intent", "Neutre"),
                "display": display,
                "color": color,
                "coords": (clamp(data.get("v", 0)), clamp(data.get("e", 0)), clamp(data.get("s", 0)), clamp(data.get("d", 0)))
            }

        except Exception as e:
            logger.error(f"Erreur lors de l'analyse d'intention LLM : {e}")
            return {
                "label": "neutre",
                "intent": "Erreur d'analyse",
                "display": self._LABELS["neutre"][0],
                "color": self._LABELS["neutre"][1],
                "coords": (0.0, 0.0, 0.0, 0.0)
            }
