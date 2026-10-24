"""Bộ điều khiển chính của trò chơi."""

import re
from pathlib import Path
from typing import Any, Callable
from queue import Queue, Empty
from threading import Thread, Lock
from math import sin, cos, pi
from random import Random

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
    Mesh,
    DirectionalLight,
    application,
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
from core.transition import apply_move, calculate_moved_block, is_goal_state, get_activated_switches
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

class LevelAtmosphere(Entity):
    """Nền động và hiệu ứng trang trí cho màn chơi."""

    def __init__(self, game):
        super().__init__(parent=game)

        self.game = game
        self.elapsed = 0.0
        self.closed = False

        # Bộ sinh số riêng, không ảnh hưởng random của phần AI.
        self.rng = Random(27)

        self.stars = []
        self.floating_cubes = []
        self.win_particles = []

        # Nền gắn với camera và nằm xa phía sau bàn chơi.
        self.background_root = Entity(
            parent=camera,
            position=(0, 0, 90),
        )
        self.background_root.hide(0b0001)

        self._create_background()
        self._create_stars()
        self._create_floating_cubes()

        # Hiệu ứng chiến thắng nằm trong không gian bàn chơi.
        self.effects_root = Entity(parent=self)

        self.effects_root.hide(0b0001)

        self._update_background(0.0)

    def _create_background(self):
        """Tạo nền chuyển sắc bằng màu tại các đỉnh."""

        background_mesh = Mesh(
            vertices=[
                (-.5, -.5, 0),
                (.5, -.5, 0),
                (.5, .5, 0),
                (-.5, .5, 0),
            ],
            triangles=[
                (0, 1, 2),
                (0, 2, 3),
            ],
            colors=[
                color.rgb32(8, 20, 35),
                color.rgb32(15, 31, 48),
                color.rgb32(35, 24, 63),
                color.rgb32(15, 17, 36),
            ],
            mode="triangle",
        )

        self.background_plane = Entity(
            parent=self.background_root,
            model=background_mesh,
            position=(0, 0, 5),
            double_sided=True,
            unlit=True,
        )

    def _create_stars(self):
        """Tạo các chấm sáng nhỏ trôi chậm phía sau bàn."""

        for _ in range(40):
            star = Entity(
                parent=self.background_root,
                model="quad",
                double_sided=True,
                unlit=True,
            )

            self.stars.append({
                "entity": star,
                "x": self.rng.uniform(-.5, .5),
                "y": self.rng.uniform(-.5, .5),
                "size": self.rng.uniform(.0015, .0028),
                "speed": self.rng.uniform(.003, .010),
                "phase": self.rng.uniform(0, 2 * pi),
            })

    def _create_floating_cubes(self):
        """Tạo một số khối trang trí ở hai bên màn hình."""

        positions = [
            (-.40, .22),
            (-.35, -.16),
            (-.24, .34),
            (.39, .18),
            (.34, -.15),
            (.22, .32),
        ]

        palette = [
            color.rgb32(66, 57, 103),
            color.rgb32(40, 78, 95),
            color.rgb32(75, 63, 115),
        ]

        for index, (x, y) in enumerate(positions):
            cube = Entity(
                parent=self.background_root,
                model="cube",
                texture="white_cube",
                color=palette[index % len(palette)],
                rotation=(
                    self.rng.uniform(0, 90),
                    self.rng.uniform(0, 90),
                    self.rng.uniform(0, 90),
                ),
            )

            self.floating_cubes.append({
                "entity": cube,
                "x": x,
                "y": y,
                "size": self.rng.uniform(.022, .038),
                "speed": self.rng.uniform(5, 11),
                "phase": self.rng.uniform(0, 2 * pi),
            })

    def _update_background(self, dt):
        """Cập nhật vị trí, kích thước và ánh sáng trang trí."""

        height = float(camera.fov)
        width = height * float(window.aspect_ratio)

        # Phủ kín vùng nhìn của camera trực giao.
        self.background_plane.scale = (
            width * 1.1,
            height * 1.1,
            1,
        )

        for data in self.stars:
            star = data["entity"]

            # Khi vượt mép trên, hạt xuất hiện lại ở mép dưới.
            y = (
                (
                    data["y"]
                    + self.elapsed * data["speed"]
                    + .5
                ) % 1.0
            ) - .5

            x = (
                data["x"]
                + .006 * sin(
                    self.elapsed * .25 + data["phase"]
                )
            )

            star.position = (
                x * width,
                y * height,
                0,
            )

            size = height * data["size"]
            star.scale = (size, size, 1)

            brightness = int(
                115
                + 55 * sin(
                    self.elapsed * 1.2 + data["phase"]
                )
            )

            star.color = color.rgba32(
                176,
                201,
                255,
                brightness,
            )

        for data in self.floating_cubes:
            cube = data["entity"]

            cube.position = (
                (
                    data["x"]
                    + .008 * cos(
                        self.elapsed * .3 + data["phase"]
                    )
                ) * width,
                (
                    data["y"]
                    + .018 * sin(
                        self.elapsed * .45 + data["phase"]
                    )
                ) * height,
                -2,
            )

            cube.scale = height * data["size"]

            cube.rotation_x += dt * data["speed"]
            cube.rotation_y += dt * data["speed"] * .7

    def celebrate(self):
        """Phát một đợt hạt màu từ ô đích khi thắng."""

        if self.closed:
            return

        self.clear_celebration()

        goal_row, goal_col = self.game.level.board.find_goal()

        origin = Vec3(
            goal_col,
            .65,
            -goal_row,
        )

        palette = [
            (255, 190, 90),
            (139, 116, 255),
            (92, 232, 182),
            (235, 242, 255),
        ]

        for index in range(28):
            angle = self.rng.uniform(0, 2 * pi)
            speed = self.rng.uniform(1.0, 2.7)

            rgb = palette[index % len(palette)]

            particle = Entity(
                parent=self.effects_root,
                model="cube",
                position=origin,
                scale=self.rng.uniform(.05, .10),
                color=color.rgb32(*rgb),
            )

            self.win_particles.append({
                "entity": particle,
                "velocity": Vec3(
                    cos(angle) * speed,
                    self.rng.uniform(2.5, 4.5),
                    sin(angle) * speed,
                ),
                "age": 0.0,
                "life": self.rng.uniform(1.0, 1.7),
                "rgb": rgb,
            })

    def _update_celebration(self, dt):
        """Cập nhật chuyển động và làm mờ hạt chiến thắng."""

        remaining = []

        for data in self.win_particles:
            data["age"] += dt

            particle = data["entity"]

            if data["age"] >= data["life"]:
                destroy(particle)
                continue

            data["velocity"] += Vec3(0, -4.5 * dt, 0)

            particle.position += data["velocity"] * dt

            particle.rotation_x += 130 * dt
            particle.rotation_z += 95 * dt

            alpha = int(
                255 * (
                    1 - data["age"] / data["life"]
                )
            )

            red, green, blue = data["rgb"]

            particle.color = color.rgba32(
                red,
                green,
                blue,
                alpha,
            )

            remaining.append(data)

        self.win_particles = remaining

    def clear_celebration(self):
        """Dọn hạt khi Restart hoặc bắt đầu hiệu ứng mới."""

        for data in self.win_particles:
            destroy(data["entity"])

        self.win_particles.clear()

    def update(self):
        """Ursina tự gọi mỗi frame."""

        if self.closed or self.game.closed:
            return

        if self.game.statistics.visible:
            return

        dt = min(time.dt, .05)

        self.elapsed += dt

        self._update_background(dt)
        self._update_celebration(dt)

    def cleanup(self):
        """Dọn nền gắn camera và các hạt khi rời màn."""

        if self.closed:
            return

        self.closed = True

        self.clear_celebration()

        # background_root nằm dưới camera,
        # nên phải xóa riêng khi rời màn chơi.
        destroy(self.background_root)

        # effects_root là con của self, được xóa theo.
        destroy(self)

        self.stars.clear()
        self.floating_cubes.clear()

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
        self.pending_switches = set()

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

        self.atmosphere = LevelAtmosphere(self)

        self._setup_lighting()
        
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
            max(board.width, board.height) * 1.20 + 2
        )

    def _setup_lighting(self) -> None:
        """Tạo ánh sáng xiên và vùng tính bóng cho bàn chơi."""

        board = self.level.board

        self.sun = DirectionalLight(
            parent=self,
            shadows=True,
            shadow_map_resolution=(2048, 2048),
            color=color.rgb32(255, 244, 228),
        )

        # Ánh sáng chiếu xiên từ trên xuống.
        self.sun.look_at(
            Vec3(1, -2, -1)
        )

        # Hộp vô hình giới hạn vùng tính bóng.
        # Bao phủ toàn bộ bàn và khoảng không để khối lăn.
        self.shadow_bounds = Entity(
            parent=self,
            model="cube",
            position=(
                (board.width - 1) / 2,
                1,
                -(board.height - 1) / 2,
            ),
            scale=(
                board.width + 6,
                12,
                board.height + 6,
            ),
            visible=False,
        )

        self.shadow_bounds.hide(0b0001)

        self.sun.update_bounds(self.shadow_bounds)

    def _cleanup_lighting(self) -> None:
        """Gỡ nguồn sáng khỏi render trước khi xóa màn chơi."""

        sun = getattr(self, "sun", None)

        if sun is not None:
            # Node ánh sáng Panda3D nằm bên trong Entity của Ursina.
            light_node = sun.find("**/+DirectionalLight")

            if not light_node.is_empty():
                application.base.render.clear_light(light_node)

            # Tắt bộ tạo bóng trước khi giải phóng đối tượng.
            sun.shadows = False

            destroy(sun)
            self.sun = None

        bounds = getattr(self, "shadow_bounds", None)

        if bounds is not None:
            destroy(bounds)
            self.shadow_bounds = None

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
            y=-.405,
            width=1.74,
            height=.23,
        )

        for index, name in enumerate(SOLVERS):
            solver_button = button(
                parent=self.ui,
                text=name,
                x=-.70 + index * .205,
                y=-.375,
                action=lambda n=name: self.solve(n),
                width=.18,
                tint=ACCENT,
            )
           

        button(
            parent=self.ui,
            text="STOP",
            x=.15,
            y=-.375,
            action=self.stop,
            width=.17,
        )

        button(
            parent=self.ui,
            text="RESTART",
            x=.36,
            y=-.375,
            action=self.restart,
            width=.21,
        )

        button(
            parent=self.ui,
            text="RESULTS",
            x=.65,
            y=-.375,
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
            y=-.415,
            size=.65,
            tint=MUTED,
        )

        label(
            parent=self.ui,
            text=(
                "Mint: goal   Coral: fragile   "
                "Purple: soft   Pink: heavy   Blue: split"
            ),
            x=-.80,
            y=-.45,
            size=.62,
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
        """Áp dụng luật và chuẩn bị hiệu ứng cho nước đi."""

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

        # Những công tắc đang được nhấn trước nước đi.
        previously_pressed = set(
            get_activated_switches(
                self.level.board,
                self.state,
            )
        )

        # Những công tắc được nhấn sau nước đi.
        currently_pressed = set(
            get_activated_switches(
                self.level.board,
                next_state,
            )
        )

        # Chỉ lóe khi vừa kích hoạt, không lóe liên tục
        # trong lúc vẫn đang đè lên cùng công tắc.
        self.pending_switches = (
            currently_pressed - previously_pressed
        )

        # Xử lý thêm công tắc tách khối.
        if (
            not self.state.is_split
            and next_state.is_split
        ):
            moved_block = calculate_moved_block(
                self.state.block,
                move,
            )

            if (
                moved_block.orientation == Orientation.STANDING
                and self.level.board.get_tile(
                    moved_block.row,
                    moved_block.col,
                ) == TileType.SPLIT_SWITCH
            ):
                self.pending_switches.add(
                    (
                        moved_block.row,
                        moved_block.col,
                    )
                )

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

        self.board.update_effects(dt)

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
        """Cập nhật trạng thái sau khi animation hoàn tất."""

        self.state = self.pending_state
        self.pending_state = None

        self.move_count += 1

        self.board.sync_bridge_states(
            self.state.bridge_states
        )

        for row, col in self.pending_switches:
            self.board.flash_switch(row, col)

        self.pending_switches.clear()

        self.has_won = is_goal_state(
            self.level.board,
            self.state,
        )

        self.mode = "play"
        self.is_busy = False

        if self.has_won:
            if self.replay is not None:
                self.replay.stop()

            self.atmosphere.celebrate()

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
        self.atmosphere.clear_celebration()

        self.state = self.level.initial_state
        self.pending_state = None

        self.pending_switches.clear()
        self.board.reset_effects()

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

        self.atmosphere.cleanup()

        self.statistics.destroy()
        self.board.destroy()
        self.block.destroy()

        self._cleanup_lighting()

        destroy(self.ui)
        destroy(self)
