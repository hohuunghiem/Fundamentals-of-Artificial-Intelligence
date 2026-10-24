"""Khung các phương thức hiển thị bàn chơi và khối."""
from __future__ import annotations

from ursina import Entity,Vec3,color,destroy,invoke
from ursina.shaders import lit_with_shadows_shader

from core.board import Board
from core.enums import Move, Orientation, TileType
from core.state import GameState

from game.animation import BlockAnimator
from gui.theme import GOLD, ACCENT

from math import sin, pi


class BoardRenderer:
    TILE_HEIGHT = .20

    def __init__(
        self,
        board,
        bridge_states=(),
    ) -> None:
        self.board = board
        self.bridge_states = tuple(bridge_states)

        self.root = Entity()

        self.tiles = {}
        self.collapsed_tiles = set()

        # Các phần viền của ô đích.
        self.goal_edges = []
        self.goal_glows = []

        # Ký hiệu và màu gốc của công tắc.
        self.switch_markers = {}
        self.switch_base_colors = {}

        # Thời gian còn lại của từng hiệu ứng lóe sáng.
        self.switch_flashes = {}

        self.effect_time = 0.0

        self._generation = 0
        self._destroyed = False

        self._create_tiles()
        self.sync_bridge_states(self.bridge_states)

    def _create_tiles(self) -> None:
        """Tạo hình ảnh cho toàn bộ ô trên bàn."""

        draw_index = 0

        for row_index, row in enumerate(self.board.tiles):
            for col_index, tile_type in enumerate(row):
                if tile_type == TileType.VOID:
                    continue

                if tile_type == TileType.GOAL:
                    self._create_goal(
                        row_index,
                        col_index,
                        draw_index,
                    )
                else:
                    self._create_floor(
                        row_index,
                        col_index,
                        tile_type,
                        draw_index,
                    )

                    if tile_type in (
                        TileType.SOFT_SWITCH,
                        TileType.HEAVY_SWITCH,
                        TileType.SPLIT_SWITCH,
                    ):
                        self._create_switch_marker(
                            row_index,
                            col_index,
                            tile_type,
                            draw_index,
                        )

                draw_index += 1

    def _create_floor(
        self,
        row: int,
        col: int,
        tile_type: TileType,
        draw_index: int,
    ) -> None:
        """Tạo một ô sàn hoặc ô đặc biệt."""

        palette = {
            TileType.FRAGILE: color.rgb32(
                209, 132, 104
            ),
            TileType.BRIDGE: color.rgb32(
                74, 191, 192
            ),
            TileType.SOFT_SWITCH: ACCENT,
            TileType.HEAVY_SWITCH: color.rgb32(
                233, 117, 166
            ),
            TileType.SPLIT_SWITCH: color.rgb32(
                103, 158, 242
            ),
        }

        default_color = color.rgb32(
            70 + ((row + col) % 2) * 9,
            84,
            113,
        )

        tile = Entity(
            parent=self.root,
            model="cube",
            texture="white_cube",
            shader=lit_with_shadows_shader,
            position=(col, 0, -row),
            scale=(
                .96,
                self.TILE_HEIGHT,
                .96,
            ),
            color=palette.get(
                tile_type,
                default_color,
            ),
        )

        self.tiles[row, col] = tile

    def _create_switch_marker(
        self,
        row: int,
        col: int,
        tile_type: TileType,
        draw_index: int,
    ) -> None:
        """Tạo ký hiệu công tắc và lưu để điều khiển hiệu ứng."""

        tile = self.tiles[row, col]
        position = (row, col)

        marker_color = color.rgb32(240, 244, 255)

        # Lưu màu thật của ô, kể cả khi đã đổi bảng màu.
        self.switch_base_colors[position] = (
            round(tile.color.r * 255),
            round(tile.color.g * 255),
            round(tile.color.b * 255),
        )

        markers = []

        if tile_type == TileType.SOFT_SWITCH:
            # Dấu trừ.
            marker = Entity(
                parent=tile,
                model="cube",
                position=(0, .57, 0),
                scale=(.42, .12, .12),
                color=marker_color,
                unlit=True,
            )

            markers.append(marker)

        elif tile_type == TileType.HEAVY_SWITCH:
            # Dấu cộng.
            for marker_scale in (
                (.42, .12, .12),
                (.12, .12, .42),
            ):
                marker = Entity(
                    parent=tile,
                    model="cube",
                    position=(0, .57, 0),
                    scale=marker_scale,
                    color=marker_color,
                    unlit=True,
                )

                markers.append(marker)

        elif tile_type == TileType.SPLIT_SWITCH:
            # Hai hình nhỏ tượng trưng cho hai cube.
            for offset in (-.16, .16):
                marker = Entity(
                    parent=tile,
                    model="cube",
                    position=(offset, .57, 0),
                    scale=(.20, .12, .25),
                    color=marker_color,
                    unlit=True,
                )

                markers.append(marker)

        self.switch_markers[position] = markers

    def flash_switch(self, row: int, col: int) -> None:
        """Bật sáng ngay khi công tắc được kích hoạt."""

        if self._destroyed:
            return

        position = (row, col)

        if position not in self.switch_markers:
            return

        # Tổng thời gian hiệu ứng.
        self.switch_flashes[position] = .8

        # Đặt màu ngay, không chờ frame tiếp theo.
        tile = self.tiles.get(position)

        if tile is not None:
            tile.color = color.rgb32(255, 245, 190)

        for marker in self.switch_markers[position]:
            marker.color = color.rgb32(255, 165, 35)


    def update_effects(self, dt: float) -> None:
        """Cập nhật ánh sáng ô đích và công tắc."""

        if self._destroyed:
            return

        dt = max(0.0, min(dt, .05))

        self.effect_time += dt

        # ----- Ô đích sáng theo nhịp -----
        pulse = (
            sin(self.effect_time * pi) + 1
        ) / 2

        goal_color = color.rgb32(
            int(65 + 55 * pulse),
            int(180 + 65 * pulse),
            int(140 + 65 * pulse),
        )

        for edge in self.goal_edges:
            edge.color = goal_color

        glow_alpha = int(35 + 95 * pulse)

        for glow in self.goal_glows:
            glow.color = color.rgba32(
                92,
                232,
                182,
                glow_alpha,
            )

        # ----- Công tắc lóe sáng -----
        for position, remaining in list(
            self.switch_flashes.items()
        ):
            remaining = max(0.0, remaining - dt)

            # Giữ sáng hoàn toàn trong 0.15 giây đầu.
            # Sau đó giảm dần trong 0.65 giây.
            strength = min(1.0, remaining / .65)

            base_color = self.switch_base_colors[position]
            flash_color = (255, 245, 190)

            tile = self.tiles.get(position)

            if tile is not None:
                tile.color = color.rgb32(
                    *[
                        round(
                            base + (bright - base) * strength
                        )
                        for base, bright in zip(
                            base_color,
                            flash_color,
                        )
                    ]
                )

            # Ký hiệu trắng chuyển sang vàng cam.
            marker_base = (240, 244, 255)
            marker_flash = (255, 165, 35)

            current_marker_color = color.rgb32(
                *[
                    round(
                        base + (bright - base) * strength
                    )
                    for base, bright in zip(
                        marker_base,
                        marker_flash,
                    )
                ]
            )

            for marker in self.switch_markers[position]:
                marker.color = current_marker_color

            if remaining <= 0:
                del self.switch_flashes[position]
            else:
                self.switch_flashes[position] = remaining

    def reset_effects(self) -> None:
        """Khôi phục màu công tắc khi chơi lại."""

        if self._destroyed:
            return

        self.switch_flashes.clear()
        self.effect_time = 0.0

        for position, rgb in self.switch_base_colors.items():
            tile = self.tiles.get(position)

            if tile is not None:
                tile.color = color.rgb32(*rgb)

        for markers in self.switch_markers.values():
            for marker in markers:
                marker.color = color.rgb32(240, 244, 255)

    def _create_goal(
        self,
        row: int,
        col: int,
        draw_index: int,
    ) -> None:
        """Tạo viền đích và lớp sáng trang trí xung quanh."""

        # Viền chính, giữ nguyên kích thước lỗ đích.
        edges = [
            (-.44, 0, .12, 1),
            (.44, 0, .12, 1),
            (0, -.44, .76, .12),
            (0, .44, .76, .12),
        ]

        for dx, dz, width, depth in edges:
            edge = Entity(
                parent=self.root,
                model="cube",
                position=(
                    col + dx,
                    0,
                    -row + dz,
                ),
                scale=(
                    width,
                    self.TILE_HEIGHT,
                    depth,
                ),
                color=color.rgb32(92, 232, 182),
                unlit=True,
            )

            self.goal_edges.append(edge)

        # Viền ngoài mỏng và bán trong suốt.
        # Nằm hơi cao hơn mặt sàn để tránh nhấp nháy bề mặt.
        glow_edges = [
            (-.50, 0, .05, 1.05),
            (.50, 0, .05, 1.05),
            (0, -.50, .95, .05),
            (0, .50, .95, .05),
        ]

        for dx, dz, width, depth in glow_edges:
            glow = Entity(
                parent=self.root,
                model="cube",
                position=(
                    col + dx,
                    self.TILE_HEIGHT / 2 + .015,
                    -row + dz,
                ),
                scale=(
                    width,
                    .012,
                    depth,
                ),
                color=color.rgba32(92, 232, 182, 80),
                unlit=True,
            )

            # Viền trang trí không tạo bóng.
            glow.hide(0b0001)

            self.goal_glows.append(glow)

    def animate_fragile_collapse(
        self,
        row: int,
        col: int,
        delay: float = 0.0,
    ) -> None:
        """Ẩn ô dễ vỡ sau khi khối lăn lên ô đó."""

        if self._destroyed:
            return

        if self.board.get_tile(row, col) != TileType.FRAGILE:
            return

        generation = self._generation

        if delay <= 0:
            self._collapse_fragile_if_current(
                generation,
                row,
                col,
            )
        else:
            invoke(
                self._collapse_fragile_if_current,
                generation,
                row,
                col,
                delay=delay,
            )

    def _collapse_fragile_if_current(
        self,
        generation: int,
        row: int,
        col: int,
    ) -> None:
        """Chỉ làm ô biến mất nếu lượt chơi chưa bị đặt lại."""

        if self._destroyed:
            return

        if generation != self._generation:
            return

        tile = self.tiles.get((row, col))

        if tile is None:
            return

        self.collapsed_tiles.add((row, col))
        tile.enabled = False

    def restore_fragile_tiles(self) -> None:
        """Khôi phục các ô dễ vỡ khi chơi lại."""

        if self._destroyed:
            return

        # Vô hiệu hóa các lệnh làm vỡ ô đang chờ.
        self._generation += 1

        self.collapsed_tiles.clear()

        self.sync_bridge_states(
            self.bridge_states
        )

    def sync_bridge_states(
        self,
        bridge_states,
    ) -> None:
        """Cập nhật cầu và giữ các ô đã vỡ ở trạng thái ẩn."""

        if self._destroyed:
            return

        self.bridge_states = tuple(bridge_states)

        for (row, col), tile in self.tiles.items():
            tile.enabled = (
                (row, col) not in self.collapsed_tiles
                and self.board.is_walkable(
                    row,
                    col,
                    self.bridge_states,
                )
            )

    def destroy(self) -> None:
        """Xóa toàn bộ bàn chơi."""

        if self._destroyed:
            return

        self._destroyed = True
        self._generation += 1

        destroy(self.root)

        self.tiles.clear()
        self.collapsed_tiles.clear()


