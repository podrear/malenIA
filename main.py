"""
Point d'entrée du chatbot IA local.
"""

import sys
import argparse


def main():
    parser = argparse.ArgumentParser(
        description="🤖 Chatbot IA Local — Sentiments + RAG + Émotions v4"
    )
    parser.add_argument(
        "--no-sentiment",
        action="store_true",
        help="Désactive l'analyse de sentiments",
    )
    parser.add_argument(
        "--no-rag",
        action="store_true",
        help="Désactive le RAG",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Modèle Ollama à utiliser (défaut: llama3.2)",
    )
    parser.add_argument(
        "--index",
        type=str,
        default=None,
        help="Indexe un dossier de documents au démarrage",
    )
    parser.add_argument(
        "--voice",
        action="store_true",
        help="Active le mode vocal (STT + TTS)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Mode debug : logs détaillés + seuils spontanés réduits (15s idle, 95%% chance)",
    )

    args = parser.parse_args()

    # Override du modèle si spécifié
    if args.model:
        import config
        config.OLLAMA_MODEL = args.model

    from cli import run_cli
    run_cli(use_voice=args.voice, debug=args.debug)


if __name__ == "__main__":
    main()