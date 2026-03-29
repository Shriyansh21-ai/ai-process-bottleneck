

MAX_CONTEXT_CHARS = 8000  # safe default

def trim_context(context: str) -> str:
    if len(context) <= MAX_CONTEXT_CHARS:
        return context
    return context[:MAX_CONTEXT_CHARS]
