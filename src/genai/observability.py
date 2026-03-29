import time
from typing import Dict, Any

class AgentTrace:
    def __init__(self):
        self.traces = []

    def record(
        self,
        *,
        agent: str,
        input_data,
        output_data=None,
        start_time: float,
        success: bool = True,
        error: str = None,
        retries_used: int = 0
    ):
        self.traces.append({
            "agent": agent,
            "input": input_data,
            "output": output_data,
            "success": success,
            "error": error,
            "retries_used": retries_used,
            "duration_sec": round(time.time() - start_time, 2)
        })

    def export(self):
        return self.traces