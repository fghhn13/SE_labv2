from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol


class Reporter(Protocol):
    """
    Offline reporter reads raw artifacts (e.g. events.jsonl) and produces
    human-readable summaries/plots.
    """

    def generate(self) -> str:
        """
        Return a rendered report string (also printed by CLI).
        """
        ...

