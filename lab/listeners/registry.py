from __future__ import annotations

from typing import Any, Callable, Dict, Type

from .base import Listener

ListenerBuilder = Callable[..., Listener]

_REGISTRY: Dict[str, ListenerBuilder] = {}


def register(name: str, builder: ListenerBuilder) -> None:
    _REGISTRY[name] = builder


def create(name: str, **kwargs: Any) -> Listener:
    """
    Factory for listeners.

    Contract:
    - `name` must be registered via `register(name, builder)`.
    - All remaining `**kwargs` are forwarded to the registered listener
      builder.

    Built-in example (for `name="async_jsonl"`):
    - `output_file` (str | Path) is required
    - optional:
      - `max_queue_size` (int, default `10000`)
      - `flush_every_n` (int, default `200`)
      - `encoding` (str, default `"utf-8"`)
    """
    if name not in _REGISTRY:
        raise ValueError(f"Unknown listener: {name}")
    return _REGISTRY[name](**kwargs)


def list_listeners() -> Dict[str, ListenerBuilder]:
    return dict(_REGISTRY)