class BlockRenderer:
    @staticmethod
    def _create_box_outline(parent):
        """Tạo 12 cạnh viền cho một khối hộp."""

        outline = Entity(parent=parent)
        outline.hide(0b0001)

        thickness = .012
        edge_position = .501
        edge_color = color.rgb32(65, 46, 35)

        # Bốn cạnh song song với trục X.
        for y in (-edge_position, edge_position):
            for z in (-edge_position, edge_position):
                Entity(
                    parent=outline,
                    model="cube",
                    position=(0, y, z),
                    scale=(
                        1.01,
                        thickness,
                        thickness,
                    ),
                    color=edge_color,
                )

        # Bốn cạnh song song với trục Y.
        for x in (-edge_position, edge_position):
            for z in (-edge_position, edge_position):
                Entity(
                    parent=outline,
                    model="cube",
                    position=(x, 0, z),
                    scale=(
                        thickness,
                        1.01,
                        thickness,
                    ),
                    color=edge_color,
                )

        # Bốn cạnh song song với trục Z.
        for x in (-edge_position, edge_position):
            for y in (-edge_position, edge_position):
                Entity(
                    parent=outline,
                    model="cube",
                    position=(x, y, 0),
                    scale=(
                        thickness,
                        thickness,
                        1.01,
                    ),
                    color=edge_color,
                )

        return outline

    def __init__(self) -> None:
        self._destroyed = False

        self.block = Entity(
            model="cube",
            texture="white_cube",
            shader=lit_with_shadows_shader,
            color=GOLD,
        )

        self._create_box_outline(self.block)

        self.cubes = []

        for _ in range(2):
            cube = Entity(
                model="cube",
                texture="white_cube",
                shader=lit_with_shadows_shader,
                scale=.94,
                enabled=False,
            )

            self._create_box_outline(cube)
            self.cubes.append(cube)

        self.animator = BlockAnimator(self)

    def _get_position(self, state):
        """Tính tâm hiển thị của khối."""

        block = state.block

        if block.orientation == Orientation.HORIZONTAL:
            return Vec3(
                block.col + .5,
                .6,
                -block.row,
            )

        if block.orientation == Orientation.VERTICAL:
            return Vec3(
                block.col,
                .6,
                -block.row - .5,
            )

        if block.orientation == Orientation.CUBE:
            return Vec3(
                block.col,
                .6,
                -block.row,
            )

        return Vec3(
            block.col,
            1.1,
            -block.row,
        )

    def position(self, state):
        """Tên hàm được BlockAnimator sử dụng."""

        return self._get_position(state)

    def _get_initial_rotation(self, state):
        """
        Hình dạng đứng/nằm được biểu diễn bằng scale.

        Vì vậy góc xoay chuẩn sau mỗi bước luôn bằng 0.
        """

        return Vec3(0, 0, 0)

    def sync_with_state(
        self,
        state,
        reset_rotation: bool = False,
    ) -> None:
        """Đồng bộ hình ảnh về trạng thái Game chính xác."""

        if self._destroyed:
            return

        self.cancel_animation()

        self.block.enabled = not state.is_split

        self.block.position = self._get_position(state)

        # Chuẩn hóa góc xoay sau mỗi animation.
        self.block.rotation = self._get_initial_rotation(
            state
        )

        self.block.scale = {
            Orientation.STANDING: (
                .94, 1.94, .94
            ),
            Orientation.HORIZONTAL: (
                1.94, .94, .94
            ),
            Orientation.VERTICAL: (
                .94, .94, 1.94
            ),
            Orientation.CUBE: (
                .94, .94, .94
            ),
        }[state.block.orientation]

        for index, cube in enumerate(self.cubes):
            cube.enabled = state.is_split
            cube.rotation = (0, 0, 0)

            if state.is_split:
                row, col = state.split_cubes[index]

                cube.position = (
                    col,
                    .6,
                    -row,
                )

                cube.color = (
                    GOLD
                    if index == state.active_cube
                    else ACCENT
                )

    def cancel_animation(self) -> None:
        """Hủy animation đang chạy."""

        self.animator.cancel()

    def animate_to_state(
        self,
        current_state,
        next_state,
        move: Move,
        duration: float = .24,
    ) -> None:
        """Hiển thị một nước đi hợp lệ."""

        self.animator.animate_to_state(
            current_state=current_state,
            next_state=next_state,
            move=move,
            duration=duration,
        )

    def animate_fall(
        self,
        board,
        move: Move,
        current_state,
        roll_duration: float = .25,
        fall_duration: float = .65,
    ) -> None:
        """Hiển thị khối lăn khỏi bàn rồi rơi."""

        self.animator.animate_fall(
            board=board,
            move=move,
            current_state=current_state,
            roll_duration=roll_duration,
            fall_duration=fall_duration,
        )

    def animate_fragile_fall(
        self,
        move: Move,
        current_state,
        roll_duration: float,
        fall_duration: float,
    ) -> None:
        """Hiển thị khối rơi xuyên qua ô dễ vỡ."""

        self.animator.animate_fragile_fall(
            move=move,
            current_state=current_state,
            roll_duration=roll_duration,
            fall_duration=fall_duration,
        )

    def destroy(self) -> None:
        """Xóa khối chính, hai cube và tài nguyên animation."""

        if self._destroyed:
            return

        self._destroyed = True

        self.animator.destroy()

        destroy(self.block)

        for cube in self.cubes:
            destroy(cube)

        self.cubes.clear()