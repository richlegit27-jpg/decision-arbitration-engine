class TelemetryBridge:


    def __init__(
        self,
        telemetry=None,
    ):

        self.telemetry = (
            telemetry
        )

        self.events = []



    def record(
        self,
        stage,
        data=None,
    ):

        event = {

            "stage": stage,

            "data": data or {},

        }


        self.events.append(
            event
        )


        if self.telemetry:

            try:

                self.telemetry.record(
                    stage,
                    data,
                )

            except Exception:

                pass


        return event



    def trace(
        self,
    ):

        return self.events



    def clear(
        self,
    ):

        self.events = []