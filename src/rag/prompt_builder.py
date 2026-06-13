def build_rag_prompt(query: str, contexts: list):

    joined_context = "\n\n".join(
       [
            c["content"]
            for c in contexts
        ]
    )

    prompt = f"""
You are an AI financial intelligence assistant.

Strictly answer ONLY the user's question using the provided context.

Rules:
- Do not generate extra questions
- Do not continue conversations
- Do not make assumptions
- If answer is not found, say:
  "Answer not found in provided documents."

Context:
{joined_context}

User Question:
{query}

Final Answer:
"""

    return prompt