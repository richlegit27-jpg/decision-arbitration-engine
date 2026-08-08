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
        completed = sum(
            1
            for task in tasks
            if task.get("completed")
        )

        return {
            "tasks": len(tasks),
            "completed_tasks": completed,
            "artifacts": len(artifacts),
            "chats": len(chats),
            "executions": len(executions),
        }

    def _build_progress(self, tasks):
        if not tasks:
            return 0

        completed = sum(
            1
            for task in tasks
            if task.get("completed")
        )

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

    def _build_risk(self, tasks):
        if not tasks:
            return "low"

        if any(
            not task.get("completed")
            for task in tasks
        ):
            return "medium"

        return "low"

    def _build_focus(self, tasks):
        for task in tasks:
            if not task.get("completed"):
                return task.get(
                    "title",
                    "Continue project",
                )

        return "No active work"

    def _build_next_action(self, tasks):
        return self._build_focus(tasks)

    def _build_recommendation(self, tasks):
        if self._build_progress(tasks) == 100:
            return "Plan the next milestone."

        return "Continue the next unfinished task."

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
        unfinished = [
            task
            for task in tasks
            if not task.get("completed")
        ]

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
            "Review the current project state.",
            "Choose the next milestone.",
            "Continue project work.",
        ]

    def _build_estimated_time(
        self,
        tasks,
    ):
        unfinished = sum(
            1
            for task in tasks
            if not task.get("completed")
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
        return [
            {
                "type": "project",
                "message": "Project loaded.",
                "time": datetime.utcnow().isoformat(),
            }
        ]

    def _build_blockers(self, tasks):
        return []


project_intelligence_service = (
    ProjectIntelligenceService()
)