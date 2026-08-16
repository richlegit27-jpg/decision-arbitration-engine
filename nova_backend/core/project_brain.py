from datetime import datetime
import uuid


class ProjectBrain:


    def __init__(self):

        self.projects = {}



    def create_project(
        self,
        name,
        goal="",
    ):

        project_id = (
            "project_"
            + uuid.uuid4().hex[:12]
        )

        project = {
            "id": project_id,
            "name": name,
            "goal": goal,
            "status": "active",
            "created_at": datetime.utcnow().isoformat(),
            "tasks": [],
            "files": [],
            "notes": [],
            "history": [],
            "blockers": [],
        }


        self.projects[project_id] = project

        return project



    def get_project(
        self,
        project_id,
    ):

        return self.projects.get(
            project_id,
            {},
        )



    def add_task(
        self,
        project_id,
        task,
    ):

        project = self.get_project(
            project_id
        )

        if project:

            project["tasks"].append(
                {
                    "task": task,
                    "status": "pending",
                    "created_at":
                        datetime.utcnow().isoformat(),
                }
            )

        return project



    def complete_task(
        self,
        project_id,
        index,
    ):

        project = self.get_project(
            project_id
        )

        if project:

            if index < len(project["tasks"]):

                project["tasks"][index]["status"] = "complete"

        return project



    def add_note(
        self,
        project_id,
        note,
    ):

        project = self.get_project(
            project_id
        )

        if project:

            project["notes"].append(
                {
                    "text": note,
                    "time":
                        datetime.utcnow().isoformat(),
                }
            )

        return project



    def checkpoint(
        self,
        project_id,
        event,
    ):

        project = self.get_project(
            project_id
        )

        if project:

            project["history"].append(
                {
                    "event": event,
                    "time":
                        datetime.utcnow().isoformat(),
                }
            )

        return project



    def snapshot(
        self,
        project_id,
    ):

        return self.get_project(
            project_id
        )