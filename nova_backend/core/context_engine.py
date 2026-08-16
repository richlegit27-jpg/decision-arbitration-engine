class ContextEngine:

    def build(
        self,
        session=None,
        memory=None,
        execution=None,
    ):

        return {
            "session": self._session(session),
            "memory": self._memory(memory),
            "execution": self._execution(execution),
        }


    def _session(self, session):

        if not isinstance(session, dict):
            return {}

        messages = session.get(
            "messages",
            []
        )

        return {
            "id": session.get("id"),
            "title": session.get("title"),
            "message_count": len(messages),
            "recent_messages": messages[-12:],
        }


    def _memory(self, memory):

        if not memory:
            return {
                "facts": []
            }

        return {
            "facts": memory
        }


    def _execution(self, execution):

        if not isinstance(execution, dict):
            return {}

        return {
            "goal": execution.get("goal",""),
            "status": execution.get("status",""),
            "steps": execution.get("steps",[]),
        }