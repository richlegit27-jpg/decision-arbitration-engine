import json

class WorkingStateService:

    def __init__(self, session_service):
        self.session_service = session_service

    def get_working_state(self, session_id):
        try:
            session = self.session_service.get_session(
                session_id
            )

            if not isinstance(session, dict):
                return {}

            state = session.get("working_state")

            return self.normalize_working_state(
                state
            )

        except Exception:
            return {}


    def update_working_state(
        self,
        session_id,
        patch,
    ):
        current = self.get_working_state(
            session_id
        )

        if not isinstance(patch, dict):
            patch = {}

        merged = dict(current)
        merged.update(patch)

        clean_state = self.normalize_working_state(
            merged
        )

        self.set_working_state(
            session_id,
            clean_state,
        )

        return clean_state
    def set_working_state(
        self,
        session_id,
        state,
    ):
        clean_state = self.normalize_working_state(
            state
        )

        self.session_service.update_working_state(
            session_id,
            clean_state,
        )

        return clean_state

    def normalize_working_state(
        self,
        working_state,
    ):
        if isinstance(working_state, dict):
            return working_state

        if working_state is None:
            return {}

        if isinstance(working_state, str):
            try:
                parsed = json.loads(
                    working_state
                )

                return (
                    parsed
                    if isinstance(parsed, dict)
                    else {}
                )

            except Exception:
                return {}

        return {}





