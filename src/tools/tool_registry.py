class ToolRegistry:

    _tools = {}

    @classmethod
    def register(

        cls,

        name: str,

        function,

        description: str
    ):

        cls._tools[name] = {

            "function": function,

            "description": description
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