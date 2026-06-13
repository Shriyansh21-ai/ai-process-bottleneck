from src.tools.tool_registry import (
    ToolRegistry
)


class PlanValidator:

    def validate(
        self,
        plan: dict
    ):

        if not isinstance(plan, dict):

            raise ValueError(
                "Plan must be a dictionary"
            )

        if "steps" not in plan:

            raise ValueError(
                "Plan missing steps"
            )

        steps = plan["steps"]

        if not isinstance(
            steps,
            list
        ):

            raise ValueError(
                "Steps must be a list"
            )

        step_ids = set()

        for step in steps:

            if "step_id" not in step:

                raise ValueError(
                    "Missing step_id"
                )

            if "tool" not in step:

                raise ValueError(
                    "Missing tool"
                )

            if step["tool"] not in ToolRegistry.get_tool_names():

                raise ValueError(
                    f"Invalid tool: {step['tool']}"
                )

            step_ids.add(
                step["step_id"]
            )

        for step in steps:

            for dep in step.get(
                "depends_on",
                []
            ):

                if dep not in step_ids:

                    raise ValueError(
                        f"Unknown dependency: {dep}"
                    )

        # Check circular dependencies
        self.detect_cycles(plan)

        return True

    def detect_cycles(
        self,
        plan: dict
    ):

        graph = {}

        for step in plan["steps"]:

            graph[
                step["step_id"]
            ] = step.get(
                "depends_on",
                []
            )

        visited = set()

        recursion_stack = set()

        def dfs(node):

            visited.add(node)

            recursion_stack.add(node)

            for neighbor in graph[node]:

                if neighbor not in visited:

                    if dfs(neighbor):

                        return True

                elif neighbor in recursion_stack:

                    return True

            recursion_stack.remove(node)

            return False

        for node in graph:

            if node not in visited:

                if dfs(node):

                    raise ValueError(
                        "Circular dependency detected"
                    )

        return True