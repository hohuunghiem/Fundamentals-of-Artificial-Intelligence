"""Tìm kiếm chi phí đồng nhất (UCS)."""
from core.level import Level
from algorithms.common import SearchResult


def ucs_search(level: Level) -> SearchResult:
    """Luôn mở rộng trạng thái có tổng chi phí đường đi thấp nhất.

    Dùng hàng đợi ưu tiên và cập nhật chi phí tốt nhất đã biết cho mỗi trạng
    thái. Hiện mỗi nước đi đều có chi phí 1, vì vậy lời giải tối ưu của UCS
    tương đương BFS. Trả về kết quả theo cấu trúc ``SearchResult``.
    """
    pass
