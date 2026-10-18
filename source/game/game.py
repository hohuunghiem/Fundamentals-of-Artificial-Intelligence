"""Bộ điều khiển chính của trò chơi."""

import re
from pathlib import Path
from typing import Any, Callable

from ursina import (
    Button,
    Entity,
    Text,
    Vec3,
    camera,
    color,
    destroy,
    invoke,
)

from algorithms.bfs import bfs_search
from algorithms.dfs import dfs_search
from algorithms.ucs import ucs_search
from algorithms.astar import astar_search
from algorithms.profiler import run_with_profiling
from algorithms.result import SolveResult
BACKGROUND_COLOR = color.rgb32(45, 55, 70)


from core.enums import Move, Orientation, TileType
from core.level import Level
from core.level_loader import load_level
from core.state import GameState
from core.transition import apply_move, calculate_moved_block, is_goal_state
from game.renderer import BlockRenderer, BoardRenderer
from game.replay_controller import ReplayController
from gui.statistics_panel import StatisticsPanel

class GameController(Entity):
    MOVE_ANIMATION_TIME = 0.28
    SOLVER_START_DELAY = 0.65
    FALL_ROLL_TIME = 0.30
    FALL_DROP_TIME = 0.70
    FALL_RESET_DELAY = FALL_ROLL_TIME + FALL_DROP_TIME + 0.10
    MOVE_KEYS: dict[str, Move] = {
        "up arrow": Move.UP,
        "w": Move.UP,

        "down arrow": Move.DOWN,
        "s": Move.DOWN,

        "left arrow": Move.LEFT,
        "a": Move.LEFT,

        "right arrow": Move.RIGHT,
        "d": Move.RIGHT,
    }

    # Registry ánh xạ tên thuật toán tới hàm tìm kiếm tương ứng.
    SOLVER_REGISTRY: dict[str, Callable[..., dict[str, Any] | None] | None] = {
        "BFS": bfs_search,
        "DFS": dfs_search,
        "UCS": ucs_search,
        "A*": astar_search,
    }

    def __init__(
        self,
        level_path: str | Path,
        on_back: Callable[[], None] | None = None,
    ) -> None:
        super().__init__()

        self.level_path = Path(level_path)
        self.on_back = on_back

        self.level: Level = load_level(self.level_path)

        self.state: GameState = self.level.initial_state
        self.move_count = 0
        self.has_won = False
        self.is_busy = False
        self._transition_generation = 0
        self._cleaned_up = False

        # Lưu kết quả tìm kiếm để hiển thị trên bảng thống kê.
        self.solver_results: list[SolveResult] = []

        # Bộ điều khiển phát lại lời giải do thuật toán tìm được.
        self.replay_controller: ReplayController | None = None

        # Bảng thống kê kết quả tìm kiếm.
        self.statistics_panel = StatisticsPanel()

        self.next_level_button: Button | None = None
        self.previous_level_button: Button | None = None

        self.board_renderer = BoardRenderer(
            self.level.board,
            self.state.bridge_states,
        )

        self.block_renderer = BlockRenderer()
        self.block_renderer.sync_with_state(self.state,reset_rotation=True,)

        self._create_environment()
        self._create_ui()
        self._setup_camera()
        self._update_status_text()
        self._create_back_button()
        
    def _create_back_button(self) -> None:
        self.back_button = Button(
            parent=camera.ui,
            text="Back",
            position=(-0.80, 0.43),
            scale=(0.14, 0.07),
            color=color.rgb32(13, 38, 57),
            highlight_color=color.rgb32(55, 235, 220),
            texture=None,
        )
        self.back_button.text_entity.color = color.rgb32(55, 235, 220)

        self.back_button.on_click = self._go_back

    def _go_back(self) -> None:
        if self.on_back is not None:
            self.on_back()

    def _create_environment(self) -> None:
        # Gắn ảnh nền phía sau camera tại tọa độ Z cục bộ bằng 50.
        # unlit=True giúp ánh sáng 3D không làm thay đổi ảnh.
        self.bg_plane = Entity(
            parent=camera,
            model="quad",
            texture="assets/background.png",
            position=(0, 0, 50),
            scale=(44, 24.75),
            unlit=True,
        )
        """
        Thiết lập màu nền và ánh sáng cho game.
        """
        # Màu nền thật sự phía sau toàn bộ bàn chơi.
        camera.clear_color = BACKGROUND_COLOR

    def _create_ui(self) -> None:
        """
        Tạo giao diện chữ và các nút chơi lại, tìm kiếm, thống kê.
        """

        self.hud_top_panel = Entity(
            parent=camera.ui,
            model="quad",
            position=(0, 0.465),
            scale=(1.0, 0.075),
            color=color.rgb32(8, 19, 37),
            z=0.5,
        )
        self.hud_top_accent = Entity(
            parent=camera.ui,
            model="quad",
            position=(0, 0.425),
            scale=(1.0, 0.006),
            color=color.rgb32(55, 235, 220),
            z=0.4,
        )
        self.solver_panel = Entity(
            parent=camera.ui,
            model="quad",
            position=(0.72, 0.015),
            scale=(0.30, 0.78),
            color=color.rgb32(8, 19, 37),
            z=0.5,
        )
        self.solver_accent = Entity(
            parent=camera.ui,
            model="quad",
            position=(0.72, 0.405),
            scale=(0.30, 0.006),
            color=color.rgb32(174, 255, 94),
            z=0.4,
        )
        self.status_panel = Entity(
            parent=camera.ui,
            model="quad",
            position=(-0.70, 0.255),
            scale=(0.40, 0.23),
            color=color.rgb32(8, 19, 37),
            z=0.5,
        )
        self.title_text = Text(
            text=self.level.name,
            position=(0, 0.46),
            origin=(0, 0),
            scale=1.15,
            color=color.rgb32(240, 247, 255),
        )

        self.status_text = Text(
            text="",
            position=(-0.87, 0.34),
            scale=0.82,
            color=color.rgb32(174, 255, 94),
        )
        self.solver_heading = Text(
            text="SOLVER LAB",
            position=(0.72, 0.34),
            origin=(0, 0),
            scale=0.9,
            color=color.rgb32(55, 235, 220),
        )

        # ----- Nút chơi lại -----
        self.restart_button = Button(
            text="Restart",
            position=(0.72, 0.43),
            scale=(0.18, 0.07),
            color=color.rgb32(30, 102, 119),
            highlight_color=color.rgb32(55, 235, 220),
            texture=None,
            on_click=self.restart,
        )
        self.restart_button.text_entity.color = color.rgb32(230, 255, 250)

        # ----- Các nút thuật toán tìm kiếm (BFS, DFS, UCS, A*) -----
        solver_names = ["BFS", "DFS", "UCS", "A*"]
        button_start_y = 0.23
        button_spacing = 0.085

        self.solver_buttons: list[Button] = []

        for i, name in enumerate(solver_names):
            btn = Button(
                text=name,
                position=(0.72, button_start_y - i * button_spacing),
                scale=(0.21, 0.064),
                color=color.rgb32(17, 39, 58),
                highlight_color=color.rgb32(48, 94, 112),
                texture=None,
                on_click=self._make_solver_callback(name),
            )
            btn.text_entity.color = color.rgb32(174, 255, 94)
            self.solver_buttons.append(btn)

        # ----- Nút thống kê -----
        self.statistics_button = Button(
            text="Statistics",
            position=(0.72, button_start_y - len(solver_names) * button_spacing - 0.02),
            scale=(0.21, 0.064),
            color=color.rgb32(48, 83, 72),
            highlight_color=color.rgb32(174, 255, 94),
            texture=None,
            on_click=self._toggle_statistics,
        )
        self.statistics_button.text_entity.color = color.rgb32(220, 255, 194)

        # ----- Các nút chuyển màn -----
        self.next_level_button = Button(
            text="Next",
            position=(-0.48, 0.43),
            scale=(0.14, 0.07),
            color=color.rgb32(13, 38, 57),
            highlight_color=color.rgb32(55, 235, 220),
            texture=None,
            on_click=self._go_to_next_level,
        )
        self.next_level_button.text_entity.color = color.rgb32(55, 235, 220)

        self.previous_level_button = Button(
            text="Previous",
            position=(-0.64, 0.43),
            scale=(0.14, 0.07),
            color=color.rgb32(13, 38, 57),
            highlight_color=color.rgb32(55, 235, 220),
            texture=None,
            on_click=self._go_to_previous_level,
        )
        self.previous_level_button.text_entity.color = color.rgb32(
            55, 235, 220
        )

    def _make_solver_callback(self, algorithm_name: str) -> Callable[[], None]:
        """Tạo hàm xử lý sự kiện cho từng nút thuật toán."""

        def callback() -> None:
            self._run_solver(algorithm_name)

        return callback

    def _run_solver(self, algorithm_name: str) -> None:
        """
        Chạy thuật toán tìm kiếm, lưu kết quả và phát lại lời giải.
        """

        replay_is_playing = (
            self.replay_controller is not None
            and self.replay_controller.is_playing
        )
        if self.is_busy or replay_is_playing:
            self._show_temporary_message("Đang chạy, vui lòng đợi!")
            return

        # Ẩn bảng thống kê nếu bảng đang mở.
        if self.statistics_panel.visible:
            self.statistics_panel.hide()

        # Kiểm tra thuật toán đã được cài đặt hay chưa.
        search_fn = self.SOLVER_REGISTRY.get(algorithm_name)

        if search_fn is None:
            self._show_temporary_message(
                f"{algorithm_name}: Chưa implement!"
            )
            return

        # Hiển thị trạng thái đang chạy
        self.restart()
        generation = self._transition_generation
        self.is_busy = True
        self.status_text.text = f"{algorithm_name}: Preparing..."
        self.status_text.color = color.rgb32(255, 255, 0)
        invoke(
            self._run_solver_after_reset,
            generation,
            algorithm_name,
            search_fn,
            delay=self.SOLVER_START_DELAY,
        )

    def _run_solver_after_reset(
        self,
        generation: int,
        algorithm_name: str,
        search_fn: Callable[[Level], dict[str, Any] | None],
    ) -> None:
        """Chạy tìm kiếm sau khi hiển thị trạng thái ban đầu trong chốc lát."""
        if self._cleaned_up or generation != self._transition_generation:
            return

        self.status_text.text = f"{algorithm_name}: Searching..."

        # Chạy thuật toán và thu thập số liệu hiệu năng.
        result = run_with_profiling(algorithm_name, search_fn, self.level)

        # Lưu kết quả, thay thế kết quả cũ nếu thuật toán này đã chạy trước đó.
        self.solver_results = [
            r for r in self.solver_results
            if r.algorithm != algorithm_name
        ]
        self.solver_results.append(result)

        if not result.success:
            self.is_busy = False
            self._show_temporary_message(
                f"{algorithm_name}: Không tìm được lời giải!"
            )
            return

        # Hiển thị kết quả tìm kiếm
        self.status_text.text = (
            f"{algorithm_name}: {result.solution_length} bước | "
            f"{result.search_time:.4f}s | "
            f"{result.memory_usage:.2f}MB"
        )
        self.status_text.color = color.rgb32(0, 255, 0)

        # Bắt đầu phát lại lời giải.
        self.is_busy = False
        self.replay_controller = ReplayController(
            game=self,
            moves=result.moves,
            step_delay=0.4,
        )
        self.replay_controller.start()

    def _toggle_statistics(self) -> None:
        """Bật/tắt panel thống kê."""

        if self.statistics_panel.visible:
            self.statistics_panel.hide()
        else:
            self.statistics_panel.show(self.solver_results)

    def _setup_camera(self) -> None:
        """
        Camera có góc nhìn cố định cho tất cả màn chơi.

        Camera không xoay, không zoom bằng phím và không di chuyển
        trong quá trình chơi. Chỉ điều chỉnh phạm vi nhìn để toàn bộ
        bàn chơi luôn nằm trong màn hình.
        """

        occupied_cells = [
            (row, col)
            for row, board_row in enumerate(self.level.board.tiles)
            for col, tile in enumerate(board_row)
            if tile != TileType.VOID
        ]
        rows = [row for row, _ in occupied_cells]
        cols = [col for _, col in occupied_cells]
        min_row, max_row = min(rows), max(rows)
        min_col, max_col = min(cols), max(cols)

        # Tâm của bàn chơi.
        center_x = (min_col + max_col) / 2
        center_z = -(min_row + max_row) / 2

        board_center = Vec3(
            center_x,
            0,
            center_z,
        )

        # Camera trực giao giúp các viên gạch không bị méo do phối cảnh.
        camera.orthographic = True

        # Một góc nhìn cố định cho tất cả level.
        camera.position = board_center + Vec3(
            10,
            14,
            -14,
        )

        camera.look_at(board_center)

        # Chỉ thay đổi vùng nhìn để level lớn vẫn nằm trọn màn hình.
        occupied_size = max(
            max_col - min_col + 1,
            max_row - min_row + 1,
        )

        camera.fov = occupied_size + 1.5

    def input(self, key: str) -> None:
        """
        Nhận thao tác bàn phím từ Ursina.
        """

        if key == "r":
            self.restart()
            return

        if key == "space":
            self.try_move(Move.SWITCH)
            return

        if key in self.MOVE_KEYS:
            self.try_move(self.MOVE_KEYS[key])
            return

    def try_move(self, move: Move) -> None:
        """
        Thử di chuyển khối theo hướng người chơi đã chọn.

        Bỏ qua thao tác khi đang phát lại lời giải hoặc đã thắng.
        """

        # Phím SPACE chỉ đổi khối được điều khiển khi khối đã tách.
        # Sau khi hai khối nhập lại, bỏ qua phím này.
        if move == Move.SWITCH and not self.state.is_split:
            return

        replay_is_playing = (
            self.replay_controller is not None
            and self.replay_controller.is_playing
        )
        if self.has_won or self.is_busy or replay_is_playing:
            return

        self._execute_move(move)

    def _execute_move(
        self,
        move: Move,
        *,
        allow_when_busy: bool = False,
    ) -> None:
        """
        Thực hiện nước đi nội bộ cho người chơi và chế độ phát lại.

        Không kiểm tra is_busy; chế độ phát lại được phép bỏ qua khóa này.
        """

        # Không cho người chơi bắt đầu hiệu ứng thứ hai từ cùng trạng thái.
        # Chế độ phát lại có thể chủ động bỏ qua điều kiện này.
        if self.is_busy and not allow_when_busy:
            return

        self.is_busy = True
        generation = self._transition_generation

        next_state = apply_move(
            self.level.board,
            self.state,
            move,
        )

        # Nước đi không hợp lệ: block rơi xuống.
        if next_state is None:
            self._show_temporary_message("You fell!")

            moved_block = (
                None
                if self.state.is_split or move == Move.SWITCH
                else calculate_moved_block(self.state.block, move)
            )
            fell_through_fragile = (
                moved_block is not None
                and moved_block.orientation == Orientation.STANDING
                and self.level.board.get_tile(
                    moved_block.row,
                    moved_block.col,
                ) == TileType.FRAGILE
            )

            if fell_through_fragile:
                self.block_renderer.animate_fragile_fall(
                    move=move,
                    current_state=self.state,
                    roll_duration=self.FALL_ROLL_TIME,
                    fall_duration=self.FALL_DROP_TIME,
                )
                self.board_renderer.animate_fragile_collapse(
                    moved_block.row,
                    moved_block.col,
                    delay=self.FALL_ROLL_TIME,
                )
            else:
                self.block_renderer.animate_fall(
                    self.level.board,
                    move,
                    current_state=self.state,
                    roll_duration=self.FALL_ROLL_TIME,
                    fall_duration=self.FALL_DROP_TIME,
                )

            invoke(
                self._reset_after_fall_if_current,
                generation,
                delay=self.FALL_RESET_DELAY,
            )

            return

        # Nước đi hợp lệ: chạy animation trước.
        self.block_renderer.animate_to_state(
            current_state=self.state,
            next_state=next_state,
            move=move,
            duration=self.MOVE_ANIMATION_TIME,
        )

        # Sau khi animation kết thúc mới cập nhật state.
        invoke(
            self._finish_valid_move_if_current,
            generation,
            next_state,
            delay=self.MOVE_ANIMATION_TIME,
        )

    def _finish_valid_move_if_current(
        self,
        generation: int,
        next_state: GameState,
    ) -> None:
        if self._cleaned_up or generation != self._transition_generation:
            return
        self._finish_valid_move(next_state)

    def _reset_after_fall_if_current(self, generation: int) -> None:
        if self._cleaned_up or generation != self._transition_generation:
            return
        self._reset_after_fall()

    def _finish_valid_move(
        self,
        next_state: GameState,
    ) -> None:
        """
        Hoàn tất một nước đi sau animation.
        """

        self.state = next_state
        self.move_count += 1
        self.is_busy = False

        self.board_renderer.sync_bridge_states(self.state.bridge_states)

        self._update_status_text()

        if is_goal_state(self.level.board, self.state):
            self.has_won = True

            self.status_text.text = (
                "YOU WIN!\n"
                f"Moves: {self.move_count}"
            )

            self.status_text.color = color.rgb32(0, 255, 0)

    def _reset_after_fall(self) -> None:
        """
        Đưa block về trạng thái đầu sau khi rơi.
        """

        self.state = self.level.initial_state
        self.move_count = 0
        self.has_won = False
        self.is_busy = False

        self.block_renderer.sync_with_state(
            self.state,
            reset_rotation=True,
        )
        self.board_renderer.sync_bridge_states(self.state.bridge_states)
        self.board_renderer.restore_fragile_tiles()

        self._update_status_text()

    def restart(self) -> None:
        """
        Đưa game về trạng thái ban đầu.
        """

        self._transition_generation += 1

        if self.replay_controller is not None:
            self.replay_controller.stop()
            self.replay_controller = None

        self.state = self.level.initial_state
        self.move_count = 0
        self.has_won = False
        self.is_busy = False

        self.block_renderer.cancel_animation()
        self.block_renderer.sync_with_state(self.state,reset_rotation=True,)
        self.board_renderer.sync_bridge_states(self.state.bridge_states)
        self.board_renderer.restore_fragile_tiles()
        self._update_status_text()

    def _update_status_text(self) -> None:
        """
        Cập nhật số bước và trạng thái của block.
        """

        if self.state.is_split:
            status = (
                f"Moves: {self.move_count}\n"
                f"Status: SPLIT (Active Cube: {self.state.active_cube})\n"
                f"Press [SPACE] to switch control"
            )
        else:
            orientation_name = self.state.block.orientation.name
            status = (
                f"Moves: {self.move_count}\n"
                f"Orientation: {orientation_name}"
            )

        self.status_text.text = status
        self.status_text.color = color.rgb32(255, 255, 255)

    def _show_temporary_message(self, message: str) -> None:
        """
        Hiện thông báo lỗi tạm thời.
        """

        self.status_text.text = message
        self.status_text.color = color.rgb32(255, 0, 0)

        invoke(
            self._restore_status,
            delay=0.7,
        )

    def _restore_status(self) -> None:
        """
        Khôi phục nội dung trạng thái sau thông báo tạm thời.
        """

        if self.has_won:
            return

        self._update_status_text()

    def _get_next_level_path(self) -> Path | None:
        """Tìm đường dẫn đến màn tiếp theo trong thư mục chứa màn chơi."""
        levels = self._get_ordered_level_paths()
        current_path = self.level_path.resolve()
        current_idx = next(
            (
                index
                for index, path in enumerate(levels)
                if path.resolve() == current_path
            ),
            None,
        )
        if current_idx is None or current_idx + 1 >= len(levels):
            return None
        return levels[current_idx + 1]

    def _get_previous_level_path(self) -> Path | None:
        """Tìm đường dẫn đến màn ngay trước màn hiện tại."""
        levels = self._get_ordered_level_paths()
        current_path = self.level_path.resolve()
        current_idx = next(
            (
                index
                for index, path in enumerate(levels)
                if path.resolve() == current_path
            ),
            None,
        )
        if current_idx is None or current_idx == 0:
            return None
        return levels[current_idx - 1]

    def _get_ordered_level_paths(self) -> list[Path]:
        """Lấy các level có dạng levelN.json, sắp xếp theo số N."""
        level_pattern = re.compile(r"^level(\d+)\.json$", re.IGNORECASE)
        numbered_levels: list[tuple[int, Path]] = []

        for path in self.level_path.parent.glob("*.json"):
            match = level_pattern.match(path.name)
            if match:
                numbered_levels.append((int(match.group(1)), path))

        numbered_levels.sort(key=lambda item: item[0])
        return [path for _, path in numbered_levels]

    def _go_to_next_level(self) -> None:
        """Chuyển sang màn kế tiếp khi người chơi chọn nút Next."""
        next_level = self._get_next_level_path()
        if next_level is None:
            self._show_temporary_message("This is the last level!")
            return

        self.load_new_level(next_level)

    def _go_to_previous_level(self) -> None:
        previous_level = self._get_previous_level_path()
        if previous_level is None:
            self._show_temporary_message("This is the first level!")
            return
        self.load_new_level(previous_level)

    def load_new_level(self, next_level_path: Path) -> None:
        """Dọn màn cũ và tải màn mới lên giao diện."""
        # 1. Hủy render của board và block cũ
        self._transition_generation += 1

        if self.board_renderer:
            self.board_renderer.destroy()

        if self.block_renderer:
            self.block_renderer.destroy()

        # 2. Tải level mới
        self.level_path = next_level_path
        self.level = load_level(self.level_path)

        # 3. Reset các biến trạng thái
        self.state = self.level.initial_state
        self.move_count = 0
        self.has_won = False
        self.is_busy = False
        self.solver_results = []
        if self.replay_controller:
            self.replay_controller.stop()
            self.replay_controller = None

        # 4. Khởi tạo lại renderers
        self.board_renderer = BoardRenderer(
            self.level.board,
            self.state.bridge_states,
        )
        self.block_renderer = BlockRenderer()
        self.block_renderer.sync_with_state(self.state, reset_rotation=True)

        # 5. Cập nhật camera để căn giữa map mới
        self._setup_camera()

        # 6. Cập nhật lại UI text hiển thị
        self.title_text.text = self.level.name
        self._update_status_text()

    def cleanup(self) -> None:
        """Xóa các đối tượng cảnh và giao diện do màn hình trò chơi quản lý."""
        if self._cleaned_up:
            return

        self._cleaned_up = True
        self._transition_generation += 1

        if self.replay_controller is not None:
            self.replay_controller.stop()
            self.replay_controller = None

        self.board_renderer.destroy()
        self.block_renderer.destroy()
        self.statistics_panel.destroy()

        for entity_name in (
            "next_level_button",
            "previous_level_button",
            "back_button",
            "restart_button",
            "statistics_button",
            "title_text",
            "status_text",
            "solver_heading",
            "hud_top_panel",
            "hud_top_accent",
            "solver_panel",
            "solver_accent",
            "status_panel",
            "brand_text",
            "bg_plane",
        ):
            entity = getattr(self, entity_name, None)
            if entity is not None:
                destroy(entity)

        for button in self.solver_buttons:
            destroy(button)

        destroy(self)
