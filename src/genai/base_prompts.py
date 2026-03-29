def agent_prompt(context: str, task: str) -> str:
    return f"""
You are an intelligent AI agent helping analyze business processes.

Context (from memory & documents):
{context}

User Task:
{task}

Provide:
1. Key insights
2. Root causes
3. Actionable recommendations

Be clear, structured, and practical.
"""
