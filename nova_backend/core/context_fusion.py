class ContextFusionEngine:


    def __init__(
        self,
        memory=None,
        brain_state=None,
        knowledge_graph=None,
    ):

        self.memory = memory
        self.brain_state = brain_state
        self.knowledge_graph = knowledge_graph



    def build(
        self,
        user_text,
        session_context=None,
    ):

        fused = {
            "user_request": user_text,
            "conversation": {},
            "memory": [],
            "brain_state": {},
            "knowledge": [],
            "active_context": {},
        }


        if session_context:
            fused["conversation"] = session_context



        if self.memory:

            try:
                fused["memory"] = (
                    self.memory.get_memory()
                )

            except Exception:
                fused["memory"] = []



        if self.brain_state:

            try:
                fused["brain_state"] = (
                    self.brain_state.get_state()
                )

            except Exception:
                fused["brain_state"] = {}



        if self.knowledge_graph:

            try:
                fused["knowledge"] = (
                    self.knowledge_graph.search(
                        user_text
                    )
                )

            except Exception:
                fused["knowledge"] = []


        fused["active_context"] = (
            self._summarize_context(
                fused
            )
        )


        return fused



    def _summarize_context(
        self,
        fused,
    ):

        return {
            "has_memory": bool(
                fused["memory"]
            ),
            "has_history": bool(
                fused["conversation"]
            ),
            "has_knowledge": bool(
                fused["knowledge"]
            ),
        }