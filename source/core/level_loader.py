"""Đọc, kiểm tra và chuyển dữ liệu JSON thành đối tượng màn chơi."""
import json
from pathlib import Path
from typing import Any

from core.block import Block
from core.board import Board
from core.enums import Orientation, TileType
from core.level import Level
from core.state import GameState

# Ký hiệu tương ứng với từng loại ô trong tệp màn chơi.
TILE_SYMBOLS: dict[str, TileType] = {
    ".": TileType.VOID,
    "#": TileType.FLOOR,
    "G": TileType.GOAL,
    "p": TileType.SPLIT_SWITCH,
    "S": TileType.SPLIT_SWITCH,
    "s": TileType.SOFT_SWITCH,
    "h": TileType.HEAVY_SWITCH,
    "b": TileType.BRIDGE,
    "B": TileType.BRIDGE,
    "f": TileType.FRAGILE,
}


ORIENTATION_NAMES: dict[str, Orientation] = {
    "standing": Orientation.STANDING,
    "horizontal": Orientation.HORIZONTAL,
    "vertical": Orientation.VERTICAL,
}


def _validate_level_data(data: dict[str, Any]) -> None:
    required_fields = {"name", "board", "start"}

    missing_fields = required_fields - data.keys()

    if missing_fields:
        raise ValueError(
            f"Missing level fields: {sorted(missing_fields)}"
        )

    board_data = data["board"]

    if not isinstance(board_data, list) or not board_data:
        raise ValueError("Level board must be a non-empty list")

    width = len(board_data[0])

    if width == 0:
        raise ValueError("Level rows cannot be empty")

    for index, row in enumerate(board_data):
        if len(row) != width:
            raise ValueError(
                f"Board row {index} has an invalid width"
            )

    goal_count = sum(row.count("G") for row in board_data)

    if goal_count != 1:
        raise ValueError(
            f"Level must contain exactly one goal, found {goal_count}"
        )


def load_level(file_path: str | Path) -> Level:
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Level file not found: {path}")

    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except json.JSONDecodeError as error:
        raise ValueError(
            f"Invalid JSON in level file {path}: {error}"
        ) from error

    _validate_level_data(data)

    board_data: list[str] = data["board"]

    tiles: list[tuple[TileType, ...]] = []

    for row_index, row_text in enumerate(board_data):
        converted_row: list[TileType] = []

        for col_index, symbol in enumerate(row_text):
            if symbol not in TILE_SYMBOLS:
                raise ValueError(
                    f"Unknown tile symbol '{symbol}' "
                    f"at row={row_index}, col={col_index}"
                )

            converted_row.append(TILE_SYMBOLS[symbol])

        tiles.append(tuple(converted_row))

    bridges_data = data.get("bridges", [])
    bridge_count = len(bridges_data)
    bridge_ids = [
        [-1 for _ in range(len(board_data[0]))]
        for _ in range(len(board_data))
    ]
    initial_bridge_states = [False] * bridge_count

    for expected_id, bridge_data in enumerate(bridges_data):
        bridge_id = int(bridge_data.get("id", expected_id))
        if bridge_id != expected_id:
            raise ValueError("Bridge IDs must be consecutive starting at 0")

        initial_bridge_states[bridge_id] = bool(
            bridge_data.get("initially_open", False)
        )

        for cell in bridge_data.get("cells", []):
            row, col = int(cell[0]), int(cell[1])
            if not (
                0 <= row < len(board_data)
                and 0 <= col < len(board_data[0])
            ):
                raise ValueError(
                    f"Bridge cell is outside board: ({row}, {col})"
                )
            if tiles[row][col] != TileType.BRIDGE:
                raise ValueError(
                    f"Bridge cell ({row}, {col}) must use symbol 'B'"
                )
            bridge_ids[row][col] = bridge_id

    for row_index, row in enumerate(tiles):
        for col_index, tile in enumerate(row):
            if tile == TileType.BRIDGE and bridge_ids[row_index][col_index] < 0:
                raise ValueError(
                    f"Bridge tile ({row_index}, {col_index}) has no definition"
                )

    switch_links = []
    split_targets = []
    for switch_data in data.get("switches", []):
        row = int(switch_data["row"])
        col = int(switch_data["col"])
        if not (
            0 <= row < len(board_data)
            and 0 <= col < len(board_data[0])
        ):
            raise ValueError(f"Switch is outside board: ({row}, {col})")
        if tiles[row][col] not in {
            TileType.SOFT_SWITCH,
            TileType.HEAVY_SWITCH,
            TileType.SPLIT_SWITCH,
        }:
            raise ValueError(
                f"Switch definition ({row}, {col}) is not on a switch tile"
            )

        if tiles[row][col] == TileType.SPLIT_SWITCH:
            cube_a_data = switch_data.get("cube_a")
            cube_b_data = switch_data.get("cube_b")
            if cube_a_data is not None or cube_b_data is not None:
                if cube_a_data is None or cube_b_data is None:
                    raise ValueError(
                        f"Split switch ({row}, {col}) requires both cube_a and cube_b"
                    )
                cube_a = (int(cube_a_data[0]), int(cube_a_data[1]))
                cube_b = (int(cube_b_data[0]), int(cube_b_data[1]))
                if cube_a == cube_b:
                    raise ValueError("Split cube targets must be different")
                for target_row, target_col in (cube_a, cube_b):
                    if not (
                        0 <= target_row < len(board_data)
                        and 0 <= target_col < len(board_data[0])
                    ):
                        raise ValueError(
                            f"Split target is outside board: ({target_row}, {target_col})"
                        )
                    if tiles[target_row][target_col] == TileType.VOID:
                        raise ValueError(
                            f"Split target is not walkable: ({target_row}, {target_col})"
                        )
                split_targets.append((row, col, cube_a, cube_b))

        targets = tuple(
            int(value) for value in switch_data.get("bridge_ids", [])
        )
        if any(target < 0 or target >= bridge_count for target in targets):
            raise ValueError(
                f"Switch ({row}, {col}) targets an unknown bridge"
            )

        action = str(switch_data.get("action", "open")).lower()
        if action not in {"open", "close", "toggle"}:
            raise ValueError(f"Unknown switch action: {action}")
        switch_links.append((row, col, targets, action))

    board = Board(
        width=len(board_data[0]),
        height=len(board_data),
        tiles=tuple(tiles),
        bridge_ids=tuple(tuple(row) for row in bridge_ids),
        switch_links=tuple(switch_links),
        split_targets=tuple(split_targets),
    )

    start_data = data["start"]

    start_row = int(start_data["row"])
    start_col = int(start_data["col"])
    orientation_name = start_data.get(
        "orientation",
        "standing",
    ).lower()

    if orientation_name not in ORIENTATION_NAMES:
        raise ValueError(
            f"Unknown start orientation: {orientation_name}"
        )

    start_block = Block(
        row=start_row,
        col=start_col,
        orientation=ORIENTATION_NAMES[orientation_name],
    )

    initial_state = GameState(
        block=start_block,
        bridge_states=tuple(initial_bridge_states),
    )

    # Kiểm tra block ban đầu có thực sự nằm trên board hay không.
    for row, col in start_block.occupied_cells():
        if not board.is_walkable(row, col, initial_state.bridge_states):
            raise ValueError(
                f"Initial block is not supported at ({row}, {col})"
            )

    if (
        start_block.orientation == Orientation.STANDING
        and board.get_tile(start_block.row, start_block.col) == TileType.FRAGILE
    ):
        raise ValueError("Initial block cannot stand on a fragile tile")

    return Level(
        name=str(data["name"]),
        board=board,
        initial_state=initial_state,
    )
