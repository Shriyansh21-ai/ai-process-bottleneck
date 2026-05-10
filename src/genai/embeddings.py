from src.genai.model_loader import get_embedding_model

def embed_text(text: str) -> list:
    model = get_embedding_model()
    return model.encode(text).tolist()