from pathlib import Path

req = Path("requirements.txt")
existing = req.read_text(encoding="utf-8", errors="ignore").splitlines() if req.exists() else []

needed = [
    "gunicorn",
    "flask",
    "requests",
    "beautifulsoup4",
]

seen = set()
for line in existing:
    s = line.strip()
    if not s or s.startswith("#"):
        continue
    name = s.split("==")[0].split(">=")[0].split("<=")[0].split("~=")[0].lower()
    seen.add(name)

out = list(existing)
for pkg in needed:
    if pkg.lower() not in seen:
        out.append(pkg)

req.write_text("\n".join(out).strip() + "\n", encoding="utf-8")
print("updated requirements.txt")
