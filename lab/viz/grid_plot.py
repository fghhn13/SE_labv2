from __future__ import annotations

from typing import Iterable, List, Sequence, Tuple, Optional

import matplotlib.pyplot as plt
import numpy as np

from lab.envs.grid.grid_map import GridMap, Coord
from lab.core.types import EpisodeResult
from lab.viz.grid_text import (
    _select_most_frequent_episode,
    _select_best_episode,
    _select_worst_episode,
)


def _grid_to_array(grid: GridMap) -> np.ndarray:
    """
    将 GridMap 转为整数矩阵，便于用 imshow 绘制。
    约定编码：
    0: 空白
    1: 墙
    2: 起点
    3: 终点
    """
    arr = np.zeros((grid.height, grid.width), dtype=int)
    for y in range(grid.height):
        for x in range(grid.width):
            coord = (x, y)
            if grid.is_wall(coord):
                arr[y, x] = 1
    sx, sy = grid.start
    gx, gy = grid.goal
    arr[sy, sx] = 2
    arr[gy, gx] = 3
    return arr


def _plot_single_path(
    grid: GridMap,
    ep: EpisodeResult,
    title: str,
    out_path: Optional[str] = None,
) -> None:
    arr = _grid_to_array(grid)

    fig, ax = plt.subplots(figsize=(4, 4))
    cmap = plt.get_cmap("tab20")
    im = ax.imshow(arr, cmap=cmap, origin="upper")

    # 绘制路径：用折线连接中心点
    if ep.path:
        xs = [x for (x, y) in ep.path]
        ys = [y for (x, y) in ep.path]
        ax.plot(xs, ys, color="red", linewidth=2, marker="o", markersize=3)

    ax.set_xticks(range(grid.width))
    ax.set_yticks(range(grid.height))
    ax.set_xticklabels(range(grid.width))
    ax.set_yticklabels(range(grid.height))
    ax.set_xlim(-0.5, grid.width - 0.5)
    ax.set_ylim(grid.height - 0.5, -0.5)
    ax.grid(True, color="black", alpha=0.3, linewidth=0.5)

    ax.set_title(title)
    plt.tight_layout()

    if out_path is None:
        plt.show()
    else:
        fig.savefig(out_path)
        plt.close(fig)


def save_representative_path_plots(
    grid: GridMap,
    history: List[EpisodeResult],
    output_dir: str,
) -> None:
    """
    保存三类代表性 episode 的路径图（使用 matplotlib）：
    - most_frequent.png
    - best.png
    - worst.png
    """
    if not history:
        return

    import os

    os.makedirs(output_dir, exist_ok=True)

    indexed = list(enumerate(history))

    most_freq = _select_most_frequent_episode(indexed)
    best = _select_best_episode(indexed)
    worst = _select_worst_episode(indexed)

    if most_freq is not None:
        idx, ep = most_freq
        _plot_single_path(
            grid,
            ep,
            title=f"Most frequent (idx={idx}, steps={ep.steps}, success={ep.success})",
            out_path=os.path.join(output_dir, "most_frequent.png"),
        )

    if best is not None:
        idx, ep = best
        _plot_single_path(
            grid,
            ep,
            title=f"Best (idx={idx}, steps={ep.steps}, success={ep.success})",
            out_path=os.path.join(output_dir, "best.png"),
        )

    if worst is not None:
        idx, ep = worst
        _plot_single_path(
            grid,
            ep,
            title=f"Worst (idx={idx}, steps={ep.steps}, success={ep.success})",
            out_path=os.path.join(output_dir, "worst.png"),
        )

