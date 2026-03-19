from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from .base import Reporter


@dataclass(frozen=True)
class TextSummaryConfig:
    # If the file contains multiple runs, this reporter can filter by run_id.
    run_id: Optional[str] = None


class TextSummaryReporter(Reporter):
    """
    Offline reporter:
    - Reads events.jsonl (schema_version >= 1.0)
    - Aggregates only `event_type == "episode_end"`
    - Prints summary + optionally writes summary.txt
    """

    def __init__(
        self,
        *,
        source_file: str | Path,
        output_file: str | Path | None = None,
        config: Optional[TextSummaryConfig] = None,
        encoding: str = "utf-8",
    ) -> None:
        self.source_file = Path(source_file)
        self.output_file = Path(output_file) if output_file is not None else None
        self.config = config or TextSummaryConfig()
        self.encoding = encoding

    def _iter_events(self) -> Iterable[Dict[str, Any]]:
        with self.source_file.open("r", encoding=self.encoding) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                yield json.loads(line)

    def generate(self) -> str:
        episode_end_events: list[dict[str, Any]] = []
        for ev in self._iter_events():
            event_type = ev.get("event_type")
            if event_type != "episode_end":
                continue
            if self.config.run_id is not None and ev.get("run_id") != self.config.run_id:
                continue
            episode_end_events.append(ev)

        total_eps = len(episode_end_events)
        success_count = sum(1 for ev in episode_end_events if bool(ev.get("success", False)))
        avg_steps = (
            (sum(int(ev.get("steps", 0)) for ev in episode_end_events) / total_eps)
            if total_eps > 0
            else 0.0
        )

        success_rate = (success_count / total_eps) if total_eps > 0 else 0.0

        report_lines = [
            f"TextSummaryReporter({self.source_file})",
            f"- schema_version: {self._guess_schema_version(episode_end_events)}",
            f"- run_id filter: {self.config.run_id or '<any>'}",
            "",
            f"Total Episodes: {total_eps}",
            f"Success Rate: {success_rate * 100:.2f}%",
            f"Average Steps: {avg_steps:.2f}",
            f"Success Episodes: {success_count}",
            f"Failure Episodes: {total_eps - success_count}",
        ]
        report = "\n".join(report_lines)
        print(report)

        if self.output_file is not None:
            self.output_file.parent.mkdir(parents=True, exist_ok=True)
            self.output_file.write_text(report, encoding=self.encoding)

        return report

    @staticmethod
    def _guess_schema_version(events: list[dict[str, Any]]) -> str:
        for ev in events:
            sv = ev.get("schema_version")
            if sv is not None:
                return str(sv)
        return "unknown"


def _build_text_summary_reporter(
    *,
    source_file: str,
    output_file: str | None = None,
    run_id: str | None = None,
    **_kwargs: Any,
) -> TextSummaryReporter:
    config = TextSummaryConfig(run_id=run_id)
    return TextSummaryReporter(source_file=source_file, output_file=output_file, config=config)


# Auto-register
from lab.reporters.registry import register as _register_reporter

_register_reporter("text_summary", _build_text_summary_reporter)

