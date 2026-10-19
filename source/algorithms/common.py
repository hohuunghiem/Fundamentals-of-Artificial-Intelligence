"""Các hàm dùng chung cho những thuật toán tìm kiếm."""
from collections.abc import Callable
from collections import deque
from typing import Any

from core.enums import Move
from core.level import Level
from core.state import GameState
from core.transition import get_valid_moves, is_goal_state

# Kết quả dạng từ điển để các solver trả về cùng một cấu trúc cho profiler.
SearchResult = dict[str, Any]


def reconstruct_path(
    goal: GameState,
    parents: dict[GameState, tuple[GameState, Move] | None],
) -> list[Move]:
    """Lần ngược bảng cha từ đích về trạng thái đầu để dựng lại đường đi.

    Mỗi giá trị trong parents lưu trạng thái trước đó và nước đi đã dùng.
    Đảo ngược danh sách sau khi lần ngược để trả về thứ tự từ đầu đến đích.
    """
    moves: list[Move] = []
    current = goal

    while parents[current] is not None:
        previous, move = parents[current]
        moves.append(move)
        current = previous

    moves.reverse()
    return moves


def result_dict(
    moves: list[Move] | None,
    expanded: int,
    generated: int,
) -> SearchResult:
    """Tạo kết quả thống nhất gồm đường đi và số nút đã duyệt hoặc tạo.

    ``moves`` là ``None`` nếu không tìm thấy lời giải; nếu tìm thấy thì đây là
    danh sách các giá trị ``Move`` theo đúng thứ tự thực hiện.
    """
    return {
        "success": moves is not None,
        "moves": moves,
        "expanded_nodes": expanded,
        "generated_nodes": generated,
    }


def search_unweighted(
    level: Level,
    *,
    lifo: bool = False,
    successors: Callable[[Level, GameState], list[tuple[Move, GameState]]] | None = None,
) -> SearchResult:
    """Duyệt đồ thị dùng chung cho BFS và DFS.

    ``lifo=False`` chọn hàng đợi FIFO (BFS); ``lifo=True`` chọn ngăn xếp LIFO
    (DFS). ``successors`` cho phép truyền hàm sinh trạng thái kế tiếp; nếu bỏ
    trống, dùng các nước đi hợp lệ của trò chơi. Cần đánh dấu trạng thái đã
    thăm để tránh lặp vô hạn và lưu trạng thái cha để dựng đường đi khi gặp đích.
    """
    next_states = successors or (
        lambda current_level, state: get_valid_moves(
            current_level.board,
            state,
        )
    )

    initial_state = level.initial_state
    frontier = deque([initial_state])
    parents: dict[GameState, tuple[GameState, Move] | None] = {
        initial_state: None,
    }
    expanded = 0
    generated = 1

    while frontier:
        if lifo:
            state = frontier.pop()
        else:
            state = frontier.popleft()

        expanded += 1
        if is_goal_state(level.board, state):
            return result_dict(
                reconstruct_path(state, parents),
                expanded,
                generated,
            )

        for move, next_state in next_states(level, state):
            generated += 1
            if next_state in parents:
                continue

            parents[next_state] = (state, move)
            frontier.append(next_state)

    return result_dict(None, expanded, generated)
