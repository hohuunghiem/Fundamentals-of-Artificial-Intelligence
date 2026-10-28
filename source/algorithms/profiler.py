"""Đo thời gian và bộ nhớ khi chạy thuật toán tìm kiếm."""
from collections.abc import Callable
from time import perf_counter
import tracemalloc
from typing import Any

from core.level import Level
from algorithms.result import SolveResult


def run_with_profiling(
    algorithm: str,
    search_fn: Callable[[Level], dict[str, Any] | None],
    level: Level,
) -> SolveResult:
    """Chạy solver, đo thời gian/bộ nhớ và đóng gói kết quả.

    Giữ nguyên đường đi, tổng chi phí và số nút do solver trả về.
    Hàm này không tính lại hoặc cộng thêm chi phí.
    """
    started_tracing_here = not tracemalloc.is_tracing()

    if started_tracing_here:
        tracemalloc.start()

    baseline, _ = tracemalloc.get_traced_memory()
    tracemalloc.reset_peak()
    start_time = perf_counter()

    try:
        search_result = search_fn(level)
        search_time = perf_counter() - start_time
        _, peak_memory = tracemalloc.get_traced_memory()
    finally:
        if started_tracing_here:
            tracemalloc.stop()

    search_result = search_result or {}

    moves = search_result.get("moves")
    success = bool(
        search_result.get("success", moves is not None)
    )

    if not success or moves is None:
        success = False
        moves = []
        solution_cost = None
    else:
        # Lấy đúng tổng chi phí mà solver đã tính.
        # Không dùng số bước để thay thế khi thiếu chi phí.
        solution_cost = search_result.get("solution_cost")

    return SolveResult(
        algorithm=algorithm,
        success=success,
        moves=list(moves),
        search_time=search_time,
        memory_usage=max(0, peak_memory - baseline) / (1024 * 1024),
        expanded_nodes=int(search_result.get("expanded_nodes", 0)),
        generated_nodes=int(search_result.get("generated_nodes", 0)),
        solution_cost=solution_cost,
    )