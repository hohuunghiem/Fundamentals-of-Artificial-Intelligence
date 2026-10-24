"""Tìm kiếm chi phí đồng nhất (UCS)."""
from heapq import heappop, heappush
from itertools import count

from core.enums import Move
from core.level import Level
from core.state import GameState
from core.transition import get_valid_moves, is_goal_state

from algorithms.common import (
    SearchResult,
    reconstruct_path,
    result_dict,
)


def ucs_search(level: Level) -> SearchResult:
    """Luôn mở rộng trạng thái có tổng chi phí đường đi thấp nhất.

    Dùng hàng đợi ưu tiên và cập nhật chi phí tốt nhất đã biết cho mỗi trạng
    thái. Hiện mỗi nước đi đều có chi phí 1, vì vậy lời giải tối ưu của UCS
    tương đương BFS. Trả về kết quả theo cấu trúc ``SearchResult``.
    """

    # Lấy trạng thái ban đầu của màn chơi, là một đối tượng GameState.
    # Trạng thái này chứa:
    # - block: vị trí (hàng, cột) và tư thế của khối.
    # - bridge_states: trạng thái mở/đóng của từng cầu.
    # - split_cubes: vị trí hai khối nhỏ nếu đã tách; () nếu chưa tách.
    # - active_cube: khối nhỏ đang điều khiển; None nếu chưa tách.
    # Bản đồ được lưu riêng trong level.board.
    start = level.initial_state # 

    # Tạo số thứ tự để phân biệt các trạng thái cùng chi phí.
    counter = count()

    # Mỗi phần tử: (chi phí, số thứ tự, trạng thái).
    frontier = [(0, next(counter), start)]

    # Chi phí thấp nhất đã biết để đến mỗi trạng thái.
    best_cost = {start: 0}

    # Trạng thái đầu không có cha.
    parents: dict[GameState, tuple[GameState, Move] | None] = {
        start: None,
    }

    expanded = 0
    generated = 1

    while frontier:
        # Lấy trạng thái đang có tổng chi phí thấp nhất.
        cost, _, current = heappop(frontier)

        # Bỏ qua mục cũ nếu trạng thái này đã có đường đi rẻ hơn.
        if cost != best_cost.get(current):
            continue

        expanded += 1

        # Nếu đã đến đích thì dựng lại đường đi và trả kết quả.
        if is_goal_state(level.board, current):
            return result_dict(
                reconstruct_path(current, parents),
                expanded,
                generated,
            )

        # Thử tất cả các nước đi hợp lệ từ trạng thái hiện tại.
        for move, next_state in get_valid_moves(level.board, current):
            generated += 1

            # Hiện tại mỗi nước đi có chi phí bằng 1.
            new_cost = cost + 1

            # Chỉ lưu nếu đây là đường đi rẻ hơn đến trạng thái kế tiếp.
            if new_cost >= best_cost.get(next_state, float("inf")):
                continue

            best_cost[next_state] = new_cost
            parents[next_state] = (current, move)

            # Đưa trạng thái mới vào hàng đợi ưu tiên.
            heappush(
                frontier,
                (new_cost, next(counter), next_state),
            )

    # Hàng đợi rỗng mà chưa gặp đích nghĩa là không có lời giải.
    return result_dict(None, expanded, generated)
