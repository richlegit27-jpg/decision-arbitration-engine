class SystemHealth:


    def __init__(self):

        self.status = {
            "system": "healthy",
            "checks": {},
        }



    def check(
        self,
        services=None,
    ):

        services = services or {}


        results = {}


        for name, service in services.items():

            try:

                alive = service is not None

                results[name] = {
                    "available": alive,
                    "status": (
                        "ok"
                        if alive
                        else "missing"
                    ),
                }


            except Exception as exc:

                results[name] = {
                    "available": False,
                    "status": "error",
                    "error": str(exc),
                }


        self.status["checks"] = results


        self.status["system"] = (
            "healthy"
            if all(
                x["available"]
                for x in results.values()
            )
            else "degraded"
        )


        return self.status



    def report(self):

        return self.status