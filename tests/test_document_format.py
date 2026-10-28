import pytest
from test_vault import day, habit, note

from habit_workspace.domain.documents import DocumentError
from habit_workspace.vault.format import decode, encode


@pytest.mark.parametrize(
    "field,value",
    [
        ("id", "bad"),
        ("schema_version", True),
        ("schema_version", 999),
        ("kind", "executable"),
        ("tags", "a tag"),
        ("title", 42),
        ("origin_page_id", "../../outside"),
    ],
)
def test_strict_known_metadata(field, value):
    document = note()
    document.metadata["hw"][field] = value
    with pytest.raises(DocumentError):
        encode(document)


def test_period_and_scope_validation():
    document = habit(note().id)
    document.metadata["hw"]["scope"]["end_exclusive"] = "2026-09-01"
    with pytest.raises(DocumentError):
        encode(document)
    document = day(note().id)
    document.metadata["hw"]["date"] = "2026-02-30"
    with pytest.raises(DocumentError):
        encode(document)


def test_history_cannot_have_simultaneous_activation():
    document = note()
    assignment = {
        "layout_id": str(note().id),
        "version": 1,
        "effective_at": "2026-10-29T10:00:00-03:00",
    }
    document.metadata["hw"]["layout_history"] = [assignment, dict(assignment, version=2)]
    with pytest.raises(DocumentError):
        encode(document)


def test_size_depth_tags_and_unsupported_versions():
    for raw in [
        b"x" * (2 * 1024 * 1024 + 1),
        b"---\nx: " + b"[" * 40 + b"0" + b"]" * 40 + b"\n---\n",
        b"---\nx: !custom text\n---\n",
        b"---\nx: .nan\n---\n",
    ]:
        with pytest.raises(DocumentError):
            decode(raw)
    raw = encode(note()).replace(b"schema_version: 4", b"schema_version: 3")
    with pytest.raises(DocumentError, match="Unsupported"):
        decode(raw)


def test_unknown_block_survives_a_known_field_edit():
    document = note()
    document.metadata["hw"]["blocks"] = [{"type": "future-widget", "data": {"x": [1, 2]}}]
    loaded = decode(encode(document))
    loaded.metadata["hw"]["title"] = "New title"
    assert decode(encode(loaded)).metadata["hw"]["blocks"] == document.metadata["hw"]["blocks"]


@pytest.mark.parametrize("value", ["!!bool invalid", "!!int bad", "!!timestamp bad"])
def test_invalid_explicit_scalar_is_a_safe_parser_error(value):
    with pytest.raises(DocumentError):
        decode(f"---\nx: {value}\n---\n".encode())
