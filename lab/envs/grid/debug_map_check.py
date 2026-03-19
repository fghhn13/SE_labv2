from __future__ import annotations

import argparse
from collections import deque
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from lab.envs.grid.grid_map import GridMap, Coord
from lab.envs.grid.map_file_parser import parse_gridmap_file
from lab.envs.grid.elements import EmptyElement, GoalElement, StartElement, TrapElement, WallElement


CoordLike = Tuple[int, int]


def _find_repo_maps_dir(start: Path) -> Optional[Path]:
    for parent in [start, *start.parents]:
        candidate = parent / "maps"
        if candidate.exists() and candidate.is_dir():
            return candidate
    return None


def _neighbors4() -> List[Tuple[int, int]]:
    return [(0, -1), (0, 1), (-1, 0), (1, 0)]


def _is_passable(grid: GridMap, p: CoordLike) -> bool:
    elem = grid.get_element_at(p)
    return bool(elem.is_passable())


def _reachable(grid: GridMap, start: CoordLike, goal: CoordLike) -> bool:
    q: deque[CoordLike] = deque([start])
    seen = {start}
    while q:
        x, y = q.popleft()
        if (x, y) == goal:
            return True
        for dx, dy in _neighbors4():
            nx, ny = x + dx, y + dy
            np = (nx, ny)
            if np in seen:
                continue
            if not grid.in_bounds(np):
                continue
            if not _is_passable(grid, np):
                continue
            seen.add(np)
            q.append(np)
    return False


def _count_symbols(grid: GridMap) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for y in range(grid.height):
        for x in range(grid.width):
            elem = grid.get_element_at((x, y))
            sym = getattr(elem, "symbol", "?")
            counts[sym] = counts.get(sym, 0) + 1
    return counts


def validate_gridmap(grid: GridMap, *, strict_reachability: bool = False) -> List[str]:
    """
    Returns a list of "problems". Empty list => pass.
    """
    problems: List[str] = []

    if grid.width <= 0 or grid.height <= 0:
        problems.append("width/height must be positive")

    if not grid.in_bounds(grid.start):
        problems.append("start out of bounds")
    if not grid.in_bounds(grid.goal):
        problems.append("goal out of bounds")

    # Start/goal should be marked in the element grid.
    start_elem = grid.get_element_at(grid.start)
    goal_elem = grid.get_element_at(grid.goal)
    if start_elem.symbol != StartElement.symbol:
        problems.append(f"start element symbol mismatch: expected {StartElement.symbol!r}, got {start_elem.symbol!r}")
    if goal_elem.symbol != GoalElement.symbol:
        problems.append(f"goal element symbol mismatch: expected {GoalElement.symbol!r}, got {goal_elem.symbol!r}")

    # Basic uniqueness checks (enforced during parsing, but keep for robustness).
    counts = _count_symbols(grid)
    if counts.get(StartElement.symbol, 0) != 1:
        problems.append(f"must contain exactly one Start {StartElement.symbol!r}, got {counts.get(StartElement.symbol, 0)}")
    if counts.get(GoalElement.symbol, 0) != 1:
        problems.append(f"must contain exactly one Goal {GoalElement.symbol!r}, got {counts.get(GoalElement.symbol, 0)}")

    # Validate wall/passable contract if we ever change elements.
    for y in range(grid.height):
        for x in range(grid.width):
            p = (x, y)
            elem = grid.get_element_at(p)
            if elem.symbol == WallElement.symbol and elem.is_passable():
                problems.append("WallElement must be non-passable")

    if strict_reachability:
        if not _reachable(grid, grid.start, grid.goal):
            problems.append("start cannot reach goal via passable cells")

    return problems


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--map-name", type=str, default=None, help="Only validate one map by stem name.")
    ap.add_argument("--strict-reachability", action="store_true", help="Fail if start cannot reach goal.")
    ap.add_argument("--maps-dir", type=str, default=None, help="Override maps directory.")
    args = ap.parse_args()

    maps_dir = Path(args.maps_dir) if args.maps_dir else _find_repo_maps_dir(Path(__file__).resolve())
    if maps_dir is None:
        raise RuntimeError("Cannot locate repo maps/ directory")

    paths: List[Path] = []
    if args.map_name:
        p = maps_dir / f"{args.map_name}.map"
        paths = [p]
    else:
        paths = sorted(maps_dir.glob("*.map"))

    if not paths:
        print("No .map files found.")
        return

    ok = True
    for path in paths:
        try:
            grid = parse_gridmap_file(path)
            problems = validate_gridmap(grid, strict_reachability=args.strict_reachability)
            if problems:
                ok = False
                print(f"[FAIL] {path.name}:")
                for p in problems:
                    print(f"  - {p}")
            else:
                counts = _count_symbols(grid)
                trap_count = counts.get(TrapElement.symbol, 0)
                print(f"[OK] {path.name}: {grid.width}x{grid.height}, traps={trap_count}, start={grid.start}, goal={grid.goal}")
        except Exception as e:
            ok = False
            print(f"[ERROR] {path.name}: {e}")

    if not ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

