class FailureAnalyzerService:

    def analyze(
        self,
        execution_result=None,
    ):

        execution_result = (
            execution_result
            if isinstance(execution_result, dict)
            else {}
        )

        stderr = str(
            execution_result.get("stderr") or ""
        )

        error = str(
            execution_result.get("error") or ""
        )

        combined = (
            stderr
            + "\n"
            + error
        ).lower()

        if "syntaxerror" in combined:
            return {
                "ok": True,
                "failure_type": "syntax_error",
                "recovery_strategy": (
                    "repair_python_syntax"
                ),
            }

        if "indentationerror" in combined:
            return {
                "ok": True,
                "failure_type": "indentation_error",
                "recovery_strategy": (
                    "repair_indentation"
                ),
            }

        if "modulenotfounderror" in combined:
            return {
                "ok": True,
                "failure_type": "missing_module",
                "recovery_strategy": (
                    "install_or_replace_dependency"
                ),
            }

        if "filenotfounderror" in combined:
            return {
                "ok": True,
                "failure_type": "missing_file",
                "recovery_strategy": (
                    "create_missing_file"
                ),
            }

        if "zerodivisionerror" in combined:
            return {
                "ok": True,
                "failure_type": "logic_error",
                "recovery_strategy": (
                    "add_input_validation"
                ),
            }

        return {
            "ok": True,
            "failure_type": "unknown",
            "recovery_strategy": (
                "request_llm_analysis"
            ),
        }

