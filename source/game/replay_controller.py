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
        game,
        moves,
        step_delay: float = .38,
    ) -> None:
        self.game = game
        self.moves = list(moves)

        self.step_delay = step_delay

        self._current_step = 0
        self._wait = 0.0

        self.is_playing = False

    def start(self) -> None:
        """Bắt đầu phát lại từ nước đi đầu tiên."""

        self._current_step = 0
        self._wait = 0.0

        self.is_playing = bool(self.moves)

    def update(self, dt: float) -> None:
        """Được GameController gọi mỗi frame."""

        if not self.is_playing:
            return

        if self.game.is_busy:
            return

        if self.game.has_won:
            self.stop()
            return

        self._wait -= dt

        if self._wait > 0:
            return

        self._play_next_step()

    def _play_next_step(self) -> None:
        """Thực hiện nước đi tiếp theo khi Game đã sẵn sàng."""

        if not self.is_playing:
            return

        if self._current_step >= len(self.moves):
            self.stop()
            return

        move = self.moves[self._current_step]

        self.game.execute_move(move)

        self._current_step += 1

        self._wait = max(
            0.0,
            self.step_delay - self.game.MOVE_DURATION,
        )

    def stop(self) -> None:
        """Ngừng phát các nước đi tiếp theo."""
        self.is_playing = False