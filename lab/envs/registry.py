from typing import Callable, Dict, Any

from lab.core.interfaces import Environment


EnvBuilder = Callable[..., Environment]

_REGISTRY: Dict[str, EnvBuilder] = {}


def register(name: str, builder: EnvBuilder) -> None:
    _REGISTRY[name] = builder


def create(name: str, **kwargs: Any) -> Environment:
    if name not in _REGISTRY:
        raise ValueError(f"Unknown environment: {name}")
    return _REGISTRY[name](**kwargs)


def list_envs() -> Dict[str, EnvBuilder]:
    return dict(_REGISTRY)

