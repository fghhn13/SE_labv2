import random

from lab.core.interfaces import Agent, Environment
from lab.core.types import State, Action, StepResult, EpisodeResult
from .base import BaseAgent


class RandomAgent(BaseAgent):
    """
    Baseline agent: uniformly random over legal actions.
    """

    def __init__(self, seed: int | None = None) -> None:
        if seed is not None:
            random.seed(seed)

    def select_action(self, state: State, env: Environment) -> Action:
        actions = env.get_actions(state)
        if not actions:
            return None  # env should handle this gracefully
        return random.choice(actions)

    def observe(self, step_result: StepResult) -> None:
        # No learning in the baseline agent.
        return

    def end_episode(self, result: EpisodeResult) -> None:
        # Could stash simple stats into result.extras later.
        return

