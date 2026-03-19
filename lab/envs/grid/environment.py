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
        # Reward is intentionally not used by the physics engine yet.
        # We keep the parameter for backward compatibility with existing callers.
        self.step_reward = float(step_reward)
        self._state: Coord = grid_map.start

    def reset(self) -> State:
        self._state = self.grid.start
        return self._state

    @property
    def state(self) -> Coord:
        """
        Minimal state accessor for external debug tools / GUIs.
        Treat `_state` as internal; use this property as the stable API.
        """
        return self._state

    def step(self, action: Action) -> StepResult:
        dx, dy = action  # expecting (dx, dy) as action
        x, y = self._state
        candidate_pos: Coord = (x + dx, y + dy)

        # Default: stay in place (blocked / out of bounds).
        old_pos = self._state
        self._state = old_pos
        done = False
        info = {}

        if not self.grid.in_bounds(candidate_pos):
            info["blocked"] = True
        else:
            elem = self.grid.get_element_at(candidate_pos)
            if not elem.is_passable():
                info["blocked"] = True
            else:
                # Successful move -> interact on the element.
                self._state = candidate_pos
                outcome = elem.interact()  # {"terminal": bool, "success": bool, ...}

                done = bool(outcome.get("terminal", False))
                if "success" in outcome:
                    info["success"] = bool(outcome["success"])
                # Merge optional payload from element.
                if isinstance(outcome.get("info"), dict):
                    info.update(outcome["info"])

        # Reward is temporarily kept for API compatibility, but physics always returns 0.
        return StepResult(
            next_state=self._state,
            reward=0.0,
            done=done,
            info=info,
        )

    def get_actions(self, state: State | None = None) -> List[Action]:
        # 4-neighborhood: up, down, left, right
        return [(0, -1), (0, 1), (-1, 0), (1, 0)]

