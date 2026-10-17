"""Run with:  python -m unittest test_solvers -v"""
import glob
import os
import unittest
from collections import deque

from game import Game
from solvers import SOLVERS, bfs, dfs, ids, ucs, astar, make_heuristic, move_cost

HERE = os.path.dirname(os.path.abspath(__file__))
LEVELS = sorted(glob.glob(os.path.join(HERE, "levels", "*.json")))


def all_reachable(game):
    start = game.initial_state()
    seen = {start}
    q = deque([start])
    while q:
        s = q.popleft()
        for _, ns, _ in game.successors(s):
            if ns not in seen:
                seen.add(ns)
                q.append(ns)
    return seen


def replay(game, path):
    s = game.initial_state()
    for action in path:
        s = game.step(s, action)
        if s is None:
            return None
    return s


class SolverTests(unittest.TestCase):
    def test_solutions_are_valid(self):
        """Every solver's path must really reach the goal when replayed."""
        for f in LEVELS:
            g = Game.load(f)
            for name, fn in SOLVERS.items():
                r = fn(g)
                self.assertTrue(r.found, f"{name} failed on {os.path.basename(f)}")
                end = replay(g, r.path)
                self.assertIsNotNone(end, f"{name}: illegal move in path ({os.path.basename(f)})")
                self.assertTrue(g.is_goal(end), f"{name}: path does not reach goal")

    def test_move_optimality(self):
        """BFS and IDS give the minimum number of moves."""
        for f in LEVELS:
            g = Game.load(f)
            self.assertEqual(ids(g).length, bfs(g).length, os.path.basename(f))
            self.assertGreaterEqual(dfs(g).length, bfs(g).length)

    def test_cost_optimality(self):
        """UCS and A* give the same minimal cost, never worse than BFS's path."""
        for f in LEVELS:
            g = Game.load(f)
            u, a, b = ucs(g), astar(g), bfs(g)
            self.assertEqual(u.cost, a.cost, os.path.basename(f))
            self.assertLessEqual(u.cost, b.cost)

    def test_astar_expands_no_more_than_ucs(self):
        for f in LEVELS:
            g = Game.load(f)
            self.assertLessEqual(astar(g).expanded, ucs(g).expanded, os.path.basename(f))

    def test_unsolvable(self):
        g = Game.from_dict({"grid": ["##.", "..G"], "start": [0, 0]})
        for name, fn in SOLVERS.items():
            self.assertFalse(fn(g).found, name)


class HeuristicTests(unittest.TestCase):
    def test_admissible(self):
        """h(s) <= true optimal remaining cost, for every reachable state."""
        for f in LEVELS:
            g = Game.load(f)
            h = make_heuristic(g)
            for s in all_reachable(g):
                r = ucs(g, start=s)
                if r.found:
                    self.assertLessEqual(h(s), r.cost, f"{os.path.basename(f)} state {s}")

    def test_goal_has_zero_h(self):
        for f in LEVELS:
            g = Game.load(f)
            h = make_heuristic(g)
            for s in all_reachable(g):
                if g.is_goal(s):
                    self.assertEqual(h(s), 0)

    def test_consistent_without_split_switch(self):
        """h(n) <= cost(n,n') + h(n') on every edge (levels without teleports)."""
        checked = 0
        for f in LEVELS:
            g = Game.load(f)
            if any(sw.kind == "split" for sw in g.switches.values()):
                continue
            h = make_heuristic(g)
            for s in all_reachable(g):
                for _, ns, _ in g.successors(s):
                    self.assertLessEqual(h(s), move_cost(g, ns) + h(ns))
            checked += 1
        self.assertGreater(checked, 0)


if __name__ == "__main__":
    unittest.main()
