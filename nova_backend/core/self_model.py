class SelfModel:


    def __init__(self):
        self.state = {
            "identity": "Nova",
            "purpose": "assist and execute goals",
            "current_goal": None,
            "active_task": None,
            "confidence": 0,
            "observations": [],
            "lessons": [],
        }



    def update_state(
        self,
        goal=None,
        task=None,
        confidence=None,
    ):

        if goal:
            self.state["current_goal"] = goal

        if task:
            self.state["active_task"] = task

        if confidence is not None:
            self.state["confidence"] = confidence


        return self.state



    def observe(
        self,
        event,
    ):

        observation = {
            "event": event,
            "timestamp": self._timestamp(),
        }

        self.state["observations"].append(
            observation
        )

        return observation



    def learn(
        self,
        lesson,
    ):

        self.state["lessons"].append(
            lesson
        )

        return {
            "learned": lesson
        }



    def introspect(self):

        return {
            "current_state": self.state,
            "status": "active",
        }



    def _timestamp(self):

        import datetime

        return (
            datetime.datetime
            .now()
            .isoformat()
        )