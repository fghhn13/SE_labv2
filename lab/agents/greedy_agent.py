from __future__ import annotations

import random
from typing import Optional

from lab.core.interfaces import Environment
from lab.core.types import State, Action, StepResult, EpisodeResult
from lab.envs.grid.environment import GridWorldEnvironment
from lab.envs.grid.grid_map import GridMap, Coord
from .base import BaseAgent


class GreedyAgent(BaseAgent):
    """
    一个简单的启发式 Agent：
    - 在 4 邻接动作中，优先选择使得到目标的曼哈顿距离最小的动作。
    - 支持 epsilon 随机探索，用于避免完全确定性行为。

    该 Agent 依赖于 GridWorldEnvironment / GridMap 中的 start/goal 坐标。
    """

    def __init__(
        self,
        env: Optional[Environment] = None,
        seed: Optional[int] = None,
        epsilon: float = 0.0,
    ) -> None:
        """
        :param env: 可选的环境引用；如果提供且为 GridWorldEnvironment，则用于读取 goal 坐标。
        :param seed: 随机种子，用于 epsilon 探索。
        :param epsilon: 以 epsilon 概率执行随机动作（0 表示纯贪心）。
        """
        if seed is not None:
            random.seed(seed)
        self.epsilon = float(epsilon)
        self._goal: Optional[Coord] = None

        # 如果可以，从环境中获取 goal 位置
        if isinstance(env, GridWorldEnvironment):
            self._goal = env.grid.goal

    def _ensure_goal(self, env: Environment) -> None:
        if self._goal is not None:
            return
        if isinstance(env, GridWorldEnvironment):
            self._goal = env.grid.goal

    def select_action(self, state: State, env: Environment) -> Action:
        # 确保知道目标坐标；否则退化为纯随机策略
        self._ensure_goal(env)
        actions = env.get_actions(state)
        if not actions:
            return None

        # epsilon 探索：以 epsilon 概率随机选动作
        if self.epsilon > 0.0 and random.random() < self.epsilon:
            return random.choice(actions)

        # 如果没有目标信息，退化为随机
        if self._goal is None:
            return random.choice(actions)

        gx, gy = self._goal
        sx, sy = state  # 假定 state 是 (x, y)

        # 选择使曼哈顿距离最小的动作；如有平局，从平局中随机挑一个
        best_actions = []
        best_dist = None
        for (dx, dy) in actions:
            nx, ny = sx + dx, sy + dy
            # 不在这里检查墙和边界，交给环境处理
            dist = abs(nx - gx) + abs(ny - gy)
            if best_dist is None or dist < best_dist:
                best_dist = dist
                best_actions = [(dx, dy)]
            elif dist == best_dist:
                best_actions.append((dx, dy))

        return random.choice(best_actions) if best_actions else random.choice(actions)

    # observe / end_episode 保持 no-op，沿用 BaseAgent 的空实现

