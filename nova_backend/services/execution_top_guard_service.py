class ExecutionTopGuardService:

    def _get_user_text(self, payload):
        if not isinstance(payload, dict):
            return ""

        return str(
            payload.get("user_text")
            or payload.get("text")
            or payload.get("message")
            or ""
        ).strip()

    def _is_execution_request(
        self,
        user_text,
        chat_execution_service,
    ):
        if not user_text:
            return False

        try:
            detector = getattr(
                chat_execution_service,
                "is_execution_trigger",
                None,
            )

            if callable(detector):
                if detector(user_text):
                    return True

        except Exception:
            pass

        text = user_text.lower()

        execution_markers = (
            "run all",
            "run all steps",
            "run the steps",
            "execute all",
            "execute all steps",
            "carry out",
            "perform the steps",
            "complete the steps",
            "continue execution",
            "start execution",
        )

        return any(
            marker in text
            for marker in execution_markers
        )

    def handle(
        self,
        payload,
        session_id,
        chat_execution_service=None,
        execution_bridge_service=None,
        **services,
    ):
        print(
            "[TOP EXECUTION GUARD ENTERED]",
            repr(payload),
            flush=True,
        )

        if not isinstance(payload, dict):
            return {
                "handled": False,
            }

        if chat_execution_service is None:
            return {
                "handled": False,
            }

        user_text = self._get_user_text(
            payload
        )

        if not self._is_execution_request(
            user_text,
            chat_execution_service,
        ):
            return {
                "handled": False,
            }

        safe_session_id = str(
            session_id
            or payload.get("session_id")
            or "default"
        ).strip() or "default"

        try:
            state = chat_execution_service.get_state(
                safe_session_id
            )

            status = str(
                state.get("status")
                or ""
            ).lower().strip()

            has_active_execution = (
                status in (
                    "running",
                    "paused",
                    "waiting_approval",
                    "ready",
                )
                or bool(state.get("steps"))
                or bool(state.get("current_step"))
            )

            if has_active_execution:
                result = chat_execution_service.run_all(
                    safe_session_id
                )

                reply_text = (
                    chat_execution_service.format_reply(
                        result
                    )
                )

                return {
                    "handled": True,
                    "response": {
                        "ok": True,
                        "session_id": safe_session_id,
                        "execution": result,
                        "execution_state": result,
                        "text": reply_text,
                        "assistant_message": {
                            "role": "assistant",
                            "text": reply_text,
                            "content": reply_text,
                        },
                        "debug": {
                            "route": "execution",
                            "route_taken": (
                                "execution_top_guard_run_all"
                            ),
                        },
                    },
                }

            if execution_bridge_service is not None:

                # No active mission exists.
                # Try to create one before attempting
                # to advance an existing mission.
                bridge_result = (
                    execution_bridge_service
                    .try_execution_autoplan_start(
                        safe_session_id,
                        user_text,
                    )
                )

                if bridge_result is not None:
                    return {
                        "handled": True,
                        "response": bridge_result,
                    }

                bridge_result = (
                    execution_bridge_service
                    .try_execution_trigger(
                        safe_session_id,
                        user_text,
                    )
                )

                if bridge_result is not None:
                    return {
                        "handled": True,
                        "response": bridge_result,
                    }

            return {
                "handled": False,
            }

        except Exception as exc:
            return {
                "handled": True,
                "response": {
                    "ok": False,
                    "session_id": safe_session_id,
                    "error": str(exc),
                    "debug": {
                        "route": "execution",
                        "route_taken": (
                            "execution_top_guard_error"
                        ),
                    },
                },
            }


execution_top_guard_service = ExecutionTopGuardService()