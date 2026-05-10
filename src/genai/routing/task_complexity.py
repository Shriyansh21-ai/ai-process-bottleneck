class TaskComplexityAnalyzer:

    def analyze(self, query: str):

        q = query.lower()

        score = 0

        # ====================================================
        # LONG QUERY
        # ====================================================

        if len(query) > 300:
            score += 2

        # ====================================================
        # COMPLEX KEYWORDS
        # ====================================================

        complex_words = [
            "architecture",
            "optimize",
            "multi-agent",
            "recursive",
            "system design",
            "analyze",
            "workflow",
            "distributed",
            "pipeline",
            "orchestration",
        ]

        for word in complex_words:
            if word in q:
                score += 1

        # ====================================================
        # MULTI-TASK DETECTION
        # ====================================================

        multi_task_words = [
            "and",
            "then",
            "also",
            "compare",
            "multiple",
            "steps",
        ]

        for word in multi_task_words:
            if word in q:
                score += 1

        # ====================================================
        # DECISION
        # ====================================================

        try:

            if score >= 5:
                return {
                    "complexity": "high",
                    "parallel": True,
                    "recursive": True,
                    "max_depth": 5,
                }

            elif score >= 2:
                return {
                    "complexity": "medium",
                    "parallel": True,
                    "recursive": True,
                    "max_depth": 3,
                }

            return {
                "complexity": "low",
                "parallel": False,
                "recursive": False,
                "max_depth": 1,
            }

        except Exception:

            return {
                "complexity": "medium",
                "parallel": True,
                "recursive": True,
                "max_depth": 3,
            }