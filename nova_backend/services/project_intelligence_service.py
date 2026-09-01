from datetime import datetime


class ProjectIntelligenceService:

    def build(
        self,
        project=None,
        tasks=None,
        artifacts=None,
        chats=None,
        executions=None,
    ):
        project = project or {}
        tasks = tasks or []
        artifacts = artifacts or []
        chats = chats or []
        executions = executions or []

        return {
            "project_id": project.get("id"),
            "generated_at": datetime.utcnow().isoformat(),
            "mission": project.get("description", ""),
            "current_focus": self._build_focus(tasks),
            "next_action": self._build_next_action(tasks),
            "recommendation": self._build_recommendation(tasks),
            "resume_summary": self._build_resume_summary(
                project,
                tasks,
            ),
            "today_plan": self._build_today_plan(
                tasks,
            ),
            "estimated_time": self._build_estimated_time(
                tasks,
            ),
            "progress": self._build_progress(tasks),
            "health": self._build_health(tasks),
            "risk": self._build_risk(tasks),
            "stats": self._build_stats(
                tasks,
                artifacts,
                chats,
                executions,
            ),
            "recent_activity": self._build_recent_activity(
                project
            ),
            "blockers": self._build_blockers(tasks),
        }

    def _build_stats(
        self,
        tasks,
        artifacts,
        chats,
        executions,
    ):
        completed = 0

        for task in tasks:
            status = str(
                task.get("status") or ""
            ).lower()

            if (
                task.get("completed") is True
                or status in {
                    "done",
                    "complete",
                    "completed",
                }
            ):
                completed += 1

        return {
            "tasks": len(tasks),
            "completed_tasks": completed,
            "artifacts": len(artifacts),
            "chats": len(chats),
            "executions": len(executions),
        }

    def _build_progress(
        self,
        tasks,
    ):
        if not tasks:
            return 0

        completed = 0

        for task in tasks:
            status = str(
                task.get("status") or ""
            ).lower()

            if (
                task.get("completed") is True
                or status in {
                    "done",
                    "complete",
                    "completed",
                }
            ):
                completed += 1

        return round(
            completed / len(tasks) * 100
        )

    def _build_health(self, tasks):
        progress = self._build_progress(tasks)

        if progress >= 80:
            return 100

        if progress >= 50:
            return 80

        if progress >= 25:
            return 60

        return 40

    def _build_risk(
        self,
        tasks,
    ):
        if not tasks:
            return "low"

        unfinished = self._unfinished_tasks(
            tasks
        )

        if unfinished:
            return "medium"

        return "low"

    def _unfinished_tasks(
        self,
        tasks,
    ):
        unfinished = []

        for task in tasks:
            status = str(
                task.get("status") or ""
            ).lower()

            completed = (
                task.get("completed") is True
                or status in {
                    "done",
                    "complete",
                    "completed",
                }
            )

            if not completed:
                unfinished.append(task)

        priority_rank = {
            "critical": 0,
            "high": 1,
            "medium": 2,
            "low": 3,
        }

        unfinished.sort(
            key=lambda task: (
                priority_rank.get(
                    str(
                        task.get("priority")
                        or "medium"
                    ).lower(),
                    2,
                ),
                str(
                    task.get("title")
                    or task.get("name")
                    or ""
                ).lower(),
            )
        )

        return unfinished


    def _build_focus(
        self,
        tasks,
    ):
        unfinished = self._unfinished_tasks(
            tasks
        )

        if not unfinished:
            return "No active work"

        task = unfinished[0]

        return (
            task.get("title")
            or task.get("name")
            or "Continue project"
        )


    def _build_next_action(
        self,
        tasks,
    ):
        unfinished = self._unfinished_tasks(
            tasks
        )

        if not unfinished:
            return "Plan the next milestone"

        task = unfinished[0]

        title = (
            task.get("title")
            or task.get("name")
            or "Continue project"
        )

        return f"Complete: {title}"


    def _build_recommendation(
        self,
        tasks,
    ):
        unfinished = self._unfinished_tasks(
            tasks
        )

        if not unfinished:
            return (
                "The current task list is complete. "
                "Define the next milestone."
            )

        task = unfinished[0]

        priority = str(
            task.get("priority")
            or "medium"
        ).lower()

        title = (
            task.get("title")
            or task.get("name")
            or "the next task"
        )

        if priority in {
            "critical",
            "high",
        }:
            return (
                f"Prioritize {title}. "
                f"It is marked {priority} priority."
            )

        return (
            f"Continue with {title}. "
            "It is the highest-priority unfinished task."
        )

    def _build_resume_summary(
        self,
        project,
        tasks,
    ):
        name = (
            project.get("name")
            or project.get("title")
            or "This project"
        )

        focus = self._build_focus(tasks)

        next_action = self._build_next_action(
            tasks
        )

        return (
            f"{name} is ready to continue. "
            f"Current focus: {focus}. "
            f"Next action: {next_action}."
        )

    def _build_today_plan(
        self,
        tasks,
    ):
        unfinished = self._unfinished_tasks(
            tasks
        )

        plan = []

        for task in unfinished[:3]:
            title = (
                task.get("title")
                or task.get("name")
                or "Continue project work"
            )

            plan.append(title)

        if plan:
            return plan

        return [
            "Review completed work.",
            "Define the next milestone.",
            "Choose the next priority.",
        ]

    def _build_estimated_time(
        self,
        tasks,
    ):
        unfinished = len(
            self._unfinished_tasks(
                tasks
            )
        )

        if unfinished == 0:
            return "5 minutes"

        if unfinished <= 2:
            return "15 minutes"

        if unfinished <= 5:
            return "30 minutes"

        return "45+ minutes"


    def _build_recent_activity(
        self,
        project,
    ):
        timeline = project.get(
            "timeline",
            [],
        )

        if not isinstance(
            timeline,
            list,
        ):
            return []

        activities = [
            item
            for item in timeline
            if isinstance(
                item,
                dict,
            )
        ]

        activities.sort(
            key=lambda item: str(
                item.get(
                    "created_at",
                    "",
                )
            ),
            reverse=True,
        )

        return activities[:20]

    def _build_blockers(self, tasks):
        return []

project_intelligence_service = (
    ProjectIntelligenceService()
)