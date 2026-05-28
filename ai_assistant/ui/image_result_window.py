from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QGuiApplication, QImage, QPixmap
from PyQt6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
)

logger = logging.getLogger(__name__)


class _AspectImageLabel(QLabel):
    """QLabel that always shows its pixmap scaled proportionally to fit the widget."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._source: QPixmap | None = None
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(1, 1)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        self.setStyleSheet("background: #111;")

    def set_source(self, pixmap: QPixmap) -> None:
        self._source = pixmap
        self._refresh()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._refresh()

    def _refresh(self) -> None:
        if self._source is None or self._source.isNull():
            return
        target = self.size()
        if target.width() <= 0 or target.height() <= 0:
            return
        scaled = self._source.scaled(
            target,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.setPixmap(scaled)


class ImageResultWindow(QDialog):
    """Shows a generated image with Save / Copy / Close buttons."""

    def __init__(
        self,
        prompt: str,
        image_bytes: bytes,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("AI Assistant – Generiertes Bild")
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowCloseButtonHint
        )
        self.setModal(False)

        self._image_bytes = image_bytes
        self._prompt = prompt
        self._image = QImage()
        self._image.loadFromData(image_bytes)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 12)
        layout.setSpacing(10)

        if prompt:
            header_font = QFont(self.font())
            header_font.setBold(True)
            header_font.setPointSize(header_font.pointSize() + 1)
            prompt_label = QLabel(f"Prompt: {prompt}")
            prompt_label.setWordWrap(True)
            prompt_label.setFont(header_font)
            layout.addWidget(prompt_label)

        self._image_label = _AspectImageLabel()
        if not self._image.isNull():
            self._image_label.set_source(QPixmap.fromImage(self._image))
        layout.addWidget(self._image_label, 1)

        self._status_label = QLabel("")
        self._status_label.setStyleSheet("color: #7cd07c;")
        layout.addWidget(self._status_label)

        button_row = QHBoxLayout()
        button_row.addStretch()

        save_btn = QPushButton("Speichern…")
        save_btn.clicked.connect(self._on_save)
        button_row.addWidget(save_btn)

        copy_btn = QPushButton("In Zwischenablage")
        copy_btn.clicked.connect(self._on_copy)
        button_row.addWidget(copy_btn)

        close_btn = QPushButton("Schließen")
        close_btn.clicked.connect(self.close)
        button_row.addWidget(close_btn)

        layout.addLayout(button_row)

        self._size_to_screen()

    def _size_to_screen(self) -> None:
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            self.resize(900, 700)
            return
        geom = screen.availableGeometry()

        # Pick a window size that fits the image's aspect ratio without exceeding
        # 80% of the available screen area.
        max_w = int(geom.width() * 0.8)
        max_h = int(geom.height() * 0.85)
        if self._image.isNull() or self._image.width() == 0 or self._image.height() == 0:
            width, height = min(900, max_w), min(700, max_h)
        else:
            aspect = self._image.width() / self._image.height()
            chrome_w = 60   # margins
            chrome_h = 160  # header + buttons + margins
            avail_w = max_w - chrome_w
            avail_h = max_h - chrome_h
            content_w = avail_w
            content_h = int(content_w / aspect)
            if content_h > avail_h:
                content_h = avail_h
                content_w = int(content_h * aspect)
            width = content_w + chrome_w
            height = content_h + chrome_h
            width = max(640, min(width, max_w))
            height = max(520, min(height, max_h))

        self.resize(width, height)
        self.move(
            geom.x() + (geom.width() - width) // 2,
            geom.y() + (geom.height() - height) // 2,
        )

    def _default_filename(self) -> str:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"ai-image-{stamp}.png"

    def _on_save(self) -> None:
        default_dir = Path.home() / "Pictures"
        if not default_dir.is_dir():
            default_dir = Path.home()
        suggested = str(default_dir / self._default_filename())
        path, _ = QFileDialog.getSaveFileName(
            self, "Bild speichern", suggested, "PNG (*.png);;JPEG (*.jpg *.jpeg)"
        )
        if not path:
            return
        try:
            Path(path).write_bytes(self._image_bytes)
            self._status_label.setStyleSheet("color: #7cd07c;")
            self._status_label.setText(f"Gespeichert: {path}")
        except Exception as exc:
            logger.exception("Saving image failed")
            QMessageBox.warning(self, "Speichern", f"Speichern fehlgeschlagen:\n{exc}")

    def _on_copy(self) -> None:
        try:
            clipboard = QGuiApplication.clipboard()
            if clipboard is not None:
                clipboard.setImage(self._image)
            self._status_label.setStyleSheet("color: #7cd07c;")
            self._status_label.setText("Bild in Zwischenablage kopiert.")
        except Exception as exc:
            logger.exception("Copying image failed")
            QMessageBox.warning(self, "Kopieren", f"Kopieren fehlgeschlagen:\n{exc}")
