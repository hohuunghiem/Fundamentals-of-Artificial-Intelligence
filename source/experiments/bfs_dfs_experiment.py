"""Chạy thực nghiệm các thuật toán tìm kiếm trên toàn bộ level, xuất CSV và biểu đồ.

Chạy từ thư mục ``source``:

    python -m experiments.bfs_dfs_experiment
    python -m experiments.bfs_dfs_experiment --algos all --out experiments/results_all
    python -m experiments.bfs_dfs_experiment --runs 10 --out experiments/results

Thời gian được đo riêng (không bật tracemalloc) và lấy trung vị qua nhiều lần
chạy; bộ nhớ đỉnh đo bằng ``run_with_profiling`` dùng chung của nhóm.
"""
from __future__ import annotations

import argparse
import csv
import json
import statistics
from collections import Counter
from pathlib import Path
from time import perf_counter

from algorithms.astar import astar_search
from algorithms.bfs import bfs_search
from algorithms.dfs import dfs_search
from algorithms.ucs import ucs_search
from algorithms.profiler import run_with_profiling
from core.level_loader import load_level
from core.transition import apply_move, is_goal_state

SOURCE_DIR = Path(__file__).resolve().parents[1]
LEVELS_DIR = SOURCE_DIR / "levels"

ALL_ALGORITHMS = {
    "BFS": bfs_search,
    "DFS": dfs_search,
    "UCS": ucs_search,
    "A*": astar_search,
}

ALGORITHMS = {name: ALL_ALGORITHMS[name] for name in ("BFS", "DFS")}

COLORS = {
    "BFS": "#2a78d6",
    "DFS": "#eb6834",
    "UCS": "#1baf7a",
    "A*": "#eda100",
}

GROUP_ORDER = ["Cơ bản", "Fragile", "Switch", "Kết hợp"]

FRAGILE_CHARS = {"f"}
SWITCH_CHARS = {"s", "h", "p", "S", "b", "B"}


def _prefix() -> str:
    return "_".join(name.lower().replace("*", "star") for name in ALGORITHMS)


def level_number(path: Path) -> int:
    return int(path.stem.removeprefix("level"))


def classify(path: Path) -> str:
    data = json.loads(path.read_text(encoding="utf-8"))
    chars = Counter(ch for row in data["board"] for ch in row)
    has_fragile = any(chars[c] for c in FRAGILE_CHARS)
    has_switch = any(chars[c] for c in SWITCH_CHARS)
    if has_fragile and has_switch:
        return "Kết hợp"
    if has_fragile:
        return "Fragile"
    if has_switch:
        return "Switch"
    return "Cơ bản"


def verify(level, moves) -> bool:
    state = level.initial_state
    for move in moves:
        state = apply_move(level.board, state, move)
        if state is None:
            return False
    return is_goal_state(level.board, state)


def measure(name, search_fn, level, runs: int) -> dict:
    times = []
    for _ in range(runs):
        start = perf_counter()
        search_fn(level)
        times.append(perf_counter() - start)

    profiled = run_with_profiling(name, search_fn, level)
    return {
        "success": profiled.success,
        "valid": profiled.success and verify(level, profiled.moves),
        "time_ms": statistics.median(times) * 1000,
        "memory_kb": profiled.memory_usage * 1024,
        "expanded": profiled.expanded_nodes,
        "generated": profiled.generated_nodes,
        "length": profiled.solution_length,
    }


def run_all(runs: int) -> list[dict]:
    rows = []
    paths = sorted(LEVELS_DIR.glob("level*.json"), key=level_number)
    for path in paths:
        level = load_level(path)
        group = classify(path)
        for name, fn in ALGORITHMS.items():
            result = measure(name, fn, level, runs)
            rows.append({
                "level": level_number(path),
                "group": group,
                "algorithm": name,
                **result,
            })
            print(
                f"Level {level_number(path):>2} [{group:<8}] {name}: "
                f"len={result['length']:<5} expanded={result['expanded']:<6} "
                f"time={result['time_ms']:8.2f} ms  mem={result['memory_kb']:9.1f} KB"
                f"  {'OK' if result['valid'] else 'FAIL'}"
            )
    return rows


