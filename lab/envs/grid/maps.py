from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Callable, Dict, Optional

from .grid_map import GridMap, Coord


MapBuilder = Callable[[], GridMap]


_MAP_REGISTRY: Dict[str, MapBuilder] = {}


def register_map(name: str, builder: MapBuilder) -> None:
    _MAP_REGISTRY[name] = builder


def list_maps() -> Dict[str, MapBuilder]:
    return dict(_MAP_REGISTRY)


def get_map(name: str) -> GridMap:
    if name not in _MAP_REGISTRY:
        raise ValueError(f"Unknown grid map: {name}")
    return _MAP_REGISTRY[name]()


def _make_open_5x5() -> GridMap:
    """
    最简单的 5x5 开放地图：无障碍，起点 (0,0)，终点 (4,4)。
    """
    width, height = 5, 5
    start: Coord = (0, 0)
    goal: Coord = (4, 4)
    walls: set[Coord] = set()
    return GridMap(width=width, height=height, start=start, goal=goal, walls=walls)


def _make_random_blocks_10x10(seed: Optional[int] = None) -> GridMap:
    """
    简单示例：在 10x10 网格上随机放置少量障碍。
    不保证 start 到 goal 可达，仅作为演示用。
    """
    if seed is not None:
        random.seed(seed)

    width, height = 10, 10
    start: Coord = (0, 0)
    goal: Coord = (9, 9)

    walls: set[Coord] = set()
    # 简单随机放置障碍：大约 15% 的格子是墙，跳过起终点
    for x in range(width):
        for y in range(height):
            coord = (x, y)
            if coord in (start, goal):
                continue
            if random.random() < 0.15:
                walls.add(coord)

    return GridMap(width=width, height=height, start=start, goal=goal, walls=walls)


def register_builtin_maps() -> None:
    """
    注册内置示例地图。
    """
    register_map("open_5x5", _make_open_5x5)
    # 随机障碍地图示例：生成函数在 get_map 时调用
    register_map("random_blocks_10x10", lambda: _make_random_blocks_10x10())


