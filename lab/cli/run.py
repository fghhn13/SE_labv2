from __future__ import annotations

import argparse
import json
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from lab.agents import registry as agent_registry
from lab.envs import registry as env_registry
from lab.listeners.registry import create as create_listener
from lab.listeners.registry import list_listeners
from lab.reporters.registry import create as create_reporter
from lab.reporters.registry import list_reporters
from lab.trainer.registry import create as create_trainer
from lab.trainer.registry import list_trainers

from lab.registry_defaults import register_all_defaults


def _repo_root() -> Path:
    # lab/cli/run.py -> lab/cli -> lab -> repo root
    return Path(__file__).resolve().parents[2]


def _validate_str(name: str, value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"`{name}` must be a non-empty string")
    return value.strip()


def _require_dict(name: str, value: Any) -> Dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"`{name}` must be an object")
    return value


def _resolve_rel_to_run_dir(run_dir: Path, p: str | Path) -> Path:
    pp = Path(p)
    if pp.is_absolute():
        return pp
    return run_dir / pp


def _compute_next_run_dir(base_dir: Path, prefix: str = "RUN_") -> Path:
    base_dir.mkdir(parents=True, exist_ok=True)
    pattern = re.compile(rf"^{re.escape(prefix)}(\d+)$")
    max_n = 0
    for d in base_dir.iterdir():
        if not d.is_dir():
            continue
        m = pattern.match(d.name)
        if not m:
            continue
        max_n = max(max_n, int(m.group(1)))
    next_n = max_n + 1
    return base_dir / f"{prefix}{next_n:03d}"


