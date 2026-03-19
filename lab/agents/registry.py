from typing import Callable, Dict, Any

from lab.core.interfaces import Agent, Environment


AgentBuilder = Callable[..., Agent]

_REGISTRY: Dict[str, AgentBuilder] = {}


def register(name: str, builder: AgentBuilder) -> None:
    _REGISTRY[name] = builder


def create(name: str, env: Environment | None = None, **kwargs: Any) -> Agent:
    """
    env is accepted here for flexibility, but builders are free to ignore it.

    Contract:
    - `name` must be registered via `register(name, builder)`.
    - `env` is optional and only used if the registered agent builder
      accepts an `env` keyword (some agents may read goal/state information
      from certain environment types).
    - `**kwargs` are agent-specific and forwarded to the builder.

    Built-in examples:
    - `name="random"`:
      - optional `seed` (int | None)
    - `name="greedy"`:
      - optional `seed` (int | None)
      - optional `epsilon` (float; default `0.0`)
    """
    if name not in _REGISTRY:
        raise ValueError(f"Unknown agent: {name}")
    builder = _REGISTRY[name]
    if env is not None:
        return builder(env=env, **kwargs)
    return builder(**kwargs)


def list_agents() -> Dict[str, AgentBuilder]:
    return dict(_REGISTRY)

