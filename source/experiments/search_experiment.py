"""Chạy thực nghiệm BFS, DFS, UCS và A*, xuất CSV và biểu đồ.

Chạy từ thư mục source:

    python -m experiments.search_experiment
    python -m experiments.search_experiment --runs 1 --no-plot
    python -m experiments.search_experiment --algos all --runs 5

Thời gian: trung vị của các lượt chạy không bật tracemalloc.
Bộ nhớ: đo riêng bằng run_with_profiling, đơn vị KiB.
Cost: tổng chi phí 1–2–4 của đường đi tìm được.
"""
from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
from pathlib import Path
from time import perf_counter

from algorithms.astar import astar_search
from algorithms.bfs import bfs_search
from algorithms.dfs import dfs_search
from algorithms.ucs import ucs_search
from algorithms.profiler import run_with_profiling
from core.enums import TileType
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

ALGORITHMS = dict(ALL_ALGORITHMS)

COLORS = {
    "BFS": "#2a78d6",
    "DFS": "#eb6834",
    "UCS": "#1baf7a",
    "A*": "#eda100",
}

GROUP_ORDER = ["Cơ bản", "Fragile", "Switch", "Kết hợp"]


def _prefix() -> str:
    return "_".join(
        name.lower().replace("*", "star")
        for name in ALGORITHMS
    )


def level_number(path: Path) -> int:
    return int(path.stem.removeprefix("level"))


def classify(path: Path) -> str:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    chars = set("".join(data["board"]))

    has_fragile = "f" in chars
    has_switch = bool(chars & {"s", "h", "p", "S", "b", "B"})

    if has_fragile and has_switch:
        return "Kết hợp"
    if has_fragile:
        return "Fragile"
    if has_switch:
        return "Switch"
    return "Cơ bản"


def verify_and_cost(level, moves) -> tuple[bool, int | None]:
    """Chạy lại đường đi và tính độc lập tổng chi phí 1–2–4.

    Chỉ tính trên đường đi trả về, không tính các nhánh đã duyệt.
    Hàm này được gọi ngoài phần đo thời gian và bộ nhớ.
    """
    state = level.initial_state
    total_cost = 0

    for move in moves:
        next_state = apply_move(level.board, state, move)

        if next_state is None:
            return False, None

        touches_fragile = any(
            level.board.get_tile(row, col) == TileType.FRAGILE
            for row, col in next_state.occupied_cells()
        )

        if touches_fragile:
            step_cost = 4
        elif state.block.orientation != next_state.block.orientation:
            step_cost = 2
        else:
            step_cost = 1

        total_cost += step_cost
        state = next_state

    if not is_goal_state(level.board, state):
        return False, None

    return True, total_cost


def measure(name, search_fn, level, runs: int) -> dict:
    times = []

    # Đo thời gian riêng, không bật tracemalloc.
    for _ in range(runs):
        start = perf_counter()
        search_fn(level)
        times.append(perf_counter() - start)

    # Chạy riêng một lượt để đo bộ nhớ và lấy kết quả.
    profiled = run_with_profiling(name, search_fn, level)

    valid = False
    checked_cost = None

    if profiled.success:
        valid, checked_cost = verify_and_cost(
            level,
            profiled.moves,
        )

    # None nghĩa là không áp dụng vì solver báo không có lời giải.
    cost_valid = (
        valid
        and profiled.solution_cost is not None
        and profiled.solution_cost == checked_cost
    ) if profiled.success else None

    return {
        "success": profiled.success,
        "valid": valid,
        "cost_valid": cost_valid,
        "length": (
            profiled.solution_length
            if profiled.success
            else None
        ),
        "cost": (
            profiled.solution_cost
            if profiled.success
            else None
        ),
        "checked_cost": checked_cost,
        "expanded": profiled.expanded_nodes,
        "generated": profiled.generated_nodes,
        "time_ms": statistics.median(times) * 1000,
        "memory_kib": profiled.memory_usage * 1024,
    }


