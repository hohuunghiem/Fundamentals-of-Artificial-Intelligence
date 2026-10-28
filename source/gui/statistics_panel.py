"""Khung giao diện hiển thị thống kê kết quả tìm kiếm."""
from __future__ import annotations

from collections.abc import Sequence

from ursina import Entity, camera, destroy, color

from algorithms.result import SolveResult
from gui.theme import (
    PANEL,
    MUTED,
    GOLD,
    panel,
    label,
    button,
)


class StatisticsPanel:
    def __init__(self) -> None:
        self.root = None
        self.visible = False

    def show(self, results: Sequence[SolveResult]) -> None:
        """Hiển thị số bước, tổng chi phí và thống kê tìm kiếm."""
        self.hide()

        self.root = Entity(
            parent=camera.ui,
            z=-2,
        )
        self.visible = True

        # Chặn click vào các nút phía sau bảng.
        Entity(
            parent=self.root,
            model="quad",
            scale=(4, 2),
            z=.2,
            color=color.rgba32(0, 0, 0, 180),
            collider="box",
        )

        panel(
            parent=self.root,
            x=0,
            y=0,
            width=1.50,
            height=.66,
            tint=PANEL,
        )

        label(
            parent=self.root,
            text="SEARCH RESULTS",
            x=-.67,
            y=.27,
            size=1.4,
        )

        # Vị trí của 7 cột.
        columns = [
            -.67,   # Method
            -.49,   # Steps
            -.32,   # Cost
            -.15,   # Time
            .08,    # Memory
            .31,    # Expanded
            .52,    # Generated
        ]

        headings = [
            "Method",
            "Steps",
            "Cost",
            "Time (s)",
            "Mem (MiB)",
            "Expanded",
            "Generated",
        ]

        for x, heading in zip(columns, headings):
            label(
                parent=self.root,
                text=heading,
                x=x,
                y=.15,
                size=.65,
                tint=GOLD,
            )

        for index, result in enumerate(results):
            steps_text = (
                str(result.solution_length)
                if result.success
                else "No path"
            )

            # Kiểm tra None để vẫn hiển thị đúng chi phí bằng 0.
            cost_text = (
                str(result.solution_cost)
                if result.success and result.solution_cost is not None
                else "N/A"
            )

            values = [
                result.algorithm,
                steps_text,
                cost_text,
                f"{result.search_time:.4f}",
                f"{result.memory_usage:.2f}",
                str(result.expanded_nodes),
                str(result.generated_nodes),
            ]

            for x, value in zip(columns, values):
                label(
                    parent=self.root,
                    text=value,
                    x=x,
                    y=.065 - index * .065,
                    size=.72,
                )

        if not results:
            label(
                parent=self.root,
                text="No AI results yet.",
                x=-.67,
                y=.04,
                size=1,
                tint=MUTED,
            )

        label(
            parent=self.root,
            text="Steps: actions taken. Cost: total 1/2/4 action cost.",
            x=-.67,
            y=-.22,
            size=.60,
            tint=MUTED,
        )

        label(
            parent=self.root,
            text="Memory: peak traced Python allocations (MiB).",
            x=-.67,
            y=-.265,
            size=.60,
            tint=MUTED,
        )

        button(
            parent=self.root,
            text="CLOSE",
            x=.59,
            y=.26,
            action=self.hide,
            width=.17,
            height=.045,
        )

    def hide(self) -> None:
        """Đóng bảng và xóa các thành phần hiển thị."""
        if self.root is not None:
            destroy(self.root)
            self.root = None

        self.visible = False

    def destroy(self) -> None:
        """Giải phóng bảng khi rời màn chơi."""
        self.hide()