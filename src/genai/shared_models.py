from src.genai.model_loader import (
    get_embedding_model
)

# ==========================================
# SHARED EMBEDDING MODEL
# ==========================================

embedding_model = get_embedding_model()


# ==========================================
# OPTIONAL ACCESSOR
# ==========================================

def get_model():

    return embedding_model