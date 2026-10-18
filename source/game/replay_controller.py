"""Bộ điều khiển phát lại: tự động di chuyển khối theo chuỗi nước đi."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ursina import invoke

from core.enums import Move

if TYPE_CHECKING:
    from game.game import GameController


class ReplayController:
    """
    Phát lại chuỗi bước đi do thuật toán tìm kiếm tìm được.

    Dùng ursina.invoke(delay=...) để gọi game.try_move() tuần tự
    sau mỗi khoảng thời gian step_delay.
    """

    def __init__(
        self,
        game: GameController,
        moves: list[Move],
        step_delay: float = 0.4,
    ) -> None:
        self.game = game
        self.moves = list(moves)  # Sao chép danh sách để tránh làm đổi dữ liệu gốc.
        self.step_delay = step_delay

        self._current_step: int = 0
        self.is_playing: bool = False

    def start(self) -> None:
        """Bắt đầu replay từ bước đầu tiên."""

        if not self.moves:
            return

        self.is_playing = True
        self._current_step = 0
        self.game.is_busy = True

        # Bắt đầu phát lại chuỗi nước đi.
        self._play_next_step()

    def _play_next_step(self) -> None:
        """Thực hiện bước tiếp theo trong chuỗi replay."""

        if self._current_step >= len(self.moves):
            # Đã phát lại hết lời giải.
            self.is_playing = False
            self.game.is_busy = False
            return

        move = self.moves[self._current_step]
        self.game._execute_move(move, allow_when_busy=True)
        self._current_step += 1

        # Lên lịch thực hiện nước đi tiếp theo.
        invoke(self._play_next_step, delay=self.step_delay)

    def stop(self) -> None:
        """Hủy phát lại; các lệnh gọi đã lên lịch sẽ không thực hiện nước đi."""
        self.is_playing = False
        self._current_step = len(self.moves)
        self.game.is_busy = False