def write_csv(rows: list[dict], out_dir: Path) -> None:
    fields = [
        "level", "group", "algorithm", "success", "valid",
        "length", "expanded", "generated", "time_ms", "memory_kb",
    ]
    with open(out_dir / f"{_prefix()}_results.csv", "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({
                **{k: row[k] for k in fields},
                "time_ms": f"{row['time_ms']:.3f}",
                "memory_kb": f"{row['memory_kb']:.1f}",
            })

    summary_fields = ["group", "algorithm", "levels", "avg_length", "avg_expanded", "avg_time_ms", "avg_memory_kb"]
    with open(out_dir / f"{_prefix()}_summary.csv", "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=summary_fields)
        writer.writeheader()
        for group in GROUP_ORDER + ["Tất cả"]:
            for name in ALGORITHMS:
                subset = [
                    r for r in rows
                    if r["algorithm"] == name and (group == "Tất cả" or r["group"] == group)
                ]
                if not subset:
                    continue
                writer.writerow({
                    "group": group,
                    "algorithm": name,
                    "levels": len(subset),
                    "avg_length": f"{statistics.mean(r['length'] for r in subset):.1f}",
                    "avg_expanded": f"{statistics.mean(r['expanded'] for r in subset):.1f}",
                    "avg_time_ms": f"{statistics.mean(r['time_ms'] for r in subset):.3f}",
                    "avg_memory_kb": f"{statistics.mean(r['memory_kb'] for r in subset):.1f}",
                })


def plot(rows: list[dict], out_dir: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({
        "font.size": 10,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.edgecolor": "#8a8a85",
        "axes.labelcolor": "#3d3d3a",
        "xtick.color": "#3d3d3a",
        "ytick.color": "#3d3d3a",
        "axes.grid": True,
        "axes.grid.axis": "y",
        "grid.color": "#e4e3dd",
        "grid.linewidth": 0.8,
        "axes.axisbelow": True,
    })

    from matplotlib.ticker import FuncFormatter

    groups = {r["level"]: r["group"] for r in rows}
    levels = sorted(groups, key=lambda lv: (GROUP_ORDER.index(groups[lv]), lv))
    plain = FuncFormatter(lambda v, _: f"{v:g}")
    by_key = {(r["level"], r["algorithm"]): r for r in rows}

    metrics = [
        ("length", "Độ dài lời giải (số bước)", "length.png", True),
        ("expanded", "Số node mở rộng", "expanded.png", True),
        ("time_ms", "Thời gian tìm kiếm (ms)", "time.png", True),
        ("memory_kb", "Bộ nhớ đỉnh (KB)", "memory.png", True),
    ]

    width = 0.8 / len(ALGORITHMS)
    x = list(range(len(levels)))
    labels = [f"L{lv}" for lv in levels]

    for key, title, filename, log in metrics:
        fig, ax = plt.subplots(figsize=(11, 4.2), dpi=160)
        for i, name in enumerate(ALGORITHMS):
            offset = (i - (len(ALGORITHMS) - 1) / 2) * width
            values = [by_key[(lv, name)][key] for lv in levels]
            ax.bar(
                [p + offset for p in x], values, width=width - 0.04,
                color=COLORS[name], label=name, edgecolor="white", linewidth=1,
            )
        if log:
            ax.set_yscale("log")
            ax.yaxis.set_major_formatter(plain)
        ax.set_xticks(x, labels)
        ax.set_xlim(-0.6, len(levels) - 0.4)
        ax.set_title(f"{title}: {', '.join(ALGORITHMS)} trên từng level", loc="left", fontsize=12, color="#1f1f1d")
        ax.set_ylabel(title + (" (thang log)" if log else ""))
        ax.legend(frameon=False, loc="upper left", ncols=2)

        for g in GROUP_ORDER:
            idx = [i for i, lv in enumerate(levels) if groups[lv] == g]
            if not idx:
                continue
            if idx[0] != 0:
                ax.axvline(idx[0] - 0.5, color="#c3c2b7", linewidth=0.8, linestyle=":")
            ax.annotate(
                g, xy=((idx[0] + idx[-1]) / 2, 0), xycoords=("data", "axes fraction"),
                xytext=(0, -30), textcoords="offset points",
                ha="center", va="top", fontsize=10, color="#6b6b66",
            )
        fig.tight_layout()
        fig.savefig(out_dir / filename)
        plt.close(fig)

    fig, ax = plt.subplots(figsize=(6.5, 5), dpi=160)
    for name in ALGORITHMS:
        pts = [by_key[(lv, name)] for lv in levels]
        ax.scatter(
            [p["expanded"] for p in pts], [p["length"] for p in pts],
            s=42, color=COLORS[name], label=name, edgecolor="white", linewidth=1.5, zorder=3,
        )
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.xaxis.set_major_formatter(plain)
    ax.yaxis.set_major_formatter(plain)
    ax.grid(True, axis="both")
    ax.set_xlabel("Số node mở rộng (thang log)")
    ax.set_ylabel("Độ dài lời giải (thang log)")
    ax.set_title("Đánh đổi: số node mở rộng và chất lượng lời giải", loc="left", fontsize=12, color="#1f1f1d")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(out_dir / "tradeoff.png")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--runs", type=int, default=5, help="số lần đo thời gian mỗi cặp (lấy trung vị)")
    parser.add_argument("--out", type=Path, default=SOURCE_DIR / "experiments" / "results")
    parser.add_argument("--no-plot", action="store_true", help="chỉ xuất CSV, không vẽ biểu đồ")
    parser.add_argument(
        "--algos", default="BFS,DFS",
        help="danh sách thuật toán, cách nhau bởi dấu phẩy (BFS,DFS,UCS,A*), hoặc 'all'",
    )
    args = parser.parse_args()

    names = list(ALL_ALGORITHMS) if args.algos == "all" else [a.strip() for a in args.algos.split(",")]
    ALGORITHMS.clear()
    ALGORITHMS.update({name: ALL_ALGORITHMS[name] for name in names})

    args.out.mkdir(parents=True, exist_ok=True)
    rows = run_all(args.runs)
    write_csv(rows, args.out)
    if not args.no_plot:
        plot(rows, args.out)
    print(f"\nĐã lưu kết quả vào {args.out}")


if __name__ == "__main__":
    main()