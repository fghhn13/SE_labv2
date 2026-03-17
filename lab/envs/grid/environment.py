from typing import List, Tuple

from lab.core.types import State, Action, StepResult
from lab.core.interfaces import Environment
from .grid_map import GridMap, Coord


class GridWorldEnvironment(Environment):
    """
    Simple 4-neighbor grid-world for shortest-path experiments.
    """

    def __init__(self, grid_map: GridMap, step_reward: float = -1.0) -> None:
        self.grid = grid_map
        self.step_reward = step_reward
        self._state: Coord = grid_map.start

    def reset(self) -> State:
        self._state = self.grid.start
        return self._state

    def step(self, action: Action) -> StepResult:
        dx, dy = action  # expecting (dx, dy) as action
        x, y = self._state
        next_pos: Coord = (x + dx, y + dy)

        # If out of bounds or into wall, stay in place
        if not self.grid.in_bounds(next_pos) or self.grid.is_wall(next_pos):
            next_pos = self._state

        self._state = next_pos
        done = next_pos == self.grid.goal

        return StepResult(
            next_state=self._state,
            reward=self.step_reward,
            done=done,
            info={},
        )

    def get_actions(self, state: State | None = None) -> List[Action]:
        # 4-neighborhood: up, down, left, right
        return [(0, -1), (0, 1), (-1, 0), (1, 0)]

