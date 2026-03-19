from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import json
from pathlib import Path
import random
from typing import Any, Dict, List, Optional, Tuple

from lab.core.interfaces import Environment
from lab.core.types import Action, EpisodeResult, State, StepResult
from lab.envs.grid.environment import GridWorldEnvironment
from .base import BaseAgent


Patch3x3 = Tuple[Tuple[int, int, int], Tuple[int, int, int], Tuple[int, int, int]]


class Facing(str, Enum):
    N = "N"
    E = "E"
    S = "S"
    W = "W"


class RelativeAction(str, Enum):
    FRONT = "front"
    BACK = "back"
    LEFT = "left"
    RIGHT = "right"


_FACINGS: Tuple[Facing, Facing, Facing, Facing] = (Facing.N, Facing.E, Facing.S, Facing.W)
_RELATIVE_ACTIONS: Tuple[RelativeAction, RelativeAction, RelativeAction, RelativeAction] = (
    RelativeAction.FRONT,
    RelativeAction.BACK,
    RelativeAction.LEFT,
    RelativeAction.RIGHT,
)
_FACING_TO_ABS_ACTION: Dict[Facing, Action] = {
    Facing.N: (0, -1),
    Facing.E: (1, 0),
    Facing.S: (0, 1),
    Facing.W: (-1, 0),
}


@dataclass
class AffordanceStat:
    move_count: int = 0
    stuck_count: int = 0


@dataclass
class Neuron:
    prototype: Patch3x3
    stats: Dict[RelativeAction, AffordanceStat]
    energy: float = 10.0

    def get_prediction(self, action: RelativeAction) -> float:
        stat = self.stats[action]
        denom = stat.move_count + stat.stuck_count
        if denom <= 0:
            return 0.5
        return stat.move_count / float(denom)


