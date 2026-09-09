from __future__ import annotations

import json
import uuid

from datetime import datetime, timezone
from pathlib import Path


_UNSET = object()
from nova_backend.services.auth_context import get_current_user_id


class ProjectWorkspaceService:

    def __init__(
        self,
        data_dir="data",
    ):
        self.data_dir = Path(data_dir)

        self.data_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.projects_file = (
            self.data_dir / "nova_projects.json"
        )

        self._ensure_storage()

    def _current_owner_id(
        self,
    ):
        return get_current_user_id()

    def _same_project_owner(
        self,
        project,
    ):
        current_owner_id = (
            self._current_owner_id()
        )

        if not current_owner_id:
            return False

        project_owner_id = str(
            project.get(
                "owner_id",
                "",
            ) or ""
        ).strip()

        if not project_owner_id:
            return False

        return (
            project_owner_id
            == str(current_owner_id).strip()
        )

        current_owner_id = self._current_owner_id()

        project_owner_id = str(
            project.get(
                "owner_id",
                "",
            ) or ""
        ).strip()

        # Legacy projects created before owner support
        # remain accessible to the current Nova installation.
        if not project_owner_id:
            return True

        # No authenticated owner context means do not
        # apply owner filtering.
        if not current_owner_id:
            return True

        return project_owner_id == str(
            current_owner_id
        )

    def _refresh_project_brain_state(
        self,
        project,
    ):
        """
        Synchronize Project Brain with the project's actual live state.

        This method derives operational intelligence from real project
        data rather than relying only on AI planning output.
        """

        if not isinstance(
            project,
            dict,
        ):
            return project

        brain = project.get(
            "brain",
            {},
        )

        if not isinstance(
            brain,
            dict,
        ):
            brain = {}

        tasks = project.get(
            "tasks",
            [],
        )

        if not isinstance(
            tasks,
            list,
        ):
            tasks = []

        total_tasks = len(tasks)

        completed_tasks = []
        active_tasks = []
        pending_tasks = []

        active_statuses = {
            "in_progress",
            "in progress",
            "active",
            "running",
        }

        completed_statuses = {
            "completed",
            "complete",
            "done",
        }

        for task in tasks:

            if not isinstance(
                task,
                dict,
            ):
                continue

            status = str(
                task.get(
                    "status",
                    "open",
                )
            ).strip().lower()

            if status in completed_statuses:

                completed_tasks.append(
                    task
                )

            elif status in active_statuses:

                active_tasks.append(
                    task
                )

            else:

                pending_tasks.append(
                    task
                )

        completed_count = len(
            completed_tasks
        )

        active_count = len(
            active_tasks
        )

        pending_count = len(
            pending_tasks
        )

        completion_percentage = 0.0

        if total_tasks > 0:

            completion_percentage = round(
                (
                    completed_count
                    / total_tasks
                ) * 100,
                1,
            )

        current_focus = []

        for task in active_tasks:

            title = str(
                task.get(
                    "title",
                    "",
                )
            ).strip()

            if title:
                current_focus.append(
                    title
                )

        if not current_focus:

            for task in pending_tasks:

                title = str(
                    task.get(
                        "title",
                        "",
                    )
                ).strip()

                if title:

                    current_focus.append(
                        title
                    )

                if len(
                    current_focus
                ) >= 5:
                    break

        next_actions = []

        for task in active_tasks + pending_tasks:

            title = str(
                task.get(
                    "title",
                    "",
                )
            ).strip()

            if not title:
                continue

            if title in next_actions:
                continue

            next_actions.append(
                title
            )

            if len(
                next_actions
            ) >= 5:
                break

        project_files = project.get(
            "files",
            [],
        )

        if not isinstance(
            project_files,
            list,
        ):
            project_files = []

        valid_files = [
            file_record
            for file_record in project_files
            if isinstance(
                file_record,
                dict,
            )
        ]

        recent_files = []

        for file_record in valid_files[-5:]:

            filename = str(
                file_record.get(
                    "filename",
                    file_record.get(
                        "name",
                        "",
                    ),
                )
            ).strip()

            if filename:

                recent_files.append(
                    filename
                )

        brain["current_state"] = {
            "total_tasks": total_tasks,
            "completed_tasks": completed_count,
            "in_progress_tasks": active_count,
            "pending_tasks": pending_count,
            "completion_percentage": (
                completion_percentage
            ),
            "current_focus": current_focus[:5],
            "file_count": len(
                valid_files
            ),
            "recent_files": recent_files,
        }

        brain["next_actions"] = (
            next_actions
        )

        # ----------------------------------------------------------
        # PROJECT HEALTH INTELLIGENCE
        # ----------------------------------------------------------

        project_health = "not_started"
        attention_required = False
        insights = []

        if total_tasks == 0:

            project_health = "not_started"

            insights.append(
                "No project tasks have been created yet."
            )

        elif completed_count == total_tasks:

            project_health = "complete"

            insights.append(
                "All project tasks are complete."
            )

        else:

            if active_count > 0:

                project_health = "on_track"

                insights.append(
                    f"{active_count} task"
                    f"{' is' if active_count == 1 else 's are'} "
                    "currently in progress."
                )

            elif pending_count > 0:

                project_health = "needs_attention"
                attention_required = True

                insights.append(
                    "No task is currently in progress."
                )

            if completed_count > 0:

                insights.append(
                    f"{completion_percentage}% of project "
                    "tasks are complete."
                )

            if pending_count > 0:

                insights.append(
                    f"{pending_count} task"
                    f"{' remains' if pending_count == 1 else 's remain'} "
                    "pending."
                )

        if valid_files:

            insights.append(
                f"{len(valid_files)} project file"
                f"{' is' if len(valid_files) == 1 else 's are'} "
                "available."
            )

        brain["project_health"] = project_health

        brain["attention_required"] = (
            attention_required
        )

        brain["insights"] = insights[:10]

        milestones = brain.get(
            "milestones",
            [],
        )

        if not isinstance(
            milestones,
            list,
        ):
            milestones = []

        normalized_milestones = []

        for milestone in milestones:

            if not isinstance(
                milestone,
                dict,
            ):
                continue

            normalized_milestones.append(
                milestone
            )

        brain["milestones"] = (
            normalized_milestones
        )

        # ----------------------------------------------------------
        # PROJECT BRAIN EVOLUTION HISTORY
        # ----------------------------------------------------------
        #
        # Keep a compact history of meaningful project state changes.
        # Do not store duplicate snapshots when the refresh produces
        # the same operational state.

        history = brain.get(
            "history",
            [],
        )

        if not isinstance(
            history,
            list,
        ):
            history = []

        snapshot = {
            "current_state": {
                "total_tasks": total_tasks,
                "completed_tasks": completed_count,
                "in_progress_tasks": active_count,
                "pending_tasks": pending_count,
                "completion_percentage": (
                    completion_percentage
                ),
                "current_focus": current_focus[:5],
                "file_count": len(
                    valid_files
                ),
                "recent_files": recent_files,
            },
            "next_actions": next_actions[:5],
        }

        previous_snapshot = None

        if history:
            last_entry = history[-1]

            if isinstance(
                last_entry,
                dict,
            ):
                previous_snapshot = {
                    "current_state": last_entry.get(
                        "current_state",
                        {},
                    ),
                    "next_actions": last_entry.get(
                        "next_actions",
                        [],
                    ),
                }

        if snapshot != previous_snapshot:

            history.append(
                {
                    "timestamp": datetime.now(
                        timezone.utc
                    ).isoformat(),
                    "current_state": snapshot[
                        "current_state"
                    ],
                    "next_actions": snapshot[
                        "next_actions"
                    ],
                }
            )

        # Prevent unlimited Project Brain history growth.
        brain["history"] = history[-100:]

        # ----------------------------------------------------------
        # PROJECT HEALTH INTELLIGENCE
        # ----------------------------------------------------------

        blockers = brain.get(
            "blockers",
            [],
        )

        if not isinstance(
            blockers,
            list,
        ):
            blockers = []

        valid_blockers = []

        for blocker in blockers:

            blocker_text = str(
                blocker or ""
            ).strip()

            if blocker_text:
                valid_blockers.append(
                    blocker_text
                )

        unknowns = brain.get(
            "unknowns",
            [],
        )

        if not isinstance(
            unknowns,
            list,
        ):
            unknowns = []

        valid_unknowns = []

        for unknown in unknowns:

            unknown_text = str(
                unknown or ""
            ).strip()

            if unknown_text:
                valid_unknowns.append(
                    unknown_text
                )

        health_score = 100

        signals = []
        risks = []

        if total_tasks == 0:

            signals.append(
                "Project has not yet defined implementation tasks."
            )

            health_score -= 10

        if active_count > 0:

            signals.append(
                f"{active_count} task(s) currently in progress."
            )

        if pending_count > 0:

            signals.append(
                f"{pending_count} task(s) remaining."
            )

        if completed_count > 0:

            signals.append(
                f"{completed_count} task(s) completed."
            )

        if valid_unknowns:

            unknown_penalty = min(
                len(valid_unknowns) * 3,
                15,
            )

            health_score -= unknown_penalty

            risks.append(
                f"{len(valid_unknowns)} unresolved project unknown(s)."
            )

        if valid_blockers:

            blocker_penalty = min(
                len(valid_blockers) * 15,
                60,
            )

            health_score -= blocker_penalty

            risks.append(
                f"{len(valid_blockers)} active blocker(s) affecting progress."
            )

        if (
            total_tasks > 0
            and active_count == 0
            and pending_count > 0
        ):

            health_score -= 10

            risks.append(
                "Project has pending work but no active task."
            )

        if (
            total_tasks > 0
            and completed_count == total_tasks
        ):

            health_status = "complete"

            health_score = 100

            signals.append(
                "All project tasks are complete."
            )

        elif valid_blockers:

            health_status = "blocked"

        elif health_score < 60:

            health_status = "attention"

        elif health_score < 80:

            health_status = "watch"

        else:

            health_status = "healthy"

        health_score = max(
            0,
            min(
                100,
                health_score,
            ),
        )

        brain["health"] = {
            "status": health_status,
            "score": health_score,
            "signals": signals[:10],
            "risks": risks[:10],
        }

        # ----------------------------------------------------------
        # PROJECT PLANNING SUMMARY
        # ----------------------------------------------------------

        planning_lines = []

        planning_lines.append(
            f"Project health: {health_status} "
            f"({health_score}/100)."
        )

        planning_lines.append(
            f"Tasks: {total_tasks} total, "
            f"{active_count} active, "
            f"{completed_count} completed, "
            f"{pending_count} pending."
        )

        planning_lines.append(
            f"Files: {len(valid_files)} available."
        )

        if next_actions:

            planning_lines.append(
                "Next action: "
                + str(
                    next_actions[0]
                )
            )

        if valid_blockers:

            planning_lines.append(
                "Blockers: "
                + "; ".join(
                    valid_blockers[:3]
                )
            )

        elif valid_unknowns:

            planning_lines.append(
                "Unknowns: "
                + "; ".join(
                    valid_unknowns[:3]
                )
            )

        else:

            planning_lines.append(
                "Risks: No active blockers or unresolved unknowns."
            )

        brain["planning_summary"] = (
            " ".join(
                planning_lines
            )
        )

        brain["updated_at"] = datetime.now(
            timezone.utc
        ).isoformat()

        project["brain"] = brain

        return project
    def _ensure_storage(
        self,
    ):
        if not self.projects_file.exists():
            self.projects_file.write_text(
                "[]",
                encoding="utf-8-sig",
                )

    def _load_projects(
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

            if changed:
                self._save_projects(
                    data
                )

            return data

        except Exception:
            return []

    def _save_projects(
        self,
        projects,
    ):
        self.projects_file.write_text(
            json.dumps(
                projects,
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8-sig",
        )

    def _default_execution_state(
        self,
    ):
        return {
            "status": "idle",
            "current_task_id": None,
            "current_step": None,
            "queue": [],
            "last_action": None,
            "updated_at": datetime.now(
                timezone.utc
            ).isoformat(),
        }

    def create_project(
        self,
        title=None,
        request_text="",
        owner_id=None,
        plan=None,
        name=None,
        description=None,
    ):
        projects = self._load_projects()

        if name is not None and not title:
            title = name

        if description is not None and not request_text:
            request_text = description

        now = datetime.now(
            timezone.utc
        ).isoformat()

        project_id = (
            "project_"
            + uuid.uuid4().hex[:12]
        )

        if owner_id is None:
            owner_id = self._current_owner_id()

        for project in projects:
            if (
                project.get("owner_id") == owner_id
            ):
                project["active"] = False

        resolved_name = (
            str(
                name
                or title
                or "New Project"
            ).strip()
            or "New Project"
        )

        resolved_description = str(
            description
            or request_text
            or ""
        ).strip()

        project = {
            "id": project_id,
            "name": resolved_name,
            "title": resolved_name,
            "description": resolved_description,
            "request": resolved_description,
            "owner_id": owner_id,
            "active": True,
            "archived": False,
            "created_at": now,
            "updated_at": now,
            "tasks": [],
            "phases": [],
            "notes": [],
            "files": [],
            "activity": [],
            "execution": (
                self._default_execution_state()
            ),
            "brain": {},
        }

        if isinstance(plan, dict):
            project["plan"] = plan

            plan_tasks = plan.get(
                "tasks",
                [],
            )

            if isinstance(plan_tasks, list):
                for item in plan_tasks:
                    if not isinstance(item, dict):
                        continue

                    task = {
                        "id": str(
                            item.get("id")
                            or uuid.uuid4()
                        ),
                        "title": str(
                            item.get(
                                "title",
                                "New Task",
                            )
                        ),
                        "description": str(
                            item.get(
                                "description",
                                "",
                            )
                        ),
                        "priority": str(
                            item.get(
                                "priority",
                                "medium",
                            )
                        ),
                        "status": "open",
                        "action": str(
                            item.get(
                                "action",
                                "",
                            )
                        ),
                        "target_file": str(
                            item.get(
                                "target_file",
                                "",
                            )
                        ),
                        "content": str(
                            item.get(
                                "content",
                                "",
                            )
                        ),
                        "command": str(
                            item.get(
                                "command",
                                "",
                            )
                        ),
                        "created_at": now,
                    }

                    project["tasks"].append(
                        task
                    )

        self._refresh_project_brain_state(
            project
        )

        projects.append(project)

        self._save_projects(
            projects
        )

        return project


    def list_projects(
        self,
    ):
        projects = self._load_projects()

        return [
            project
            for project in projects
            if self._same_project_owner(
                project
            )
        ]

    def get_project(
        self,
        project_id,
    ):
        for project in self._load_projects():
            if (
                project.get("id") == project_id
                and self._same_project_owner(project)
            ):
                return project

        return None

    def get_active_project(
        self,
    ):
        projects = self._load_projects()

        for project in projects:
            if (
                project.get(
                    "active",
                    False,
                ) is True
                and self._same_project_owner(
                    project
                )
            ):
                return project

        return None


    def set_active_project(
        self,
        project_id,
    ):
        projects = self._load_projects()

        target_project = None

        for project in projects:
            if not self._same_project_owner(
                project
            ):
                continue

            if project.get(
                "id"
            ) == project_id:
                target_project = project

        if target_project is None:
            return None

        now = datetime.now(
            timezone.utc
        ).isoformat()

        for project in projects:
            if self._same_project_owner(
                project
            ):
                project["active"] = (
                    project.get(
                        "id"
                    ) == project_id
                )

                if project.get(
                    "id"
                ) == project_id:
                    project["updated_at"] = now

        self._save_projects(
            projects
        )

        return target_project

    def get_project_brain_summary(
        self,
        project_id,
    ):
        project = self.get_project(
            project_id
        )

        if not project:
            return None

        brain = project.get(
            "brain",
            {},
        )

        if not isinstance(
            brain,
            dict,
        ):
            brain = {}

        try:
            self._refresh_project_brain_state(
                project
            )

            brain = project.get(
                "brain",
                brain,
            )

        except Exception:
            pass

        return brain


    def list_notes(
        self,
        project_id,
    ):
        project = self.get_project(
            project_id
        )

        if not project:
            return []

        notes = project.get(
            "notes",
            [],
        )

        if not isinstance(
            notes,
            list,
        ):
            return []

        return notes


    def add_note(
        self,
        project_id,
        title,
        content,
    ):
        import uuid
        from datetime import datetime, timezone

        projects = self._load_projects()

        project = None

        for item in projects:
            if str(
                item.get("id", "")
            ) == str(project_id):
                project = item
                break

        if not project:
            return None

        notes = project.get(
            "notes"
        )

        if not isinstance(
            notes,
            list,
        ):
            notes = []
            project["notes"] = notes

        now = datetime.now(
            timezone.utc
        ).isoformat()

        note = {
            "id": str(
                uuid.uuid4()
            ),
            "title": str(
                title or "Untitled Note"
            ).strip(),
            "content": str(
                content or ""
            ),
            "created_at": now,
            "updated_at": now,
        }

        notes.append(note)

        self._save_projects(
            projects
        )

        return note


    def update_note(
        self,
        project_id,
        note_id,
        title=None,
        content=None,
    ):
        from datetime import datetime, timezone

        projects = self._load_projects()

        project = None

        for item in projects:
            if str(
                item.get("id", "")
            ) == str(project_id):
                project = item
                break

        if not project:
            return None

        notes = project.get(
            "notes",
            [],
        )

        if not isinstance(
            notes,
            list,
        ):
            return None

        for note in notes:
            if str(
                note.get("id", "")
            ) != str(note_id):
                continue

            if title is not None:
                note["title"] = str(
                    title
                ).strip()

            if content is not None:
                note["content"] = str(
                    content
                )

            note["updated_at"] = (
                datetime.now(
                    timezone.utc
                ).isoformat()
            )

            self._save_projects(
                projects
            )

            return note

        return None


    def delete_note(
        self,
        project_id,
        note_id,
    ):
        projects = self._load_projects()

        project = None

        for item in projects:
            if str(
                item.get("id", "")
            ) == str(project_id):
                project = item
                break

        if not project:
            return False

        notes = project.get(
            "notes",
            [],
        )

        if not isinstance(
            notes,
            list,
        ):
            return False

        original_count = len(
            notes
        )

        project["notes"] = [
            note
            for note in notes
            if str(
                note.get("id", "")
            ) != str(note_id)
        ]

        if len(
            project["notes"]
        ) == original_count:
            return False

        self._save_projects(
            projects
        )

        return True
    def get_execution_state(
        self,
        project_id,
    ):
        project = self.get_project(
            project_id
        )

        if not project:
            return None

        execution = project.get(
            "execution"
        )

        if not isinstance(
            execution,
            dict,
        ):
            execution = self._default_execution_state()

            project["execution"] = execution

            projects = self._load_projects()

            for index, stored_project in enumerate(
                projects
            ):
                if (
                    stored_project.get("id")
                    == project_id
                ):
                    projects[index] = project
                    break

            self._save_projects(
                projects
            )

        return execution

    def update_execution_state(
        self,
        project_id,
        status=_UNSET,
        current_task_id=_UNSET,
        current_step=_UNSET,
        queue=_UNSET,
        last_action=_UNSET,
    ):
        projects = self._load_projects()

        for project in projects:
            if (
                project.get("id") != project_id
                or not self._same_project_owner(
                    project
                )
            ):
                continue

            execution = project.get(
                "execution"
            )

            if not isinstance(
                execution,
                dict,
            ):
                execution = (
                    self._default_execution_state()
                )

            if status is not _UNSET:
                execution["status"] = (
                    str(status).strip()
                    if status is not None
                    else ""
                )

            if current_task_id is not _UNSET:
                execution[
                    "current_task_id"
                ] = current_task_id

            if current_step is not _UNSET:
                execution[
                    "current_step"
                ] = current_step

            if queue is not _UNSET:
                execution["queue"] = (
                    queue
                    if isinstance(queue, list)
                    else []
                )

            if last_action is not _UNSET:
                execution[
                    "last_action"
                ] = (
                    str(last_action).strip()
                    if last_action is not None
                    else ""
                )

            execution["updated_at"] = (
                datetime.now(
                    timezone.utc
                ).isoformat()
            )

            project["execution"] = execution

            project["updated_at"] = (
                execution["updated_at"]
            )

            self._save_projects(
                projects
            )

            return execution

        return None

    def reset_execution_state(
        self,
        project_id,
    ):
        execution = (
            self._default_execution_state()
        )

        projects = self._load_projects()

        for project in projects:
            if (
                project.get("id") != project_id
                or not self._same_project_owner(
                    project
                )
            ):
                continue

            project["execution"] = execution
            project["updated_at"] = (
                execution["updated_at"]
            )

            self._save_projects(
                projects
            )

            return execution

        return None

    def archive_project(
        self,
        project_id,
    ):
        projects = self._load_projects()

        for project in projects:
            if (
                project.get("id") != project_id
                or not self._same_project_owner(project)
            ):
                continue

            project["status"] = "archived"
            project["active"] = False

            project["updated_at"] = datetime.now(
                timezone.utc
            ).isoformat()

            self._save_projects(
                projects
            )

            return project

        return None

    def restore_project(
        self,
        project_id,
    ):
        projects = self._load_projects()

        for project in projects:
            if (
                project.get("id") != project_id
                or not self._same_project_owner(project)
            ):
                continue

            project["status"] = "active"
            project["active"] = True

            project["updated_at"] = datetime.now(
                timezone.utc
            ).isoformat()

            self._save_projects(
                projects
            )

            return project

        return None

    def add_activity(
        self,
        project_id,
        action,
        details="",
    ):
        projects = self._load_projects()

        for project in projects:
            if (
                project.get("id") != project_id
                or not self._same_project_owner(project)
            ):
                continue

            activity = {
                "id": str(
                    uuid.uuid4()
                ),
                "action": str(
                    action
                ),
                "details": str(
                    details
                ),
                "created_at": datetime.now(
                    timezone.utc
                ).isoformat(),
            }

            project.setdefault(
                "timeline",
                [],
            ).append(
                activity
            )

            project["updated_at"] = datetime.now(
                timezone.utc
            ).isoformat()

            self._save_projects(
                projects
            )

            return activity

        return None

    def get_project_summary(
        self,
        project_id,
    ):
        project = self.get_project(
            project_id
        )

        if not project:
            return None

        return {
            "id": project.get("id"),
            "name": project.get("name"),
            "description": project.get("description"),
            "status": project.get("status"),
            "task_count": len(
                project.get("tasks", [])
            ),
            "file_count": len(
                project.get("files", [])
            ),
            "note_count": len(
                project.get("notes", [])
            ),
            "updated_at": project.get(
                "updated_at",
                "",
            ),
        }

    def list_phases(
        self,
        project_id,
    ):
        project = self.get_project(
            project_id
        )

        if not project:
            return None

        phases = project.get(
            "phases",
            [],
        )

        if not isinstance(
            phases,
            list,
        ):
            return []

        return [
            phase
            for phase in phases
            if isinstance(
                phase,
                dict,
            )
        ]

    def get_phase(
        self,
        project_id,
        phase_id,
    ):
        phases = self.list_phases(
            project_id
        )

        if phases is None:
            return None

        for phase in phases:
            if str(
                phase.get(
                    "id",
                    "",
                )
            ) == str(phase_id):
                return phase

        return None

    def add_phase(
        self,
        project_id,
        title,
        description="",
        status="planned",
        order=None,
        goal="",
        milestone="",
    ):
        projects = self._load_projects()

        for project in projects:

            if (
                project.get("id") != project_id
                or not self._same_project_owner(project)
            ):
                continue

            phases = project.setdefault(
                "phases",
                [],
            )

            if not isinstance(
                phases,
                list,
            ):
                phases = []
                project["phases"] = phases

            if order is None:
                order = len(phases) + 1

            phase = {
                "id": str(
                    uuid.uuid4()
                ),
                "title": str(
                    title or "New Phase"
                ).strip(),
                "description": str(
                    description or ""
                ).strip(),
                "status": str(
                    status or "planned"
                ).strip().lower(),
                "order": order,
                "goal": str(
                    goal or ""
                ).strip(),
                "milestone": str(
                    milestone or ""
                ).strip(),
                "created_at": datetime.now(
                    timezone.utc
                ).isoformat(),
                "updated_at": datetime.now(
                    timezone.utc
                ).isoformat(),
            }

            phases.append(
                phase
            )

            project = self._refresh_project_brain_state(
                project
            )

            project["updated_at"] = datetime.now(
                timezone.utc
            ).isoformat()

            self._save_projects(
                projects
            )

            return phase

        return None

    def update_phase(
        self,
        project_id,
        phase_id,
        updates,
    ):
        if not isinstance(
            updates,
            dict,
        ):
            return None

        projects = self._load_projects()

        allowed_fields = {
            "title",
            "description",
            "status",
            "order",
            "goal",
            "milestone",
        }

        for project in projects:

            if (
                project.get("id") != project_id
                or not self._same_project_owner(project)
            ):
                continue

            phases = project.get(
                "phases",
                [],
            )

            if not isinstance(
                phases,
                list,
            ):
                phases = []

            for phase in phases:

                if not isinstance(
                    phase,
                    dict,
                ):
                    continue

                if str(
                    phase.get(
                        "id",
                        "",
                    )
                ) != str(phase_id):
                    continue

                for key, value in updates.items():

                    if key not in allowed_fields:
                        continue

                    if key == "status":
                        phase[key] = str(
                            value or "planned"
                        ).strip().lower()

                    elif key == "order":
                        try:
                            phase[key] = int(value)
                        except (
                            TypeError,
                            ValueError,
                        ):
                            continue

                    else:
                        phase[key] = str(
                            value or ""
                        ).strip()

                phase["updated_at"] = datetime.now(
                    timezone.utc
                ).isoformat()

                project = self._refresh_project_brain_state(
                    project
                )

                project["updated_at"] = datetime.now(
                    timezone.utc
                ).isoformat()

                self._save_projects(
                    projects
                )

                return phase

        return None

    def delete_phase(
        self,
        project_id,
        phase_id,
    ):
        projects = self._load_projects()

        for project in projects:

            if (
                project.get("id") != project_id
                or not self._same_project_owner(project)
            ):
                continue

            phases = project.get(
                "phases",
                [],
            )

            if not isinstance(
                phases,
                list,
            ):
                phases = []

            updated_phases = [
                phase
                for phase in phases
                if not (
                    isinstance(
                        phase,
                        dict,
                    )
                    and str(
                        phase.get(
                            "id",
                            "",
                        )
                    ) == str(phase_id)
                )
            ]

            if len(
                updated_phases
            ) == len(phases):
                return False

            project["phases"] = updated_phases

            tasks = project.get(
                "tasks",
                [],
            )

            if isinstance(
                tasks,
                list,
            ):
                for task in tasks:
                    if not isinstance(
                        task,
                        dict,
                    ):
                        continue

                    if str(
                        task.get(
                            "phase_id",
                            "",
                        )
                    ) == str(phase_id):
                        task["phase_id"] = ""

            project = self._refresh_project_brain_state(
                project
            )

            project["updated_at"] = datetime.now(
                timezone.utc
            ).isoformat()

            self._save_projects(
                projects
            )

            return True

        return False


    def add_task(
        self,
        project_id,
        title,
        priority="medium",
        description="",
        action="",
        execution_mode="",
        target_file="",
        target_files=None,
        target_function="",
        dependencies=None,
        expected_output="",
        completion_criteria=None,
        phase_id="",
        content="",
        code="",
        replacement="",
        command="",
    ):

        projects = self._load_projects()

        for project in projects:

            if (
                project.get("id") != project_id
                or not self._same_project_owner(project)
            ):
                continue

            tasks = project.setdefault(
                "tasks",
                [],
            )

            if not isinstance(
                tasks,
                list,
            ):
                tasks = []
                project["tasks"] = tasks

            task = {
                "id": str(
                    uuid.uuid4()
                ),
                "title": str(
                    title or "New Task"
                ).strip(),
                "priority": str(
                    priority or "medium"
                ).strip(),
                "status": "open",
                "phase_id": str(
                    phase_id or ""
                ).strip(),
                "description": str(
                    description or ""
                ).strip(),


                "action": str(
                    action or ""
                ).strip().lower(),
                "execution_mode": str(
                    execution_mode or ""
                ).strip().lower(),
                "dependencies": (
                    list(dependencies)
                    if isinstance(
                        dependencies,
                        list,
                    )
                    else []
                ),
                "expected_output": str(
                    expected_output or ""
                ).strip(),
                "completion_criteria": (
                    list(completion_criteria)
                    if isinstance(
                        completion_criteria,
                        list,
                    )
                    else []
                ),

                "target_file": str(
                    target_file or ""
                ).strip(),
                "target_files": (
                    list(target_files)
                    if isinstance(
                        target_files,
                        list,
                    )
                    else []
                ),
                "target_function": str(
                    target_function or ""
                ).strip(),
                "content": str(
                    content or ""
                ),
                "code": str(
                    code or ""
                ),
                "replacement": str(
                    replacement or ""
                ),
                "command": str(
                    command or ""
                ).strip(),

                "created_at": datetime.now(
                    timezone.utc
                ).isoformat(),
            }

            tasks.append(
                task
            )

            # Keep Project Brain synchronized after task creation.
            project = self._refresh_project_brain_state(
                project
            )

            project["updated_at"] = datetime.now(
                timezone.utc
            ).isoformat()

            self._save_projects(
                projects
            )

            return task

        return None
    def update_task_status(
        self,
        project_id,
        task_id,
        status,
    ):
        projects = self._load_projects()

        for project in projects:

            if (
                project.get("id") != project_id
                or not self._same_project_owner(project)
            ):
                continue

            tasks = project.get(
                "tasks",
                [],
            )

            if not isinstance(
                tasks,
                list,
            ):
                tasks = []

                project["tasks"] = tasks

            for task in tasks:

                if not isinstance(
                    task,
                    dict,
                ):
                    continue

                if task.get("id") != task_id:
                    continue

                task["status"] = str(
                    status
                ).strip()

                # Recalculate the live Project Brain immediately after
                # task progress changes.
                project = self._refresh_project_brain_state(
                    project
                )

                project["updated_at"] = datetime.now(
                    timezone.utc
                ).isoformat()

                self._save_projects(
                    projects
                )

                return task

        return None
    def delete_task(
        self,
        project_id,
        task_id,
    ):
        projects = self._load_projects()

        for project in projects:

            if (
                project.get("id") != project_id
                or not self._same_project_owner(project)
            ):
                continue

            original_tasks = project.get(
                "tasks",
                [],
            )

            if not isinstance(
                original_tasks,
                list,
            ):
                original_tasks = []

            updated_tasks = [
                task
                for task in original_tasks
                if not (
                    isinstance(
                        task,
                        dict,
                    )
                    and task.get("id") == task_id
                )
            ]

            if (
                len(updated_tasks)
                == len(original_tasks)
            ):
                return False

            project["tasks"] = updated_tasks

            # Keep Project Brain synchronized after task removal.
            project = self._refresh_project_brain_state(
                project
            )

            project["updated_at"] = datetime.now(
                timezone.utc
            ).isoformat()

            self._save_projects(
                projects
            )

            return True

        return False

    def get_task_intelligence(
        self,
        project_id,
    ):
        project = self.get_project(
            project_id
        )

        if not project:
            return None

        tasks = project.get(
            "tasks",
            [],
        )

        if not isinstance(
            tasks,
            list,
        ):
            tasks = []

        total_tasks = len(
            tasks
        )

        completed_statuses = {
            "completed",
            "complete",
            "done",
        }

        active_statuses = {
            "in_progress",
            "in progress",
            "active",
            "running",
        }

        blocked_statuses = {
            "blocked",
            "waiting",
            "stuck",
        }

        completed_tasks = []
        active_tasks = []
        blocked_tasks = []
        open_tasks = []

        priority_breakdown = {
            "high": 0,
            "medium": 0,
            "low": 0,
            "other": 0,
        }

        normalized_tasks = []

        for task in tasks:

            if not isinstance(
                task,
                dict,
            ):
                continue

            normalized_tasks.append(
                task
            )

            status = str(
                task.get(
                    "status",
                    "open",
                )
                or "open"
            ).strip().lower()

            priority = str(
                task.get(
                    "priority",
                    "medium",
                )
                or "medium"
            ).strip().lower()

            if priority in priority_breakdown:
                priority_breakdown[
                    priority
                ] += 1
            else:
                priority_breakdown[
                    "other"
                ] += 1

            if status in completed_statuses:
                completed_tasks.append(
                    task
                )
                continue

            if status in active_statuses:
                active_tasks.append(
                    task
                )
                continue

            if status in blocked_statuses:
                blocked_tasks.append(
                    task
                )
                continue

            open_tasks.append(
                task
            )

        completion_percentage = 0.0

        if total_tasks > 0:
            completion_percentage = round(
                (
                    len(completed_tasks)
                    / total_tasks
                )
                * 100,
                1,
            )

        priority_order = {
            "high": 0,
            "medium": 1,
            "low": 2,
        }

        candidate_tasks = (
            active_tasks
            + open_tasks
        )

        candidate_tasks = sorted(
            candidate_tasks,
            key=lambda task: (
                priority_order.get(
                    str(
                        task.get(
                            "priority",
                            "medium",
                        )
                        or "medium"
                    ).strip().lower(),
                    3,
                ),
                str(
                    task.get(
                        "created_at",
                        "",
                    )
                ),
            ),
        )

        recommended_next_task = (
            candidate_tasks[0]
            if candidate_tasks
            else None
        )

        attention_required = (
            len(blocked_tasks) > 0
        )

        summary_parts = [
            (
                f"{total_tasks} total"
            ),
            (
                f"{len(active_tasks)} active"
            ),
            (
                f"{len(open_tasks)} open"
            ),
            (
                f"{len(completed_tasks)} completed"
            ),
            (
                f"{len(blocked_tasks)} blocked"
            ),
        ]

        return {
            "project_id": project_id,
            "total_tasks": total_tasks,
            "completed_count": len(
                completed_tasks
            ),
            "active_count": len(
                active_tasks
            ),
            "open_count": len(
                open_tasks
            ),
            "blocked_count": len(
                blocked_tasks
            ),
            "completion_percentage": (
                completion_percentage
            ),
            "attention_required": (
                attention_required
            ),
            "priority_breakdown": (
                priority_breakdown
            ),
            "recommended_next_task": (
                recommended_next_task
            ),
            "summary": (
                "Tasks: "
                + ", ".join(
                    summary_parts
                )
            ),
        }

    def list_files(
        self,
        project_id,
    ):
        project = self.get_project(
            project_id
        )

        if not project:
            return []

        files = project.get(
            "files",
            [],
        )

        return (
            files
            if isinstance(files, list)
            else []
        )

    def add_file(
        self,
        project_id,
        filename,
        path="",
        size=0,
        mime_type="",
    ):
        projects = self._load_projects()

        normalized_filename = str(
            filename or "Untitled file"
        ).strip()

        normalized_path = str(
            path or normalized_filename
        ).strip().replace("\\", "/")

        for project in projects:

            if (
                project.get("id") != project_id
                or not self._same_project_owner(project)
            ):
                continue

            files = project.setdefault(
                "files",
                [],
            )

            if not isinstance(files, list):
                files = []
                project["files"] = files

            now = datetime.now(
                timezone.utc
            ).isoformat()

            # IMPORTANT:
            # A project can only have one registry record for a
            # given logical file path.
            existing_file = None

            for file_record in files:

                if not isinstance(
                    file_record,
                    dict,
                ):
                    continue

                existing_path = str(
                    file_record.get("path")
                    or file_record.get("filename")
                    or ""
                ).strip().replace("\\", "/")

                if (
                    existing_path == normalized_path
                    or (
                        not normalized_path
                        and str(
                            file_record.get("filename")
                            or ""
                        ).strip()
                        == normalized_filename
                    )
                ):
                    existing_file = file_record
                    break

            if existing_file is not None:

                existing_file["filename"] = (
                    normalized_filename
                )
                existing_file["name"] = (
                    normalized_filename
                )
                existing_file["path"] = (
                    normalized_path
                )
                existing_file["size"] = int(
                    size or 0
                )
                existing_file["mime_type"] = str(
                    mime_type or ""
                )
                existing_file["updated_at"] = now

                project = (
                    self._refresh_project_brain_state(
                        project
                    )
                )

                project["updated_at"] = now

                self._save_projects(
                    projects
                )

                return existing_file

            file_record = {
                "id": str(
                    uuid.uuid4()
                ),
                "filename": normalized_filename,
                "name": normalized_filename,
                "path": normalized_path,
                "size": int(size or 0),
                "mime_type": str(
                    mime_type or ""
                ),
                "created_at": now,
                "updated_at": now,
            }

            files.append(file_record)

            project = (
                self._refresh_project_brain_state(
                    project
                )
            )

            project["updated_at"] = now

            self._save_projects(
                projects
            )

            return file_record

        return None

    def delete_file(
        self,
        project_id,
        file_id,
    ):
        projects = self._load_projects()

        for project in projects:

            if (
                project.get("id") != project_id
                or not self._same_project_owner(project)
            ):
                continue

            original_files = project.get(
                "files",
                [],
            )

            if not isinstance(
                original_files,
                list,
            ):
                original_files = []

            updated_files = [
                file_record
                for file_record in original_files
                if not (
                    isinstance(
                        file_record,
                        dict,
                    )
                    and file_record.get("id") == file_id
                )
            ]

            if (
                len(updated_files)
                == len(original_files)
            ):
                return False

            project["files"] = updated_files

            # Keep Project Brain synchronized after file removal.
            project = self._refresh_project_brain_state(
                project
            )

            project["updated_at"] = datetime.now(
                timezone.utc
            ).isoformat()

            self._save_projects(
                projects
            )

            return True

        return False
    def get_project_context(
        self,
        project_id,
    ):
        """
        Build a clean intelligence context for Project Planning AI.

        This is intentionally more than raw project storage. It gives
        Nova a structured understanding of the project's accumulated
        intelligence, current progress, and evolution.
        """

        project = self.get_project(
            project_id
        )

        if not project:
            return {}

        brain = project.get(
            "brain",
            {},
        )

        if not isinstance(
            brain,
            dict,
        ):
            brain = {}

        tasks = project.get(
            "tasks",
            [],
        )

        if not isinstance(
            tasks,
            list,
        ):
            tasks = []

        files = project.get(
            "files",
            [],
        )

        if not isinstance(
            files,
            list,
        ):
            files = []

        return {
            # ----------------------------------------------------------
            # PROJECT IDENTITY
            # ----------------------------------------------------------

            "project_id": project.get(
                "id",
                project_id,
            ),

            "project_name": project.get(
                "name",
                "",
            ),

            "description": project.get(
                "description",
                "",
            ),

            # ----------------------------------------------------------
            # CORE PROJECT INTELLIGENCE
            # ----------------------------------------------------------

            "goal": brain.get(
                "goal",
                "",
            ),

            "requirements": brain.get(
                "requirements",
                [],
            ),

            "assumptions": brain.get(
                "assumptions",
                [],
            ),

            "unknowns": brain.get(
                "unknowns",
                [],
            ),

            "milestones": brain.get(
                "milestones",
                [],
            ),

            "decisions": brain.get(
                "decisions",
                [],
            ),

            "blockers": brain.get(
                "blockers",
                [],
            ),

            "next_actions": brain.get(
                "next_actions",
                [],
            ),

            "recommendations": brain.get(
                "recommendations",
                [],
            ),

            # ----------------------------------------------------------
            # LIVE PROJECT STATE
            # ----------------------------------------------------------

            "current_state": brain.get(
                "current_state",
                {},
            ),

            "health": brain.get(
                "health",
                {},
            ),

            "project_health": brain.get(
                "project_health",
                "",
            ),

            "attention_required": brain.get(
                "attention_required",
                False,
            ),

            "insights": brain.get(
                "insights",
                [],
            ),

            "planning_summary": brain.get(
                "planning_summary",
                "",
            ),

            # ----------------------------------------------------------
            # PROJECT EVOLUTION
            # ----------------------------------------------------------

            "history": brain.get(
                "history",
                [],
            )[-20:],

            # ----------------------------------------------------------
            # ACTIVE PROJECT DATA
            # ----------------------------------------------------------

            "tasks": tasks,

            "files": files,

            # ----------------------------------------------------------
            # PLANNING METADATA
            # ----------------------------------------------------------

            "updated_at": project.get(
                "updated_at",
                "",
            ),
        }
    def delete_project(
        self,
        project_id,
    ):
        projects = self._load_projects()

        if not isinstance(
            projects,
            list,
        ):
            return None

        project = None

        for item in projects:
            if (
                item.get("id") == project_id
                and self._same_project_owner(item)
            ):
                project = item
                break

        if not project:
            return None

        projects = [
            item
            for item in projects
            if item.get("id") != project_id
        ]

        self._save_projects(
            projects
        )

        return project

# NOVA_PROJECT_WORKSPACE_SINGLETON_20260904
# Shared authoritative project workspace service instance.

project_workspace_service = ProjectWorkspaceService()









































