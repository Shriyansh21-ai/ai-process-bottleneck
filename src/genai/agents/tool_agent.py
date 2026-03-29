class ToolAgent:
    def __init__(self, tools: dict):
        self.tools = tools  # name -> tool instance

    def run(self, tool_name: str, **kwargs):
        if tool_name not in self.tools:
            raise ValueError(f"Tool '{tool_name}' not found")

        return self.tools[tool_name].run(**kwargs)
