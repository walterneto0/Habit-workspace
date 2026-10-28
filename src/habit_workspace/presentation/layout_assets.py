"""Bounded local raster decoding; QML receives pixels, never a vault URL."""

import base64
from pathlib import Path

from PySide6.QtCore import QBuffer, QByteArray, QIODevice
from PySide6.QtGui import QImageReader

from habit_workspace.domain.documents import DocumentError
from habit_workspace.vault.atomic_io import contained_path, read_bytes


def image_source(root: Path, relative: str) -> str:
    raw, _ = read_bytes(contained_path(root, relative))
    buffer = QBuffer()
    buffer.setData(raw)
    buffer.open(QIODevice.ReadOnly)
    reader = QImageReader(buffer)
    if bytes(reader.format()).lower() not in (b"png", b"jpeg", b"webp", b"gif"):
        raise DocumentError("Formato de imagem não suportado.")
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
