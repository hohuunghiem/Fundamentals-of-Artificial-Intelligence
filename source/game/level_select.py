"""Khung giao diện chọn màn chơi."""
from __future__ import annotations

from collections.abc import Callable
from ursina import Entity,camera,window,destroy,load_texture,color

from pathlib import Path
from gui.theme import BG,ACCENT,GOLD,MUTED,panel,label,button,ERROR,PANEL

LEVELS_DIRECTORY = Path(__file__).resolve().parents[1] / "levels"
ASSETS_DIRECTORY = Path(__file__).resolve().parents[1] / "assets"


class LevelSelectScreen(Entity):
    """Màn hình chọn màn chơi từ 1 đến 15."""

    LEVEL_NUMBERS = tuple(range(1, 16))

    def __init__(
        self,
        on_level_selected: Callable[[int], None],
        on_back: Callable[[], None],
    ) -> None:
        super().__init__(parent=camera.ui)

        # Lưu các hàm xử lý để những phương thức bên dưới sử dụng.
        self.on_level_selected = on_level_selected
        self.on_back = on_back

        self.level_buttons = []

        self._create_background()
        self._create_title()
        self._create_level_buttons()
        self._create_back_button()
        
    def _create_background(self) -> None:
        """Tạo nền và khung chứa các nút."""
        window.color = BG

        # Ảnh nền phủ màn hình, nằm phía sau các thành phần khác.
        self.background = Entity(
            parent=self,
            model="quad",
            texture=load_texture("menuSelect.png", folder=ASSETS_DIRECTORY),
            position=(0, 0, 1),
            scale=(window.aspect_ratio * 2, 2),
            color=color.rgb32(180, 180, 200),
        )

        # Khung chứa lưới 15 nút.
        self.level_panel = panel(
            parent=self,
            x=0,
            y=-.02,
            width=1.30,
            height=.66,
            tint=PANEL,
            z=.5,
        )

        # Đường nhấn màu tím bên dưới phần tiêu đề.
        self.accent_line = panel(
            parent=self,
            x=0,
            y=.255,
            width=1.30,
            height=.006,
            tint=ACCENT,
            z=.4,
        )

    def _create_title(self) -> None:
        """Tạo tiêu đề, phụ đề, thông báo lỗi và chú thích."""
        self.title = label(
            parent=self,
            text="CHOOSE YOUR PUZZLE",
            x=-.61,
            y=.37,
            size=1.8,
        )

        self.subtitle = label(
            parent=self,
            text="01 - 15 / Practice, explore, compare",
            x=-.61,
            y=.29,
            size=.9,
            tint=MUTED,
        )

        # Ban đầu chưa có lỗi nên để chuỗi rỗng.
        self.message = label(
            parent=self,
            text="",
            x=-.61,
            y=-.30,
            size=.75,
            tint=ERROR,
        )

        self.legend = label(
            parent=self,
            text="Amber block / Mint goal / Purple switches",
            x=-.61,
            y=-.36,
            size=.8,
            tint=GOLD,
        )

    def _create_level_buttons(self) -> None:
        """Tạo 15 nút, bố trí thành 3 hàng và 5 cột."""

        columns = 5

        start_x = -.48
        start_y = .145

        spacing_x = .24
        spacing_y = .12

        for index, number in enumerate(self.LEVEL_NUMBERS):
            row = index // columns
            col = index % columns

            x = start_x + col * spacing_x
            y = start_y - row * spacing_y

            level_button = button(
                parent=self,
                text=f"{number:02d}",
                x=x,
                y=y,
                action=lambda n=number: self.on_level_selected(n),
                width=.20,
                height=.11,
                tint=BG,
            )

            level_path = (
                LEVELS_DIRECTORY / f"level{number}.json"
            )

            # Không cho chọn màn chưa có file dữ liệu.
            if not level_path.exists():
                level_button.disabled = True
                level_button.color = PANEL
                level_button.text_entity.color = MUTED

            self.level_buttons.append(level_button)

    def _create_back_button(self) -> None:
        """Tạo nút quay về menu chính."""

        self.back_button = button(
            parent=self,
            text="BACK",
            x=-.51,
            y=-.44,
            action=self.on_back,
            width=.20,
            height=.055,
        )


    def show_error(self, message):
        self.message.text = message

    def cleanup(self) -> None:
        destroy(self)
