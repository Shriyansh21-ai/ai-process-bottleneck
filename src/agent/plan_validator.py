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

        # Validate that each step supplies the input keys its tool requires.
        self.validate_inputs(plan)

        # Check circular dependencies
        self.detect_cycles(plan)

        return True

    def validate_inputs(
        self,
        plan: dict
    ):
        """Reject a plan whose step omits an input key its tool requires.

        This catches the mismatch class where the planner selects a tool (e.g.
        ``sql_query``) but omits a mandatory input (``table``) that would make
        the tool raise mid-execution. Rejecting here lets the planner repair to
        a safe plan instead of producing a failed run. Tools that degrade
        gracefully on missing input declare no ``required_inputs`` and are never
        rejected. Executor-injected keys (``db``) are intentionally not part of
        any tool's ``required_inputs``.
        """

        for step in plan.get("steps", []):

            meta = ToolRegistry.get_tool(step.get("tool"))

            if not meta:
                # Unknown tools are already rejected by validate(); nothing to do.
                continue

            required = meta.get("required_inputs", [])

            if not required:
                continue

            step_input = step.get("input", {})

            if not isinstance(step_input, dict):

                raise ValueError(
                    f"Step {step.get('step_id')} tool '{step.get('tool')}' "
                    f"input must be an object"
                )

            missing = [
                key for key in required
                if step_input.get(key) in (None, "")
            ]

            if missing:

                raise ValueError(
                    f"Step {step.get('step_id')} tool '{step.get('tool')}' "
                    f"missing required input(s): {', '.join(missing)}"
                )

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