from pathlib import Path


ROOT = Path.cwd()
TARGET = ROOT / "nova_backend" / "services" / "chat_service.py"

MARKER = "# NOVA_IMAGE_ATTACHMENT_WEB_BLOCK_20260607"


def assert_true(name, condition, detail=""):
    if not condition:
        raise AssertionError(f"{name} FAILED {detail}")
    print(f"PASS {name}")


def main():
    print("NOVA PHASE 6E IMAGE WEB BLOCK CLEANUP VALIDATION")
    print("")

    assert_true("chat_service exists", TARGET.exists(), str(TARGET))

    lines = TARGET.read_text(encoding="utf-8", errors="ignore").splitlines()

    starts = [
        index
        for index, line in enumerate(lines, start=1)
        if MARKER in line
    ]

    print(f"Image/web block owners found: {len(starts)}")
    for line_no in starts:
        print(f"- owner at line {line_no}")

    assert_true(
        "single image web block owner remains",
        len(starts) == 1,
        f"owners={starts}",
    )

    keep = starts[0]
    final_window = "\n".join(lines[max(0, keep - 1): min(len(lines), keep + 140)])

    assert_true(
        "remaining owner has image attachment route lock",
        "image_attachment_web_block" in final_window,
    )

    assert_true(
        "remaining owner clears web sources",
        'decision["source_urls"] = []' in final_window
        and 'decision["sources"] = []' in final_window,
    )

    assert_true(
        "remaining owner preserves image analysis mode",
        'decision["mode"] = "image_analysis"' in final_window,
    )

    print("")
    print("NOVA PHASE 6E IMAGE WEB BLOCK CLEANUP VALIDATION PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
