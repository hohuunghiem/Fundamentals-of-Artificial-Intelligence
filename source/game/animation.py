"""Các phương thức tạo hiệu ứng chuyển động cho khối."""
from __future__ import annotations

from collections.abc import Callable
from core.board import Board
from core.enums import Move, Orientation
from core.state import GameState
from core.transition import calculate_moved_block

from dataclasses import replace

from ursina import Entity, Vec3, destroy, scene


class BlockAnimator:
    """Quản lý hiệu ứng của khối đang hiển thị."""

    def __init__(self, renderer) -> None:
        self.renderer = renderer
        self.root = renderer.block

        self.tile_top_y = .1

        self.get_position = renderer.position
        self.sync_with_state = renderer.sync_with_state

        self.pivot = None
        self.busy = False

        self.elapsed = 0.0
        self.duration = 0.0

        self._generation = 0
        self._update_motion = None
        self._on_finish = None

        self._fall_entity = self.root

    @staticmethod
    def _get_rotation_delta(move: Move):
        rotations = {
            Move.UP: Vec3(90, 0, 0),
            Move.DOWN: Vec3(-90, 0, 0),
            Move.LEFT: Vec3(0, 0, -90),
            Move.RIGHT: Vec3(0, 0, 90),
        }

        return rotations.get(move, Vec3(0, 0, 0))

    @staticmethod
    def _get_move_direction(move: Move):
        directions = {
            Move.UP: Vec3(0, 0, 1),
            Move.DOWN: Vec3(0, 0, -1),
            Move.LEFT: Vec3(-1, 0, 0),
            Move.RIGHT: Vec3(1, 0, 0),
        }

        return directions.get(move, Vec3(0, 0, 0))

    @staticmethod
    def _get_roll_extent(state: GameState, move: Move) -> float:
        if state.is_split:
            return .5

        orientation = state.block.orientation

        if (
            orientation == Orientation.HORIZONTAL
            and move in (Move.LEFT, Move.RIGHT)
        ):
            return 1.0

        if (
            orientation == Orientation.VERTICAL
            and move in (Move.UP, Move.DOWN)
        ):
            return 1.0

        return .5

    def _begin_motion(
        self,
        duration,
        update_motion,
        on_finish=None,
    ) -> None:
        """Khởi tạo một giai đoạn animation."""

        self.elapsed = 0.0
        self.duration = max(float(duration), .001)

        self._update_motion = update_motion
        self._on_finish = on_finish

        self.busy = True

    def step(self, dt: float) -> None:
        """GameController gọi hàm này mỗi frame."""

        if not self.busy:
            return

        generation = self._generation

        self.elapsed += max(0.0, dt)

        progress = min(
            1.0,
            self.elapsed / self.duration,
        )

        # Smoothstep: chậm ở đầu và cuối chuyển động.
        smooth = (
            progress
            * progress
            * (3.0 - 2.0 * progress)
        )

        if self._update_motion is not None:
            self._update_motion(smooth)

        # Animation đã bị hủy hoặc thay thế.
        if generation != self._generation:
            return

        if progress >= 1.0:
            callback = self._on_finish

            self.busy = False
            self._update_motion = None
            self._on_finish = None

            if callback is not None:
                callback()
    def start(
        self,
        current,
        target,
        move,
        duration=.24,
    ) -> None:
        """Giữ giao diện gọi đang được GameController sử dụng."""

        self.animate_to_state(
            current_state=current,
            next_state=target,
            move=move,
            duration=duration,
        )

    def clear_roll_pivot(self) -> None:
        if self.pivot is None:
            return

        # Giữ nguyên vị trí, góc quay và kích thước thế giới.
        self.root.world_parent = scene

        destroy(self.pivot)
        self.pivot = None

    def _begin_edge_roll(self, state: GameState, move: Move, duration: float) -> None:
        """Bắt đầu lăn khối quanh cạnh tiếp xúc với sàn."""

        self.clear_roll_pivot()

        center = self.get_position(state)

        direction = self._get_move_direction(move)
        extent = self._get_roll_extent(state, move)

        pivot_position = (
            Vec3(
                center.x,
                self.tile_top_y,
                center.z,
            )
            + direction * extent
        )

        self.pivot = Entity(
            position=pivot_position,
        )

        self.root.world_parent = self.pivot

        pivot = self.pivot
        rotation_delta = self._get_rotation_delta(move)

        def update_rotation(progress):
            pivot.rotation = rotation_delta * progress

        self._begin_motion(
            duration=duration,
            update_motion=update_rotation,
        )

    def animate_to_state(self, current_state: GameState, next_state: GameState, move: Move, duration: float = 0.2) -> None:
        """Tạo animation cho một nước đi hợp lệ."""

        self.cancel()

        if current_state.is_split:
            self.animate_split_to_state(
                current_state,
                next_state,
                move,
                duration,
            )
            return

        generation = self._generation

        if move == Move.SWITCH:
            self._sync_if_current(
                generation,
                next_state,
            )
            return

        self._begin_edge_roll(
            current_state,
            move,
            duration,
        )

        self._on_finish = lambda: self._sync_if_current(
            generation,
            next_state,
        )

    def animate_split_to_state(self, current_state: GameState, next_state: GameState, move: Move, duration: float = 0.2) -> None:
        """Di chuyển cube đang được điều khiển."""

        self.cancel()
        generation = self._generation

        if move == Move.SWITCH:
            # Chỉ đổi màu nhận diện cube đang điều khiển.
            self._sync_if_current(
                generation,
                next_state,
            )
            return

        active_index = current_state.active_cube
        cube = self.renderer.cubes[active_index]

        start_position = Vec3(cube.position)

        end_position = (
            start_position
            + self._get_move_direction(move)
        )

        def update_position(progress):
            cube.position = (
                start_position
                + (
                    end_position - start_position
                ) * progress
            )

        self._begin_motion(
            duration=duration,
            update_motion=update_position,
            on_finish=lambda: self._sync_if_current(
                generation,
                next_state,
            ),
        )

    def _sync_if_current(self, generation: int, state: GameState) -> None:
        """Đồng bộ về trạng thái chính xác nếu chưa bị hủy."""

        if generation != self._generation:
            return

        self.cancel()
        self.sync_with_state(state)

    def animate_fall(self, board: Board, move: Move, current_state: GameState, roll_duration: float = 0.25, fall_duration: float = 0.65) -> None:
        """Lăn ra mép bàn rồi nghiêng hoặc rơi xuống."""

        self.cancel()

        if move == Move.SWITCH:
            return

        if current_state.is_split:
            self._fall_entity = self.renderer.cubes[
                current_state.active_cube
            ]

            self._drop_down(
                duration=fall_duration,
                move=move,
            )
            return

        self._fall_entity = self.root

        moved_block = calculate_moved_block(
            current_state.block,
            move,
        )

        moved_state = replace(
            current_state,
            block=moved_block,
        )

        fulcrum = self._get_fall_fulcrum(
            board,
            current_state,
            move,
        )

        generation = self._generation

        self._begin_edge_roll(
            current_state,
            move,
            roll_duration,
        )

        def after_roll():
            if generation != self._generation:
                return

            # Đưa khối về hình học chuẩn sau bước lăn.
            self.sync_with_state(moved_state)

            # sync_with_state có thể gọi cancel(),
            # vì vậy lấy lại generation hiện tại.
            self._tip_or_drop_if_current(
                self._generation,
                fulcrum,
                move,
                fall_duration,
            )

        self._on_finish = after_roll

    def _get_fall_fulcrum(
        self,
        board,
        state,
        move: Move,
    ):
        """Tìm mép ô còn đỡ khối sau nước đi bị rơi."""

        if state.is_split or move == Move.SWITCH:
            return None

        moved_block = calculate_moved_block(
            state.block,
            move,
        )

        occupied_cells = moved_block.occupied_cells()

        supported_cells = [
            (row, col)
            for row, col in occupied_cells
            if board.is_walkable(
                row,
                col,
                state.bridge_states,
            )
        ]

        # Chỉ có một trong hai ô còn được đỡ:
        # dùng mép ô đó làm điểm tựa.
        if (
            len(occupied_cells) != 2
            or len(supported_cells) != 1
        ):
            return None

        row, col = supported_cells[0]

        direction = self._get_move_direction(move)

        return (
            Vec3(
                col,
                self.tile_top_y,
                -row,
            )
            + direction * .5
        )

    def _tip_or_drop_if_current(
        self,
        generation: int,
        fulcrum,
        move: Move,
        duration: float,
    ) -> None:
        """Nghiêng ở mép sàn trước khi rơi, nếu còn điểm tựa."""

        if generation != self._generation:
            return

        if fulcrum is None:
            self._drop_if_current(
                generation,
                duration,
                move,
            )
            return

        self.clear_roll_pivot()

        self.pivot = Entity(position=fulcrum)
        self.root.world_parent = self.pivot

        pivot = self.pivot

        rotation_delta = (
            self._get_rotation_delta(move) * .35
        )

        def update_tip(progress):
            pivot.rotation = rotation_delta * progress

        self._begin_motion(
            duration=duration * .3,
            update_motion=update_tip,
            on_finish=lambda: self._drop_if_current(
                generation,
                duration * .7,
                move,
            ),
        )

    def _drop_if_current(
        self,
        generation: int,
        duration: float,
        move: Move,
    ) -> None:
        """Bắt đầu rơi nếu animation vẫn còn hiệu lực."""

        if generation != self._generation:
            return

        self.clear_roll_pivot()

        self._drop_down(
            duration=duration,
            move=move,
        )

    def _drop_down(
        self,
        duration: float,
        move: Move,
    ) -> None:
        """Hạ khối xuống, kèm một chút dịch chuyển ngang."""

        entity = self._fall_entity

        start_position = Vec3(entity.position)
        direction = self._get_move_direction(move)

        def update_drop(progress):
            entity.position = (
                start_position
                + direction * (.35 * progress)
                + Vec3(0, -6 * progress * progress, 0)
            )

        self._begin_motion(
            duration=duration,
            update_motion=update_drop,
        )

    def animate_fragile_fall(
        self,
        move: Move,
        current_state,
        roll_duration: float,
        fall_duration: float,
        tile_lead: float = .12,
    ) -> None:
        """Lăn lên ô dễ vỡ rồi rơi thẳng xuống."""

        self.cancel()

        if current_state.is_split or move == Move.SWITCH:
            return

        self._fall_entity = self.root

        moved_block = calculate_moved_block(
            current_state.block,
            move,
        )

        moved_state = replace(
            current_state,
            block=moved_block,
        )

        generation = self._generation

        self._begin_edge_roll(
            current_state,
            move,
            roll_duration,
        )

        def after_roll():
            if generation != self._generation:
                return

            self.sync_with_state(moved_state)

            current_generation = self._generation

            def begin_drop():
                self._drop_fragile_if_current(
                    current_generation,
                    fall_duration,
                )

            if tile_lead > 0:
                # Chờ một chút để hiệu ứng ô vỡ có thể đi trước.
                self._begin_motion(
                    duration=tile_lead,
                    update_motion=lambda progress: None,
                    on_finish=begin_drop,
                )
            else:
                begin_drop()

        self._on_finish = after_roll

    def _drop_fragile_if_current(
        self,
        generation: int,
        duration: float,
    ) -> None:
        """Rơi thẳng qua ô dễ vỡ, không dịch chuyển ngang."""

        if generation != self._generation:
            return

        self.clear_roll_pivot()

        entity = self.root
        start_position = Vec3(entity.position)

        def update_drop(progress):
            entity.position = (
                start_position
                + Vec3(0, -6 * progress * progress, 0)
            )

        self._begin_motion(
            duration=duration,
            update_motion=update_drop,
        )

    def cancel(self) -> None:
        """Hủy animation và vô hiệu hóa các callback cũ."""

        self._generation += 1

        self.busy = False
        self.elapsed = 0.0
        self.duration = 0.0

        self._update_motion = None
        self._on_finish = None

        self.clear_roll_pivot()

        self._fall_entity = self.root

    def destroy(self) -> None:
        self.cancel()