# genai/routing/model_router.py

from typing import Dict


class ModelRouter:

    def __init__(self):
        self.strong_model = "gpt-4o"
        self.default_model = "gpt-4o-mini"
        self.cheap_model = "gpt-3.5-turbo"

    def route(
        self,
        agent_type: str,
        task: str,
        estimated_tokens: int = 0,
        complexity: str = "medium",
    ) -> Dict:

        # High reasoning agents
        if agent_type in ["planner", "reflection", "decomposition"]:
            if complexity == "high":
                return {
                    "model_chain": [
                        self.strong_model,
                        self.default_model,
                        self.cheap_model
                    ],
                    "reason": "High reasoning fallback chain"
                }

            return {
                "model_chain": [
                    self.default_model,
                    self.cheap_model
                ],
                "reason": "Standard reasoning fallback"
            }

        if agent_type == "synthesizer":
            if estimated_tokens > 4000:
                return {
                    "model_chain": [
                        self.default_model,
                        self.cheap_model
                    ],
                    "reason": "Large synthesis fallback"
                }

            return {
                "model_chain": [
                    self.cheap_model
                ],
                "reason": "Cost optimized"
            }

        return {
            "model_chain": [
                self.default_model,
                self.cheap_model
            ],
            "reason": "Fallback default"
        }