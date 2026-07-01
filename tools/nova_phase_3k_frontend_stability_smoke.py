from html.parser import HTMLParser
from pathlib import Path
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]

TEMPLATE_FILES = [
    ROOT / "templates" / "mobile.html",
    ROOT / "templates" / "index-mobile.html",
    ROOT / "templates" / "index.html",
]

MUST_EXIST = [
    ROOT / "app.py",
    ROOT / "static" / "css" / "nova-mobile.css",
    ROOT / "static" / "js" / "nova-mobile-app.js",
    ROOT / "static" / "js" / "mobile" / "nova-mobile-core.js",
    ROOT / "static" / "js" / "mobile" / "nova-mobile-sessions.js",
    ROOT / "static" / "js" / "mobile" / "nova-mobile-upload.js",
    ROOT / "static" / "js" / "mobile" / "nova-mobile-images.js",
    ROOT / "static" / "js" / "mobile" / "nova-mobile-voice.js",
]


BAD_REF_MARKERS = [
    ".bak",
    ".BAK",
    "BROKEN",
    "STABLE",
    "js_backup_",
]


class AssetParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.assets = []

    def handle_starttag(self, tag, attrs):
        data = dict(attrs)

        if tag == "script" and data.get("src"):
            self.assets.append(data["src"])

        if tag == "link" and data.get("href"):
            rel = str(data.get("rel", "")).lower()
            href = data["href"]
            if "stylesheet" in rel or href.endswith(".css"):
                self.assets.append(href)


def assert_true(name, condition, detail=""):
    if not condition:
        raise AssertionError(f"{name} FAILED {detail}")
    print(f"PASS {name}")


def clean_static_path(asset):
    asset = asset.split("?", 1)[0].split("#", 1)[0]

    if asset.startswith("/static/"):
        return ROOT / asset.lstrip("/")

    if asset.startswith("static/"):
        return ROOT / asset

    return None


def check_template_assets():
    checked_templates = [path for path in TEMPLATE_FILES if path.exists()]
    assert_true("frontend templates exist", bool(checked_templates), "no templates found")

    missing_assets = []
    bad_refs = []

    for template in checked_templates:
        text = template.read_text(encoding="utf-8", errors="replace")
        parser = AssetParser()
        parser.feed(text)

        for asset in parser.assets:
            for marker in BAD_REF_MARKERS:
                if marker in asset:
                    bad_refs.append(f"{template.relative_to(ROOT)} references {asset}")

            path = clean_static_path(asset)
            if path and not path.exists():
                missing_assets.append(f"{template.relative_to(ROOT)} -> {asset}")

    assert_true("template static assets exist", not missing_assets, "\n" + "\n".join(missing_assets))
    assert_true("template has no backup/relic asset refs", not bad_refs, "\n" + "\n".join(bad_refs))


def check_required_files():
    missing = [str(path.relative_to(ROOT)) for path in MUST_EXIST if not path.exists()]
    assert_true("required frontend files exist", not missing, "\n" + "\n".join(missing))


def check_no_static_relics():
    relics = []
    static_root = ROOT / "static"

    if static_root.exists():
        for path in static_root.rglob("*"):
            if not path.is_file():
                continue

            normalized = path.as_posix()
            name = path.name

            if "static/js_backup_" in normalized:
                relics.append(str(path.relative_to(ROOT)))
                continue

            if any(marker in name for marker in BAD_REF_MARKERS):
                relics.append(str(path.relative_to(ROOT)))

    assert_true("no static backup relic files", not relics, "\n" + "\n".join(relics[:100]))


def check_js_syntax_with_node():
    node = shutil.which("node")
    if not node:
        print("SKIP node js syntax check - node not found")
        return

    js_files = [
        ROOT / "static" / "js" / "nova-mobile-app.js",
        *sorted((ROOT / "static" / "js" / "mobile").glob("*.js")),
    ]

    failures = []

    for path in js_files:
        if not path.exists():
            continue

        result = subprocess.run(
            [node, "--check", str(path)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            failures.append(
                f"{path.relative_to(ROOT)}\n{result.stdout.strip()}\n{result.stderr.strip()}"
            )

    assert_true("mobile js syntax clean", not failures, "\n\n".join(failures))


def main():
    check_required_files()
    check_template_assets()
    check_no_static_relics()
    check_js_syntax_with_node()

    print("NOVA PHASE 3K FRONTEND STABILITY SMOKE PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
