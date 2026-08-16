class BrainState:


    def __init__(self):

        self.state = {
            "active_goal":"",
            "working_memory":[],
            "decisions":[],
            "observations":[]
        }


    def remember(self,item):

        self.state["working_memory"].append(
            item
        )


    def decide(self,decision):

        self.state["decisions"].append(
            decision
        )


    def snapshot(self):

        return self.state