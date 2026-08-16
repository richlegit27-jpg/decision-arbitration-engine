class FailureRecovery:


    def __init__(self):

        self.failures = []



    def handle(
        self,
        error,
        context=None,
    ):

        failure = {
            "error": str(error),
            "type": self._classify(error),
            "action": None,
            "recovered": False,
            "context": context or {},
        }


        failure["action"] = (
            self._choose_action(
                failure["type"]
            )
        )


        failure["recovered"] = (
            failure["action"]
            != "stop"
        )


        self.failures.append(
            failure
        )


        return failure



    def _classify(
        self,
        error,
    ):

        text = str(error).lower()


        if "timeout" in text:
            return "timeout"


        if "connection" in text:
            return "connection"


        if "not found" in text:
            return "missing_resource"


        if "permission" in text:
            return "permission"


        return "unknown"



    def _choose_action(
        self,
        failure_type,
    ):

        actions = {

            "timeout":
                "retry",

            "connection":
                "reconnect",

            "missing_resource":
                "request_missing_input",

            "permission":
                "request_authorization",

            "unknown":
                "safe_fallback",
        }


        return actions.get(
            failure_type,
            "stop",
        )



    def history(self):

        return self.failures