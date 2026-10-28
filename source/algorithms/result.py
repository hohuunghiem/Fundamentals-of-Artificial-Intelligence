"""Kiểu dữ liệu lưu kết quả solver cho game và bảng thống kê."""
from dataclasses import dataclass

from core.enums import Move


@dataclass(frozen=True)
class SolveResult:
    # Tên thuật toán và trạng thái tìm được lời giải.
    algorithm: str
    success: bool

    # Các hành động theo thứ tự phát lại; rỗng nếu thất bại.
    moves: list[Move]

    # Thời gian chạy (giây) và bộ nhớ Python được theo dõi (MiB).
    search_time: float
    memory_usage: float

    # Số nút đã xử lý và sinh ra.
    expanded_nodes: int = 0
    generated_nodes: int = 0

    # Tổng chi phí 1–2–4 của lời giải.
    # None nếu không có lời giải hoặc solver chưa cung cấp chi phí.
    solution_cost: int | None = None

    @property
    def solution_length(self) -> int:
        """Số hành động trong lời giải; bằng 0 nếu danh sách rỗng."""
        return len(self.moves)