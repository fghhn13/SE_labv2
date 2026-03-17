import csv
import os
from typing import Optional

from lab.core.types import EpisodeResult
from lab.core.interfaces import StructureService
from lab.trainer.loop import TrainerCallback


class CsvEpisodeLogger(TrainerCallback):
    """
    Simple per-episode CSV logger.
    """

    def __init__(self, filepath: str) -> None:
        self.filepath = filepath
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        if not os.path.exists(filepath):
            with open(filepath, mode="w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["episode", "success", "cost", "steps"])

    def on_episode_end(
        self,
        episode_idx: int,
        result: EpisodeResult,
        structure: Optional[StructureService],
    ) -> None:
        with open(self.filepath, mode="a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    episode_idx,
                    int(result.success),
                    result.cost,
                    result.steps,
                ]
            )

