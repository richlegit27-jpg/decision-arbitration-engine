import copy
import time
import uuid


class RuntimeReplayService:
    def __init__(self, max_replays=200):
        self.max_replays = max_replays
        self.replays = []

    def _safe_dict(self, value):
        return value if isinstance(value, dict) else {}

    def _safe_list(self, value):
        return value if isinstance(value, list) else []

    def _clone(self, value):
        try:
            return copy.deepcopy(value)
        except Exception:
            return value

    def _now(self):
        return time.time()

    def build_replay(
        self,
        trace=None,
        runtime_result=None,
    ):
        trace = self._safe_dict(trace)
        runtime_result = self._safe_dict(runtime_result)

        replay_id = str(uuid.uuid4())

        events = self._safe_list(trace.get("events"))

        replay = {
            "replay_id": replay_id,
            "trace_id": trace.get("trace_id"),
            "created_at": self._now(),
            "status": "created",
            "event_count": len(events),
            "events": self._clone(events),
            "runtime_result": self._clone(runtime_result),
            "summary": self.summarize_trace(trace),
        }

        self.replays.append(replay)
        self.replays = self.replays[-self.max_replays:]

        return replay

    def summarize_trace(self, trace):
        trace = self._safe_dict(trace)
        events = self._safe_list(trace.get("events"))

        event_types = []

        for event in events:
            if not isinstance(event, dict):
                continue

            event_type = event.get("type")

            if event_type and event_type not in event_types:
                event_types.append(event_type)

        return {
            "trace_id": trace.get("trace_id"),
            "type": trace.get("type"),
            "status": trace.get("status"),
            "event_count": len(events),
            "event_types": event_types,
            "started_at": trace.get("started_at"),
            "ended_at": trace.get("ended_at"),
        }

    def replay_events(self, replay):
        replay = self._safe_dict(replay)

        events = self._safe_list(replay.get("events"))

        output = []

        for index, event in enumerate(events):
            if not isinstance(event, dict):
                continue

            output.append(
                {
                    "index": index,
                    "event_id": event.get("event_id"),
                    "type": event.get("type"),
                    "trace_id": event.get("trace_id"),
                    "timestamp": event.get("timestamp"),
                    "payload": self._clone(event.get("payload")),
                }
            )

        return {
            "ok": True,
            "replay_id": replay.get("replay_id"),
            "trace_id": replay.get("trace_id"),
            "event_count": len(output),
            "events": output,
        }

    def inspect_decisions(self, replay):
        replay = self._safe_dict(replay)
        events = self._safe_list(replay.get("events"))

        decisions = []

        for event in events:
            if not isinstance(event, dict):
                continue

            if event.get("type") != "decision_trace":
                continue

            payload = self._safe_dict(event.get("payload"))

            decisions.append(
                {
                    "event_id": event.get("event_id"),
                    "trace_id": event.get("trace_id"),
                    "route": payload.get("route"),
                    "decision": self._clone(payload.get("decision")),
                    "final_action": payload.get("final_action"),
                    "brain_state": self._clone(payload.get("brain_state")),
                }
            )

        return {
            "ok": True,
            "replay_id": replay.get("replay_id"),
            "decision_count": len(decisions),
            "decisions": decisions,
        }

    def inspect_graph_changes(self, replay):
        replay = self._safe_dict(replay)
        events = self._safe_list(replay.get("events"))

        graph_changes = []

        for event in events:
            if not isinstance(event, dict):
                continue

            if event.get("type") != "graph_trace":
                continue

            payload = self._safe_dict(event.get("payload"))

            graph_changes.append(
                {
                    "event_id": event.get("event_id"),
                    "trace_id": event.get("trace_id"),
                    "reason": payload.get("reason"),
                    "before_graph": self._clone(payload.get("before_graph")),
                    "after_graph": self._clone(payload.get("after_graph")),
                }
            )

        return {
            "ok": True,
            "replay_id": replay.get("replay_id"),
            "graph_change_count": len(graph_changes),
            "graph_changes": graph_changes,
        }

    def inspect_execution_changes(self, replay):
        replay = self._safe_dict(replay)
        events = self._safe_list(replay.get("events"))

        execution_changes = []

        for event in events:
            if not isinstance(event, dict):
                continue

            if event.get("type") != "execution_trace":
                continue

            payload = self._safe_dict(event.get("payload"))

            execution_changes.append(
                {
                    "event_id": event.get("event_id"),
                    "trace_id": event.get("trace_id"),
                    "step": self._clone(payload.get("step")),
                    "before_state": self._clone(payload.get("before_state")),
                    "after_state": self._clone(payload.get("after_state")),
                    "result": self._clone(payload.get("result")),
                }
            )

        return {
            "ok": True,
            "replay_id": replay.get("replay_id"),
            "execution_change_count": len(execution_changes),
            "execution_changes": execution_changes,
        }

    def find_replay(self, replay_id=None, trace_id=None):
        for replay in reversed(self.replays):
            if replay_id and replay.get("replay_id") == replay_id:
                return replay

            if trace_id and replay.get("trace_id") == trace_id:
                return replay

        return None

    def recent_replays(self, limit=25):
        return self.replays[-limit:]

    def explain_replay(self, replay):
        replay = self._safe_dict(replay)

        decision_report = self.inspect_decisions(replay)
        graph_report = self.inspect_graph_changes(replay)
        execution_report = self.inspect_execution_changes(replay)

        return {
            "ok": True,
            "replay_id": replay.get("replay_id"),
            "trace_id": replay.get("trace_id"),
            "summary": self._clone(replay.get("summary")),
            "decision_report": decision_report,
            "graph_report": graph_report,
            "execution_report": execution_report,
        }

