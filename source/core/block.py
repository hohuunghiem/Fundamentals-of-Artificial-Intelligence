"""Biểu diễn vị trí và hướng của khối trong trò chơi."""
from dataclasses import dataclass

from core.enums import Orientation


@dataclass(frozen=True)  # Đối tượng không thể thay đổi sau khi được tạo.
class Block:
    """
    Trạng thái hình học của block.

    row và col là vị trí neo:
    - STANDING: ô duy nhất block đang đứng.
    - HORIZONTAL: ô bên trái.
    - VERTICAL: ô phía trên.
    """

    row: int
    col: int
    orientation: Orientation

    def occupied_cells(self) -> tuple[tuple[int, int], ...]:
        """
        Trả về tất cả ô mà block đang chiếm.

        Hàm này rất quan trọng vì game và các thuật toán tìm kiếm
        sẽ cùng sử dụng nó để kiểm tra trạng thái hợp lệ.
        """

        if self.orientation == Orientation.STANDING:
            return ((self.row, self.col),)

        if self.orientation == Orientation.HORIZONTAL:
            return (
                (self.row, self.col),
                (self.row, self.col + 1),
            )

        if self.orientation == Orientation.VERTICAL:
            return (
                (self.row, self.col),
                (self.row + 1, self.col),
            )

        raise ValueError(f"Unsupported orientation: {self.orientation}")
