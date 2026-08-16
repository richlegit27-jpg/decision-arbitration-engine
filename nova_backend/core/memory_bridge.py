class MemoryBridge:


    def __init__(
        self,
        memory_service=None,
    ):

        self.memory_service = (
            memory_service
        )



    def load(
        self,
        session_id="",
    ):

        if not self.memory_service:

            return []


        try:

            memories = (
                self.memory_service.get(
                    session_id
                )
            )

            if isinstance(
                memories,
                list,
            ):

                return memories


        except Exception as exc:

            print(
                "[MEMORY BRIDGE LOAD FAILED]",
                repr(exc),
            )


        return []



    def apply(
        self,
        nova_state,
        session_id="",
    ):

        memories = self.load(
            session_id
        )


        nova_state.update_memory(
            memories
        )


        return nova_state