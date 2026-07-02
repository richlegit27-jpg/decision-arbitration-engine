from pathlib import Path

path = Path("app.py")
text = path.read_text(encoding="utf-8", errors="ignore")

lines = text.splitlines()
if not any(line.strip() == "import json" for line in lines):
    text = "import json\n" + text
    path.write_text(text, encoding="utf-8")
    print("ADDED import json")
else:
    print("import json already exists")