def warm_up(paths) -> None:
    """Chạy khởi động trước các lượt đo chính thức."""
    for path in paths:
        level = load_level(path)
        for search_fn in ALGORITHMS.values():
            search_fn(level)


def run_all(runs: int) -> list[dict]:
    paths = sorted(
        LEVELS_DIR.glob("level*.json"),
        key=level_number,
    )

    if not paths:
        raise FileNotFoundError(
            f"Không tìm thấy level*.json trong {LEVELS_DIR}"
        )

    print("Đang chạy khởi động...")
    warm_up(paths)

    rows = []

    for path in paths:
        level = load_level(path)
        group = classify(path)

        for name, search_fn in ALGORITHMS.items():
            result = measure(name, search_fn, level, runs)

            rows.append({
                "level": level_number(path),
                "group": group,
                "algorithm": name,
                **result,
            })

            if not result["success"]:
                status = "NO PATH"
            elif not result["valid"]:
                status = "INVALID PATH"
            elif not result["cost_valid"]:
                status = "COST MISMATCH"
            else:
                status = "OK"

            length_text = (
                str(result["length"])
                if result["length"] is not None
                else "N/A"
            )
            cost_text = (
                str(result["cost"])
                if result["cost"] is not None
                else "N/A"
            )

            print(
                f"Level {level_number(path):>2} "
                f"[{group:<8}] {name:<3}: "
                f"steps={length_text:<5} "
                f"cost={cost_text:<6} "
                f"expanded={result['expanded']:<6} "
                f"time={result['time_ms']:8.2f} ms "
                f"mem={result['memory_kib']:9.1f} KiB "
                f"{status}"
            )

    return rows


def check_results(rows: list[dict]) -> list[str]:
    """Kiểm tra đường đi, chi phí và đối chiếu các solver."""
    errors = []

    for row in rows:
        if row["success"] and not row["valid"]:
            errors.append(
                f"Level {row['level']} {row['algorithm']}: "
                "đường đi không hợp lệ."
            )
        elif row["success"] and not row["cost_valid"]:
            errors.append(
                f"Level {row['level']} {row['algorithm']}: "
                f"cost trả về={row['cost']}, "
                f"cost tính lại={row['checked_cost']}."
            )

    for level_id in sorted({row["level"] for row in rows}):
        results = {
            row["algorithm"]: row
            for row in rows
            if row["level"] == level_id
        }

        # Các solver hoàn tất trên cùng màn phải thống nhất
        # về việc có hay không có lời giải.
        successes = {row["success"] for row in results.values()}
        if len(successes) > 1:
            errors.append(
                f"Level {level_id}: các solver không thống nhất "
                "về việc có lời giải."
            )

        ucs = results.get("UCS")
        astar = results.get("A*")

        if (
            ucs is not None
            and astar is not None
            and ucs["cost_valid"]
            and astar["cost_valid"]
            and ucs["cost"] != astar["cost"]
        ):
            errors.append(
                f"Level {level_id}: UCS cost={ucs['cost']} "
                f"khác A* cost={astar['cost']}."
            )

        # BFS phải có số hành động không lớn hơn
        # bất kỳ lời giải hợp lệ nào của solver khác.
        bfs = results.get("BFS")
        if bfs is not None and bfs["valid"]:
            for name, row in results.items():
                if row["valid"] and row["length"] < bfs["length"]:
                    errors.append(
                        f"Level {level_id}: {name} có ít bước hơn BFS."
                    )

        # UCS không được đắt hơn một lời giải hợp lệ khác.
        if ucs is not None and ucs["cost_valid"]:
            for name, row in results.items():
                if row["cost_valid"] and row["cost"] < ucs["cost"]:
                    errors.append(
                        f"Level {level_id}: {name} có cost thấp hơn UCS."
                    )

    return errors


def average(rows: list[dict], key: str) -> str:
    values = [
        row[key]
        for row in rows
        if row[key] is not None
    ]
    if not values:
        return ""
    return f"{statistics.mean(values):.3f}"


