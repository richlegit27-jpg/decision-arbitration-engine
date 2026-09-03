import json

path = r"data\nova_projects.json"

with open(path, encoding="utf-8") as f:
    projects = json.load(f)

repairs = {
    "project_ad158f8a359a": "Test Project",
    "project_155c5d852b2c": "Project 2",
    "project_1f91c424ada5": "Nova Project",
    "project_6b5e712dcf99": "Project 3",
}

for project in projects:
    project_id = project.get("id")

    if project_id in repairs:
        name = repairs[project_id]
        project["name"] = name
        project["title"] = name

with open(path, "w", encoding="utf-8") as f:
    json.dump(
        projects,
        f,
        indent=2,
        ensure_ascii=False,
    )

print("PROJECT NAME REPAIR COMPLETE.")
