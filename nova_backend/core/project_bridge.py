class ProjectBridge:


    def __init__(
        self,
        project_brain=None,
        working_state_service=None,
    ):

        self.project_brain = (
            project_brain
        )

        self.working_state_service = (
            working_state_service
        )



    def load(
        self,
        session_id="",
    ):

        project_state = {

            "project": {},

            "working_state": {},

        }


        if self.project_brain:

            try:

                project = (
                    self.project_brain.get_state()
                )

                if isinstance(
                    project,
                    dict,
                ):

                    project_state["project"] = (
                        project
                    )

            except Exception as exc:

                project_state["project_error"] = (
                    str(exc)
                )



        if self.working_state_service:

            try:

                working = (
                    self.working_state_service.get(
                        session_id
                    )
                )

                if isinstance(
                    working,
                    dict,
                ):

                    project_state[
                        "working_state"
                    ] = working


            except Exception as exc:

                project_state[
                    "working_state_error"
                ] = str(exc)


        return project_state