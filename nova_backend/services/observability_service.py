import copy
import json
import time
import uuid


class ObservabilityService:
    def __init__(self, max_events=500):
        self.max_events = max_events
        self.events = []
        self.traces = {}

    def _now(self):
        return time.time()

    def _clone(self, value):
        try:
            return copy.deepcopy(value)
        except Exception:
            return value

    def _json_safe(self, value):
        try:
            json.dumps(value)
            return value
        except Exception:
            return str(value)

    def start_trace(self, trace_type="runtime_cycle", payload=None):
        trace_id = str(uuid.uuid4())

        trace = {
            "trace_id": trace_id,
            "type": trace_type,
            "started_at": self._now(),
            "ended_at": None,
            "events": [],
            "payload": self._json_safe(payload or {}),
            "status": "running",
        }

        self.traces[trace_id] = trace

        self.emit(
            event_type="trace_started",
            trace_id=trace_id,
            payload={
                "trace_type": trace_type,
            },
        )

        return trace_id

    def end_trace(self, trace_id, status="completed", payload=None):
        trace = self.traces.get(trace_id)

        if not trace:
            return None

        trace["ended_at"] = self._now()
        trace["status"] = status
        trace["final_payload"] = self._json_safe(payload or {})

        self.emit(
            event_type="trace_ended",
            trace_id=trace_id,
            payload={
                "status": status,
            },
        )

        return trace

    def emit(self, event_type, trace_id=None, payload=None):
        event = {
            "event_id": str(uuid.uuid4()),
            "type": event_type,
            "trace_id": trace_id,
            "timestamp": self._now(),
            "payload": self._json_safe(payload or {}),
        }

        self.events.append(event)
        self.events = self.events[-self.max_events:]

        if trace_id and trace_id in self.traces:
            self.traces[trace_id]["events"].append(event)

        return event

    def record_decision(
        self,
        trace_id,
        input_text=None,
        route=None,
        brain_state=None,
        decision=None,
        final_action=None,
    ):
        return self.emit(
            event_type="decision_trace",
            trace_id=trace_id,
            payload={
                "input_text": input_text,
                "route": route,
                "brain_state": self._clone(brain_state),
                "decision": self._clone(decision),
                "final_action": final_action,
            },
        )

    def record_execution(
        self,
        trace_id,
        step=None,
        before_state=None,
        after_state=None,
        result=None,
    ):
        return self.emit(
            event_type="execution_trace",
            trace_id=trace_id,
            payload={
                "step": self._clone(step),
                "before_state": self._clone(before_state),
                "after_state": self._clone(after_state),
                "result": self._clone(result),
            },
        )

    def record_graph_change(
        self,
        trace_id,
        before_graph=None,
        after_graph=None,
        reason=None,
    ):
        return self.emit(
            event_type="graph_trace",
            trace_id=trace_id,
            payload={
                "reason": reason,
                "before_graph": self._clone(before_graph),
                "after_graph": self._clone(after_graph),
            },
        )

    def get_trace(self, trace_id):
        return self.traces.get(trace_id)

    def recent_events(self, limit=50):
        return self.events[-limit:]

