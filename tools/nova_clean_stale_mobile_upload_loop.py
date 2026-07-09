import json
from pathlib import Path
from datetime import datetime

TARGET = "mobile_master_ae8aa56d26464a25bd70a2d54ffbe768.txt"

sessions_path = Path("data/nova_sessions.json")
backup_dir = Path("nova_backups")
backup_dir.mkdir(exist_ok=True)

if not sessions_path.exists():
    raise SystemExit("Missing data/nova_sessions.json")

backup_path = backup_dir / f"nova_sessions_before_stale_upload_clean_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
backup_path.write_text(sessions_path.read_text(encoding="utf-8"), encoding="utf-8")

data = json.loads(sessions_path.read_text(encoding="utf-8"))

removed = 0

def contains_target(value):
    if isinstance(value, str):
        return TARGET in value
    if isinstance(value, dict):
        return any(contains_target(v) for v in value.values())
    if isinstance(value, list):
        return any(contains_target(v) for v in value)
    return False

def clean(obj, parent_key=""):
    global removed

    if isinstance(obj, list):
        new_items = []
        for item in obj:
            if contains_target(item) and any(word in parent_key.lower() for word in ["attach", "upload", "file", "image"]):
                removed += 1
                continue
            new_items.append(clean(item, parent_key))
        return new_items

    if isinstance(obj, dict):
        out = {}
        for key, value in obj.items():
            lower_key = str(key).lower()

            if isinstance(value, list) and any(word in lower_key for word in ["attach", "upload", "file", "image"]):
                cleaned_list = []
                for item in value:
                    if contains_target(item):
                        removed += 1
                        continue
                    cleaned_list.append(clean(item, lower_key))
                out[key] = cleaned_list
                continue

            if isinstance(value, str) and TARGET in value and any(word in lower_key for word in ["attach", "upload", "file", "image", "url", "path"]):
                removed += 1
                out[key] = ""
                continue

            out[key] = clean(value, lower_key)

        return out

    return obj

cleaned = clean(data)
sessions_path.write_text(json.dumps(cleaned, ensure_ascii=False, indent=2), encoding="utf-8")

upload_path = Path("uploads") / TARGET
if upload_path.exists():
    stale_dir = backup_dir / "stale_uploads"
    stale_dir.mkdir(exist_ok=True)
    upload_path.replace(stale_dir / TARGET)
    print(f"MOVED stale upload file to {stale_dir / TARGET}")

print(f"BACKUP {backup_path}")
print(f"REMOVED_OR_CLEARED_REFERENCES {removed}")
print("NOVA STALE MOBILE UPLOAD CLEAN PASSED")
