from dataclasses import dataclass, field
from typing import Any, List, Dict


State = Any
Action = Any
Cost = float
Path = List[State]


@dataclass
class StepResult:
    """
    Result of a single environment step.
    """

    next_state: State
    reward: float
    done: bool
    info: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EpisodeResult:
    """
    Summary of a full episode rollout.
    """

    path: Path
    cost: Cost
    success: bool
    steps: int
    extras: Dict[str, Any] = field(default_factory=dict)

