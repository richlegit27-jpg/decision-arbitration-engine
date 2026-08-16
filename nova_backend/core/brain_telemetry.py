class BrainTelemetry:


    def __init__(self):

        self.events = []



    def record(
        self,
        stage,
        data=None,
    ):

        event = {
            "stage": stage,
            "data": data or {},
            "index": len(self.events),
        }


        self.events.append(
            event
        )


        return event



    def trace_request(
        self,
        request_id,
    ):

        return [
            event
            for event in self.events
            if event["data"].get(
                "request_id"
            ) == request_id
        ]



    def last_events(
        self,
        limit=20,
    ):

        return self.events[-limit:]



    def clear(self):

        self.events = []