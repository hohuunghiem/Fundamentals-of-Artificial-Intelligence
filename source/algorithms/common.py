"""Các hàm dùng chung cho những thuật toán tìm kiếm."""
from collections.abc import Callable
from typing import Any

from core.enums import Move
from core.level import Level
from core.state import GameState

# Kết quả dạng từ điển để các solver trả về cùng một cấu trúc cho profiler.
SearchResult = dict[str, Any]


def reconstruct_path(
    goal: GameState,
    parents: dict[GameState, tuple[GameState, Move] | None],
) -> list[Move]:
    """Lần ngược bảng cha từ đích về trạng thái đầu để dựng lại đường đi.

    Mỗi giá trị trong parents lưu trạng thái trước đó và nước đi đã dùng.
    Đảo ngược danh sách sau khi lần ngược để trả về thứ tự từ đầu đến đích.
    """
    pass


def result_dict(
    moves: list[Move] | None,
    expanded: int,
    generated: int,
) -> SearchResult:
    """Tạo kết quả thống nhất gồm đường đi và số nút đã duyệt hoặc tạo.

    ``moves`` là ``None`` nếu không tìm thấy lời giải; nếu tìm thấy thì đây là
    danh sách các giá trị ``Move`` theo đúng thứ tự thực hiện.
    """
    pass


def search_unweighted(
    level: Level,
    *,
    lifo: bool = False,
    successors: Callable[[Level, GameState], list[tuple[Move, GameState]]] | None = None,
) -> SearchResult:
    """Duyệt đồ thị dùng chung cho BFS và DFS.

    ``lifo=False`` chọn hàng đợi FIFO (BFS); ``lifo=True`` chọn ngăn xếp LIFO
    (DFS). ``successors`` cho phép truyền hàm sinh trạng thái kế tiếp; nếu bỏ
    trống, dùng các nước đi hợp lệ của trò chơi. Cần đánh dấu trạng thái đã
    thăm để tránh lặp vô hạn và lưu trạng thái cha để dựng đường đi khi gặp đích.
    """
    pass
