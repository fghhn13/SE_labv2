from typing import List, Optional

from lab.core.interfaces import Environment, Agent, StructureService
from lab.core.types import EpisodeResult


class TrainerCallback:
    """
    Simple callback interface for logging / metrics / visualization hooks.
    """

    def on_episode_end(
        self,
        episode_idx: int,
        result: EpisodeResult,
        structure: Optional[StructureService],
    ) -> None:
        ...


class Trainer:
    """
    Controls the episode loop.
    Agents focus on step-level decisions; StructureService handles structure updates.
    """

    def __init__(
        self,
        env: Environment,
        agent: Agent,
        structure: Optional[StructureService] = None,
        callbacks: Optional[List[TrainerCallback]] = None,
        max_steps: int = 100,
    ) -> None:
        self.env = env
        self.agent = agent
        self.structure = structure
        self.callbacks = callbacks or []
        self.max_steps = max_steps
        # 允许从某个 episode 索引开始，用于简单的断点续训（基于日志的续跑）
        self.start_episode: int = 0

    def run(self, num_episodes: int) -> None:
        for local_ep in range(num_episodes):
            ep = self.start_episode + local_ep
            state = self.env.reset()
            self.agent.reset()

            path = [state]
            total_cost = 0.0
            success = False

            for _step_idx in range(self.max_steps):
                action = self.agent.select_action(state, self.env)
                step_result = self.env.step(action)
                self.agent.observe(step_result)

                state = step_result.next_state
                path.append(state)
                total_cost += step_result.reward

                if step_result.done:
                    success = True
                    break

            episode_result = EpisodeResult(
                path=path,
                cost=total_cost,
                success=success,
                steps=len(path) - 1,
            )

            self.agent.end_episode(episode_result)

            if self.structure is not None:
                self.structure.on_episode_end(episode_result, self.env)

            for cb in self.callbacks:
                cb.on_episode_end(ep, episode_result, self.structure)

