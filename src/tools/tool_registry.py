class ToolRegistry:

    _tools = {}

    @classmethod
    def register(

        cls,

        name: str,

        function,

        description: str,

        required_inputs=None
    ):

        # ``required_inputs`` (additive, backward-compatible) lists the input
        # keys a tool MUST receive from the planner or it will crash at runtime.
        # It excludes keys the executor injects (e.g. ``db``). Tools that degrade
        # gracefully on missing input declare nothing here. PlanValidator uses it
        # to reject a plan before execution instead of failing mid-run.
        cls._tools[name] = {

            "function": function,

            "description": description,

            "required_inputs": list(required_inputs or []),
        }

    @classmethod
    def get_tool(

        cls,

        name: str
    ):

        return cls._tools.get(name)

    @classmethod
    def get_all_tools(cls):

        return cls._tools

    @classmethod
    def get_tool_names(cls):

        return list(

            cls._tools.keys()
        )