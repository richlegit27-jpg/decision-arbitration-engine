from nova_backend.services.execution_handler import NextMove


class RepairExecutionService:

    def __init__(self, execution_handler):
        self.execution_handler = execution_handler

    def _safe_str(self, value):
        return str(value or "")

    def _attempt_function_self_fix(
        self, session_id: str, active_task: str, error_text: str
    ) -> str:
        """
        Safer self-fix path for function-scoped repairs.
        """

        session_id = self._safe_str(session_id).strip() or "default"
        active_task = self._safe_str(active_task).strip()
        error_text = self._safe_str(error_text).strip()

        if not active_task:
            return "Function self-fix skipped: no active task."

        try:
            fix_move = NextMove(
                id=f"{session_id}:function_auto_fix",
                type="apply_function_fix",
                payload={
                    "target": active_task,
                    "error": error_text,
                },
            )

            results = self.execution_handler.run_chain(fix_move)
            last = results[-1] if results else None

            if last and last.status == "success":
                return str(last.output)

            if last:
                return f"Function auto-fix failed:\n{last.error}"

            return "Function auto-fix produced no result."

        except Exception as e:
            return f"Function auto-fix exception:\n{str(e)}"

    def _attempt_self_fix(
        self, session_id: str, active_task: str, error_text: str
    ) -> str:
        """
        Smart self-fix dispatcher.
        Tries safer function-level fix first, then falls back to file-level fix.
        """

        session_id = self._safe_str(session_id).strip() or "default"
        active_task = self._safe_str(active_task).strip()
        error_text = self._safe_str(error_text).strip()

        if not active_task:
            return "Auto-fix skipped: no active task."

        error_kind = self._classify_execution_error(error_text)

        if error_kind in {"import", "missing_file"}:
            return (
                f"Auto-fix paused: {error_kind} error needs file/dependency context.\n\n"
                f"Error:\n{error_text}"
            )

        function_fix_result = self._attempt_function_self_fix(
            session_id=session_id,
            active_task=active_task,
            error_text=error_text,
        )

        if (
            "failed" not in function_fix_result.lower()
            and "exception" not in function_fix_result.lower()
        ):
            return function_fix_result

        try:
            fix_move = NextMove(
                id=f"{session_id}:file_auto_fix",
                type="apply_file_fix",
                payload={
                    "file_path": active_task,
                    "content": error_text,
                },
            )

            results = self.execution_handler.run_chain(fix_move)
            last = results[-1] if results else None

            if last and last.status == "success":
                return str(last.output)

            if last:
                return (
                    "Function auto-fix failed, then file auto-fix failed:\n\n"
                    f"Function result:\n{function_fix_result}\n\n"
                    f"File error:\n{last.error}"
                )

            return (
                "Function auto-fix failed, then file auto-fix produced no result.\n\n"
                f"Function result:\n{function_fix_result}"
            )

        except Exception as e:
            return (
                "Function auto-fix failed, then file auto-fix raised an exception:\n\n"
                f"Function result:\n{function_fix_result}\n\n"
                f"File exception:\n{str(e)}"
            )