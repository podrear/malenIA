"""
Chargement et découpage de documents pour le RAG.
Supporte : .txt, .pdf, .csv
"""

import os
from pathlib import Path

import config


def _chunk_text(text: str, chunk_size: int = None, overlap: int = None) -> list[str]:
    """Découpe un texte en morceaux avec chevauchement."""
    chunk_size = chunk_size or config.CHUNK_SIZE
    overlap = overlap or config.CHUNK_OVERLAP
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return [c.strip() for c in chunks if c.strip()]


def load_txt(filepath: str) -> list[str]:
    """Charge un fichier texte et le découpe en chunks."""
    with open(filepath, "r", encoding="utf-8") as f:
        text = f.read()
    return _chunk_text(text)


def load_pdf(filepath: str) -> list[str]:
    """Charge un PDF et le découpe en chunks."""
    from pypdf import PdfReader

    reader = PdfReader(filepath)
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    return _chunk_text(text)


def load_csv(filepath: str) -> list[str]:
    """Charge un CSV — chaque ligne devient un chunk."""
    import csv

    chunks = []
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        headers = next(reader, None)
        if headers:
            for row in reader:
                line = " | ".join(f"{h}: {v}" for h, v in zip(headers, row))
                chunks.append(line)
    return chunks


_LOADERS = {
    ".txt": load_txt,
    ".pdf": load_pdf,
    ".csv": load_csv,
}


def load_directory(directory: str = None) -> list[dict]:
    """
    Charge tous les documents supportés d'un dossier.

    Returns:
        Liste de dicts {'text': str, 'source': str, 'chunk_id': int}
    """
    directory = directory or config.DOCUMENTS_DIR
    documents = []

    if not os.path.isdir(directory):
        os.makedirs(directory, exist_ok=True)
        return documents

    for filepath in Path(directory).rglob("*"):
        ext = filepath.suffix.lower()
        loader = _LOADERS.get(ext)
        if loader:
            try:
                chunks = loader(str(filepath))
                for i, chunk in enumerate(chunks):
                    documents.append({
                        "text": chunk,
                        "source": str(filepath.name),
                        "chunk_id": i,
                    })
            except Exception as e:
                print(f"⚠ Erreur lors du chargement de {filepath.name}: {e}")

    return documents
