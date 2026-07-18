class HistoryService:

    def __init__(self, session_history_service):
        self.session_history_service = session_history_service


    def load_sessions(self):
        store = self.session_history_service.load_sessions_store()

        if isinstance(store, dict):
            sessions = store.get("sessions", [])
        else:
            sessions = store

        if not isinstance(sessions, list):
            return []

        return [
            session
            for session in sessions
            if isinstance(session, dict)
        ]


    def sid(self, session):
        return str(
            session.get("id")
            or session.get("session_id")
            or ""
        )


    def title(self, session):
        return str(
            session.get("title")
            or "Untitled Session"
        )


    def messages(self, session):
        value = session.get("messages")

        if isinstance(value, list):
            return value

        return []


    def msg_text(self, message):
        if not isinstance(message, dict):
            return ""

        return str(
            message.get("content")
            or message.get("text")
            or ""
        )


    def msg_role(self, message):
        if not isinstance(message, dict):
            return ""

        return str(
            message.get("role")
            or ""
        )