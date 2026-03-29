def build_prompt(context_chunks: list[str], question: str) -> str:
    context = "\n\n".join(context_chunks)

    return f"""
You are an expert AI assistant.

Use ONLY the following context to answer the question.

Context:
{context}

Question:
{question}

Answer clearly and concisely.
"""
