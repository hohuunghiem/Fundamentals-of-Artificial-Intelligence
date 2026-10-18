"""Định nghĩa bàn chơi và các thao tác tra cứu ô."""
from dataclasses import dataclass

from core.enums import TileType


@dataclass(frozen=True)
class Board:
    width: int
    height: int
    tiles: tuple[tuple[TileType, ...], ...]
    bridge_ids: tuple[tuple[int, ...], ...] = ()
    switch_links: tuple[
        tuple[int, int, tuple[int, ...], str], ...
    ] = ()
    split_targets: tuple[
        tuple[int, int, tuple[int, int], tuple[int, int]], ...
    ] = ()

    def is_inside(self, row: int, col: int) -> bool:
        return (
            0 <= row < self.height
            and 0 <= col < self.width
        )

    def get_tile(self, row: int, col: int) -> TileType:
        if not self.is_inside(row, col):
            return TileType.VOID

        return self.tiles[row][col]

    def is_walkable(
        self,
        row: int,
        col: int,
        bridge_states: tuple[bool, ...] = (),
    ) -> bool:
        """
        Kiểm tra một ô có thể đỡ block hay không.

        Sàn và ô đích luôn đỡ được khối. Ô cầu chỉ đỡ khối khi cầu đang mở.
        """
        tile = self.get_tile(row, col)

        if tile == TileType.BRIDGE:
            bridge_id = self.get_bridge_id(row, col)
            return (
                bridge_id is not None
                and bridge_id < len(bridge_states)
                and bridge_states[bridge_id]
            )

        return tile in {
            TileType.FLOOR,
            TileType.GOAL,
            TileType.SPLIT_SWITCH,
            TileType.SOFT_SWITCH,
            TileType.HEAVY_SWITCH,
            TileType.FRAGILE,
        }

    def get_bridge_id(self, row: int, col: int) -> int | None:
        if not self.bridge_ids or not self.is_inside(row, col):
            return None

        bridge_id = self.bridge_ids[row][col]
        return bridge_id if bridge_id >= 0 else None

    def get_switch_link(
        self,
        row: int,
        col: int,
    ) -> tuple[tuple[int, ...], str] | None:
        for switch_row, switch_col, bridge_ids, action in self.switch_links:
            if (row, col) == (switch_row, switch_col):
                return bridge_ids, action

        return None

    def get_split_targets(
        self,
        row: int,
        col: int,
    ) -> tuple[tuple[int, int], tuple[int, int]] | None:
        for switch_row, switch_col, cube_a, cube_b in self.split_targets:
            if (row, col) == (switch_row, switch_col):
                return cube_a, cube_b

        return None

    def find_goal(self) -> tuple[int, int]:
        for row in range(self.height):
            for col in range(self.width):
                if self.tiles[row][col] == TileType.GOAL:
                    return row, col

        raise ValueError("Board does not contain a goal tile")
