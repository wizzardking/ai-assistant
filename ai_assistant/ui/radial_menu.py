from __future__ import annotations

from dataclasses import dataclass

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QMouseEvent, QPainter, QPixmap
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import QWidget

from ai_assistant.modules.base import Module, ModuleAction
from ai_assistant.ui.layout_utils import (
    RadialLayout,
    circle_positions,
    compute_radial_layout,
    sub_menu_positions,
)


@dataclass
class IconHitTarget:
    kind: str
    module_id: str
    action_id: str | None
    rect: tuple[int, int, int, int]
    icon_path: str
    label: str


class RadialMenu(QWidget):
    module_selected = pyqtSignal(str, str)
    module_interactive = pyqtSignal(str)
    dismissed = pyqtSignal()

    BACKGROUND_ALPHA = 180
    ICON_BG = QColor(30, 30, 30, 220)
    ICON_HOVER = QColor(55, 55, 55, 240)
    ICON_BORDER = QColor(255, 255, 255, 60)

    def __init__(self) -> None:
        super().__init__(
            None,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self._modules: list[Module] = []
        self._layout = compute_radial_layout(1)
        self._center_x = 0
        self._center_y = 0
        self._expanded_module_id: str | None = None
        self._hit_targets: list[IconHitTarget] = []
        self._hover_target: IconHitTarget | None = None
        self._icon_cache: dict[tuple[str, int], QPixmap] = {}

    def show_at(self, x: int, y: int, modules: list[Module]) -> None:
        self._modules = modules
        self._center_x = x
        self._center_y = y
        self._expanded_module_id = None
        self._layout = compute_radial_layout(len(modules))
        self._resize_and_move()
        self.show()
        self.raise_()
        self.activateWindow()
        self.setFocus()

    def close_menu(self) -> None:
        if self.isVisible():
            self.hide()
            self.dismissed.emit()

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.close_menu()
            return
        super().keyPressEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return

        target = self._target_at(event.position().toPoint())
        if target is None:
            self.close_menu()
            return

        if target.kind == "module":
            module = self._find_module(target.module_id)
            if module is None:
                return

            actions = module.actions()
            if module.is_interactive():
                self.hide()
                self.module_interactive.emit(module.id)
                return

            if actions:
                self._expanded_module_id = module.id
                self._rebuild_hit_targets()
                self._resize_and_move()
                self.update()
                return

            self.hide()
            self.module_selected.emit(module.id, "")
            return

        if target.kind == "action":
            self.hide()
            self.module_selected.emit(target.module_id, target.action_id or "")

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        self._hover_target = self._target_at(event.position().toPoint())
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        local_center_x = self._center_x - self.x()
        local_center_y = self._center_y - self.y()

        for target in self._hit_targets:
            x, y, w, h = target.rect
            hovered = self._hover_target == target
            self._draw_icon_button(painter, target.icon_path, x, y, w, h, hovered)

        painter.setPen(QColor(255, 255, 255, 40))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(
            int(local_center_x - 6),
            int(local_center_y - 6),
            12,
            12,
        )

    def _draw_icon_button(
        self,
        painter: QPainter,
        icon_path: str,
        x: int,
        y: int,
        w: int,
        h: int,
        hovered: bool,
    ) -> None:
        painter.setPen(self.ICON_BORDER)
        painter.setBrush(self.ICON_HOVER if hovered else self.ICON_BG)
        painter.drawRoundedRect(x, y, w, h, 10, 10)

        pixmap = self._load_icon(icon_path, min(w, h) - 12)
        icon_x = x + (w - pixmap.width()) // 2
        icon_y = y + (h - pixmap.height()) // 2
        painter.drawPixmap(icon_x, icon_y, pixmap)

    def _load_icon(self, path: str, size: int) -> QPixmap:
        key = (path, size)
        if key in self._icon_cache:
            return self._icon_cache[key]

        renderer = QSvgRenderer(path)
        pixmap = QPixmap(size, size)
        pixmap.fill(QColor(0, 0, 0, 0))
        icon_painter = QPainter(pixmap)
        renderer.render(icon_painter)
        icon_painter.end()
        self._icon_cache[key] = pixmap
        return pixmap

    def _find_module(self, module_id: str) -> Module | None:
        for module in self._modules:
            if module.id == module_id:
                return module
        return None

    def _target_at(self, point) -> IconHitTarget | None:
        px, py = point.x(), point.y()
        for target in self._hit_targets:
            x, y, w, h = target.rect
            if x <= px <= x + w and y <= py <= y + h:
                return target
        return None

    def _rebuild_hit_targets(self) -> None:
        self._hit_targets = []
        positions = circle_positions(
            len(self._modules),
            self._center_x,
            self._center_y,
            self._layout.radius,
        )

        size = self._layout.icon_size
        for module, (px, py) in zip(self._modules, positions):
            rect = self._icon_rect(px, py, size)
            self._hit_targets.append(
                IconHitTarget(
                    kind="module",
                    module_id=module.id,
                    action_id=None,
                    rect=rect,
                    icon_path=module.icon,
                    label=module.label,
                )
            )

        if self._expanded_module_id is None:
            return

        module = self._find_module(self._expanded_module_id)
        if module is None:
            return

        actions = module.actions()
        if not actions:
            return

        parent_pos = self._module_position(module.id)
        if parent_pos is None:
            return

        sub_positions = sub_menu_positions(
            len(actions),
            parent_pos[0],
            parent_pos[1],
            self._center_x,
            self._center_y,
            self._layout.sub_radius,
        )

        sub_size = self._layout.sub_icon_size
        for action, (px, py) in zip(actions, sub_positions):
            rect = self._icon_rect(px, py, sub_size)
            self._hit_targets.append(
                IconHitTarget(
                    kind="action",
                    module_id=module.id,
                    action_id=action.id,
                    rect=rect,
                    icon_path=action.icon,
                    label=action.label,
                )
            )

    def _module_position(self, module_id: str) -> tuple[float, float] | None:
        for index, module in enumerate(self._modules):
            if module.id == module_id:
                positions = circle_positions(
                    len(self._modules),
                    self._center_x,
                    self._center_y,
                    self._layout.radius,
                )
                return positions[index]
        return None

    def _icon_rect(self, center_x: float, center_y: float, size: int) -> tuple[int, int, int, int]:
        top_left_x = int(center_x - size / 2) - self.x()
        top_left_y = int(center_y - size / 2) - self.y()
        return top_left_x, top_left_y, size, size

    def _resize_and_move(self) -> None:
        padding = self._layout.sub_radius + self._layout.icon_size
        width = padding * 2 + 40
        height = padding * 2 + 40
        self.setFixedSize(width, height)
        self.move(self._center_x - width // 2, self._center_y - height // 2)
        self._rebuild_hit_targets()
