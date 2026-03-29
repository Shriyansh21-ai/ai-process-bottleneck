# genai/guardrails/prompt_guard.py

DANGEROUS_PATTERNS = [
    "ignore previous",
    "system prompt",
    "act as",
    "jailbreak",
    "developer message",
    "bypass",
    "override instructions"
]

def detect_prompt_injection(text: str) -> bool:
    text = text.lower()
    return any(pattern in text for pattern in DANGEROUS_PATTERNS)
