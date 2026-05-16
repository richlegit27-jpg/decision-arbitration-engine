class RuntimeStateCommitService:

    def commit(
        self,
        execution_state=None,
        updates=None,
    ):
        execution_state = (
            execution_state.copy()
            if isinstance(execution_state, dict)
            else {}
        )

        updates = (
            updates
            if isinstance(updates, dict)
            else {}
        )

        changed_keys = []

        for key, value in updates.items():

            old_value = execution_state.get(key)

            if old_value != value:
                changed_keys.append(key)

            execution_state[key] = value

        execution_state[
            "runtime_last_commit"
        ] = {
            "changed_keys": changed_keys,
            "commit_size": len(changed_keys),
        }

        return {
            "ok": True,
            "changed_keys": changed_keys,
            "execution_state": execution_state,
        }