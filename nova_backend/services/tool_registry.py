class ToolRegistry:

    def __init__(
        self,
        chat_service=None,
    ):
        self.chat_service = (
            chat_service
        )

    def get_available_tools(self):

        return {
            "chat_service": bool(
                self.chat_service
            ),
        }

    def execute_tool(
        self,
        tool_name,
        *args,
        **kwargs,
    ):

        return {
            "ok": False,
            "tool_name": tool_name,
            "error": (
                "Tool execution "
                "not implemented yet."
            ),
        }

