from typing import Protocol, List, Optional

from .types import State, Action, StepResult, EpisodeResult


class Environment(Protocol):
    """
    Generic environment interface for the lab.
    """

    def reset(self) -> State:
        ...

    def step(self, action: Action) -> StepResult:
        ...

    def get_actions(self, state: Optional[State] = None) -> List[Action]:
        ...


class Agent(Protocol):
    """
    Agent focuses on step-level decision making.
    The Trainer controls the episode loop.
    """

    def reset(self) -> None:
        ...

    def select_action(self, state: State, env: Environment) -> Action:
        ...

    def observe(self, step_result: StepResult) -> None:
        ...

    def end_episode(self, result: EpisodeResult) -> None:
        ...


class StructureService(Protocol):
    """
    Interface that hides memory / macro / discovery / forgetting details.
    """

    def on_episode_end(self, result: EpisodeResult, env: Environment) -> None:
        ...

    def query(self, state: State):
        """
        Return any structure-related suggestion for a given state.
        The concrete return type is intentionally left open.
        """
        ...

