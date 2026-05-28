from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from PyQt6.QtCore import QRect, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QFontMetrics, QMouseEvent, QPainter, QPixmap
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import QWidget

from ai_assistant.config import ModuleSettings
from ai_assistant.modules.base import MenuNode, Module
from ai_assistant.ui.layout_utils import circle_positions, compute_radial_layout


@dataclass
class IconHitTarget:
    kind: str  # "node" or "center"
    node: MenuNode | None
    rect: tuple[int, int, int, int]
    icon_path: str
    label: str


def _center_icon_path(is_top_level: bool) -> str:
    from ai_assistant.modules.base import assets_dir

    name = "close" if is_top_level else "back"
    return str(assets_dir() / f"{name}.svg")


class RadialMenu(QWidget):
    """Hierarchical radial menu with arbitrary nesting depth."""

    module_interactive = pyqtSignal(str)
    leaf_selected = pyqtSignal(str, tuple, object)  # module_id, path_ids, MenuNode

    ICON_BG = QColor(30, 30, 30, 220)
    ICON_HOVER = QColor(55, 55, 55, 240)
    ICON_BORDER = QColor(255, 255, 255, 60)
    LABEL_BG = QColor(20, 20, 20, 230)
    LABEL_BORDER = QColor(255, 255, 255, 70)
    LABEL_TEXT = QColor(240, 240, 240, 255)
    LABEL_GAP = 8
    LABEL_PADDING_X = 10
    LABEL_PADDING_Y = 5

    def __init__(self) -> None:
        super().__init__(
            None,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Popup,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)

        self._modules: list[Module] = []
        self._modules_by_id: dict[str, Module] = {}
        self._settings_provider: Callable[[str, str], ModuleSettings] | None = None

        self._center_x = 0
        self._center_y = 0
        # stack of layers; layer 0 = top-level modules as nodes; deeper layers = sub-nodes
        self._stack: list[tuple[MenuNode, ...]] = []
        # ids of the parents we descended through (parallel to stack[1:])
        self._path: list[str] = []

        self._layout = compute_radial_layout(1)
        self._hit_targets: list[IconHitTarget] = []
        self._hover_target: IconHitTarget | None = None
        self._icon_cache: dict[tuple[str, int], QPixmap] = {}

    def show_at(
        self,
        x: int,
        y: int,
        modules: list[Module],
        settings_provider: Callable[[str, str], ModuleSettings],
    ) -> None:
        self._modules = modules
        self._modules_by_id = {m.id: m for m in modules}
        self._settings_provider = settings_provider
        self._center_x = x
        self._center_y = y
        self._stack = [
            tuple(
                MenuNode(id=m.id, label=m.label, icon=m.icon) for m in modules
            )
        ]
        self._path = []
        self._refresh_layer()
        self.show()
        self.raise_()
        self.activateWindow()
        self.setFocus(Qt.FocusReason.PopupFocusReason)

    def close_menu(self) -> None:
        if self.isVisible():
            self.hide()

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.close_menu()
            return
        if event.key() == Qt.Key.Key_Backspace and len(self._stack) > 1:
            self._go_back()
            return
        super().keyPressEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return

        target = self._target_at(event.position().toPoint())
        if target is None:
            self.close_menu()
            return

        if target.kind == "center":
            if len(self._stack) > 1:
                self._go_back()
            else:
                self.close_menu()
            return

        node = target.node
        assert node is not None
        if not self._path:
            self._activate_module(node.id)
        else:
            self._activate_node(node)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        self._hover_target = self._target_at(event.position().toPoint())
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        for target in self._hit_targets:
            x, y, w, h = target.rect
            hovered = self._hover_target == target
            self._draw_icon_button(painter, target.icon_path, x, y, w, h, hovered)

        if self._hover_target is not None and self._hover_target.label:
            self._draw_hover_label(painter, self._hover_target)

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

    def _draw_hover_label(self, painter: QPainter, target: IconHitTarget) -> None:
        font = QFont(self.font())
        font.setPointSize(max(9, font.pointSize()))
        font.setBold(True)
        painter.setFont(font)
        metrics = QFontMetrics(font)

        text = target.label
        text_w = metrics.horizontalAdvance(text)
        text_h = metrics.height()
        box_w = text_w + 2 * self.LABEL_PADDING_X
        box_h = text_h + 2 * self.LABEL_PADDING_Y

        x, y, w, h = target.rect
        icon_center_x = x + w // 2

        box_x = icon_center_x - box_w // 2
        box_y = y + h + self.LABEL_GAP

        if box_y + box_h > self.height() - 4:
            box_y = y - self.LABEL_GAP - box_h

        if box_x < 2:
            box_x = 2
        elif box_x + box_w > self.width() - 2:
            box_x = self.width() - 2 - box_w

        rect = QRect(box_x, box_y, box_w, box_h)
        painter.setPen(self.LABEL_BORDER)
        painter.setBrush(self.LABEL_BG)
        painter.drawRoundedRect(rect, 6, 6)

        painter.setPen(self.LABEL_TEXT)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)

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

    def _target_at(self, point) -> IconHitTarget | None:
        px, py = point.x(), point.y()
        for target in self._hit_targets:
            x, y, w, h = target.rect
            if x <= px <= x + w and y <= py <= y + h:
                return target
        return None

    def _activate_module(self, module_id: str) -> None:
        module = self._modules_by_id.get(module_id)
        if module is None:
            return

        if module.is_interactive():
            self.hide()
            self.module_interactive.emit(module.id)
            return

        assert self._settings_provider is not None
        settings = self._settings_provider(module.id, module.default_prompt())
        children = module.menu(settings)
        if not children:
            self.hide()
            self.leaf_selected.emit(
                module.id,
                tuple(),
                MenuNode(id="", label="", icon=""),
            )
            return

        # If the module exposes exactly one leaf, skip the intermediate sub-menu
        # and activate that leaf directly (useful for image generation etc.).
        if len(children) == 1 and children[0].is_leaf:
            self._path = [module.id]
            self._activate_node(children[0])
            return

        self._path = [module.id]
        self._stack.append(children)
        self._refresh_layer()

    def _activate_node(self, node: MenuNode) -> None:
        if node.children:
            self._path.append(node.id)
            self._stack.append(node.children)
            self._refresh_layer()
            return

        module_id = self._path[0]
        sub_path = tuple(self._path[1:]) + (node.id,)
        self.hide()
        self.leaf_selected.emit(module_id, sub_path, node)

    def _go_back(self) -> None:
        if len(self._stack) <= 1:
            return
        self._stack.pop()
        if self._path:
            self._path.pop()
        self._refresh_layer()

    def _refresh_layer(self) -> None:
        nodes = self._stack[-1]
        self._layout = compute_radial_layout(len(nodes))
        self._resize_and_move()
        self._rebuild_hit_targets()
        self.update()

    def _rebuild_hit_targets(self) -> None:
        self._hit_targets = []
        nodes = self._stack[-1]

        size = self._layout.icon_size
        center_size = max(28, size - 12)
        center_rect = self._icon_rect(self._center_x, self._center_y, center_size)
        is_top = len(self._stack) == 1
        self._hit_targets.append(
            IconHitTarget(
                kind="center",
                node=None,
                rect=center_rect,
                icon_path=_center_icon_path(is_top),
                label="Schließen" if is_top else "Zurück",
            )
        )

        positions = circle_positions(
            len(nodes),
            self._center_x,
            self._center_y,
            self._layout.radius,
        )
        for node, (px, py) in zip(nodes, positions):
            rect = self._icon_rect(px, py, size)
            self._hit_targets.append(
                IconHitTarget(
                    kind="node",
                    node=node,
                    rect=rect,
                    icon_path=node.icon,
                    label=node.label,
                )
            )

    def _icon_rect(self, center_x: float, center_y: float, size: int) -> tuple[int, int, int, int]:
        top_left_x = int(center_x - size / 2) - self.x()
        top_left_y = int(center_y - size / 2) - self.y()
        return top_left_x, top_left_y, size, size

    def _resize_and_move(self) -> None:
        # Extra Platz unter/über jedem Icon für das Hover-Label
        label_reserve = 56
        padding = self._layout.radius + self._layout.icon_size + label_reserve
        width = padding * 2 + 40
        height = padding * 2 + 40
        self.setFixedSize(width, height)
        self.move(self._center_x - width // 2, self._center_y - height // 2)
