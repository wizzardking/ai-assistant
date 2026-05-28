from __future__ import annotations

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPainter
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import QWidget


class StatusOverlay(QWidget):
    LOADING = "loading"
    DONE = "done"
    ERROR = "error"
    INFO = "info"

    _HIDE_MS = {
        DONE: 2000,
        ERROR: 3000,
        INFO: 2000,
    }

    def __init__(self) -> None:
        super().__init__(
            None,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(32, 32)

        self._rotation = 0
        self._spin_timer = QTimer(self)
        self._spin_timer.timeout.connect(self._rotate_loading)
        self._spin_timer.setInterval(50)

        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self.hide)

        self._current_state = ""
        self._current_icon = ""
        self._cursor_x = 0
        self._cursor_y = 0

    def show_at(self, x: int, y: int, state: str, icon_path: str, message: str = "") -> None:
        self._cursor_x = x
        self._cursor_y = y
        self._current_state = state
        self._current_icon = icon_path
        self.setToolTip(message)
        self._position()
        self.update()
        self.show()
        self.raise_()

        self._hide_timer.stop()
        self._spin_timer.stop()

        if state == self.LOADING:
            self._spin_timer.start()
        elif state in self._HIDE_MS:
            self._hide_timer.start(self._HIDE_MS[state])

    def _position(self) -> None:
        self.move(self._cursor_x + 16, self._cursor_y - 16)

    def _rotate_loading(self) -> None:
        if self._current_state != self.LOADING:
            return
        self._rotation = (self._rotation + 30) % 360
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if self._current_state == self.LOADING:
            painter.translate(self.width() / 2, self.height() / 2)
            painter.rotate(self._rotation)
            painter.translate(-self.width() / 2, -self.height() / 2)

        renderer = QSvgRenderer(self._current_icon)
        renderer.render(painter)

    @staticmethod
    def icon_path(name: str) -> str:
        from ai_assistant.modules.base import assets_dir

        return str(assets_dir() / f"{name}.svg")
