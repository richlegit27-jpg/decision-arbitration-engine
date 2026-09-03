import json

with open(r"data\nova_projects.json", encoding="utf-8") as f:
    projects = json.load(f)

for project in projects:
    if project.get("name") == "{'active': True}":
        print()
        print("ID:", project.get("id"))
        print("DESCRIPTION:", repr(project.get("description")))
        print("CREATED:", project.get("created_at"))
        print("UPDATED:", project.get("updated_at"))
        print("METADATA:", project.get("metadata"))
        print("TASKS:", [t.get("title") for t in project.get("tasks", [])])
        print("NOTES:", [n.get("title") for n in project.get("notes", [])])
