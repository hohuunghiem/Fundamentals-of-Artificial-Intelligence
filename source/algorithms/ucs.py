"""Tìm kiếm chi phí đồng nhất (UCS)."""
from heapq import heappop, heappush
from itertools import count

from core.enums import Move, TileType
from core.level import Level
from core.state import GameState
from core.transition import get_valid_moves, is_goal_state

from algorithms.common import (
    SearchResult,
    reconstruct_path,
    result_dict,
)


# Quy ước chi phí của UCS:
# - Trạng thái mới chiếm ít nhất một ô fragile: chi phí 4.
# - Không chạm fragile nhưng đổi tư thế: chi phí 2.
# - Các trường hợp còn lại: chi phí 1.
# Các mức phí không cộng dồn.
#
# Khi đang split, xét cả hai cube. Nếu một cube đang trên
# fragile, kể cả hành động đổi điều khiển cũng có chi phí 4.


def ucs_search(level: Level) -> SearchResult:
    """Tìm lời giải có tổng chi phí thấp nhất bằng hàng đợi ưu tiên."""

    start = level.initial_state

    # Phân biệt các trạng thái có cùng tổng chi phí.
    counter = count()

    # Mỗi mục: (tổng chi phí, số thứ tự, trạng thái).
    frontier = [(0, next(counter), start)]

    # Chi phí thấp nhất đã biết để đến mỗi trạng thái.
    best_cost = {start: 0}

    # Lưu trạng thái cha và hành động để dựng lại lời giải.
    parents: dict[GameState, tuple[GameState, Move] | None] = {
        start: None,
    }

    expanded = 0
    generated = 1

    while frontier:
        cost, _, current = heappop(frontier)

        # Bỏ mục cũ nếu đã tìm được đường rẻ hơn.
        if cost != best_cost.get(current):
            continue

        expanded += 1

        # Đến đích: trả đường đi và tổng chi phí tối ưu.
        if is_goal_state(level.board, current):
            result = result_dict(
                reconstruct_path(current, parents),
                expanded,
                generated,
            )
            result["solution_cost"] = cost
            return result

        for move, next_state in get_valid_moves(level.board, current):
            generated += 1

            touches_fragile = any(
                level.board.get_tile(row, col) == TileType.FRAGILE
                for row, col in next_state.occupied_cells()
            )

            if touches_fragile:
                step_cost = 4
            elif current.block.orientation != next_state.block.orientation:
                step_cost = 2
            else:
                step_cost = 1

            new_cost = cost + step_cost

            # Chỉ cập nhật nếu tìm được đường có chi phí thấp hơn.
            if new_cost >= best_cost.get(next_state, float("inf")):
                continue

            best_cost[next_state] = new_cost
            parents[next_state] = (current, move)

            heappush(
                frontier,
                (new_cost, next(counter), next_state),
            )

    # Không có lời giải nên không có tổng chi phí lời giải.
    result = result_dict(None, expanded, generated)
    result["solution_cost"] = None
    return result