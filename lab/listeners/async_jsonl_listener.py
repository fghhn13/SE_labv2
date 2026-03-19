from __future__ import annotations

import json
import os
import queue
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from .base import Listener


@dataclass(frozen=True)
class AsyncJsonlListenerConfig:
    """
    Minimal async jsonl writer.

    - `max_queue_size` bounds trainer memory usage.
    - `flush_every_n` controls background flush frequency.
    """

    max_queue_size: int = 10000
    flush_every_n: int = 200
    encoding: str = "utf-8"


class AsyncJsonlListener(Listener):
    """
    Background thread writes events to a jsonl file.

    Trainer main thread only does `queue.put(event)` which is expected
    to be fast (optionally bounded by queue size).
    """

    def __init__(
        self,
        output_file: str | Path,
        *,
        config: Optional[AsyncJsonlListenerConfig] = None,
    ) -> None:
        self.output_file = str(output_file)
        self.config = config or AsyncJsonlListenerConfig()

        out_path = Path(self.output_file)
        os.makedirs(out_path.parent, exist_ok=True)
        # Ensure file exists
        out_path.touch(exist_ok=True)

        self._q: queue.Queue[Dict[str, Any] | None] = queue.Queue(
            maxsize=int(self.config.max_queue_size)
        )
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()

    def on_step(self, event: Dict[str, Any]) -> None:
        self._enqueue(event)

    def on_episode_end(self, event: Dict[str, Any]) -> None:
        self._enqueue(event)

    def close(self) -> None:
        # Signal stop and wait for flush.
        self._stop_event.set()
        # Sentinel: put None to unblock worker even if queue is full.
        # If queue is full, remove one oldest event to make room.
        try:
            self._q.put_nowait(None)
        except queue.Full:
            _ = self._q.get_nowait()
            self._q.put_nowait(None)
        self._thread.join(timeout=10.0)

    def _enqueue(self, event: Dict[str, Any]) -> None:
        # Non-blocking enqueue to protect trainer FPS.
        try:
            self._q.put_nowait(event)
        except queue.Full:
            # Drop oldest to make room.
            try:
                _ = self._q.get_nowait()
                self._q.put_nowait(event)
            except queue.Empty:
                return

    def _worker(self) -> None:
        out_path = Path(self.output_file)
        write_count = 0
        with out_path.open("a", encoding=self.config.encoding) as f:
            while True:
                item = self._q.get()
                if item is None:
                    break

                f.write(json.dumps(item, ensure_ascii=False) + "\n")
                write_count += 1
                if write_count % int(self.config.flush_every_n) == 0:
                    f.flush()

            # Final flush on exit
            f.flush()


def _build_async_jsonl_listener(
    *,
    output_file: str | Path,
    max_queue_size: int = 10000,
    flush_every_n: int = 200,
    encoding: str = "utf-8",
    **_kwargs: Any,
) -> AsyncJsonlListener:
    cfg = AsyncJsonlListenerConfig(
        max_queue_size=max_queue_size,
        flush_every_n=flush_every_n,
        encoding=encoding,
    )
    return AsyncJsonlListener(output_file=output_file, config=cfg)


# Auto-register for config-driven construction.
from lab.listeners.registry import register as _register_listener

_register_listener("async_jsonl", _build_async_jsonl_listener)

