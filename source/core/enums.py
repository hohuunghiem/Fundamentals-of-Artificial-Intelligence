"""Các kiểu liệt kê dùng chung trong trò chơi."""
from enum import Enum, auto


class Orientation(Enum):
    """
    Hướng đặt của block 1x1x2.

    STANDING:
        Block chiếm một ô.

    HORIZONTAL:
        Block nằm ngang theo chiều cột.
        Chiếm (row, col) và (row, col + 1).

    VERTICAL:
        Block nằm dọc theo chiều hàng.
        Chiếm (row, col) và (row + 1, col).
    """

    STANDING = auto()
    HORIZONTAL = auto()
    VERTICAL = auto()
    CUBE = auto()


class Move(Enum):
    UP = auto()
    DOWN = auto()
    LEFT = auto()
    RIGHT = auto()
    SWITCH = auto()


class TileType(Enum):
    VOID = auto()
    FLOOR = auto()
    GOAL = auto()

    # Khai báo trước để sau này mở rộng.
    FRAGILE = auto()
    BRIDGE = auto()
    SOFT_SWITCH = auto()
    HEAVY_SWITCH = auto()
    SPLIT_SWITCH = auto()
