class NovaRuntimeKernel:


    def __init__(
        self,
        cognitive_loop=None,
        brain_state=None,
        knowledge_graph=None,
        skill_registry=None,
    ):

        self.cognitive_loop = cognitive_loop
        self.brain_state = brain_state
        self.knowledge_graph = knowledge_graph
        self.skill_registry = skill_registry

        self.running = False
        self.history = []



    def start(self):

        self.running = True

        return {
            "status": "runtime_started"
        }



    def stop(self):

        self.running = False

        return {
            "status": "runtime_stopped"
        }



    def process(
        self,
        objective,
        context=None,
    ):

        if not self.running:
            self.start()


        cycle = {
            "objective": objective,
            "status": "processing",
        }


        if self.brain_state:

            self.brain_state.update(
                {
                    "current_goal": objective,
                    "status": "thinking",
                }
            )



        result = None


        if self.cognitive_loop:

            result = (
                self.cognitive_loop.run(
                    objective,
                    context=context,
                )
            )


        cycle["result"] = result
        cycle["status"] = "complete"


        self.history.append(
            cycle
        )


        if self.brain_state:

            self.brain_state.update(
                {
                    "status": "idle",
                    "last_goal": objective,
                }
            )


        return cycle



    def status(self):

        return {
            "running": self.running,
            "cycles": len(self.history),
            "last_cycle": (
                self.history[-1]
                if self.history
                else None
            ),
        }