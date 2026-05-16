from datetime import datetime


class WorldStateService:

    def __init__(self):

        self.state = {
            "active_missions": [],
            "active_files": [],
            "recent_errors": [],
            "successful_repairs": [],
            "tool_history": [],
            "project_map": {},
            "execution_history": [],
            "environment_health": {},
            "last_updated": None,
        }

    def update_state(
        self,
        key="",
        value=None,
    ):

        if not key:
            return

        self.state[key] = value

        self.state[
            "last_updated"
        ] = (
            datetime.utcnow()
            .isoformat()
        )

    def append_state(
        self,
        key="",
        value=None,
    ):

        if key not in self.state:
            self.state[key] = []

        if not isinstance(
            self.state[key],
            list,
        ):
            return

        self.state[key].append(value)

        self.state[
            "last_updated"
        ] = (
            datetime.utcnow()
            .isoformat()
        )

    def get_state(self):

        return self.state

    def summarize(self):

        return {
            "missions": len(
                self.state.get(
                    "active_missions",
                    [],
                )
            ),
            "files": len(
                self.state.get(
                    "active_files",
                    [],
                )
            ),
            "errors": len(
                self.state.get(
                    "recent_errors",
                    [],
                )
            ),
            "repairs": len(
                self.state.get(
                    "successful_repairs",
                    [],
                )
            ),
            "tool_events": len(
                self.state.get(
                    "tool_history",
                    [],
                )
            ),
            "last_updated": (
                self.state.get(
                    "last_updated"
                )
            ),
        }