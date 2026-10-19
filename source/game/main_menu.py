"""Khung giao diện menu chính; cần hoàn thiện bố cục trong các phương thức."""
from __future__ import annotations

from collections.abc import Callable
from ursina import Entity,camera,destroy,application,window
from gui.theme import BG,ACCENT,GOLD,MUTED,panel,label,button


class MainMenuScreen(Entity):
    """Màn hình menu chính, gọi hàm được truyền vào khi người chơi chọn bắt đầu."""

    def __init__(self, on_play: Callable[[], None]) -> None:
        super().__init__(parent=camera.ui)

        window.color = BG

        panel(
            self,
            -.60,
            .05,
            .012,
            .62,
            ACCENT,
        )

        label(
            self,
            "BLOX / LAB",
            -.53,
            .27,
            3,
        )

        label(
            self,
            "ROLL. THINK. SOLVE.",
            -.53,
            .14,
            1.1,
            GOLD,
        )

        label(
            self,
            "15 puzzles. Four search algorithms.\n"
            "One block. Find your way home.",
            -.53,
            .04,
            1,
            MUTED,
        )

        button(
            self,
            "START EXPLORING",
            -.32,
            -.16,
            on_play,
            .42,
            .075,
            ACCENT,
        )

        button(
            self,
            "EXIT",
            -.32,
            -.27,
            application.quit,
            .42,
        )

        # Họa tiết hình học trang trí.
        for index in range(3):
            panel(
                self,
                .30 + index * .085,
                -.16 + index * .09,
                .16,
                .16,
                ACCENT,
            )

        panel(
            self,
            .47,
            .20,
            .16,
            .30,
            GOLD,
        )

        label(
            self,
            "ARTIFICIAL INTELLIGENCE / SEARCH STUDIO",
            -.53,
            -.43,
            .7,
            MUTED,
        )

    def cleanup(self) -> None:
        destroy(self)