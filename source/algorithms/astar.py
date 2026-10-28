"""A* với chi phí 1–2–4 và heuristic an toàn khi có split/teleport."""

from heapq import heappop, heappush
from itertools import count

from core.enums import Orientation, TileType
from core.level import Level
from core.state import GameState
from core.transition import get_valid_moves, is_goal_state

from algorithms.common import (
    SearchResult,
    reconstruct_path,
    result_dict,
)


def _step_cost(
    level: Level,
    current: GameState,
    next_state: GameState,
) -> int:
    """Tính chi phí một hành động theo cùng quy tắc với UCS.

    - Trạng thái mới chiếm ít nhất một ô fragile: 4.
    - Không chạm fragile nhưng đổi tư thế: 2.
    - Các trường hợp còn lại: 1.

    Các mức phí không cộng dồn.

    Khi đang split, xét cả hai cube. Vì vậy, kể cả hành động
    đổi cube điều khiển cũng tốn 4 nếu một cube đang trên fragile.
    """
    touches_fragile = any(
        level.board.get_tile(row, col) == TileType.FRAGILE
        for row, col in next_state.occupied_cells()
    )

    if touches_fragile:
        return 4

    if current.block.orientation != next_state.block.orientation:
        return 2

    return 1


def _has_split_switch(level: Level) -> bool:
    """Kiểm tra toàn bộ bản đồ có ô split switch hay không."""
    return any(
        tile == TileType.SPLIT_SWITCH
        for row in level.board.tiles
        for tile in row
    )


def _calc_h(
    goal_pos: tuple[int, int],
    state: GameState,
    has_split: bool = False,
) -> int:
    """Ước lượng cận dưới của chi phí còn lại.

    Màn có split:
        Dùng h = 0 trên toàn bộ màn vì teleport có thể làm
        khoảng cách hình học vượt quá chi phí thật còn lại.

    Màn không có split:
        Dùng ceil(khoảng cách Manhattan nhỏ nhất / 2).
        Một lần lăn giảm khoảng cách này tối đa 2 và mỗi
        hành động có chi phí ít nhất 1.

    Nếu khối chạm đích nhưng chưa đứng thẳng, cần ít nhất
    một hành động nữa để thắng.
    """
    if has_split or state.is_split:
        return 0

    goal_row, goal_col = goal_pos

    min_dist = min(
        abs(row - goal_row) + abs(col - goal_col)
        for row, col in state.occupied_cells()
    )

    # Tương đương ceil(min_dist / 2) với số nguyên không âm.
    h = (min_dist + 1) // 2

    if state.block.orientation != Orientation.STANDING:
        h = max(h, 1)

    return h


def _heuristic(level: Level, state: GameState) -> int:
    """Hàm tiện ích để kiểm tra heuristic của một trạng thái."""
    return _calc_h(
        level.board.find_goal(),
        state,
        has_split=_has_split_switch(level),
    )


def astar_search(level: Level) -> SearchResult:
    """Tìm lời giải có tổng chi phí nhỏ nhất bằng A*.

    f(s) = g(s) + h(s)

    g(s): Tổng chi phí 1–2–4 từ trạng thái đầu tới s.
    h(s): Cận dưới của chi phí từ s tới đích.

    Cho phép xét lại trạng thái nếu tìm được đường rẻ hơn.
    Trên màn có split, h = 0 nên thuật toán hoạt động như UCS.
    """
    start = level.initial_state

    # Chỉ tra cứu thông tin cố định của bản đồ một lần.
    goal_pos = level.board.find_goal()
    has_split = _has_split_switch(level)

    counter = count()

    start_h = _calc_h(
        goal_pos,
        start,
        has_split=has_split,
    )

    # Mỗi mục: (f, số thứ tự, g, trạng thái).
    frontier = [(start_h, next(counter), 0, start)]

    best_cost = {start: 0}
    parents = {start: None}

    expanded = 0
    generated = 1

    while frontier:
        _, _, cost, current = heappop(frontier)

        # Bỏ mục hàng đợi cũ khi đã có đường rẻ hơn.
        if cost != best_cost.get(current):
            continue

        # Giữ quy ước đếm giống các solver hiện tại:
        # tính cả trạng thái đích được lấy ra khỏi frontier.
        expanded += 1

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

            new_cost = cost + _step_cost(
                level,
                current,
                next_state,
            )

            # Chỉ cập nhật nếu tìm được đường rẻ hơn.
            if new_cost >= best_cost.get(next_state, float("inf")):
                continue

            best_cost[next_state] = new_cost
            parents[next_state] = (current, move)

            heuristic = _calc_h(
                goal_pos,
                next_state,
                has_split=has_split,
            )

            heappush(
                frontier,
                (
                    new_cost + heuristic,
                    next(counter),
                    new_cost,
                    next_state,
                ),
            )

    result = result_dict(None, expanded, generated)
    result["solution_cost"] = None
    return result