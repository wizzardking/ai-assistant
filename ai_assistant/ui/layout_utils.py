from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class RadialLayout:
    icon_size: int
    radius: int
    sub_icon_size: int
    sub_radius: int


def compute_radial_layout(item_count: int) -> RadialLayout:
    if item_count <= 0:
        item_count = 1

    icon_size = 48
    radius = 80

    if item_count > 4:
        icon_size = max(32, 48 - (item_count - 4) * 4)
        radius = min(140, 80 + (item_count - 4) * 8)

    return RadialLayout(
        icon_size=icon_size,
        radius=radius,
        sub_icon_size=max(28, icon_size - 8),
        sub_radius=radius + icon_size // 2 + 12,
    )


def circle_positions(
    count: int,
    center_x: float,
    center_y: float,
    radius: float,
    start_angle: float = -math.pi / 2,
) -> list[tuple[float, float]]:
    if count == 0:
        return []

    positions: list[tuple[float, float]] = []
    for index in range(count):
        angle = start_angle + (2 * math.pi * index / count)
        x = center_x + radius * math.cos(angle)
        y = center_y + radius * math.sin(angle)
        positions.append((x, y))
    return positions


def sub_menu_positions(
    count: int,
    parent_x: float,
    parent_y: float,
    center_x: float,
    center_y: float,
    radius: float,
) -> list[tuple[float, float]]:
    if count == 0:
        return []

    parent_angle = math.atan2(parent_y - center_y, parent_x - center_x)
    spread = math.pi / 6
    start = parent_angle - spread * (count - 1) / 2

    positions: list[tuple[float, float]] = []
    for index in range(count):
        angle = start + spread * index
        x = center_x + radius * math.cos(angle)
        y = center_y + radius * math.sin(angle)
        positions.append((x, y))
    return positions
