class ExecutionGuardService:

    def __init__(self, chat_execution_service):
        self.chat_execution_service = chat_execution_service

    def handle(self, payload):
        if not isinstance(payload, dict):
            return None

        user_text = str(
            payload.get("user_text")
            or payload.get("text")
            or payload.get("message")
            or ""
        ).strip()

        clean = " ".join(user_text.lower().split())

        session_id = str(
            payload.get("session_id")
            or payload.get("client_session_id")
            or "default"
        ).strip() or "default"

        if clean in {
            "status",
            "execution status",
            "mission status",
        }:
            state = self.chat_execution_service.get_state(session_id)
            reply = self.chat_execution_service.format_reply(state)

            return {
                "ok": True,
                "text": reply,
                "assistant_message": {
                    "role": "assistant",
                    "text": reply,
                    "content": reply,
                    "execution_state": state,
                    "attachments": [],
                },
                "execution_state": state,
                "skip_cleanup": True,
                "skip_post_processing": True,
                "skip_rewrite": True,
            }

        if clean.startswith("auto-plan "):
            goal = user_text.split("auto-plan", 1)[1].strip()

            steps = [
                "Inspect the mission and identify the likely target files",
                "Make the smallest safe implementation change",
                "Verify the result and report the next move",
            ]

            goal_lower = goal.lower()

            if (
                "web" in goal_lower
                or "fetch" in goal_lower
                or "search" in goal_lower
            ):
                steps = [
                    "Inspect the web fetch route, ranking path, and displayed source output",
                    "Patch the smallest mismatch between backend fetch results and UI/session output",
                    "Verify fresh search results, source ordering, and displayed cards",
                ]

            elif (
                "memory" in goal_lower
                or "recall" in goal_lower
            ):
                steps = [
                    "Inspect memory write, ranking, and recall injection path",
                    "Patch the smallest issue blocking correct memory recall",
                    "Verify recall with a direct follow-up prompt",
                ]

            elif (
                "execution" in goal_lower
                or "plan" in goal_lower
            ):
                steps = [
                    "Inspect execution state, trigger routing, and durable save file",
                    "Patch the smallest issue in mission start or step advancement",
                    "Verify auto-plan, k, next, continue, and completion behavior",
                ]

            state = self.chat_execution_service.start(
                session_id,
                goal,
                steps,
            )

            reply = (
                "Execution mission started: "
                + goal
                + "\n\n"
                + "Step 1/3: "
                + str(
                    state.get("current_step")
                    or steps[0]
                )
                + "\n\n"
                + "Send k, next, continue, or run it to advance."
            )

            return {
                "ok": True,
                "text": reply,
                "assistant_message": {
                    "role": "assistant",
                    "text": reply,
                    "content": reply,
                    "execution_state": state,
                    "attachments": [],
                },
                "execution_state": state,
                "skip_cleanup": True,
                "skip_post_processing": True,
                "skip_rewrite": True,
            }

        if clean in {
            "k",
            "ok",
            "okay",
            "next",
            "continue",
            "run it",
            "run step",
            "execute",
            "go",
            "advance",
        }:
            current_state = self.chat_execution_service.get_state(
                session_id
            )
            print("[EXEC_DEBUG_STATE]", current_state)

            if isinstance(current_state, dict):
                current_status = str(
                    current_state.get("status")
                    or ""
                ).lower()

                if current_status in {
                    "idle",
                    "stopped",
                    "complete",
                    "completed",
                    "waiting",
                }:
                    reply = self.chat_execution_service.format_reply(
                        current_state
                    )

                    return {
                        "ok": True,
                        "text": reply,
                        "assistant_message": {
                            "role": "assistant",
                            "text": reply,
                            "content": reply,
                            "execution_state": current_state,
                            "attachments": [],
                        },
                        "execution_state": current_state,
                        "skip_cleanup": True,
                        "skip_post_processing": True,
                        "skip_rewrite": True,
                    }


            state = self.chat_execution_service.advance(
                session_id
            )

            reply = self.chat_execution_service.format_reply(
                state
            )

            return {
                "ok": True,
                "text": reply,
                "assistant_message": {
                    "role": "assistant",
                    "text": reply,
                    "content": reply,
                    "execution_state": state,
                    "attachments": [],
                },
                "execution_state": state,
                "skip_cleanup": True,
                "skip_post_processing": True,
                "skip_rewrite": True,
            }

        return None