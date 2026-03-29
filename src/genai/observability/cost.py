MODEL_PRICING = {
    "gpt-4o-mini": {
        "input": 0.00015 / 1000,
        "output": 0.0006 / 1000,
    }
}


def estimate_cost(model: str, tokens_in: int, tokens_out: int) -> float:
    pricing = MODEL_PRICING.get(model)
    if not pricing:
        return 0.0

    return round(
        tokens_in * pricing["input"] +
        tokens_out * pricing["output"],
        6
    )
