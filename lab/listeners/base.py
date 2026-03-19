from __future__ import annotations

from typing import Any, Dict, Protocol


class Listener(Protocol):
    """
    Listener consumes trainer events.

    Contract:
    - Trainer calls these methods frequently.
    - Implementations must be non-blocking w.r.t. the trainer main thread.
    - Implementations should support clean shutdown via `close()`.
    """

    def on_step(self, event: Dict[str, Any]) -> None:
        ...

    def on_episode_end(self, event: Dict[str, Any]) -> None:
        ...

    def close(self) -> None:
        ...

