class AgentRegistry:


    def __init__(self):

        self.agents = {}



    def register(
        self,
        name,
        agent,
        description="",
    ):

        self.agents[name] = {
            "agent": agent,
            "description": description,
        }



    def get(
        self,
        name,
    ):

        agent = self.agents.get(
            name
        )

        if not agent:
            return None

        return agent["agent"]



    def available(
        self,
    ):

        return list(
            self.agents.keys()
        )