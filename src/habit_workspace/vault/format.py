"""Bounded, inert YAML frontmatter with exact Markdown preservation."""

from copy import deepcopy
from io import StringIO

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError
from ruamel.yaml.events import (
    AliasEvent,
    CollectionEndEvent,
    CollectionStartEvent,
    DocumentStartEvent,
)

from habit_workspace.domain.documents import Document, DocumentError, require

MAX_DOCUMENT_BYTES = 2 * 1024 * 1024
MAX_FRONTMATTER_BYTES = 256 * 1024
STANDARD_TAGS = {
    f"tag:yaml.org,2002:{tag}"
    for tag in ("str", "null", "bool", "int", "float", "timestamp", "map", "seq")
}


def _yaml() -> YAML:
    parser = YAML(typ="rt", pure=True)
    parser.preserve_quotes = True
    parser.allow_duplicate_keys = False
    parser.width = 100
    return parser


def _preflight(frontmatter: str) -> None:
    depth = documents = 0
    for count, event in enumerate(_yaml().parse(frontmatter), 1):
        require(count <= 20000, "Frontmatter exceeds event limit")
        require(
            not isinstance(event, AliasEvent) and getattr(event, "anchor", None) is None,
            "YAML anchors and aliases are not supported",
        )
        tag = getattr(event, "tag", None)
        require(tag is None or tag in STANDARD_TAGS, "Unsafe or unsupported YAML tag")
        require(getattr(event, "value", None) != "<<", "YAML merge keys are not supported")
        if isinstance(event, CollectionStartEvent):
            depth += 1
            require(depth <= 32, "Frontmatter exceeds nesting limit")
        elif isinstance(event, CollectionEndEvent):
            depth -= 1
        elif isinstance(event, DocumentStartEvent):
            documents += 1
            require(documents == 1, "Multiple YAML documents are not supported")


def decode(raw: bytes) -> Document:
    require(len(raw) <= MAX_DOCUMENT_BYTES, "Document exceeds 2 MiB limit")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise DocumentError("Document is not valid UTF-8") from error
    lines = text.splitlines(keepends=True)
    require(bool(lines) and lines[0] in ("---\n", "---\r\n"), "Missing YAML frontmatter")
    end = next((i for i in range(1, len(lines)) if lines[i].rstrip("\r\n") == "---"), None)
    require(end is not None, "Unterminated YAML frontmatter")
    frontmatter = "".join(lines[1:end])
    require(
        len(frontmatter.encode("utf-8")) <= MAX_FRONTMATTER_BYTES,
        "Frontmatter exceeds 256 KiB limit",
    )
    try:
        _preflight(frontmatter)
        metadata = _yaml().load(frontmatter)
    except (YAMLError, ValueError, TypeError, OverflowError, KeyError) as error:
        if isinstance(error, DocumentError):
            raise
        raise DocumentError(f"Invalid YAML: {error}") from error
    body = "".join(lines[end + 1 :])
    document = Document.from_metadata(metadata, body)
    document.original_bytes = raw
    document.original_signature = deepcopy((metadata, body))
    document.newline = "\r\n" if lines[0].endswith("\r\n") else "\n"
    document.bom = raw.startswith(b"\xef\xbb\xbf")
    return document


def encode(document: Document) -> bytes:
    document.validate()
    # Exact no-op round trips retain whitespace, delimiters, comments and BOM.
    if document.original_bytes is not None and document.original_signature == (
        document.metadata,
        document.body,
    ):
        return document.original_bytes
    stream = StringIO()
    try:
        _yaml().dump(document.metadata, stream)
    except (YAMLError, TypeError, ValueError) as error:
        raise DocumentError(f"Cannot serialize metadata: {error}") from error
    frontmatter = stream.getvalue().replace("\n", document.newline)
    text = ("\ufeff" if document.bom else "") + "---" + document.newline
    text += frontmatter + "---" + document.newline + document.body
    raw = text.encode("utf-8")
    # Writers obey precisely the same limits and safe profile as readers.
    decode(raw)
    return raw
