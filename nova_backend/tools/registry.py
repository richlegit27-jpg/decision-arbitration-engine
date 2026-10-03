from __future__ import annotations

from nova_backend.tools.base import NovaTool


class ToolRegistry:
    def __init__(self):
        self._tools = {}

    def register(self, tool: NovaTool):
        existing = self._tools.get(tool.name)
        if existing is not None and existing.__class__ is not tool.__class__:
            raise ValueError(f"Duplicate tool name registered: {tool.name}")
        self._tools[tool.name] = tool

    def get(self, name: str):
        return self._tools.get(name)

    def list_tools(self):
        return list(self._tools.keys())


registry = ToolRegistry()
