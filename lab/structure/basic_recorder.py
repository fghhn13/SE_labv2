from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from lab.core.interfaces import StructureService, Environment
from lab.core.types import EpisodeResult


@dataclass
class BasicRecordingStructure(StructureService):
    """
    Minimal StructureService 实现：
    - 仅记录每个 episode 的结果，方便后续分析 / 可视化。
    - 不向 Agent 提供任何反馈（query 返回 None）。
    """

    history: List[EpisodeResult] = field(default_factory=list)

    def on_episode_end(self, result: EpisodeResult, env: Environment) -> None:
        self.history.append(result)

    def query(self, state):
        return None

