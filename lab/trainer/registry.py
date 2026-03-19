from __future__ import annotations

from typing import Any, Callable, Dict, Optional, Type

from lab.core.interfaces import Agent, Environment


TrainerBuilder = Callable[..., Any]

_REGISTRY: Dict[str, TrainerBuilder] = {}


def register(name: str, builder: TrainerBuilder) -> None:
    _REGISTRY[name] = builder


def create(
    name: str,
    *,
    env: Environment,
    agent: Agent,
    listeners: Optional[list[Any]] = None,
    **kwargs: Any,
) -> Any:
    """
    Factory for trainer variants.

    Contract:
    - `name` must be registered via `register(name, builder)`.
    - `env` is required (keyword-only).
    - `agent` is required (keyword-only).
    - `listeners` is optional; when provided it will be passed to the trainer
      builder as-is.
    - `**kwargs` are trainer-specific and are forwarded to the underlying
      trainer builder.

    Built-in example (for `name="standard"`):
    - `max_steps` (int, optional; default `50`)
    - `record_path` (bool, optional; default `False`)
    - `run_id` (str | None, optional; default: auto-generated uuid4)
    - `schema_version` (str, optional; default `"1.0"`)
    """
    if name not in _REGISTRY:
        raise ValueError(f"Unknown trainer: {name}")
    builder = _REGISTRY[name]
    if listeners is None:
        return builder(env=env, agent=agent, **kwargs)
    return builder(env=env, agent=agent, listeners=listeners, **kwargs)


def list_trainers() -> Dict[str, TrainerBuilder]:
    return dict(_REGISTRY)

