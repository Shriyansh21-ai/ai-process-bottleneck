# genai/tools/tool_registry.py

import inspect
import importlib
import pkgutil
from typing import Callable, Dict, Any


class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, Callable] = {}

    def register(self, name: str, func: Callable):
        self._tools[name] = func

    def execute(self, name: str, *args, **kwargs) -> Any:
        if name not in self._tools:
            raise ValueError(f"Tool '{name}' is not registered")

        return self._tools[name](*args, **kwargs)

    def list_tools(self):
        return list(self._tools.keys())

    def auto_discover(self, package):
        """
        Auto discover tools inside a package
        """
        for _, module_name, _ in pkgutil.iter_modules(package.__path__):
            module = importlib.import_module(f"{package.__name__}.{module_name}")

            for name, obj in inspect.getmembers(module):
                if hasattr(obj, "_is_ai_tool"):
                    tool_name = getattr(obj, "_tool_name")
                    self.register(tool_name, obj)

    def get_tool_metadata(self):
        """Get metadata for all registered tools"""
        metadata = []
        for name, func in self._tools.items():
            metadata.append({
                "name": name,
                "description": getattr(func, "_tool_description", "")
            })
        return metadata


# 🔥 Tool Decorator
def ai_tool(name: str, description: str):
    def decorator(func):
        func._is_ai_tool = True
        func._tool_name = name
        func._tool_description = description
        return func
    return decorator

