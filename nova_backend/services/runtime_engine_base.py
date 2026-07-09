import time
import uuid


class RuntimeEngineBase:
    def __init__(
        self,
        name="runtime_engine",
        tags=None,
    ):
        self.name = name
        self.tags = tags or []
        self.engine_id = str(uuid.uuid4())
        self.created_at = time.time()
        self.last_result = None
        self.run_count = 0
        self.failure_count = 0
        self.success_count = 0

    def _now(self):
        return time.time()

    def _safe_dict(self, value):
        return value if isinstance(value, dict) else {}

    def _safe_list(self, value):
        return value if isinstance(value, list) else []

    def _safe_str(self, value):
        return str(value or "").strip()

    def run(self, context=None):
        context = self._safe_dict(context)

        self.run_count += 1

        try:
            result = self.execute(context=context)

            if not isinstance(result, dict):
                result = {
                    "ok": True,
                    "result": result,
                }

            if result.get("ok"):
                self.success_count += 1
            else:
                self.failure_count += 1

            result["engine"] = self.name
            result["engine_id"] = self.engine_id
            result["ran_at"] = self._now()

            self.last_result = result

            return result

        except Exception as exc:
            self.failure_count += 1

            result = {
                "ok": False,
                "engine": self.name,
                "engine_id": self.engine_id,
                "error": str(exc),
                "ran_at": self._now(),
            }

            self.last_result = result

            return result

    def execute(self, context=None):
        return {
            "ok": True,
            "engine": self.name,
            "message": "Base engine executed.",
            "context": self._safe_dict(context),
        }

    def status(self):
        return {
            "name": self.name,
            "engine_id": self.engine_id,
            "tags": self.tags,
            "created_at": self.created_at,
            "run_count": self.run_count,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "last_result": self.last_result,
        }

