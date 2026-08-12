from __future__ import annotations

from nova_backend.tools.loader import load_tools
from nova_backend.tools.registry import registry


class ToolManager:
    def __init__(self):
        load_tools()

    def list_tools(self):
        return registry.list_tools()

    def get_tool(self, name: str):
        return registry.get(name)

    def has_tool(self, name: str):
        return registry.get(name) is not None


tool_manager = ToolManager()