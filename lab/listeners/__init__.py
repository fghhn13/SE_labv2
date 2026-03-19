"""
Listeners consume trainer events during online training.

The first implementation focuses on an async jsonl writer so that the
trainer main thread never performs blocking IO.
"""

# Import side-effects: ensure listener builders are registered.
from . import async_jsonl_listener as _async_jsonl_listener  # noqa: F401