def write_csv(rows: list[dict], out_dir: Path) -> None:
    fields = [
        "level", "group", "algorithm",
        "success", "valid", "cost_valid",
        "length", "cost", "checked_cost",
        "expanded", "generated", "time_ms", "memory_kib",
    ]

    results_path = out_dir / f"{_prefix()}_results.csv"

    with results_path.open(
        "w", newline="", encoding="utf-8-sig"
    ) as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()

        for row in rows:
            writer.writerow({
                **{key: row[key] for key in fields},
                "time_ms": f"{row['time_ms']:.3f}",
                "memory_kib": f"{row['memory_kib']:.3f}",
            })

    summary_fields = [
        "group", "algorithm", "levels",
        "successes", "valid_solutions", "verified_costs",
        "avg_length", "avg_cost",
        "avg_expanded", "avg_time_ms", "avg_memory_kib",
    ]

    summary_path = out_dir / f"{_prefix()}_summary.csv"

    with summary_path.open(
        "w", newline="", encoding="utf-8-sig"
    ) as file:
        writer = csv.DictWriter(file, fieldnames=summary_fields)
        writer.writeheader()

        for group in GROUP_ORDER + ["Tất cả"]:
            for name in ALGORITHMS:
                subset = [
                    row for row in rows
                    if row["algorithm"] == name
                    and (
                        group == "Tất cả"
                        or row["group"] == group
                    )
                ]

                if not subset:
                    continue

                valid_rows = [
                    row for row in subset if row["valid"]
                ]
                cost_rows = [
                    row for row in subset if row["cost_valid"]
                ]

                writer.writerow({
                    "group": group,
                    "algorithm": name,
                    "levels": len(subset),
                    "successes": sum(
                        row["success"] for row in subset
                    ),
                    "valid_solutions": len(valid_rows),
                    "verified_costs": len(cost_rows),
                    # Chất lượng lời giải chỉ tính trên
                    # các lời giải đã kiểm tra hợp lệ.
                    "avg_length": average(valid_rows, "length"),
                    "avg_cost": average(cost_rows, "cost"),
                    # Tài nguyên tính trên tất cả màn,
                    # kể cả khi không tìm được lời giải.
                    "avg_expanded": average(subset, "expanded"),
                    "avg_time_ms": average(subset, "time_ms"),
                    "avg_memory_kib": average(subset, "memory_kib"),
                })


