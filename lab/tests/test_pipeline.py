from __future__ import annotations

import json
from pathlib import Path


def test_pipeline_smoke(tmp_path: Path) -> None:
    """
    Integration test:
    - load map (via env registry defaults)
    - run 5 episodes
    - validate jsonl fields (events.jsonl)
    - run reporter (text_summary) and assert success_rate exists
    """
    from lab.cli.run import run_pipeline_from_config

    config = {
        "episodes": 5,
        "env": {"name": "grid_basic", "kwargs": {"map_name": "open_5x5"}},
        "agent": {"name": "greedy", "kwargs": {"seed": 1, "epsilon": 0.0}},
        "trainer": {"name": "standard", "kwargs": {"max_steps": 20, "record_path": False}},
        "listeners": [
            {"name": "async_jsonl", "kwargs": {"output_file": "events.jsonl"}}
        ],
        "reporters": [
            {
                "name": "text_summary",
                "kwargs": {"source_file": "events.jsonl", "output_file": "summary.txt"},
            }
        ],
    }

    run_dir = tmp_path / "RUN_TEST"
    meta = run_pipeline_from_config(config, run_dir=run_dir)

    events_path = Path(meta["events_path"])
    summary_path = Path(meta["summary_path"])

    assert events_path.exists(), f"events.jsonl not found: {events_path}"
    assert summary_path.exists(), f"summary.txt not found: {summary_path}"

    lines = events_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) > 0

    events = [json.loads(line) for line in lines if line.strip()]
    assert any(ev.get("event_type") == "episode_end" for ev in events)

    episode_end_events = [ev for ev in events if ev.get("event_type") == "episode_end"]
    assert len(episode_end_events) == 5

    required_episode_end_keys = {"schema_version", "run_id", "event_type", "episode", "steps", "success"}
    for ev in episode_end_events:
        assert required_episode_end_keys.issubset(set(ev.keys()))
        assert isinstance(ev["episode"], int)
        assert isinstance(ev["steps"], int)
        assert isinstance(ev["success"], bool)

    summary_text = summary_path.read_text(encoding="utf-8")
    assert "Success Rate:" in summary_text

