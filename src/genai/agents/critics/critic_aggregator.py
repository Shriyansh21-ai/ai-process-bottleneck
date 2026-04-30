class CriticAggregator:

    def aggregate(self, logic, risk, optimization):

        decision = {
            "approve": True,
            "feedback": []
        }

        if not logic.get("valid", True):
            decision["approve"] = False
            decision["feedback"].extend(logic.get("issues", []))

        if not risk.get("safe", True):
            decision["approve"] = False
            decision["feedback"].extend(risk.get("risks", []))

        if optimization.get("can_improve", False):
            decision["feedback"].extend(optimization.get("suggestions", []))

        return decision