"""
Agent 模板：复制此文件并重命名即可作为新 Agent 的起点。

- 继承 BaseAgent，只需实现 select_action（observe/end_episode 可选）。
- 通过 lab/registry_defaults.py 注册后，可在 JSON config 里用 agent.name 引用。
"""
from __future__ import annotations

from lab.core.interfaces import Environment
from lab.core.types import State, Action, StepResult, EpisodeResult
from .base import BaseAgent


class TemplateAgent(BaseAgent):
    """
    最小示例：在合法动作中选第一个（可改为随机/贪心等）。
    """

    def __init__(self, seed: int | None = None) -> None:
        # 可选：用 seed 控制随机性，便于复现
        self._seed = seed

    def select_action(self, state: State, env: Environment) -> Action:
        actions = env.get_actions(state)
        if not actions:
            return None
        # 示例策略：取第一个合法动作（可改为 random.choice(actions) 等）
        return actions[0]

    def observe(self, step_result: StepResult) -> None:
        # 可选：根据 step_result 更新内部状态
        return

    def end_episode(self, result: EpisodeResult) -> None:
        # 可选：回合结束时的统计/清理
        return
