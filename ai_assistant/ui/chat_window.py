from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import html as html_lib

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QGuiApplication, QTextCursor, QTextDocument
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ai_assistant.chat_store import (
    Chat,
    ChatMessage,
    ChatStore,
    estimate_tokens,
    messages_token_estimate,
)
from ai_assistant.config import RESPONSE_TOKEN_RESERVE, token_limit_for
from ai_assistant.providers.openai import OpenAIProvider
from ai_assistant.worker import ModuleWorker

logger = logging.getLogger(__name__)


class _ChatListItem(QWidget):
    """Custom row widget for the chat sidebar: title label + delete button."""

    def __init__(self, title: str, on_delete) -> None:
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 4, 4)
        layout.setSpacing(6)

        self._label = QLabel(title)
        self._label.setWordWrap(False)
        self._label.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        self._label.setSizePolicy(self._label.sizePolicy().horizontalPolicy(),
                                  self._label.sizePolicy().verticalPolicy())
        layout.addWidget(self._label, 1)

        self._delete_btn = QToolButton()
        self._delete_btn.setText("×")
        self._delete_btn.setToolTip("Chat löschen")
        self._delete_btn.setAutoRaise(True)
        self._delete_btn.setStyleSheet(
            "QToolButton { color: #aaa; font-size: 16px; padding: 0 6px; }"
            "QToolButton:hover { color: #ff7777; }"
        )
        self._delete_btn.clicked.connect(on_delete)
        layout.addWidget(self._delete_btn)

    def set_title(self, title: str) -> None:
        self._label.setText(title)


