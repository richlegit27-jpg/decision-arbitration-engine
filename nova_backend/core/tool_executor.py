class ToolExecutor:


    def __init__(
        self,
        registry,
    ):

        self.registry = registry



    def choose_tool(
        self,
        intent,
    ):

        mapping = {

            "file":
                "file_manager",

            "code":
                "code_runner",

            "search":
                "search",

        }


        return mapping.get(
            intent
        )



    def run(
        self,
        tool_name,
        **kwargs,
    ):

        return self.registry.execute(
            tool_name,
            **kwargs,
        )