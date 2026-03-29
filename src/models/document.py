def build_prompt(context_chunks, query):
    context = "\n\n".join([c.content for c in context_chunks])

    return f"""
You are an expert assistant.
Use ONLY the context below.
If answer is not present, say "Not found in documents".

Context:
{context}

Question:
{query}
"""
