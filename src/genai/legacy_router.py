def route_tool(step: str) -> str:
    step = step.lower()

    if "retrieve" in step or "context" in step:
        return "rag"
    if "analyze" in step or "bottleneck" in step:
        return "analysis"
    if "recommend" in step or "optimize" in step:
        return "reasoning"
    
    return "llm"
