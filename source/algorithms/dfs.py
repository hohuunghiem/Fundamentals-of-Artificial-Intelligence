"""Tìm kiếm theo chiều sâu (DFS)."""
from core.enums import Move, TileType
from core.level import Level
from core.state import GameState
from core.transition import get_valid_moves, is_goal_state

from algorithms.common import SearchResult, result_dict


def dfs_search(level: Level) -> SearchResult:
    """Duyệt theo chiều sâu bằng ngăn xếp LIFO.

    Dùng visited để tránh duyệt lặp trạng thái.

    DFS không bảo đảm số hành động ít nhất hoặc tổng chi phí
    nhỏ nhất. Chi phí 1–2–4 chỉ được tính khi đã tìm được
    lời giải, không ảnh hưởng đến thứ tự tìm kiếm.
    """
    start = level.initial_state

    stack: list[GameState] = [start]
    visited: set[GameState] = {start}

    # Lưu trạng thái cha và hành động dẫn tới mỗi trạng thái.
    parents: dict[GameState, tuple[GameState, Move] | None] = {
        start: None,
    }

    expanded = 0
    generated = 1

    while stack:
        current = stack.pop()
        expanded += 1

        if is_goal_state(level.board, current):
            moves: list[Move] = []
            solution_cost = 0
            state = current

            # Lần ngược đường đi và cộng phí từng hành động.
            while parents[state] is not None:
                previous, move = parents[state]
                moves.append(move)

                # state là trạng thái SAU hành động.
                # Xét cả hai cube nếu khối đang bị tách.
                touches_fragile = any(
                    level.board.get_tile(row, col) == TileType.FRAGILE
                    for row, col in state.occupied_cells()
                )

                # Giống quy tắc của UCS/A*: không cộng dồn.
                if touches_fragile:
                    step_cost = 4
                elif previous.block.orientation != state.block.orientation:
                    step_cost = 2
                else:
                    step_cost = 1

                solution_cost += step_cost
                state = previous

            moves.reverse()

            result = result_dict(
                moves,
                expanded,
                generated,
            )
            result["solution_cost"] = solution_cost
            return result

        for move, next_state in get_valid_moves(level.board, current):
            generated += 1

            if next_state in visited:
                continue

            visited.add(next_state)
            parents[next_state] = (current, move)
            stack.append(next_state)

    # Không tìm được lời giải.
    result = result_dict(None, expanded, generated)
    result["solution_cost"] = None
    return result