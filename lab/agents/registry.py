from typing import Callable, Dict, Any

from lab.core.interfaces import Agent, Environment


AgentBuilder = Callable[..., Agent]

_REGISTRY: Dict[str, AgentBuilder] = {}


def register(name: str, builder: AgentBuilder) -> None:
    _REGISTRY[name] = builder


def create(name: str, env: Environment | None = None, **kwargs: Any) -> Agent:
    """
    env is accepted here for flexibility, but builders are free to ignore it.
    """
    if name not in _REGISTRY:
        raise ValueError(f"Unknown agent: {name}")
    builder = _REGISTRY[name]
    if env is not None:
        return builder(env=env, **kwargs)
    return builder(**kwargs)


def list_agents() -> Dict[str, AgentBuilder]:
    return dict(_REGISTRY)

