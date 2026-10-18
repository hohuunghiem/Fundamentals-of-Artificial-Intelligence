"""Thuật toán A* kết hợp chi phí đã đi với ước lượng còn lại."""
from core.level import Level
from core.state import GameState
from algorithms.common import SearchResult


def _heuristic(level: Level, state: GameState) -> int:
    """Ước lượng số bước còn lại từ trạng thái hiện tại đến ô đích.

    Heuristic nên rẻ để tính và không vượt quá chi phí thật còn lại nếu cần
    đảm bảo A* tìm được lời giải tối ưu. Nên xét tư thế block và cả hai cube
    khi trạng thái đang bị tách.
    """
    pass


def astar_search(level: Level) -> SearchResult:
    """Tìm lời giải bằng hàng đợi ưu tiên theo ``f = g + h``.

    ``g`` là chi phí từ đầu đến trạng thái hiện tại; ``h`` là kết quả của
    _heuristic. Cần bỏ qua mục hàng đợi cũ nếu đã có đường đi rẻ hơn đến
    trạng thái đó, đồng thời lưu trạng thái cha để dựng lại danh sách nước đi.
    """
    pass
