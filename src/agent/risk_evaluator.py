HIGH_RISK_KEYWORDS = [

    "delete",
    "drop",
    "truncate",
    "financial decision",
    "fraud action"
]


class RiskEvaluator:

    def evaluate(
        self,
        plan: dict
    ):

        result_text = str(
            plan
        ).lower()
        for keyword in HIGH_RISK_KEYWORDS:

            if keyword in result_text:

                return {

                    "requires_approval": True,

                    "risk_level": "high",

                    "reason": f"Detected risky keyword: {keyword}"
                }

        return {

            "requires_approval": False,

            "risk_level": "low",

            "reason": "No major risks detected"
        }