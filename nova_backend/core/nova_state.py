from datetime import datetime


class NovaState:


    def __init__(
        self,
        session_id="",
        user_id="",
    ):

        self.session_id = session_id
        self.user_id = user_id

        self.session = {}

        self.memory = []

        self.execution = {}

        self.project = {}

        self.decisions = {}

        self.telemetry = []

        self.created_at = (
            datetime.utcnow().isoformat()
        )



    def update_session(
        self,
        data,
    ):

        if isinstance(data, dict):

            self.session.update(
                data
            )



    def update_memory(
        self,
        items,
    ):

        if isinstance(items, list):

            self.memory = items



    def update_execution(
        self,
        execution,
    ):

        if isinstance(execution, dict):

            self.execution = execution



    def update_project(
        self,
        project,
    ):

        if isinstance(project, dict):

            self.project = project



    def add_decision(
        self,
        name,
        value,
    ):

        self.decisions[name] = value



    def add_telemetry(
        self,
        event,
    ):

        self.telemetry.append(
            event
        )



    def export(
        self,
    ):

        return {

            "session_id":
                self.session_id,

            "user_id":
                self.user_id,

            "session":
                self.session,

            "memory":
                self.memory,

            "execution":
                self.execution,

            "project":
                self.project,

            "decisions":
                self.decisions,

            "telemetry":
                self.telemetry,

            "created_at":
                self.created_at,
        }