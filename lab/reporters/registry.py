from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from .base import Reporter


ReporterBuilder = Callable[..., Reporter]

_REGISTRY: Dict[str, ReporterBuilder] = {}


def register(name: str, builder: ReporterBuilder) -> None:
    _REGISTRY[name] = builder


def create(
    name: str,
    *,
    source_file: str,
    output_file: Optional[str] = None,
    **kwargs: Any,
) -> Reporter:
    """
    Factory for reporters.

    Contract:
    - `name` must be registered via `register(name, builder)`.
    - `source_file` is required (path to the input events file, typically
      `events.jsonl`).
    - `output_file` is optional; when provided, the reporter may write a
      summary artifact to this path.
    - `**kwargs` are reporter-specific and are forwarded to the registered
      reporter builder.

    Built-in example (for `name="text_summary"`):
    - `source_file` (required)
    - `output_file` (optional; default `None`)
    - `run_id` (str | None, optional)
    """
    if name not in _REGISTRY:
        raise ValueError(f"Unknown reporter: {name}")
    return _REGISTRY[name](source_file=source_file, output_file=output_file, **kwargs)


def list_reporters() -> Dict[str, ReporterBuilder]:
    return dict(_REGISTRY)

