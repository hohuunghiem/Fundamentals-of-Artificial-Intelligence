"""Thuật toán A* kết hợp chi phí đã đi với ước lượng còn lại."""
from heapq import heappop, heappush
from itertools import count
from math import ceil
from typing import Tuple

from core.enums import Orientation
from core.level import Level
from core.state import GameState
from core.transition import get_valid_moves, is_goal_state

from algorithms.common import SearchResult, reconstruct_path, result_dict


def _calculate_heuristic(goal_pos: Tuple[int, int], state: GameState) -> int:
    """Ước lượng số bước tối thiểu còn lại đến đích.
    
    Tính admissible:
    - Mỗi bước di chuyển thay đổi tọa độ nhiều nhất 2 ô. Do đó ceil(min_distance / 2) 
      là cận dưới hợp lệ của số bước di chuyển điểm.
    - Nếu khối gỗ chưa đứng, cần ít nhất 1 thao tác di chuyển để đưa về trạng thái STANDING.
    """
    goal_row, goal_col = goal_pos
    positions = state.occupied_cells()
    
    min_dist = min(
        abs(r - goal_row) + abs(c - goal_col)
        for r, c in positions
    )

    h = ceil(min_dist / 2)
    
    # Nếu chưa đứng thẳng hoặc đang bị tách thì không thể thắng ngay lập tức
    if (state.is_split or state.block.orientation != Orientation.STANDING) and h == 0:
        h = 1

    return h


def astar_search(level: Level) -> SearchResult:
    """Tìm lời giải bằng thuật toán A* với hàng đợi ưu tiên f = g + h."""
    start = level.initial_state
    goal_pos = level.board.find_goal()  # Tìm goal 1 lần duy nhất để tối ưu thời gian
    
    counter = count()
    start_h = _calculate_heuristic(goal_pos, start)
    frontier = [(start_h, next(counter), 0, start)]
    
    best_cost = {start: 0}
    parents = {start: None}
    
    expanded = 0
    generated = 1

    while frontier:
        _, _, cost, current = heappop(frontier)

        # Bỏ qua trạng thái cũ nếu đã có đường đi rẻ hơn
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
                priority = new_cost + _calculate_heuristic(goal_pos, next_state)
                heappush(
                    frontier,
                    (priority, next(counter), new_cost, next_state),
                )

    return result_dict(None, expanded, generated)