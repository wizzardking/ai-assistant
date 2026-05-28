from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QGuiApplication
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)


class ResultWindow(QDialog):
    """Non-modal window that shows a generated text result with copy & close actions."""

    def __init__(self, title: str, text: str, copy_callback=None, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"AI Assistant – {title}")
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowCloseButtonHint
        )
        self.setModal(False)

        self._copy_callback = copy_callback
        self._text = text

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 12)
        layout.setSpacing(10)

        header = QLabel(title)
        header_font = QFont(self.font())
        header_font.setPointSize(header_font.pointSize() + 2)
        header_font.setBold(True)
        header.setFont(header_font)
        layout.addWidget(header)

        self._text_view = QPlainTextEdit()
        self._text_view.setPlainText(text)
        self._text_view.setReadOnly(True)
        self._text_view.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        body_font = QFont(self.font())
        body_font.setPointSize(body_font.pointSize() + 1)
        self._text_view.setFont(body_font)
        layout.addWidget(self._text_view, 1)

        self._status_label = QLabel("")
        self._status_label.setStyleSheet("color: #7cd07c;")
        layout.addWidget(self._status_label)

        button_row = QHBoxLayout()
        button_row.addStretch()

        self._copy_btn = QPushButton("Kopieren")
        self._copy_btn.setDefault(True)
        self._copy_btn.clicked.connect(self._on_copy)
        button_row.addWidget(self._copy_btn)

        self._close_btn = QPushButton("Schließen")
        self._close_btn.clicked.connect(self.close)
        button_row.addWidget(self._close_btn)

        layout.addLayout(button_row)

        self._size_to_screen()

    def _size_to_screen(self) -> None:
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            self.resize(640, 480)
            return
        geom = screen.availableGeometry()
        width = min(720, int(geom.width() * 0.6))
        height = min(560, int(geom.height() * 0.6))
        self.resize(width, height)
        self.move(
            geom.x() + (geom.width() - width) // 2,
            geom.y() + (geom.height() - height) // 2,
        )

    def _on_copy(self) -> None:
        try:
            if self._copy_callback is not None:
                self._copy_callback(self._text)
            else:
                clipboard = QGuiApplication.clipboard()
                if clipboard is not None:
                    clipboard.setText(self._text)
            self._status_label.setText("In Zwischenablage kopiert.")
        except Exception as exc:  # pragma: no cover
            self._status_label.setStyleSheet("color: #ff7777;")
            self._status_label.setText(f"Kopieren fehlgeschlagen: {exc}")
