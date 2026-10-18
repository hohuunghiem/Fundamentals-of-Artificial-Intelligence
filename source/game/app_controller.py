"""Điều khiển việc chuyển đổi giữa các màn hình của ứng dụng."""

from pathlib import Path

from ursina import Entity, destroy

from game.game import GameController
from game.level_select import LevelSelectScreen
from game.main_menu import MainMenuScreen


class AppController(Entity):
    """
    Quản lý việc chuyển đổi giữa:
    - màn hình chọn level;
    - màn hình chơi game.
    """

    def __init__(self) -> None:
        super().__init__()

        self.current_screen: Entity | None = None

        self.show_main_menu()

    def _clear_current_screen(self) -> None:
        if self.current_screen is None:
            return

        cleanup = getattr(
            self.current_screen,
            "cleanup",
            None,
        )

        if callable(cleanup):
            cleanup()
        else:
            destroy(self.current_screen)

        self.current_screen = None

    def show_main_menu(self) -> None:
        self._clear_current_screen()

        self.current_screen = MainMenuScreen(
            on_play=self.show_level_select,
        )

    def show_level_select(self) -> None:
        self._clear_current_screen()

        self.current_screen = LevelSelectScreen(
            on_level_selected=self.start_level,
            on_back=self.show_main_menu,
        )

    def start_level(self, level_number: int) -> None:
        self._clear_current_screen()

        level_path = Path(f"levels/level{level_number}.json")
        if not level_path.exists():
            print(
                f"Level file does not exist: {level_path}"
            )
            self.show_level_select()
            return

        self.current_screen = GameController(
            level_path=level_path,
            on_back=self.show_level_select,
        )
