class RecoveryBridge:


    def __init__(
        self,
        recovery_system=None,
    ):

        self.recovery_system = (
            recovery_system
        )

        self.failures = []



    def handle(
        self,
        error,
        context=None,
    ):

        failure = {

            "error": str(error),

            "context": context or {},

            "action": "fallback",

            "recovered": False,

        }


        self.failures.append(
            failure
        )


        if self.recovery_system:

            try:

                result = (
                    self.recovery_system.handle(
                        error,
                        context,
                    )
                )

                if isinstance(
                    result,
                    dict,
                ):

                    failure.update(
                        result
                    )

            except Exception as exc:

                failure["recovery_error"] = (
                    str(exc)
                )


        else:

            failure["action"] = (
                "safe_fallback"
            )

            failure["recovered"] = True


        return failure



    def history(
        self,
    ):

        return self.failures