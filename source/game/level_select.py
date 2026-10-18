"""Khung giao diện chọn màn chơi."""
from __future__ import annotations

from collections.abc import Callable
from ursina import Entity


class LevelSelectScreen(Entity):
    """Màn hình chọn màn chơi từ 1 đến 15."""

    LEVEL_NUMBERS = tuple(range(1, 16))

    def __init__(
        self,
        on_level_selected: Callable[[int], None],
        on_back: Callable[[], None],
    ) -> None:
        # CẦN LÀM: Dựng bố cục chọn màn và gắn các hàm xử lý sự kiện.
        pass

    def _create_background(self) -> None:
        # CẦN LÀM: Tạo hình nền cho màn hình.
        pass

    def _create_title(self) -> None:
        # CẦN LÀM: Thêm tiêu đề và nhãn cho màn hình.
        pass

    def _create_level_buttons(self) -> None:
        # CẦN LÀM: Tạo nút cho từng số màn trong LEVEL_NUMBERS.
        pass

    def _create_back_button(self) -> None:
        # CẦN LÀM: Tạo nút quay lại.
        pass

    def cleanup(self) -> None:
        # CẦN LÀM: Giải phóng các đối tượng do màn hình này tạo ra.
        pass
