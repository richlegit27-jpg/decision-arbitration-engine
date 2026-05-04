import threading
import time


class ExecutionDaemon:
    def __init__(self, chat_service, interval_seconds: int = 3):
        self.chat_service = chat_service
        self.interval_seconds = interval_seconds
        self._running = False
        self._thread = None
        self._lock = threading.Lock()
        self._active_sessions = set()

    def start(self):
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(
            target=self._loop,
            daemon=True,
        )
        self._thread.start()

    def stop(self):
        self._running = False

    def _loop(self):
        while self._running:
            try:
                self.tick()
            except Exception as exc:
                print("[EXECUTION_DAEMON_ERROR]", repr(exc))

            time.sleep(self.interval_seconds)

    def tick(self):
        sessions = getattr(self.chat_service, "sessions", None)

        if not sessions:
            return

        all_sessions = sessions.load_sessions()

        for session in all_sessions:
            session_id = session.get("id")
            meta = session.get("meta") or {}
            execution_state = meta.get("execution_state") or {}

            if not session_id:
                continue

            if not execution_state:
                continue

            if execution_state.get("status") == "complete":
                continue

            if execution_state.get("waiting"):
                continue

            if not self._claim_session(session_id):
                continue

            try:
                execution_state["daemon_running"] = True
                self.chat_service._set_session_meta(
                    session_id,
                    "execution_state",
                    execution_state,
                )

                updated_state = self.chat_service._process_execution(
                    execution_state,
                    session_id,
                )

                updated_state["daemon_running"] = False

                self.chat_service._set_session_meta(
                    session_id,
                    "execution_state",
                    updated_state,
                )

            except Exception as exc:
                execution_state["daemon_running"] = False
                execution_state["waiting"] = True
                execution_state["last_error"] = repr(exc)

                self.chat_service._set_session_meta(
                    session_id,
                    "execution_state",
                    execution_state,
                )

                print("[EXECUTION_DAEMON_SESSION_ERROR]", session_id, repr(exc))

            finally:
                self._release_session(session_id)

    def _claim_session(self, session_id: str) -> bool:
        with self._lock:
            if session_id in self._active_sessions:
                return False

            self._active_sessions.add(session_id)
            return True

    def _release_session(self, session_id: str):
        with self._lock:
            self._active_sessions.discard(session_id)