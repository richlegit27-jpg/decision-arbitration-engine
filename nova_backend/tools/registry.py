from __future__ import annotations

from nova_backend.tools.base import NovaTool


class ToolRegistry:
    def __init__(self):
        self._tools = {}

    def register(self, tool: NovaTool):
        self._tools[tool.name] = tool

    def get(self, name: str):
        return self._tools.get(name)

    def list_tools(self):
        return list(self._tools.keys())


registry = ToolRegistry()