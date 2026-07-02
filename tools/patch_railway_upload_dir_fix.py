from pathlib import Path

path = Path("nova_backend/services/chat_service.py")
text = path.read_text(encoding="utf-8")

old = '''        uploads_dir = _NovaImagePath(self.uploads_dir)
        uploads_dir.mkdir(parents=True, exist_ok=True)
        filepath = uploads_dir / filename
'''

new = '''        uploads_dir = _NovaImagePath(self.uploads_dir)

        # NOVA_RAILWAY_UPLOAD_DIR_FIX_20260702
        # Railway/Linux must not use the old Windows dev path C:\\Users\\Owner\\nova\\uploads.
        uploads_dir_text = str(uploads_dir)
        if ":" in uploads_dir_text or "\\\\" in uploads_dir_text:
            uploads_dir = _NovaImagePath.cwd() / "uploads"

        uploads_dir.mkdir(parents=True, exist_ok=True)
        filepath = uploads_dir / filename
        print("[NOVA_RAILWAY_UPLOAD_DIR_FIX_20260702] uploads_dir", str(uploads_dir))
'''

if old not in text:
    raise SystemExit("target uploads_dir block not found")

text = text.replace(old, new, 1)
path.write_text(text, encoding="utf-8")
print("patched railway upload dir fix")
