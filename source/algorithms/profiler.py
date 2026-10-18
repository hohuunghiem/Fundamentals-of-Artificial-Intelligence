"""Đo thời gian và bộ nhớ khi chạy thuật toán tìm kiếm."""
from collections.abc import Callable
from typing import Any

from core.level import Level
from algorithms.result import SolveResult


def run_with_profiling(
    algorithm: str,
    search_fn: Callable[[Level], dict[str, Any] | None],
    level: Level,
) -> SolveResult:
    """Chạy ``search_fn`` trên level và đóng gói kết quả thành ``SolveResult``.

    Đo thời gian chạy và lượng bộ nhớ thuật toán sử dụng; lấy đường đi cùng
    số nút mở rộng/tạo từ từ điển kết quả. Nếu không tìm thấy lời giải, đánh
    dấu thất bại và cung cấp danh sách nước đi rỗng cho giao diện.
    """
    pass
