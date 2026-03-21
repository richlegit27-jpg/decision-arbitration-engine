# notepad C:\Users\Owner\nova\launch_nova.py

import os
from pathlib import Path
import sys
import subprocess

BASE_DIR = Path(__file__).parent

REQUIRED_TEMPLATES = ["index.html"]
REQUIRED_JS = [
    "nova-full.js",
    "nova-complete.js",
    "nova-bindings.js",
    "composer.js"
]
REQUIRED_CSS = [
    "base.css",
    "layout.css",
    "answer-payload.css"
]

def check_files(folder, required_files):
    missing = []
    for f in required_files:
        if not (folder / f).exists():
            missing.append(f)
    return missing

def main():
    print("🔍 Running preflight check for Nova...")

    templates_folder = BASE_DIR / "templates"
    static_js_folder = BASE_DIR / "static" / "js"
    static_css_folder = BASE_DIR / "static" / "css"

    missing_templates = check_files(templates_folder, REQUIRED_TEMPLATES)
    missing_js = check_files(static_js_folder, REQUIRED_JS)
    missing_css = check_files(static_css_folder, REQUIRED_CSS)

    any_missing = False

    if missing_templates:
        any_missing = True
        print(f"❌ Missing templates: {missing_templates}")
    if missing_js:
        any_missing = True
        print(f"❌ Missing JS files: {missing_js}")
    if missing_css:
        any_missing = True
        print(f"❌ Missing CSS files: {missing_css}")

    if any_missing:
        print("\n⚠️ Cannot start Nova. Fix missing files first!")
        sys.exit(1)
    else:
        print("✅ All required files are present. Launching Nova...")

    # Launch Uvicorn
    uvicorn_cmd = [
        sys.executable, "-m", "uvicorn", "app:app",
        "--reload", "--port", "8000"
    ]
    subprocess.run(uvicorn_cmd)

if __name__ == "__main__":
    main()