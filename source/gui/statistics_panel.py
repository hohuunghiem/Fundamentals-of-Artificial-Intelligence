"""Khung giao diện hiển thị thống kê kết quả tìm kiếm."""
from __future__ import annotations

from collections.abc import Sequence
from algorithms.result import SolveResult


class StatisticsPanel:
    """Hiển thị kết quả của các thuật toán tìm kiếm."""

    def __init__(self) -> None:
        # CẦN LÀM: Tạo giao diện bảng và khởi tạo trạng thái hiển thị.
        pass

    def show(self, results: Sequence[SolveResult]) -> None:
        # CẦN LÀM: Hiển thị các kết quả tìm kiếm được truyền vào.
        pass

    def hide(self) -> None:
        # CẦN LÀM: Ẩn bảng thống kê.
        pass

    def destroy(self) -> None:
        # CẦN LÀM: Giải phóng các đối tượng của bảng thống kê.
        pass
