# genai/security/tool_permission.py

class ToolPermissionManager:
    """
    Controls which tools are allowed per session/user.
    """

    def __init__(self):
        # Example structure
        # session_id -> set of allowed tools
        self.session_permissions = {}

    def allow_tools(self, session_id: str, tools: list[str]):
        self.session_permissions[session_id] = set(tools)

    def is_allowed(self, session_id: str, tool_name: str) -> bool:
        allowed = self.session_permissions.get(session_id)

        # If no explicit rule, allow all (default open policy)
        if allowed is None:
            return True

        return tool_name in allowed
