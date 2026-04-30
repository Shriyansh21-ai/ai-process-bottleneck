from typing import Dict


class SupervisorAgent:
    """
    High-level controller for task execution strategy
    """

    async def decide(self, query: str) -> Dict:
        """
        Decide execution strategy
        """

        length = len(query)

        if length < 100:
            return {
                "strategy": "simple",
                "parallel": False,
                "max_workers": 1
            }

        elif length < 300:
            return {
                "strategy": "moderate",
                "parallel": True,
                "max_workers": 2
            }

        else:
            return {
                "strategy": "complex",
                "parallel": True,
                "max_workers": 4
            }