"""Tìm kiếm theo chiều sâu (DFS)."""
from core.enums import Move
from core.level import Level
from core.state import GameState
from core.transition import get_valid_moves, is_goal_state

from algorithms.common import SearchResult, reconstruct_path, result_dict


def dfs_search(level: Level) -> SearchResult:
    """Duyệt sâu từng nhánh bằng ngăn xếp LIFO.

    Cần theo dõi trạng thái đã thăm để tránh duyệt lặp. DFS có thể tìm được
    lời giải nhưng không đảm bảo lời giải đó có ít bước nhất. Trả về kết quả
    theo cấu trúc ``SearchResult`` trong ``common``.
    """
    start = level.initial_state

    stack: list[GameState] = [start]
    visited: set[GameState] = {start}
    parents: dict[GameState, tuple[GameState, Move] | None] = {
        start: None,
    }
    expanded = 0
    generated = 1

    while stack:
        current = stack.pop()
        expanded += 1

        if is_goal_state(level.board, current):
            return result_dict(
                reconstruct_path(current, parents),
                expanded,
                generated,
            )

        for move, next_state in get_valid_moves(level.board, current):
            generated += 1
            if next_state in visited:
                continue

            visited.add(next_state)
            parents[next_state] = (current, move)
            stack.append(next_state)

    return result_dict(None, expanded, generated)