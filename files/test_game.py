"""Run with:  python -m unittest test_game -v"""
import glob
import os
import unittest
from collections import deque

from game import Game, orientation, STAND, HORZ, VERT, SPLIT

HERE = os.path.dirname(os.path.abspath(__file__))


def open_board(n=11):
    """n x n board of floor, goal far in the corner."""
    grid = ["#" * n for _ in range(n)]
    grid[n - 1] = "#" * (n - 1) + "G"
    return Game.from_dict({"grid": grid, "start": [0, 0]})


def S(r, c, mask=0):
    return (((r, c), (r, c)), mask)


def H(r, c, mask=0):
    return (((r, c), (r, c + 1)), mask)


def V(r, c, mask=0):
    return (((r, c), (r + 1, c)), mask)


def moves(game, state):
    return {a[0] if a[1] is None else a: s for a, s, _ in game.successors(state)}


def bfs_solve(game):
    start = game.initial_state()
    parent = {start: None}
    q = deque([start])
    while q:
        s = q.popleft()
        if game.is_goal(s):
            n = 0
            while parent[s] is not None:
                s, n = parent[s], n + 1
            return n
        for _, ns, _ in game.successors(s):
            if ns not in parent:
                parent[ns] = s
                q.append(ns)
    return None


def to_cells(o, r, c):
    return {STAND: ((r, c), (r, c)), HORZ: ((r, c), (r, c + 1)), VERT: ((r, c), (r + 1, c))}[o]


class TransitionTable(unittest.TestCase):
    """The (orientation, direction) -> (orientation, anchor) table from the notes."""
    TABLE = {
        (STAND, "U"): (VERT, -2, 0), (STAND, "D"): (VERT, 1, 0),
        (STAND, "L"): (HORZ, 0, -2), (STAND, "R"): (HORZ, 0, 1),
        (HORZ, "U"): (HORZ, -1, 0), (HORZ, "D"): (HORZ, 1, 0),
        (HORZ, "L"): (STAND, 0, -1), (HORZ, "R"): (STAND, 0, 2),
        (VERT, "U"): (STAND, -1, 0), (VERT, "D"): (STAND, 2, 0),
        (VERT, "L"): (VERT, 0, -1), (VERT, "R"): (VERT, 0, 1),
    }

    def test_table(self):
        g = open_board()
        for (o, d), (no, dr, dc) in self.TABLE.items():
            start = (to_cells(o, 5, 5), 0)
            got = moves(g, start)[d]
            self.assertEqual(got[0], to_cells(no, 5 + dr, 5 + dc), f"{o} {d}")
            self.assertEqual(orientation(got[0]), no)

    def test_roll_and_back(self):
        g = open_board()
        opposite = {"U": "D", "D": "U", "L": "R", "R": "L"}
        for start in (S(5, 5), H(5, 5), V(5, 5)):
            for d in "UDLR":
                mid = moves(g, start)[d]
                self.assertEqual(moves(g, mid)[opposite[d]], start, f"{start} {d}")


class Legality(unittest.TestCase):
    def test_out_of_board_and_void(self):
        g = Game.from_dict({"grid": ["###", "#.#", "##G"], "start": [0, 0]})
        # standing (0,0): Right -> HORZ (0,1),(0,2) ok; Down -> VERT (1,0),(2,0) ok
        m = moves(g, S(0, 0))
        self.assertIn("R", m)
        self.assertIn("D", m)
        self.assertNotIn("U", m)
        self.assertNotIn("L", m)
        # HORZ (0,1),(0,2) rolling Down would cover (1,1) = void and (1,2)
        self.assertNotIn("D", moves(g, H(0, 1)))

    def test_fragile(self):
        g = Game.from_dict({"grid": ["#F###", "#F##G"], "start": [0, 0]})
        # standing -> lying across (0,1)? HORZ (0,1),(0,2) lies on fragile: allowed
        self.assertIn("R", moves(g, S(0, 0)))
        # VERT (0,1),(1,1) both fragile but lying: allowed; standing on (0,1) not allowed
        g2 = Game.from_dict({"grid": ["##F#", "#..G"], "start": [0, 0]})
        # HORZ (0,0),(0,1) rolling Right stands on (0,2) = fragile -> illegal
        self.assertNotIn("R", moves(g2, H(0, 0)))

    def test_goal_requires_standing(self):
        g = Game.from_dict({"grid": ["#####", "###G#"], "start": [0, 0]})
        self.assertTrue(g.is_goal(S(1, 3)))
        self.assertFalse(g.is_goal(H(1, 3)))
        self.assertFalse(g.is_goal(H(1, 2)))
        self.assertFalse(g.is_goal(V(0, 3)))
        self.assertEqual(list(g.successors(S(1, 3))), [])     # terminal


