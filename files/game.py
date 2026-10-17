"""
game.py - Bloxorz game logic (no GUI, no search).

STATE
    state = (cells, bridges)
      cells   : tuple of 2 cells, SORTED, each cell is (row, col)
                  ((5,5),(5,5))  -> standing
                  ((5,5),(5,6))  -> lying horizontally
                  ((5,5),(6,5))  -> lying vertically
                  any 2 non-adjacent cells -> block is SPLIT into two 1x1x1 cubes
      bridges : int bitmask, bit k = 1 means bridge k is open

    Orientation is not stored: it is derived from the 2 cells (see `orientation`).
    Everything in `state` is hashable, so it can go straight into a set / dict.

ACTION
    action = (direction, cube_cell)
      direction : 'U' | 'D' | 'L' | 'R'
      cube_cell : None for a normal block; for a split block, the cell of the
                  cube that is being moved (so that a replay is unambiguous).

The only thing solvers need from this file:
    game.initial_state(), game.is_goal(state), game.successors(state)

ASSUMPTIONS (the assignment does not specify them - state them in your report)
    * A split cube is light: it may stand on a fragile tile safely.
    * A split cube may not move onto the cell of the other cube.
    * When a cube moves next to the other cube they merge into a lying block.
      Only the cube that moved can press a soft switch on that move.
    * Heavy / split switches fire only when the FULL block stands on them.
    * A move is illegal if, after switches fire, any part of the block is left
      over a void / closed bridge (e.g. a bridge closes under the other cube).
    * Rolling off the board, over void, or standing on a fragile tile = the
      block falls, so the move is simply not generated.
    * The goal state is terminal: no successors are generated from it.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Iterator, Optional

# --------------------------------------------------------------------------
# Constants
# --------------------------------------------------------------------------
DIRS = {"U": (-1, 0), "D": (1, 0), "L": (0, -1), "R": (0, 1)}

STAND, HORZ, VERT, SPLIT = "STAND", "HORZ", "VERT", "SPLIT"

# grid characters
VOID, FLOOR, FRAGILE, GOAL = ".", "#", "F", "G"

Cell = tuple
State = tuple


def make_cells(a: Cell, b: Cell) -> tuple:
    """Canonical (sorted) pair of cells."""
    return (a, b) if a <= b else (b, a)


def orientation(cells: tuple) -> str:
    a, b = cells
    if a == b:
        return STAND
    if a[0] == b[0] and abs(a[1] - b[1]) == 1:
        return HORZ
    if a[1] == b[1] and abs(a[0] - b[0]) == 1:
        return VERT
    return SPLIT


@dataclass(frozen=True)
class Switch:
    pos: Cell
    kind: str                      # 'soft' | 'heavy' | 'split'
    targets: tuple = ()            # bridge ids this switch affects
    mode: str = "toggle"           # 'toggle' | 'open' | 'close' (the last two = permanent)
    split_to: tuple = ()           # for kind == 'split': the two cells of the cubes


# --------------------------------------------------------------------------
# Game
# --------------------------------------------------------------------------
class Game:
    def __init__(self, grid, start, bridges=(), switches=()):
        self.grid = list(grid)
        self.rows = len(self.grid)
        self.cols = len(self.grid[0]) if self.rows else 0
        if any(len(row) != self.cols for row in self.grid):
            raise ValueError("all grid rows must have the same length")

        goals = [(r, c) for r in range(self.rows) for c in range(self.cols)
                 if self.grid[r][c] == GOAL]
        if len(goals) != 1:
            raise ValueError("grid must contain exactly one goal 'G'")
        self.goal = goals[0]
        self.start = tuple(start)

        # bridges: id = index in the list
        self.bridge_cells = {}     # cell -> bridge id
        self.bridge_initial = 0
        for bid, b in enumerate(bridges):
            for cell in b["cells"]:
                self.bridge_cells[tuple(cell)] = bid
            if b.get("open", False):
                self.bridge_initial |= 1 << bid
        self.n_bridges = len(bridges)

        # switches
        self.switches = {}
        for s in switches:
            sw = Switch(
                pos=tuple(s["pos"]),
                kind=s["type"],
                targets=tuple(s.get("targets", ())),
                mode=s.get("mode", "toggle"),
                split_to=tuple(tuple(x) for x in s.get("split_to", ())),
            )
            self.switches[sw.pos] = sw
        self._validate()

    # ---------------------------------------------------------------- loading
    @classmethod
    def from_dict(cls, d: dict) -> "Game":
        return cls(d["grid"], d["start"], d.get("bridges", ()), d.get("switches", ()))

    @classmethod
    def load(cls, path: str) -> "Game":
        with open(path, encoding="utf-8") as f:
            return cls.from_dict(json.load(f))

    def _validate(self):
        init = self.initial_state()
        if not self._valid(init[0], init[1]):
            raise ValueError("start cell is not a valid standing position")
        for pos, sw in self.switches.items():
            if sw.kind not in ("soft", "heavy", "split"):
                raise ValueError(f"unknown switch type {sw.kind!r}")
            if sw.mode not in ("toggle", "open", "close"):
                raise ValueError(f"unknown switch mode {sw.mode!r}")
            if not self._in_bounds(pos) or self.grid[pos[0]][pos[1]] == VOID \
                    or pos in self.bridge_cells:
                raise ValueError(f"switch at {pos} must be on a floor tile")
            for t in sw.targets:
                if not 0 <= t < self.n_bridges:
                    raise ValueError(f"switch at {pos} targets unknown bridge {t}")
            if sw.kind == "split":
                if len(sw.split_to) != 2 or orientation(make_cells(*sw.split_to)) != SPLIT:
                    raise ValueError("split_to needs 2 distinct, non-adjacent cells")

    # ------------------------------------------------------------ basic API
    def initial_state(self) -> State:
        return ((self.start, self.start), self.bridge_initial)

    def is_goal(self, state: State) -> bool:
        a, b = state[0]
        return a == b == self.goal

    def successors(self, state: State) -> Iterator[tuple]:
        """Yield (action, new_state, cost). Cost is 1 per move; UCS may redefine it."""
        if self.is_goal(state):
            return
        cells, mask = state
        if orientation(cells) == SPLIT:
            yield from self._split_moves(cells, mask)
        else:
            yield from self._block_moves(cells, mask)

    def step(self, state: State, action) -> Optional[State]:
        """Apply one action. Returns None if the move is illegal (block falls)."""
        for a, s, _ in self.successors(state):
            if a == action:
                return s
        return None

    # --------------------------------------------------------------- moves
    def _block_moves(self, cells, mask):
        orient = orientation(cells)
        for name, (dr, dc) in DIRS.items():
            new = self._roll(cells, orient, dr, dc)
            if not self._valid(new, mask):
                continue
            standing = new[0] == new[1]
            new_mask, split = self._trigger(set(new), standing, mask)
            if split:
                new = make_cells(*split)
            if not self._valid(new, new_mask):
                continue
            yield (name, None), (new, new_mask), 1

    def _split_moves(self, cells, mask):
        for i in (0, 1):
            cube, other = cells[i], cells[1 - i]
            for name, (dr, dc) in DIRS.items():
                new = (cube[0] + dr, cube[1] + dc)
                if new == other or not self._supports(new, mask, False):
                    continue
                new_mask, _ = self._trigger({new}, False, mask)
                new_cells = make_cells(new, other)     # adjacent => merged automatically
                if not self._valid(new_cells, new_mask):
                    continue
                yield (name, cube), (new_cells, new_mask), 1

    @staticmethod
    def _roll(cells, orient, dr, dc):
        """Cells of the block after rolling in direction (dr, dc) (not yet validated)."""
        a, b = cells
        if orient == STAND:
            r, c = a
            return make_cells((r + dr, c + dc), (r + 2 * dr, c + 2 * dc))
        axis = (b[0] - a[0], b[1] - a[1])              # (0,1) or (1,0) since cells are sorted
        if (dr, dc) == axis:                           # rolling along the body, forward end
            p = (b[0] + dr, b[1] + dc)
            return (p, p)
        if (dr, dc) == (-axis[0], -axis[1]):           # rolling along the body, backward end
            p = (a[0] + dr, a[1] + dc)
            return (p, p)
        return make_cells((a[0] + dr, a[1] + dc), (b[0] + dr, b[1] + dc))   # sideways

    # -------------------------------------------------- tiles / validity
    def _in_bounds(self, cell):
        return 0 <= cell[0] < self.rows and 0 <= cell[1] < self.cols

    def _supports(self, cell, mask, heavy) -> bool:
        """Can `cell` hold part of the block? heavy=True means the full block stands here."""
        if not self._in_bounds(cell):
            return False
        bid = self.bridge_cells.get(cell)
        if bid is not None:
            return bool(mask >> bid & 1)
        ch = self.grid[cell[0]][cell[1]]
        if ch == VOID:
            return False
        if ch == FRAGILE and heavy:
            return False
        return True

    def _valid(self, cells, mask) -> bool:
        heavy = cells[0] == cells[1]
        return all(self._supports(c, mask, heavy) for c in set(cells))

    # ----------------------------------------------------------- switches
    def _trigger(self, touched, full_standing, mask):
        """Fire switches under `touched` cells. Returns (new_mask, split_cells or None)."""
        split = None
        for cell in touched:
            sw = self.switches.get(cell)
            if sw is None:
                continue
            if sw.kind == "soft" or full_standing:     # heavy & split need the full block standing
                mask = self._apply(sw, mask)
                if sw.kind == "split":
                    split = sw.split_to
        return mask, split

    @staticmethod
    def _apply(sw: Switch, mask: int) -> int:
        for b in sw.targets:
            bit = 1 << b
            if sw.mode == "toggle":
                mask ^= bit
            elif sw.mode == "open":
                mask |= bit
            else:
                mask &= ~bit
        return mask

    # -------------------------------------------------------------- debug
    def to_text(self, state: State) -> str:
        """ASCII picture: B block, G goal, F fragile, # floor, = open bridge,
        : closed bridge, o soft / x heavy / p split switch, blank = void."""
        cells, mask = state
        sym = {"soft": "o", "heavy": "x", "split": "p"}
        lines = []
        for r in range(self.rows):
            row = ""
            for c in range(self.cols):
                cell = (r, c)
                if cell in cells:
                    row += "B"
                elif cell in self.bridge_cells:
                    row += "=" if mask >> self.bridge_cells[cell] & 1 else ":"
                elif cell in self.switches:
                    row += sym[self.switches[cell].kind]
                else:
                    ch = self.grid[r][c]
                    row += " " if ch == VOID else ch
            lines.append(row)
        return "\n".join(lines)


if __name__ == "__main__":
    import sys
    g = Game.load(sys.argv[1] if len(sys.argv) > 1 else "levels/level1.json")
    s = g.initial_state()
    print(g.to_text(s))
    print("moves from start:", [a for a, _, _ in g.successors(s)])
