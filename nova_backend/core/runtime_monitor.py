import time


class RuntimeMonitor:


    def __init__(self):

        self.events = []



    def start(
        self,
        operation,
    ):

        event = {
            "operation": operation,
            "started": time.time(),
        }

        self.events.append(event)

        return event



    def finish(
        self,
        event,
        success=True,
    ):

        event["finished"] = time.time()

        event["duration"] = (
            event["finished"]
            -
            event["started"]
        )

        event["success"] = success

        return event



    def recent(
        self,
        limit=50,
    ):

        return self.events[-limit:]