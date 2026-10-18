"""Tính nước đi và áp dụng luật chuyển trạng thái của trò chơi."""
from core.block import Block
from core.board import Board
from core.enums import Move, Orientation, TileType
from core.state import GameState


def calculate_moved_block(block: Block, move: Move) -> Block:
    """
    Tính vị trí và orientation mới sau khi block lăn.

    Hàm này chỉ tính hình học.
    Nó chưa kiểm tra block mới có nằm trên board hay không.
    """

    row = block.row
    col = block.col
    orientation = block.orientation

    # Block đang đứng.
    if orientation == Orientation.STANDING:
        if move == Move.UP:
            return Block(row - 2, col, Orientation.VERTICAL)

        if move == Move.DOWN:
            return Block(row + 1, col, Orientation.VERTICAL)

        if move == Move.LEFT:
            return Block(row, col - 2, Orientation.HORIZONTAL)

        if move == Move.RIGHT:
            return Block(row, col + 1, Orientation.HORIZONTAL)

    # Block đang nằm ngang theo chiều cột.
    elif orientation == Orientation.HORIZONTAL:
        if move == Move.UP:
            return Block(row - 1, col, Orientation.HORIZONTAL)

        if move == Move.DOWN:
            return Block(row + 1, col, Orientation.HORIZONTAL)

        if move == Move.LEFT:
            return Block(row, col - 1, Orientation.STANDING)

        if move == Move.RIGHT:
            return Block(row, col + 2, Orientation.STANDING)

    # Block đang nằm dọc theo chiều hàng.
    elif orientation == Orientation.VERTICAL:
        if move == Move.UP:
            return Block(row - 1, col, Orientation.STANDING)

        if move == Move.DOWN:
            return Block(row + 2, col, Orientation.STANDING)

        if move == Move.LEFT:
            return Block(row, col - 1, Orientation.VERTICAL)

        if move == Move.RIGHT:
            return Block(row, col + 1, Orientation.VERTICAL)

    raise ValueError(
        f"Unsupported transition: "
        f"orientation={orientation}, move={move}"
    )


def is_block_supported(
    board: Board,
    state: GameState,
    block: Block,
) -> bool:
    """
    Kiểm tra tất cả ô block chiếm đều có thể đỡ block.
    """

    # Gạch mềm chỉ đỡ được block khi nằm ngang hoặc nằm dọc. Khi block
    # đứng thẳng, toàn bộ trọng lượng dồn lên một ô và gạch sẽ vỡ.
    if (
        block.orientation == Orientation.STANDING
        and board.get_tile(block.row, block.col) == TileType.FRAGILE
    ):
        return False

    for row, col in block.occupied_cells():
        if not board.is_walkable(
            row,
            col,
            state.bridge_states,
        ):
            return False

    return True


def find_split_targets(
    board: Board,
    row: int,
    col: int,
    bridge_states: tuple[bool, ...] = (),
) -> tuple[tuple[int, int], tuple[int, int]] | None:
    """
    Tìm 2 ô lân cận phù hợp để đặt 2 khối lập phương khi block bị tách.
    Thứ tự ưu tiên: cặp ô ngang, rồi đến cặp ô dọc, cuối cùng là bất kỳ cặp ô nào walkable.
    """
    configured_targets = board.get_split_targets(row, col)
    if configured_targets is not None:
        if all(
            board.is_walkable(r, c, bridge_states)
            for r, c in configured_targets
        ):
            return configured_targets
        return None

    horizontal = [(row, col - 1), (row, col + 1)]
    vertical = [(row - 1, col), (row + 1, col)]

    # 1. Thử cả 2 ô ngang
    if all(board.is_walkable(r, c, bridge_states) for r, c in horizontal):
        return (horizontal[0], horizontal[1])

    # 2. Thử cả 2 ô dọc
    if all(board.is_walkable(r, c, bridge_states) for r, c in vertical):
        return (vertical[0], vertical[1])

    # 3. Fallback: Chọn bất kỳ 2 ô lân cận nào walkable
    all_neighbors = horizontal + vertical
    walkable = [
        pos
        for pos in all_neighbors
        if board.is_walkable(pos[0], pos[1], bridge_states)
    ]
    if len(walkable) >= 2:
        return (walkable[0], walkable[1])

    return None