def plot(rows: list[dict], out_dir: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")

    import matplotlib.pyplot as plt
    from matplotlib.ticker import FuncFormatter

    plt.rcParams.update({
        "font.size": 10,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "axes.grid.axis": "y",
        "grid.color": "#e4e3dd",
        "axes.axisbelow": True,
    })

    groups = {row["level"]: row["group"] for row in rows}
    levels = sorted(groups)
    by_key = {
        (row["level"], row["algorithm"]): row
        for row in rows
    }

    metrics = [
        ("length", "Độ dài lời giải (số hành động)", "length.png"),
        ("cost", "Tổng chi phí lời giải", "cost.png"),
        ("expanded", "Số nút mở rộng", "expanded.png"),
        ("time_ms", "Thời gian tìm kiếm (ms)", "time.png"),
        ("memory_kib", "Bộ nhớ Python đỉnh (KiB)", "memory.png"),
    ]

    width = 0.8 / len(ALGORITHMS)
    x = list(range(len(levels)))
    tick_labels = [
        f"L{level_id}\n{groups[level_id]}"
        for level_id in levels
    ]

    for key, title, filename in metrics:
        fig, ax = plt.subplots(figsize=(12, 4.5), dpi=160)
        plotted_values = []

        for index, name in enumerate(ALGORITHMS):
            offset = (
                index - (len(ALGORITHMS) - 1) / 2
            ) * width

            values = []
            for level_id in levels:
                row = by_key[(level_id, name)]
                value = row[key]

                if key == "length" and not row["valid"]:
                    value = None
                if key == "cost" and not row["cost_valid"]:
                    value = None

                if value is not None:
                    plotted_values.append(value)

                values.append(
                    float("nan") if value is None else value
                )

            ax.bar(
                [position + offset for position in x],
                values,
                width=width * .9,
                color=COLORS[name],
                label=name,
                edgecolor="white",
                linewidth=.8,
            )

        # Chỉ dùng log khi tất cả giá trị hiển thị đều dương.
        use_log = (
            bool(plotted_values)
            and all(value > 0 for value in plotted_values)
        )
        if use_log:
            ax.set_yscale("log")
            ax.yaxis.set_major_formatter(
                FuncFormatter(lambda value, _: f"{value:g}")
            )

        ax.set_xticks(x, tick_labels, fontsize=8)
        ax.set_xlim(-.6, len(levels) - .4)
        ax.set_title(title, loc="left", fontsize=12)
        ax.set_ylabel(
            title + (" (thang log)" if use_log else "")
        )
        ax.legend(frameon=False, ncols=len(ALGORITHMS))

        fig.tight_layout()
        fig.savefig(out_dir / filename)
        plt.close(fig)

    # Giữ biểu đồ đánh đổi số nút mở rộng và số hành động.
    fig, ax = plt.subplots(figsize=(7, 5), dpi=160)
    all_points = []

    for name in ALGORITHMS:
        points = [
            row for row in rows
            if row["algorithm"] == name and row["valid"]
        ]
        all_points.extend(points)

        ax.scatter(
            [row["expanded"] for row in points],
            [row["length"] for row in points],
            color=COLORS[name],
            label=name,
            s=45,
            edgecolor="white",
        )

    log_x = (
        bool(all_points)
        and all(row["expanded"] > 0 for row in all_points)
    )
    log_y = (
        bool(all_points)
        and all(row["length"] > 0 for row in all_points)
    )

    if log_x:
        ax.set_xscale("log")
    if log_y:
        ax.set_yscale("log")

    ax.set_xlabel(
        "Số nút mở rộng" + (" (thang log)" if log_x else "")
    )
    ax.set_ylabel(
        "Số hành động" + (" (thang log)" if log_y else "")
    )
    ax.set_title("Số nút mở rộng và độ dài lời giải")
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(out_dir / "tradeoff.png")
    plt.close(fig)


def main() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(
                encoding="utf-8",
                errors="replace",
            )

    parser = argparse.ArgumentParser(
        description=__doc__.splitlines()[0]
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=5,
        help="Số lượt đo thời gian mỗi cặp thuật toán/level.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=SOURCE_DIR / "experiments" / "results_all",
    )
    parser.add_argument(
        "--no-plot",
        action="store_true",
        help="Chỉ xuất CSV, không cần Matplotlib.",
    )
    parser.add_argument(
        "--algos",
        default="all",
        help="BFS,DFS,UCS,A* hoặc all.",
    )

    args = parser.parse_args()

    if args.runs < 1:
        parser.error("--runs phải lớn hơn hoặc bằng 1.")

    names = (
        list(ALL_ALGORITHMS)
        if args.algos.strip().lower() == "all"
        else [name.strip() for name in args.algos.split(",")]
    )

    unknown = [
        name for name in names if name not in ALL_ALGORITHMS
    ]
    if unknown:
        parser.error(f"Thuật toán không hợp lệ: {unknown}")

    ALGORITHMS.clear()
    ALGORITHMS.update({
        name: ALL_ALGORITHMS[name]
        for name in names
    })

    args.out.mkdir(parents=True, exist_ok=True)

    rows = run_all(args.runs)
    errors = check_results(rows)

    # Vẫn lưu CSV để có dữ liệu kiểm tra nếu phát hiện lỗi.
    write_csv(rows, args.out)

    if errors:
        print("\nPhát hiện vấn đề:")
        for error in errors:
            print(f"- {error}")
        print(f"\nCSV kiểm tra đã lưu tại: {args.out}")
        raise SystemExit(1)

    print("\nKhông phát hiện sai lệch trong các kiểm tra đã chạy.")
    print("Đường đi và chi phí được kiểm tra theo luật của code.")

    if not args.no_plot:
        plot(rows, args.out)

    print(f"\nĐã lưu kết quả tại: {args.out}")


if __name__ == "__main__":
    main()