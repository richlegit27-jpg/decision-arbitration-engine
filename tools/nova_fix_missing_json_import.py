from pathlib import Path

path = Path("app.py")
text = path.read_text(encoding="utf-8", errors="ignore")

if "import json" not in text:
    text = "import json`n" + text
    path.write_text(text, encoding="utf-8")
    print("ADDED import json to app.py")
else:
    print("import json already exists")
