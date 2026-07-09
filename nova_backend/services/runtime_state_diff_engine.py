class RuntimeStateDiffEngine:

    def compare(
        self,
        before_state=None,
        after_state=None,
    ):

        before_state = (
            before_state
            if isinstance(before_state, dict)
            else {}
        )

        after_state = (
            after_state
            if isinstance(after_state, dict)
            else {}
        )

        changes = {}

        keys = set(
            list(before_state.keys())
            + list(after_state.keys())
        )

        for key in keys:

            before_value = before_state.get(key)
            after_value = after_state.get(key)

            if before_value != after_value:

                changes[key] = {
                    "before": before_value,
                    "after": after_value,
                }

        severity = len(changes)

        return {
            "ok": True,
            "change_count": severity,
            "changes": changes,
        }