class HebbianAgent(BaseAgent):
    """
    Stage 2 Hebbian agent:
    - 3x3 egocentric perception aligned by facing.
    - Unlimited neurons with WTA prototype matching.
    - Prediction-error-driven neurogenesis.
    - Hebbian synapses between neurons based on agreement with actual outcomes.
    """

    def __init__(
        self,
        env: Optional[Environment] = None,
        *,
        seed: Optional[int] = None,
        epsilon: float = 0.1,
        prototype_lr: float = 0.2,
        init_facing: str = "N",
        oob_as_wall: bool = True,
        oob_code: int = -1,
        wall_code: int = 1,
        energy_decay: float = 0.05,
        energy_boost: float = 2.0,
        max_energy: float = 100.0,
    ) -> None:
        if not (0.0 <= epsilon <= 1.0):
            raise ValueError("epsilon must be in [0, 1]")
        if not (0.0 <= prototype_lr <= 1.0):
            raise ValueError("prototype_lr must be in [0, 1]")

        self._env = env
        self._rng = random.Random(seed)
        self._epsilon = float(epsilon)
        self._prototype_lr = float(prototype_lr)
        self._oob_as_wall = bool(oob_as_wall)
        self._oob_code = int(oob_code)
        self._wall_code = int(wall_code)
        self._energy_decay = float(energy_decay)
        self._energy_boost = float(energy_boost)
        self._max_energy = float(max_energy)

        self._init_facing = self._parse_facing(init_facing)
        self._facing = self._init_facing

        self._neurons: Dict[int, Neuron] = {}
        self._next_neuron_id: int = 0
        self._synapses: Dict[Tuple[int, int], float] = {}

        self._last_winner_id: Optional[int] = None
        self._last_action: Optional[RelativeAction] = None
        self._last_patch: Optional[Patch3x3] = None
        self._last_state: Optional[Tuple[int, int]] = None

    def reset(self) -> None:
        self._facing = self._init_facing
        self._last_winner_id = None
        self._last_action = None
        self._last_patch = None
        self._last_state = None

    def set_epsilon(self, epsilon: float) -> None:
        if not (0.0 <= epsilon <= 1.0):
            raise ValueError("epsilon must be in [0, 1]")
        self._epsilon = float(epsilon)

    def select_action(self, state: State, env: Environment) -> Action:
        grid_env = self._as_grid_env(env)
        patch = self._extract_egocentric_patch(grid_env, state, self._facing)
        winner_id = self._pick_winner(patch)
        neuron = self._neurons[winner_id]

        scores: Dict[RelativeAction, float] = {}
        for ra in _RELATIVE_ACTIONS:
            scores[ra] = neuron.get_prediction(ra)

        rel_action = self._select_relative_action(scores)
        next_facing = self._relative_action_to_facing(self._facing, rel_action)
        abs_action = _FACING_TO_ABS_ACTION[next_facing]

        self._facing = next_facing
        self._last_winner_id = winner_id
        self._last_action = rel_action
        self._last_patch = patch
        self._last_state = self._coerce_coord(state)
        return abs_action

    def observe(self, step_result: StepResult) -> None:
        if (
            self._last_winner_id is None
            or self._last_action is None
            or self._last_patch is None
            or self._last_state is None
        ):
            return

        winner_id = self._last_winner_id
        if winner_id not in self._neurons:
            return
        winner = self._neurons[winner_id]
        action = self._last_action

        blocked = bool((step_result.info or {}).get("blocked", False))
        moved = step_result.next_state != self._last_state
        actual = 0.0 if blocked or not moved else 1.0

        P_move = winner.get_prediction(action)
        PE = abs(actual - P_move)

        stat = winner.stats[action]
        experience = stat.move_count + stat.stuck_count

        did_split = False
        if experience >= 3 and PE > 0.7:
            # Mechanism A: neurogenesis
            new_id = self._add_neuron(self._last_patch)
            new_neuron = self._neurons[new_id]
            if actual == 1.0:
                new_neuron.stats[action].move_count += 1
            else:
                new_neuron.stats[action].stuck_count += 1

            winner_id = new_id
            winner = new_neuron
            did_split = True

        # Mechanism B: Hebbian synapses
        for j_id, neuron_j in self._neurons.items():
            P_j = neuron_j.get_prediction(action)
            diff = abs(P_j - actual)
            key = (winner_id, j_id)
            w = self._synapses.get(key, 0.0)
            if diff < 0.3:
                w += 0.1
            elif diff > 0.7:
                w -= 0.1
            self._synapses[key] = w

        # Mechanism C: stats update and prototype nudge
        if not did_split:
            if actual == 1.0:
                winner.stats[action].move_count += 1
            else:
                winner.stats[action].stuck_count += 1

        winner.prototype = self._nudge_prototype(winner.prototype, self._last_patch)

        # Mechanism D: metabolism & apoptosis
        winner.energy = min(self._max_energy, winner.energy + self._energy_boost)
        for neuron in self._neurons.values():
            neuron.energy -= self._energy_decay

        dead_ids = {nid for nid, neuron in self._neurons.items() if neuron.energy <= 0.0}
        if dead_ids:
            for dead_id in dead_ids:
                del self._neurons[dead_id]
            self._synapses = {
                (i, j): w
                for (i, j), w in self._synapses.items()
                if i not in dead_ids and j not in dead_ids
            }

    def end_episode(self, result: EpisodeResult) -> None:
        return

    def dump_state(self, path: str | Path) -> None:
        payload = {
            "version": "hebbian.v1",
            "config": {
                "epsilon": self._epsilon,
                "prototype_lr": self._prototype_lr,
                "oob_as_wall": self._oob_as_wall,
                "oob_code": self._oob_code,
                "wall_code": self._wall_code,
                "init_facing": self._init_facing.value,
                "energy_decay": self._energy_decay,
                "energy_boost": self._energy_boost,
                "max_energy": self._max_energy,
            },
            "runtime": {
                "facing": self._facing.value,
                "next_neuron_id": self._next_neuron_id,
                "neurons": [self._neuron_to_dict(nid, neuron) for nid, neuron in self._neurons.items()],
                "synapses": [
                    {"from": int(i), "to": int(j), "weight": float(w)}
                    for (i, j), w in self._synapses.items()
                    if w != 0.0
                ],
            },
        }
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def load_state(self, path: str | Path) -> None:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        runtime = payload.get("runtime", {})
        neurons_raw = runtime.get("neurons", [])
        synapses_raw = runtime.get("synapses", [])

        self._facing = self._parse_facing(runtime.get("facing", self._init_facing.value))
        self._neurons = {}
        max_seen_id = -1
        for idx, item in enumerate(neurons_raw):
            neuron_id = int(item.get("id", idx))
            self._neurons[neuron_id] = self._neuron_from_dict(item)
            if neuron_id > max_seen_id:
                max_seen_id = neuron_id
        runtime_next_id = runtime.get("next_neuron_id")
        if runtime_next_id is None:
            self._next_neuron_id = max_seen_id + 1 if max_seen_id >= 0 else 0
        else:
            self._next_neuron_id = int(runtime_next_id)
        self._synapses = {}
        for edge in synapses_raw:
            i = int(edge.get("from", 0))
            j = int(edge.get("to", 0))
            w = float(edge.get("weight", 0.0))
            self._synapses[(i, j)] = w

        self._last_winner_id = None
        self._last_action = None
        self._last_patch = None
        self._last_state = None

    # === internal helpers ===

    def _as_grid_env(self, env: Environment) -> GridWorldEnvironment:
        if isinstance(env, GridWorldEnvironment):
            return env
        if isinstance(self._env, GridWorldEnvironment):
            return self._env
        raise TypeError("HebbianAgent requires GridWorldEnvironment.")

    def _parse_facing(self, facing: str | Facing) -> Facing:
        if isinstance(facing, Facing):
            return facing
        try:
            return Facing(str(facing).upper())
        except ValueError as exc:
            raise ValueError(f"Unknown facing: {facing}") from exc

    def _coerce_coord(self, state: State) -> Tuple[int, int]:
        if isinstance(state, tuple) and len(state) == 2:
            return int(state[0]), int(state[1])
        raise ValueError(f"State must be (x, y), got: {state!r}")

    def _extract_egocentric_patch(
        self, env: GridWorldEnvironment, state: State, facing: Facing
    ) -> Patch3x3:
        cx, cy = self._coerce_coord(state)
        rows: List[Tuple[int, int, int]] = []
        for dy in (-1, 0, 1):
            row: List[int] = []
            for dx in (-1, 0, 1):
                px, py = cx + dx, cy + dy
                if env.grid.in_bounds((px, py)):
                    row.append(env.grid.get_numeric_code_at((px, py)))
                else:
                    row.append(self._wall_code if self._oob_as_wall else self._oob_code)
            rows.append((row[0], row[1], row[2]))
        patch: Patch3x3 = (rows[0], rows[1], rows[2])
        return self._rotate_patch_to_facing_north(patch, facing)

    def _rotate_patch_to_facing_north(self, patch: Patch3x3, facing: Facing) -> Patch3x3:
        if facing == Facing.N:
            return patch
        if facing == Facing.E:
            return self._rotate_ccw(patch)
        if facing == Facing.S:
            return self._rotate_180(patch)
        return self._rotate_cw(patch)

    def _rotate_cw(self, patch: Patch3x3) -> Patch3x3:
        return (
            (patch[2][0], patch[1][0], patch[0][0]),
            (patch[2][1], patch[1][1], patch[0][1]),
            (patch[2][2], patch[1][2], patch[0][2]),
        )

    def _rotate_ccw(self, patch: Patch3x3) -> Patch3x3:
        return (
            (patch[0][2], patch[1][2], patch[2][2]),
            (patch[0][1], patch[1][1], patch[2][1]),
            (patch[0][0], patch[1][0], patch[2][0]),
        )

    def _rotate_180(self, patch: Patch3x3) -> Patch3x3:
        return (
            (patch[2][2], patch[2][1], patch[2][0]),
            (patch[1][2], patch[1][1], patch[1][0]),
            (patch[0][2], patch[0][1], patch[0][0]),
        )

    def _hamming_distance(self, a: Patch3x3, b: Patch3x3) -> int:
        dist = 0
        for y in range(3):
            for x in range(3):
                if a[y][x] != b[y][x]:
                    dist += 1
        return dist

    def _new_neuron(self, patch: Patch3x3) -> Neuron:
        return Neuron(
            prototype=patch,
            stats={ra: AffordanceStat() for ra in _RELATIVE_ACTIONS},
        )

    def _allocate_neuron_id(self) -> int:
        neuron_id = self._next_neuron_id
        self._next_neuron_id += 1
        return neuron_id

    def _add_neuron(self, patch: Patch3x3) -> int:
        neuron_id = self._allocate_neuron_id()
        self._neurons[neuron_id] = self._new_neuron(patch)
        return neuron_id

    def _pick_winner(self, patch: Patch3x3) -> int:
        if not self._neurons:
            return self._add_neuron(patch)

        winner_id: Optional[int] = None
        winner_dist: Optional[int] = None
        for neuron_id, neuron in self._neurons.items():
            dist = self._hamming_distance(neuron.prototype, patch)
            if winner_dist is None or dist < winner_dist:
                winner_dist = dist
                winner_id = neuron_id
        if winner_id is None:
            return self._add_neuron(patch)
        return winner_id

    def _select_relative_action(self, scores: Dict[RelativeAction, float]) -> RelativeAction:
        if self._rng.random() < self._epsilon:
            return self._rng.choice(list(_RELATIVE_ACTIONS))
        best = max(scores.values())
        cands = [ra for ra, s in scores.items() if s == best]
        return self._rng.choice(cands)

    def _relative_action_to_facing(self, facing: Facing, action: RelativeAction) -> Facing:
        idx = _FACINGS.index(facing)
        if action == RelativeAction.FRONT:
            return _FACINGS[idx]
        if action == RelativeAction.BACK:
            return _FACINGS[(idx + 2) % 4]
        if action == RelativeAction.LEFT:
            return _FACINGS[(idx - 1) % 4]
        return _FACINGS[(idx + 1) % 4]

    def _nudge_prototype(self, prototype: Patch3x3, sample: Patch3x3) -> Patch3x3:
        rows: List[Tuple[int, int, int]] = []
        for y in range(3):
            row: List[int] = []
            for x in range(3):
                if prototype[y][x] != sample[y][x] and self._rng.random() < self._prototype_lr:
                    row.append(sample[y][x])
                else:
                    row.append(prototype[y][x])
            rows.append((row[0], row[1], row[2]))
        return (rows[0], rows[1], rows[2])

    def _neuron_to_dict(self, neuron_id: int, neuron: Neuron) -> Dict[str, Any]:
        return {
            "id": int(neuron_id),
            "energy": float(neuron.energy),
            "prototype": [list(row) for row in neuron.prototype],
            "stats": {
                ra.value: {
                    "move_count": int(neuron.stats[ra].move_count),
                    "stuck_count": int(neuron.stats[ra].stuck_count),
                }
                for ra in _RELATIVE_ACTIONS
            },
        }

    def _neuron_from_dict(self, item: Dict[str, Any]) -> Neuron:
        proto_raw = item.get("prototype")
        if not isinstance(proto_raw, list) or len(proto_raw) != 3:
            raise ValueError("Invalid neuron prototype in state file.")
        rows: List[Tuple[int, int, int]] = []
        for row in proto_raw:
            if not isinstance(row, list) or len(row) != 3:
                raise ValueError("Invalid neuron prototype row in state file.")
            rows.append((int(row[0]), int(row[1]), int(row[2])))
        prototype: Patch3x3 = (rows[0], rows[1], rows[2])

        stats_raw = item.get("stats", {})
        stats: Dict[RelativeAction, AffordanceStat] = {}
        for ra in _RELATIVE_ACTIONS:
            raw = stats_raw.get(ra.value, {})
            stats[ra] = AffordanceStat(
                move_count=int(raw.get("move_count", 0)),
                stuck_count=int(raw.get("stuck_count", 0)),
            )
        energy = float(item.get("energy", 10.0))
        return Neuron(prototype=prototype, stats=stats, energy=energy)

