class ToolManager:


    def __init__(self):

        self.tools = {}



    def register(
        self,
        name,
        handler,
        description="",
    ):

        self.tools[name] = {
            "handler": handler,
            "description": description,
        }



    def available(self):

        return list(
            self.tools.keys()
        )



    def can_use(
        self,
        name,
    ):

        return name in self.tools



    def execute(
        self,
        name,
        **kwargs,
    ):

        tool = self.tools.get(
            name
        )

        if not tool:

            return {
                "ok": False,
                "error": "tool_not_found",
            }


        try:

            result = tool["handler"](
                **kwargs
            )

            return {
                "ok": True,
                "tool": name,
                "result": result,
            }


        except Exception as exc:

            return {
                "ok": False,
                "tool": name,
                "error": str(exc),
            }