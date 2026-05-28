from __future__ import annotations

import logging
from typing import Any

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QGuiApplication, QTextCursor
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from ai_assistant.providers.openai import OpenAIProvider
from ai_assistant.worker import ModuleWorker

logger = logging.getLogger(__name__)


class ChatWindow(QDialog):
    """Free-form chat dialog with multi-turn history."""

    def __init__(
        self,
        model: str,
        system_prompt: str,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("AI Assistant – Chat")
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowCloseButtonHint
        )
        self.setModal(False)

        self._model = model
        self._messages: list[dict[str, Any]] = []
        if system_prompt:
            self._messages.append({"role": "system", "content": system_prompt})
        self._last_answer: str = ""
        self._worker: ModuleWorker | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 12)
        layout.setSpacing(10)

        header = QLabel("Chat")
        header_font = QFont(self.font())
        header_font.setPointSize(header_font.pointSize() + 2)
        header_font.setBold(True)
        header.setFont(header_font)
        layout.addWidget(header)

        self._history_view = QTextEdit()
        self._history_view.setReadOnly(True)
        body_font = QFont(self.font())
        body_font.setPointSize(body_font.pointSize() + 1)
        self._history_view.setFont(body_font)
        layout.addWidget(self._history_view, 1)

        self._status_label = QLabel("")
        self._status_label.setStyleSheet("color: #888;")
        layout.addWidget(self._status_label)

        layout.addWidget(QLabel("Deine Frage:"))
        self._input = QPlainTextEdit()
        self._input.setFont(body_font)
        self._input.setFixedHeight(110)
        self._input.installEventFilter(self)
        layout.addWidget(self._input)

        button_row = QHBoxLayout()
        button_row.addStretch()

        self._send_btn = QPushButton("Senden")
        self._send_btn.setDefault(True)
        self._send_btn.clicked.connect(self._on_send)
        button_row.addWidget(self._send_btn)

        self._new_btn = QPushButton("Neue Frage")
        self._new_btn.clicked.connect(self._on_new_question)
        button_row.addWidget(self._new_btn)

        self._copy_btn = QPushButton("Antwort kopieren")
        self._copy_btn.clicked.connect(self._on_copy_answer)
        self._copy_btn.setEnabled(False)
        button_row.addWidget(self._copy_btn)

        self._close_btn = QPushButton("Schließen")
        self._close_btn.clicked.connect(self.close)
        button_row.addWidget(self._close_btn)

        layout.addLayout(button_row)

        self._size_to_screen()
        self._input.setFocus()

    def eventFilter(self, obj, event) -> bool:
        # Ctrl+Enter (or Cmd+Enter) sends the question.
        if obj is self._input and event.type() == event.Type.KeyPress:
            if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and (
                event.modifiers() & Qt.KeyboardModifier.ControlModifier
            ):
                self._on_send()
                return True
        return super().eventFilter(obj, event)

    def _size_to_screen(self) -> None:
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            self.resize(720, 600)
            return
        geom = screen.availableGeometry()
        width = min(820, int(geom.width() * 0.65))
        height = min(720, int(geom.height() * 0.8))
        self.resize(width, height)
        self.move(
            geom.x() + (geom.width() - width) // 2,
            geom.y() + (geom.height() - height) // 2,
        )

    def _append_history(self, role: str, content: str) -> None:
        cursor = self._history_view.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        if self._history_view.toPlainText():
            cursor.insertText("\n\n")
        if role == "user":
            cursor.insertHtml(f"<b style='color:#88ddff;'>Du:</b><br>")
        else:
            cursor.insertHtml(f"<b style='color:#7cd07c;'>Assistent:</b><br>")
        cursor.insertText(content)
        self._history_view.setTextCursor(cursor)
        self._history_view.ensureCursorVisible()

    def _on_send(self) -> None:
        if self._worker is not None and self._worker.isRunning():
            return
        question = self._input.toPlainText().strip()
        if not question:
            return

        self._append_history("user", question)
        self._messages.append({"role": "user", "content": question})
        self._input.clear()
        self._status_label.setText("Antwort wird geladen…")
        self._send_btn.setEnabled(False)
        self._copy_btn.setEnabled(False)

        provider = OpenAIProvider()
        worker = ModuleWorker(provider.chat(list(self._messages), self._model))
        worker.finished_ok.connect(self._on_answer)
        worker.finished_error.connect(self._on_error)
        worker.finished.connect(worker.deleteLater)
        self._worker = worker
        worker.start()

    def _on_answer(self, result) -> None:
        answer = result if isinstance(result, str) else str(result)
        self._messages.append({"role": "assistant", "content": answer})
        self._append_history("assistant", answer)
        self._last_answer = answer
        self._status_label.setText("")
        self._send_btn.setEnabled(True)
        self._copy_btn.setEnabled(True)
        self._input.setFocus()

    def _on_error(self, message: str) -> None:
        logger.error("Chat error: %s", message)
        self._append_history("assistant", f"[Fehler: {message}]")
        self._status_label.setStyleSheet("color: #ff7777;")
        self._status_label.setText(f"Fehler: {message}")
        self._send_btn.setEnabled(True)

    def _on_copy_answer(self) -> None:
        if not self._last_answer:
            return
        clipboard = QGuiApplication.clipboard()
        if clipboard is not None:
            clipboard.setText(self._last_answer)
            self._status_label.setStyleSheet("color: #7cd07c;")
            self._status_label.setText("Letzte Antwort in Zwischenablage kopiert.")

    def _on_new_question(self) -> None:
        """Reset the conversation but keep the system prompt."""
        system = [m for m in self._messages if m["role"] == "system"]
        self._messages = system
        self._last_answer = ""
        self._history_view.clear()
        self._status_label.setStyleSheet("color: #888;")
        self._status_label.setText("Neue Unterhaltung gestartet.")
        self._copy_btn.setEnabled(False)
        self._input.clear()
        self._input.setFocus()
