class RetestLoopService:

    def __init__(
        self,
        tool_registry=None,
        failure_analyzer=None,
        patch_engine=None,
    ):

        self.tool_registry = tool_registry
        self.failure_analyzer = (
            failure_analyzer
        )
        self.patch_engine = (
            patch_engine
        )

    def attempt_recovery(
        self,
        target_file="",
        max_attempts=3,
    ):

        history = []

        for attempt in range(
            1,
            max_attempts + 1,
        ):

            run_result = (
                self.tool_registry.execute(
                    "run_python_file",
                    path=target_file,
                )
            )

            history.append({
                "attempt": attempt,
                "run_result": run_result,
            })

            if run_result.get("ok"):

                return {
                    "ok": True,
                    "attempts": attempt,
                    "history": history,
                    "final_result": run_result,
                }

            analysis = (
                self.failure_analyzer.analyze(
                    run_result
                )
            )

            history.append({
                "attempt": attempt,
                "analysis": analysis,
            })

            read_result = (
                self.tool_registry.execute(
                    "read_file",
                    path=target_file,
                )
            )

            if not read_result.get("ok"):

                return {
                    "ok": False,
                    "history": history,
                    "error": (
                        "Failed to read target "
                        "file during recovery."
                    ),
                }

            patch_result = (
                self.patch_engine.generate_patch(
                    failure_analysis=analysis,
                    target_file=target_file,
                    original_code=read_result.get(
                        "content",
                        "",
                    ),
                )
            )

            history.append({
                "attempt": attempt,
                "patch_result": patch_result,
            })

            if not patch_result.get("ok"):

                return {
                    "ok": False,
                    "history": history,
                    "error": (
                        "Patch generation failed."
                    ),
                }

            apply_result = (
                self.patch_engine.apply_patch(
                    target_file=target_file,
                    patched_code=patch_result.get(
                        "patched_code",
                        "",
                    ),
                )
            )

            history.append({
                "attempt": attempt,
                "apply_result": apply_result,
            })

            if not apply_result.get("ok"):

                return {
                    "ok": False,
                    "history": history,
                    "error": (
                        "Patch apply failed."
                    ),
                }

        return {
            "ok": False,
            "history": history,
            "error": (
                "Recovery attempts exhausted."
            ),
        }