class Switches(unittest.TestCase):
    def level(self, kind, mode="toggle"):
        return Game.from_dict({
            "grid": ["######", "######", "#####G"],
            "start": [0, 0],
            "bridges": [{"cells": [[2, 4]], "open": False}],
            "switches": [{"pos": [0, 2], "type": kind, "targets": [0], "mode": mode}],
        })

    def test_soft_lying_triggers(self):
        g = self.level("soft")
        # standing (0,0), Right -> HORZ (0,1),(0,2): touches soft switch
        self.assertEqual(moves(g, S(0, 0))["R"][1], 1)

    def test_heavy_needs_standing(self):
        g = self.level("heavy")
        # standing (0,0) rolling Right lies across (0,1),(0,2): on the switch but lying
        self.assertEqual(moves(g, S(0, 0))["R"][1], 0)
        # HORZ (0,0),(0,1) rolling Right stands on (0,2): standing on the switch
        self.assertEqual(moves(g, H(0, 0))["R"][1], 1)

    def test_toggle_vs_permanent(self):
        g = self.level("soft", "toggle")
        on = moves(g, S(0, 0))["R"]                 # touches switch -> bridge open
        self.assertEqual(on[1], 1)
        away = moves(g, on)["L"]                    # roll off the switch (bridge stays open)
        self.assertEqual(away[1], 1)
        off = moves(g, away)["R"]                   # touch it again -> toggled back
        self.assertEqual(off[1], 0)
        gp = self.level("soft", "open")             # permanent
        on = moves(gp, S(0, 0))["R"]
        again = moves(gp, moves(gp, on)["L"])["R"]  # touch it a second time
        self.assertEqual(again[1], 1)               # stays open

    def test_closed_bridge_blocks(self):
        g = Game.from_dict({
            "grid": ["#####", "##..G"], "start": [0, 0],
            "bridges": [{"cells": [[1, 2], [1, 3]], "open": False}],
        })
        # HORZ (0,2),(0,3) rolling Down covers the closed bridge cells -> illegal
        self.assertNotIn("D", moves(g, H(0, 2)))
        self.assertIn("D", moves(g, H(0, 2, 1)))     # same move with the bridge open


class Splitting(unittest.TestCase):
    def setUp(self):
        self.g = Game.from_dict({
            "grid": ["########", "########", "########", "#######G"],
            "start": [0, 0],
            "bridges": [{"cells": [[3, 0]], "open": False}],
            "switches": [
                {"pos": [0, 2], "type": "split", "split_to": [[2, 4], [2, 6]]},
                {"pos": [2, 5], "type": "soft", "targets": [0], "mode": "open"},
                {"pos": [2, 6 - 3], "type": "heavy", "targets": [0], "mode": "open"},
            ],
        })

    def test_split_teleports(self):
        after = moves(self.g, H(0, 0))["R"]                    # stands on (0,2)
        self.assertEqual(after[0], ((2, 4), (2, 6)))
        self.assertEqual(orientation(after[0]), SPLIT)

    def test_cube_moves_and_soft_switch(self):
        state = ((( 2, 4), (2, 6)), 0)
        res = moves(self.g, state)
        self.assertEqual(len(res), 8)                          # 2 cubes x 4 dirs
        got = res[("R", (2, 4))]                               # cube (2,4) -> (2,5): soft switch
        self.assertEqual(got[1], 1)
        self.assertEqual(got[0], ((2, 5), (2, 6)))             # adjacent -> merged (HORZ)
        self.assertEqual(orientation(got[0]), HORZ)

    def test_cube_cannot_fire_heavy(self):
        state = (((2, 2), (2, 6)), 0)                          # cube at (2,2), heavy at (2,3)
        got = moves(self.g, state)[("R", (2, 2))]
        self.assertEqual(got[1], 0)

    def test_cube_cannot_win(self):
        g = Game.from_dict({"grid": ["###", "#.G"], "start": [0, 0]})
        self.assertFalse(g.is_goal((((0, 0), (1, 2)), 0)))   # a cube on the goal is not a win

    def test_cube_cannot_overlap(self):
        # cubes at (2,4) and (2,6); after (2,4)->(2,5) they merge, never share a cell
        for _, (cells, _m), in [(a, s) for a, s, _ in self.g.successors((((2, 4), (2, 6)), 0))]:
            self.assertNotEqual(cells[0], cells[1])


class Levels(unittest.TestCase):
    def test_all_levels_load_and_are_solvable(self):
        files = sorted(glob.glob(os.path.join(HERE, "levels", "*.json")))
        self.assertTrue(files)
        for f in files:
            g = Game.load(f)
            n = bfs_solve(g)
            self.assertIsNotNone(n, f"{os.path.basename(f)} has no solution")
            print(f"  {os.path.basename(f)}: shortest solution = {n} moves")


if __name__ == "__main__":
    unittest.main()
