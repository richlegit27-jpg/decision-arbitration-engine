from pathlib import Path
import re

files = [
    Path("templates/mobile.html"),
    Path("static/js/nova-mobile-app.js"),
    Path("static/js/mobile/nova-mobile-copy-action-fix.js"),
    Path("static/js/mobile/nova-mobile-message-actions.js"),
]

needles = [
    "NOVA_MOBILE_COPY_SINGLE_OWNER_FIXED_BUTTON_20260702",
    "NOVA_MOBILE_COPY_SINGLE_OWNER_20260702",
    "nova-mobile-single-owner-copy",
    "nova-mobile-row-copy",
    "nova-mobile-copy-chat",
    "nova-mobile-menu-copy-chat",
    "nova-mobile-copy-action-fix",
    "NOVA_MOBILE_COPY_ACTION_FIX_20260702",
    "NOVA_MOBILE_COPY_REGENERATE_FINAL_20260630",
    "NOVA MOBILE MESSAGE ACTIONS SINGLE OWNER CLEANUP",
    "nova-final-message-actions",
    "nova-mobile-copy-btn",
    "document.execCommand(\"copy\")",
    "navigator.clipboard.writeText",
]

print("NOVA MOBILE COPY DUPLICATE AUDIT")
print("=" * 90)

for path in files:
    print("")
    print(path)
    print("-" * 90)

    if not path.exists():
        print("MISSING")
        continue

    text = path.read_text(encoding="utf-8", errors="replace")

    for needle in needles:
        count = text.count(needle)
        if count:
            print(f"{count:>3}  {needle}")

    if path.name == "mobile.html":
        fixed_blocks = re.findall(
            r"<!-- NOVA_MOBILE_COPY_SINGLE_OWNER_FIXED_BUTTON_20260702_START -->.*?<!-- NOVA_MOBILE_COPY_SINGLE_OWNER_FIXED_BUTTON_20260702_END -->",
            text,
            flags=re.DOTALL,
        )
        old_blocks = re.findall(
            r"<!-- NOVA_MOBILE_COPY_SINGLE_OWNER_20260702_START -->.*?<!-- NOVA_MOBILE_COPY_SINGLE_OWNER_20260702_END -->",
            text,
            flags=re.DOTALL,
        )

        print("")
        print(f"fixed single-owner blocks: {len(fixed_blocks)}")
        print(f"old single-owner blocks:   {len(old_blocks)}")

        scripts = re.findall(r"<script[^>]+src=.*?</script>", text, flags=re.IGNORECASE | re.DOTALL)
        print("")
        print("mobile script tags containing copy/app/actions:")
        for s in scripts:
            if any(x in s for x in ["copy", "nova-mobile-app", "message-actions"]):
                print("  " + re.sub(r"\s+", " ", s).strip())

print("")
print("GIT STATUS")
print("=" * 90)
