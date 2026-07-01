from pathlib import Path
import re

path = Path("app.py")
text = path.read_text(encoding="utf-8", errors="replace")

before = text

pattern = re.compile(
    r'if __name__ == "__main__":\s*\n'
    r'([ \t]+)create_startup_backup\(\)\s*\n'
    r'app\.run\(\s*\n'
    r'([ \t]+)host="0\.0\.0\.0",\s*\n'
    r'([ \t]+)port=5001,\s*\n'
    r'([ \t]+)debug=True,\s*\n'
    r'\)\s*',
    re.MULTILINE,
)

replacement = (
    'if __name__ == "__main__":\n'
    '    create_startup_backup()\n'
    '    app.run(\n'
    '        host="0.0.0.0",\n'
    '        port=5001,\n'
    '        debug=True,\n'
    '    )\n'
)

text = pattern.sub(replacement, text)

if text == before:
    raise SystemExit("No app.run indentation patch happened")

path.write_text(text, encoding="utf-8")
print("Patched app.run under __main__ guard")
