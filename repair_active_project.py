import json
from datetime import datetime, timezone

path = r"data\nova_projects.json"
active_id = "project_cc41a6ab439d"

with open(path, encoding="utf-8") as f:
    projects = json.load(f)

for project in projects:
    project["active"] = project.get("id") == active_id

    if project.get("id") == active_id:
        project["status"] = "active"

    project["updated_at"] = datetime.now(
        timezone.utc
    ).isoformat()

with open(path, "w", encoding="utf-8") as f:
    json.dump(
        projects,
        f,
        indent=2,
        ensure_ascii=False,
    )

print("ACTIVE PROJECT REPAIR COMPLETE.")
