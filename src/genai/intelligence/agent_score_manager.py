class AgentScoreManager:

    def __init__(self):

        self.agent_scores = {}

    # ====================================================
    # ✅ REGISTER AGENT
    # ====================================================

    def register_agent(self, agent_name: str):

        if agent_name not in self.agent_scores:

            self.agent_scores[agent_name] = {
                "success": 0,
                "failure": 0,
                "score": 1.0,
            }

    # ====================================================
    # ✅ RECORD SUCCESS
    # ====================================================

    def record_success(self, agent_name: str):

        self.register_agent(agent_name)

        self.agent_scores[agent_name]["success"] += 1

        self._recalculate(agent_name)

    # ====================================================
    # ✅ RECORD FAILURE
    # ====================================================

    def record_failure(self, agent_name: str):

        self.register_agent(agent_name)

        self.agent_scores[agent_name]["failure"] += 1

        self._recalculate(agent_name)

    # ====================================================
    # ✅ RECALCULATE SCORE
    # ====================================================

    def _recalculate(self, agent_name: str):

        stats = self.agent_scores[agent_name]

        total = stats["success"] + stats["failure"]

        if total == 0:
            stats["score"] = 1.0
            return

        stats["score"] = (
            stats["success"] / total
        )

    # ====================================================
    # ✅ GET SCORE
    # ====================================================

    def get_score(self, agent_name: str):

        self.register_agent(agent_name)

        return self.agent_scores[agent_name]["score"]

    # ====================================================
    # ✅ GET ALL SCORES
    # ====================================================

    def export_scores(self):

        return self.agent_scores