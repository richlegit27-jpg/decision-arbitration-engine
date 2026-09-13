from pathlib import Path

path = Path(r"C:\Users\Owner\nova\nova_backend\services\project_workspace_service.py")

text = path.read_text(encoding="utf-8")

helper = '''    def _normalize_terminal_parent_nested_steps(
        self,
        projects,
    ):
        if not isinstance(projects, list):
            return False

        changed = False

        terminal_statuses = {
            "completed",
            "complete",
            "done",
            "success",
            "succeeded",
            "failed",
            "cancelled",
            "canceled",
        }

        for project in projects:
            if not isinstance(project, dict):
                continue

            tasks = project.get("tasks")

            if not isinstance(tasks, list):
                continue

            for task in tasks:
                if not isinstance(task, dict):
                    continue

                parent_status = str(
                    task.get("status")
                    or task.get("state")
                    or task.get("completion_status")
                    or ""
                ).strip().lower()

                if parent_status not in terminal_statuses:
                    continue

                steps = task.get("steps")

                if not isinstance(steps, list):
                    continue

                for step in steps:
                    if not isinstance(step, dict):
                        continue

                    current_status = str(
                        step.get("status")
                        or ""
                    ).strip().lower()

                    current_state = str(
                        step.get("state")
                        or ""
                    ).strip().lower()

                    current_completion_status = str(
                        step.get("completion_status")
                        or ""
                    ).strip().lower()

                    if (
                        current_status == "completed"
                        and current_state == "completed"
                        and current_completion_status == "completed"
                    ):
                        continue

                    step["status"] = "completed"
                    step["state"] = "completed"
                    step["completion_status"] = "completed"

                    changed = True

        return changed

'''

anchor = "    def _load_projects(\n"

if helper not in text:
    if anchor not in text:
        raise RuntimeError("Could not find _load_projects anchor")
    text = text.replace(anchor, helper + anchor, 1)

load_start = text.index("    def _load_projects(\n")
save_start = text.index("    def _save_projects(\n", load_start)

new_load = '''    def _load_projects(
        self,
    ):
        try:
            data = json.loads(
                self.projects_file.read_text(
                    encoding="utf-8-sig"
                )
            )

            if not isinstance(data, list):
                return []

            changed = False

            for project in data:
                if not isinstance(project, dict):
                    continue

                if not isinstance(
                    project.get("execution"),
                    dict,
                ):
                    project["execution"] = (
                        self._default_execution_state()
                    )

                    changed = True

            if self._normalize_terminal_parent_nested_steps(
                data
            ):
                changed = True

            if changed:
                self._save_projects(
                    data
                )

            return data

        except Exception:
            return []

'''

text = text[:load_start] + new_load + text[save_start:]

save_start = text.index("    def _save_projects(\n")
default_start = text.index("    def _default_execution_state(\n", save_start)

new_save = '''    def _save_projects(
        self,
        projects,
    ):
        self._normalize_terminal_parent_nested_steps(
            projects
        )

        self.projects_file.write_text(
            json.dumps(
                projects,
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8-sig",
        )

'''

text = text[:save_start] + new_save + text[default_start:]

path.write_text(text, encoding="utf-8")

print("PATCHED:", path)
