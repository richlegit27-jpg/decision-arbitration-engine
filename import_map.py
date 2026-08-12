from pathlib import Path
import ast

root = Path(".")

imports = {}
reverse = {}

for file in root.rglob("*.py"):
    if ".venv" in str(file) or "__pycache__" in str(file):
        continue

    try:
        tree = ast.parse(file.read_text(encoding="utf-8", errors="ignore"))
    except:
        continue

    imports[file.as_posix()] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for name in node.names:
                imports[file.as_posix()].append(name.name)

        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports[file.as_posix()].append(node.module)

for source, targets in imports.items():
    for target in targets:
        reverse.setdefault(target, []).append(source)

print("TOTAL PYTHON FILES:", len(imports))

print("\nMOST IMPORTED:")
for item, users in sorted(
    reverse.items(),
    key=lambda x: len(x[1]),
    reverse=True
)[:20]:
    print(len(users), item)

print("\nFILES WITH NO IMPORTERS:")
for file in imports:
    name = file.replace("/", ".").replace(".py", "")
    found = any(
        name in key
        for key in reverse.keys()
    )
    if not found:
        print(file)