"""Kiểu dữ liệu lưu kết quả solver cho game và bảng thống kê."""
from dataclasses import dataclass
from core.enums import Move


@dataclass(frozen=True)
class SolveResult:
    # Tên thuật toán và kết quả có/không tìm được lời giải.
    algorithm: str
    success: bool
    # Các nước đi theo thứ tự phát lại; rỗng nếu thất bại.
    moves: list[Move]
    # Thời gian chạy (giây), bộ nhớ dùng (MB) và số nút đã xử lý.
    search_time: float
    memory_usage: float
    expanded_nodes: int = 0
    generated_nodes: int = 0

    @property
    def solution_length(self) -> int:
        """Trả về số nước đi trong lời giải; bằng 0 nếu danh sách rỗng."""
        pass
