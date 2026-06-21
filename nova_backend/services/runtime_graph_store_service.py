# RUNTIME_GRAPH_TIMEZONE_UTC_LOCK
import json
import os
from datetime import datetime, timezone

from nova_backend.services.runtime_memory_compression_service import (
    RuntimeMemoryCompressionService,
)

class RuntimeGraphStoreService:
    def __init__(
        self,
        path=None,
        max_events=250,
    ):
        self.path = (
            path
            or os.path.join(
                "data",
                "runtime_graph_memory.json",
            )
        )

        self.max_events = max_events

        self.compressor = (
            RuntimeMemoryCompressionService(
                max_raw_events=max_events
            )
        )

    def _safe_dict(
        self,
        value,
    ):
        return (
            value
            if isinstance(value, dict)
            else {}
        )

    def load(
        self,
    ):
        if not os.path.exists(self.path):
            return {
                "events": [],
                "event_count": 0,
                "loaded_at": datetime.now(timezone.utc).isoformat(),
            }

        try:
            with open(
                self.path,
                "r",
                encoding="utf-8",
            ) as file:
                data = json.load(file)

            data = self._safe_dict(data)

            events = (
                data.get("events")
                if isinstance(data.get("events"), list)
                else []
            )

            return {
                "events": events[-self.max_events:],
                "event_count": len(events[-self.max_events:]),
                "loaded_at": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as exc:
            return {
                "events": [],
                "event_count": 0,
                "error": str(exc),
                "loaded_at": datetime.now(timezone.utc).isoformat(),
            }

    def save(
        self,
        memory=None,
    ):
        memory = self._safe_dict(memory)

        events = (
            memory.get("events")
            if isinstance(memory.get("events"), list)
            else []
        )

        events = events[-self.max_events:]

        compressed = self.compressor.compress(
            {
                "events": events,
            }
        )

        payload = {
            "events": compressed.get(
                "events",
                [],
            ),
            "event_count": len(
                compressed.get(
                    "events",
                    [],
                )
            ),
            "compressed_patterns": compressed.get(
                "compressed_patterns",
                [],
            ),
            "compressed_pattern_count": compressed.get(
                "compressed_pattern_count",
                0,
            ),
            "raw_event_count": compressed.get(
                "raw_event_count",
                0,
            ),
            "saved_at": datetime.now(timezone.utc).isoformat(),
        }

        folder = os.path.dirname(self.path)

        if folder:
            os.makedirs(
                folder,
                exist_ok=True,
            )

        with open(
            self.path,
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                payload,
                file,
                indent=2,
                ensure_ascii=False,
            )

        return {
            "ok": True,
            "path": self.path,
            "event_count": len(events),
        }

