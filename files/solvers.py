"""
solvers.py - BFS, DFS, IDS, UCS, A* for Bloxorz.

Solvers only use three things from the game:
    game.initial_state(), game.is_goal(state), game.successors(state)

Every solver has the signature  solver(game, start=None, ...) -> SearchResult
Use `measure(solver, game)` to also record search time and peak memory.

A search node is a tuple (state, action, parent_node); the path is rebuilt by
following parent pointers.  "Expanded nodes" = number of states whose
successors were generated.

COST FUNCTION (used by UCS and A*)
    cost of a move = 1
                   + 2 if, after the move, the full block (not split cubes)
                     lies on a fragile tile  (risky: one wrong roll breaks it)
    so every move costs >= 1, a move onto fragile costs 3.
    BFS / DFS / IDS ignore costs (they work on the number of moves).

HEURISTIC (A*)  - see `make_heuristic`.  Lower bound on the number of moves,
    and since every move costs >= 1, also a lower bound on the cost.
"""
from __future__ import annotations

import heapq
import itertools
import time
import tracemalloc
from collections import deque
from dataclasses import dataclass, field

from game import FRAGILE, SPLIT, STAND, orientation


# --------------------------------------------------------------------------
# Result container
# --------------------------------------------------------------------------
@dataclass
class SearchResult:
    found: bool
    path: list = field(default_factory=list)   # list of actions
    cost: float = 0                            # total cost under move_cost
    length: int = 0                            # number of moves
    expanded: int = 0
    time: float = 0.0                          # seconds (filled by measure)
    memory_mb: float = 0.0                     # peak MB (filled by measure)


# --------------------------------------------------------------------------
# Cost function
# --------------------------------------------------------------------------
FRAGILE_PENALTY = 2


def move_cost(game, new_state) -> int:
    cells = new_state[0]
    if orientation(cells) != SPLIT:
        for (r, c) in set(cells):
            if (r, c) not in game.bridge_cells and game.grid[r][c] == FRAGILE:
                return 1 + FRAGILE_PENALTY
    return 1


# --------------------------------------------------------------------------
# Heuristic
# --------------------------------------------------------------------------
def make_heuristic(game):
    """
    m = min Manhattan distance from any block cell to the goal.
    One move changes m by at most 2 (standing -> lying toward the goal), so:
        standing : h = ceil(m / 2)
        lying    : h = max(1, ceil(m / 2))     (needs >= 1 roll to stand up)
        split    : h = max(2, ceil(m / 2))     (>= 1 merge move + >= 1 final roll)
    Splitting switches TELEPORT the block, which breaks the "<= 2 per move" argument,
    so when the level has one we also take a minimum with the teleport route:
        normal : ceil(ms / 2) + 2     (ms = distance to nearest split switch;
                                       after the teleport: merge + final roll)
        split  : 3
    Voids, fragile tiles, bridges and costs > 1 are ignored (only makes h smaller).
    """
    goal = game.goal
    splits = [p for p, sw in game.switches.items() if sw.kind == "split"]

    def dist(a, b):
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    def h(state):
        cells = state[0]
        o = orientation(cells)
        half = (min(dist(c, goal) for c in cells) + 1) // 2
        if o == STAND:
            base = half
        elif o == SPLIT:
            base = max(2, half)
        else:
            base = max(1, half)
        if splits:
            if o == SPLIT:
                tele = 3
            else:
                tele = (min(dist(c, p) for c in set(cells) for p in splits) + 1) // 2 + 2
            return min(base, tele)
        return base

    return h


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def _finish(game, node, expanded, cost_fn):
    path, cost = [], 0
    while node[2] is not None:
        path.append(node[1])
        cost += cost_fn(game, node[0])
        node = node[2]
    path.reverse()
    return SearchResult(True, path, cost, len(path), expanded)


def _fail(expanded):
    return SearchResult(False, expanded=expanded)


# --------------------------------------------------------------------------
# BFS
# --------------------------------------------------------------------------
def bfs(game, start=None, cost_fn=move_cost) -> SearchResult:
    start = start or game.initial_state()
    root = (start, None, None)
    if game.is_goal(start):
        return _finish(game, root, 0, cost_fn)
    visited = {start}
    queue = deque([root])
    expanded = 0
    while queue:
        node = queue.popleft()
        expanded += 1
        for action, ns, _ in game.successors(node[0]):
            if ns in visited:
                continue
            visited.add(ns)
            child = (ns, action, node)
            if game.is_goal(ns):                       # goal test when generated
                return _finish(game, child, expanded, cost_fn)
            queue.append(child)
    return _fail(expanded)


