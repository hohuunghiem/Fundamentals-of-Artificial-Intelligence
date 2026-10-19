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
    """Chạy ``search_fn`` trên level và đóng gói kết quả thành ``SolveResult``.

    Đo thời gian chạy và lượng bộ nhớ thuật toán sử dụng; lấy đường đi cùng
    số nút mở rộng/tạo từ từ điển kết quả. Nếu không tìm thấy lời giải, đánh
    dấu thất bại và cung cấp danh sách nước đi rỗng cho giao diện.
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
    success = bool(search_result.get("success", moves is not None))
    if not success or moves is None:
        moves = []

    return SolveResult(
        algorithm=algorithm,
        success=success,
        moves=list(moves),
        search_time=search_time,
        memory_usage=max(0, peak_memory - baseline) / (1024 * 1024),
        expanded_nodes=int(search_result.get("expanded_nodes", 0)),
        generated_nodes=int(search_result.get("generated_nodes", 0)),
    )
