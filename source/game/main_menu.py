"""Khung giao diện menu chính; cần hoàn thiện bố cục trong các phương thức."""
from __future__ import annotations

from collections.abc import Callable
from ursina import Entity


class MainMenuScreen(Entity):
    """Màn hình menu chính, gọi hàm được truyền vào khi người chơi chọn bắt đầu."""

    def __init__(self, on_play: Callable[[], None]) -> None:
        # CẦN LÀM: Tạo các thành phần menu và gắn thao tác bắt đầu trò chơi.
        pass

    def cleanup(self) -> None:
        # CẦN LÀM: Giải phóng các đối tượng do màn hình này tạo ra.
        pass
