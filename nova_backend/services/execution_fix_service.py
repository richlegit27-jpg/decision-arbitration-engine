import uuid


class ExecutionFixService:

    def __init__(
        self,
        session_service,
        default_executor,
        next_move_class,
        update_execution_state_safe,
    ):
        self.session_service = session_service
        self.default_executor = default_executor
        self.NextMove = next_move_class
        self.update_execution_state_safe = update_execution_state_safe

    def apply_fix(
        self,
        session_id,
        session,
        execution,
        action,
    ):
        pending_file = ""
        pending_code = ""

        try:
            session = (
                self.session_service.get_session(session_id)
                or {}
            )

            working_state = (
                session.get("working_state", {})
                if isinstance(session, dict)
                else {}
            )

            meta = (
                session.get("meta", {})
                if isinstance(session, dict)
                else {}
            )

            pending_file = str(
                working_state.get("pending_fix_file_path")
                or meta.get("pending_fix_file_path")
                or ""
            ).strip()

            pending_code = str(
                working_state.get("pending_fix_code")
                or meta.get("pending_fix_code")
                or ""
            )

        except Exception:
            pending_file = ""
            pending_code = ""

        step = {
            "title": "Apply pending file fix",
            "status": "running",
            "move": {
                "id": f"fix-file-{uuid.uuid4().hex}",
                "type": "fix_file",
                "payload": {
                    "file_path": pending_file,
                    "code": pending_code,
                },
            },
        }

        execution["status"] = "running"
        execution["current_step"] = step["title"]
        execution["last_action"] = action
        execution.setdefault("steps", []).append(step)

        result = self.default_executor(
            self.NextMove(
                id=step["move"]["id"],
                type="fix_file",
                payload=step["move"]["payload"],
            )
        )

        ok = str(
            result.status or ""
        ).lower() == "success"

        step["status"] = (
            "done"
            if ok
            else "failed"
        )

        step["output"] = (
            result.output
            or {
                "error": result.error,
            }
        )

        self.update_execution_state_safe(
            execution,
            status=(
                "complete"
                if ok
                else "error"
            ),
        )

        self.update_execution_state_safe(
            execution,
            current_step=(
                "Fix applied"
                if ok
                else "Fix failed"
            ),
        )

        execution.setdefault(
            "history",
            [],
        ).append(
            f"fix_file: {'success' if ok else 'failed'}"
        )

        return {
            "ok": ok,
            "step": step,
            "execution": execution,
        }