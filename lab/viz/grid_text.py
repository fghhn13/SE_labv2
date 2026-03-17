from __future__ import annotations

from collections import Counter
from typing import Iterable, List, Sequence, Tuple

from lab.envs.grid.grid_map import GridMap, Coord
from lab.core.types import EpisodeResult


def _select_most_frequent_episode(
    history: Iterable[Tuple[int, EpisodeResult]]
) -> Tuple[int, EpisodeResult] | None:
    counter: Counter[Tuple] = Counter()
    index_by_path: dict[Tuple, int] = {}

    for idx, ep in history:
        key = tuple(ep.path)
        counter[key] += 1
        # 记录首次出现的 episode 索引，方便回溯
        if key not in index_by_path:
            index_by_path[key] = idx

    if not counter:
        return None

    path_key, count = counter.most_common(1)[0]
    ep_idx = index_by_path[path_key]
    # 再次遍历找到对应 EpisodeResult
    for idx, ep in history:
        if idx == ep_idx:
            return idx, ep
    return None


def _select_best_episode(
    history: Iterable[Tuple[int, EpisodeResult]]
) -> Tuple[int, EpisodeResult] | None:
    best: Tuple[int, EpisodeResult] | None = None
    for idx, ep in history:
        if not ep.success:
            continue
        if best is None or ep.steps < best[1].steps:
            best = (idx, ep)
    return best


def _select_worst_episode(
    history: Iterable[Tuple[int, EpisodeResult]]
) -> Tuple[int, EpisodeResult] | None:
    worst: Tuple[int, EpisodeResult] | None = None
    for idx, ep in history:
        # 优先考虑失败的；如果都成功，则选步数最多的
        if worst is None:
            worst = (idx, ep)
            continue
        cur = worst[1]
        if (not ep.success and cur.success) or (
            ep.success == cur.success and ep.steps > cur.steps
        ):
            worst = (idx, ep)
    return worst


def print_path_summaries(
    grid: GridMap, history: List[EpisodeResult]
) -> None:
    """
    根据奖励历史打印训练日志与 3 类代表性路径：
    - 最多次数（路径模式出现次数最多）
    - 最好路径（成功且步数最短）
    - 最坏路径（优先失败，其次步数最长）
    """
    if not history:
        print("No episodes recorded; nothing to summarize.")
        return

    indexed = list(enumerate(history))

    # 训练整体日志
    total_eps = len(history)
    successes = sum(1 for ep in history if ep.success)
    avg_steps = sum(ep.steps for ep in history) / total_eps
    print(
        f"Training summary: episodes={total_eps}, "
        f"success_rate={successes/total_eps:.2f}, "
        f"avg_steps={avg_steps:.2f}"
    )

    # 选择三个代表性 episode
    most_freq = _select_most_frequent_episode(indexed)
    best = _select_best_episode(indexed)
    worst = _select_worst_episode(indexed)

    printed: set[int] = set()

    def _print_case(tag: str, res: Tuple[int, EpisodeResult] | None) -> None:
        if res is None:
            print(f"{tag}: <none>")
            return
        idx, ep = res
        if idx in printed:
            return
        printed.add(idx)
        print(
            f"\n=== {tag} episode (idx={idx}, "
            f"success={ep.success}, steps={ep.steps}, cost={ep.cost:.2f}) ==="
        )

    _print_case("Most frequent path", most_freq)
    _print_case("Best path", best)
    _print_case("Worst path", worst)

