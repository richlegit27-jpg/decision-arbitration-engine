from pathlib import Path
import re

path = Path("nova_backend/services/chat_service.py")
text = path.read_text(encoding="utf-8", errors="replace")

before = text

text = re.sub(
    r'(?m)^([ \t]*)print\(\s*\n[ \t]*"\[Nova OpenAI Key\] loaded",\s*\n[ \t]*env_key\[:10\]\s*\+\s*"\.\.\."\s*\+\s*env_key\[-4:\],\s*\n[ \t]*\)',
    r'\1print("[Nova OpenAI Key] loaded")',
    text,
)

text = text.replace(
    'print("[Nova OpenAI Key] WARNING: OPENAI_API_KEY missing")',
    'print("[Nova OpenAI Key] not configured")',
)

if text == before:
    raise SystemExit("No unsafe OpenAI key log replacement happened")

if "env_key[:10]" in text or "env_key[-4:]" in text:
    raise SystemExit("Unsafe env_key slice still present")

path.write_text(text, encoding="utf-8")

print("Patched chat_service.py OpenAI key boot log")
