import json
import os
import sys
from typing import Any, Dict

from lab.core.types import EpisodeResult
from lab.envs import registry as env_registry
from lab.agents import registry as agent_registry
from lab.structure import registry as structure_registry
from lab.trainer.loop import Trainer
from lab.logging.csv_logger import CsvEpisodeLogger
from lab.envs.grid.grid_map import GridMap
from lab.envs.grid.environment import GridWorldEnvironment
from lab.agents.random_agent import RandomAgent


def _register_defaults() -> None:
    # Env: basic grid
    def build_grid_env(**kwargs: Any):
        width = kwargs.get("width", 5)
        height = kwargs.get("height", 5)
        start = tuple(kwargs.get("start", (0, 0)))
        goal = tuple(kwargs.get("goal", (width - 1, height - 1)))
        walls = set(map(tuple, kwargs.get("walls", [])))
        grid = GridMap(width=width, height=height, start=start, goal=goal, walls=walls)
        return GridWorldEnvironment(grid_map=grid)

    env_registry.register("grid_basic", build_grid_env)

    # Agent: random
    def build_random_agent(**kwargs: Any):
        return RandomAgent(seed=kwargs.get("seed"))

    agent_registry.register("random", build_random_agent)

    # Structure: placeholder no-op
    class NoOpStructure:
        def on_episode_end(self, result: EpisodeResult, env):
            return

        def query(self, state):
            return None

    def build_noop_structure(**kwargs: Any):
        return NoOpStructure()

    structure_registry.register("none", build_noop_structure)


def load_config(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main(config_path: str) -> None:
    _register_defaults()
    cfg = load_config(config_path)

    env_cfg = cfg.get("env", {})
    agent_cfg = cfg.get("agent", {})
    structure_cfg = cfg.get("structure", {})
    trainer_cfg = cfg.get("trainer", {})
    logging_cfg = cfg.get("logging", {})

    env = env_registry.create(env_cfg.get("name", "grid_basic"), **env_cfg)
    agent = agent_registry.create(agent_cfg.get("name", "random"))
    structure = structure_registry.create(structure_cfg.get("name", "none"))

    callbacks = []
    csv_path = logging_cfg.get("csv_path")
    if csv_path:
        os.makedirs(os.path.dirname(csv_path), exist_ok=True)
        callbacks.append(CsvEpisodeLogger(csv_path))

    trainer = Trainer(
        env=env,
        agent=agent,
        structure=structure,
        callbacks=callbacks,
        max_steps=trainer_cfg.get("max_steps", 100),
    )
    episodes = trainer_cfg.get("episodes", 50)
    trainer.run(episodes)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m lab.cli.run_experiment <config_path>")
        sys.exit(1)
    main(sys.argv[1])

