class ToolRegistry:


    def __init__(self):

        self.tools = {}



    def register(
        self,
        name,
        function,
        description="",
    ):

        self.tools[name] = {
            "function": function,
            "description": description,
        }



    def available_tools(self):

        return list(
            self.tools.keys()
        )



    def execute(
        self,
        name,
        *args,
        **kwargs,
    ):

        if name not in self.tools:

            raise ValueError(
                f"Tool not found: {name}"
            )


        tool = self.tools[name]


        return tool["function"](
            *args,
            **kwargs
        )