def apply_split_move(
    board: Board,
    state: GameState,
    move: Move,
) -> GameState | None:
    """
    Xử lý bước di chuyển của khối đơn khi block đang bị tách làm hai.
    """
    cubes = list(state.split_cubes)
    active_idx = state.active_cube
    inactive_idx = 1 - active_idx

    active_pos = cubes[active_idx]
    inactive_pos = cubes[inactive_idx]

    # Hành động chuyển đổi quyền điều khiển
    if move == Move.SWITCH:
        new_active = inactive_idx
        new_active_pos = cubes[new_active]
        return GameState(
            block=Block(new_active_pos[0], new_active_pos[1], Orientation.CUBE),
            bridge_states=state.bridge_states,
            split_cubes=state.split_cubes,
            active_cube=new_active,
        )

    # Tính vị trí mới của khối chủ động
    r, c = active_pos
    if move == Move.UP:
        new_pos = (r - 1, c)
    elif move == Move.DOWN:
        new_pos = (r + 1, c)
    elif move == Move.LEFT:
        new_pos = (r, c - 1)
    elif move == Move.RIGHT:
        new_pos = (r, c + 1)
    else:
        return None

    # Khối chủ động phải di chuyển trên ô hợp lệ
    if not board.is_walkable(new_pos[0], new_pos[1], state.bridge_states):
        return None

    # Không được chồng khít lên vị trí khối bị động
    if new_pos == inactive_pos:
        return None

    # Kiểm tra tự động hợp nhất (kề cạnh - khoảng cách Manhattan bằng 1)
    if abs(new_pos[0] - inactive_pos[0]) + abs(new_pos[1] - inactive_pos[1]) == 1:
        if new_pos[0] == inactive_pos[0]:
            # Cùng hàng -> Nằm ngang
            orientation = Orientation.HORIZONTAL
            row = new_pos[0]
            col = min(new_pos[1], inactive_pos[1])
        else:
            # Cùng cột -> Nằm dọc
            orientation = Orientation.VERTICAL
            row = min(new_pos[0], inactive_pos[0])
            col = new_pos[1]

        merged_block = Block(row, col, orientation)
        return GameState(
            block=merged_block,
            bridge_states=state.bridge_states,
            split_cubes=(),
            active_cube=None,
        )

    # Nếu chưa chạm nhau, cập nhật vị trí khối chủ động
    new_cubes = list(state.split_cubes)
    new_cubes[active_idx] = new_pos

    return GameState(
        block=Block(new_pos[0], new_pos[1], Orientation.CUBE),
        bridge_states=state.bridge_states,
        split_cubes=tuple(new_cubes),
        active_cube=active_idx,
    )


def get_activated_switches(
    board: Board,
    state: GameState,
) -> tuple[tuple[int, int], ...]:
    """Trả về các công tắc mềm và công tắc nặng đang được nhấn."""

    activated: list[tuple[int, int]] = []

    for row, col in state.occupied_cells():
        tile = board.get_tile(row, col)

        if tile == TileType.SOFT_SWITCH:
            activated.append((row, col))
        elif (
            tile == TileType.HEAVY_SWITCH
            and not state.is_split
            and state.block.orientation == Orientation.STANDING
        ):
            activated.append((row, col))

    return tuple(activated)


def _is_state_supported(board: Board, state: GameState) -> bool:
    return all(
        board.is_walkable(row, col, state.bridge_states)
        for row, col in state.occupied_cells()
    )


def _apply_switch_effects(
    board: Board,
    previous_state: GameState,
    next_state: GameState,
) -> GameState | None:
    previously_pressed = set(
        get_activated_switches(board, previous_state)
    )
    currently_pressed = set(get_activated_switches(board, next_state))
    bridge_states = list(next_state.bridge_states)

    for row, col in currently_pressed - previously_pressed:
        link = board.get_switch_link(row, col)
        if link is None:
            continue

        bridge_ids, action = link
        for bridge_id in bridge_ids:
            if action == "open":
                bridge_states[bridge_id] = True
            elif action == "close":
                bridge_states[bridge_id] = False
            else:
                bridge_states[bridge_id] = not bridge_states[bridge_id]

    final_state = GameState(
        block=next_state.block,
        bridge_states=tuple(bridge_states),
        split_cubes=next_state.split_cubes,
        active_cube=next_state.active_cube,
    )

    if not _is_state_supported(board, final_state):
        return None

    return final_state


def apply_move(
    board: Board,
    state: GameState,
    move: Move,
) -> GameState | None:
    """
    Áp dụng một hành động lên state (hỗ trợ cả block bình thường và split block).

    Trả về:
        Trạng thái mới nếu nước đi hợp lệ; None nếu khối rơi khỏi bàn
        hoặc đi vào ô trống.
    """

    if state.is_split:
        next_state = apply_split_move(board, state, move)
        if next_state is None:
            return None
        return _apply_switch_effects(board, state, next_state)

    # Không thể SWITCH khi block chưa bị tách
    if move == Move.SWITCH:
        return None

    moved_block = calculate_moved_block(state.block, move)

    if not is_block_supported(board, state, moved_block):
        return None

    # Kiểm tra trigger chia cắt (Split Switch) khi block đứng thẳng trên ô chia cắt
    if moved_block.orientation == Orientation.STANDING:
        tile = board.get_tile(moved_block.row, moved_block.col)
        if tile == TileType.SPLIT_SWITCH:
            targets = find_split_targets(
                board,
                moved_block.row,
                moved_block.col,
                state.bridge_states,
            )
            if targets is not None:
                pos0, pos1 = targets
                next_state = GameState(
                    block=Block(pos0[0], pos0[1], Orientation.CUBE),
                    bridge_states=state.bridge_states,
                    split_cubes=(pos0, pos1),
                    active_cube=0,
                )
                return _apply_switch_effects(board, state, next_state)

    next_state = GameState(
        block=moved_block,
        bridge_states=state.bridge_states,
        split_cubes=state.split_cubes,
        active_cube=state.active_cube,
    )
    return _apply_switch_effects(board, state, next_state)


def is_goal_state(board: Board, state: GameState) -> bool:
    """
    Chỉ thắng khi block đang đứng trên ô goal.
    """

    if state.is_split:
        return False

    block = state.block

    if block.orientation != Orientation.STANDING:
        return False

    return board.get_tile(block.row, block.col) == TileType.GOAL


def get_valid_moves(
    board: Board,
    state: GameState,
) -> list[tuple[Move, GameState]]:
    """
    Sinh tất cả successor hợp lệ từ một state.

    Đây là hàm các thuật toán tìm kiếm sẽ sử dụng.
    """

    successors: list[tuple[Move, GameState]] = []

    for move in Move:
        next_state = apply_move(board, state, move)

        if next_state is not None:
            successors.append((move, next_state))

    return successors
