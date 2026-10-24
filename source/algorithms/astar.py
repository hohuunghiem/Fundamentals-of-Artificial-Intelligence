"""Thuật toán A* kết hợp chi phí đã đi với ước lượng còn lại."""
from heapq import heappop, heappush
from itertools import count
from math import ceil

from core.enums import Orientation
from core.level import Level
from core.state import GameState
from core.transition import get_valid_moves, is_goal_state

from algorithms.common import SearchResult, reconstruct_path, result_dict


def _calc_h(goal_pos: tuple[int, int], state: GameState) -> int:
    """Hàm phụ tính toán heuristic để tránh việc gọi level.board.find_goal() liên tục."""
    goal_row, goal_col = goal_pos
    positions = state.occupied_cells()
    
    min_dist = min(
        abs(r - goal_row) + abs(c - goal_col)
        for r, c in positions
    )

    h = ceil(min_dist / 2)
    
    # Đảm bảo tính admissible: Nếu chưa đứng thẳng hoặc đang tách, cần ít nhất 1 bước
    if (state.is_split or state.block.orientation != Orientation.STANDING) and h == 0:
        h = 1

    return h


def _heuristic(level: Level, state: GameState) -> int:
    """Ước lượng số bước còn lại từ trạng thái hiện tại đến ô đích.

    Heuristic nên rẻ để tính và không vượt quá chi phí thật còn lại nếu cần
    đảm bảo A* tìm được lời giải tối ưu. Nên xét tư thế block và cả hai cube
    khi trạng thái đang bị tách.
    """
    
    return _calc_h(level.board.find_goal(), state)


def astar_search(level: Level) -> SearchResult:
    """Tìm lời giải bằng hàng đợi ưu tiên theo ``f = g + h``.

    ``g`` là chi phí từ đầu đến trạng thái hiện tại; ``h`` là kết quả của
    _heuristic. Cần bỏ qua mục hàng đợi cũ nếu đã có đường đi rẻ hơn đến
    trạng thái đó, đồng thời lưu trạng thái cha để dựng lại danh sách nước đi.
    """
    start = level.initial_state
    goal_pos = level.board.find_goal()  # Tìm goal 1 lần duy nhất trước khi duyệt đồ thị
    
    counter = count()
    start_h = _calc_h(goal_pos, start)
    frontier = [(start_h, next(counter), 0, start)]
    
    best_cost = {start: 0}
    parents = {start: None}
    
    expanded = 0
    generated = 1

    while frontier:
        _, _, cost, current = heappop(frontier)

        # Lazy deletion: Bỏ qua trạng thái cũ nếu đã tìm được đường đi ngắn hơn
        if cost > best_cost.get(current, float("inf")):
            continue

        expanded += 1
        if is_goal_state(level.board, current):
            return result_dict(
                reconstruct_path(current, parents),
                expanded,
                generated,
            )

        for move, next_state in get_valid_moves(level.board, current):
            generated += 1
            new_cost = cost + 1

            if new_cost < best_cost.get(next_state, float("inf")):
                best_cost[next_state] = new_cost
                parents[next_state] = (current, move)
                
                # Sử dụng hàm phụ với goal_pos đã lưu sẵn để tối ưu tốc độ
                priority = new_cost + _calc_h(goal_pos, next_state)
                heappush(
                    frontier,
                    (priority, next(counter), new_cost, next_state),
                )

    return result_dict(None, expanded, generated)