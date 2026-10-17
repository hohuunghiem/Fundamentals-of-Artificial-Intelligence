"""
gui_common.py - everything the two GUIs share, with NO tkinter / pygame imports.

    Session   : one play session (current level, block state, split-cube control,
                win/lose status, solver run + step-by-step replay)
    cell_info : what to draw on a board cell
    COLORS ...: shared palette

Both gui_tkinter.py and gui_pygame.py only draw what Session tells them and
forward key presses / button clicks to it, so the game behaves identically in both.
"""
from __future__ import annotations

import glob
import json
import os
from collections import namedtuple

from game import DIRS, SPLIT, Game, orientation
from solvers import SOLVERS, measure

LEVEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "levels")
SOLVER_NAMES = list(SOLVERS)            # BFS, DFS, IDS, UCS, A*

COLORS = dict(
    bg="#1e2230", panel="#262b3d", text="#e8ebf5", muted="#9aa3bd",
    floor="#c9ced6", floor_edge="#8b929c",
    fragile="#f0a040", fragile_edge="#a8641c",
    hole="#0b0d14",
    block="#2f6fd6", block_edge="#14336b", block_top="#6a9bf0",
    block_fell="#d64545", block_won="#2fa84f", active="#ffd93d",
    split="#a66be0", switch_default="#444a5a",
)
BRIDGE_COLORS = ["#2bb3a3", "#e05a9c", "#8bc34a", "#5c8de0", "#d9b13a", "#b07cdc"]

KEY_TO_DIR = {"up": "U", "w": "U", "down": "D", "s": "D",
              "left": "L", "a": "L", "right": "R", "d": "R"}

HELP_TEXT = ("Arrows / WASD: roll\n"
             "Space: switch cube (when split)\n"
             "R: restart   N: next level")

CellInfo = namedtuple("CellInfo", "tile switch bridge")
# tile   : 'void' | 'floor' | 'fragile' | 'goal' | 'bridge_open' | 'bridge_closed'
# switch : game.Switch or None
# bridge : bridge id (for bridge tiles) or None


def bridge_color(bid: int) -> str:
    return BRIDGE_COLORS[bid % len(BRIDGE_COLORS)]


def switch_color(sw) -> str:
    if sw.targets:
        return bridge_color(sw.targets[0])
    return COLORS["split"] if sw.kind == "split" else COLORS["switch_default"]


def list_levels():
    return sorted(glob.glob(os.path.join(LEVEL_DIR, "*.json")))


class Session:
    def __init__(self, level_dir: str | None = None):
        self.paths = sorted(glob.glob(os.path.join(level_dir or LEVEL_DIR, "*.json")))
        if not self.paths:
            raise FileNotFoundError("no level files found in the levels/ folder")
        self.names = []
        for p in self.paths:
            with open(p, encoding="utf-8") as f:
                self.names.append(json.load(f).get("name", os.path.basename(p)))
        self.index = 0
        self.result_text = ""
        self.load(0)

    # -------------------------------------------------------------- levels
    def load(self, index: int):
        self.index = index % len(self.paths)
        self.game = Game.load(self.paths[self.index])
        self.result_text = ""
        self.restart()

    def next_level(self):
        self.load(self.index + 1)

    @property
    def level_name(self) -> str:
        return self.names[self.index]

    def restart(self):
        self.state = self.game.initial_state()
        self.active = None            # (r, c) of the cube under control when split
        self.moves = 0
        self.status = "playing"       # 'playing' | 'won' | 'fell'
        self.replay = []
        self.replay_pos = 0
        self.message = "Reach the goal hole standing upright."

    # --------------------------------------------------------- play by hand
    @property
    def is_split(self) -> bool:
        return orientation(self.state[0]) == SPLIT

    @property
    def replaying(self) -> bool:
        return self.replay_pos < len(self.replay)

    def move(self, direction: str):
        if self.replaying:
            self.message = "Replay running - press Stop first."
            return
        if self.status != "playing":
            return
        cells = self.state[0]
        cube = None
        if self.is_split:
            cube = self.active if self.active in cells else cells[0]
        action = (direction, cube)
        new = self.game.step(self.state, action)
        if new is None:
            self.status = "fell"
            self.message = "The block fell! Press Restart."
            return
        self._commit(action, new)

    def toggle_active(self):
        if not self.is_split or self.status != "playing":
            return
        cells = self.state[0]
        self.active = cells[1] if self.active == cells[0] else cells[0]

    def _commit(self, action, new):
        self.state = new
        cells = new[0]
        if orientation(cells) == SPLIT:
            if action[1] is not None:                      # a cube moved: follow it
                dr, dc = DIRS[action[0]]
                self.active = (action[1][0] + dr, action[1][1] + dc)
            else:                                          # just split: control the first cube
                self.active = cells[0]
        else:
            self.active = None                             # normal block, or cubes merged
        self.moves += 1
        if self.game.is_goal(new):
            self.status = "won"
            self.message = f"You win in {self.moves} moves!"
        elif self.status == "playing" and not self.replaying:
            self.message = ""

    # --------------------------------------------------------------- solver
    def solve(self, name: str):
        """Run solver `name` from the CURRENT position and prepare the replay."""
        self.stop_replay(silent=True)
        if self.status != "playing":
            self.restart()
        res = measure(SOLVERS[name], self.game, start=self.state)
        if not res.found:
            self.result_text = f"{name}: no solution from this position."
            self.message = self.result_text
            return res
        self.result_text = (f"{name}: {res.length} moves | cost {res.cost} | "
                            f"expanded {res.expanded} | {res.time * 1000:.1f} ms | "
                            f"{res.memory_mb:.3f} MB")
        self.replay = list(res.path)
        self.replay_pos = 0
        self.message = f"Replaying the {name} solution..."
        return res

    def replay_step(self) -> bool:
        """Apply the next solver move. Returns True while more moves remain."""
        if not self.replaying:
            return False
        action = self.replay[self.replay_pos]
        new = self.game.step(self.state, action)
        if new is None:                                    # should never happen
            self.stop_replay(silent=True)
            self.status = "fell"
            self.message = "Replay hit an illegal move."
            return False
        self.replay_pos += 1
        self._commit(action, new)
        return self.replaying

    def stop_replay(self, silent: bool = False):
        was = self.replaying
        self.replay = []
        self.replay_pos = 0
        if was and not silent:
            self.message = "Replay stopped."

    # -------------------------------------------------------------- drawing
    def cell_info(self, r: int, c: int) -> CellInfo:
        cell = (r, c)
        bid = self.game.bridge_cells.get(cell)
        if bid is not None:
            open_ = bool(self.state[1] >> bid & 1)
            return CellInfo("bridge_open" if open_ else "bridge_closed", None, bid)
        tile = {".": "void", "#": "floor", "F": "fragile", "G": "goal"}[self.game.grid[r][c]]
        return CellInfo(tile, self.game.switches.get(cell), None)

    def block_color(self) -> str:
        return {"fell": COLORS["block_fell"], "won": COLORS["block_won"]}.get(
            self.status, COLORS["block"])
