import base64

import pytest

from habit_workspace.domain.documents import DocumentError
from habit_workspace.presentation.layout_assets import image_source


def test_local_image_and_unsafe_paths(tmp_path):
    raw = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a9X8AAAAASUVORK5CYII="
    )
    # Generate a valid PNG with Qt, avoiding any external fixture.
    from PySide6.QtGui import QImage

    image = QImage(8, 8, QImage.Format_RGB32)
    image.fill(0)
    assert image.save(str(tmp_path / "local.png"))
    assert image_source(tmp_path, "local.png").startswith("data:image/png;base64,")
    for path in ("../local.png", "/tmp/local.png", "https://example.com/a.png"):
        with pytest.raises((DocumentError, OSError)):
            image_source(tmp_path, path)
    (tmp_path / "bad.png").write_bytes(raw[:20])
    with pytest.raises(DocumentError):
        image_source(tmp_path, "bad.png")
    (tmp_path / "link.png").symlink_to(tmp_path / "local.png")
    with pytest.raises(DocumentError):
        image_source(tmp_path, "link.png")
