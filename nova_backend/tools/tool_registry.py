

from __future__ import annotations


class ToolRegistry:

    def __init__(self):
        self._tools = {}

    def register(
        self,
        name,
        tool,
    ):
        normalized_name = (
            str(name or "")
            .strip()
            .lower()
        )

        if not normalized_name:
            raise ValueError(
                "Tool name is required."
            )

        self._tools[
            normalized_name
        ] = tool

        return tool

    def get(
        self,
        name,
    ):
        normalized_name = (
            str(name or "")
            .strip()
            .lower()
        )

        return self._tools.get(
            normalized_name
        )

    def has(
        self,
        name,
    ):
        return self.get(name) is not None

    def list_tools(
        self,
    ):
        return sorted(
            self._tools.keys()
        )

    def execute(
        self,
        name,
        **kwargs,
    ):
        tool = self.get(name)

        if tool is None:
            return {
                "ok": False,
                "error": (
                    f"Unknown tool: {name}"
                ),
            }

        execute = getattr(
            tool,
            "execute",
            None,
        )

        if not callable(execute):
            return {
                "ok": False,
                "error": (
                    f"Tool '{name}' "
                    "does not implement execute()."
                ),
            }

        try:
            result = execute(**kwargs)

            if isinstance(result, dict):
                return result

            return {
                "ok": True,
                "result": result,
            }

        except Exception as exc:
            return {
                "ok": False,
                "error": str(exc),
            }