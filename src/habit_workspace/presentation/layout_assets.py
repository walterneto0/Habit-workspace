"""Bounded local raster decoding; QML receives pixels, never a vault URL."""

import base64
import re
from collections import OrderedDict
from pathlib import Path
from threading import RLock
from uuid import uuid4

from PySide6.QtCore import QBuffer, QByteArray, QIODevice
from PySide6.QtGui import QImageReader

from habit_workspace.domain.documents import DocumentError, require
from habit_workspace.domain.layouts.components import ImageConfig
from habit_workspace.vault.atomic_io import atomic_write, contained_path, read_bytes

# At most 64 MiB encoded pixels. Keys include ctime to invalidate external edits.
_CACHE = OrderedDict()
_CACHE_LOCK = RLock()
_CACHE_BYTES = 64 * 1024 * 1024
_FORMATS = {".png": b"png", ".jpg": b"jpeg", ".jpeg": b"jpeg", ".webp": b"webp", ".gif": b"gif"}
IMAGE_LINK = re.compile(r"!\[((?:\\.|[^\]\\])*)\]\(([^)\r\n]*)\)")


def _decode(raw: bytes, suffix: str) -> str:
    buffer = QBuffer()
    buffer.setData(raw)
    buffer.open(QIODevice.ReadOnly)
    reader = QImageReader(buffer)
    require(
        suffix.lower() in _FORMATS and bytes(reader.format()).lower() == _FORMATS[suffix.lower()],
        "Formato real e extensão da imagem incompatíveis.",
    )
    size = reader.size()
    if size.width() <= 0 or size.height() <= 0 or size.width() * size.height() > 4_000_000:
        raise DocumentError("Imagem excede o limite de 4 milhões de pixels.")
    image = reader.read()
    if image.isNull():
        raise DocumentError("Imagem inválida.")
    encoded = QByteArray()
    output = QBuffer(encoded)
    output.open(QIODevice.WriteOnly)
    if not image.save(output, "PNG"):
        raise DocumentError("Não foi possível apresentar a imagem.")
    return "data:image/png;base64," + base64.b64encode(bytes(encoded)).decode("ascii")


def image_source(root: Path, relative: str) -> str:
    try:
        ImageConfig(relative)
    except ValueError as error:
        raise DocumentError(str(error)) from error
    path = contained_path(root, relative)
    info = path.stat()
    key = (
        str(path.absolute()),
        info.st_dev,
        info.st_ino,
        info.st_size,
        info.st_mtime_ns,
        info.st_ctime_ns,
    )
    with _CACHE_LOCK:
        if key in _CACHE:
            _CACHE.move_to_end(key)
            return _CACHE[key]
    raw, _ = read_bytes(path)
    source = _decode(raw, path.suffix)
    with _CACHE_LOCK:
        if len(source) <= _CACHE_BYTES:
            _CACHE[key] = source
            while sum(map(len, _CACHE.values())) > _CACHE_BYTES:
                _CACHE.popitem(last=False)
    return source


def import_image(root: Path, source: Path) -> str:
    source = Path(source)
    require(source.is_absolute(), "Selecione um arquivo local absoluto.")
    require(
        not any(p.is_symlink() for p in (source, *source.parents)),
        "Links simbólicos não são permitidos.",
    )
    raw, _ = read_bytes(source)
    pixels = _decode(raw, source.suffix)
    relative = f"Assets/{uuid4()}{source.suffix.lower()}"
    destination = contained_path(root, relative)
    atomic_write(destination, raw)
    # Seed the bounded cache, so the first GUI presentation does not decode again.
    info = destination.stat()
    key = (
        str(destination.absolute()),
        info.st_dev,
        info.st_ino,
        info.st_size,
        info.st_mtime_ns,
        info.st_ctime_ns,
    )
    with _CACHE_LOCK:
        if len(pixels) <= _CACHE_BYTES:
            _CACHE[key] = pixels
            while sum(map(len, _CACHE.values())) > _CACHE_BYTES:
                _CACHE.popitem(last=False)
    return relative


def markdown_images(root: Path, body: str) -> list[dict]:
    rows = []
    for match in list(IMAGE_LINK.finditer(body))[:64]:
        alt, path = match.groups()
        row = dict(alt=re.sub(r"\\(.)", r"\1", alt), path=path, source="", error="")
        try:
            require(path.startswith("Assets/"), "Somente imagens locais em Assets/ são permitidas.")
            row["source"] = image_source(root, path)
        except (OSError, ValueError) as error:
            row["error"] = "Imagem indisponível: " + str(error)
        rows.append(row)
    return rows


def image_markdown(path: str, alt: str) -> str:
    ImageConfig(path)
    escaped = alt.replace("\\", "\\\\").replace("[", "\\[").replace("]", "\\]")
    escaped = escaped.replace("\r", " ").replace("\n", " ")
    return f"![{escaped}]({path})"