def validate_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate and normalize the JSON config for the pipeline.

    Fail-fast rules (currently enforced):
    - top-level keys: `episodes`, `env`, `agent`, `trainer`, `listeners`, `reporters`
    - `env.kwargs.map_name` is required for `env.name == "grid_basic"`
    - each listener spec must have `name` and `kwargs` (dict); `async_jsonl` default
      `output_file` to `events.jsonl` if missing.
    - each reporter spec must have `name` and `kwargs` (dict); `text_summary`
      requires `source_file` (no default) and defaults `output_file` to `summary.txt`
      if missing.
    """
    if not isinstance(config, dict):
        raise ValueError("Config must be a JSON object")

    required_top = ["episodes", "env", "agent", "trainer", "listeners", "reporters"]
    for k in required_top:
        if k not in config:
            raise ValueError(f"Missing top-level key: `{k}`")

    episodes = config["episodes"]
    if not isinstance(episodes, int) or episodes <= 0:
        raise ValueError("`episodes` must be a positive integer")

    env_spec = _require_dict("env", config["env"])
    agent_spec = _require_dict("agent", config["agent"])
    trainer_spec = _require_dict("trainer", config["trainer"])
    listeners_spec = config["listeners"]
    reporters_spec = config["reporters"]

    if not isinstance(listeners_spec, list) or not listeners_spec:
        raise ValueError("`listeners` must be a non-empty list")
    if not isinstance(reporters_spec, list) or not reporters_spec:
        raise ValueError("`reporters` must be a non-empty list")

    env_name = _validate_str("env.name", env_spec.get("name"))
    agent_name = _validate_str("agent.name", agent_spec.get("name"))
    trainer_name = _validate_str("trainer.name", trainer_spec.get("name"))

    env_kwargs = _require_dict("env.kwargs", env_spec.get("kwargs", {}))
    agent_kwargs = _require_dict("agent.kwargs", agent_spec.get("kwargs", {}))
    trainer_kwargs = _require_dict("trainer.kwargs", trainer_spec.get("kwargs", {}))

    # Built-in policy: require map_name for grid_basic.
    if env_name == "grid_basic":
        if "map_name" not in env_kwargs or not isinstance(env_kwargs["map_name"], str):
            raise ValueError("`env.kwargs.map_name` is required when env.name == 'grid_basic'")
        if not env_kwargs["map_name"].strip():
            raise ValueError("`env.kwargs.map_name` must be a non-empty string")

    normalized: Dict[str, Any] = dict(config)
    normalized["episodes"] = episodes
    normalized["env"] = {"name": env_name, "kwargs": env_kwargs}
    normalized["agent"] = {"name": agent_name, "kwargs": agent_kwargs}
    normalized["trainer"] = {"name": trainer_name, "kwargs": trainer_kwargs}

    # Validate component existence (fail-fast for unknown names).
    envs_registry = env_registry.list_envs()
    agents_registry = agent_registry.list_agents()

    if env_name not in envs_registry:
        raise ValueError(f"Unknown environment: {env_name}")
    if agent_name not in agents_registry:
        raise ValueError(f"Unknown agent: {agent_name}")

    listeners_registry = list_listeners()
    reporters_registry = list_reporters()
    trainers_registry = list_trainers()

    if trainer_name not in trainers_registry:
        raise ValueError(f"Unknown trainer: {trainer_name}")

    norm_listeners: List[Dict[str, Any]] = []
    for i, lst in enumerate(listeners_spec):
        if not isinstance(lst, dict):
            raise ValueError(f"`listeners[{i}]` must be an object")
        ln = _validate_str(f"listeners[{i}].name", lst.get("name"))
        if ln not in listeners_registry:
            raise ValueError(f"Unknown listener: {ln} (at listeners[{i}])")
        kw = _require_dict(f"listeners[{i}].kwargs", lst.get("kwargs", {}))
        if ln == "async_jsonl":
            kw.setdefault("output_file", "events.jsonl")
        norm_listeners.append({"name": ln, "kwargs": kw})

    norm_reporters: List[Dict[str, Any]] = []
    for i, rep in enumerate(reporters_spec):
        if not isinstance(rep, dict):
            raise ValueError(f"`reporters[{i}]` must be an object")
        rn = _validate_str(f"reporters[{i}].name", rep.get("name"))
        if rn not in reporters_registry:
            raise ValueError(f"Unknown reporter: {rn} (at reporters[{i}])")
        kw = _require_dict(f"reporters[{i}].kwargs", rep.get("kwargs", {}))
        if rn == "text_summary":
            if "source_file" not in kw:
                raise ValueError("`reporters[].kwargs.source_file` is required for text_summary reporter")
            if not isinstance(kw["source_file"], str) or not kw["source_file"].strip():
                raise ValueError("`reporters[].kwargs.source_file` must be a non-empty string")
            kw.setdefault("output_file", "summary.txt")
        norm_reporters.append({"name": rn, "kwargs": kw})

    normalized["listeners"] = norm_listeners
    normalized["reporters"] = norm_reporters
    return normalized


def run_pipeline_from_config(
    config: Dict[str, Any],
    *,
    run_dir: Path,
    save_config_snapshot: bool = True,
) -> Dict[str, Any]:
    """
    Run the full pipeline driven by a validated config.

    Returns:
      metadata dict containing paths + run_id + reporter outputs.
    """
    # Ensure built-in registrations exist.
    register_all_defaults()
    # Auto-register side-effect components.
    import lab.trainer.standard_trainer as _  # noqa: F401
    import lab.listeners.async_jsonl_listener as _  # noqa: F401
    import lab.reporters.text_summary_reporter as _  # noqa: F401

    cfg = validate_config(config)

    run_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_id_for_dir = f"{run_dir.name}_{ts}"

    if save_config_snapshot:
        snapshot = dict(cfg)
        snapshot["_run_dir"] = str(run_dir)
        snapshot["_run_id_for_dir"] = run_id_for_dir
        (run_dir / "config.json").write_text(
            json.dumps(snapshot, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    env = env_registry.create(cfg["env"]["name"], **cfg["env"]["kwargs"])
    agent = agent_registry.create(cfg["agent"]["name"], **cfg["agent"]["kwargs"])

    # Listeners
    listeners: List[Any] = []
    for lst in cfg["listeners"]:
        l_name = lst["name"]
        l_kwargs = dict(lst["kwargs"])
        if "output_file" in l_kwargs:
            l_kwargs["output_file"] = str(
                _resolve_rel_to_run_dir(run_dir, l_kwargs["output_file"])
            )
        listeners.append(create_listener(l_name, **l_kwargs))

    # Trainer
    t_kwargs = dict(cfg["trainer"]["kwargs"])
    if cfg["trainer"]["name"] == "standard" and "run_id" not in t_kwargs:
        t_kwargs["run_id"] = run_id_for_dir

    trainer = create_trainer(
        cfg["trainer"]["name"],
        env=env,
        agent=agent,
        listeners=listeners,
        **t_kwargs,
    )

    episodes: int = int(cfg["episodes"])
    trainer.run(episodes)

    # Reporters
    reporter_outputs: Dict[str, str] = {}
    for rep in cfg["reporters"]:
        r_name = rep["name"]
        r_kwargs = dict(rep["kwargs"])
        if "source_file" in r_kwargs:
            r_kwargs["source_file"] = str(
                _resolve_rel_to_run_dir(run_dir, r_kwargs["source_file"])
            )
        if "output_file" in r_kwargs and r_kwargs["output_file"] is not None:
            r_kwargs["output_file"] = str(
                _resolve_rel_to_run_dir(run_dir, r_kwargs["output_file"])
            )

        reporter = create_reporter(r_name, **r_kwargs)
        output = reporter.generate()
        reporter_outputs[r_name] = str(output)

    events_path = run_dir / "events.jsonl"
    summary_path = run_dir / "summary.txt"

    return {
        "run_dir": str(run_dir),
        "trainer_run_id": getattr(trainer, "run_id", None),
        "events_path": str(events_path),
        "summary_path": str(summary_path),
        "reporter_outputs": reporter_outputs,
    }


def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="Run the full pipeline from JSON config.")
    parser.add_argument("--config", type=str, required=True, help="Path to pipeline config JSON.")
    parser.add_argument(
        "--runs-base-dir",
        type=str,
        default=None,
        help="Base dir for runs (default: <repo_root>/lab_v2_results/runs).",
    )
    parser.add_argument(
        "--run-id",
        type=str,
        default=None,
        help="Optional run id override for the run directory name.",
    )

    args = parser.parse_args(argv)

    cfg_path = Path(args.config)
    if not cfg_path.exists():
        raise FileNotFoundError(str(cfg_path))

    config = json.loads(cfg_path.read_text(encoding="utf-8"))
    # Ensure registries are populated before validation (fail-fast).
    register_all_defaults()
    import lab.trainer.standard_trainer as _  # noqa: F401
    import lab.listeners.async_jsonl_listener as _  # noqa: F401
    import lab.reporters.text_summary_reporter as _  # noqa: F401

    normalized_cfg = validate_config(config)  # fail-fast before creating dirs

    base_dir = (
        Path(args.runs_base_dir)
        if args.runs_base_dir is not None
        else _repo_root() / "lab_v2_results" / "runs"
    )

    if args.run_id:
        run_dir = base_dir / args.run_id
        run_dir.mkdir(parents=True, exist_ok=True)
    else:
        run_dir = _compute_next_run_dir(base_dir)

    meta = run_pipeline_from_config(normalized_cfg, run_dir=run_dir)

    print(f"[done] run_dir={meta['run_dir']}")


if __name__ == "__main__":
    main()

