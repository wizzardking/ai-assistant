from __future__ import annotations

from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QVBoxLayout,
)


_QUALITY_LABELS: dict[str, str] = {
    "auto": "Auto",
    "high": "Hoch",
    "medium": "Mittel",
    "low": "Niedrig",
}


class ImagePromptDialog(QDialog):
    """Dialog asking for an image prompt, the desired output size and quality."""

    def __init__(
        self,
        prompt_label: str,
        default_size: str,
        available_sizes: list[str],
        default_quality: str,
        available_qualities: list[str],
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("AI Assistant – Bild generieren")
        self.setModal(True)
        self.resize(600, 320)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 12)
        layout.setSpacing(8)

        intro = QLabel(prompt_label)
        intro.setWordWrap(True)
        layout.addWidget(intro)

        self._prompt_edit = QPlainTextEdit()
        body_font = QFont(self.font())
        body_font.setPointSize(body_font.pointSize() + 1)
        self._prompt_edit.setFont(body_font)
        self._prompt_edit.setMinimumHeight(120)
        layout.addWidget(self._prompt_edit, 1)

        options_row = QHBoxLayout()

        options_row.addWidget(QLabel("Größe:"))
        self._size_combo = QComboBox()
        self._size_combo.addItems(available_sizes)
        if default_size in available_sizes:
            self._size_combo.setCurrentText(default_size)
        elif default_size:
            self._size_combo.setEditable(True)
            self._size_combo.setCurrentText(default_size)
        options_row.addWidget(self._size_combo, 1)

        options_row.addSpacing(12)

        options_row.addWidget(QLabel("Qualität:"))
        self._quality_combo = QComboBox()
        for q in available_qualities:
            self._quality_combo.addItem(_QUALITY_LABELS.get(q, q.capitalize()), userData=q)
        idx = self._quality_combo.findData(default_quality)
        if idx < 0:
            idx = self._quality_combo.findData("auto")
        if idx >= 0:
            self._quality_combo.setCurrentIndex(idx)
        options_row.addWidget(self._quality_combo, 1)

        layout.addLayout(options_row)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Generieren")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._prompt_edit.setFocus()

    def prompt_text(self) -> str:
        return self._prompt_edit.toPlainText().strip()

    def selected_size(self) -> str:
        return self._size_combo.currentText().strip()

    def selected_quality(self) -> str:
        data = self._quality_combo.currentData()
        if isinstance(data, str) and data:
            return data
        return self._quality_combo.currentText().strip().lower() or "auto"
