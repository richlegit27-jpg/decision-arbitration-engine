from datetime import datetime


class CognitiveScheduler:

    def __init__(self):

        self.queue = []

    def add_task(
        self,
        execution_state=None,
        priority=5,
    ):

        execution_state = (
            execution_state
            if isinstance(
                execution_state,
                dict,
            )
            else {}
        )

        task = {
            "execution_state": (
                execution_state
            ),
            "priority": priority,
            "created_at": (
                datetime.utcnow()
                .isoformat()
            ),
            "status": "queued",
        }

        self.queue.append(task)

        self.queue.sort(
            key=lambda t: t.get(
                "priority",
                999,
            )
        )

        return {
            "ok": True,
            "task": task,
        }

    def get_next_task(self):

        queued = [
            t
            for t in self.queue
            if t.get("status")
            == "queued"
        ]

        if not queued:
            return None

        task = queued[0]

        task["status"] = (
            "running"
        )

        return task

    def complete_task(
        self,
        task=None,
    ):

        if not isinstance(task, dict):
            return

        task["status"] = (
            "completed"
        )

    def fail_task(
        self,
        task=None,
        error="",
    ):

        if not isinstance(task, dict):
            return

        task["status"] = "failed"

        task["error"] = error

    def summarize(self):

        return {
            "queued": len([
                t
                for t in self.queue
                if t.get("status")
                == "queued"
            ]),
            "running": len([
                t
                for t in self.queue
                if t.get("status")
                == "running"
            ]),
            "completed": len([
                t
                for t in self.queue
                if t.get("status")
                == "completed"
            ]),
            "failed": len([
                t
                for t in self.queue
                if t.get("status")
                == "failed"
            ]),
        }

