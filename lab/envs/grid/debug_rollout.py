from __future__ import annotations

import argparse
from collections import deque
from pathlib import Path
from typing import Deque, Dict, List, Optional, Tuple

from lab.envs.grid.elements import GoalElement, StartElement, TrapElement, WallElement
from lab.envs.grid.environment import GridWorldEnvironment
from lab.envs.grid.grid_map import Coord, GridMap
from lab.envs.grid.map_file_parser import parse_gridmap_file
from lab.envs.grid.maps import get_map, register_builtin_maps


Action = Tuple[int, int]


def _neighbors4() -> List[Action]:
    return [(0, -1), (0, 1), (-1, 0), (1, 0)]


def _is_passable(grid: GridMap, p: Coord) -> bool:
    elem = grid.get_element_at(p)
    return bool(elem.is_passable())


def _bfs_path(grid: GridMap, start: Coord, goal: Coord) -> Optional[List[Coord]]:
    q: Deque[Coord] = deque([start])
    came_from: Dict[Coord, Optional[Coord]] = {start: None}
    while q:
        cur = q.popleft()
        if cur == goal:
            break
        cx, cy = cur
        for dx, dy in _neighbors4():
            nxt = (cx + dx, cy + dy)
            if nxt in came_from:
                continue
            if not grid.in_bounds(nxt):
                continue
            if not _is_passable(grid, nxt):
                continue
            came_from[nxt] = cur
            q.append(nxt)
    if goal not in came_from:
        return None

    # reconstruct
    path: List[Coord] = []
    cur: Optional[Coord] = goal
    while cur is not None:
        path.append(cur)
        cur = came_from[cur]
    path.reverse()
    return path


def _find_first_trap(grid: GridMap) -> Optional[Coord]:
    for y in range(grid.height):
        for x in range(grid.width):
            p = (x, y)
            elem = grid.get_element_at(p)
            if elem.symbol == TrapElement.symbol:
                return p
    return None


def _safe_load_map(map_name: str) -> GridMap:
    # Prefer the runtime registry path (uses auto registration).
    try:
        register_builtin_maps()
        return get_map(map_name)
    except Exception:
        # Fallback to direct parsing from `maps/`.
        # This keeps the debug scripts usable even if auto-registration breaks.
        here = Path(__file__).resolve()
        for parent in [here, *here.parents]:
            maps_dir = parent / "maps"
            if maps_dir.exists():
                p = maps_dir / f"{map_name}.map"
                if p.exists():
                    return parse_gridmap_file(p)
        raise


def _simulate_path(env: GridWorldEnvironment, path: List[Coord]) -> None:
    state = env.reset()
    assert state == path[0]
    print(f"[rollout] start={state} steps={len(path) - 1}")
    for i, nxt in enumerate(path[1:], start=1):
        dx = nxt[0] - state[0]
        dy = nxt[1] - state[1]
        action: Action = (dx, dy)
        step_result = env.step(action)
        code = env.grid.get_numeric_code_at(nxt)
        print(
            f"  step {i:02d}: action={action} next={step_result.next_state} "
            f"code@next={code} done={step_result.done} info={step_result.info}"
        )
        state = step_result.next_state
        if step_result.done:
            break


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--map-name", type=str, default="level_01_trap_maze")
    ap.add_argument("--check-blocked", action="store_true", help="Try one blocked move from start.")
    args = ap.parse_args()

    grid = _safe_load_map(args.map_name)

    # Find traps (may be none).
    trap_pos = _find_first_trap(grid)
    goal_pos = grid.goal
    start_pos = grid.start

    env = GridWorldEnvironment(grid_map=grid, step_reward=0.0)

    if args.check_blocked:
        # Attempt one move into a non-passable neighbor from start.
        state = env.reset()
        for dx, dy in env.get_actions(state):
            cand = (state[0] + dx, state[1] + dy)
            if not grid.in_bounds(cand):
                continue
            if not _is_passable(grid, cand):
                step_result = env.step((dx, dy))
                print(f"[blocked-check] tried action={(dx, dy)} -> {step_result.next_state}, info={step_result.info}")
                break

    # Check terminal on trap.
    if trap_pos is not None:
        path = _bfs_path(grid, start_pos, trap_pos)
        if path is None:
            print(f"[trap-check] cannot find passable path from start to trap at {trap_pos}")
        else:
            env.reset()
            print(f"[trap-check] trap_pos={trap_pos}")
            _simulate_path(env, path)
            # After simulation, env's last `step_result` isn't captured here,
            # so we do a quick direct check by stepping again if desired.
    else:
        print("[trap-check] no trap found in map")

    # Check terminal on goal.
    path = _bfs_path(grid, start_pos, goal_pos)
    if path is None:
        raise RuntimeError(f"[goal-check] cannot reach goal from start in passable graph. start={start_pos}, goal={goal_pos}")
    print(f"[goal-check] goal_pos={goal_pos}")
    _simulate_path(env, path)


if __name__ == "__main__":
    main()

