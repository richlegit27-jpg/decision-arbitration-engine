import json

path = r"data\nova_projects.json"

with open(path, encoding="utf-8") as f:
    projects = json.load(f)

bad = [
    project
    for project in projects
    if project.get("name") == "{'active': True}"
]

print("CORRUPTED PROJECT COUNT:", len(bad))

for project in bad:
    print(
        project["id"],
        "name=", repr(project.get("name")),
        "title=", repr(project.get("title")),
        "active=", project.get("active"),
        "tasks=", len(project.get("tasks", [])),
        "notes=", len(project.get("notes", [])),
    )
