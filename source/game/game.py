"""Bộ điều khiển chính của trò chơi."""

import re
from pathlib import Path
from typing import Any, Callable

from queue import Queue, Empty
from threading import Thread, Lock

from ursina import (
    Button,
    Entity,
    Text,
    Vec3,
    camera,
    color,
    destroy,
    time,
    window,
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

from gui.theme import (
    BG,
    GOLD,
    ACCENT,
    MUTED,
    panel,
    label,
    button,
)


SOLVERS = {
    "BFS": bfs_search,
    "DFS": dfs_search,
    "UCS": ucs_search,
    "A*": astar_search,
}

MOVE_KEYS = {
    "w": Move.UP,
    "up arrow": Move.UP,
    "s": Move.DOWN,
    "down arrow": Move.DOWN,
    "a": Move.LEFT,
    "left arrow": Move.LEFT,
    "d": Move.RIGHT,
    "right arrow": Move.RIGHT,
    "space": Move.SWITCH,
}

# Không cho nhiều lượt AI chạy đồng thời.
AI_LOCK = Lock()


class GameController(Entity):
    MOVE_DURATION = .24
    FALL_ROLL_DURATION = .25
    FALL_DROP_DURATION = .65

    def __init__(self, level, on_back=None):
        super().__init__()

        self.level = level
        self.on_back = on_back

        self.state = self.level.initial_state
        self.pending_state = None

        self.move_count = 0
        self.has_won = False
        self.is_busy = False

        self.mode = "play"
        self.closed = False

        self.worker = None
        self.messages = Queue()
        self.generation = 0

        self.results = {}
        self.replay = None

        self.statistics = StatisticsPanel()

        self.board = BoardRenderer(
            self.level.board,
            self.state.bridge_states,
        )

        self.block = BlockRenderer()

        self.block.sync_with_state(
            self.state,
            reset_rotation=True,
        )

        self.ui = Entity(parent=camera.ui)

        self._setup_camera()
        self._create_ui()
        self.refresh()

    def _setup_camera(self) -> None:
        """Đặt camera để nhìn toàn bộ bàn chơi."""

        window.color = BG

        board = self.level.board

        center = Vec3(
            (board.width - 1) / 2,
            0,
            -(board.height - 1) / 2,
        )

        camera.orthographic = True

        camera.position = (
            center + Vec3(10, 16, -18)
        )

        camera.look_at(center)

        camera.fov = (
            max(board.width, board.height) * 1.05 + 2
        )

    def _create_ui(self) -> None:
        """Tạo thanh trạng thái và các nút điều khiển."""

        panel(
            parent=self.ui,
            x=0,
            y=.435,
            width=1.74,
            height=.11,
        )

        label(
            parent=self.ui,
            text="BLOX / LAB",
            x=-.83,
            y=.47,
            size=1.2,
            tint=GOLD,
        )

        label(
            parent=self.ui,
            text=self.level.name,
            x=-.83,
            y=.425,
            size=.85,
            tint=MUTED,
        )

        self.status = label(
            parent=self.ui,
            text="",
            x=-.34,
            y=.46,
            size=.78,
        )

        button(
            parent=self.ui,
            text="LEVELS",
            x=.73,
            y=.435,
            action=self.go_back,
            width=.18,
        )

        panel(
            parent=self.ui,
            x=0,
            y=-.365,
            width=1.74,
            height=.23,
        )

        for index, name in enumerate(SOLVERS):
            solver_button = button(
                parent=self.ui,
                text=name,
                x=-.70 + index * .205,
                y=-.31,
                action=lambda n=name: self.solve(n),
                width=.18,
                tint=ACCENT,
            )
            if name == "BFS":
                solver_button.color = BG
                solver_button.highlight_color = BG
                solver_button.pressed_color = ACCENT
            else:
                solver_button.disabled = True
                solver_button.color = BG
                solver_button.text_entity.color = MUTED

        button(
            parent=self.ui,
            text="STOP",
            x=.15,
            y=-.31,
            action=self.stop,
            width=.17,
        )

        button(
            parent=self.ui,
            text="RESTART",
            x=.36,
            y=-.31,
            action=self.restart,
            width=.21,
        )

        button(
            parent=self.ui,
            text="RESULTS",
            x=.65,
            y=-.31,
            action=self.show_results,
            width=.27,
        )

        label(
            parent=self.ui,
            text=(
                "WASD / Arrows: roll    "
                "SPACE: switch cube    "
                "R: restart    ESC: levels"
            ),
            x=-.80,
            y=-.385,
            size=.72,
            tint=MUTED,
        )

        label(
            parent=self.ui,
            text=(
                "Mint: goal   Coral: fragile   "
                "Purple: soft   Pink: heavy   Blue: split"
            ),
            x=-.80,
            y=-.43,
            size=.68,
            tint=MUTED,
        )

    def refresh(self) -> None:
        """Cập nhật thông tin trạng thái."""

        if self.has_won:
            self.status.text = (
                f"COMPLETE!   {self.move_count} moves"
            )
            return

        if self.state.is_split:
            pose = (
                f"Cube {self.state.active_cube + 1}"
            )
        else:
            pose = self.state.block.orientation.name

        self.status.text = (
            f"Moves: {self.move_count}   /   {pose}"
        )

    def input(self, key: str) -> None:
        """Nhận thao tác bàn phím."""

        if self.closed:
            return

        if self.statistics.visible:
            if key == "escape":
                self.statistics.hide()
            return

        if key == "escape":
            self.go_back()
            return

        if key == "r":
            self.restart()
            return

        if key not in MOVE_KEYS:
            return

        if self.is_busy or self.has_won:
            return

        if (
            self.replay is not None
            and self.replay.is_playing
        ):
            return

        self.execute_move(MOVE_KEYS[key])

    def execute_move(self, move: Move) -> None:
        """Áp dụng luật rồi chọn animation tương ứng."""

        if self.closed or self.is_busy or self.has_won:
            return

        if (
            move == Move.SWITCH
            and not self.state.is_split
        ):
            return

        next_state = apply_move(
            self.level.board,
            self.state,
            move,
        )

        self.is_busy = True

        if next_state is None:
            self._begin_fall(move)
            return

        self.pending_state = next_state
        self.mode = "move"

        self.block.animate_to_state(
            current_state=self.state,
            next_state=next_state,
            move=move,
            duration=self.MOVE_DURATION,
        )

    def _begin_fall(self, move: Move) -> None:
        """Phân biệt rơi khỏi bàn và rơi qua ô dễ vỡ."""

        if self.replay is not None:
            self.replay.stop()

        self.mode = "fall"
        self.status.text = "Fell! Resetting..."

        fragile_position = None

        if not self.state.is_split:
            moved_block = calculate_moved_block(
                self.state.block,
                move,
            )

            if (
                moved_block.orientation
                == Orientation.STANDING
                and self.level.board.get_tile(
                    moved_block.row,
                    moved_block.col,
                ) == TileType.FRAGILE
            ):
                fragile_position = (
                    moved_block.row,
                    moved_block.col,
                )

        if fragile_position is not None:
            row, col = fragile_position

            self.block.animate_fragile_fall(
                move=move,
                current_state=self.state,
                roll_duration=self.FALL_ROLL_DURATION,
                fall_duration=self.FALL_DROP_DURATION,
            )

            self.board.animate_fragile_collapse(
                row=row,
                col=col,
                delay=self.FALL_ROLL_DURATION,
            )

        else:
            self.block.animate_fall(
                board=self.level.board,
                move=move,
                current_state=self.state,
                roll_duration=self.FALL_ROLL_DURATION,
                fall_duration=self.FALL_DROP_DURATION,
            )

    def update(self) -> None:
        """Cập nhật Game theo từng frame."""

        if self.closed:
            return

        dt = min(time.dt, .05)

        self._receive_ai_results()

        if self.statistics.visible:
            return

        if self.mode in ("move", "fall"):
            self.block.animator.step(dt)

            if not self.block.animator.busy:
                if self.mode == "move":
                    self._finish_move()
                else:
                    self.restart()

        if (
            self.replay is not None
            and not self.has_won
        ):
            self.replay.update(dt)

    def _finish_move(self) -> None:
        """Cập nhật trạng thái logic sau khi lăn xong."""

        self.state = self.pending_state
        self.pending_state = None

        self.move_count += 1

        self.board.sync_bridge_states(
            self.state.bridge_states
        )

        self.has_won = is_goal_state(
            self.level.board,
            self.state,
        )

        self.mode = "play"
        self.is_busy = False

        if self.has_won and self.replay is not None:
            self.replay.stop()

        self.refresh()

    def stop(self) -> None:
        """Dừng replay hoặc bỏ qua kết quả AI đang chờ."""

        self.generation += 1

        if self.replay is not None:
            self.replay.stop()

        if self.mode == "search":
            self.mode = "play"
            self.is_busy = False

            self.status.text = (
                "AI result ignored. Manual play enabled."
            )

    def restart(self) -> None:
        """Đưa Game về trạng thái đầu màn."""

        if self.closed:
            return

        self.stop()
        self.statistics.hide()

        self.state = self.level.initial_state
        self.pending_state = None

        self.move_count = 0
        self.has_won = False
        self.is_busy = False

        self.mode = "play"
        self.replay = None

        self.block.sync_with_state(
            self.state,
            reset_rotation=True,
        )

        self.board.restore_fragile_tiles()

        self.board.sync_bridge_states(
            self.state.bridge_states
        )

        self.refresh()

    def solve(self, name: str) -> None:
        """Gọi module AI qua API hiện có."""

        if self.closed or self.statistics.visible:
            return

        search_function = SOLVERS.get(name)

        if search_function is None:
            self.status.text = (
                f"{name}: unavailable."
            )
            return

        if not AI_LOCK.acquire(blocking=False):
            self.status.text = (
                "AI is still running. Please wait."
            )
            return

        self.restart()

        self.mode = "search"
        self.is_busy = True

        self.status.text = (
            f"{name}: searching..."
        )

        generation = self.generation
        level = self.level
        messages = self.messages

        def work():
            try:
                result = run_with_profiling(
                    name,
                    search_function,
                    level,
                )

                if result is None:
                    messages.put(
                        (
                            generation,
                            name,
                            None,
                            "AI module is not ready.",
                        )
                    )
                    return

                required_fields = (
                    "algorithm",
                    "success",
                    "moves",
                    "search_time",
                    "memory_usage",
                    "expanded_nodes",
                    "generated_nodes",
                )

                if any(
                    not hasattr(result, field)
                    for field in required_fields
                ):
                    raise ValueError(
                        "Invalid AI result structure"
                    )

                if not isinstance(
                    result.moves,
                    (list, tuple),
                ):
                    raise ValueError(
                        "AI moves must be a list or tuple"
                    )

                if any(
                    not isinstance(move, Move)
                    for move in result.moves
                ):
                    raise ValueError(
                        "AI returned an invalid move type"
                    )

                numeric_fields = (
                    "search_time",
                    "memory_usage",
                    "expanded_nodes",
                    "generated_nodes",
                )

                for field in numeric_fields:
                    value = getattr(result, field)

                    if not isinstance(value, (int, float)):
                        raise ValueError(
                            f"Invalid AI field: {field}"
                        )

                if result.success:
                    checked_state = level.initial_state

                    for move in result.moves:
                        checked_state = apply_move(
                            level.board,
                            checked_state,
                            move,
                        )

                        if checked_state is None:
                            raise ValueError(
                                "AI solution contains an illegal move"
                            )

                    if not is_goal_state(
                        level.board,
                        checked_state,
                    ):
                        raise ValueError(
                            "AI solution does not reach the goal"
                        )

                messages.put(
                    (
                        generation,
                        name,
                        result,
                        None,
                    )
                )

            except NotImplementedError:
                messages.put(
                    (
                        generation,
                        name,
                        None,
                        "AI is not implemented yet.",
                    )
                )

            except Exception as error:
                print(
                    f"[AI ERROR] {name}: {error}"
                )

                messages.put(
                    (
                        generation,
                        name,
                        None,
                        "AI error. Check the terminal.",
                    )
                )

            finally:
                AI_LOCK.release()

        self.worker = Thread(
            target=work,
            daemon=True,
        )

        try:
            self.worker.start()
        except Exception as error:
            AI_LOCK.release()

            self.mode = "play"
            self.is_busy = False

            self.status.text = (
                "Cannot start AI worker."
            )

            print(
                f"[THREAD ERROR] {error}"
            )

    def _receive_ai_results(self) -> None:
        """Nhận dữ liệu từ AI và cập nhật GUI ở luồng chính."""

        while True:
            try:
                generation, name, result, error = (
                    self.messages.get_nowait()
                )
            except Empty:
                return

            if generation != self.generation:
                continue

            self.mode = "play"
            self.is_busy = False

            if error is not None:
                self.status.text = error
                continue

            self.results[name] = result

            if not result.success:
                self.status.text = (
                    "AI did not find a solution."
                )
                continue

            self.replay = ReplayController(
                game=self,
                moves=result.moves,
            )

            self.replay.start()

            self.has_won = is_goal_state(
                self.level.board,
                self.state,
            )

            self.refresh()

    def show_results(self) -> None:
        """Mở bảng kết quả theo thứ tự các thuật toán."""

        if self.closed:
            return

        ordered_results = [
            self.results[name]
            for name in SOLVERS
            if name in self.results
        ]

        self.statistics.show(
            ordered_results
        )

    def go_back(self) -> None:
        """Quay về màn chọn level."""

        if self.on_back is not None:
            self.on_back()

    def cleanup(self) -> None:
        """Xóa các tài nguyên khi rời màn chơi."""

        if self.closed:
            return

        self.stop()
        self.closed = True

        self.statistics.destroy()
        self.board.destroy()
        self.block.destroy()

        destroy(self.ui)
        destroy(self)
