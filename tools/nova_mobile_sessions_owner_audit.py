from pathlib import Path
import re

ROOT = Path(".")
TEMPLATE = ROOT / "templates" / "mobile.html"
MOBILE_JS_DIR = ROOT / "static" / "js" / "mobile"

REPORT = ROOT / "tools" / "nova_mobile_sessions_owner_audit_report.txt"

KEYWORDS = [
    "nova-mobile-sessions-panel",
    "nova-mobile-sessions-button",
    "mobileSessionsButton",
    "NovaMobileSessions",
    "NovaMobileSession",
    "nova-session-panel-open",
    "nova-mobile-sessions-open",
    "nova-sessions-open",
    "sessions-open",
    "aria-hidden",
    "setAttribute(\"aria-hidden\"",
    "setAttribute('aria-hidden'",
    "removeAttribute(\"aria-hidden\"",
    "removeAttribute('aria-hidden'",
    "document.body.hidden",
    "body.hidden",
    "setProperty(\"display\", \"none\"",
    "setProperty('display', 'none'",
    "display: none !important",
]

CANONICAL_KEEP = [
    "static/js/mobile/nova-mobile-sessions.js",
    "static/js/mobile/nova-mobile-sessions-rescue-final-v1.js",
]

KNOWN_GUARDS_KEEP_FOR_NOW = [
    "static/js/mobile/nova-mobile-sessions-close-final-v1.js",
    "static/js/mobile/nova-mobile-close-layout-reset-v1.js",
]

def read(path):
    return path.read_text(encoding="utf-8", errors="replace")

def script_srcs(template_text):
    found = []
    for m in re.finditer(r'<script[^>]+src=["\']([^"\']+)["\'][^>]*>\s*</script>', template_text, re.I):
        src = m.group(1)
        line = template_text[:m.start()].count("\n") + 1
        found.append((line, src))
    return found

def inline_scripts(template_text):
    blocks = []
    for m in re.finditer(r'<script(?![^>]+src=)[^>]*>(.*?)</script>', template_text, re.I | re.S):
        body = m.group(1)
        line = template_text[:m.start()].count("\n") + 1
        hits = [k for k in KEYWORDS if k in body]
        if hits:
            blocks.append((line, hits, body[:500].replace("\n", "\\n")))
    return blocks

def keyword_hits(path, text):
    hits = []
    for keyword in KEYWORDS:
        if keyword in text:
            lines = []
            for i, line in enumerate(text.splitlines(), 1):
                if keyword in line:
                    lines.append(i)
                    if len(lines) >= 8:
                        break
            hits.append((keyword, lines))
    return hits

def classify_src(src):
    clean = src.split("?", 1)[0].lstrip("/")
    if clean in CANONICAL_KEEP:
        return "CANONICAL_KEEP"
    if clean in KNOWN_GUARDS_KEEP_FOR_NOW:
        return "GUARD_KEEP_FOR_NOW"
    lowered = clean.lower()
    if any(word in lowered for word in ["session", "sessions", "menu", "close", "layout"]):
        return "REVIEW_COMPETING_OWNER"
    return "other"

def main():
    if not TEMPLATE.exists():
        raise SystemExit("missing templates/mobile.html")

    template_text = read(TEMPLATE)
    lines = []

    lines.append("NOVA MOBILE SESSIONS OWNER AUDIT")
    lines.append("=" * 40)
    lines.append("")

    lines.append("CANONICAL OWNER PLAN")
    lines.append("- static/js/mobile/nova-mobile-sessions.js")
    lines.append("- static/js/mobile/nova-mobile-sessions-rescue-final-v1.js")
    lines.append("")
    lines.append("Temporary guards kept for now:")
    lines.append("- static/js/mobile/nova-mobile-sessions-close-final-v1.js")
    lines.append("- static/js/mobile/nova-mobile-close-layout-reset-v1.js")
    lines.append("")

    lines.append("SCRIPT TAGS IN templates/mobile.html")
    lines.append("-" * 40)

    review_count = 0
    for line, src in script_srcs(template_text):
        cls = classify_src(src)
        if cls == "REVIEW_COMPETING_OWNER":
            review_count += 1
        lines.append(f"{line}: {cls}: {src}")

    lines.append("")
    lines.append("INLINE SCRIPT BLOCKS TOUCHING SESSIONS/BODY")
    lines.append("-" * 40)

    inline = inline_scripts(template_text)
    if not inline:
        lines.append("none")
    else:
        for line, hits, preview in inline:
            lines.append(f"line {line}: hits={hits}")
            lines.append(f"preview={preview}")
            lines.append("")

    lines.append("")
    lines.append("MOBILE JS FILE KEYWORD HITS")
    lines.append("-" * 40)

    if MOBILE_JS_DIR.exists():
        for path in sorted(MOBILE_JS_DIR.glob("*.js")):
            text = read(path)
            hits = keyword_hits(path, text)
            if not hits:
                continue
            rel = path.as_posix()
            lines.append("")
            lines.append(rel)
            for keyword, hit_lines in hits:
                lines.append(f"  {keyword}: lines {hit_lines}")
    else:
        lines.append("missing static/js/mobile directory")

    lines.append("")
    lines.append("SUMMARY")
    lines.append("-" * 40)
    lines.append(f"review_competing_script_tags: {review_count}")
    lines.append(f"inline_blocks_touching_sessions_or_body: {len(inline)}")

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("wrote:", REPORT)
    print("review_competing_script_tags:", review_count)
    print("inline_blocks_touching_sessions_or_body:", len(inline))
    print("")
    print("Open report with:")
    print("notepad .\\tools\\nova_mobile_sessions_owner_audit_report.txt")

if __name__ == "__main__":
    main()
