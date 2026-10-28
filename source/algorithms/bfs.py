"""Tìm kiếm theo chiều rộng (BFS)."""
from core.enums import Move, TileType
from core.level import Level
from core.state import GameState
from core.transition import get_valid_moves, is_goal_state

from algorithms.common import SearchResult


def bfs_search(level: Level) -> SearchResult:
    """Tìm lời giải ít hành động nhất bằng hàng đợi FIFO.

    Chi phí 1–2–4 chỉ dùng để đánh giá lời giải tìm được,
    không ảnh hưởng đến thứ tự tìm kiếm.

    BFS bảo đảm số hành động ít nhất, nhưng không bảo đảm
    tổng chi phí 1–2–4 nhỏ nhất.
    """
    start = level.initial_state

    # Dùng list và chỉ số đầu hàng đợi để duyệt FIFO.
    frontier = [start]
    queue_index = 0

    visited = {start}

    # Lưu trạng thái cha và hành động dẫn tới mỗi trạng thái.
    parents: dict[GameState, tuple[GameState, Move] | None] = {
        start: None,
    }

    expanded = 0
    generated = 1

    while queue_index < len(frontier):
        current = frontier[queue_index]
        queue_index += 1
        expanded += 1

        if is_goal_state(level.board, current):
            moves: list[Move] = []
            solution_cost = 0
            state = current

            # Lần ngược đường đi và cộng chi phí từng hành động.
            while parents[state] is not None:
                previous, move = parents[state]
                moves.append(move)

                # state là trạng thái SAU hành động;
                # previous là trạng thái TRƯỚC hành động.
                touches_fragile = any(
                    level.board.get_tile(row, col) == TileType.FRAGILE
                    for row, col in state.occupied_cells()
                )

                if touches_fragile:
                    step_cost = 4
                elif previous.block.orientation != state.block.orientation:
                    step_cost = 2
                else:
                    step_cost = 1

                solution_cost += step_cost
                state = previous

            moves.reverse()

            return {
                "success": True,
                "moves": moves,
                "solution_cost": solution_cost,
                "expanded_nodes": expanded,
                "generated_nodes": generated,
            }

        for move, next_state in get_valid_moves(level.board, current):
            generated += 1

            if next_state in visited:
                continue

            visited.add(next_state)
            parents[next_state] = (current, move)
            frontier.append(next_state)

    return {
        "success": False,
        "moves": None,
        "solution_cost": None,
        "expanded_nodes": expanded,
        "generated_nodes": generated,
    }