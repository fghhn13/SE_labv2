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

    def __init__(self, filepath: str, print_to_stdout: bool = True) -> None:
        self.filepath = filepath
        self.print_to_stdout = print_to_stdout
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
        # 写入 CSV
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

        # 可选：在终端打印一行简要信息，方便快速观察
        if self.print_to_stdout:
            print(
                f"[episode {episode_idx}] success={result.success} "
                f"cost={result.cost:.2f} steps={result.steps}"
            )

