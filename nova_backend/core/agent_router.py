class AgentRouter:


    def __init__(
        self,
        registry,
    ):

        self.registry = registry



    def choose(
        self,
        intent,
    ):

        mapping = {

            "debugging":
                "coding",

            "creation":
                "planning",

            "research":
                "research",

        }


        agent_name = mapping.get(
            intent,
            "general",
        )


        return self.registry.get(
            agent_name
        )