# --------------------------------------------------------------------------
# DFS (graph search with a visited set)
# --------------------------------------------------------------------------
def dfs(game, start=None, cost_fn=move_cost) -> SearchResult:
    start = start or game.initial_state()
    visited = {start}
    stack = [(start, None, None)]
    expanded = 0
    while stack:
        node = stack.pop()
        if game.is_goal(node[0]):
            return _finish(game, node, expanded, cost_fn)
        expanded += 1
        for action, ns, _ in reversed(list(game.successors(node[0]))):
            if ns not in visited:                      # avoids cycles
                visited.add(ns)
                stack.append((ns, action, node))
    return _fail(expanded)


# --------------------------------------------------------------------------
# IDS (iterative deepening; optimal in number of moves)
# --------------------------------------------------------------------------
def ids(game, start=None, cost_fn=move_cost, max_depth=500) -> SearchResult:
    start = start or game.initial_state()
    expanded = 0
    for limit in range(max_depth + 1):
        best = {start: 0}                              # shallowest depth seen in this round
        stack = [((start, None, None), 0)]
        cutoff = False
        while stack:
            node, d = stack.pop()
            if game.is_goal(node[0]):
                return _finish(game, node, expanded, cost_fn)
            expanded += 1
            for action, ns, _ in reversed(list(game.successors(node[0]))):
                if best.get(ns, float("inf")) <= d + 1:
                    continue
                if d == limit:
                    cutoff = True                      # something lies deeper than the limit
                    continue
                best[ns] = d + 1
                stack.append(((ns, action, node), d + 1))
        if not cutoff:
            break                                      # whole space explored, no solution
    return _fail(expanded)


# --------------------------------------------------------------------------
# UCS
# --------------------------------------------------------------------------
def ucs(game, start=None, cost_fn=move_cost) -> SearchResult:
    start = start or game.initial_state()
    tie = itertools.count()
    g_best = {start: 0}
    heap = [(0, next(tie), (start, None, None))]
    expanded = 0
    while heap:
        g, _, node = heapq.heappop(heap)
        state = node[0]
        if g > g_best[state]:
            continue                                   # stale queue entry
        if game.is_goal(state):
            return _finish(game, node, expanded, cost_fn)
        expanded += 1
        for action, ns, _ in game.successors(state):
            ng = g + cost_fn(game, ns)
            if ng < g_best.get(ns, float("inf")):
                g_best[ns] = ng
                heapq.heappush(heap, (ng, next(tie), (ns, action, node)))
    return _fail(expanded)


# --------------------------------------------------------------------------
# A*
# --------------------------------------------------------------------------
def astar(game, start=None, cost_fn=move_cost, heuristic=None) -> SearchResult:
    start = start or game.initial_state()
    h = heuristic or make_heuristic(game)
    tie = itertools.count()
    g_best = {start: 0}
    heap = [(h(start), next(tie), 0, (start, None, None))]
    expanded = 0
    while heap:
        _, _, g, node = heapq.heappop(heap)
        state = node[0]
        if g > g_best[state]:
            continue
        if game.is_goal(state):
            return _finish(game, node, expanded, cost_fn)
        expanded += 1
        for action, ns, _ in game.successors(state):
            ng = g + cost_fn(game, ns)
            # re-opening is allowed (strictly lower g), so A* stays optimal
            # even if the heuristic were admissible but not consistent
            if ng < g_best.get(ns, float("inf")):
                g_best[ns] = ng
                heapq.heappush(heap, (ng + h(ns), next(tie), ng, (ns, action, node)))
    return _fail(expanded)


SOLVERS = {"BFS": bfs, "DFS": dfs, "IDS": ids, "UCS": ucs, "A*": astar}


# --------------------------------------------------------------------------
# Measurement
# --------------------------------------------------------------------------
def measure(solver, game, **kwargs) -> SearchResult:
    """Run `solver` twice: once for the time, once under tracemalloc for peak memory
    (tracemalloc slows Python down, so the two are not measured together)."""
    t0 = time.perf_counter()
    result = solver(game, **kwargs)
    elapsed = time.perf_counter() - t0

    tracemalloc.start()
    solver(game, **kwargs)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    result.time = elapsed
    result.memory_mb = peak / (1024 * 1024)
    return result


if __name__ == "__main__":
    import sys
    from game import Game

    g = Game.load(sys.argv[1] if len(sys.argv) > 1 else "levels/level1.json")
    print(f"{'solver':6} {'found':5} {'moves':>5} {'cost':>5} {'expanded':>9} {'time(ms)':>9} {'mem(MB)':>8}")
    for name, fn in SOLVERS.items():
        r = measure(fn, g)
        print(f"{name:6} {str(r.found):5} {r.length:5} {r.cost:5} {r.expanded:9} "
              f"{r.time * 1000:9.2f} {r.memory_mb:8.3f}")
