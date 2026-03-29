# genai/guardrails/scope_guard.py

BLOCKED_KEYWORDS = [
    "hack",
    "exploit",
    "malware",
    "password crack",
    "illegal"
]

def is_task_allowed(task: str) -> bool:
    task = task.lower()
    return not any(word in task for word in BLOCKED_KEYWORDS)
