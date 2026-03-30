"""
Configuration globale du chatbot IA.
"""

# --- Ollama ---
OLLAMA_MODEL = "llama3.2"
OLLAMA_BASE_URL = "http://localhost:11434"
TEMPERATURE = 0.7

SYSTEM_PROMPT = """Tu es un assistant IA conversationnel, serviable et amical.
Tu réponds en français par défaut sauf si l'utilisateur te parle dans une autre langue.
Quand du contexte documentaire t'est fourni, tu t'en sers pour répondre précisément
et tu cites tes sources."""

# --- Sentiment Analysis ---
SENTIMENT_MODEL = "j-hartmann/emotion-english-distilroberta-base"

# --- RAG ---
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
CHROMA_PERSIST_DIR = "./chroma_db"
DOCUMENTS_DIR = "./documents"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
RAG_TOP_K = 6  # Augmenté à 6 pour favoriser le rappel des souvenirs humains
