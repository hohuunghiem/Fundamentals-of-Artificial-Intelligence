"""Lưu trạng thái đầy đủ của trò chơi tại một thời điểm."""
from dataclasses import dataclass

from core.block import Block


@dataclass(frozen=True)
class GameState:
    """
    Lưu vị trí khối, trạng thái các cây cầu và vị trí hai khối lập phương
    khi khối chính bị tách.
    """

    block: Block

    # Mỗi phần tử cho biết một cây cầu đang đóng hay mở.
    bridge_states: tuple[bool, ...] = ()

    # Khi block bị tách, đây sẽ là vị trí hai cube.
    # Tuple rỗng nghĩa là khối chưa bị tách.
    split_cubes: tuple[tuple[int, int], ...] = ()

    # Chỉ số khối lập phương đang được điều khiển khi khối bị tách.
    active_cube: int | None = None

    @property
    def is_split(self) -> bool:
        return len(self.split_cubes) == 2

    def occupied_cells(self) -> tuple[tuple[int, int], ...]:
        """Trả về toàn bộ các ô bị chiếm bởi trạng thái hiện tại (hỗ trợ split)."""
        if self.is_split:
            return self.split_cubes
        return self.block.occupied_cells()
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, GameState):
            return False
        return (
            self.block == other.block
            and self.bridge_states == other.bridge_states
            and self.split_cubes == other.split_cubes
            and self.active_cube == other.active_cube
        )

    def __hash__(self) -> int:
        return hash((
            self.block,
            self.bridge_states,
            self.split_cubes,
            self.active_cube,
        ))
