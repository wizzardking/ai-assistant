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
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

logger = logging.getLogger(__name__)


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

        header_font = QFont(self.font())
        header_font.setBold(True)
        header_font.setPointSize(header_font.pointSize() + 1)

        if prompt:
            prompt_label = QLabel(f"Prompt: {prompt}")
            prompt_label.setWordWrap(True)
            prompt_label.setFont(header_font)
            layout.addWidget(prompt_label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self._image_label = QLabel()
        self._image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._image_label.setPixmap(self._scaled_pixmap())
        scroll.setWidget(self._image_label)
        layout.addWidget(scroll, 1)

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

    def _scaled_pixmap(self) -> QPixmap:
        pix = QPixmap.fromImage(self._image)
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            return pix
        max_w = int(screen.availableGeometry().width() * 0.7)
        max_h = int(screen.availableGeometry().height() * 0.7)
        if pix.width() > max_w or pix.height() > max_h:
            pix = pix.scaled(
                max_w, max_h,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        return pix

    def _size_to_screen(self) -> None:
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            self.resize(800, 600)
            return
        geom = screen.availableGeometry()
        width = min(900, int(geom.width() * 0.7))
        height = min(800, int(geom.height() * 0.8))
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
