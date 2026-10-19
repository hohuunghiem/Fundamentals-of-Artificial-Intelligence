"""Tìm kiếm theo chiều rộng (BFS)."""
from core.enums import Move
from core.level import Level
from core.state import GameState
from core.transition import get_valid_moves, is_goal_state

from algorithms.common import SearchResult


def bfs_search(level: Level) -> SearchResult:
    """Tìm lời giải ngắn nhất theo số nước đi bằng hàng đợi FIFO.

    Mỗi nước đi có chi phí bằng nhau nên BFS đảm bảo lời giải tìm được có ít
    bước nhất. Trả về kết quả theo cấu trúc ``SearchResult`` trong ``common``.
    """
    start = level.initial_state

    # Dùng list cùng chỉ số đầu hàng đợi để BFS tự quản lý FIFO.
    frontier = [start]
    queue_index = 0
    visited = {start}
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
            state = current
            while parents[state] is not None:
                previous, move = parents[state]
                moves.append(move)
                state = previous
            moves.reverse()

            return {
                "success": True,
                "moves": moves,
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
        "expanded_nodes": expanded,
        "generated_nodes": generated,
    }
