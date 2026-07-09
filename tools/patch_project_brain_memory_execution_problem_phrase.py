from pathlib import Path

path = Path("nova_backend/services/project_brain_general_intelligence.py")
text = path.read_text(encoding="utf-8")

old = '''    if (
        _has_any(text, memory_terms)
        and _has_any(text, execution_terms)
        and _has_any(text, ("nova", "separate", "difference", "distinction", "versus", "vs", "what should", "what is"))
    ):
        return "memory_execution_distinction"
'''

new = '''    if (
        _has_any(text, memory_terms)
        and _has_any(text, execution_terms)
        and _has_any(
            text,
            (
                "nova",
                "separate",
                "difference",
                "distinction",
                "versus",
                "vs",
                "what should",
                "what is",
                "problem",
                "issue",
                "this a",
                "is this",
            ),
        )
    ):
        return "memory_execution_distinction"
'''

if old not in text:
    raise SystemExit("target classifier block not found")

text = text.replace(old, new, 1)
path.write_text(text, encoding="utf-8")
print("patched memory/execution problem phrasing")
