from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import uuid

from lab.core.interfaces import Agent, Environment
from lab.core.types import EpisodeResult
from lab.listeners.base import Listener


@dataclass(frozen=True)
class StandardTrainerConfig:
    max_steps: int = 50
    record_path: bool = False


class StandardTrainer:
    """
    Standard (online) trainer:
    - Drives env-agent interaction for `num_episodes`.
    - Emits events to async listeners (trainer main thread should not do IO).
    - Success semantics is strictly `step_result.info["success"]`.
    - Reward/cost are not used by the trainer logic; EpisodeResult.cost is set to steps.
    """

    def __init__(
        self,
        env: Environment,
        agent: Agent,
        *,
        listeners: Optional[List[Listener]] = None,
        max_steps: int = 50,
        record_path: bool = False,
        run_id: Optional[str] = None,
        schema_version: str = "1.0",
    ) -> None:
        self.env = env
        self.agent = agent
        self.listeners = listeners or []
        self.max_steps = int(max_steps)
        self.record_path = bool(record_path)
        self.run_id = run_id or str(uuid.uuid4())
        self.schema_version = str(schema_version)

    def _emit_step(self, payload: Dict[str, Any]) -> None:
        for ln in self.listeners:
            ln.on_step(payload)

    def _emit_episode_end(self, payload: Dict[str, Any]) -> None:
        for ln in self.listeners:
            ln.on_episode_end(payload)

    def run(self, num_episodes: int) -> None:
        try:
            for ep in range(int(num_episodes)):
                state = self.env.reset()
                self.agent.reset()

                path: List[Any] = [state] if self.record_path else []
                steps = 0
                success = False

                for step_idx in range(self.max_steps):
                    action = self.agent.select_action(state, self.env)
                    step_result = self.env.step(action)
                    self.agent.observe(step_result)

                    next_state = step_result.next_state
                    done = bool(step_result.done)
                    info = dict(step_result.info or {})

                    if self.record_path:
                        path.append(next_state)

                    steps += 1

                    self._emit_step(
                        {
                            "schema_version": self.schema_version,
                            "run_id": self.run_id,
                            "event_type": "step",
                            "episode": ep,
                            "step": step_idx,
                            # Keep core metrics present in every line.
                            # For non-terminal steps, success will be False.
                            "steps": step_idx + 1,
                            "success": bool(info.get("success", False)),
                            "state": state,
                            "action": action,
                            "next_state": next_state,
                            "done": done,
                            "info": info,
                        }
                    )

                    state = next_state

                    if done:
                        success = bool(info.get("success", False))
                        break

                episode_path = path if self.record_path else []
                episode_result = EpisodeResult(
                    path=episode_path,
                    cost=float(steps),
                    success=success,
                    steps=steps,
                )
                self.agent.end_episode(episode_result)

                self._emit_episode_end(
                    {
                        "schema_version": self.schema_version,
                        "run_id": self.run_id,
                        "event_type": "episode_end",
                        "episode": ep,
                        "steps": steps,
                        "success": success,
                        "path": episode_path if self.record_path else None,
                    }
                )
        finally:
            for ln in self.listeners:
                ln.close()


def _build_standard_trainer(
    *,
    env: Environment,
    agent: Agent,
    listeners: Optional[List[Listener]] = None,
    max_steps: int = 50,
    record_path: bool = False,
    run_id: Optional[str] = None,
    schema_version: str = "1.0",
    **_kwargs: Any,
) -> StandardTrainer:
    return StandardTrainer(
        env=env,
        agent=agent,
        listeners=listeners,
        max_steps=max_steps,
        record_path=record_path,
        run_id=run_id,
        schema_version=schema_version,
    )


# Auto-register for config-driven construction.
from lab.trainer.registry import register as _register_trainer

_register_trainer("standard", _build_standard_trainer)

