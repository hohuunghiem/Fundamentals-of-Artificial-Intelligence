"""Run with:  python -m unittest test_gui_common -v   (no GUI library needed)"""
import unittest

from gui_common import SOLVER_NAMES, Session
from solvers import bfs


def play_path(session, path):
    """Play a solver path by hand through Session.move (selecting the cube when split)."""
    for direction, cube in path:
        if cube is not None:
            session.active = cube
        session.move(direction)


class SessionTests(unittest.TestCase):
    def test_manual_play_wins_every_level(self):
        for i in range(len(Session().paths)):
            s = Session()
            s.load(i)
            play_path(s, bfs(s.game).path)
            self.assertEqual(s.status, "won", s.level_name)
            self.assertEqual(s.moves, bfs(s.game).length)

    def test_fall_then_restart(self):
        s = Session()
        s.load(0)                          # level 1: start (1,1)
        s.move("U")
        s.move("U")                        # standing -> vertical at row -1 ... off the board
        self.assertEqual(s.status, "fell")
        before = s.state
        s.move("R")                        # ignored after a fall
        self.assertEqual(s.state, before)
        s.restart()
        self.assertEqual((s.status, s.moves), ("playing", 0))

    def test_split_control(self):
        s = Session()
        s.load(2)                          # level 3: split switch at (0,3)
        for d in "RR":
            s.move(d)
        self.assertTrue(s.is_split)
        self.assertEqual(s.state[0], ((2, 5), (2, 7)))
        first = s.active
        s.toggle_active()
        self.assertNotEqual(s.active, first)
        moved = s.active
        s.move("U")                        # moves only the active cube
        self.assertIn((moved[0] - 1, moved[1]), s.state[0])
        self.assertIn(first, s.state[0])
        self.assertEqual(s.active, (moved[0] - 1, moved[1]))   # control follows the cube

    def test_bridge_display(self):
        s = Session()
        s.load(1)                          # level 2
        self.assertEqual(s.cell_info(1, 4).tile, "bridge_closed")
        s.move("R")                        # lies across the soft switch at (0,2)
        self.assertEqual(s.cell_info(1, 4).tile, "bridge_open")
        self.assertIsNotNone(s.cell_info(0, 2).switch)

    def test_every_solver_replays_to_a_win(self):
        for i in range(len(Session().paths)):
            for name in SOLVER_NAMES:
                s = Session()
                s.load(i)
                res = s.solve(name)
                self.assertTrue(res.found)
                self.assertTrue(s.replaying)
                n = 0
                while s.replay_step():
                    n += 1
                self.assertEqual(s.status, "won", f"{name} on level {i + 1}")
                self.assertEqual(s.moves, res.length)

    def test_solve_from_midgame_and_after_fall(self):
        s = Session()
        s.load(0)
        s.move("R")
        s.solve("A*")
        while s.replay_step():
            pass
        self.assertEqual(s.status, "won")
        s.restart()
        s.move("U"); s.move("U")
        self.assertEqual(s.status, "fell")
        s.solve("BFS")                     # restarts first, then solves
        self.assertEqual((s.status, s.moves), ("playing", 0))
        self.assertTrue(s.replaying)

    def test_stop_and_block_manual_moves_during_replay(self):
        s = Session()
        s.solve("BFS")
        s.replay_step()
        state = s.state
        s.move("D")                        # ignored while replaying
        self.assertEqual(s.state, state)
        s.stop_replay()
        self.assertFalse(s.replaying)

    def test_new_game_cycles(self):
        s = Session()
        n = len(s.paths)
        for _ in range(n):
            s.next_level()
        self.assertEqual(s.index, 0)


if __name__ == "__main__":
    unittest.main()
