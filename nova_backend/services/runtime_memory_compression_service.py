class RuntimeMemoryCompressionService:
    def __init__(
        self,
        max_raw_events=100,
    ):
        self.max_raw_events = max_raw_events

    def _safe_dict(
        self,
        value,
    ):
        return (
            value
            if isinstance(value, dict)
            else {}
        )

    def _safe_list(
        self,
        value,
    ):
        return (
            value
            if isinstance(value, list)
            else []
        )

    def _signature(
        self,
        event,
    ):
        event = self._safe_dict(event)

        execution_summary = self._safe_dict(
            event.get("execution_summary")
        )

        execution_state = self._safe_dict(
            event.get("execution_state")
        )

        return "|".join(
            [
                str(
                    event.get("type")
                    or "unknown"
                ),
                str(
                    execution_summary.get("status")
                    or "unknown"
                ),
                str(
                    execution_summary.get("failed_count")
                    or 0
                ),
                str(
                    execution_summary.get("completed_count")
                    or 0
                ),
                str(
                    execution_state.get("runtime_signal")
                    or "none"
                ),
                str(
                    execution_state.get("governed_action")
                    or "none"
                ),
                str(
                    execution_state.get("healing_mode")
                    or "none"
                ),
            ]
        )

    def compress(
        self,
        memory=None,
    ):
        memory = self._safe_dict(memory)

        events = self._safe_list(
            memory.get("events")
        )

        groups = {}

        for event in events:

            event = self._safe_dict(event)

            signature = self._signature(event)

            if signature not in groups:
                groups[signature] = {
                    "signature": signature,
                    "count": 0,
                    "first_event": event,
                    "last_event": event,
                }

            groups[signature]["count"] += 1
            groups[signature]["last_event"] = event

        compressed_patterns = list(
            groups.values()
        )

        compressed_patterns.sort(
            key=lambda item: item.get(
                "count",
                0,
            ),
            reverse=True,
        )

        raw_events = events[
            -self.max_raw_events:
        ]

        return {
            "ok": True,
            "raw_event_count": len(events),
            "stored_raw_event_count": len(raw_events),
            "compressed_pattern_count": len(
                compressed_patterns
            ),
            "compressed_patterns": compressed_patterns,
            "events": raw_events,
        }