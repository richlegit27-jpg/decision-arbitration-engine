from nova_backend.services.execution_handler import (
    ExecutionHandler,
    NextMove,
    default_executor,
)


def test_file_mutation_requires_explicit_replacement_code():
    handler = ExecutionHandler(service=None)

    result = handler._build_mutation_payload_from_step(
        {
            "target_file": "nova_backend/services/mutation_test.py",
            "target_files": ["nova_backend/services/mutation_test.py"],
            "mutation_mode": "file",
        }
    )

    assert result["ok"] is False
    assert "explicit replacement code" in result["error"]


def test_file_mutation_uses_provided_replacement_code():
    handler = ExecutionHandler(service=None)

    result = handler._build_mutation_payload_from_step(
        {
            "target_file": "nova_backend/services/mutation_test.py",
            "target_files": ["nova_backend/services/mutation_test.py"],
            "mutation_mode": "file",
            "code": "def mutation_test_value():\n    return 'after'",
        }
    )

    assert result["ok"] is True
    assert result["move_type"] == "fix_file"
    assert result["payload"]["code"] == (
        "def mutation_test_value():\n    return 'after'"
    )


def test_invalid_python_file_mutation_restores_the_original_file(tmp_path):
    target = tmp_path / "target.py"
    original = "def value():\n    return 'before'\n"
    target.write_text(original, encoding="utf-8")

    result = default_executor(
        NextMove(
            id="invalid-file-mutation",
            type="fix_file",
            payload={
                "file_path": str(target),
                "code": "def value(:\n    return 'broken'\n",
            },
        )
    )

    assert result.status == "failed"
    assert target.read_text(encoding="utf-8") == original
