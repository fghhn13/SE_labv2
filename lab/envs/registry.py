from typing import Callable, Dict, Any

from lab.core.interfaces import Environment


EnvBuilder = Callable[..., Environment]

_REGISTRY: Dict[str, EnvBuilder] = {}


def register(name: str, builder: EnvBuilder) -> None:
    _REGISTRY[name] = builder


def create(name: str, **kwargs: Any) -> Environment:
    """
    Factory for environments.

    Contract:
    - `name` must be registered via `register(name, builder)`.
    - `**kwargs` are forwarded to the registered environment builder.
      There is no universal schema for all environments; each environment
      builder defines its own accepted keyword arguments.

    Built-in example (for `name="grid_basic"`):
    - optional `map_name` (str; default `"open_5x5"`)
    """
    if name not in _REGISTRY:
        raise ValueError(f"Unknown environment: {name}")
    return _REGISTRY[name](**kwargs)


def list_envs() -> Dict[str, EnvBuilder]:
    return dict(_REGISTRY)

