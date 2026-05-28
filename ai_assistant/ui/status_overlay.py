from __future__ import annotations

from PyQt6.QtCore import QPointF, QRectF, Qt, QTimer
from PyQt6.QtGui import QColor, QCursor, QFont, QPainter
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

    # Layout constants for the overlay surface.
    _ICON_SIZE = 32
    _TEXT_WIDTH = 32   # space reserved for the "AI" label
    _PADDING = 6
    _WIDTH = _ICON_SIZE + _TEXT_WIDTH + _PADDING * 2
    _HEIGHT = _ICON_SIZE + _PADDING * 2

    def __init__(self) -> None:
        super().__init__(
            None,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setFixedSize(self._WIDTH, self._HEIGHT)

        self._rotation = 0
        self._spin_timer = QTimer(self)
        self._spin_timer.timeout.connect(self._rotate_loading)
        self._spin_timer.setInterval(40)

        self._follow_timer = QTimer(self)
        self._follow_timer.timeout.connect(self._follow_cursor)
        self._follow_timer.setInterval(16)  # ~60 Hz

        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self.hide)

        self._current_state = ""
        self._current_icon = ""
        self._anchor_x = 0
        self._anchor_y = 0

    def show_at(self, x: int, y: int, state: str, icon_path: str, message: str = "") -> None:
        self._anchor_x = x
        self._anchor_y = y
        self._current_state = state
        self._current_icon = icon_path
        self.setToolTip(message)

        self._hide_timer.stop()
        self._spin_timer.stop()
        self._follow_timer.stop()

        if state == self.LOADING:
            # Stick to the live cursor while a request is running.
            self._follow_cursor()
            self._follow_timer.start()
            self._spin_timer.start()
        else:
            self._move_to(x, y)
            if state in self._HIDE_MS:
                self._hide_timer.start(self._HIDE_MS[state])

        self.update()
        self.show()
        self.raise_()

    def hide(self) -> None:
        self._spin_timer.stop()
        self._follow_timer.stop()
        super().hide()

    def _move_to(self, x: int, y: int) -> None:
        # Place to the right of (and slightly above) the given cursor position.
        self.move(x + 16, y - 16)

    def _follow_cursor(self) -> None:
        pos = QCursor.pos()
        self._move_to(pos.x(), pos.y())

    def _rotate_loading(self) -> None:
        if self._current_state != self.LOADING:
            return
        self._rotation = (self._rotation + 30) % 360
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        icon_rect = QRectF(
            self._PADDING,
            self._PADDING,
            self._ICON_SIZE,
            self._ICON_SIZE,
        )

        # Draw the icon (spinning during loading) inside icon_rect.
        if self._current_icon:
            painter.save()
            if self._current_state == self.LOADING:
                center = icon_rect.center()
                painter.translate(center)
                painter.rotate(self._rotation)
                painter.translate(-center)
            renderer = QSvgRenderer(self._current_icon)
            renderer.render(painter, icon_rect)
            painter.restore()

        # Draw the "AI" label to the right of the icon.
        text_rect = QRectF(
            self._PADDING + self._ICON_SIZE,
            self._PADDING,
            self._TEXT_WIDTH,
            self._ICON_SIZE,
        )
        font = QFont(self.font())
        font.setBold(True)
        font.setPointSize(max(11, font.pointSize() + 2))
        painter.setFont(font)

        # Subtle shadow for legibility on any background.
        painter.setPen(QColor(0, 0, 0, 180))
        painter.drawText(
            text_rect.translated(QPointF(1, 1)),
            int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft),
            "AI",
        )
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(
            text_rect,
            int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft),
            "AI",
        )

    @staticmethod
    def icon_path(name: str) -> str:
        from ai_assistant.modules.base import assets_dir

        return str(assets_dir() / f"{name}.svg")
