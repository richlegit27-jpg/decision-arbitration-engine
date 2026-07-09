from pathlib import Path

path = Path("nova_backend/services/project_brain_general_intelligence.py")
text = path.read_text(encoding="utf-8")


def replace_function(source: str, name: str, body: str) -> str:
    start = source.index(f"def {name}(")
    next_start = source.find("\ndef ", start + 1)

    if next_start == -1:
        next_start = source.find("\n\ndef build_project_brain_general_answer", start + 1)

    if next_start == -1:
        raise SystemExit(f"could not find end for {name}")

    header_end = source.index(":\n", start) + 2
    return source[:header_end] + body + source[next_start:]


text = replace_function(
    text,
    "_current_project_answer",
    '''    from nova_backend.services.project_brain_context_builder import build_current_project_answer

    return build_current_project_answer()
''',
)

text = replace_function(
    text,
    "_safe_next_answer",
    '''    from nova_backend.services.project_brain_context_builder import build_safe_next_answer

    return build_safe_next_answer()
''',
)

text = replace_function(
    text,
    "_memory_execution_answer",
    '''    from nova_backend.services.project_brain_context_builder import build_memory_execution_answer

    return build_memory_execution_answer()
''',
)

text = replace_function(
    text,
    "_app_py_risk_answer",
    '''    from nova_backend.services.project_brain_context_builder import build_app_py_risk_answer

    return build_app_py_risk_answer()
''',
)

text = replace_function(
    text,
    "_practical_project_answer",
    '''    from nova_backend.services.project_brain_context_builder import build_practical_project_answer

    return build_practical_project_answer()
''',
)

path.write_text(text, encoding="utf-8")
print("project brain general intelligence now uses context builder")
