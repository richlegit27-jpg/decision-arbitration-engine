# notepad C:\Users\Owner\nova\launch_nova_versioned.py

import sys
import subprocess
from pathlib import Path
import hashlib

BASE_DIR = Path(__file__).parent

# === REQUIRED FILES ===
REQUIRED_TEMPLATES = ["index.html"]

# JS/CSS expected SHA256 hashes (replace with your March 13 versions)
REQUIRED_JS = {
    "nova-full.js": "YOUR_SHA256_HASH_HERE",
    "nova-complete.js": "YOUR_SHA256_HASH_HERE",
    "nova-bindings.js": "YOUR_SHA256_HASH_HERE",
    "composer.js": "YOUR_SHA256_HASH_HERE"
}

REQUIRED_CSS = {
    "base.css": "YOUR_SHA256_HASH_HERE",
    "layout.css": "YOUR_SHA256_HASH_HERE",
    "answer-payload.css": "YOUR_SHA256_HASH_HERE"
}

def sha256sum(file_path):
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

def check_files_with_hash(folder, required_files):
    missing = []
    outdated = []
    for fname, expected_hash in required_files.items():
        fpath = folder / fname
        if not fpath.exists():
            missing.append(fname)
        else:
            actual_hash = sha256sum(fpath)
            if actual_hash != expected_hash:
                outdated.append(fname)
    return missing, outdated

def main():
    print("🔍 Running versioned preflight check for Nova...")

    # Check templates
    templates_folder = BASE_DIR / "templates"
    missing_templates = [f for f in REQUIRED_TEMPLATES if not (templates_folder / f).exists()]
    any_missing = bool(missing_templates)
    if missing_templates:
        print(f"❌ Missing templates: {missing_templates}")

    # Check JS
    js_folder = BASE_DIR / "static/js"
    missing_js, outdated_js = check_files_with_hash(js_folder, REQUIRED_JS)
    any_missing |= bool(missing_js or outdated_js)
    if missing_js:
        print(f"❌ Missing JS files: {missing_js}")
    if outdated_js:
        print(f"⚠️ Outdated JS files: {outdated_js}")

    # Check CSS
    css_folder = BASE_DIR / "static/css"
    missing_css, outdated_css = check_files_with_hash(css_folder, REQUIRED_CSS)
    any_missing |= bool(missing_css or outdated_css)
    if missing_css:
        print(f"❌ Missing CSS files: {missing_css}")
    if outdated_css:
        print(f"⚠️ Outdated CSS files: {outdated_css}")

    if any_missing:
        print("\n⚠️ Fix missing/outdated files before launching Nova!")
        sys.exit(1)
    else:
        print("✅ All files present and up-to-date. Launching Nova...")

    # Launch Uvicorn
    subprocess.run([sys.executable, "-m", "uvicorn", "app:app", "--reload", "--port", "8000"])

if __name__ == "__main__":
    main()