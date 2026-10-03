from __future__ import annotations

import pytest

from nova_backend.core.json_store import read_json
from nova_backend.utils.file_utils import load_json_file


@pytest.mark.parametrize("reader", [load_json_file, read_json])
def test_corrupt_existing_json_is_preserved_and_not_returned_as_default(
    tmp_path,
    reader,
):
    store = tmp_path / "user-data.json"
    corrupt_bytes = b'{"users": [broken'
    store.write_bytes(corrupt_bytes)

    with pytest.raises(ValueError, match="Unable to read JSON store"):
        reader(store, {"users": []})

    assert store.read_bytes() == corrupt_bytes


@pytest.mark.parametrize("reader", [load_json_file, read_json])
@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        (b'{"plans": [{"id": "valid"}]}', {"plans": [{"id": "valid"}]}),
        (b'\xef\xbb\xbf{"plans": [{"id": "bom"}]}', {"plans": [{"id": "bom"}]}),
    ],
)
def test_valid_json_with_or_without_utf8_bom_loads(tmp_path, reader, payload, expected):
    store = tmp_path / "planner_plans.json"
    store.write_bytes(payload)

    assert reader(store, {"plans": []}) == expected
