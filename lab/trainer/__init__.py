"""
Trainer variants and registry.

`loop.py` currently hosts `BarebonesTrainer` for a minimal proof-of-loop.
"""

# Import side-effects: ensure trainer builders are registered.
from . import standard_trainer as _standard_trainer  # noqa: F401

