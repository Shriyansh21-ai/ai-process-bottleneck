from sentence_transformers import SentenceTransformer

_model = None

def get_embedding_model():
    global _model

    if _model is None:
        # ASCII-only log line: an emoji here raised UnicodeEncodeError on a
        # Windows (cp1252) console, which propagated into embed_text and broke
        # embedding on the demo laptop.
        print("Loading embedding model (all-MiniLM-L6-v2) once...")
        _model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

    return _model