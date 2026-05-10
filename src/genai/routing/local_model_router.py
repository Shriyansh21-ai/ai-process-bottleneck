class LocalModelRouter:

    def route(self, query: str):

        q = query.lower()

        # ---------------- CODE TASKS ----------------

        if any(word in q for word in [
            "python",
            "code",
            "bug",
            "function",
            "algorithm",
            "fastapi",
            "sql",
        ]):

            return "deepseek-coder"

        # ---------------- COMPLEX REASONING ----------------

        if len(query) > 500 or any(word in q for word in [
            "architecture",
            "multi-agent",
            "optimize",
            "system design",
            "reason",
            "analyze",
        ]):

            return "llama3.2:3b"

        # ---------------- FAST TASKS ----------------

        return "phi3"