class ChatWindow(QDialog):
    """Chat dialog with persistent sidebar of past conversations."""

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
        self._system_prompt = system_prompt
        self._store = ChatStore()
        self._current_chat: Chat | None = None
        self._worker: ModuleWorker | None = None
        self._sending: bool = False
        self._last_answer: str = ""

        self._build_ui()
        self._refresh_chat_list(select_id=None)

        # If no chats exist yet, start a fresh one so the user sees an empty
        # conversation ready to receive a message.
        if not self._store.chats:
            self._on_new_chat()
        else:
            self._select_chat(self._store.chats[0].id)

        self._size_to_screen()
        self._input.setFocus()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 10)
        outer.setSpacing(8)

        header = QLabel("Chat")
        header_font = QFont(self.font())
        header_font.setPointSize(header_font.pointSize() + 2)
        header_font.setBold(True)
        header.setFont(header_font)
        outer.addWidget(header)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        outer.addWidget(splitter, 1)

        # --- Sidebar -------------------------------------------------
        sidebar = QWidget()
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(6)

        sidebar_buttons = QHBoxLayout()
        self._new_chat_btn_sidebar = QPushButton("+ Neuer Chat")
        self._new_chat_btn_sidebar.clicked.connect(self._on_new_chat)
        sidebar_buttons.addWidget(self._new_chat_btn_sidebar)

        self._clear_all_btn = QPushButton("Alle löschen")
        self._clear_all_btn.clicked.connect(self._on_clear_all)
        sidebar_buttons.addWidget(self._clear_all_btn)
        sidebar_layout.addLayout(sidebar_buttons)

        self._chat_list = QListWidget()
        self._chat_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self._chat_list.itemClicked.connect(self._on_chat_item_clicked)
        sidebar_layout.addWidget(self._chat_list, 1)

        splitter.addWidget(sidebar)

        # --- Conversation pane --------------------------------------
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)

        self._title_label = QLabel("")
        title_font = QFont(self.font())
        title_font.setBold(True)
        self._title_label.setFont(title_font)
        right_layout.addWidget(self._title_label)

        self._history_view = QTextEdit()
        self._history_view.setReadOnly(True)
        body_font = QFont(self.font())
        body_font.setPointSize(body_font.pointSize() + 1)
        self._history_view.setFont(body_font)
        right_layout.addWidget(self._history_view, 1)

        self._status_label = QLabel("")
        self._status_label.setStyleSheet("color: #888;")
        right_layout.addWidget(self._status_label)

        right_layout.addWidget(QLabel("Deine Nachricht (Strg+Enter zum Senden):"))
        self._input = QPlainTextEdit()
        self._input.setFont(body_font)
        self._input.setFixedHeight(110)
        self._input.installEventFilter(self)
        right_layout.addWidget(self._input)

        button_row = QHBoxLayout()
        button_row.addStretch()

        self._send_btn = QPushButton("Senden")
        self._send_btn.setDefault(True)
        self._send_btn.clicked.connect(self._on_send)
        button_row.addWidget(self._send_btn)

        self._new_chat_btn = QPushButton("Neuer Chat")
        self._new_chat_btn.clicked.connect(self._on_new_chat)
        button_row.addWidget(self._new_chat_btn)

        self._copy_btn = QPushButton("Antwort kopieren")
        self._copy_btn.clicked.connect(self._on_copy_answer)
        self._copy_btn.setEnabled(False)
        button_row.addWidget(self._copy_btn)

        self._close_btn = QPushButton("Schließen")
        self._close_btn.clicked.connect(self.close)
        button_row.addWidget(self._close_btn)

        right_layout.addLayout(button_row)
        splitter.addWidget(right)

        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([220, 680])

    def _size_to_screen(self) -> None:
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            self.resize(920, 640)
            return
        geom = screen.availableGeometry()
        width = min(1000, int(geom.width() * 0.7))
        height = min(740, int(geom.height() * 0.8))
        self.resize(width, height)
        self.move(
            geom.x() + (geom.width() - width) // 2,
            geom.y() + (geom.height() - height) // 2,
        )

    # ------------------------------------------------------------------
    # Sidebar / chat list handling
    # ------------------------------------------------------------------

    def _refresh_chat_list(self, select_id: str | None) -> None:
        self._chat_list.clear()
        for chat in self._store.chats:
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, chat.id)
            item.setToolTip(chat.title)
            widget = _ChatListItem(
                title=chat.title or "Neuer Chat",
                on_delete=lambda _checked=False, cid=chat.id: self._on_delete_chat(cid),
            )
            item.setSizeHint(widget.sizeHint())
            self._chat_list.addItem(item)
            self._chat_list.setItemWidget(item, widget)
            if select_id == chat.id:
                self._chat_list.setCurrentItem(item)

    def _on_chat_item_clicked(self, item: QListWidgetItem) -> None:
        chat_id = item.data(Qt.ItemDataRole.UserRole)
        if chat_id:
            self._select_chat(chat_id)

    def _on_delete_chat(self, chat_id: str) -> None:
        chat = self._store.get(chat_id)
        if chat is None:
            return
        confirm = QMessageBox.question(
            self,
            "Chat löschen",
            f'Den Chat "{chat.title}" wirklich löschen?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        was_current = self._current_chat is not None and self._current_chat.id == chat_id
        self._store.delete_chat(chat_id)
        if was_current:
            self._current_chat = None
        if not self._store.chats:
            self._on_new_chat()
        else:
            next_id = self._store.chats[0].id if was_current else (
                self._current_chat.id if self._current_chat else self._store.chats[0].id
            )
            self._refresh_chat_list(select_id=next_id)
            self._select_chat(next_id)

    def _on_clear_all(self) -> None:
        if not self._store.chats:
            return
        confirm = QMessageBox.question(
            self,
            "Alle Chats löschen",
            "Wirklich alle gespeicherten Chats löschen? Dies kann nicht rückgängig gemacht werden.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        self._store.clear()
        self._current_chat = None
        self._on_new_chat()

    def _on_new_chat(self) -> None:
        chat = self._store.create_chat(model=self._model, system_prompt=self._system_prompt)
        self._refresh_chat_list(select_id=chat.id)
        self._select_chat(chat.id)
        self._input.setFocus()

    # ------------------------------------------------------------------
    # Conversation rendering
    # ------------------------------------------------------------------

    def _select_chat(self, chat_id: str) -> None:
        chat = self._store.get(chat_id)
        if chat is None:
            return
        self._current_chat = chat
        self._title_label.setText(chat.title or "Neuer Chat")
        self._render_history()
        self._update_last_answer()
        self._status_label.setStyleSheet("color: #888;")
        self._status_label.setText("")
        # Sync selection in the sidebar.
        for i in range(self._chat_list.count()):
            item = self._chat_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == chat_id:
                self._chat_list.setCurrentItem(item)
                break

    def _render_history(self) -> None:
        self._history_view.clear()
        if self._current_chat is None:
            return
        for msg in self._current_chat.messages:
            self._append_history_view(msg.role, msg.content, msg.timestamp)

    def _append_history_view(self, role: str, content: str, timestamp: str) -> None:
        cursor = self._history_view.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        if self._history_view.toPlainText():
            cursor.insertText("\n\n")

        ts = self._format_timestamp(timestamp)
        if role == "user":
            header = (
                f"<b style='color:#88ddff;'>Du</b> "
                f"<span style='color:#888;'>– {ts}</span>"
            )
        elif role == "assistant":
            header = (
                f"<b style='color:#7cd07c;'>Assistent</b> "
                f"<span style='color:#888;'>– {ts}</span>"
            )
        else:
            header = (
                f"<b style='color:#bbbbbb;'>{role}</b> "
                f"<span style='color:#888;'>– {ts}</span>"
            )
        cursor.insertHtml(header + "<br>")
        if role == "assistant":
            body_html = self._markdown_to_html(content)
        else:
            body_html = self._plaintext_to_html(content)
        cursor.insertHtml(body_html)
        self._history_view.setTextCursor(cursor)
        self._history_view.ensureCursorVisible()

    @staticmethod
    def _markdown_to_html(text: str) -> str:
        """Render Markdown to HTML using Qt's built-in renderer."""
        if not text:
            return ""
        doc = QTextDocument()
        doc.setMarkdown(text)
        html = doc.toHtml()
        # toHtml() returns a full document; extract only the body content
        # so it can be embedded into the existing QTextEdit without disturbing
        # surrounding markup.
        start = html.find("<body")
        end = html.rfind("</body>")
        if start != -1 and end != -1:
            body_open_close = html.find(">", start)
            if body_open_close != -1 and body_open_close < end:
                return html[body_open_close + 1:end].strip()
        return html

    @staticmethod
    def _plaintext_to_html(text: str) -> str:
        if not text:
            return ""
        escaped = html_lib.escape(text)
        return escaped.replace("\n", "<br>")

    @staticmethod
    def _format_timestamp(ts: str) -> str:
        try:
            return datetime.fromisoformat(ts).strftime("%d.%m.%Y %H:%M:%S")
        except Exception:
            return ts

    def _update_last_answer(self) -> None:
        self._last_answer = ""
        if self._current_chat is None:
            self._copy_btn.setEnabled(False)
            return
        for msg in reversed(self._current_chat.messages):
            if msg.role == "assistant":
                self._last_answer = msg.content
                break
        self._copy_btn.setEnabled(bool(self._last_answer))

    # ------------------------------------------------------------------
    # Sending
    # ------------------------------------------------------------------

    def eventFilter(self, obj, event) -> bool:
        if obj is self._input and event.type() == event.Type.KeyPress:
            if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and (
                event.modifiers() & Qt.KeyboardModifier.ControlModifier
            ):
                self._on_send()
                return True
        return super().eventFilter(obj, event)

    def _build_api_messages(self, chat: Chat, new_user_message: str) -> list[dict[str, Any]]:
        """Compose the message list that is sent to the model.

        The full history (with timestamps) is supplied as context. Timestamps
        are inlined as a prefix in each user/assistant message content.
        """
        messages: list[dict[str, Any]] = []
        if chat.system_prompt:
            messages.append({"role": "system", "content": chat.system_prompt})
        for msg in chat.messages:
            ts = self._format_timestamp(msg.timestamp)
            messages.append({
                "role": msg.role,
                "content": f"[{ts}] {msg.content}",
            })
        new_ts = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        messages.append({"role": "user", "content": f"[{new_ts}] {new_user_message}"})
        return messages

    def _on_send(self) -> None:
        if self._sending:
            return
        if self._current_chat is None:
            self._on_new_chat()
            if self._current_chat is None:
                return

        question = self._input.toPlainText().strip()
        if not question:
            return

        api_messages = self._build_api_messages(self._current_chat, question)
        used_tokens = messages_token_estimate(api_messages) + RESPONSE_TOKEN_RESERVE
        limit = token_limit_for(self._model)
        if used_tokens > limit:
            QMessageBox.warning(
                self,
                "Kontextlänge überschritten",
                (
                    f"Der Chat ist mit geschätzten {used_tokens:,} Tokens länger "
                    f"als das Kontextfenster des Modells {self._model} ({limit:,} Tokens). "
                    "Bitte einen neuen Chat starten."
                ).replace(",", "."),
            )
            return

        now = datetime.now().isoformat(timespec="seconds")
        self._current_chat.messages.append(
            ChatMessage(role="user", content=question, timestamp=now)
        )
        self._current_chat.touch()
        if self._current_chat.title == "Neuer Chat":
            self._current_chat.title = self._current_chat.derive_title()
        self._store.update_chat(self._current_chat)

        self._append_history_view("user", question, now)
        self._input.clear()
        self._status_label.setStyleSheet("color: #888;")
        self._status_label.setText(
            f"Antwort wird geladen… (≈{used_tokens:,} Tokens im Kontext)".replace(",", ".")
        )
        self._sending = True
        self._send_btn.setEnabled(False)
        self._copy_btn.setEnabled(False)

        provider = OpenAIProvider()
        worker = ModuleWorker(provider.chat(api_messages, self._model))
        worker.finished_ok.connect(self._on_answer)
        worker.finished_error.connect(self._on_error)
        worker.finished.connect(worker.deleteLater)
        worker.finished.connect(lambda: setattr(self, "_worker", None))
        self._worker = worker
        worker.start()
        self._refresh_chat_list(select_id=self._current_chat.id)

    def _on_answer(self, result) -> None:
        self._sending = False
        if self._current_chat is None:
            self._send_btn.setEnabled(True)
            return
        answer = result if isinstance(result, str) else str(result)
        now = datetime.now().isoformat(timespec="seconds")
        self._current_chat.messages.append(
            ChatMessage(role="assistant", content=answer, timestamp=now)
        )
        self._current_chat.touch()
        self._store.update_chat(self._current_chat)
        self._append_history_view("assistant", answer, now)
        self._last_answer = answer
        self._copy_btn.setEnabled(True)
        self._send_btn.setEnabled(True)
        self._status_label.setText("")
        self._input.setFocus()
        self._refresh_chat_list(select_id=self._current_chat.id)

    def _on_error(self, message: str) -> None:
        self._sending = False
        logger.error("Chat error: %s", message)
        now = datetime.now().isoformat(timespec="seconds")
        self._append_history_view("assistant", f"[Fehler: {message}]", now)
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
