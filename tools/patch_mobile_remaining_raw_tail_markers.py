from pathlib import Path

path = Path("templates/mobile.html")
text = path.read_text(encoding="utf-8", errors="replace")

marker = "NOVA_MOBILE_REMOVE_REMAINING_RAW_TAIL_MARKERS_20260703_FIXED"
target = "NOVA_MOBILE_HIDE_TOP_BRAND_SIGN_20260624"

if marker in text and target not in text:
    print("remaining raw tail marker patch already installed")
    raise SystemExit(0)

removed_total = 0
passes = 0

while target in text:
    passes += 1
    if passes > 20:
        raise SystemExit("safety stop: too many removals")

    idx = text.find(target)

    start = text.rfind("\n(() => {", 0, idx)
    if start == -1:
        start = text.rfind("(() => {", 0, idx)
    if start == -1:
        start = text.rfind("\n(function", 0, idx)
    if start == -1:
        start = text.rfind("\n", 0, idx)
    if start == -1:
        start = 0

    end = text.find("})();", idx)
    if end != -1:
        end += len("})();")
    else:
        end = text.find("</script>", idx)
        if end != -1:
            end += len("</script>")
        else:
            end = idx + len(target)

    if end <= start:
        raise SystemExit("bad removal range")

    removed = text[start:end]

    # IMPORTANT: replacement must NOT include the target string, or loop repeats forever.
    replacement = "\n<!-- " + marker + ": removed malformed leftover mobile raw block -->\n"

    text = text[:start] + replacement + text[end:]
    removed_total += len(removed)

path.write_text(text.rstrip() + "\n", encoding="utf-8")
print("removed remaining raw tail chars:", removed_total)
print("patched:", path)
